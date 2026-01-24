"""
DDProcessEnhancedStart - Async DD Processing Launcher

This endpoint:
1. Validates the request and creates a checkpoint record
2. Spawns a background thread to run processing
3. Returns 202 Accepted immediately

The frontend polls DDProgressEnhanced to get real-time progress updates.

DEV MODE: Uses threading for background processing (no EventGrid/Durable Functions dependency)
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
from shared.models import (
    Document, DueDiligence, DueDiligenceMember, Folder,
    PerspectiveRisk, PerspectiveRiskFinding, Perspective, DDWizardDraft,
    DDProcessingCheckpoint, DDAnalysisRun, DDReportVersion
)
from shared.audit import log_audit_event, AuditEventType

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Global dict to track running processes (for dev mode)
_running_processes: Dict[str, threading.Thread] = {}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Start async DD processing for a specific run.

    Returns 202 Accepted immediately with checkpoint_id.
    Frontend should poll DDProgressEnhanced for updates.

    Query params:
        run_id: The Analysis Run ID (required) - created via DDAnalysisRunCreate

    Body (optional JSON):
        include_tier3: bool - Include deep-dive questions (default: false)
        use_clustered_pass3: bool - Use optimized Pass 3 (default: true)
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
        use_clustered_pass3 = options.get('use_clustered_pass3', True)
        model_tier = options.get('model_tier', 'balanced')  # cost_optimized, balanced, high_accuracy, maximum_accuracy

        # Validate model_tier
        valid_tiers = ['cost_optimized', 'balanced', 'high_accuracy', 'maximum_accuracy']
        if model_tier not in valid_tiers:
            model_tier = 'balanced'

        logging.info(f"[DDProcessEnhancedStart] Starting async processing for Run: {run_id}, Tier: {model_tier}")

        # Check if already processing this run
        if run_id in _running_processes:
            thread = _running_processes[run_id]
            if thread.is_alive():
                return func.HttpResponse(
                    json.dumps({
                        "error": "Processing already in progress for this run",
                        "run_id": run_id
                    }),
                    status_code=409,  # Conflict
                    mimetype="application/json"
                )
            else:
                # Clean up dead thread
                del _running_processes[run_id]

        # Initialize checkpoint in database
        with transactional_session() as session:
            # Validate run exists and get its details
            run_uuid = uuid_module.UUID(run_id)
            run = session.query(DDAnalysisRun).filter(DDAnalysisRun.id == run_uuid).first()
            if not run:
                return func.HttpResponse(
                    json.dumps({"error": "Run not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            dd_id = run.dd_id  # Keep as UUID object for database operations
            dd_id_str = str(run.dd_id)  # String version for JSON responses
            selected_doc_ids = run.selected_document_ids or []

            if not selected_doc_ids:
                return func.HttpResponse(
                    json.dumps({"error": "No documents selected for this run"}),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check run status
            if run.status == "processing":
                return func.HttpResponse(
                    json.dumps({"error": "Run is already processing"}),
                    status_code=409,
                    mimetype="application/json"
                )

            if run.status == "completed":
                return func.HttpResponse(
                    json.dumps({"error": "Run has already completed. Create a new run to process again."}),
                    status_code=409,
                    mimetype="application/json"
                )

            doc_count = len(selected_doc_ids)

            # Delete existing checkpoint for this run if any
            existing = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_id
            ).first()
            if existing:
                session.delete(existing)
                session.flush()

            # Create new checkpoint linked to run
            checkpoint = DDProcessingCheckpoint(
                dd_id=dd_id,  # UUID object
                run_id=run_uuid,  # UUID object
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

            # Update run status and model tier
            run.status = 'processing'
            run.started_at = datetime.datetime.utcnow()
            run.model_tier = model_tier

            session.commit()

            checkpoint_id = str(checkpoint.id)

        # Spawn background thread (pass string versions for JSON/logging operations)
        thread = threading.Thread(
            target=_run_processing_in_background,
            args=(dd_id_str, run_id, checkpoint_id, selected_doc_ids, include_tier3, use_clustered_pass3, model_tier),
            daemon=True
        )
        thread.start()
        _running_processes[run_id] = thread

        logging.info(f"[DDProcessEnhancedStart] Background thread started for Run: {run_id}")

        # Log audit event for analysis start
        try:
            with transactional_session() as audit_session:
                log_audit_event(
                    session=audit_session,
                    event_type=AuditEventType.ANALYSIS_STARTED,
                    entity_type="analysis_run",
                    entity_id=run_id,
                    dd_id=dd_id_str,
                    details={
                        "checkpoint_id": checkpoint_id,
                        "document_count": doc_count,
                        "include_tier3": include_tier3,
                        "use_clustered_pass3": use_clustered_pass3
                    }
                )
                audit_session.commit()
        except Exception as audit_err:
            logging.warning(f"[DDProcessEnhancedStart] Audit logging failed: {audit_err}")

        return func.HttpResponse(
            json.dumps({
                "status": "accepted",
                "message": "Processing started",
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
        logging.exception(f"[DDProcessEnhancedStart] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _run_processing_in_background(
    dd_id: str,
    run_id: str,
    checkpoint_id: str,
    selected_doc_ids: list,
    include_tier3: bool,
    use_clustered_pass3: bool,
    model_tier: str = "balanced"
):
    """
    Background worker that processes DD with granular checkpoint updates.

    This runs in a separate thread and updates the checkpoint after:
    - Each document in Pass 1
    - Each document in Pass 2
    - Each cluster in Pass 3
    - Pass 4 completion

    Model Tiers:
    - cost_optimized: Haiku → Sonnet → Sonnet → Sonnet (~R350/200 docs)
    - balanced: Haiku → Sonnet → Opus → Sonnet (~R500/200 docs)
    - high_accuracy: Haiku → Sonnet → Opus → Opus (~R650/200 docs)
    - maximum_accuracy: Haiku → Opus → Opus → Opus (~R900/200 docs)
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

    from shared.dev_adapters.dev_config import get_dev_config
    from config.blueprints.loader import load_blueprint
    from dd_enhanced.core.claude_client import ClaudeClient, ModelTier
    from dd_enhanced.core.document_clusters import group_documents_by_cluster
    from dd_enhanced.core.question_prioritizer import prioritize_questions
    from dd_enhanced.core.materiality import calculate_materiality_thresholds, apply_materiality_to_findings

    try:
        # Use print for debugging since logging.info from threads isn't captured by Azure Functions
        print(f"[BackgroundProcessor] Starting for Run: {run_id}, DD: {dd_id}", flush=True)
        logging.info(f"[BackgroundProcessor] Starting for Run: {run_id}, DD: {dd_id}")

        # Phase 1: Load data
        print(f"[BackgroundProcessor] Loading data...", flush=True)
        _update_checkpoint(checkpoint_id, {
            'current_stage': 'loading_data',
            'current_pass': 1
        })

        load_result = _load_dd_data_for_processing(dd_id, selected_doc_ids)
        if load_result.get("error"):
            print(f"[BackgroundProcessor] ERROR loading data: {load_result['error']}", flush=True)
            _update_checkpoint(checkpoint_id, {
                'status': 'failed',
                'last_error': load_result["error"]
            })
            return

        doc_dicts = load_result["doc_dicts"]
        print(f"[BackgroundProcessor] Loaded {len(doc_dicts)} documents", flush=True)
        blueprint = load_result["blueprint"]
        transaction_context = load_result["transaction_context"]
        transaction_context_str = load_result["transaction_context_str"]
        reference_docs = load_result["reference_docs"]
        owned_by = load_result["owned_by"]

        # Phase 2: Calculate materiality thresholds based on transaction value
        transaction_value = load_result.get("transaction_value")
        materiality_thresholds = calculate_materiality_thresholds(transaction_value)
        logging.info(f"[BackgroundProcessor] Materiality thresholds: {materiality_thresholds.get('description', 'default')}")

        total_docs = len(doc_dicts)

        _update_checkpoint(checkpoint_id, {
            'current_stage': 'pass1_extraction',
            'total_documents': total_docs
        })

        # Map model_tier string to ModelTier enum
        tier_map = {
            'cost_optimized': ModelTier.COST_OPTIMIZED,
            'balanced': ModelTier.BALANCED,
            'high_accuracy': ModelTier.HIGH_ACCURACY,
            'maximum_accuracy': ModelTier.MAXIMUM_ACCURACY,
        }
        selected_tier = tier_map.get(model_tier, ModelTier.BALANCED)

        # Initialize Claude client with selected tier
        client = ClaudeClient(model_tier=selected_tier)
        logging.info(f"[BackgroundProcessor] Using model tier: {selected_tier.value}")

        # ===== PASS 1: Extract (with per-document updates) =====
        print(f"[BackgroundProcessor] Pass 1: Extracting from {total_docs} documents", flush=True)
        logging.info(f"[BackgroundProcessor] Pass 1: Extracting from {total_docs} documents")

        pass1_results = _run_pass1_with_progress(
            doc_dicts, client, checkpoint_id, total_docs, run_id
        )

        # Check if we should exit (None = paused timeout, thread should exit cleanly)
        if pass1_results is None:
            logging.info(f"[BackgroundProcessor] Thread exiting after Pass 1 pause timeout (state saved)")
            return

        # Check if cancelled after Pass 1
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            logging.info(f"[BackgroundProcessor] Stopped after Pass 1: {reason}")
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

        # ===== PASS 2: Per-document analysis (with per-document updates) =====
        logging.info(f"[BackgroundProcessor] Pass 2: Analyzing {total_docs} documents")

        pass2_result = _run_pass2_with_progress(
            doc_dicts, reference_docs, blueprint, client, checkpoint_id,
            transaction_context_str, prioritized_questions, total_docs, run_id,
            pass1_results  # Pass for saving on timeout
        )

        # Check if we should exit (None = paused timeout)
        if pass2_result is None:
            logging.info(f"[BackgroundProcessor] Thread exiting after Pass 2 pause timeout (state saved)")
            return

        # Extract findings and blueprint Q&A from pass2 result
        pass2_findings = pass2_result.get("findings", [])
        blueprint_qa = pass2_result.get("blueprint_qa", [])

        # Check if cancelled after Pass 2
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            logging.info(f"[BackgroundProcessor] Stopped after Pass 2: {reason}")
            return

        # ===== PASS 3: Cross-document analysis =====
        _update_checkpoint(checkpoint_id, {
            'current_pass': 3,
            'current_stage': 'pass3_crossdoc',
            'pass2_progress': 100
        })

        logging.info("[BackgroundProcessor] Pass 3: Cross-document analysis")

        if use_clustered_pass3:
            pass3_results = _run_pass3_clustered_with_progress(
                doc_dicts, pass1_results, blueprint, client, checkpoint_id, run_id, pass2_findings
            )
        else:
            pass3_results = _run_pass3_simple(
                doc_dicts, pass2_findings, blueprint, client
            )
            _update_checkpoint(checkpoint_id, {'pass3_progress': 100})

        # Check if we should exit (None = paused timeout)
        if pass3_results is None:
            logging.info(f"[BackgroundProcessor] Thread exiting after Pass 3 pause timeout (state saved)")
            return

        # Check if cancelled after Pass 3
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            logging.info(f"[BackgroundProcessor] Stopped after Pass 3: {reason}")
            return

        # ===== PASS 4: Synthesis =====
        _update_checkpoint(checkpoint_id, {
            'current_pass': 4,
            'current_stage': 'pass4_synthesis',
            'pass3_progress': 100
        })

        logging.info("[BackgroundProcessor] Pass 4: Final synthesis")

        from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis
        pass4_results = run_pass4_synthesis(
            doc_dicts, pass1_results, pass2_findings, pass3_results, client, verbose=False
        )

        _update_checkpoint(checkpoint_id, {
            'pass4_progress': 100,
            'current_stage': 'storing_findings'
        })

        # ===== Phase 2: Apply materiality classification to all findings =====
        all_findings_for_materiality = pass4_results.get("all_findings", [])
        enriched_findings = apply_materiality_to_findings(all_findings_for_materiality, materiality_thresholds)
        pass4_results["all_findings"] = enriched_findings
        logging.info(f"[BackgroundProcessor] Applied materiality classification to {len(enriched_findings)} findings")

        # ===== Store findings =====
        logging.info("[BackgroundProcessor] Storing findings in database")

        store_result = _store_findings_to_db(
            dd_id, run_id, owned_by, doc_dicts, pass4_results, pass3_results, blueprint
        )

        if store_result.get("error"):
            logging.error(f"[BackgroundProcessor] Failed to store findings: {store_result.get('error')}")
        else:
            logging.info(f"[BackgroundProcessor] Stored {store_result.get('stored_count', 0)} findings")

        # Get final cost summary
        cost_summary = client.get_cost_summary()

        # Update checkpoint with final stats
        all_findings = pass4_results.get("all_findings", [])
        cross_doc_findings = pass3_results.get("cross_doc_findings", [])

        # Count findings by severity
        critical = sum(1 for f in all_findings if f.get("severity") == "critical")
        high = sum(1 for f in all_findings if f.get("severity") == "high")
        medium = sum(1 for f in all_findings if f.get("severity") == "medium")
        low = sum(1 for f in all_findings if f.get("severity") == "low")

        deal_blockers = sum(1 for f in all_findings if f.get("deal_impact") == "deal_blocker")
        cps = sum(1 for f in all_findings if f.get("deal_impact") == "condition_precedent")

        total_findings = len(all_findings) + len(cross_doc_findings)

        _update_checkpoint(checkpoint_id, {
            'status': 'completed',
            'current_stage': 'completed',
            'completed_at': datetime.datetime.utcnow(),
            'findings_total': total_findings,
            'findings_critical': critical,
            'findings_high': high,
            'findings_medium': medium,
            'findings_low': low,
            'findings_deal_blockers': deal_blockers,
            'findings_cps': cps,
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        # Prepare synthesis data for storage
        synthesis_data = {
            'executive_summary': pass4_results.get('executive_summary', ''),
            'deal_assessment': pass4_results.get('deal_assessment', {}),
            'financial_exposures': pass4_results.get('financial_exposures', {}),
            'financial_analysis': pass4_results.get('financial_analysis', {}),  # Detailed financial analysis
            'deal_blockers': pass4_results.get('deal_blockers', []),
            'conditions_precedent': pass4_results.get('conditions_precedent', []),
            'warranties_register': pass4_results.get('warranties_register', []),
            'indemnities_register': pass4_results.get('indemnities_register', []),
            'recommendations': pass4_results.get('recommendations', []),
            'blueprint_qa': blueprint_qa,  # Q&A pairs for Blueprint Answers view
        }

        # Update run status to completed with synthesis data
        _update_run_status(run_id, 'completed', {
            'findings_total': total_findings,
            'findings_critical': critical,
            'findings_high': high,
            'findings_medium': medium,
            'findings_low': low,
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'synthesis_data': synthesis_data
        })

        # Create initial report version (V1) for the refinement loop
        try:
            _create_initial_report_version(run_id, synthesis_data, owned_by)
            logging.info(f"[BackgroundProcessor] Created V1 report version for Run: {run_id}")
        except Exception as e:
            logging.warning(f"[BackgroundProcessor] Failed to create V1 report version (non-fatal): {e}")

        logging.info(f"[BackgroundProcessor] Processing complete for Run: {run_id}")

    except Exception as e:
        import traceback
        print(f"[BackgroundProcessor] EXCEPTION: {e}", flush=True)
        print(f"[BackgroundProcessor] Traceback:\n{traceback.format_exc()}", flush=True)
        logging.exception(f"[BackgroundProcessor] Error: {e}")
        _update_checkpoint(checkpoint_id, {
            'status': 'failed',
            'last_error': str(e)[:1000],
            'retry_count': 1
        })
        # Update run status to failed
        _update_run_status(run_id, 'failed', {'last_error': str(e)[:1000]})

    finally:
        # Clean up thread reference
        if run_id in _running_processes:
            del _running_processes[run_id]


def _update_checkpoint(checkpoint_id: str, updates: Dict[str, Any]):
    """Update checkpoint with fresh database session."""
    try:
        with transactional_session() as session:
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.id == checkpoint_id
            ).first()
            if checkpoint:
                for key, value in updates.items():
                    setattr(checkpoint, key, value)
                checkpoint.last_updated = datetime.datetime.utcnow()
                session.commit()
    except Exception as e:
        logging.warning(f"[BackgroundProcessor] Failed to update checkpoint: {e}")


def _create_initial_report_version(run_id: str, synthesis_data: Dict[str, Any], created_by: str):
    """
    Create the initial V1 report version when analysis completes.

    This enables the Ask AI refinement loop - users can iterate on V1 to create V2, V3, etc.
    """
    run_uuid = uuid_module.UUID(run_id) if isinstance(run_id, str) else run_id

    with transactional_session() as session:
        # Check if V1 already exists
        existing = session.query(DDReportVersion).filter(
            DDReportVersion.run_id == run_uuid,
            DDReportVersion.version == 1
        ).first()

        if existing:
            logging.info(f"[BackgroundProcessor] V1 already exists for run {run_id}")
            return

        # Create V1
        version = DDReportVersion(
            id=uuid_module.uuid4(),
            run_id=run_uuid,
            version=1,
            content=synthesis_data,
            refinement_prompt=None,  # V1 is the initial version, no refinement
            changes=None,
            is_current=True,
            change_summary="Initial report generated from DD analysis",
            created_at=datetime.datetime.utcnow(),
            created_by=created_by
        )
        session.add(version)
        session.commit()


def _check_should_stop(checkpoint_id: str) -> tuple[bool, str]:
    """
    Check if processing should stop (cancelled or paused).
    Returns (should_stop, reason).
    """
    try:
        with transactional_session() as session:
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.id == checkpoint_id
            ).first()
            if checkpoint:
                if checkpoint.status == 'failed':
                    # Check if it was cancelled
                    if checkpoint.last_error and 'cancelled' in checkpoint.last_error.lower():
                        return True, 'cancelled'
                    return True, 'failed'
                if checkpoint.status == 'paused':
                    return True, 'paused'
        return False, ''
    except Exception as e:
        logging.warning(f"[BackgroundProcessor] Error checking status: {e}")
        return False, ''


