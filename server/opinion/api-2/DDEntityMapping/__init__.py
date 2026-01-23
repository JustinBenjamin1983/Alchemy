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
from shared.models import Document, Folder, DueDiligence, DDWizardDraft, DDEntityMap, DDAnalysisRun

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

        # Get target entity information from wizard draft
        draft = session.query(DDWizardDraft).filter(
            DDWizardDraft.owned_by == dd.owned_by,
            DDWizardDraft.transaction_name == dd.name
        ).first()

        target_entity = {
            "name": dd.name,
            "registration_number": None,
            "expected_counterparties": []
        }

        if draft:
            target_entity["name"] = draft.target_entity_name or dd.name
            if hasattr(draft, 'target_registration_number'):
                target_entity["registration_number"] = draft.target_registration_number
            if hasattr(draft, 'expected_counterparties'):
                target_entity["expected_counterparties"] = draft.expected_counterparties or []

        # Load known entities from wizard (subsidiaries, holding company)
        known_entities = []
        if draft:
            if hasattr(draft, 'known_subsidiaries') and draft.known_subsidiaries:
                for sub in draft.known_subsidiaries:
                    known_entities.append({
                        "entity_name": sub.get("name", ""),
                        "relationship_to_target": sub.get("relationship", "subsidiary")
                    })
            if hasattr(draft, 'holding_company') and draft.holding_company:
                known_entities.append({
                    "entity_name": draft.holding_company.get("name", ""),
                    "relationship_to_target": "parent"
                })

        # Get all classified documents
        folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
        folder_ids = [f.id for f in folders]

        documents = (
            session.query(Document)
            .filter(
                Document.folder_id.in_(folder_ids),
                Document.classification_status == "classified",
                Document.is_original == False
            )
            .all()
        )

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
                "checkpoint_recommended": False
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
            "cost": cost_summary
        }

        logging.info(f"[DDEntityMapping] Completed: {summary.get('total_unique_entities', 0)} entities, "
                     f"{summary.get('entities_needing_confirmation', 0)} need confirmation")

        return response


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Run entity mapping for a DD project.

    POST /api/dd-entity-mapping
    Body: {
        "dd_id": "uuid",
        "run_id": "uuid" (optional),
        "max_docs": 50 (optional, for testing)
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

        # Parse request body
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
