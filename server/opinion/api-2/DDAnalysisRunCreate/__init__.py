# File: server/opinion/api-2/DDAnalysisRunCreate/__init__.py
"""
Create a new DD Analysis Run.

Creates a run record with selected document IDs and assigns a sequential run number.
Returns the run details including the generated run_id for starting processing.
"""
import logging
import os
import json
import datetime
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDAnalysisRun, DueDiligence, Document, Folder
from shared.session import transactional_session
from sqlalchemy import func as sql_func


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        data = req.get_json()
        dd_id = data.get("dd_id")
        selected_document_ids = data.get("selected_document_ids", [])

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

        if not selected_document_ids or len(selected_document_ids) == 0:
            return func.HttpResponse(
                json.dumps({"error": "selected_document_ids is required and must not be empty"}),
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

            # Get next run number for this DD
            max_run_number = session.query(sql_func.max(DDAnalysisRun.run_number)).filter(
                DDAnalysisRun.dd_id == dd_uuid
            ).scalar()
            next_run_number = (max_run_number or 0) + 1

            # Generate default name: "Run {n} - {timestamp}"
            timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            default_name = f"Run {next_run_number} - {timestamp}"

            # Create the run record
            run = DDAnalysisRun(
                dd_id=dd_uuid,
                run_number=next_run_number,
                name=default_name,
                status="pending",
                selected_document_ids=selected_document_ids,
                total_documents=len(selected_document_ids),
                documents_processed=0,
                findings_total=0,
                findings_critical=0,
                findings_high=0,
                findings_medium=0,
                findings_low=0,
                estimated_cost_usd=0.0,
                created_at=datetime.datetime.utcnow()
            )
            session.add(run)
            session.commit()

            # Return run details
            return func.HttpResponse(
                json.dumps({
                    "run_id": str(run.id),
                    "dd_id": str(dd_id),
                    "run_number": run.run_number,
                    "name": run.name,
                    "status": run.status,
                    "selected_document_ids": run.selected_document_ids,
                    "total_documents": run.total_documents,
                    "created_at": run.created_at.isoformat()
                }),
                status_code=201,
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