def _wait_while_paused(checkpoint_id: str, run_id: str, max_wait_seconds: int = 3600) -> str:
    """
    Wait while processing is paused, up to max_wait_seconds (default 1 hour).

    Returns:
        'resumed' - Processing was resumed, continue
        'cancelled' - Processing was cancelled, stop
        'timeout' - Waited too long, thread should exit (but status stays paused)
    """
    import time
    wait_interval = 10  # Check every 10 seconds
    total_waited = 0

    while total_waited < max_wait_seconds:
        should_stop, reason = _check_should_stop(checkpoint_id)
        if not should_stop:
            # No longer paused, continue processing
            logging.info(f"[BackgroundProcessor] Run {run_id} resumed after {total_waited}s pause")
            return 'resumed'
        if reason in ('cancelled', 'failed'):
            # Was cancelled while paused
            return 'cancelled'
        # Still paused, wait
        time.sleep(wait_interval)
        total_waited += wait_interval
        # Log every 5 minutes
        if total_waited % 300 == 0:
            logging.info(f"[BackgroundProcessor] Run {run_id} paused, waiting... ({total_waited // 60} min)")

    # Timed out - thread will exit but status stays 'paused' for later resume
    logging.info(f"[BackgroundProcessor] Run {run_id} paused for 1 hour, saving state and exiting thread")
    return 'timeout'


