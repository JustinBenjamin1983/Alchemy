# File: server/opinion/api-2/DDEvalRubricCreate/__init__.py
"""
Create a new DD Evaluation Rubric.

Accepts rubric data as JSON and validates the structure.
"""
import logging
import os
import json
import datetime
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
        data = req.get_json()
        name = data.get("name")
        description = data.get("description")
        rubric_data = data.get("rubric_data")
        total_points = data.get("total_points", 200)
        dd_id = data.get("dd_id")

        if not name:
            return func.HttpResponse(
                json.dumps({"error": "name is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not rubric_data:
            return func.HttpResponse(
                json.dumps({"error": "rubric_data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate rubric_data structure
        validation_error = _validate_rubric_data(rubric_data)
        if validation_error:
            return func.HttpResponse(
                json.dumps({"error": validation_error}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert dd_id to UUID if provided
        dd_uuid = None
        if dd_id:
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
            # Verify DD exists if dd_id provided
            if dd_uuid:
                dd = session.query(DueDiligence).filter(
                    DueDiligence.id == dd_uuid
                ).first()
                if not dd:
                    return func.HttpResponse(
                        json.dumps({"error": "Due diligence not found"}),
                        status_code=404,
                        mimetype="application/json"
                    )

            # Calculate total points from rubric_data if not provided
            if total_points == 200:  # Default value, calculate from data
                total_points = _calculate_total_points(rubric_data)

            # Create the rubric
            rubric = DDEvalRubric(
                name=name,
                description=description,
                rubric_data=rubric_data,
                total_points=total_points,
                dd_id=dd_uuid,
                created_at=datetime.datetime.utcnow(),
                created_by=email
            )
            session.add(rubric)
            session.flush()

            rubric_id = str(rubric.id)

            session.commit()

            logging.info(f"[DDEvalRubricCreate] Created rubric: {rubric_id}")

            return func.HttpResponse(
                json.dumps({
                    "id": rubric_id,
                    "name": name,
                    "description": description,
                    "total_points": total_points,
                    "dd_id": str(dd_uuid) if dd_uuid else None,
                    "created_at": rubric.created_at.isoformat(),
                    "created_by": email
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


def _validate_rubric_data(rubric_data: dict) -> str | None:
    """
    Validate rubric data structure.
    Returns error message if invalid, None if valid.
    """
    if not isinstance(rubric_data, dict):
        return "rubric_data must be an object"

    # Check for at least one category
    categories = [
        "critical_red_flags",
        "amber_flags",
        "cross_document_connections",
        "intelligent_questions",
        "missing_documents",
        "overall_quality"
    ]

    has_category = any(rubric_data.get(cat) for cat in categories)
    if not has_category:
        return "rubric_data must contain at least one category"

    # Validate critical_red_flags if present
    if "critical_red_flags" in rubric_data:
        if not isinstance(rubric_data["critical_red_flags"], list):
            return "critical_red_flags must be an array"
        for i, flag in enumerate(rubric_data["critical_red_flags"]):
            if not isinstance(flag, dict):
                return f"critical_red_flags[{i}] must be an object"
            if "name" not in flag:
                return f"critical_red_flags[{i}] must have a name"

    # Validate amber_flags if present
    if "amber_flags" in rubric_data:
        if not isinstance(rubric_data["amber_flags"], list):
            return "amber_flags must be an array"
        for i, flag in enumerate(rubric_data["amber_flags"]):
            if not isinstance(flag, dict):
                return f"amber_flags[{i}] must be an object"
            if "name" not in flag:
                return f"amber_flags[{i}] must have a name"

    # Validate cross_document_connections if present
    if "cross_document_connections" in rubric_data:
        if not isinstance(rubric_data["cross_document_connections"], list):
            return "cross_document_connections must be an array"

    # Validate missing_documents if present
    if "missing_documents" in rubric_data:
        if not isinstance(rubric_data["missing_documents"], list):
            return "missing_documents must be an array"

    return None


def _calculate_total_points(rubric_data: dict) -> int:
    """Calculate total points from rubric data."""
    total = 0

    # Critical red flags: default 10 points each
    critical_flags = rubric_data.get("critical_red_flags", [])
    for flag in critical_flags:
        total += flag.get("points", 10)

    # Amber flags: default 5 points each
    amber_flags = rubric_data.get("amber_flags", [])
    for flag in amber_flags:
        total += flag.get("points", 5)

    # Cross-document connections: default 5 points each
    cross_doc = rubric_data.get("cross_document_connections", [])
    for conn in cross_doc:
        total += conn.get("points", 5)

    # Intelligent questions: default 15 points
    if "intelligent_questions" in rubric_data:
        iq = rubric_data["intelligent_questions"]
        total += iq.get("points", 15) if isinstance(iq, dict) else 15

    # Missing documents: default 1 point each
    missing_docs = rubric_data.get("missing_documents", [])
    for doc in missing_docs:
        total += doc.get("points", 1)

    # Overall quality: default 5 points
    if "overall_quality" in rubric_data:
        oq = rubric_data["overall_quality"]
        total += oq.get("points", 5) if isinstance(oq, dict) else 5

    return total if total > 0 else 200
