"""
DDAnalyzeDocuments - Runs Pass 1 (Extract) and Pass 2 (Analyze) only

This endpoint is the first part of the split DD pipeline:
1. DDAnalyzeDocuments - Pass 1 + Pass 2 + Create Checkpoint C
2. DDGenerateReport - Pass 3-7 (after user completes Checkpoint C)

The endpoint:
1. Validates the request and creates a checkpoint record
2. Spawns a background thread to run Pass 1-2
3. Returns 202 Accepted immediately
4. When Pass 1-2 complete, creates Checkpoint C for user validation
5. The frontend shows Checkpoint C as a popup modal

POST /api/dd-analyze?run_id=xxx
"""
import logging
import os
import json
import threading
import uuid as uuid_module
import datetime
from typing import Dict, Any

import azure.functions as func

from shared.session import transactional_session
from sqlalchemy import text
from shared.models import (
    Document, DueDiligence, Folder,
    DDProcessingCheckpoint, DDAnalysisRun
)
from shared.audit import log_audit_event, AuditEventType

# Checkpoint C imports
from DDValidationCheckpoint import get_validated_context, create_checkpoint
from dd_enhanced.core.checkpoint_questions import generate_checkpoint_c_content

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Global dict to track running processes (for dev mode)
_running_processes: Dict[str, threading.Thread] = {}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Start Pass 1-2 analysis for a specific run.

    Returns 202 Accepted immediately with checkpoint_id.
    When analysis completes, Checkpoint C is created.
    Frontend should poll DDProgressEnhanced for updates.

    Query params:
        run_id: The Analysis Run ID (required) - created via DDAnalysisRunCreate

    Body (optional JSON):
        include_tier3: bool - Include deep-dive questions (default: false)
    """
    # Only allow in dev mode for now
    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            status_code=403,
            mimetype="application/json"
        )

    try:
        # Get run_id from query params
        run_id = req.params.get('run_id')
        if not run_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate UUID format
        try:
            uuid_module.UUID(run_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid run_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse options from body
        options = {}
        try:
            body = req.get_json()
            options = body if isinstance(body, dict) else {}
        except (ValueError, TypeError):
            pass

        include_tier3 = options.get('include_tier3', False)
        model_tier = options.get('model_tier', 'balanced')

        # Validate model_tier
        valid_tiers = ['cost_optimized', 'balanced', 'high_accuracy', 'maximum_accuracy']
        if model_tier not in valid_tiers:
            model_tier = 'balanced'

        logging.info(f"[DDAnalyzeDocuments] Starting analysis for Run: {run_id}, Tier: {model_tier}")

        # Check if already processing this run
        if run_id in _running_processes:
            thread = _running_processes[run_id]
            if thread.is_alive():
                return func.HttpResponse(
                    json.dumps({
                        "error": "Analysis already in progress for this run",
                        "run_id": run_id
                    }),
                    status_code=409,
                    mimetype="application/json"
                )
            else:
                del _running_processes[run_id]

        # Initialize checkpoint in database
        with transactional_session() as session:
            run_uuid = uuid_module.UUID(run_id)

            # Validate run exists
            run = session.query(DDAnalysisRun).filter(DDAnalysisRun.id == run_uuid).first()
            if not run:
                return func.HttpResponse(
                    json.dumps({"error": "Run not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            dd_id = run.dd_id
            dd_id_str = str(dd_id)
            selected_doc_ids = run.selected_document_ids or []
            doc_count = len(selected_doc_ids)

            if doc_count == 0:
                return func.HttpResponse(
                    json.dumps({"error": "No documents selected for analysis"}),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check if analysis already completed for this run
            existing_checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_uuid,
                DDProcessingCheckpoint.pass2_progress >= 100
            ).first()

            if existing_checkpoint:
                return func.HttpResponse(
                    json.dumps({
                        "status": "already_completed",
                        "message": "Analysis already completed for this run",
                        "run_id": run_id,
                        "checkpoint_id": str(existing_checkpoint.id)
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            # Create or get processing checkpoint
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_uuid
            ).first()

            if checkpoint:
                # Resume existing checkpoint
                checkpoint.status = 'processing'
                checkpoint.current_stage = 'resuming_analysis'
            else:
                # Create new checkpoint
                checkpoint = DDProcessingCheckpoint(
                    dd_id=dd_id,
                    run_id=run_uuid,
                    status='processing',
                    current_pass=1,
                    current_stage='queued',
                    total_documents=doc_count,
                    documents_processed=0,
                    pass1_progress=0,
                    pass2_progress=0,
                    pass3_progress=0,
                    pass4_progress=0,
                    findings_total=0,
                    findings_critical=0,
                    findings_high=0,
                    findings_medium=0,
                    findings_low=0,
                    findings_deal_blockers=0,
                    findings_cps=0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    estimated_cost_usd=0.0,
                    started_at=datetime.datetime.utcnow()
                )
                session.add(checkpoint)

            # Update run status
            run.status = 'processing'
            run.started_at = datetime.datetime.utcnow()
            run.model_tier = model_tier

            session.commit()
            checkpoint_id = str(checkpoint.id)

        # Spawn background thread
        thread = threading.Thread(
            target=_run_analysis_in_background,
            args=(dd_id_str, run_id, checkpoint_id, selected_doc_ids, include_tier3, model_tier),
            daemon=True
        )
        thread.start()
        _running_processes[run_id] = thread

        logging.info(f"[DDAnalyzeDocuments] Background thread started for Run: {run_id}")

        return func.HttpResponse(
            json.dumps({
                "status": "accepted",
                "message": "Analysis started (Pass 1-2)",
                "run_id": run_id,
                "dd_id": dd_id_str,
                "checkpoint_id": checkpoint_id,
                "total_documents": doc_count,
                "poll_url": f"/api/dd-progress-enhanced?run_id={run_id}"
            }),
            status_code=202,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception(f"[DDAnalyzeDocuments] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _run_analysis_in_background(
    dd_id: str,
    run_id: str,
    checkpoint_id: str,
    selected_doc_ids: list,
    include_tier3: bool,
    model_tier: str = "balanced"
):
    """
    Background worker that runs Pass 1-2 only.
    After completion, creates Checkpoint C for user validation.
    """
    import sys
    import traceback
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

    from config.blueprints.loader import load_blueprint
    from dd_enhanced.core.claude_client import ClaudeClient, ModelTier
    from dd_enhanced.core.question_prioritizer import prioritize_questions
    from dd_enhanced.core.materiality import calculate_materiality_thresholds

    # Import shared functions from DDProcessEnhancedStart
    from DDProcessEnhancedStart import (
        _load_dd_data_for_processing,
        _run_pass1_with_progress,
        _run_pass2_with_progress,
        _update_checkpoint,
        _update_run_status,
        _check_should_stop,
        _save_intermediate_results
    )

    try:
        print(f"\n{'='*60}", flush=True)
        print(f"[DDAnalyzeDocuments] STARTING ANALYSIS (Pass 1-2)", flush=True)
        print(f"[DDAnalyzeDocuments] Run: {run_id}, DD: {dd_id}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # Phase 1: Load data
        print(f"[DDAnalyzeDocuments] Loading data...", flush=True)
        _update_checkpoint(checkpoint_id, {
            'current_stage': 'loading_data',
            'current_pass': 1
        })

        load_result = _load_dd_data_for_processing(dd_id, selected_doc_ids)
        if load_result.get("error"):
            print(f"[DDAnalyzeDocuments] ERROR loading data: {load_result['error']}", flush=True)
            _update_checkpoint(checkpoint_id, {
                'status': 'failed',
                'last_error': load_result["error"]
            })
            _update_run_status(run_id, 'failed', {'last_error': load_result["error"]})
            return

        doc_dicts = load_result["doc_dicts"]
        blueprint = load_result["blueprint"]
        transaction_context = load_result["transaction_context"]
        transaction_context_str = load_result["transaction_context_str"]
        reference_docs = load_result["reference_docs"]

        print(f"[DDAnalyzeDocuments] Loaded {len(doc_dicts)} documents", flush=True)

        # Phase 2: Calculate materiality thresholds
        transaction_value = load_result.get("transaction_value")
        materiality_thresholds = calculate_materiality_thresholds(transaction_value)

        total_docs = len(doc_dicts)
        _update_checkpoint(checkpoint_id, {
            'current_stage': 'pass1_extraction',
            'total_documents': total_docs
        })

        # Map model tier
        tier_map = {
            'cost_optimized': ModelTier.COST_OPTIMIZED,
            'balanced': ModelTier.BALANCED,
            'high_accuracy': ModelTier.HIGH_ACCURACY,
            'maximum_accuracy': ModelTier.MAXIMUM_ACCURACY,
        }
        selected_tier = tier_map.get(model_tier, ModelTier.BALANCED)

        # Initialize Claude client
        client = ClaudeClient(model_tier=selected_tier)
        print(f"[DDAnalyzeDocuments] Using model tier: {selected_tier.value}", flush=True)

        # ===== PASS 1: Extract =====
        print(f"\n[DDAnalyzeDocuments] Pass 1: Extracting from {total_docs} documents", flush=True)

        pass1_results = _run_pass1_with_progress(
            doc_dicts, client, checkpoint_id, total_docs, run_id
        )

        if pass1_results is None:
            print(f"[DDAnalyzeDocuments] Thread exiting after Pass 1 pause timeout", flush=True)
            return

        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            print(f"[DDAnalyzeDocuments] Stopped after Pass 1: {reason}", flush=True)
            return

        # ===== Prioritize questions for Pass 2 =====
        prioritized_questions = prioritize_questions(
            blueprint=blueprint,
            transaction_context=transaction_context,
            include_tier3=include_tier3,
            max_questions=150
        )
        total_questions = sum(len(q.get("questions", [])) for q in prioritized_questions)

        _update_checkpoint(checkpoint_id, {
            'current_pass': 2,
            'current_stage': 'pass2_analysis',
            'pass1_progress': 100,
            'total_questions': total_questions
        })

        # ===== PASS 2: Analyze =====
        print(f"\n[DDAnalyzeDocuments] Pass 2: Analyzing {total_docs} documents", flush=True)

        pass2_result = _run_pass2_with_progress(
            doc_dicts, reference_docs, blueprint, client, checkpoint_id,
            transaction_context_str, prioritized_questions, total_docs, run_id,
            pass1_results
        )

        if pass2_result is None:
            print(f"[DDAnalyzeDocuments] Thread exiting after Pass 2 pause timeout", flush=True)
            return

        pass2_findings = pass2_result.get("findings", [])
        blueprint_qa = pass2_result.get("blueprint_qa", [])

        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            print(f"[DDAnalyzeDocuments] Stopped after Pass 2: {reason}", flush=True)
            return

        # ===== Save intermediate results =====
        print(f"[DDAnalyzeDocuments] Saving intermediate results...", flush=True)
        _save_intermediate_results(checkpoint_id, {
            'pass1_extractions': pass1_results,
            'pass2_findings': pass2_findings,
            'blueprint_qa': blueprint_qa
        })

        # ===== Create Checkpoint C =====
        print(f"\n{'='*60}", flush=True)
        print(f"[DDAnalyzeDocuments] Creating Checkpoint C for user validation", flush=True)

        checkpoint_c_created = _create_checkpoint_c(
            dd_id=dd_id,
            run_id=run_id,
            pass1_results=pass1_results,
            pass2_findings=pass2_findings,
            transaction_context=transaction_context,
            checkpoint_id=checkpoint_id
        )

        if checkpoint_c_created:
            print(f"[DDAnalyzeDocuments] Checkpoint C created successfully", flush=True)
        else:
            print(f"[DDAnalyzeDocuments] WARNING: Failed to create Checkpoint C", flush=True)

        # Update status to paused (waiting for Checkpoint C validation)
        # Using 'paused' status with 'waiting_for_checkpoint_c' stage to indicate state
        _update_checkpoint(checkpoint_id, {
            'current_stage': 'waiting_for_checkpoint_c',
            'status': 'paused',
            'pass2_progress': 100
        })

        # Update run status to paused
        _update_run_status(run_id, 'paused', {
            'analysis_completed_at': datetime.datetime.utcnow().isoformat()
        })

        # Get cost summary
        cost_summary = client.get_cost_summary()

        print(f"\n{'='*60}", flush=True)
        print(f"[DDAnalyzeDocuments] ANALYSIS COMPLETE (Pass 1-2)", flush=True)
        print(f"[DDAnalyzeDocuments] Findings: {len(pass2_findings)}", flush=True)
        print(f"[DDAnalyzeDocuments] Cost: ${cost_summary.get('total_cost_usd', 0):.4f}", flush=True)
        print(f"[DDAnalyzeDocuments] Status: Waiting for Checkpoint C validation", flush=True)
        print(f"{'='*60}\n", flush=True)

    except Exception as e:
        error_msg = str(e)
        print(f"[DDAnalyzeDocuments] EXCEPTION: {error_msg}", flush=True)
        print(f"[DDAnalyzeDocuments] Traceback:\n{traceback.format_exc()}", flush=True)

        _update_checkpoint(checkpoint_id, {
            'status': 'failed',
            'last_error': error_msg[:1000]
        })
        _update_run_status(run_id, 'failed', {'last_error': error_msg[:500]})


def _create_checkpoint_c(
    dd_id: str,
    run_id: str,
    pass1_results: Dict[str, Any],
    pass2_findings: Any,
    transaction_context: Dict[str, Any],
    checkpoint_id: str
) -> bool:
    """
    Create Checkpoint C (post-analysis validation).

    Returns True if checkpoint was created successfully.
    """
    import traceback

    print(f"[Checkpoint C] Creating checkpoint for run {run_id}", flush=True)

    try:
        # Check if Checkpoint C already exists
        validated_result = get_validated_context(run_id)
        if validated_result.get("has_validated_context"):
            print(f"[Checkpoint C] Already completed for run {run_id}", flush=True)
            return True

        # Check if pending checkpoint exists
        with transactional_session() as session:
            from shared.models import DDValidationCheckpoint as CheckpointModel
            run_uuid = uuid_module.UUID(run_id) if isinstance(run_id, str) else run_id
            existing = session.query(CheckpointModel).filter(
                CheckpointModel.run_id == run_uuid,
                CheckpointModel.checkpoint_type == "post_analysis",
                CheckpointModel.status.in_(["pending", "awaiting_user_input"])
            ).first()

            if existing:
                print(f"[Checkpoint C] Already pending for run {run_id}: {existing.id}", flush=True)
                return True

        # Generate Checkpoint C content
        findings_list = pass2_findings if isinstance(pass2_findings, list) else pass2_findings.get('findings', [])
        print(f"[Checkpoint C] Generating content from {len(findings_list)} findings", flush=True)

        checkpoint_content = generate_checkpoint_c_content(
            findings=findings_list,
            pass1_results=pass1_results,
            transaction_context=transaction_context,
            synthesis_preview=None
        )

        # Create the checkpoint
        result = create_checkpoint(
            dd_id=dd_id,
            run_id=run_id,
            checkpoint_type="post_analysis",
            content={
                "preliminary_summary": checkpoint_content.get("step_1_understanding", {}).get("preliminary_summary", ""),
                "questions": checkpoint_content.get("step_1_understanding", {}).get("questions", []),
                "financial_confirmations": checkpoint_content.get("step_2_financial", {}).get("confirmations", []),
                "missing_docs": checkpoint_content.get("step_3_missing_docs", {}).get("missing_documents", [])
            }
        )

        if result.get("checkpoint_id"):
            print(f"[Checkpoint C] Created: {result['checkpoint_id']}", flush=True)
            return True
        else:
            print(f"[Checkpoint C] Failed to create: {result}", flush=True)
            return False

    except Exception as e:
        print(f"[Checkpoint C] EXCEPTION: {e}", flush=True)
        print(f"[Checkpoint C] Traceback:\n{traceback.format_exc()}", flush=True)
        return False
