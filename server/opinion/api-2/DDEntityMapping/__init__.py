# DDEntityMapping/__init__.py
"""
Phase 6: Entity Mapping Endpoint

Maps entities across documents to identify relationships with the target.
Runs after classification, before Pass 1 extraction.

Features:
- Extracts all entities from documents
- Classifies relationship to target
- Identifies subsidiaries, counterparties, related parties
- Triggers human confirmation checkpoint when needed
"""
import logging
import os
import json
import datetime
import azure.functions as func
import uuid as uuid_module

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence, DDEntityMap, DDAnalysisRun
from shared.document_selector import get_processable_documents

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "")


def get_claude_client():
    """Import and create Claude client (deferred to avoid import errors)."""
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.claude_client import ClaudeClient
    return ClaudeClient()


def extract_text_from_document(doc_id: str, file_type: str) -> str:
    """Extract text content from a document for entity mapping."""
    from DDProcessAllDev import extract_text_from_file_with_extension

    if DEV_MODE and LOCAL_STORAGE_PATH:
        file_path = os.path.join(LOCAL_STORAGE_PATH, "docs", doc_id)
    else:
        file_path = os.path.join("/tmp/dd_storage", "docs", doc_id)

    try:
        text = extract_text_from_file_with_extension(file_path, file_type)

        # Truncate to approximately 12500 tokens (~50000 characters)
        max_chars = 50000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... truncated for entity mapping ...]"

        return text
    except Exception as e:
        logging.warning(f"Failed to extract text from {doc_id}: {e}")
        return ""


