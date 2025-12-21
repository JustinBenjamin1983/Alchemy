# DDOrganisationProgress/__init__.py
"""
Organisation Progress Endpoint

Returns the current classification/organisation progress for a DD project.
Frontend polls this endpoint every 2-3 seconds during the organising phase.

This is Phase 1 of the Document Organisation feature.
"""
import logging
import os
import json
import azure.functions as func

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence, DDOrganisationStatus

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get organisation/classification progress for a DD project.

    GET /api/dd-organisation-progress?dd_id=uuid

    Returns: {
        "dd_id": "uuid",
        "status": "pending|classifying|organising|completed|failed",
        "total_documents": 45,
        "classified_count": 23,
        "low_confidence_count": 3,
        "failed_count": 2,
        "percent_complete": 51,
        "category_counts": {"01_Corporate": 10, "02_Commercial": 5, ...},
        "error_message": null,
        "started_at": "2024-01-15T10:30:00Z",
        "completed_at": null
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

        # Get dd_id from query params
        dd_id = req.params.get("dd_id")

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id query parameter is required"}),
                status_code=400,
                mimetype="application/json"
            )

        with transactional_session() as session:
            # Verify DD exists
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get organisation status
            org_status = session.query(DDOrganisationStatus).filter(
                DDOrganisationStatus.dd_id == dd_id
            ).first()

            if org_status:
                # Calculate percent complete
                percent_complete = 0
                if org_status.total_documents > 0:
                    percent_complete = int(
                        (org_status.classified_count / org_status.total_documents) * 100
                    )

                response = {
                    "dd_id": str(dd_id),
                    "status": org_status.status,
                    "total_documents": org_status.total_documents,
                    "classified_count": org_status.classified_count,
                    "low_confidence_count": org_status.low_confidence_count,
                    "failed_count": org_status.failed_count,
                    "percent_complete": percent_complete,
                    "category_counts": org_status.category_counts or {},
                    "error_message": org_status.error_message,
                    "started_at": org_status.started_at.isoformat() if org_status.started_at else None,
                    "completed_at": org_status.completed_at.isoformat() if org_status.completed_at else None,
                    "updated_at": org_status.updated_at.isoformat() if org_status.updated_at else None
                }
            else:
                # No status record exists - check if there are documents that need classification
                folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
                folder_ids = [f.id for f in folders]

                if not folder_ids:
                    # No folders yet - DD just created
                    response = {
                        "dd_id": str(dd_id),
                        "status": "pending",
                        "total_documents": 0,
                        "classified_count": 0,
                        "low_confidence_count": 0,
                        "failed_count": 0,
                        "percent_complete": 0,
                        "category_counts": {},
                        "error_message": None,
                        "started_at": None,
                        "completed_at": None,
                        "updated_at": None
                    }
                else:
                    # Count documents and their classification status
                    docs = (
                        session.query(Document)
                        .filter(
                            Document.folder_id.in_(folder_ids),
                            Document.is_original == False
                        )
                        .all()
                    )

                    total = len(docs)
                    classified = sum(1 for d in docs if d.classification_status == "classified")
                    pending = sum(1 for d in docs if d.classification_status == "pending")
                    failed = sum(1 for d in docs if d.classification_status == "failed")
                    low_conf = sum(1 for d in docs if d.ai_confidence and d.ai_confidence < 70)

                    # Determine status based on document states
                    if total == 0:
                        status = "pending"
                    elif pending == total:
                        status = "pending"
                    elif classified == total:
                        status = "completed"
                    elif pending > 0:
                        status = "pending"  # Still has pending docs, hasn't started
                    else:
                        status = "completed"

                    # Count by category
                    category_counts = {}
                    for doc in docs:
                        if doc.ai_category:
                            category_counts[doc.ai_category] = category_counts.get(doc.ai_category, 0) + 1

                    percent_complete = int((classified / total) * 100) if total > 0 else 0

                    response = {
                        "dd_id": str(dd_id),
                        "status": status,
                        "total_documents": total,
                        "classified_count": classified,
                        "low_confidence_count": low_conf,
                        "failed_count": failed,
                        "percent_complete": percent_complete,
                        "category_counts": category_counts,
                        "error_message": None,
                        "started_at": None,
                        "completed_at": None,
                        "updated_at": None
                    }

            return func.HttpResponse(
                json.dumps(response),
                status_code=200,
                mimetype="application/json"
            )

    except Exception as e:
        logging.error(f"[DDOrganisationProgress] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
