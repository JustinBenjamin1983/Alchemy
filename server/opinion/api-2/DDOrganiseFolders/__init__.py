# DDOrganiseFolders/__init__.py
"""
Blueprint Folder Organisation Endpoint

Creates standardised blueprint folders and moves documents into them based on
AI classification results from Phase 1.

Phase 2 of the Document Organisation feature:
1. Loads folder_structure from blueprint YAML based on transaction_type
2. Creates blueprint folders (01_Corporate through 99_Needs_Review)
3. Moves documents to appropriate folders based on ai_category
4. Documents with low confidence (< 70%) go to 99_Needs_Review
5. Preserves original_folder_id for audit trail
6. Updates organisation status to 'organised'
"""
import logging
import os
import json
import datetime
import uuid as uuid_module
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence, DDOrganisationStatus
from shared.audit import log_audit_event, AuditEventType

# Import folder structure helpers
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from dd_enhanced.config.blueprints.folder_loader import (
    load_folder_structure,
    get_folder_for_category,
    get_all_folder_categories,
    extract_sort_order,
    CONFIDENCE_THRESHOLD
)

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def create_blueprint_folders(session, dd_id: str, transaction_type: str) -> dict:
    """
    Create blueprint folders for a DD project based on transaction type.

    Returns dict mapping folder_category to folder_id.
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    # Load folder structure from blueprint
    folder_structure = load_folder_structure(transaction_type)

    folder_map = {}  # category -> folder_id

    for folder_category, config in folder_structure.items():
        # Check if blueprint folder already exists
        existing = session.query(Folder).filter(
            Folder.dd_id == dd_uuid,
            Folder.folder_category == folder_category,
            Folder.is_blueprint_folder == True
        ).first()

        if existing:
            folder_map[folder_category] = existing.id
            logging.info(f"Blueprint folder {folder_category} already exists")
            continue

        # Create new blueprint folder
        folder_name = folder_category.replace("_", " ")  # e.g., "01 Corporate"
        sort_order = extract_sort_order(folder_category)

        new_folder = Folder(
            id=uuid_module.uuid4(),
            dd_id=dd_uuid,
            folder_name=folder_name,
            is_root=True,  # Blueprint folders are at root level
            path=folder_name,
            folder_category=folder_category,
            is_blueprint_folder=True,
            expected_doc_types=config.get("expected_documents", []),
            sort_order=sort_order,
            relevance=config.get("relevance", "medium"),
            document_count=0
        )

        session.add(new_folder)
        folder_map[folder_category] = new_folder.id

        logging.info(f"Created blueprint folder: {folder_category} (relevance: {config.get('relevance', 'medium')})")

    session.commit()
    return folder_map


def organise_documents(session, dd_id: str, folder_map: dict) -> dict:
    """
    Move documents to their appropriate blueprint folders based on AI classification.

    Returns summary of the organisation process.
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    # Get all non-blueprint folders for this DD
    original_folders = session.query(Folder).filter(
        Folder.dd_id == dd_uuid,
        Folder.is_blueprint_folder == False
    ).all()

    original_folder_ids = [f.id for f in original_folders]

    # Get all documents in original folders that have been classified
    documents = session.query(Document).filter(
        Document.folder_id.in_(original_folder_ids),
        Document.is_original == False,
        Document.classification_status == "classified"
    ).all()

    summary = {
        "total_documents": len(documents),
        "moved_count": 0,
        "needs_review_count": 0,
        "skipped_count": 0,
        "category_distribution": {cat: 0 for cat in get_all_folder_categories()}
    }

    for doc in documents:
        # Store original folder if not already set
        if doc.original_folder_id is None:
            doc.original_folder_id = doc.folder_id

        # Determine target folder based on AI classification
        target_category = get_folder_for_category(
            doc.ai_category,
            doc.ai_confidence,
            CONFIDENCE_THRESHOLD
        )

        target_folder_id = folder_map.get(target_category)

        if not target_folder_id:
            logging.warning(f"No folder found for category {target_category}, using 99_Needs_Review")
            target_folder_id = folder_map.get("99_Needs_Review")
            target_category = "99_Needs_Review"

        if target_folder_id:
            # Move document to target folder
            original_folder_id = str(doc.folder_id) if doc.folder_id else None
            doc.folder_id = target_folder_id
            doc.folder_assignment_source = "ai"

            summary["moved_count"] += 1
            summary["category_distribution"][target_category] += 1

            if target_category == "99_Needs_Review":
                summary["needs_review_count"] += 1

            logging.debug(f"Moved {doc.original_file_name} -> {target_category}")

            # Log audit event for document move
            try:
                log_audit_event(
                    session=session,
                    event_type=AuditEventType.DOCUMENT_MOVED,
                    entity_type="document",
                    entity_id=str(doc.id),
                    dd_id=dd_id,
                    details={
                        "filename": doc.original_file_name,
                        "from_folder_id": original_folder_id,
                        "to_folder_category": target_category
                    }
                )
            except Exception as audit_err:
                logging.warning(f"[DDOrganiseFolders] Audit logging failed: {audit_err}")
        else:
            summary["skipped_count"] += 1
            logging.warning(f"Could not find target folder for {doc.original_file_name}")

    session.commit()

    # Update document counts for each blueprint folder
    for folder_category, folder_id in folder_map.items():
        count = session.query(Document).filter(
            Document.folder_id == folder_id,
            Document.is_original == False
        ).count()

        folder = session.query(Folder).filter(Folder.id == folder_id).first()
        if folder:
            folder.document_count = count

    session.commit()

    return summary