def _save_intermediate_results(checkpoint_id: str, results: Dict[str, Any]):
    """Save intermediate processing results to checkpoint for resume capability."""
    try:
        with transactional_session() as session:
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.id == checkpoint_id
            ).first()
            if checkpoint:
                # Store results that can be used to resume
                if 'pass1_extractions' in results:
                    checkpoint.pass1_extractions = results['pass1_extractions']
                if 'pass2_findings' in results:
                    checkpoint.pass2_findings = results['pass2_findings']
                if 'processed_doc_ids' in results:
                    checkpoint.processed_doc_ids = results['processed_doc_ids']
                checkpoint.last_updated = datetime.datetime.utcnow()
                session.commit()
                logging.info(f"[BackgroundProcessor] Saved intermediate results to checkpoint {checkpoint_id}")
    except Exception as e:
        logging.warning(f"[BackgroundProcessor] Failed to save intermediate results: {e}")


def _update_run_status(run_id: str, status: str, updates: Dict[str, Any] = None):
    """Update run status and stats with fresh database session."""
    try:
        with transactional_session() as session:
            run_uuid = uuid_module.UUID(run_id) if isinstance(run_id, str) else run_id
            run = session.query(DDAnalysisRun).filter(DDAnalysisRun.id == run_uuid).first()
            if run:
                run.status = status
                if status == 'completed':
                    run.completed_at = datetime.datetime.utcnow()
                if updates:
                    for key, value in updates.items():
                        if hasattr(run, key):
                            setattr(run, key, value)
                session.commit()
    except Exception as e:
        logging.warning(f"[BackgroundProcessor] Failed to update run status: {e}")


