"""
DD Progress Enhanced Endpoint

Provides real-time processing progress for the DD Processing Dashboard.
Reads from the dd_processing_checkpoint table.
"""
import azure.functions as func
import json
from datetime import datetime
from shared.session import transactional_session
from shared.models import DueDiligence
from sqlalchemy import text


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get real-time processing progress for a DD.

    Query params:
        dd_id: UUID of the due diligence
    """
    try:
        dd_id = req.params.get("dd_id")

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        with transactional_session() as session:
            # Get checkpoint data
            checkpoint_query = text("""
                SELECT
                    id,
                    dd_id,
                    current_pass,
                    current_stage,
                    status,
                    pass1_extractions,
                    documents_processed,
                    total_documents,
                    clusters_processed,
                    questions_processed,
                    total_questions,
                    pass1_progress,
                    pass2_progress,
                    pass3_progress,
                    pass4_progress,
                    current_document_id,
                    current_document_name,
                    current_question,
                    findings_total,
                    findings_critical,
                    findings_high,
                    findings_medium,
                    findings_low,
                    findings_deal_blockers,
                    findings_cps,
                    clusters_total,
                    total_input_tokens,
                    total_output_tokens,
                    estimated_cost_usd,
                    cost_by_model,
                    started_at,
                    last_updated,
                    completed_at,
                    last_error,
                    retry_count
                FROM dd_processing_checkpoint
                WHERE dd_id = :dd_id
            """)

            result = session.execute(checkpoint_query, {"dd_id": dd_id}).fetchone()

            if not result:
                # Check if DD exists but no checkpoint record exists
                # This happens when DDProcessAllDev was used instead of DDProcessEnhanced
                dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
                if not dd:
                    return func.HttpResponse(
                        json.dumps({"error": "DD not found"}),
                        status_code=404,
                        mimetype="application/json"
                    )

                # Even without a checkpoint, we should still show:
                # 1. Document statuses from the document table
                # 2. Finding counts from perspective_risk_finding
                # This makes the dashboard work with DDProcessAllDev processed data

                # Get document statuses
                doc_query = text("""
                    SELECT
                        d.id::text,
                        d.original_file_name as filename,
                        d.type as doc_type,
                        d.processing_status,
                        CASE
                            WHEN d.processing_status IN ('completed', 'processed') THEN 'completed'
                            WHEN d.processing_status = 'processing' THEN 'processing'
                            WHEN d.processing_status = 'error' THEN 'error'
                            ELSE 'queued'
                        END as status
                    FROM document d
                    JOIN folder f ON d.folder_id = f.id
                    WHERE f.dd_id = :dd_id
                    ORDER BY d.uploaded_at
                """)
                doc_results = session.execute(doc_query, {"dd_id": dd_id}).fetchall()

                documents = []
                docs_completed = 0
                total_docs = 0
                for doc in doc_results:
                    total_docs += 1
                    doc_status = doc.status
                    if doc_status == 'completed':
                        docs_completed += 1
                    documents.append({
                        "id": doc.id,
                        "filename": doc.filename,
                        "doc_type": doc.doc_type or "other",
                        "status": doc_status
                    })

                # Get finding counts - use status field which contains 'Red', 'Amber', 'Green'
                # Note: DDProcessAllDev maps severity->status as: high->Red, medium->Amber, low->Green
                finding_query = text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE prf.status = 'Red') as critical,
                        COUNT(*) FILTER (WHERE prf.status = 'Amber' OR prf.status = 'New') as high,
                        COUNT(*) FILTER (WHERE prf.action_priority = 'medium') as medium,
                        COUNT(*) FILTER (WHERE prf.status = 'Green' OR prf.status = 'Info') as low,
                        COUNT(*) FILTER (WHERE prf.deal_impact = 'deal_blocker') as deal_blockers,
                        COUNT(*) FILTER (WHERE prf.deal_impact = 'condition_precedent' OR prf.requires_action = true) as conditions_precedent
                    FROM perspective_risk_finding prf
                    JOIN perspective_risk pr ON prf.perspective_risk_id = pr.id
                    JOIN perspective p ON pr.perspective_id = p.id
                    JOIN due_diligence_member ddm ON p.member_id = ddm.id
                    WHERE ddm.dd_id = :dd_id
                    AND prf.status != 'Deleted'
                """)
                finding_counts_row = session.execute(finding_query, {"dd_id": dd_id}).fetchone()

                finding_counts = {
                    "total": finding_counts_row.total if finding_counts_row else 0,
                    "critical": finding_counts_row.critical if finding_counts_row else 0,
                    "high": finding_counts_row.high if finding_counts_row else 0,
                    "medium": finding_counts_row.medium if finding_counts_row else 0,
                    "low": finding_counts_row.low if finding_counts_row else 0,
                    "deal_blockers": finding_counts_row.deal_blockers if finding_counts_row else 0,
                    "conditions_precedent": finding_counts_row.conditions_precedent if finding_counts_row else 0
                }

                # Determine status based on what we have:
                # - If we have findings -> completed (processed via DDProcessAllDev)
                # - If we have docs but no findings -> pending
                has_findings = finding_counts["total"] > 0
                all_docs_processed = docs_completed == total_docs and total_docs > 0

                if has_findings and all_docs_processed:
                    status = "completed"
                    pass_progress = {
                        "extract": {"status": "completed", "progress": 100, "items_processed": total_docs, "total_items": total_docs},
                        "analyze": {"status": "completed", "progress": 100, "items_processed": total_docs, "total_items": total_docs},
                        "crossdoc": {"status": "completed", "progress": 100, "items_processed": 1, "total_items": 1},
                        "synthesize": {"status": "completed", "progress": 100, "items_processed": 1, "total_items": 1}
                    }
                    current_pass = "synthesize"
                elif has_findings:
                    # Some findings but maybe still processing
                    status = "processing"
                    progress_pct = int((docs_completed / max(total_docs, 1)) * 100)
                    pass_progress = {
                        "extract": {"status": "completed", "progress": 100, "items_processed": total_docs, "total_items": total_docs},
                        "analyze": {"status": "processing", "progress": progress_pct, "items_processed": docs_completed, "total_items": total_docs},
                        "crossdoc": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "synthesize": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1}
                    }
                    current_pass = "analyze"
                else:
                    status = "pending"
                    pass_progress = {
                        "extract": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": total_docs},
                        "analyze": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": total_docs},
                        "crossdoc": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "synthesize": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1}
                    }
                    current_pass = None

                return func.HttpResponse(
                    json.dumps({
                        "dd_id": dd_id,
                        "status": status,
                        "current_pass": current_pass,
                        "current_stage": None,
                        "pass_progress": pass_progress,
                        "documents": documents,
                        "documents_processed": docs_completed,
                        "total_documents": total_docs,
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "estimated_cost_usd": 0,
                        "finding_counts": finding_counts,
                        "started_at": None,
                        "elapsed_seconds": 0,
                        "retry_count": 0
                    }),
                    mimetype="application/json"
                )

            # Map current_pass to our pass names
            pass_mapping = {
                1: "extract",
                2: "analyze",
                3: "crossdoc",
                4: "synthesize"
            }

            current_pass_num = result.current_pass or 1
            current_pass = pass_mapping.get(current_pass_num, "extract")

            # Calculate elapsed time
            started_at = result.started_at
            elapsed_seconds = 0
            if started_at:
                elapsed_seconds = int((datetime.utcnow() - started_at).total_seconds())

            # Build pass progress based on current state
            # Use granular progress fields if available
            pass_progress = {}

            # Helper to get progress value safely
            def get_progress(field_name, default=0):
                val = getattr(result, field_name, None) if hasattr(result, field_name) else None
                return val if val is not None else default

            pass1_prog = get_progress('pass1_progress', 0)
            pass2_prog = get_progress('pass2_progress', 0)
            pass3_prog = get_progress('pass3_progress', 0)
            pass4_prog = get_progress('pass4_progress', 0)

            total_docs = result.total_documents or 0
            docs_processed = result.documents_processed or 0
            clusters_total = get_progress('clusters_total', 1)

            for pass_num, pass_name in pass_mapping.items():
                if current_pass_num > pass_num:
                    # Completed pass
                    pass_progress[pass_name] = {
                        "status": "completed",
                        "progress": 100,
                        "items_processed": total_docs if pass_name in ["extract", "analyze"] else clusters_total,
                        "total_items": total_docs if pass_name in ["extract", "analyze"] else clusters_total
                    }
                elif current_pass_num == pass_num:
                    # Current pass - use granular progress
                    if pass_name == "extract":
                        progress = pass1_prog
                        items_processed = docs_processed
                        total_items = total_docs
                    elif pass_name == "analyze":
                        progress = pass2_prog
                        items_processed = docs_processed
                        total_items = total_docs
                    elif pass_name == "crossdoc":
                        progress = pass3_prog
                        # Get cluster progress
                        clusters = result.clusters_processed or {}
                        if isinstance(clusters, dict):
                            items_processed = len([c for c in clusters.values() if isinstance(c, dict) and c.get("status") == "completed"])
                            total_items = clusters_total if clusters_total > 0 else len(clusters) or 1
                        else:
                            items_processed = 0
                            total_items = clusters_total or 1
                    elif pass_name == "synthesize":
                        progress = pass4_prog
                        items_processed = 1 if pass4_prog > 0 else 0
                        total_items = 1

                    pass_progress[pass_name] = {
                        "status": "processing" if result.status == "processing" else "pending",
                        "progress": progress,
                        "items_processed": items_processed,
                        "total_items": total_items
                    }
                else:
                    # Future pass
                    pass_progress[pass_name] = {
                        "status": "pending",
                        "progress": 0,
                        "items_processed": 0,
                        "total_items": total_docs if pass_name in ["extract", "analyze"] else clusters_total or 1
                    }

            # Get finding counts from perspective_risk_finding via the membership chain
            # Status field contains: 'Red', 'Amber', 'Green', 'New', 'Info'
            # DDProcessAllDev maps: high->Red, medium->Amber, low->Green
            finding_query = text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE prf.status = 'Red') as critical,
                    COUNT(*) FILTER (WHERE prf.status = 'Amber' OR prf.status = 'New') as high,
                    COUNT(*) FILTER (WHERE prf.action_priority = 'medium') as medium,
                    COUNT(*) FILTER (WHERE prf.status = 'Green' OR prf.status = 'Info') as low,
                    COUNT(*) FILTER (WHERE prf.deal_impact = 'deal_blocker') as deal_blockers,
                    COUNT(*) FILTER (WHERE prf.deal_impact = 'condition_precedent' OR prf.requires_action = true) as conditions_precedent
                FROM perspective_risk_finding prf
                JOIN perspective_risk pr ON prf.perspective_risk_id = pr.id
                JOIN perspective p ON pr.perspective_id = p.id
                JOIN due_diligence_member ddm ON p.member_id = ddm.id
                WHERE ddm.dd_id = :dd_id
                AND prf.status != 'Deleted'
            """)

            finding_counts_row = session.execute(finding_query, {"dd_id": dd_id}).fetchone()

            finding_counts = {
                "total": finding_counts_row.total if finding_counts_row else 0,
                "critical": finding_counts_row.critical if finding_counts_row else 0,
                "high": finding_counts_row.high if finding_counts_row else 0,
                "medium": finding_counts_row.medium if finding_counts_row else 0,
                "low": finding_counts_row.low if finding_counts_row else 0,
                "deal_blockers": finding_counts_row.deal_blockers if finding_counts_row else 0,
                "conditions_precedent": finding_counts_row.conditions_precedent if finding_counts_row else 0
            }

            # Get document statuses from the document table via folder
            doc_query = text("""
                SELECT
                    d.id::text,
                    d.original_file_name as filename,
                    d.type as doc_type,
                    CASE
                        WHEN d.processing_status = 'completed' THEN 'completed'
                        WHEN d.processing_status = 'processing' THEN 'processing'
                        WHEN d.processing_status = 'error' THEN 'error'
                        ELSE 'queued'
                    END as status
                FROM document d
                JOIN folder f ON d.folder_id = f.id
                WHERE f.dd_id = :dd_id
                ORDER BY d.uploaded_at
            """)

            doc_results = session.execute(doc_query, {"dd_id": dd_id}).fetchall()
            documents = []
            for doc in doc_results:
                documents.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "doc_type": doc.doc_type or "other",
                    "status": doc.status
                })

            # Use checkpoint finding counts if available (real-time during processing)
            # Fall back to database query for completed processing
            checkpoint_findings_total = get_progress('findings_total', 0)
            if checkpoint_findings_total > 0:
                finding_counts = {
                    "total": checkpoint_findings_total,
                    "critical": get_progress('findings_critical', 0),
                    "high": get_progress('findings_high', 0),
                    "medium": get_progress('findings_medium', 0),
                    "low": get_progress('findings_low', 0),
                    "deal_blockers": get_progress('findings_deal_blockers', 0),
                    "conditions_precedent": get_progress('findings_cps', 0)
                }

            # Get current document being processed
            current_document_name = None
            try:
                current_document_name = result.current_document_name
            except AttributeError:
                pass

            # Build response
            response_data = {
                "dd_id": dd_id,
                "status": result.status or "pending",
                "current_pass": current_pass,
                "current_stage": result.current_stage,
                "current_document_name": current_document_name,
                "pass_progress": pass_progress,
                "documents": documents,
                "documents_processed": result.documents_processed or 0,
                "total_documents": result.total_documents or 0,
                "total_input_tokens": result.total_input_tokens or 0,
                "total_output_tokens": result.total_output_tokens or 0,
                "estimated_cost_usd": float(result.estimated_cost_usd or 0),
                "finding_counts": finding_counts,
                "started_at": started_at.isoformat() if started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "elapsed_seconds": elapsed_seconds,
                "last_error": result.last_error,
                "retry_count": result.retry_count or 0
            }

            return func.HttpResponse(
                json.dumps(response_data),
                mimetype="application/json"
            )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
