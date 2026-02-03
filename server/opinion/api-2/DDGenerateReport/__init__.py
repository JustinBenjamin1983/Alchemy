"""
DDGenerateReport - Runs Pass 3-7 (Calculate → Cross-Doc → Aggregate → Synthesize → Verify)

This endpoint is the second part of the split DD pipeline:
1. DDAnalyzeDocuments - Pass 1 + Pass 2 + Create Checkpoint C
2. DDGenerateReport - Pass 3-7 (after user completes Checkpoint C)

Prerequisites:
- DDAnalyzeDocuments must have completed (pass1/pass2 results stored)
- Checkpoint C must be validated by user

POST /api/dd-generate-report?run_id=xxx
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
    DDProcessingCheckpoint, DDAnalysisRun
)
from DDValidationCheckpoint import get_validated_context

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Global dict to track running processes
_running_processes: Dict[str, threading.Thread] = {}


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Start Pass 3-7 report generation for a specific run.

    Prerequisites:
    - Pass 1-2 must be complete (via DDAnalyzeDocuments)
    - Checkpoint C must be validated by user

    Query params:
        run_id: The Analysis Run ID (required)

    Body (optional JSON):
        use_clustered_pass3: bool - Use optimized Pass 3 (default: true)
    """
    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            status_code=403,
            mimetype="application/json"
        )

    try:
        run_id = req.params.get('run_id')
        if not run_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        try:
            uuid_module.UUID(run_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid run_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse options
        options = {}
        try:
            body = req.get_json()
            options = body if isinstance(body, dict) else {}
        except (ValueError, TypeError):
            pass

        use_clustered_pass3 = options.get('use_clustered_pass3', True)

        logging.info(f"[DDGenerateReport] Starting report generation for Run: {run_id}")

        # Check if already processing
        if run_id in _running_processes:
            thread = _running_processes[run_id]
            if thread.is_alive():
                return func.HttpResponse(
                    json.dumps({
                        "error": "Report generation already in progress for this run",
                        "run_id": run_id
                    }),
                    status_code=409,
                    mimetype="application/json"
                )
            else:
                del _running_processes[run_id]

        # Verify prerequisites
        with transactional_session() as session:
            run_uuid = uuid_module.UUID(run_id)

            # Get run
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
            model_tier = run.model_tier or 'balanced'

            # Get checkpoint with stored Pass 1-2 results
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_uuid
            ).first()

            if not checkpoint:
                return func.HttpResponse(
                    json.dumps({
                        "error": "No checkpoint found. Run DDAnalyzeDocuments first.",
                        "run_id": run_id
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check Pass 1-2 completed
            if checkpoint.pass2_progress < 100:
                return func.HttpResponse(
                    json.dumps({
                        "error": "Pass 1-2 not complete. Run DDAnalyzeDocuments first.",
                        "pass1_progress": checkpoint.pass1_progress,
                        "pass2_progress": checkpoint.pass2_progress
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check Checkpoint C validated
            validated_result = get_validated_context(run_id)
            if not validated_result.get("has_validated_context"):
                return func.HttpResponse(
                    json.dumps({
                        "error": "Checkpoint C not validated. Complete the validation wizard first.",
                        "run_id": run_id
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

            # Check if already completed
            if checkpoint.status == 'completed':
                return func.HttpResponse(
                    json.dumps({
                        "status": "already_completed",
                        "message": "Report generation already completed",
                        "run_id": run_id,
                        "checkpoint_id": str(checkpoint.id)
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            # Update status to processing
            checkpoint.status = 'processing'
            checkpoint.current_stage = 'starting_pass3'
            checkpoint.current_pass = 3
            run.status = 'processing'

            session.commit()
            checkpoint_id = str(checkpoint.id)

        # Spawn background thread
        thread = threading.Thread(
            target=_run_report_generation_in_background,
            args=(dd_id_str, run_id, checkpoint_id, selected_doc_ids, use_clustered_pass3, model_tier),
            daemon=True
        )
        thread.start()
        _running_processes[run_id] = thread

        logging.info(f"[DDGenerateReport] Background thread started for Run: {run_id}")

        return func.HttpResponse(
            json.dumps({
                "status": "accepted",
                "message": "Report generation started (Pass 3-7)",
                "run_id": run_id,
                "dd_id": dd_id_str,
                "checkpoint_id": checkpoint_id,
                "poll_url": f"/api/dd-progress-enhanced?run_id={run_id}"
            }),
            status_code=202,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception(f"[DDGenerateReport] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _run_report_generation_in_background(
    dd_id: str,
    run_id: str,
    checkpoint_id: str,
    selected_doc_ids: list,
    use_clustered_pass3: bool,
    model_tier: str = "balanced"
):
    """
    Background worker that runs Pass 3-7.
    Uses stored Pass 1-2 results from checkpoint.
    """
    import sys
    import traceback
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

    from config.blueprints.loader import load_blueprint
    from dd_enhanced.core.claude_client import ClaudeClient, ModelTier
    from dd_enhanced.core.materiality import calculate_materiality_thresholds, apply_materiality_to_findings
    from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis
    from dd_enhanced.core.pass5_verify import run_pass5_verification, apply_verification_adjustments

    # Import shared functions
    from DDProcessEnhancedStart import (
        _load_dd_data_for_processing,
        _run_pass3_clustered_with_progress,
        _run_pass3_simple,
        _update_checkpoint,
        _update_run_status,
        _check_should_stop,
        _store_findings_to_db,
        _create_initial_report_version
    )

    try:
        print(f"\n{'='*60}", flush=True)
        print(f"[DDGenerateReport] STARTING REPORT GENERATION (Pass 3-7)", flush=True)
        print(f"[DDGenerateReport] Run: {run_id}, DD: {dd_id}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # Load stored Pass 1-2 results from checkpoint
        with transactional_session() as session:
            checkpoint_uuid = uuid_module.UUID(checkpoint_id)
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.id == checkpoint_uuid
            ).first()

            if not checkpoint:
                raise ValueError("Checkpoint not found")

            pass1_results = checkpoint.pass1_extractions or {}
            pass2_findings = checkpoint.pass2_findings or []

            print(f"[DDGenerateReport] Loaded Pass 1 results: {len(pass1_results)} extractions", flush=True)
            print(f"[DDGenerateReport] Loaded Pass 2 findings: {len(pass2_findings)} findings", flush=True)

        # Load document data
        print(f"[DDGenerateReport] Loading document data...", flush=True)
        load_result = _load_dd_data_for_processing(dd_id, selected_doc_ids)
        if load_result.get("error"):
            raise ValueError(f"Failed to load data: {load_result['error']}")

        doc_dicts = load_result["doc_dicts"]
        blueprint = load_result["blueprint"]
        transaction_context = load_result["transaction_context"]
        owned_by = load_result["owned_by"]
        transaction_value = load_result.get("transaction_value")

        # Calculate materiality thresholds
        materiality_thresholds = calculate_materiality_thresholds(transaction_value)

        # Initialize Claude client
        tier_map = {
            'cost_optimized': ModelTier.COST_OPTIMIZED,
            'balanced': ModelTier.BALANCED,
            'high_accuracy': ModelTier.HIGH_ACCURACY,
            'maximum_accuracy': ModelTier.MAXIMUM_ACCURACY,
        }
        selected_tier = tier_map.get(model_tier, ModelTier.BALANCED)
        client = ClaudeClient(model_tier=selected_tier)

        print(f"[DDGenerateReport] Using model tier: {selected_tier.value}", flush=True)

        # ===== PASS 3: Cross-Document Analysis =====
        print(f"\n[DDGenerateReport] Pass 3: Cross-document analysis", flush=True)

        _update_checkpoint(checkpoint_id, {
            'current_pass': 3,
            'current_stage': 'pass3_crossdoc',
            'pass2_progress': 100
        })

        try:
            if use_clustered_pass3:
                pass3_results = _run_pass3_clustered_with_progress(
                    doc_dicts, pass1_results, blueprint, client, checkpoint_id, run_id, pass2_findings
                )
            else:
                pass3_results = _run_pass3_simple(
                    doc_dicts, pass2_findings, blueprint, client
                )
                _update_checkpoint(checkpoint_id, {'pass3_progress': 100})

            print(f"[DDGenerateReport] Pass 3 complete: {len(pass3_results.get('cross_doc_findings', []))} findings", flush=True)

        except Exception as pass3_error:
            print(f"[DDGenerateReport] PASS 3 EXCEPTION: {pass3_error}", flush=True)
            print(f"[DDGenerateReport] Traceback:\n{traceback.format_exc()}", flush=True)
            _update_checkpoint(checkpoint_id, {
                'status': 'failed',
                'last_error': f"Pass 3 error: {str(pass3_error)[:800]}"
            })
            _update_run_status(run_id, 'failed', {'last_error': f"Pass 3 error: {str(pass3_error)[:500]}"})
            raise

        if pass3_results is None:
            print(f"[DDGenerateReport] Pass 3 returned None - exiting", flush=True)
            return

        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            print(f"[DDGenerateReport] Stopped after Pass 3: {reason}", flush=True)
            return

        # ===== PASS 4: Synthesis =====
        print(f"\n[DDGenerateReport] Pass 4: Final synthesis", flush=True)

        _update_checkpoint(checkpoint_id, {
            'current_pass': 4,
            'current_stage': 'pass4_synthesis',
            'pass3_progress': 100
        })

        pass4_results = run_pass4_synthesis(
            doc_dicts, pass1_results, pass2_findings, pass3_results, client, verbose=False
        )

        _update_checkpoint(checkpoint_id, {
            'pass4_progress': 100,
            'current_stage': 'storing_findings'
        })

        # Apply materiality classification
        all_findings_for_materiality = pass4_results.get("all_findings", [])
        enriched_findings = apply_materiality_to_findings(all_findings_for_materiality, materiality_thresholds)
        pass4_results["all_findings"] = enriched_findings

        print(f"[DDGenerateReport] Applied materiality to {len(enriched_findings)} findings", flush=True)

        # ===== PASS 7: Verification =====
        print(f"\n[DDGenerateReport] Pass 7: Opus verification", flush=True)

        _update_checkpoint(checkpoint_id, {
            'current_pass': 7,
            'current_stage': 'pass7_verify'
        })

        verification_result = None
        try:
            # Build transaction context string for verification
            transaction_context_str = json.dumps(transaction_context) if isinstance(transaction_context, dict) else str(transaction_context)

            verification_result = run_pass5_verification(
                pass4_results=pass4_results,
                pass3_results=pass3_results,
                pass2_findings=pass2_findings,
                pass1_results=pass1_results,
                calculation_aggregates=None,  # Not available in this flow
                transaction_context=transaction_context_str,
                client=client,
                verbose=True
            )

            if verification_result and not verification_result.error:
                # Apply verification adjustments
                pass4_results = apply_verification_adjustments(pass4_results, verification_result)

                status = "PASSED" if verification_result.verification_passed else "NEEDS REVIEW"
                print(f"[DDGenerateReport] Pass 7 complete: {status} ({verification_result.overall_confidence:.0%} confidence)", flush=True)

                if verification_result.critical_issues:
                    print(f"[DDGenerateReport] Pass 7 found {len(verification_result.critical_issues)} critical issues to review", flush=True)

                _update_checkpoint(checkpoint_id, {
                    'verification_passed': verification_result.verification_passed,
                    'verification_confidence': verification_result.overall_confidence,
                    'critical_issues_count': len(verification_result.critical_issues)
                })
            else:
                error_msg = verification_result.error if verification_result else "No result"
                print(f"[DDGenerateReport] Pass 7 verification had issues: {error_msg}", flush=True)

        except Exception as verify_error:
            print(f"[DDGenerateReport] Pass 7 verification failed (non-fatal): {verify_error}", flush=True)
            # Continue without verification - it's quality assurance, not critical

        # ===== Store findings =====
        print(f"[DDGenerateReport] Storing findings in database", flush=True)

        store_result = _store_findings_to_db(
            dd_id, run_id, owned_by, doc_dicts, pass4_results, pass3_results, blueprint
        )

        if store_result.get("error"):
            print(f"[DDGenerateReport] WARNING: Failed to store findings: {store_result.get('error')}", flush=True)
        else:
            print(f"[DDGenerateReport] Stored {store_result.get('stored_count', 0)} findings", flush=True)

        # Get cost summary
        cost_summary = client.get_cost_summary()

        # Calculate final stats
        all_findings = pass4_results.get("all_findings", [])
        cross_doc_findings = pass3_results.get("cross_doc_findings", [])

        critical = sum(1 for f in all_findings if f.get("severity") == "critical")
        high = sum(1 for f in all_findings if f.get("severity") == "high")
        medium = sum(1 for f in all_findings if f.get("severity") == "medium")
        low = sum(1 for f in all_findings if f.get("severity") == "low")
        deal_blockers = sum(1 for f in all_findings if f.get("deal_impact") == "deal_blocker")
        cps = sum(1 for f in all_findings if f.get("deal_impact") == "condition_precedent")
        total_findings = len(all_findings) + len(cross_doc_findings)

        # Update checkpoint
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

        # Prepare synthesis data
        # Get blueprint_qa from checkpoint if available
        with transactional_session() as session:
            cp = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.id == uuid_module.UUID(checkpoint_id)
            ).first()
            blueprint_qa = []
            if cp and cp.pass2_findings:
                # Blueprint Q&A might be stored with findings
                if isinstance(cp.pass2_findings, dict):
                    blueprint_qa = cp.pass2_findings.get('blueprint_qa', [])

        synthesis_data = {
            'executive_summary': pass4_results.get('executive_summary', ''),
            'deal_assessment': pass4_results.get('deal_assessment', {}),
            'financial_exposures': pass4_results.get('financial_exposures', {}),
            'financial_analysis': pass4_results.get('financial_analysis', {}),
            'deal_blockers': pass4_results.get('deal_blockers', []),
            'conditions_precedent': pass4_results.get('conditions_precedent', []),
            'warranties_register': pass4_results.get('warranties_register', []),
            'indemnities_register': pass4_results.get('indemnities_register', []),
            'recommendations': pass4_results.get('recommendations', []),
            'blueprint_qa': blueprint_qa,
            # Pass 7 verification results
            'verification': pass4_results.get('verification', {}),
            'verified_recommendation': pass4_results.get('verified_recommendation', ''),
            'potential_missing_blockers': pass4_results.get('potential_missing_blockers', []),
            'consistency_issues': pass4_results.get('consistency_issues', []),
        }

        # Update run status
        _update_run_status(run_id, 'completed', {
            'findings_total': total_findings,
            'findings_critical': critical,
            'findings_high': high,
            'findings_medium': medium,
            'findings_low': low,
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'synthesis_data': synthesis_data
        })

        # Create V1 report
        try:
            _create_initial_report_version(run_id, synthesis_data, owned_by)
            print(f"[DDGenerateReport] Created V1 report version", flush=True)
        except Exception as e:
            print(f"[DDGenerateReport] WARNING: Failed to create V1 report: {e}", flush=True)

        print(f"\n{'='*60}", flush=True)
        print(f"[DDGenerateReport] REPORT GENERATION COMPLETE", flush=True)
        print(f"[DDGenerateReport] Total findings: {total_findings}", flush=True)
        print(f"[DDGenerateReport] Cost: ${cost_summary.get('total_cost_usd', 0):.4f}", flush=True)
        print(f"{'='*60}\n", flush=True)

    except Exception as e:
        error_msg = str(e)
        print(f"[DDGenerateReport] EXCEPTION: {error_msg}", flush=True)
        print(f"[DDGenerateReport] Traceback:\n{traceback.format_exc()}", flush=True)

        _update_checkpoint(checkpoint_id, {
            'status': 'failed',
            'last_error': error_msg[:1000]
        })
        _update_run_status(run_id, 'failed', {'last_error': error_msg[:500]})

    finally:
        if run_id in _running_processes:
            del _running_processes[run_id]