def _load_dd_data_for_processing(dd_id: str, selected_doc_ids: list = None) -> Dict[str, Any]:
    """Load DD data for processing."""
    from config.blueprints.loader import load_blueprint
    from shared.dev_adapters.dev_config import get_dev_config
    from DDProcessAllDev import extract_text_from_file_with_extension

    try:
        # Convert string UUID to UUID object
        dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

        with transactional_session() as session:
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
            if not dd:
                return {"error": "DD not found"}

            dd_name = dd.name
            dd_briefing = dd.briefing
            owned_by = dd.owned_by

            # Get wizard draft for transaction context
            draft = session.query(DDWizardDraft).filter(
                DDWizardDraft.owned_by == owned_by,
                DDWizardDraft.transaction_name == dd_name
            ).first()

            transaction_type = draft.transaction_type if draft else "General"
            transaction_type_code = _map_transaction_type(transaction_type)

            # Phase 2: Extract transaction value for materiality calculation
            transaction_value = None
            if draft and hasattr(draft, 'estimated_value'):
                transaction_value = draft.estimated_value

            # Load blueprint
            try:
                blueprint = load_blueprint(transaction_type_code)
            except ValueError:
                blueprint = load_blueprint("ma_corporate")

            # Build transaction context
            transaction_context = {}
            if draft:
                if draft.known_concerns:
                    try:
                        transaction_context['known_concerns'] = json.loads(draft.known_concerns)
                    except:
                        pass
                if draft.critical_priorities:
                    try:
                        transaction_context['critical_priorities'] = json.loads(draft.critical_priorities)
                    except:
                        pass

            # Get folders and documents
            folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
            folder_ids = [f.id for f in folders]
            folder_lookup = {str(f.id): f for f in folders}

            # Filter documents by selected_doc_ids if provided
            if selected_doc_ids:
                # Convert string UUIDs to UUID objects if needed
                doc_uuids = [uuid_module.UUID(d) if isinstance(d, str) else d for d in selected_doc_ids]
                documents = session.query(Document).filter(
                    Document.id.in_(doc_uuids)
                ).all()
            else:
                documents = session.query(Document).filter(
                    Document.folder_id.in_(folder_ids)
                ).all()

            if not documents:
                return {"error": "No documents found"}

            # Extract document content
            dev_config = get_dev_config()
            local_storage_path = dev_config.get("local_storage_path", "/tmp/dd_storage")

            doc_dicts = []
            for doc in documents:
                file_path = os.path.join(local_storage_path, "docs", str(doc.id))
                extension = doc.type if doc.type else os.path.splitext(doc.original_file_name)[1].lstrip('.')

                try:
                    content = extract_text_from_file_with_extension(file_path, extension)
                except:
                    content = ""

                if content:
                    folder = folder_lookup.get(str(doc.folder_id))
                    doc_dicts.append({
                        "id": str(doc.id),
                        "filename": doc.original_file_name,
                        "text": content,
                        "doc_type": _classify_doc_type(doc.original_file_name, folder),
                        "word_count": len(content.split()),
                        "folder_path": folder.path if folder else ""
                    })

            if not doc_dicts:
                return {"error": "Could not extract content from any documents"}

            # Identify reference documents
            reference_docs = [d for d in doc_dicts if d.get("doc_type") in ["constitutional", "governance"]]

            # Build transaction context string
            transaction_context_str = f"This is a {blueprint.get('transaction_type', 'corporate')} transaction.\nProject: {dd_name}"
            if dd_briefing:
                transaction_context_str += f"\nBriefing: {dd_briefing}"

            return {
                "doc_dicts": doc_dicts,
                "blueprint": blueprint,
                "transaction_context": transaction_context,
                "transaction_context_str": transaction_context_str,
                "reference_docs": reference_docs,
                "owned_by": owned_by,
                "dd_name": dd_name,
                "transaction_value": transaction_value,  # Phase 2: For materiality calculation
            }

    except Exception as e:
        logging.exception(f"[BackgroundProcessor] Error loading DD data: {e}")
        return {"error": str(e)}


