# DDDocumentReassign/__init__.py
"""
Document Category Reassignment Endpoint

Allows users to manually reassign a document's AI category during the
organisation review phase (before folders are created).

This updates the document's ai_category field and marks it as manually assigned.
"""
import logging
import os
import json
import datetime
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence, DDOrganisationStatus

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Reassign a document to a different category.

    POST /api/dd-document-reassign
    Body: {
        "dd_id": "uuid",
        "document_id": "uuid",
        "target_category": "01_Corporate",
        "reason": "optional reason for manual assignment"
    }

    Returns: {
        "success": true,
        "document_id": "uuid",
        "document_name": "example.pdf",
        "from_category": "02_Commercial",
        "to_category": "01_Corporate"
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
        document_id = req_body.get("document_id")
        target_category = req_body.get("target_category")
        reason = req_body.get("reason", "Manual reassignment")

        if not dd_id or not document_id or not target_category:
            return func.HttpResponse(
                json.dumps({"error": "dd_id, document_id, and target_category are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"[DDDocumentReassign] Reassigning document {document_id} to {target_category}")

        with transactional_session() as session:
            # Verify DD exists
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get document
            doc = session.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return func.HttpResponse(
                    json.dumps({"error": f"Document {document_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Store original category
            from_category = doc.ai_category or "Unclassified"

            # Update document category
            doc.ai_category = target_category
            doc.category_source = "manual"
            doc.classification_status = "classified"

            session.commit()

            # Update organisation status category counts
            org_status = session.query(DDOrganisationStatus).filter(
                DDOrganisationStatus.dd_id == dd_id
            ).first()

            if org_status and org_status.category_counts:
                counts = dict(org_status.category_counts)

                # Decrement old category count
                if from_category in counts:
                    counts[from_category] = max(0, counts[from_category] - 1)

                # Increment new category count
                counts[target_category] = counts.get(target_category, 0) + 1

                org_status.category_counts = counts
                session.commit()

            logging.info(f"[DDDocumentReassign] Moved {doc.original_file_name}: {from_category} -> {target_category}")

            response = {
                "success": True,
                "document_id": str(document_id),
                "document_name": doc.original_file_name,
                "from_category": from_category,
                "to_category": target_category,
                "reason": reason
            }

            return func.HttpResponse(
                json.dumps(response),
                status_code=200,
                mimetype="application/json"
            )

    except Exception as e:
        logging.error(f"[DDDocumentReassign] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
