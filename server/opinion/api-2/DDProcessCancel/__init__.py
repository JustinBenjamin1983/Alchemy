"""
DDProcessCancel - Cancel DD Processing

Cancels an in-progress DD processing job by updating the checkpoint and run status.
Also supports cancelling document classification/organisation.
Supports both run_id (preferred) and dd_id (legacy) parameters.
"""
import logging
import os
import json
import datetime
import uuid as uuid_module

import azure.functions as func

from shared.session import transactional_session
from shared.models import DDProcessingCheckpoint, DDAnalysisRun, DDOrganisationStatus

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Cancel DD processing.

    Query params:
        run_id: The Analysis Run ID (preferred)
        dd_id: The DD project ID (legacy fallback - cancels most recent processing run)
    """
    try:
        run_id = req.params.get('run_id')
        dd_id = req.params.get('dd_id')

        if not run_id and not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id or dd_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(f"[DDProcessCancel] Cancelling processing - run_id: {run_id}, dd_id: {dd_id}")

        with transactional_session() as session:
            checkpoint = None
            run = None

            if run_id:
                # Find by run_id (preferred)
                try:
                    run_uuid = uuid_module.UUID(run_id)
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid run_id format"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                checkpoint = session.query(DDProcessingCheckpoint).filter(
                    DDProcessingCheckpoint.run_id == run_uuid
                ).first()

                run = session.query(DDAnalysisRun).filter(
                    DDAnalysisRun.id == run_uuid
                ).first()

            elif dd_id:
                # Legacy: find most recent processing checkpoint for dd_id
                try:
                    dd_uuid = uuid_module.UUID(dd_id)
                except ValueError:
                    return func.HttpResponse(
                        json.dumps({"error": "Invalid dd_id format"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                checkpoint = session.query(DDProcessingCheckpoint).filter(
                    DDProcessingCheckpoint.dd_id == dd_uuid,
                    DDProcessingCheckpoint.status == 'processing'
                ).order_by(DDProcessingCheckpoint.started_at.desc()).first()

                if checkpoint and checkpoint.run_id:
                    run = session.query(DDAnalysisRun).filter(
                        DDAnalysisRun.id == checkpoint.run_id
                    ).first()

            # Track what was cancelled
            cancelled_processing = False
            cancelled_organisation = False
            result_dd_id = None

            # Cancel processing checkpoint if found
            if checkpoint:
                if checkpoint.status in ('processing', 'pending'):
                    checkpoint.status = 'failed'
                    checkpoint.last_error = 'Cancelled by user'
                    checkpoint.last_updated = datetime.datetime.utcnow()
                    cancelled_processing = True
                    result_dd_id = str(checkpoint.dd_id)

                    # Also update the run status if we have one
                    if run:
                        run.status = 'failed'
                        run.last_error = 'Cancelled by user'

            # Also check for and cancel organisation status
            org_dd_id = dd_id or (str(checkpoint.dd_id) if checkpoint else None)
            if org_dd_id:
                try:
                    org_uuid = uuid_module.UUID(org_dd_id)
                    org_status = session.query(DDOrganisationStatus).filter(
                        DDOrganisationStatus.dd_id == org_uuid
                    ).first()

                    if org_status and org_status.status in ('classifying', 'organising'):
                        org_status.status = 'cancelled'
                        org_status.error_message = 'Cancelled by user'
                        org_status.updated_at = datetime.datetime.utcnow()
                        cancelled_organisation = True
                        result_dd_id = org_dd_id
                        logging.info(f"[DDProcessCancel] Cancelled organisation for dd_id: {org_dd_id}")
                except Exception as org_err:
                    logging.warning(f"[DDProcessCancel] Error cancelling organisation: {org_err}")

            if not cancelled_processing and not cancelled_organisation:
                return func.HttpResponse(
                    json.dumps({"error": "No active processing or classification found to cancel"}),
                    status_code=404,
                    mimetype="application/json"
                )

            session.commit()

            result_run_id = str(run.id) if run else None
            logging.info(f"[DDProcessCancel] Successfully cancelled - run: {result_run_id}, org: {cancelled_organisation}")

            return func.HttpResponse(
                json.dumps({
                    "status": "cancelled",
                    "run_id": result_run_id,
                    "dd_id": result_dd_id,
                    "cancelled_processing": cancelled_processing,
                    "cancelled_organisation": cancelled_organisation,
                    "message": "Cancelled successfully"
                }),
                mimetype="application/json"
            )

    except Exception as e:
        logging.exception(f"[DDProcessCancel] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
