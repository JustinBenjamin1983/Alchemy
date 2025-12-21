# File: server/opinion/api-2/DDAnalysisRunList/__init__.py
"""
List all Analysis Runs for a DD.

Returns runs ordered by created_at descending (most recent first).
Includes document names for each run.
"""
import logging
import os
import json
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDAnalysisRun, DueDiligence, Document, Folder
from shared.session import transactional_session
from sqlalchemy import desc


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        dd_id = req.params.get("dd_id")

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert to UUID object for database operations
        try:
            dd_uuid = uuid_module.UUID(dd_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid dd_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            # Verify DD exists
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": "Due diligence not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get all runs for this DD, ordered by created_at desc
            runs = session.query(DDAnalysisRun).filter(
                DDAnalysisRun.dd_id == dd_uuid
            ).order_by(desc(DDAnalysisRun.created_at)).all()

            # Get all documents for this DD to map IDs to names
            folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
            folder_ids = [f.id for f in folders]

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all() if folder_ids else []

            doc_lookup = {str(d.id): d.original_file_name for d in documents}

            # Build response
            runs_data = []
            for run in runs:
                # Get document names for this run
                doc_names = []
                for doc_id in (run.selected_document_ids or []):
                    doc_name = doc_lookup.get(doc_id, "Unknown Document")
                    doc_names.append({"id": doc_id, "name": doc_name})

                runs_data.append({
                    "run_id": str(run.id),
                    "dd_id": str(run.dd_id),
                    "run_number": run.run_number,
                    "name": run.name,
                    "status": run.status,
                    "selected_documents": doc_names,
                    "total_documents": run.total_documents,
                    "documents_processed": run.documents_processed,
                    "findings_total": run.findings_total,
                    "findings_critical": run.findings_critical,
                    "findings_high": run.findings_high,
                    "findings_medium": run.findings_medium,
                    "findings_low": run.findings_low,
                    "estimated_cost_usd": run.estimated_cost_usd,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "last_error": run.last_error,
                    "synthesis_data": run.synthesis_data if hasattr(run, 'synthesis_data') else None
                })

            return func.HttpResponse(
                json.dumps({"runs": runs_data}),
                status_code=200,
                mimetype="application/json"
            )

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