def _run_pass1_with_progress(doc_dicts, client, checkpoint_id, total_docs, run_id: str = None):
    """Run Pass 1 with per-document progress updates. Supports pause/cancel."""
    try:
        from dd_enhanced.core.pass1_extract import extract_document
        logging.info(f"[BackgroundProcessor] Successfully imported extract_document")
    except Exception as import_error:
        logging.exception(f"[BackgroundProcessor] Failed to import extract_document: {import_error}")
        raise

    combined_results = {
        "key_dates": [],
        "financial_figures": [],
        "coc_clauses": [],
        "consent_requirements": [],
        "key_parties": [],
        "document_summaries": {}
    }
    processed_doc_ids = []

    for idx, doc in enumerate(doc_dicts):
        # Check if we should stop (cancelled or paused)
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop:
            if reason == 'paused':
                logging.info(f"[BackgroundProcessor] Pass 1 paused at doc {idx + 1}/{total_docs}")
                wait_result = _wait_while_paused(checkpoint_id, run_id or '')
                if wait_result == 'resumed':
                    logging.info(f"[BackgroundProcessor] Pass 1 resumed")
                elif wait_result == 'timeout':
                    # Save state and exit - can resume later
                    _save_intermediate_results(checkpoint_id, {
                        'pass1_extractions': combined_results,
                        'processed_doc_ids': processed_doc_ids
                    })
                    return None  # Signal to exit thread
                else:  # cancelled
                    logging.info(f"[BackgroundProcessor] Pass 1 cancelled while paused")
                    return combined_results
            else:
                # Cancelled or failed
                logging.info(f"[BackgroundProcessor] Pass 1 stopped: {reason}")
                return combined_results

        try:
            _update_checkpoint(checkpoint_id, {
                'current_document_id': doc.get("id"),
                'current_document_name': doc.get("filename", ""),
                'documents_processed': idx,
                'pass1_progress': int((idx / total_docs) * 100)
            })

            result = extract_document(doc, client)

            # Merge results
            combined_results["key_dates"].extend(result.get("key_dates", []))
            combined_results["financial_figures"].extend(result.get("financial_figures", []))
            combined_results["coc_clauses"].extend(result.get("coc_clauses", []))
            combined_results["consent_requirements"].extend(result.get("consent_requirements", []))
            combined_results["key_parties"].extend(result.get("key_parties", []))
            combined_results["document_summaries"][doc["filename"]] = result.get("summary", "")
            processed_doc_ids.append(doc.get("id"))

        except Exception as e:
            logging.exception(f"[BackgroundProcessor] Pass 1 error for {doc.get('filename')}: {e}")
            # Update checkpoint with error so we can see what's happening
            _update_checkpoint(checkpoint_id, {
                'last_error': f"Pass 1 error on {doc.get('filename', 'unknown')}: {str(e)[:500]}"
            })
            # Continue to next document rather than failing completely

    logging.info(f"[BackgroundProcessor] Pass 1 complete, processed {len(processed_doc_ids)} documents")
    _update_checkpoint(checkpoint_id, {
        'documents_processed': total_docs,
        'pass1_progress': 100,
        'pass1_extractions': combined_results,
        'current_document_name': None
    })

    return combined_results