def run_entity_mapping(dd_id: str, run_id: str = None, max_docs: int = None) -> dict:
    """
    Run entity mapping for a DD project.

    Args:
        dd_id: The UUID of the DD project
        run_id: Optional analysis run ID to associate with
        max_docs: Optional limit on number of documents to process

    Returns:
        dict with entity mapping results
    """
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.entity_mapping import (
        map_entities_for_document,
        aggregate_entity_map,
        store_entity_map,
        check_entity_checkpoint_trigger
    )

    logging.info(f"[DDEntityMapping] Starting entity mapping for DD: {dd_id}")

    # Initialize Claude client
    try:
        client = get_claude_client()
    except Exception as e:
        logging.error(f"Failed to initialize Claude client: {e}")
        return {"error": f"Failed to initialize AI client: {str(e)}", "status": "failed"}

    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    with transactional_session() as session:
        # Verify DD exists
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
        if not dd:
            return {"error": f"Due diligence {dd_id} not found", "status": "failed"}

        # Get target entity information from dd.project_setup (stored directly on the DD record)
        # This is the correct approach - linked by dd_id, no name matching needed
        project_setup = dd.project_setup or {}

        logging.info(f"[DDEntityMapping] DD '{dd.name}' has project_setup: {bool(project_setup)}")

        target_entity = {
            "name": project_setup.get("targetEntityName") or dd.name,
            "registration_number": project_setup.get("targetRegistrationNumber"),
            "transaction_type": project_setup.get("transactionType"),
            "deal_structure": project_setup.get("dealStructure"),
            "expected_counterparties": []
        }

        # Client entity (the acquirer/buyer in the transaction)
        client_entity = None
        if project_setup.get("clientName"):
            client_entity = {
                "name": project_setup.get("clientName"),
                "registration_number": project_setup.get("clientRegistrationNumber"),
                "role": project_setup.get("clientRole"),
                "deal_structure": project_setup.get("dealStructure"),
            }

        # Shareholders list for display
        shareholders_list = []
        if project_setup.get("shareholders"):
            for sh in project_setup.get("shareholders", []):
                if isinstance(sh, dict) and sh.get("name"):
                    shareholders_list.append({
                        "name": sh.get("name"),
                        "ownership_percentage": sh.get("percentage") or sh.get("ownership_percentage"),
                        "registration_number": sh.get("registrationNumber") or sh.get("registration_number"),
                    })
                elif isinstance(sh, str) and sh:
                    shareholders_list.append({"name": sh, "ownership_percentage": None, "registration_number": None})

        # Load known entities from project_setup
        known_entities = []

        # Add shareholders as known entities
        for sh in shareholders_list:
            if sh.get("name"):
                known_entities.append({
                    "entity_name": sh["name"],
                    "relationship_to_target": "shareholder"
                })

        # Add key customers/counterparties as known entities
        for customer in project_setup.get("keyCustomers", []):
            if isinstance(customer, dict) and customer.get("name"):
                known_entities.append({
                    "entity_name": customer["name"],
                    "relationship_to_target": "counterparty"
                })

        # Add key lenders as known entities
        for lender in project_setup.get("keyLenders", []):
            if isinstance(lender, dict) and lender.get("name"):
                known_entities.append({
                    "entity_name": lender["name"],
                    "relationship_to_target": "lender"
                })

        # Add key suppliers as known entities
        for supplier in project_setup.get("keySuppliers", []):
            if isinstance(supplier, str) and supplier:
                known_entities.append({
                    "entity_name": supplier,
                    "relationship_to_target": "supplier"
                })

        logging.info(f"[DDEntityMapping] Target entity: {target_entity['name']}, "
                     f"Registration: {target_entity['registration_number']}, "
                     f"Known entities from project_setup: {len(known_entities)}")

        # Get all classified documents using smart selection
        # This ensures we process converted PDFs instead of originals when both exist
        folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
        folder_ids = [str(f.id) for f in folders]

        # Use smart document selection to avoid processing duplicates
        all_processable = get_processable_documents(session, folder_ids)

        # Filter to only classified documents
        documents = [
            doc for doc in all_processable
            if doc.classification_status == "classified"
        ]

        logging.info(f"[DDEntityMapping] Smart selection: {len(all_processable)} processable → {len(documents)} classified")

        if max_docs:
            documents = documents[:max_docs]

        total_docs = len(documents)
        logging.info(f"[DDEntityMapping] Processing {total_docs} documents")

        if total_docs == 0:
            return {
                "dd_id": str(dd_uuid),
                "status": "no_documents",
                "message": "No classified documents found",
                "entity_map": [],
                "checkpoint_recommended": False,
                "summary": {
                    "total_unique_entities": 0,
                    "entities_needing_confirmation": 0,
                    "high_confidence_entities": 0,
                    "target_subsidiaries": 0,
                    "counterparties": 0,
                    "unknown_relationships": 0,
                },
                "total_documents_processed": 0,
                "target_entity": target_entity,
                "client_entity": client_entity,
                "shareholders": shareholders_list,
            }

        # Process each document
        per_doc_results = []
        for idx, doc in enumerate(documents):
            doc_id = str(doc.id)
            filename = doc.original_file_name
            file_type = doc.type or filename.split('.')[-1] if '.' in filename else 'pdf'

            logging.info(f"[DDEntityMapping] Processing {idx + 1}/{total_docs}: {filename}")

            try:
                # Extract text
                doc_text = extract_text_from_document(doc_id, file_type)

                if not doc_text.strip():
                    logging.warning(f"[DDEntityMapping] No text for {filename}, skipping")
                    continue

                # Map entities
                doc_dict = {
                    "id": doc_id,
                    "filename": filename,
                    "text": doc_text,
                    "doc_type": doc.ai_document_type or file_type
                }

                result = map_entities_for_document(
                    doc=doc_dict,
                    target_entity=target_entity,
                    known_entities=known_entities + [
                        {"entity_name": e["entity_name"], "relationship_to_target": e["relationship_to_target"]}
                        for e in per_doc_results
                        for ent in result.get("entities", [])
                        if ent.get("confidence", 0) >= 0.7
                    ][:20],  # Include high-confidence entities from previous docs
                    client=client,
                    verbose=True
                )

                per_doc_results.append(result)

            except Exception as e:
                logging.error(f"[DDEntityMapping] Error processing {filename}: {e}")
                per_doc_results.append({
                    "document_name": filename,
                    "entities": [],
                    "error": str(e)
                })

        # Aggregate entity map
        aggregated = aggregate_entity_map(
            per_doc_results=per_doc_results,
            target_entity=target_entity,
            client=client,
            use_ai_aggregation=False  # Use rule-based for now
        )

        entity_map = aggregated.get("entity_map", [])
        checkpoint_recommended = aggregated.get("checkpoint_recommended", False)
        checkpoint_reason = aggregated.get("checkpoint_reason")
        summary = aggregated.get("summary", {})

        # Store entity map to database
        store_result = store_entity_map(
            dd_id=str(dd_uuid),
            run_id=run_id,
            entity_map=entity_map,
            session=session
        )

        # Get cost summary
        cost_summary = client.get_cost_summary() if hasattr(client, 'get_cost_summary') else {}

        response = {
            "dd_id": str(dd_uuid),
            "run_id": run_id,
            "status": "completed",
            "total_documents_processed": len(per_doc_results),
            "entity_map": entity_map,
            "summary": summary,
            "checkpoint_recommended": checkpoint_recommended,
            "checkpoint_reason": checkpoint_reason,
            "stored_count": store_result.get("stored_count", 0),
            "cost": cost_summary,
            # Include wizard data for organogram display
            "target_entity": {
                "name": target_entity["name"],
                "registration_number": target_entity.get("registration_number"),
                "transaction_type": target_entity.get("transaction_type"),
                "deal_structure": target_entity.get("deal_structure"),
            },
            "client_entity": client_entity,
            "shareholders": shareholders_list,
        }

        logging.info(f"[DDEntityMapping] Completed: {summary.get('total_unique_entities', 0)} entities, "
                     f"{summary.get('entities_needing_confirmation', 0)} need confirmation")

        return response


