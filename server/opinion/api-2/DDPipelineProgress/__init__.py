# File: server/opinion/api-2/DDPipelineProgress/__init__.py
"""
DD Pipeline Progress API

Provides endpoints for:
- Getting current pipeline progress and stage
- Setting/resuming from a specific stage
- Marking stages as complete
- Getting all stage metadata for UI display
"""

import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDProcessingCheckpoint, DueDiligence
from shared.session import transactional_session
from shared.pipeline_stages import (
    PipelineStage,
    PipelinePhase,
    STAGE_ORDER,
    STAGE_METADATA,
    get_stage_index,
    get_next_stage,
    get_resumable_stages,
    get_checkpoint_stages,
    calculate_overall_progress,
)
import uuid
import datetime

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("DDPipelineProgress function triggered")

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get("function-key") != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("Unauthorized", status_code=401)

    # Auth
    if DEV_MODE:
        email = "dev@alchemy.local"
    else:
        email, err = auth_get_email(req)
        if err:
            return err

    method = req.method.upper()

    try:
        if method == "GET":
            return handle_get(req, email)
        elif method == "POST":
            return handle_post(req, email)
        elif method == "PUT":
            return handle_put(req, email)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {method} not allowed"}),
                mimetype="application/json",
                status_code=405
            )
    except Exception as e:
        logging.error(f"Error in DDPipelineProgress: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def handle_get(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    GET /api/dd-pipeline-progress?dd_id=<uuid>
    GET /api/dd-pipeline-progress?stages=metadata  (get all stage metadata)

    Returns current pipeline progress for a DD or all stage metadata.
    """
    # Check if requesting stage metadata
    if req.params.get("stages") == "metadata":
        return get_stage_metadata()

    dd_id = req.params.get("dd_id")
    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        # Get or create checkpoint
        checkpoint = session.query(DDProcessingCheckpoint).filter(
            DDProcessingCheckpoint.dd_id == uuid.UUID(dd_id)
        ).first()

        if not checkpoint:
            # Return default progress (wizard stage)
            return func.HttpResponse(
                json.dumps({
                    "dd_id": dd_id,
                    "pipeline_stage": PipelineStage.WIZARD.value,
                    "completed_stages": [],
                    "overall_progress": 0,
                    "stage_progress": {
                        "classification": 0,
                        "readability": 0,
                        "entity_mapping": 0,
                        "pass_1": 0,
                        "pass_2": 0,
                        "pass_3": 0,
                        "pass_4": 0,
                        "pass_5": 0,
                        "pass_6": 0,
                        "pass_7": 0,
                    },
                    "can_resume_from": [s.value for s in get_resumable_stages()],
                    "checkpoints": [s.value for s in get_checkpoint_stages()],
                }),
                mimetype="application/json",
                status_code=200
            )

        # Build response
        completed_stages = checkpoint.completed_stages or []
        pipeline_stage = getattr(checkpoint, 'pipeline_stage', None) or PipelineStage.WIZARD.value

        response = {
            "dd_id": dd_id,
            "checkpoint_id": str(checkpoint.id),
            "pipeline_stage": pipeline_stage,
            "current_stage_name": STAGE_METADATA.get(
                PipelineStage(pipeline_stage), {}
            ).get("name", pipeline_stage),
            "completed_stages": completed_stages,
            "overall_progress": calculate_overall_progress(
                [PipelineStage(s) for s in completed_stages if s in [ps.value for ps in PipelineStage]]
            ),
            "stage_progress": {
                "classification": getattr(checkpoint, 'classification_progress', 0) or 0,
                "readability": getattr(checkpoint, 'readability_progress', 0) or 0,
                "entity_mapping": getattr(checkpoint, 'entity_mapping_progress', 0) or 0,
                "pass_1": checkpoint.pass1_progress or 0,
                "pass_2": checkpoint.pass2_progress or 0,
                "pass_3": checkpoint.pass3_progress or 0,
                "pass_4": checkpoint.pass4_progress or 0,
                "pass_5": getattr(checkpoint, 'pass5_progress', 0) or 0,
                "pass_6": getattr(checkpoint, 'pass6_progress', 0) or 0,
                "pass_7": getattr(checkpoint, 'pass7_progress', 0) or 0,
            },
            "documents_processed": checkpoint.documents_processed or 0,
            "total_documents": checkpoint.total_documents or 0,
            "findings_count": {
                "total": checkpoint.findings_total or 0,
                "critical": checkpoint.findings_critical or 0,
                "high": checkpoint.findings_high or 0,
                "medium": checkpoint.findings_medium or 0,
                "low": checkpoint.findings_low or 0,
                "deal_blockers": checkpoint.findings_deal_blockers or 0,
            },
            "status": checkpoint.status,
            "last_error": checkpoint.last_error,
            "started_at": checkpoint.started_at.isoformat() if checkpoint.started_at else None,
            "last_updated": checkpoint.last_updated.isoformat() if checkpoint.last_updated else None,
            "paused_at": getattr(checkpoint, 'paused_at', None),
            "can_resume_from": [s.value for s in get_resumable_stages()],
            "checkpoints": [s.value for s in get_checkpoint_stages()],
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )


def handle_post(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    POST /api/dd-pipeline-progress
    Body: { dd_id, action: "resume_from" | "mark_complete" | "pause", stage?: string }

    Perform actions on pipeline progress.
    """
    req_body = req.get_json()
    dd_id = req_body.get("dd_id")
    action = req_body.get("action")
    stage = req_body.get("stage")

    if not dd_id or not action:
        return func.HttpResponse(
            json.dumps({"error": "dd_id and action are required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        # Get or create checkpoint
        checkpoint = session.query(DDProcessingCheckpoint).filter(
            DDProcessingCheckpoint.dd_id == uuid.UUID(dd_id)
        ).first()

        if not checkpoint:
            checkpoint = DDProcessingCheckpoint(
                id=uuid.uuid4(),
                dd_id=uuid.UUID(dd_id),
                pipeline_stage=PipelineStage.WIZARD.value,
                completed_stages=[],
                status="pending",
            )
            session.add(checkpoint)

        if action == "resume_from":
            # Resume from a specific stage
            if not stage:
                return func.HttpResponse(
                    json.dumps({"error": "stage is required for resume_from action"}),
                    mimetype="application/json",
                    status_code=400
                )

            # Validate stage
            try:
                target_stage = PipelineStage(stage)
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": f"Invalid stage: {stage}"}),
                    mimetype="application/json",
                    status_code=400
                )

            # Check if stage is resumable
            if target_stage not in get_resumable_stages():
                return func.HttpResponse(
                    json.dumps({"error": f"Stage {stage} cannot be resumed from"}),
                    mimetype="application/json",
                    status_code=400
                )

            # Update checkpoint
            checkpoint.pipeline_stage = target_stage.value
            checkpoint.resume_from_stage = target_stage.value
            checkpoint.resumed_at = datetime.datetime.utcnow()
            checkpoint.paused_at = None
            checkpoint.status = "processing"
            checkpoint.last_error = None

            # Remove stages after the resume point from completed_stages
            target_idx = get_stage_index(target_stage)
            completed = checkpoint.completed_stages or []
            checkpoint.completed_stages = [
                s for s in completed
                if s in [ps.value for ps in PipelineStage] and
                get_stage_index(PipelineStage(s)) < target_idx
            ]

            session.commit()

            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": f"Pipeline will resume from {STAGE_METADATA[target_stage]['name']}",
                    "pipeline_stage": target_stage.value,
                    "completed_stages": checkpoint.completed_stages,
                }),
                mimetype="application/json",
                status_code=200
            )

        elif action == "mark_complete":
            # Mark a stage as complete
            if not stage:
                return func.HttpResponse(
                    json.dumps({"error": "stage is required for mark_complete action"}),
                    mimetype="application/json",
                    status_code=400
                )

            try:
                completed_stage = PipelineStage(stage)
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": f"Invalid stage: {stage}"}),
                    mimetype="application/json",
                    status_code=400
                )

            # Add to completed stages if not already there
            completed = checkpoint.completed_stages or []
            if completed_stage.value not in completed:
                completed.append(completed_stage.value)
                checkpoint.completed_stages = completed

            # Move to next stage
            next_stage = get_next_stage(completed_stage)
            if next_stage:
                checkpoint.pipeline_stage = next_stage.value

            checkpoint.last_updated = datetime.datetime.utcnow()
            session.commit()

            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": f"Stage {STAGE_METADATA[completed_stage]['name']} marked complete",
                    "pipeline_stage": checkpoint.pipeline_stage,
                    "completed_stages": checkpoint.completed_stages,
                    "next_stage": next_stage.value if next_stage else None,
                }),
                mimetype="application/json",
                status_code=200
            )

        elif action == "pause":
            # Pause processing
            checkpoint.paused_at = datetime.datetime.utcnow()
            checkpoint.status = "paused"
            session.commit()

            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": "Pipeline paused",
                    "pipeline_stage": checkpoint.pipeline_stage,
                    "paused_at": checkpoint.paused_at.isoformat(),
                }),
                mimetype="application/json",
                status_code=200
            )

        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown action: {action}"}),
                mimetype="application/json",
                status_code=400
            )


