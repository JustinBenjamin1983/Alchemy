# File: server/opinion/api-2/DDAnalysisRunDelete/__init__.py
"""
Delete an Analysis Run.

Deletes the run and all associated findings (via CASCADE).
Cannot delete a run that is currently processing.
"""
import logging
import os
import json
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDAnalysisRun, DDProcessingCheckpoint
from shared.session import transactional_session


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        data = req.get_json()
        run_id = data.get("run_id")

        if not run_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert to UUID object for database operations
        try:
            run_uuid = uuid_module.UUID(run_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid run_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            # Find the run
            run = session.query(DDAnalysisRun).filter(DDAnalysisRun.id == run_uuid).first()
            if not run:
                return func.HttpResponse(
                    json.dumps({"error": "Run not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Cannot delete if processing
            if run.status == "processing":
                return func.HttpResponse(
                    json.dumps({"error": "Cannot delete a run that is currently processing"}),
                    status_code=409,
                    mimetype="application/json"
                )

            # Delete associated checkpoint if exists
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_uuid
            ).first()
            if checkpoint:
                session.delete(checkpoint)

            # Store info before deletion
            run_name = run.name
            dd_id = str(run.dd_id)

            # Delete the run (findings will cascade delete)
            session.delete(run)
            session.commit()

            return func.HttpResponse(
                json.dumps({
                    "message": f"Run '{run_name}' deleted successfully",
                    "dd_id": dd_id
                }),
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
