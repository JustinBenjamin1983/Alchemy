# File: server/opinion/api-2/DDEvaluationGet/__init__.py
"""
Get a single DD Evaluation by ID.

Returns the full evaluation results including detailed scoring breakdown.
"""
import logging
import os
import json
import uuid as uuid_module
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDEvaluation, DDEvalRubric, DDAnalysisRun, DueDiligence
from shared.session import transactional_session


DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        evaluation_id = req.params.get("evaluation_id")

        if not evaluation_id:
            return func.HttpResponse(
                json.dumps({"error": "evaluation_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Convert to UUID object for database operations
        try:
            eval_uuid = uuid_module.UUID(evaluation_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid evaluation_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        email, err = auth_get_email(req)
        if err:
            return err

        with transactional_session() as session:
            evaluation = session.query(DDEvaluation).filter(
                DDEvaluation.id == eval_uuid
            ).first()

            if not evaluation:
                return func.HttpResponse(
                    json.dumps({"error": "Evaluation not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get rubric details
            rubric = session.query(DDEvalRubric).filter(
                DDEvalRubric.id == evaluation.rubric_id
            ).first()

            # Get run details
            run = session.query(DDAnalysisRun).filter(
                DDAnalysisRun.id == evaluation.run_id
            ).first()

            dd_name = None
            dd_id = None
            if run:
                dd = session.query(DueDiligence).filter(
                    DueDiligence.id == run.dd_id
                ).first()
                if dd:
                    dd_name = dd.name
                    dd_id = str(dd.id)

            return func.HttpResponse(
                json.dumps({
                    "id": str(evaluation.id),
                    "rubric_id": str(evaluation.rubric_id),
                    "rubric_name": rubric.name if rubric else None,
                    "rubric_total_points": rubric.total_points if rubric else None,
                    "run_id": str(evaluation.run_id),
                    "run_name": run.name if run else None,
                    "dd_id": dd_id,
                    "dd_name": dd_name,
                    "status": evaluation.status,
                    "scores": evaluation.scores,
                    "total_score": evaluation.total_score,
                    "percentage": evaluation.percentage,
                    "performance_band": evaluation.performance_band,
                    "evaluation_model": evaluation.evaluation_model,
                    "raw_response": evaluation.raw_response,
                    "error_message": evaluation.error_message,
                    "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
                    "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None
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
