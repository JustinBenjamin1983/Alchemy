# File: server/opinion/api-2/DDEvalRubricList/__init__.py
"""
List all DD Evaluation Rubrics.

Returns rubrics ordered by created_at descending (most recent first).
"""
import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDEvalRubric
from shared.session import transactional_session
from sqlalchemy import desc


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            # Get all rubrics ordered by created_at desc
            rubrics = session.query(DDEvalRubric).order_by(
                desc(DDEvalRubric.created_at)
            ).all()

            # Build response
            rubrics_data = []
            for rubric in rubrics:
                rubrics_data.append({
                    "id": str(rubric.id),
                    "name": rubric.name,
                    "description": rubric.description,
                    "total_points": rubric.total_points,
                    "dd_id": str(rubric.dd_id) if rubric.dd_id else None,
                    "created_at": rubric.created_at.isoformat() if rubric.created_at else None,
                    "created_by": rubric.created_by,
                    # Include summary counts from rubric_data
                    "summary": _get_rubric_summary(rubric.rubric_data)
                })

            return func.HttpResponse(
                json.dumps({"rubrics": rubrics_data}),
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


def _get_rubric_summary(rubric_data: dict) -> dict:
    """Extract summary counts from rubric data."""
    if not rubric_data:
        return {}

    return {
        "critical_red_flags_count": len(rubric_data.get("critical_red_flags", [])),
        "amber_flags_count": len(rubric_data.get("amber_flags", [])),
        "cross_document_connections_count": len(rubric_data.get("cross_document_connections", [])),
        "missing_documents_count": len(rubric_data.get("missing_documents", []))
    }
