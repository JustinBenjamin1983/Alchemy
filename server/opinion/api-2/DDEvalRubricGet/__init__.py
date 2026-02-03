# File: server/opinion/api-2/DDEvalRubricGet/__init__.py
"""
Get a single DD Evaluation Rubric by ID.

Returns the full rubric details including all expected findings.
"""
import logging
import os
import json
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDEvalRubric, DueDiligence
from shared.session import transactional_session


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        rubric_id = req.params.get("rubric_id")

        if not rubric_id:
            return func.HttpResponse(
                json.dumps({"error": "rubric_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert to UUID object for database operations
        try:
            rubric_uuid = uuid_module.UUID(rubric_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid rubric_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            rubric = session.query(DDEvalRubric).filter(
                DDEvalRubric.id == rubric_uuid
            ).first()

            if not rubric:
                return func.HttpResponse(
                    json.dumps({"error": "Rubric not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get linked DD name if exists
            dd_name = None
            if rubric.dd_id:
                dd = session.query(DueDiligence).filter(
                    DueDiligence.id == rubric.dd_id
                ).first()
                if dd:
                    dd_name = dd.name

            return func.HttpResponse(
                json.dumps({
                    "id": str(rubric.id),
                    "name": rubric.name,
                    "description": rubric.description,
                    "rubric_data": rubric.rubric_data,
                    "total_points": rubric.total_points,
                    "dd_id": str(rubric.dd_id) if rubric.dd_id else None,
                    "dd_name": dd_name,
                    "created_at": rubric.created_at.isoformat() if rubric.created_at else None,
                    "created_by": rubric.created_by
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
