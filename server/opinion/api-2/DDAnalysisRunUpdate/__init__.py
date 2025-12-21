# File: server/opinion/api-2/DDAnalysisRunUpdate/__init__.py
"""
Update an Analysis Run (rename).

Allows editing the run name after creation.
"""
import logging
import os
import json
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDAnalysisRun
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
        name = data.get("name")

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

        if not name or len(name.strip()) == 0:
            return func.HttpResponse(
                json.dumps({"error": "name is required and cannot be empty"}),
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

            # Update the name
            run.name = name.strip()
            session.commit()

            return func.HttpResponse(
                json.dumps({
                    "run_id": str(run.id),
                    "name": run.name,
                    "message": "Run renamed successfully"
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