def _run_pass2_with_progress(
    doc_dicts, reference_docs, blueprint, client, checkpoint_id,
    transaction_context_str, prioritized_questions, total_docs, run_id: str = None,
    pass1_results: Dict = None
):
    """Run Pass 2 with per-document progress updates. Supports pause/cancel."""
    try:
        from dd_enhanced.core.pass2_analyze import analyze_document, _generate_gap_findings
        from config.question_loader import QuestionLoader
        logging.info(f"[BackgroundProcessor] Successfully imported analyze_document")
    except Exception as import_error:
        logging.exception(f"[BackgroundProcessor] Failed to import analyze_document: {import_error}")
        raise

    all_findings = []
    processed_doc_ids = []
    all_blueprint_qa = []  # Collect all Q&A pairs for blueprint answers view

    # Track questions asked vs answered for gap detection
    questions_asked: Dict[str, List[Dict]] = {}  # folder_category -> list of questions
    questions_answered: Dict[str, set] = {}  # folder_category -> set of answered question texts
    folder_docs_analyzed: Dict[str, List[str]] = {}  # folder_category -> list of doc filenames
    missing_info_by_folder: Dict[str, List[str]] = {}  # folder_category -> missing info items

    # Initialize QuestionLoader for folder-aware analysis
    question_loader = QuestionLoader(blueprint) if blueprint else None

    # Create RefDoc objects
    class RefDoc:
        def __init__(self, d):
            self.filename = d['filename']
            self.text = d['text']
            self.doc_type = d.get('doc_type', '')

    ref_doc_objects = [RefDoc(d) for d in reference_docs]

    for idx, doc in enumerate(doc_dicts):
        # Check if we should stop (cancelled or paused)
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop:
            if reason == 'paused':
                logging.info(f"[BackgroundProcessor] Pass 2 paused at doc {idx + 1}/{total_docs}")
                wait_result = _wait_while_paused(checkpoint_id, run_id or '')
                if wait_result == 'resumed':
                    logging.info(f"[BackgroundProcessor] Pass 2 resumed")
                elif wait_result == 'timeout':
                    # Save state and exit - can resume later
                    _save_intermediate_results(checkpoint_id, {
                        'pass1_extractions': pass1_results,
                        'pass2_findings': all_findings,
                        'processed_doc_ids': processed_doc_ids
                    })
                    return None  # Signal to exit thread
                else:  # cancelled
                    logging.info(f"[BackgroundProcessor] Pass 2 cancelled while paused")
                    return {"findings": all_findings, "blueprint_qa": all_blueprint_qa}
            else:
                logging.info(f"[BackgroundProcessor] Pass 2 stopped: {reason}")
                return {"findings": all_findings, "blueprint_qa": all_blueprint_qa}

        try:
            folder_category = doc.get("folder_category")
            filename = doc.get("filename", "")

            # Track folder-specific questions for gap detection
            if question_loader and folder_category:
                folder_questions = question_loader.get_questions_for_folder(folder_category)
                if folder_questions and folder_category not in questions_asked:
                    questions_asked[folder_category] = folder_questions
                # Track which docs were analyzed per folder
                if folder_category not in folder_docs_analyzed:
                    folder_docs_analyzed[folder_category] = []
                folder_docs_analyzed[folder_category].append(filename)

            _update_checkpoint(checkpoint_id, {
                'current_document_id': doc.get("id"),
                'current_document_name': filename,
                'documents_processed': idx,
                'pass2_progress': int((idx / total_docs) * 100)
            })

            analysis_result = analyze_document(
                doc, ref_doc_objects, blueprint, client,
                transaction_context=transaction_context_str,
                prioritized_questions=prioritized_questions,
                return_qa_data=True  # Get Q&A pairs for blueprint answers view
            )

            # Extract findings and Q&A data
            findings = analysis_result.get("findings", [])
            qa_pairs = analysis_result.get("questions_answered", [])

            # Collect Q&A pairs for blueprint answers
            if qa_pairs:
                all_blueprint_qa.extend(qa_pairs)

            # Update finding counts as we go
            if findings:
                all_findings.extend(findings)
                critical = sum(1 for f in all_findings if f.get("severity") == "critical")
                high = sum(1 for f in all_findings if f.get("severity") == "high")

                _update_checkpoint(checkpoint_id, {
                    'findings_total': len(all_findings),
                    'findings_critical': critical,
                    'findings_high': high
                })

                # Track questions answered from findings for gap detection
                for finding in findings:
                    if finding.get("blueprint_question_answered") and folder_category:
                        if folder_category not in questions_answered:
                            questions_answered[folder_category] = set()
                        questions_answered[folder_category].add(
                            finding.get("blueprint_question_answered").lower().strip()
                        )

            processed_doc_ids.append(doc.get("id"))

        except Exception as e:
            logging.warning(f"[BackgroundProcessor] Pass 2 error for {doc.get('filename')}: {e}")

    _update_checkpoint(checkpoint_id, {
        'documents_processed': total_docs,
        'pass2_progress': 100,
        'current_document_name': None
    })

    # Generate gap findings for unanswered questions
    gap_findings = _generate_gap_findings(
        questions_asked=questions_asked,
        questions_answered=questions_answered,
        folder_docs_analyzed=folder_docs_analyzed,
        missing_info_by_folder=missing_info_by_folder,
        blueprint=blueprint
    )

    if gap_findings:
        logging.info(f"[BackgroundProcessor] Generated {len(gap_findings)} gap findings for unanswered questions")
        all_findings.extend(gap_findings)

        # Update counts to include gaps
        _update_checkpoint(checkpoint_id, {
            'findings_total': len(all_findings),
            'findings_gap': len(gap_findings)
        })

    return {
        "findings": all_findings,
        "blueprint_qa": all_blueprint_qa
    }


def _run_pass3_clustered_with_progress(doc_dicts, pass1_results, blueprint, client, checkpoint_id, run_id: str = None, pass2_findings: list = None):
    """Run Pass 3 with per-cluster progress updates. Supports pause/cancel."""
    from dd_enhanced.core.document_clusters import group_documents_by_cluster
    from dd_enhanced.core.pass3_clustered import analyze_cluster

    clustered_docs = group_documents_by_cluster(doc_dicts)
    total_clusters = len(clustered_docs)

    _update_checkpoint(checkpoint_id, {
        'clusters_total': total_clusters,
        'clusters_processed': {}
    })

    all_cross_doc_findings = []
    clusters_status = {}

    for idx, (cluster_name, docs) in enumerate(clustered_docs.items()):
        # Check if we should stop (cancelled or paused)
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop:
            if reason == 'paused':
                logging.info(f"[BackgroundProcessor] Pass 3 paused at cluster {idx + 1}/{total_clusters}")
                wait_result = _wait_while_paused(checkpoint_id, run_id or '')
                if wait_result == 'resumed':
                    logging.info(f"[BackgroundProcessor] Pass 3 resumed")
                elif wait_result == 'timeout':
                    # Save state and exit - can resume later
                    _save_intermediate_results(checkpoint_id, {
                        'pass1_extractions': pass1_results,
                        'pass2_findings': pass2_findings or [],
                    })
                    return None  # Signal to exit thread
                else:  # cancelled
                    logging.info(f"[BackgroundProcessor] Pass 3 cancelled while paused")
                    break
            else:
                logging.info(f"[BackgroundProcessor] Pass 3 stopped: {reason}")
                break

        try:
            _update_checkpoint(checkpoint_id, {
                'current_stage': f'pass3_{cluster_name}',
                'pass3_progress': int((idx / total_clusters) * 100)
            })

            cluster_results = analyze_cluster(
                cluster_name, docs, pass1_results, blueprint, client
            )

            findings = cluster_results.get("cross_doc_findings", [])
            all_cross_doc_findings.extend(findings)
            clusters_status[cluster_name] = {"status": "completed", "findings": len(findings)}

            _update_checkpoint(checkpoint_id, {
                'clusters_processed': clusters_status
            })

        except Exception as e:
            logging.warning(f"[BackgroundProcessor] Pass 3 error for cluster {cluster_name}: {e}")
            clusters_status[cluster_name] = {"status": "error", "error": str(e)}

    return {
        "cross_doc_findings": all_cross_doc_findings,
        "clusters_analyzed": total_clusters,
        "conflicts": [],
        "cascade_analysis": {"cascade_items": []},
        "authorization_issues": [],
        "consent_matrix": []
    }


def _run_pass3_simple(doc_dicts, pass2_findings, blueprint, client):
    """Run simple Pass 3 without clustering."""
    from dd_enhanced.core.pass3_crossdoc import run_pass3_crossdoc_synthesis
    return run_pass3_crossdoc_synthesis(doc_dicts, pass2_findings, blueprint, client, verbose=False)