def update_organisation_status(session, dd_id: str, status: str, summary: dict = None,
                                error_message: str = None):
    """Update the organisation status for a DD project."""
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    org_status = session.query(DDOrganisationStatus).filter(
        DDOrganisationStatus.dd_id == dd_uuid
    ).first()

    if org_status:
        org_status.status = status
        org_status.updated_at = datetime.datetime.utcnow()

        if status == "organised":
            org_status.organised_at = datetime.datetime.utcnow()
            if summary:
                org_status.organised_count = summary.get("moved_count", 0)
                org_status.needs_review_count = summary.get("needs_review_count", 0)
                org_status.category_counts = summary.get("category_distribution", {})

        if error_message:
            org_status.error_message = error_message

        session.commit()


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create blueprint folders and organise documents into them.

    POST /api/dd-organise-folders
    Body: {
        "dd_id": "uuid",
        "transaction_type": "mining_resources"  # optional, uses DD's transaction_type if not provided
    }

    Returns: {
        "dd_id": "uuid",
        "status": "organised",
        "transaction_type": "mining_resources",
        "folders_created": ["01_Corporate", "02_Commercial", ...],
        "summary": {
            "total_documents": 45,
            "moved_count": 43,
            "needs_review_count": 5,
            "skipped_count": 2,
            "category_distribution": {"01_Corporate": 10, "02_Commercial": 8, ...}
        }
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
        transaction_type = req_body.get("transaction_type")

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"[DDOrganiseFolders] Starting folder organisation for DD: {dd_id}")

        with transactional_session() as session:
            # Verify DD exists and get transaction type if not provided
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Use DD's transaction type if not provided in request
            if not transaction_type:
                transaction_type = dd.transaction_type or "ma_corporate"

            logging.info(f"[DDOrganiseFolders] Using transaction type: {transaction_type}")

            # Check current organisation status
            org_status = session.query(DDOrganisationStatus).filter(
                DDOrganisationStatus.dd_id == dd_id
            ).first()

            if org_status and org_status.status == "organised":
                return func.HttpResponse(
                    json.dumps({
                        "dd_id": str(dd_id),
                        "status": "already_organised",
                        "message": "Documents have already been organised. Use DDDocumentAssign for manual changes."
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            # Update status to organising
            update_organisation_status(session, dd_id, "organising")

            try:
                # Step 1: Create blueprint folders
                logging.info("[DDOrganiseFolders] Creating blueprint folders...")
                folder_map = create_blueprint_folders(session, dd_id, transaction_type)

                folders_created = list(folder_map.keys())
                logging.info(f"[DDOrganiseFolders] Created/verified {len(folders_created)} blueprint folders")

                # Step 2: Organise documents into folders
                logging.info("[DDOrganiseFolders] Organising documents into folders...")
                summary = organise_documents(session, dd_id, folder_map)

                # Step 3: Update status to organised
                update_organisation_status(session, dd_id, "organised", summary)

                response = {
                    "dd_id": str(dd_id),
                    "status": "organised",
                    "transaction_type": transaction_type,
                    "folders_created": folders_created,
                    "summary": summary
                }

                logging.info(f"[DDOrganiseFolders] Completed: {summary['moved_count']}/{summary['total_documents']} documents organised")

                return func.HttpResponse(
                    json.dumps(response),
                    status_code=200,
                    mimetype="application/json"
                )

            except Exception as e:
                logging.error(f"[DDOrganiseFolders] Organisation failed: {e}")
                update_organisation_status(session, dd_id, "failed", error_message=str(e)[:500])
                raise

    except Exception as e:
        logging.error(f"[DDOrganiseFolders] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
