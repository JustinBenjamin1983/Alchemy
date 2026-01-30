# dd_progress/__init__.py
"""
DD Progress Endpoint

Returns document processing progress for a DD project.
Uses smart document selection to count only processable documents
(avoiding duplicates between originals and converted versions).
"""
import json
import uuid
import azure.functions as func
from shared.session import transactional_session
from shared.models import Document, Folder
from shared.document_selector import get_processable_documents


def main(req: func.HttpRequest) -> func.HttpResponse:
    dd_id = req.route_params.get("dd_id")
    if not dd_id:
        return func.HttpResponse("Missing dd_id", status_code=400)

    dd_id = uuid.UUID(dd_id)

    with transactional_session() as session:
        # Get folders for this DD
        folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
        folder_ids = [str(f.id) for f in folders]

        if not folder_ids:
            return func.HttpResponse(
                json.dumps({
                    "total": 0,
                    "complete": 0,
                    "unsupported": 0,
                    "in_progress": 0,
                    "percent": 0
                }),
                mimetype="application/json",
                status_code=200
            )

        # Use smart document selection to get actual processable documents
        # This avoids counting both original AND converted versions
        processable_docs = get_processable_documents(session, folder_ids)

        total_docs = len(processable_docs)
        complete = sum(1 for doc in processable_docs if doc.processing_status == "Complete")
        unsupported = sum(1 for doc in processable_docs if doc.processing_status == "Unsupported")

    in_progress = total_docs - complete - unsupported
    pct = round(100 * complete / total_docs, 1) if total_docs else 0

    return func.HttpResponse(
        json.dumps({
            "total": total_docs,
            "complete": complete,
            "unsupported": unsupported,
            "in_progress": in_progress,
            "percent": pct
        }),
        mimetype="application/json",
        status_code=200
    )