def _store_findings_to_db(dd_id, run_id, owned_by, doc_dicts, pass4_results, pass3_results, blueprint):
    """Store all findings to database with run_id."""
    try:
        # Convert string UUIDs to UUID objects for database operations
        dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id
        run_uuid = uuid_module.UUID(run_id) if isinstance(run_id, str) else run_id

        logging.info(f"[BackgroundProcessor] _store_findings_to_db called with dd_id={dd_id}, run_id={run_id}, owned_by={owned_by}")

        all_findings = pass4_results.get("all_findings", [])
        cross_doc_findings = pass3_results.get("cross_doc_findings", [])
        logging.info(f"[BackgroundProcessor] Findings to store: {len(all_findings)} per-doc, {len(cross_doc_findings)} cross-doc")

        with transactional_session() as session:
            # Get folders and documents
            folders = session.query(Folder).filter(Folder.dd_id == dd_uuid).all()
            folder_ids = [f.id for f in folders]
            logging.info(f"[BackgroundProcessor] Found {len(folders)} folders")

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()
            logging.info(f"[BackgroundProcessor] Found {len(documents)} documents")

            # Create lookup by filename AND by document ID
            doc_lookup = {doc.original_file_name: doc for doc in documents}
            doc_id_lookup = {str(doc.id): doc for doc in documents}

            # Also create lookup from doc_dicts filename to doc ID for fallback
            doc_dict_lookup = {d.get("filename"): d.get("id") for d in doc_dicts if d.get("filename") and d.get("id")}

            # Get or create member
            member = session.query(DueDiligenceMember).filter(
                DueDiligenceMember.dd_id == dd_uuid,
                DueDiligenceMember.member_email == owned_by
            ).first()

            if not member:
                member = DueDiligenceMember(dd_id=dd_uuid, member_email=owned_by)
                session.add(member)
                session.flush()

            # Get or create perspective
            perspective = session.query(Perspective).filter(
                Perspective.member_id == member.id,
                Perspective.lens == "Enhanced AI Analysis"
            ).first()

            if not perspective:
                perspective = Perspective(member_id=member.id, lens="Enhanced AI Analysis")
                session.add(perspective)
                session.flush()

            # Store findings
            all_findings = pass4_results.get("all_findings", [])
            risk_cache = {}
            stored_count = 0

            for finding in all_findings:
                try:
                    category = finding.get("category", "General")

                    if category not in risk_cache:
                        risk = session.query(PerspectiveRisk).filter(
                            PerspectiveRisk.perspective_id == perspective.id,
                            PerspectiveRisk.category == category
                        ).first()

                        if not risk:
                            risk = PerspectiveRisk(
                                perspective_id=perspective.id,
                                category=category,
                                detail=f"Risks related to {category}"
                            )
                            session.add(risk)
                            session.flush()

                        risk_cache[category] = risk

                    risk = risk_cache[category]

                    # Get document - try multiple lookup strategies
                    source_doc = finding.get("source_document", "")
                    doc = doc_lookup.get(source_doc)

                    # Fallback 1: Try lookup by document ID from finding
                    if not doc and finding.get("document_id"):
                        doc = doc_id_lookup.get(str(finding.get("document_id")))

                    # Fallback 2: Try to find doc ID from doc_dicts by filename, then lookup
                    if not doc and source_doc:
                        doc_id_from_dicts = doc_dict_lookup.get(source_doc)
                        if doc_id_from_dicts:
                            doc = doc_id_lookup.get(doc_id_from_dicts)

                    doc_id = doc.id if doc else None
                    if not doc:
                        logging.debug(f"[BackgroundProcessor] No document match for source_document='{source_doc}'")

                    # Map severity
                    severity = finding.get("severity", "medium")
                    status_map = {"critical": "Red", "high": "Red", "medium": "Amber", "low": "Green"}
                    status = status_map.get(severity.lower(), "Amber")

                    # Extract action_category (from nested structure)
                    action_category_data = finding.get("action_category", {})
                    action_category = action_category_data.get("type") if isinstance(action_category_data, dict) else action_category_data

                    # Extract resolution_path fields
                    resolution_path = finding.get("resolution_path", {})
                    resolution_mechanism = resolution_path.get("mechanism") if isinstance(resolution_path, dict) else None
                    resolution_responsible = resolution_path.get("responsible_party") if isinstance(resolution_path, dict) else None
                    resolution_timeline = resolution_path.get("timeline") if isinstance(resolution_path, dict) else None
                    resolution_description = resolution_path.get("description") if isinstance(resolution_path, dict) else None

                    # Extract resolution cost
                    resolution_cost_data = resolution_path.get("estimated_cost_to_resolve", {}) if isinstance(resolution_path, dict) else {}
                    resolution_cost = resolution_cost_data.get("amount") if isinstance(resolution_cost_data, dict) else None
                    resolution_cost_confidence = resolution_cost_data.get("confidence") if isinstance(resolution_cost_data, dict) else None

                    # Extract confidence fields
                    confidence_data = finding.get("confidence", {})
                    confidence_finding_exists = confidence_data.get("finding_exists") if isinstance(confidence_data, dict) else None
                    confidence_severity = confidence_data.get("severity_correct") if isinstance(confidence_data, dict) else None
                    confidence_amount = confidence_data.get("financial_amount") if isinstance(confidence_data, dict) else None
                    confidence_basis = confidence_data.get("basis") if isinstance(confidence_data, dict) else None
                    confidence_overall = confidence_data.get("overall", 0.85) if isinstance(confidence_data, dict) else 0.85

                    # Extract statutory reference fields
                    statutory_ref = finding.get("statutory_reference", {})
                    statutory_act = statutory_ref.get("act") if isinstance(statutory_ref, dict) else None
                    statutory_section = statutory_ref.get("section") if isinstance(statutory_ref, dict) else None
                    statutory_consequence = statutory_ref.get("consequence") if isinstance(statutory_ref, dict) else None
                    regulatory_body = statutory_ref.get("regulatory_body") if isinstance(statutory_ref, dict) else None

                    # Extract materiality fields (from Phase 2 enrichment)
                    materiality_classification = finding.get("materiality_classification")
                    materiality_ratio = finding.get("materiality_ratio")
                    materiality_threshold = finding.get("materiality_threshold")
                    materiality_qualitative = finding.get("materiality_qualitative_override")

                    # Create finding with run_id and Phase 1 enhancement fields
                    db_finding = PerspectiveRiskFinding(
                        perspective_risk_id=risk.id,
                        document_id=doc_id,
                        run_id=run_uuid,
                        phrase=finding.get("description", "")[:2000],
                        page_number=finding.get("clause_reference", ""),
                        actual_page_number=finding.get("actual_page_number"),  # Integer page from [PAGE X] markers
                        status=status,
                        finding_type=finding.get("finding_type", "negative"),
                        confidence_score=confidence_overall,
                        requires_action=finding.get("deal_impact") in ["deal_blocker", "condition_precedent"],
                        action_priority=_map_priority(finding.get("deal_impact")),
                        direct_answer=finding.get("action_required", "")[:500] if finding.get("action_required") else "",
                        evidence_quote=finding.get("evidence_quote", "")[:500] if finding.get("evidence_quote") else "",
                        deal_impact=finding.get("deal_impact", "none") if finding.get("deal_impact") else "none",
                        clause_reference=finding.get("clause_reference", "")[:100] if finding.get("clause_reference") else None,
                        analysis_pass=finding.get("pass", 2),

                        # Phase 1: Action Category fields
                        action_category=action_category[:50] if action_category else None,
                        resolution_mechanism=resolution_mechanism[:100] if resolution_mechanism else None,
                        resolution_responsible_party=resolution_responsible[:50] if resolution_responsible else None,
                        resolution_timeline=resolution_timeline[:50] if resolution_timeline else None,
                        resolution_cost=resolution_cost,
                        resolution_cost_confidence=resolution_cost_confidence,
                        resolution_description=resolution_description[:2000] if resolution_description else None,

                        # Phase 1: Materiality fields
                        materiality_classification=materiality_classification[:50] if materiality_classification else None,
                        materiality_ratio=materiality_ratio,
                        materiality_threshold=materiality_threshold[:200] if materiality_threshold else None,
                        materiality_qualitative_override=materiality_qualitative[:200] if materiality_qualitative else None,

                        # Phase 1: Confidence fields
                        confidence_finding_exists=confidence_finding_exists,
                        confidence_severity=confidence_severity,
                        confidence_amount=confidence_amount,
                        confidence_basis=confidence_basis[:2000] if confidence_basis else None,

                        # Phase 1: Statutory Reference fields
                        statutory_act=statutory_act[:200] if statutory_act else None,
                        statutory_section=statutory_section[:100] if statutory_section else None,
                        statutory_consequence=statutory_consequence[:2000] if statutory_consequence else None,
                        regulatory_body=regulatory_body[:200] if regulatory_body else None,
                    )
                    session.add(db_finding)
                    stored_count += 1

                except Exception as e:
                    logging.warning(f"[BackgroundProcessor] Could not store finding: {e}")

            # Store cross-doc findings
            cross_doc_findings = pass3_results.get("cross_doc_findings", [])

            cross_doc_risk = session.query(PerspectiveRisk).filter(
                PerspectiveRisk.perspective_id == perspective.id,
                PerspectiveRisk.category == "Cross-Document Analysis"
            ).first()

            if not cross_doc_risk and cross_doc_findings:
                cross_doc_risk = PerspectiveRisk(
                    perspective_id=perspective.id,
                    category="Cross-Document Analysis",
                    detail="Issues identified by analyzing multiple documents together"
                )
                session.add(cross_doc_risk)
                session.flush()

            for finding in cross_doc_findings:
                try:
                    severity = finding.get("severity", "high")
                    status_map = {"critical": "Red", "high": "Red", "medium": "Amber", "low": "Green"}
                    status = status_map.get(severity.lower(), "Amber")

                    db_finding = PerspectiveRiskFinding(
                        perspective_risk_id=cross_doc_risk.id,
                        document_id=None,
                        run_id=run_uuid,
                        phrase=finding.get("description", "")[:2000],
                        page_number=finding.get("clause_reference", ""),
                        status=status,
                        finding_type="conflict",
                        confidence_score=0.9,
                        requires_action=True,
                        action_priority="high",
                        direct_answer=finding.get("action_required", "")[:500] if finding.get("action_required") else "",
                        deal_impact="condition_precedent",
                        cross_doc_source=finding.get("source_document", "")[:200],
                        analysis_pass=3
                    )
                    session.add(db_finding)
                    stored_count += 1

                except Exception as e:
                    logging.warning(f"[BackgroundProcessor] Could not store cross-doc finding: {e}")

            # Update document statuses
            for doc in documents:
                doc.processing_status = 'processed'

            session.commit()
            logging.info(f"[BackgroundProcessor] Successfully stored {stored_count} findings to database")

            return {"stored_count": stored_count}

    except Exception as e:
        logging.exception(f"[BackgroundProcessor] Error storing findings: {e}")
        return {"error": str(e)}


