"""
DDProcessPause - Pause/Resume DD Processing

Pauses or resumes an in-progress DD processing job.
Handles both short pauses (< 1 hour, thread still waiting) and
long pauses (> 1 hour, thread exited, needs new thread to continue).
"""
import logging
import os
import json
import datetime
import uuid as uuid_module
import threading

import azure.functions as func

from shared.session import transactional_session
from shared.models import DDProcessingCheckpoint, DDAnalysisRun

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Pause or resume DD processing.

    Query params:
        run_id: The Analysis Run ID (required)
        action: 'pause' or 'resume' (required)
    """
    try:
        run_id = req.params.get('run_id')
        action = req.params.get('action')

        if not run_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        if action not in ('pause', 'resume'):
            return func.HttpResponse(
                json.dumps({"error": "action parameter must be 'pause' or 'resume'"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate UUID format
        try:
            run_uuid = uuid_module.UUID(run_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid run_id format"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"[DDProcessPause] {action.capitalize()} processing for run: {run_id}")

        with transactional_session() as session:
            # Find the checkpoint
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_uuid
            ).first()

            # Try to get run from DDAnalysisRun if table exists
            run = None
            try:
                run = session.query(DDAnalysisRun).filter(
                    DDAnalysisRun.id == run_uuid
                ).first()
            except Exception:
                # DDAnalysisRun table may not exist - continue without it
                pass

            if not checkpoint:
                return func.HttpResponse(
                    json.dumps({"error": "No processing checkpoint found for this run"}),
                    status_code=404,
                    mimetype="application/json"
                )

            current_status = checkpoint.status

            if action == 'pause':
                if current_status != 'processing':
                    return func.HttpResponse(
                        json.dumps({
                            "error": f"Cannot pause - processing is '{current_status}'",
                            "status": current_status
                        }),
                        status_code=409,
                        mimetype="application/json"
                    )

                # Update to paused
                checkpoint.status = 'paused'
                checkpoint.last_updated = datetime.datetime.utcnow()
                if run:
                    run.status = 'paused'

                message = "Processing paused successfully"
                needs_thread_spawn = False

            else:  # resume
                if current_status != 'paused':
                    return func.HttpResponse(
                        json.dumps({
                            "error": f"Cannot resume - processing is '{current_status}'",
                            "status": current_status
                        }),
                        status_code=409,
                        mimetype="application/json"
                    )

                # Update back to processing
                checkpoint.status = 'processing'
                checkpoint.last_updated = datetime.datetime.utcnow()
                if run:
                    run.status = 'processing'

                # Capture checkpoint data for potential thread spawn
                checkpoint_id = str(checkpoint.id)
                dd_id = str(checkpoint.dd_id)
                current_pass = checkpoint.current_pass
                pass1_extractions = checkpoint.pass1_extractions
                pass2_findings = checkpoint.pass2_findings
                processed_doc_ids = checkpoint.processed_doc_ids or []

                # Get selected_doc_ids from run if available, otherwise fetch from DD
                selected_doc_ids = []
                if run and run.selected_document_ids:
                    selected_doc_ids = run.selected_document_ids
                else:
                    # Fallback: get all non-original documents for this DD
                    from sqlalchemy import text
                    doc_query = text("""
                        SELECT d.id::text
                        FROM document d
                        JOIN folder f ON d.folder_id = f.id
                        WHERE f.dd_id = :dd_id
                        AND d.is_original = false
                    """)
                    doc_results = session.execute(doc_query, {"dd_id": dd_id}).fetchall()
                    selected_doc_ids = [row[0] for row in doc_results]

                message = "Processing resumed successfully"
                needs_thread_spawn = True

            session.commit()

            logging.info(f"[DDProcessPause] {action.capitalize()} successful for run: {run_id}")

            # If resuming, check if we need to spawn a new processing thread
            if action == 'resume' and needs_thread_spawn:
                thread_spawned = _spawn_resume_thread_if_needed(
                    run_id=run_id,
                    dd_id=dd_id,
                    checkpoint_id=checkpoint_id,
                    selected_doc_ids=selected_doc_ids,
                    current_pass=current_pass,
                    pass1_extractions=pass1_extractions,
                    pass2_findings=pass2_findings,
                    processed_doc_ids=processed_doc_ids
                )
                if thread_spawned:
                    message = "Processing resumed (new thread spawned after long pause)"

            return func.HttpResponse(
                json.dumps({
                    "status": "processing" if action == 'resume' else "paused",
                    "run_id": run_id,
                    "dd_id": dd_id if action == 'resume' else str(checkpoint.dd_id),
                    "message": message
                }),
                mimetype="application/json"
            )

    except Exception as e:
        logging.exception(f"[DDProcessPause] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _spawn_resume_thread_if_needed(
    run_id: str,
    dd_id: str,
    checkpoint_id: str,
    selected_doc_ids: list,
    current_pass: int,
    pass1_extractions: dict,
    pass2_findings: list,
    processed_doc_ids: list
) -> bool:
    """
    Check if a processing thread exists for this run_id.
    If not (thread exited after 1hr pause), spawn a new thread to continue from checkpoint.

    Returns True if a new thread was spawned, False if existing thread will handle it.
    """
    try:
        # Import the running processes dict from DDProcessEnhancedStart
        from DDProcessEnhancedStart import _running_processes

        # Check if there's already a running thread
        if run_id in _running_processes:
            thread = _running_processes[run_id]
            if thread.is_alive():
                # Thread is still running, it will pick up the status change
                logging.info(f"[DDProcessPause] Thread still alive for run {run_id}, will resume automatically")
                return False
            else:
                # Thread died, clean up
                del _running_processes[run_id]

        # No running thread - spawn a new one to continue from checkpoint
        logging.info(f"[DDProcessPause] Spawning new thread to continue processing for run {run_id} from pass {current_pass}")

        thread = threading.Thread(
            target=_run_resume_processing,
            args=(
                dd_id, run_id, checkpoint_id, selected_doc_ids,
                current_pass, pass1_extractions, pass2_findings, processed_doc_ids
            ),
            daemon=True
        )
        thread.start()
        _running_processes[run_id] = thread

        return True

    except ImportError:
        # Can't import - just log and continue (thread might pick it up)
        logging.warning(f"[DDProcessPause] Could not import _running_processes, assuming thread will resume")
        return False
    except Exception as e:
        logging.exception(f"[DDProcessPause] Error spawning resume thread: {e}")
        return False


def _run_resume_processing(
    dd_id: str,
    run_id: str,
    checkpoint_id: str,
    selected_doc_ids: list,
    current_pass: int,
    pass1_extractions: dict,
    pass2_findings: list,
    processed_doc_ids: list
):
    """
    Resume processing from checkpoint state.
    Continues from where the previous thread left off.
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

    from DDProcessEnhancedStart import (
        _update_checkpoint, _update_run_status, _check_should_stop,
        _load_dd_data_for_processing, _run_pass1_with_progress,
        _run_pass2_with_progress, _run_pass3_clustered_with_progress,
        _run_pass3_simple, _store_findings_to_db, _running_processes
    )
    from shared.dev_adapters.dev_config import get_dev_config
    from config.blueprints.loader import load_blueprint
    from dd_enhanced.core.claude_client import ClaudeClient
    from dd_enhanced.core.question_prioritizer import prioritize_questions

    try:
        logging.info(f"[DDProcessPause] Resume processing for Run: {run_id}, starting from pass {current_pass}")

        # Load DD data
        load_result = _load_dd_data_for_processing(dd_id, selected_doc_ids)
        if load_result.get("error"):
            _update_checkpoint(checkpoint_id, {
                'status': 'failed',
                'last_error': load_result["error"]
            })
            return

        doc_dicts = load_result["doc_dicts"]
        blueprint = load_result["blueprint"]
        transaction_context = load_result["transaction_context"]
        transaction_context_str = load_result["transaction_context_str"]
        reference_docs = load_result["reference_docs"]
        owned_by = load_result["owned_by"]

        total_docs = len(doc_dicts)
        client = ClaudeClient()

        # Filter out already-processed documents if we have checkpoint data
        remaining_doc_dicts = doc_dicts
        if processed_doc_ids:
            remaining_doc_dicts = [d for d in doc_dicts if d.get("id") not in processed_doc_ids]
            logging.info(f"[DDProcessPause] Resuming with {len(remaining_doc_dicts)} remaining docs (of {total_docs} total)")

        # Resume from the appropriate pass
        if current_pass <= 1:
            # Still in Pass 1 - continue extraction
            _update_checkpoint(checkpoint_id, {'current_stage': 'pass1_extraction'})

            additional_results = _run_pass1_with_progress(
                remaining_doc_dicts, client, checkpoint_id, len(remaining_doc_dicts), run_id
            )

            if additional_results is None:
                logging.info(f"[DDProcessPause] Thread exiting after Pass 1 pause timeout")
                return

            # Merge with existing results
            if pass1_extractions:
                for key in ["key_dates", "financial_figures", "coc_clauses", "consent_requirements", "key_parties"]:
                    pass1_extractions.setdefault(key, []).extend(additional_results.get(key, []))
                pass1_extractions.get("document_summaries", {}).update(additional_results.get("document_summaries", {}))
            else:
                pass1_extractions = additional_results

            current_pass = 2

        # Pass 2: Per-document analysis
        if current_pass <= 2:
            prioritized_questions = prioritize_questions(
                blueprint=blueprint,
                transaction_context=transaction_context,
                include_tier3=False,
                max_questions=150
            )
            total_questions = sum(len(q.get("questions", [])) for q in prioritized_questions)

            _update_checkpoint(checkpoint_id, {
                'current_pass': 2,
                'current_stage': 'pass2_analysis',
                'pass1_progress': 100,
                'total_questions': total_questions
            })

            # Filter docs that weren't processed in Pass 2
            docs_for_pass2 = remaining_doc_dicts if current_pass < 2 else doc_dicts
            if pass2_findings and current_pass == 2:
                # Some Pass 2 was done, only process remaining
                processed_filenames = {f.get("source_document") for f in pass2_findings if f.get("source_document")}
                docs_for_pass2 = [d for d in doc_dicts if d.get("filename") not in processed_filenames]

            new_findings = _run_pass2_with_progress(
                docs_for_pass2, reference_docs, blueprint, client, checkpoint_id,
                transaction_context_str, prioritized_questions, len(docs_for_pass2), run_id,
                pass1_extractions
            )

            if new_findings is None:
                logging.info(f"[DDProcessPause] Thread exiting after Pass 2 pause timeout")
                return

            # Merge findings
            if pass2_findings:
                pass2_findings.extend(new_findings)
            else:
                pass2_findings = new_findings

            current_pass = 3

        # Check if cancelled
        should_stop, reason = _check_should_stop(checkpoint_id)
        if should_stop and reason in ('cancelled', 'failed'):
            logging.info(f"[DDProcessPause] Stopped: {reason}")
            return

        # Pass 3: Cross-document analysis
        if current_pass <= 3:
            _update_checkpoint(checkpoint_id, {
                'current_pass': 3,
                'current_stage': 'pass3_crossdoc',
                'pass2_progress': 100
            })

            pass3_results = _run_pass3_clustered_with_progress(
                doc_dicts, pass1_extractions, blueprint, client, checkpoint_id, run_id, pass2_findings
            )

            if pass3_results is None:
                logging.info(f"[DDProcessPause] Thread exiting after Pass 3 pause timeout")
                return

            current_pass = 4
        else:
            pass3_results = {"cross_doc_findings": [], "clusters_analyzed": 0, "conflicts": [],
                           "cascade_analysis": {"cascade_items": []}, "authorization_issues": [], "consent_matrix": []}

        # Pass 4: Synthesis
        _update_checkpoint(checkpoint_id, {
            'current_pass': 4,
            'current_stage': 'pass4_synthesis',
            'pass3_progress': 100
        })

        from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis
        pass4_results = run_pass4_synthesis(
            doc_dicts, pass1_extractions, pass2_findings, pass3_results, client, verbose=False
        )

        _update_checkpoint(checkpoint_id, {
            'pass4_progress': 100,
            'current_stage': 'storing_findings'
        })

        # Store findings
        _store_findings_to_db(
            dd_id, run_id, owned_by, doc_dicts, pass4_results, pass3_results, blueprint
        )

        # Get cost summary
        cost_summary = client.get_cost_summary()

        # Final stats
        all_findings = pass4_results.get("all_findings", [])
        cross_doc_findings = pass3_results.get("cross_doc_findings", [])

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

        _update_run_status(run_id, 'completed', {
            'findings_total': total_findings,
            'findings_critical': critical,
            'findings_high': high,
            'findings_medium': medium,
            'findings_low': low,
            'estimated_cost_usd': cost_summary['total_cost_usd']
        })

        logging.info(f"[DDProcessPause] Resume processing complete for Run: {run_id}")

    except Exception as e:
        logging.exception(f"[DDProcessPause] Error in resume processing: {e}")
        _update_checkpoint(checkpoint_id, {
            'status': 'failed',
            'last_error': str(e)[:1000]
        })
        _update_run_status(run_id, 'failed', {'last_error': str(e)[:1000]})

    finally:
        # Clean up thread reference
        if run_id in _running_processes:
            del _running_processes[run_id]
