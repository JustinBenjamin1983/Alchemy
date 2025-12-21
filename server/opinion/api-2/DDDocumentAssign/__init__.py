# DDDocumentAssign/__init__.py
"""
Manual Document Assignment Endpoint

Allows users to manually reassign documents to different blueprint folders.
This is used during the organisation review phase when the user wants to
override the AI-assigned folder category.

Phase 2 of the Document Organisation feature.
"""
import logging
import os
import json
import datetime
import uuid as uuid_module
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manually assign a document to a different folder.

    POST /api/dd-document-assign
    Body: {
        "dd_id": "uuid",
        "document_id": "uuid",
        "target_folder_id": "uuid",
        "reason": "optional reason for manual assignment"
    }

    For bulk assignment:
    Body: {
        "dd_id": "uuid",
        "assignments": [
            {"document_id": "uuid1", "target_folder_id": "uuid"},
            {"document_id": "uuid2", "target_folder_id": "uuid"}
        ],
        "reason": "optional reason for manual assignment"
    }

    Returns: {
        "success": true,
        "assigned_count": 1,
        "assignments": [
            {
                "document_id": "uuid",
                "document_name": "example.pdf",
                "from_folder": "02_Commercial",
                "to_folder": "01_Corporate",
                "previous_source": "ai",
                "new_source": "manual"
            }
        ]
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

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Handle single assignment or bulk assignments
        assignments = req_body.get("assignments")
        if not assignments:
            # Single assignment
            document_id = req_body.get("document_id")
            target_folder_id = req_body.get("target_folder_id")

            if not document_id or not target_folder_id:
                return func.HttpResponse(
                    json.dumps({"error": "document_id and target_folder_id are required"}),
                    status_code=400,
                    mimetype="application/json"
                )

            assignments = [{"document_id": document_id, "target_folder_id": target_folder_id}]

        reason = req_body.get("reason", "Manual reassignment")

        logging.info(f"[DDDocumentAssign] Processing {len(assignments)} assignment(s) for DD: {dd_id}")

        results = []

        with transactional_session() as session:
            # Verify DD exists
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

            # Process each assignment
            for assignment in assignments:
                doc_id = assignment.get("document_id")
                target_folder_id = assignment.get("target_folder_id")

                if not doc_id or not target_folder_id:
                    logging.warning(f"Skipping invalid assignment: {assignment}")
                    continue

                # Get document
                doc = session.query(Document).filter(Document.id == doc_id).first()
                if not doc:
                    logging.warning(f"Document {doc_id} not found")
                    results.append({
                        "document_id": doc_id,
                        "error": "Document not found"
                    })
                    continue

                # Get target folder
                target_folder = session.query(Folder).filter(
                    Folder.id == target_folder_id,
                    Folder.dd_id == dd_uuid
                ).first()

                if not target_folder:
                    logging.warning(f"Target folder {target_folder_id} not found")
                    results.append({
                        "document_id": doc_id,
                        "document_name": doc.original_file_name,
                        "error": "Target folder not found"
                    })
                    continue

                # Get current folder for logging
                current_folder = session.query(Folder).filter(Folder.id == doc.folder_id).first()
                from_folder_name = current_folder.folder_category or current_folder.folder_name if current_folder else "Unknown"
                to_folder_name = target_folder.folder_category or target_folder.folder_name

                previous_source = doc.folder_assignment_source

                # Store original folder if not already set (first move from ZIP location)
                if doc.original_folder_id is None:
                    doc.original_folder_id = doc.folder_id

                # Move document to target folder
                doc.folder_id = target_folder.id
                doc.folder_assignment_source = "manual"

                # Update document counts on both folders
                if current_folder and current_folder.document_count is not None:
                    current_folder.document_count = max(0, current_folder.document_count - 1)

                if target_folder.document_count is not None:
                    target_folder.document_count += 1
                else:
                    target_folder.document_count = 1

                results.append({
                    "document_id": str(doc_id),
                    "document_name": doc.original_file_name,
                    "from_folder": from_folder_name,
                    "to_folder": to_folder_name,
                    "previous_source": previous_source,
                    "new_source": "manual"
                })

                logging.info(f"[DDDocumentAssign] Moved {doc.original_file_name}: {from_folder_name} -> {to_folder_name}")

            session.commit()

        successful_count = len([r for r in results if "error" not in r])

        response = {
            "success": True,
            "assigned_count": successful_count,
            "total_requested": len(assignments),
            "assignments": results,
            "reason": reason
        }

        logging.info(f"[DDDocumentAssign] Completed: {successful_count}/{len(assignments)} assignments")

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[DDDocumentAssign] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