def handle_get(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    Get stored entity map for a DD project.

    GET /api/dd-entity-mapping?dd_id=uuid

    Returns: {
        "dd_id": "uuid",
        "status": "success",
        "entity_map": [...],
        "summary": {...}
    }
    """
    from dd_enhanced.core.entity_mapping import get_entity_map_for_dd

    dd_id = req.params.get("dd_id")
    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id query parameter is required"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        with transactional_session() as session:
            # Verify user owns this DD
            dd_uuid = uuid_module.UUID(dd_id)
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()

            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            if dd.owned_by != email and not DEV_MODE:
                return func.HttpResponse(
                    json.dumps({"error": "Unauthorized"}),
                    status_code=403,
                    mimetype="application/json"
                )

            # Get entity map
            entity_map = get_entity_map_for_dd(dd_id, session)

            # Calculate total documents from all entities' documents_appearing_in
            all_doc_names = set()
            for entity in entity_map:
                doc_names = entity.get("documents_appearing_in", [])
                if isinstance(doc_names, list):
                    all_doc_names.update(doc_names)
            total_documents_processed = len(all_doc_names)

            # Get wizard data from dd.project_setup (stored directly on the DD record)
            # This is linked by dd_id - no name matching needed
            project_setup = dd.project_setup or {}

            logging.info(f"[DDEntityMapping GET] DD '{dd.name}' has project_setup: {bool(project_setup)}")

            # Build target entity info from project_setup
            target_entity = {
                "name": project_setup.get("targetEntityName") or dd.name,
                "registration_number": project_setup.get("targetRegistrationNumber"),
                "transaction_type": project_setup.get("transactionType"),
                "deal_structure": project_setup.get("dealStructure"),
            }

            # Build client/acquirer info
            client_entity = None
            if project_setup.get("clientName"):
                client_entity = {
                    "name": project_setup.get("clientName"),
                    "registration_number": project_setup.get("clientRegistrationNumber"),
                    "role": project_setup.get("clientRole"),
                    "deal_structure": project_setup.get("dealStructure"),
                }

            # Build shareholders list from project_setup
            shareholders = []
            for sh in project_setup.get("shareholders", []):
                if isinstance(sh, dict) and sh.get("name"):
                    shareholders.append({
                        "name": sh.get("name"),
                        "ownership_percentage": sh.get("percentage") or sh.get("ownership_percentage"),
                        "registration_number": sh.get("registrationNumber") or sh.get("registration_number"),
                    })
                elif isinstance(sh, str) and sh:
                    shareholders.append({"name": sh, "ownership_percentage": None, "registration_number": None})

            logging.info(f"[DDEntityMapping GET] Target: {target_entity['name']}, "
                        f"Client: {client_entity['name'] if client_entity else 'None'}, "
                        f"Shareholders: {len(shareholders)}")

            # Calculate summary
            summary = {
                "total_unique_entities": len(entity_map),
                "entities_needing_confirmation": sum(1 for e in entity_map if e.get("requires_human_confirmation") and not e.get("human_confirmed")),
                "entities_confirmed": sum(1 for e in entity_map if e.get("human_confirmed")),
                "high_confidence_entities": sum(1 for e in entity_map if e.get("confidence", 0) >= 0.7),
                "target_subsidiaries": sum(1 for e in entity_map if e.get("relationship_to_target") == "subsidiary"),
                "counterparties": sum(1 for e in entity_map if e.get("relationship_to_target") == "counterparty"),
                "unknown_relationships": sum(1 for e in entity_map if e.get("relationship_to_target") == "unknown"),
            }

            return func.HttpResponse(
                json.dumps({
                    "dd_id": dd_id,
                    "status": "success",
                    "entity_map": entity_map,
                    "summary": summary,
                    "total_documents_processed": total_documents_processed,
                    "target_entity": target_entity,
                    "client_entity": client_entity,
                    "shareholders": shareholders,
                }, default=str),
                status_code=200,
                mimetype="application/json"
            )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid dd_id format: {str(e)}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"[DDEntityMapping GET] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_put(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    Modify entity map using AI based on user instructions.

    PUT /api/dd-entity-mapping
    Body: {
        "dd_id": "uuid",
        "instruction": "Remove G. Pietersen and change Standard Bank to lender",
        "current_entity_map": [...] (optional - if not provided, fetches from DB)
    }

    Returns: {
        "success": true,
        "entity_map": [...],  // Modified entity map
        "changes_made": [...],
        "explanation": "Removed G. Pietersen as they are a signatory..."
    }
    """
    from dd_enhanced.core.entity_mapping import modify_entity_map_with_ai, get_entity_map_for_dd

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    dd_id = req_body.get("dd_id")
    instruction = req_body.get("instruction")
    current_entity_map = req_body.get("current_entity_map")

    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id is required"}),
            status_code=400,
            mimetype="application/json"
        )

    if not instruction:
        return func.HttpResponse(
            json.dumps({"error": "instruction is required"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        dd_uuid = uuid_module.UUID(dd_id)

        with transactional_session() as session:
            # Verify user owns this DD
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()

            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            if dd.owned_by != email and not DEV_MODE:
                return func.HttpResponse(
                    json.dumps({"error": "Unauthorized"}),
                    status_code=403,
                    mimetype="application/json"
                )

            # Get current entity map if not provided
            if not current_entity_map:
                current_entity_map = get_entity_map_for_dd(dd_id, session)

            # Get target entity info from dd.project_setup (linked by dd_id)
            project_setup = dd.project_setup or {}
            target_entity = {
                "name": project_setup.get("targetEntityName") or dd.name,
                "registration_number": project_setup.get("targetRegistrationNumber"),
            }

            # Initialize Claude client
            client = get_claude_client()

            # Modify entity map with AI
            result = modify_entity_map_with_ai(
                current_entity_map=current_entity_map,
                user_instruction=instruction,
                target_entity=target_entity,
                client=client
            )

            logging.info(f"[DDEntityMapping PUT] AI modification: {len(result.get('changes_made', []))} changes made")

            return func.HttpResponse(
                json.dumps(result, default=str),
                status_code=200,
                mimetype="application/json"
            )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid dd_id format: {str(e)}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"[DDEntityMapping PUT] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def handle_patch(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    Confirm and save the final entity map.

    PATCH /api/dd-entity-mapping
    Body: {
        "dd_id": "uuid",
        "entity_map": [...]  // Final entity map to save
    }

    Returns: {
        "success": true,
        "confirmed_count": 25,
        "message": "Entity map confirmed and saved"
    }
    """
    from dd_enhanced.core.entity_mapping import confirm_entity_map

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    dd_id = req_body.get("dd_id")
    entity_map = req_body.get("entity_map")

    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id is required"}),
            status_code=400,
            mimetype="application/json"
        )

    if not entity_map:
        return func.HttpResponse(
            json.dumps({"error": "entity_map is required"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        dd_uuid = uuid_module.UUID(dd_id)

        with transactional_session() as session:
            # Verify user owns this DD
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()

            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            if dd.owned_by != email and not DEV_MODE:
                return func.HttpResponse(
                    json.dumps({"error": "Unauthorized"}),
                    status_code=403,
                    mimetype="application/json"
                )

            # Confirm and save entity map
            result = confirm_entity_map(
                dd_id=dd_id,
                entity_map=entity_map,
                session=session
            )

            logging.info(f"[DDEntityMapping PATCH] Entity map confirmed: {result.get('confirmed_count', 0)} entities")

            return func.HttpResponse(
                json.dumps({
                    **result,
                    "message": "Entity map confirmed and saved" if result.get("success") else "Failed to save entity map"
                }, default=str),
                status_code=200 if result.get("success") else 500,
                mimetype="application/json"
            )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid dd_id format: {str(e)}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"[DDEntityMapping PATCH] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Entity mapping endpoint.

    GET /api/dd-entity-mapping?dd_id=uuid
        Get stored entity map for a DD project.

    POST /api/dd-entity-mapping
        Run entity mapping for a DD project.
        Body: {
            "dd_id": "uuid",
            "run_id": "uuid" (optional),
            "max_docs": 50 (optional, for testing)
        }

    PUT /api/dd-entity-mapping
        Modify entity map using AI based on user instructions.
        Body: {
            "dd_id": "uuid",
            "instruction": "Remove G. Pietersen - they are just a signatory",
            "current_entity_map": [...] (optional)
        }

    PATCH /api/dd-entity-mapping
        Confirm and save the final entity map.
        Body: {
            "dd_id": "uuid",
            "entity_map": [...]
        }

    Returns: {
        "dd_id": "uuid",
        "status": "completed",
        "entity_map": [
            {
                "entity_name": "ABC Mining (Pty) Ltd",
                "relationship_to_target": "subsidiary",
                "confidence": 0.92,
                "documents_appearing_in": ["doc1.pdf", "doc2.pdf"],
                "requires_human_confirmation": false
            }
        ],
        "summary": {
            "total_unique_entities": 25,
            "entities_needing_confirmation": 3,
            "target_subsidiaries": 5,
            "counterparties": 12
        },
        "checkpoint_recommended": true,
        "checkpoint_reason": "3 entities need confirmation"
    }
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("No matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        # Handle GET request
        if req.method.upper() == "GET":
            return handle_get(req, email)

        # Handle PUT request (AI-assisted modification)
        if req.method.upper() == "PUT":
            return handle_put(req, email)

        # Handle PATCH request (confirm and save)
        if req.method.upper() == "PATCH":
            return handle_patch(req, email)

        # Parse request body for POST
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        dd_id = req_body.get("dd_id")
        run_id = req_body.get("run_id")
        max_docs = req_body.get("max_docs")

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Run entity mapping
        result = run_entity_mapping(dd_id, run_id=run_id, max_docs=max_docs)

        # Check for errors in result
        if "error" in result:
            status_code = 404 if "not found" in result.get("error", "") else 500
            return func.HttpResponse(
                json.dumps(result),
                status_code=status_code,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[DDEntityMapping] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
