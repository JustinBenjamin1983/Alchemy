# dd_progress/__init__.py  (new Function)
import json, uuid
import azure.functions as func
from shared.session import transactional_session
from shared.models import Document

def main(req: func.HttpRequest) -> func.HttpResponse:
    dd_id = req.route_params.get("dd_id")
    if not dd_id:
        return func.HttpResponse("Missing dd_id", status_code=400)

    dd_id = uuid.UUID(dd_id)

    with transactional_session() as session:
        total_docs = session.query(Document)\
            .filter(Document.folder.has(dd_id=dd_id),
                    Document.is_original == False).count()

        complete = session.query(Document)\
            .filter(Document.folder.has(dd_id=dd_id),
                    Document.processing_status == "Complete").count()

        unsupported = session.query(Document)\
            .filter(Document.folder.has(dd_id=dd_id),
                    Document.processing_status == "Unsupported").count()

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