def handle_put(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    PUT /api/dd-pipeline-progress
    Body: { dd_id, pipeline_stage?, stage_progress?: { pass_1?: int, ... }, ... }

    Update pipeline progress directly (used by processing endpoints).
    """
    req_body = req.get_json()
    dd_id = req_body.get("dd_id")

    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        checkpoint = session.query(DDProcessingCheckpoint).filter(
            DDProcessingCheckpoint.dd_id == uuid.UUID(dd_id)
        ).first()

        if not checkpoint:
            checkpoint = DDProcessingCheckpoint(
                id=uuid.uuid4(),
                dd_id=uuid.UUID(dd_id),
                pipeline_stage=PipelineStage.WIZARD.value,
                completed_stages=[],
                status="pending",
            )
            session.add(checkpoint)

        # Update fields if provided
        if "pipeline_stage" in req_body:
            checkpoint.pipeline_stage = req_body["pipeline_stage"]

        if "status" in req_body:
            checkpoint.status = req_body["status"]

        if "stage_progress" in req_body:
            sp = req_body["stage_progress"]
            if "classification" in sp:
                checkpoint.classification_progress = sp["classification"]
            if "readability" in sp:
                checkpoint.readability_progress = sp["readability"]
            if "entity_mapping" in sp:
                checkpoint.entity_mapping_progress = sp["entity_mapping"]
            if "pass_1" in sp:
                checkpoint.pass1_progress = sp["pass_1"]
            if "pass_2" in sp:
                checkpoint.pass2_progress = sp["pass_2"]
            if "pass_3" in sp:
                checkpoint.pass3_progress = sp["pass_3"]
            if "pass_4" in sp:
                checkpoint.pass4_progress = sp["pass_4"]
            if "pass_5" in sp:
                checkpoint.pass5_progress = sp["pass_5"]
            if "pass_6" in sp:
                checkpoint.pass6_progress = sp["pass_6"]
            if "pass_7" in sp:
                checkpoint.pass7_progress = sp["pass_7"]

        if "completed_stages" in req_body:
            checkpoint.completed_stages = req_body["completed_stages"]

        if "documents_processed" in req_body:
            checkpoint.documents_processed = req_body["documents_processed"]

        if "total_documents" in req_body:
            checkpoint.total_documents = req_body["total_documents"]

        if "last_error" in req_body:
            checkpoint.last_error = req_body["last_error"]

        checkpoint.last_updated = datetime.datetime.utcnow()
        session.commit()

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "pipeline_stage": checkpoint.pipeline_stage,
                "completed_stages": checkpoint.completed_stages or [],
            }),
            mimetype="application/json",
            status_code=200
        )


def get_stage_metadata() -> func.HttpResponse:
    """Return all stage metadata for UI display."""
    stages = []
    for stage in STAGE_ORDER:
        meta = STAGE_METADATA.get(stage, {})
        stages.append({
            "id": stage.value,
            "name": meta.get("name", stage.value),
            "description": meta.get("description", ""),
            "phase": meta.get("phase", PipelinePhase.PRE_PROCESSING).value,
            "order": meta.get("order", 0),
            "is_checkpoint": meta.get("is_checkpoint", False),
            "requires_user_input": meta.get("requires_user_input", False),
            "model": meta.get("model"),
            "can_resume_from": meta.get("can_resume_from", False),
        })

    return func.HttpResponse(
        json.dumps({
            "stages": stages,
            "phases": [
                {"id": "pre_processing", "name": "Pre-Processing"},
                {"id": "processing", "name": "Processing"},
                {"id": "post_processing", "name": "Post-Processing"},
            ],
        }),
        mimetype="application/json",
        status_code=200
    )