def _map_transaction_type(transaction_type: str) -> str:
    """Map transaction type to blueprint code."""
    mapping = {
        "Mining & Resources": "mining_resources",
        "M&A / Corporate": "ma_corporate",
        "Banking & Finance": "banking_finance",
        "Real Estate": "real_estate",
        "General": "ma_corporate"
    }

    for key, code in mapping.items():
        if key.lower() in transaction_type.lower():
            return code

    return "ma_corporate"


def _classify_doc_type(filename: str, folder) -> str:
    """Classify document type."""
    filename_lower = filename.lower()

    if any(term in filename_lower for term in ['moi', 'memorandum', 'articles']):
        return 'constitutional'
    if any(term in filename_lower for term in ['resolution', 'minutes']):
        return 'governance'
    if any(term in filename_lower for term in ['license', 'permit', 'certificate']):
        return 'regulatory'
    if any(term in filename_lower for term in ['financial', 'audit', 'afs']):
        return 'financial'

    return 'contract'


def _map_priority(deal_impact: str) -> str:
    """Map deal impact to priority."""
    mapping = {
        "deal_blocker": "critical",
        "condition_precedent": "high",
        "price_chip": "medium",
        "warranty_indemnity": "medium",
        "post_closing": "low"
    }
    return mapping.get(deal_impact, "medium")
