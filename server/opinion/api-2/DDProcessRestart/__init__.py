"""
DDProcessRestart - Restart Interrupted DD Processing

Restarts DD processing that was interrupted unexpectedly (server restart, crash, etc.).
Continues from the last saved checkpoint.

Use cases:
- Server crashed or restarted mid-processing
- Azure Functions instance was recycled
- Process was killed unexpectedly
- Status stuck at "processing" with no active thread
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
    Restart interrupted DD processing.

    Query params:
        run_id: The Analysis Run ID (required)

    This endpoint:
    1. Checks if the run was interrupted (status='processing' but no active thread)
    2. Validates there's checkpoint data to resume from
    3. Spawns a new thread to continue from the checkpoint
    """
    try:
        run_id = req.params.get('run_id')

        if not run_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id parameter required"}),
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

        logging.info(f"[DDProcessRestart] Restart request for run: {run_id}")

        # Check if there's already a running thread
        try:
            from DDProcessEnhancedStart import _running_processes
            if run_id in _running_processes:
                thread = _running_processes[run_id]
                if thread.is_alive():
                    return func.HttpResponse(
                        json.dumps({
                            "error": "Processing is already running for this run",
                            "status": "processing",
                            "message": "No restart needed - processing thread is active"
                        }),
                        status_code=409,
                        mimetype="application/json"
                    )
                else:
                    # Clean up dead thread reference
                    del _running_processes[run_id]
        except ImportError:
            pass

        with transactional_session() as session:
            # Find the checkpoint
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.run_id == run_uuid
            ).first()

            # Try to get run from DDAnalysisRun if table exists, but don't fail if it doesn't
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
                    json.dumps({
                        "error": "No checkpoint found for this run",
                        "message": "Cannot restart - no progress was saved. Please start a new run."
                    }),
                    status_code=404,
                    mimetype="application/json"
                )

            current_status = checkpoint.status

            # Check if restart is appropriate
            if current_status == 'completed':
                return func.HttpResponse(
                    json.dumps({
                        "error": "Run already completed",
                        "status": "completed",
                        "message": "Processing finished successfully. No restart needed."
                    }),
                    status_code=409,
                    mimetype="application/json"
                )

            if current_status == 'failed':
                # Check if it was user-cancelled
                if checkpoint.last_error and 'cancelled' in checkpoint.last_error.lower():
                    return func.HttpResponse(
                        json.dumps({
                            "error": "Run was cancelled by user",
                            "status": "cancelled",
                            "message": "This run was manually cancelled. Please start a new run if needed."
                        }),
                        status_code=409,
                        mimetype="application/json"
                    )

            # Capture checkpoint data for restart
            checkpoint_id = str(checkpoint.id)
            dd_id = str(checkpoint.dd_id)
            current_pass = checkpoint.current_pass or 1
            pass1_extractions = checkpoint.pass1_extractions
            pass2_findings = checkpoint.pass2_findings
            processed_doc_ids = checkpoint.processed_doc_ids or []
            documents_processed = checkpoint.documents_processed or 0
            total_documents = checkpoint.total_documents or 0

            # Get selected_doc_ids from run if available, otherwise fetch from checkpoint's dd_id
            selected_doc_ids = []
            if run and run.selected_document_ids:
                selected_doc_ids = run.selected_document_ids
            else:
                # Fallback: get all non-original documents for this DD
                from shared.models import Document, Folder
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

            # Calculate how much progress was saved
            progress_info = {
                "current_pass": current_pass,
                "documents_processed": documents_processed,
                "total_documents": total_documents,
                "has_pass1_data": bool(pass1_extractions),
                "has_pass2_data": bool(pass2_findings),
                "processed_doc_count": len(processed_doc_ids)
            }

            # Reset status to processing
            checkpoint.status = 'processing'
            checkpoint.last_error = None  # Clear any previous error
            checkpoint.last_updated = datetime.datetime.utcnow()

            if run:
                run.status = 'processing'
                run.last_error = None

            session.commit()

        # Spawn new processing thread
        thread_spawned = _spawn_restart_thread(
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
            logging.info(f"[DDProcessRestart] Successfully restarted processing for run: {run_id}")
            return func.HttpResponse(
                json.dumps({
                    "status": "restarted",
                    "run_id": run_id,
                    "dd_id": dd_id,
                    "checkpoint_id": checkpoint_id,
                    "message": "Processing restarted from checkpoint",
                    "progress": progress_info,
                    "poll_url": f"/api/dd-progress-enhanced?run_id={run_id}"
                }),
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({
                    "error": "Failed to spawn restart thread",
                    "message": "Could not start processing thread. Please try again."
                }),
                status_code=500,
                mimetype="application/json"
            )

    except Exception as e:
        logging.exception(f"[DDProcessRestart] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _spawn_restart_thread(
    run_id: str,
    dd_id: str,
    checkpoint_id: str,
    selected_doc_ids: list,
    current_pass: int,
    pass1_extractions: dict,
    pass2_findings: list,
    processed_doc_ids: list
) -> bool:
    """Spawn a new thread to continue processing from checkpoint."""
    try:
        from DDProcessEnhancedStart import _running_processes

        # Import the resume processing function from DDProcessPause
        from DDProcessPause import _run_resume_processing

        logging.info(f"[DDProcessRestart] Spawning thread for run {run_id} from pass {current_pass}")

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

    except Exception as e:
        logging.exception(f"[DDProcessRestart] Error spawning thread: {e}")
        return False
