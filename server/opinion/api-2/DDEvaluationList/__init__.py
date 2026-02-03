# File: server/opinion/api-2/DDEvaluationList/__init__.py
"""
List DD Evaluations with optional filters.

Supports filtering by dd_id, rubric_id, run_id, and status.
Returns evaluations ordered by created_at descending.
"""
import logging
import os
import json
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDEvaluation, DDEvalRubric, DDAnalysisRun, DueDiligence
from shared.session import transactional_session
from sqlalchemy import desc


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        # Optional filters
        dd_id = req.params.get("dd_id")
        rubric_id = req.params.get("rubric_id")
        run_id = req.params.get("run_id")
        status = req.params.get("status")

        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            # Build query
            query = session.query(DDEvaluation)

            # Apply filters
            if rubric_id:
                try:
                    rubric_uuid = uuid_module.UUID(rubric_id)
                    query = query.filter(DDEvaluation.rubric_id == rubric_uuid)
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid rubric_id format"}),
                        status_code=400,
                        mimetype="application/json"
                    )

            if run_id:
                try:
                    run_uuid = uuid_module.UUID(run_id)
                    query = query.filter(DDEvaluation.run_id == run_uuid)
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid run_id format"}),
                        status_code=400,
                        mimetype="application/json"
                    )

            if dd_id:
                try:
                    dd_uuid = uuid_module.UUID(dd_id)
                    # Filter by DD through the run relationship
                    query = query.join(DDAnalysisRun).filter(
                        DDAnalysisRun.dd_id == dd_uuid
                    )
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid dd_id format"}),
                        status_code=400,
                        mimetype="application/json"
                    )

            if status:
                valid_statuses = ["pending", "evaluating", "completed", "failed"]
                if status not in valid_statuses:
                    return func.HttpResponse(
                        json.dumps({"error": f"Invalid status. Must be one of: {valid_statuses}"}),
                        status_code=400,
                        mimetype="application/json"
                    )
                query = query.filter(DDEvaluation.status == status)

            # Order by created_at desc
            evaluations = query.order_by(desc(DDEvaluation.created_at)).all()

            # Build response with related data
            evaluations_data = []
            for evaluation in evaluations:
                # Get rubric name
                rubric = session.query(DDEvalRubric).filter(
                    DDEvalRubric.id == evaluation.rubric_id
                ).first()

                # Get run info
                run = session.query(DDAnalysisRun).filter(
                    DDAnalysisRun.id == evaluation.run_id
                ).first()

                dd_name = None
                if run:
                    dd = session.query(DueDiligence).filter(
                        DueDiligence.id == run.dd_id
                    ).first()
                    if dd:
                        dd_name = dd.name

                evaluations_data.append({
                    "id": str(evaluation.id),
                    "rubric_id": str(evaluation.rubric_id),
                    "rubric_name": rubric.name if rubric else None,
                    "run_id": str(evaluation.run_id),
                    "run_name": run.name if run else None,
                    "dd_id": str(run.dd_id) if run else None,
                    "dd_name": dd_name,
                    "status": evaluation.status,
                    "total_score": evaluation.total_score,
                    "percentage": evaluation.percentage,
                    "performance_band": evaluation.performance_band,
                    "evaluation_model": evaluation.evaluation_model,
                    "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
                    "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None
                })

            return func.HttpResponse(
                json.dumps({"evaluations": evaluations_data}),
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
