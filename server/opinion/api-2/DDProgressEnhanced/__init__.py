"""
DD Progress Enhanced Endpoint

Provides real-time processing progress for the DD Processing Dashboard.
Reads from the dd_processing_checkpoint table.

PHASE 6: Extended to support parallel processing with:
- Processing mode (sequential/parallel)
- Worker utilization
- Documents from cache (incremental processing)
- Failed document tracking
- Hierarchical synthesis progress
"""
import azure.functions as func
import json
from datetime import datetime
from shared.session import transactional_session
from shared.models import DueDiligence, Folder
from shared.document_selector import get_processable_documents
from sqlalchemy import text


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get real-time processing progress for a DD run.

    Query params:
        run_id: UUID of the analysis run (preferred)
        dd_id: UUID of the due diligence (fallback for legacy)
    """
    try:
        run_id = req.params.get("run_id")
        dd_id = req.params.get("dd_id")

        if not run_id and not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "run_id or dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        with transactional_session() as session:
            # Build query based on whether we have run_id or dd_id
            if run_id:
                checkpoint_query = text("""
                    SELECT
                        id,
                        dd_id,
                        run_id,
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
                        retry_count,
                        compression_enabled,
                        batching_enabled,
                        total_batches,
                        batches_completed,
                        compression_stats,
                        batch_stats,
                        graph_vertices,
                        graph_edges,
                        processing_mode,
                        parallel_workers,
                        documents_from_cache,
                        documents_failed,
                        failed_documents,
                        partial_results,
                        previous_run_id,
                        synthesis_progress,
                        synthesis_level
                    FROM dd_processing_checkpoint
                    WHERE run_id = :run_id
                """)
                result = session.execute(checkpoint_query, {"run_id": run_id}).fetchone()
            else:
                # Legacy: query by dd_id (gets most recent checkpoint)
                checkpoint_query = text("""
                    SELECT
                        id,
                        dd_id,
                        run_id,
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
                        retry_count,
                        compression_enabled,
                        batching_enabled,
                        total_batches,
                        batches_completed,
                        compression_stats,
                        batch_stats,
                        graph_vertices,
                        graph_edges,
                        processing_mode,
                        parallel_workers,
                        documents_from_cache,
                        documents_failed,
                        failed_documents,
                        partial_results,
                        previous_run_id,
                        synthesis_progress,
                        synthesis_level
                    FROM dd_processing_checkpoint
                    WHERE dd_id = :dd_id
                    ORDER BY started_at DESC
                    LIMIT 1
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

                # Get document statuses using smart selection (avoids counting duplicates)
                documents = _get_processable_documents_for_progress(session, dd_id)
                total_docs = len(documents)
                docs_completed = sum(1 for d in documents if d['status'] == 'completed')

                # Get finding counts - MUST match RiskSummary.tsx severity mapping exactly:
                #   - critical: action_priority = 'critical'
                #   - high: status = 'Red' AND action_priority != 'critical', OR action_priority = 'high', OR finding_type = 'negative'
                #   - medium: status = 'Amber'
                #   - positive: status = 'Green' OR finding_type = 'positive'
                #   - gap: finding_type = 'gap' OR status = 'Info'
                #   - low: finding_type IN ('neutral', 'informational')
                finding_query = text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE prf.action_priority = 'critical') as critical,
                        COUNT(*) FILTER (WHERE (prf.status = 'Red' AND prf.action_priority != 'critical') OR prf.action_priority = 'high' OR (prf.finding_type = 'negative' AND prf.status != 'Red')) as high,
                        COUNT(*) FILTER (WHERE prf.status = 'Amber') as medium,
                        COUNT(*) FILTER (WHERE prf.status = 'Green' OR prf.finding_type = 'positive') as positive,
                        COUNT(*) FILTER (WHERE prf.finding_type = 'gap' OR prf.status = 'Info') as gap,
                        COUNT(*) FILTER (WHERE prf.finding_type IN ('neutral', 'informational')) as low
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
                    "positive": finding_counts_row.positive if finding_counts_row else 0,
                    "gap": finding_counts_row.gap if finding_counts_row else 0,
                    "deal_blockers": 0,  # Synthesis data not available without checkpoint
                    "conditions_precedent": 0,
                    "warranties": 0,
                    "indemnities": 0
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
                        "calculate": {"status": "completed", "progress": 100, "items_processed": total_docs, "total_items": total_docs},
                        "crossdoc": {"status": "completed", "progress": 100, "items_processed": 1, "total_items": 1},
                        "aggregate": {"status": "completed", "progress": 100, "items_processed": 1, "total_items": 1},
                        "synthesize": {"status": "completed", "progress": 100, "items_processed": 1, "total_items": 1},
                        "verify": {"status": "completed", "progress": 100, "items_processed": 1, "total_items": 1}
                    }
                    current_pass = "verify"
                elif has_findings:
                    # Some findings but maybe still processing
                    status = "processing"
                    progress_pct = int((docs_completed / max(total_docs, 1)) * 100)
                    pass_progress = {
                        "extract": {"status": "completed", "progress": 100, "items_processed": total_docs, "total_items": total_docs},
                        "analyze": {"status": "processing", "progress": progress_pct, "items_processed": docs_completed, "total_items": total_docs},
                        "calculate": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": total_docs},
                        "crossdoc": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "aggregate": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "synthesize": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "verify": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1}
                    }
                    current_pass = "analyze"
                else:
                    status = "pending"
                    pass_progress = {
                        "extract": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": total_docs},
                        "analyze": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": total_docs},
                        "calculate": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": total_docs},
                        "crossdoc": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "aggregate": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "synthesize": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1},
                        "verify": {"status": "pending", "progress": 0, "items_processed": 0, "total_items": 1}
                    }
                    current_pass = None

                # Get classification/organisation progress
                org_progress = _get_organisation_progress(session, dd_id)

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
                        "retry_count": 0,
                        "organisation_progress": org_progress
                    }),
                    mimetype="application/json"
                )

            # Map current_pass to our pass names
            # Pipeline: 1=extract, 2=analyze, 2.5=calculate, 3=crossdoc, 3.5=aggregate, 4=synthesize, 5=verify
            pass_mapping = {
                1: "extract",
                2: "analyze",
                3: "crossdoc",
                4: "synthesize",
                5: "verify"
            }

            current_pass_num = result.current_pass or 1
            current_stage = result.current_stage or ""

            # Determine current pass - check for intermediate passes via stage name
            if "pass2_5" in current_stage or "calculate" in current_stage.lower():
                current_pass = "calculate"
            elif "pass3_5" in current_stage or "aggregate" in current_stage.lower():
                current_pass = "aggregate"
            else:
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

            # Define the full 7-pass pipeline order
            full_pass_order = ["extract", "analyze", "calculate", "crossdoc", "aggregate", "synthesize", "verify"]

            # Determine which passes are completed based on current_pass
            def is_pass_completed(pass_name):
                """Check if a pass is completed based on current position in pipeline."""
                pass_index = full_pass_order.index(pass_name)
                current_index = full_pass_order.index(current_pass) if current_pass in full_pass_order else 0

                # If status is completed, all passes are done
                if result.status == "completed":
                    return True

                return pass_index < current_index

            def is_current_pass(pass_name):
                """Check if this is the currently running pass."""
                return pass_name == current_pass and result.status == "processing"

            for pass_name in full_pass_order:
                if is_pass_completed(pass_name):
                    # Completed pass
                    pass_progress[pass_name] = {
                        "status": "completed",
                        "progress": 100,
                        "items_processed": total_docs if pass_name in ["extract", "analyze"] else 1,
                        "total_items": total_docs if pass_name in ["extract", "analyze"] else 1
                    }
                elif is_current_pass(pass_name):
                    # Current pass - use granular progress
                    if pass_name == "extract":
                        progress = pass1_prog
                        items_processed = docs_processed
                        total_items = total_docs
                    elif pass_name == "analyze":
                        progress = pass2_prog
                        items_processed = docs_processed
                        total_items = total_docs
                    elif pass_name == "calculate":
                        # Pass 2.5 - fast Python calculation, show as 50% when active
                        progress = 50
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
                    elif pass_name == "aggregate":
                        # Pass 3.5 - fast Python aggregation, show as 50% when active
                        progress = 50
                        items_processed = 1
                        total_items = 1
                    elif pass_name == "synthesize":
                        progress = pass4_prog
                        items_processed = 1 if pass4_prog > 0 else 0
                        total_items = 1
                    elif pass_name == "verify":
                        # Pass 5 - Opus verification
                        progress = 50  # Show 50% when active
                        items_processed = 1
                        total_items = 1
                    else:
                        progress = 0
                        items_processed = 0
                        total_items = 1

                    pass_progress[pass_name] = {
                        "status": "processing",
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
                        "total_items": total_docs if pass_name in ["extract", "analyze"] else 1
                    }

            # Get finding counts from perspective_risk_finding via the membership chain
            # Status field contains: 'Red', 'Amber', 'Green', 'New', 'Info'
            # DDProcessAllDev maps: high->Red, medium->Amber, low->Green
            # IMPORTANT: When run_id is provided, filter by run_id to show only findings from that run
            actual_dd_id = str(result.dd_id) if result.dd_id else dd_id
            actual_run_id = str(result.run_id) if result.run_id else run_id

            if actual_run_id:
                # Filter by run_id for run-specific finding counts
                # IMPORTANT: This severity mapping MUST match RiskSummary.tsx exactly:
                #   - critical: action_priority = 'critical'
                #   - high: status = 'Red' AND action_priority != 'critical', OR action_priority = 'high', OR finding_type = 'negative'
                #   - medium: status = 'Amber'
                #   - positive: status = 'Green' OR finding_type = 'positive'
                #   - gap: finding_type = 'gap' OR status = 'Info'
                #   - low: finding_type IN ('neutral', 'informational')
                finding_query = text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE prf.action_priority = 'critical') as critical,
                        COUNT(*) FILTER (WHERE (prf.status = 'Red' AND prf.action_priority != 'critical') OR prf.action_priority = 'high' OR (prf.finding_type = 'negative' AND prf.status != 'Red')) as high,
                        COUNT(*) FILTER (WHERE prf.status = 'Amber') as medium,
                        COUNT(*) FILTER (WHERE prf.status = 'Green' OR prf.finding_type = 'positive') as positive,
                        COUNT(*) FILTER (WHERE prf.finding_type = 'gap' OR prf.status = 'Info') as gap,
                        COUNT(*) FILTER (WHERE prf.finding_type IN ('neutral', 'informational')) as low
                    FROM perspective_risk_finding prf
                    JOIN perspective_risk pr ON prf.perspective_risk_id = pr.id
                    JOIN perspective p ON pr.perspective_id = p.id
                    JOIN due_diligence_member ddm ON p.member_id = ddm.id
                    WHERE ddm.dd_id = :dd_id
                    AND prf.run_id = :run_id
                    AND prf.status != 'Deleted'
                """)
                finding_counts_row = session.execute(finding_query, {"dd_id": actual_dd_id, "run_id": actual_run_id}).fetchone()

                # Get deal blockers and conditions precedent from synthesis_data (authoritative source)
                # These are stored in dd_analysis_run.synthesis_data, not computed from findings
                # Note: dd_analysis_run uses 'id' as the primary key, not 'run_id'
                synthesis_query = text("""
                    SELECT synthesis_data
                    FROM dd_analysis_run
                    WHERE dd_id = :dd_id AND id = :run_id
                """)
                synthesis_row = session.execute(synthesis_query, {"dd_id": actual_dd_id, "run_id": actual_run_id}).fetchone()
                synthesis_data = synthesis_row.synthesis_data if synthesis_row and synthesis_row.synthesis_data else {}
                deal_blockers_count = len(synthesis_data.get('deal_blockers', [])) if isinstance(synthesis_data, dict) else 0
                cps_count = len(synthesis_data.get('conditions_precedent', [])) if isinstance(synthesis_data, dict) else 0
                # Warranties and indemnities are now separate registers
                warranties_count = len(synthesis_data.get('warranties_register', [])) if isinstance(synthesis_data, dict) else 0
                indemnities_count = len(synthesis_data.get('indemnities_register', [])) if isinstance(synthesis_data, dict) else 0
            else:
                # Legacy: no run_id, count all findings for the DD
                # IMPORTANT: This severity mapping MUST match RiskSummary.tsx exactly
                finding_query = text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE prf.action_priority = 'critical') as critical,
                        COUNT(*) FILTER (WHERE (prf.status = 'Red' AND prf.action_priority != 'critical') OR prf.action_priority = 'high' OR (prf.finding_type = 'negative' AND prf.status != 'Red')) as high,
                        COUNT(*) FILTER (WHERE prf.status = 'Amber') as medium,
                        COUNT(*) FILTER (WHERE prf.status = 'Green' OR prf.finding_type = 'positive') as positive,
                        COUNT(*) FILTER (WHERE prf.finding_type = 'gap' OR prf.status = 'Info') as gap,
                        COUNT(*) FILTER (WHERE prf.finding_type IN ('neutral', 'informational')) as low
                    FROM perspective_risk_finding prf
                    JOIN perspective_risk pr ON prf.perspective_risk_id = pr.id
                    JOIN perspective p ON pr.perspective_id = p.id
                    JOIN due_diligence_member ddm ON p.member_id = ddm.id
                    WHERE ddm.dd_id = :dd_id
                    AND prf.status != 'Deleted'
                """)
                finding_counts_row = session.execute(finding_query, {"dd_id": actual_dd_id}).fetchone()
                deal_blockers_count = 0
                cps_count = 0
                warranties_count = 0
                indemnities_count = 0

            finding_counts = {
                "total": finding_counts_row.total if finding_counts_row else 0,
                "critical": finding_counts_row.critical if finding_counts_row else 0,
                "high": finding_counts_row.high if finding_counts_row else 0,
                "medium": finding_counts_row.medium if finding_counts_row else 0,
                "positive": finding_counts_row.positive if finding_counts_row else 0,
                "gap": finding_counts_row.gap if finding_counts_row else 0,
                "low": finding_counts_row.low if finding_counts_row else 0,
                "deal_blockers": deal_blockers_count,
                "conditions_precedent": cps_count,
                "warranties": warranties_count,
                "indemnities": indemnities_count
            }

            # Get document statuses using smart selection (avoids counting duplicates)
            # IMPORTANT: Use actual_dd_id (from checkpoint) not dd_id (from request params, may be None)
            documents = _get_processable_documents_for_progress(session, actual_dd_id)

            # Use checkpoint finding counts ONLY during active processing (real-time updates)
            # For completed runs, always use the authoritative database query
            checkpoint_findings_total = get_progress('findings_total', 0)
            is_actively_processing = result.status == "processing"
            if checkpoint_findings_total > 0 and is_actively_processing:
                finding_counts = {
                    "total": checkpoint_findings_total,
                    "critical": get_progress('findings_critical', 0),
                    "high": get_progress('findings_high', 0),
                    "medium": get_progress('findings_medium', 0),
                    "positive": get_progress('findings_positive', 0),
                    "gap": get_progress('findings_gap', 0),
                    "low": get_progress('findings_low', 0),
                    "deal_blockers": get_progress('findings_deal_blockers', 0),
                    "conditions_precedent": get_progress('findings_cps', 0),
                    "warranties": 0,  # Synthesis happens at the end, so 0 during processing
                    "indemnities": 0
                }
            # For completed runs, we already have the correct counts from the database query above

            # Get current document being processed
            current_document_name = None
            try:
                current_document_name = result.current_document_name
            except AttributeError:
                pass

            # Get compression and batching stats
            compression_enabled = getattr(result, 'compression_enabled', False) or False
            batching_enabled = getattr(result, 'batching_enabled', False) or False
            total_batches = getattr(result, 'total_batches', 0) or 0
            batches_completed = getattr(result, 'batches_completed', 0) or 0
            compression_stats = getattr(result, 'compression_stats', None)
            batch_stats = getattr(result, 'batch_stats', None)

            # Get cost breakdown by model (shows which models are being used)
            cost_by_model = getattr(result, 'cost_by_model', None)
            if isinstance(cost_by_model, str):
                try:
                    cost_by_model = json.loads(cost_by_model)
                except (json.JSONDecodeError, TypeError):
                    cost_by_model = None

            # Phase 5: Get knowledge graph stats
            graph_stats = None
            current_stage = result.current_stage or ""
            is_graph_phase = "graph" in current_stage.lower() if current_stage else False

            # First try to get from checkpoint (quick)
            checkpoint_graph_vertices = getattr(result, 'graph_vertices', 0) or 0
            checkpoint_graph_edges = getattr(result, 'graph_edges', 0) or 0

            if checkpoint_graph_vertices > 0 or checkpoint_graph_edges > 0:
                graph_stats = {
                    "status": "completed" if not is_graph_phase else "processing",
                    "vertices": checkpoint_graph_vertices,
                    "edges": checkpoint_graph_edges,
                    "progress": 100 if not is_graph_phase else 50
                }
            else:
                # Try to get from kg_build_status table
                try:
                    graph_query = text("""
                        SELECT
                            status,
                            entities_processed,
                            total_entities,
                            edges_created,
                            started_at,
                            completed_at
                        FROM kg_build_status
                        WHERE dd_id = :dd_id
                        ORDER BY started_at DESC
                        LIMIT 1
                    """)
                    # IMPORTANT: Use actual_dd_id (from checkpoint) not dd_id (from request params)
                    graph_result = session.execute(graph_query, {"dd_id": actual_dd_id}).fetchone()
                    if graph_result:
                        graph_stats = {
                            "status": graph_result.status,
                            "entities_processed": graph_result.entities_processed or 0,
                            "total_entities": graph_result.total_entities or 0,
                            "edges_created": graph_result.edges_created or 0,
                            "progress": int((graph_result.entities_processed or 0) / max(graph_result.total_entities or 1, 1) * 100)
                        }
                except Exception:
                    # Graph tables may not exist yet
                    pass

            # Get classification/organisation progress from dd_organisation_status
            # IMPORTANT: Use actual_dd_id (from checkpoint) not dd_id (from request params)
            organisation_progress = _get_organisation_progress(session, actual_dd_id)

            # Build response
            response_data = {
                "dd_id": str(result.dd_id) if result.dd_id else dd_id,
                "run_id": str(result.run_id) if result.run_id else run_id,
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
                "started_at": (started_at.isoformat() + "Z") if started_at else None,
                "last_updated": (result.last_updated.isoformat() + "Z") if result.last_updated else None,
                "completed_at": (result.completed_at.isoformat() + "Z") if result.completed_at else None,
                "elapsed_seconds": elapsed_seconds,
                "last_error": result.last_error,
                "retry_count": result.retry_count or 0,
                # Phase 4: Compression & Batching
                "compression_enabled": compression_enabled,
                "batching_enabled": batching_enabled,
                "total_batches": total_batches,
                "batches_completed": batches_completed,
                "compression_stats": compression_stats,
                "batch_stats": batch_stats,
                # Model usage breakdown (verify tier config)
                "cost_by_model": cost_by_model,
                # Phase 5: Knowledge Graph
                "graph_stats": graph_stats,
                "is_graph_phase": is_graph_phase,
                # Phase 6: Parallel Processing
                "parallel_processing": _build_parallel_stats(result),
                # Phase 7: Classification & Organisation
                "organisation_progress": organisation_progress,
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


def _build_parallel_stats(result) -> dict:
    """
    Build parallel processing statistics from checkpoint result.

    Returns None if not using parallel processing.
    """
    processing_mode = getattr(result, 'processing_mode', None)

    if not processing_mode or processing_mode == 'sequential':
        return None

    # Get parallel processing fields
    parallel_workers = getattr(result, 'parallel_workers', 0) or 0
    documents_from_cache = getattr(result, 'documents_from_cache', 0) or 0
    documents_failed = getattr(result, 'documents_failed', 0) or 0
    failed_documents = getattr(result, 'failed_documents', None)
    partial_results = getattr(result, 'partial_results', False) or False
    previous_run_id = getattr(result, 'previous_run_id', None)
    synthesis_progress = getattr(result, 'synthesis_progress', 0) or 0
    synthesis_level = getattr(result, 'synthesis_level', None)

    # Parse failed_documents if it's a JSON string
    if isinstance(failed_documents, str):
        try:
            failed_documents = json.loads(failed_documents)
        except (json.JSONDecodeError, TypeError):
            failed_documents = []

    return {
        "mode": processing_mode,
        "workers": parallel_workers,
        "documents_from_cache": documents_from_cache,
        "documents_failed": documents_failed,
        "failed_documents": failed_documents[:5] if failed_documents else [],  # Limit to first 5
        "partial_results": partial_results,
        "previous_run_id": str(previous_run_id) if previous_run_id else None,
        "incremental": previous_run_id is not None,
        "synthesis": {
            "progress": synthesis_progress,
            "level": synthesis_level,
        } if synthesis_level else None,
    }


def _get_organisation_progress(session, dd_id: str) -> dict:
    """
    Get classification and organisation progress from dd_organisation_status table.

    Returns progress data for the classification and folder organisation phases.
    """
    try:
        org_query = text("""
            SELECT
                status,
                classified_count,
                total_documents,
                low_confidence_count,
                failed_count,
                category_counts,
                last_updated
            FROM dd_organisation_status
            WHERE dd_id = :dd_id
        """)
        result = session.execute(org_query, {"dd_id": dd_id}).fetchone()

        if not result:
            return None

        # Parse category_counts if it's JSON
        category_counts = result.category_counts
        if isinstance(category_counts, str):
            try:
                category_counts = json.loads(category_counts)
            except (json.JSONDecodeError, TypeError):
                category_counts = {}

        total_docs = result.total_documents or 0
        classified_count = result.classified_count or 0

        # Calculate progress percentage
        progress = 0
        if total_docs > 0:
            progress = int((classified_count / total_docs) * 100)

        # Map status to phase
        status = result.status or "pending"
        current_phase = "pending"
        if status == "classifying":
            current_phase = "classifying"
        elif status == "classified":
            current_phase = "classified"
        elif status == "organising":
            current_phase = "organising"
        elif status == "organised":
            current_phase = "organised"
        elif status == "completed":
            current_phase = "completed"
        elif status == "failed":
            current_phase = "failed"

        return {
            "status": status,
            "current_phase": current_phase,
            "classification": {
                "status": "completed" if status in ["classified", "organising", "organised", "completed"] else ("processing" if status == "classifying" else "pending"),
                "progress": 100 if status in ["classified", "organising", "organised", "completed"] else progress,
                "classified_count": classified_count,
                "total_documents": total_docs,
                "low_confidence_count": result.low_confidence_count or 0,
                "failed_count": result.failed_count or 0,
            },
            "organisation": {
                "status": "completed" if status in ["organised", "completed"] else ("processing" if status == "organising" else "pending"),
                "progress": 100 if status in ["organised", "completed"] else (0 if status != "organising" else 50),
                "category_counts": category_counts or {},
            },
            "last_updated": (result.last_updated.isoformat() + "Z") if result.last_updated else None,
        }
    except Exception as e:
        # Table may not exist or other error - return None
        return None


def _get_processable_documents_for_progress(session, dd_id: str) -> list:
    """
    Get processable documents for progress display using smart selection.

    Returns documents in the same format as the original SQL query but uses
    smart document selection to avoid duplicates (original vs converted).

    Args:
        session: SQLAlchemy session
        dd_id: Due diligence UUID string

    Returns:
        List of document dicts with: id, filename, doc_type, status,
        readability_status, readability_error
    """
    # Get folders for this DD
    folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
    folder_ids = [str(f.id) for f in folders]

    if not folder_ids:
        return []

    # Use smart document selection
    processable_docs = get_processable_documents(session, folder_ids)

    # Build result list in same format as SQL query
    documents = []
    for doc in processable_docs:
        # Determine status
        if doc.processing_status in ('completed', 'processed'):
            status = 'completed'
        elif doc.processing_status == 'processing':
            status = 'processing'
        elif doc.processing_status == 'error':
            status = 'error'
        else:
            status = 'queued'

        documents.append({
            "id": str(doc.id),
            "filename": doc.original_file_name,
            "original_file_name": doc.original_file_name,
            "doc_type": doc.type or "other",
            "type": doc.type or "other",
            "status": status,
            "readability_status": doc.readability_status or "pending",
            "readability_error": doc.readability_error
        })

    return documents
