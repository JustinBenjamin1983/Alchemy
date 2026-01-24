# DDProcessEnhanced - Multi-pass document processing using enhanced architecture
# This endpoint orchestrates the 4-pass DD analysis pipeline with blueprint-driven prompts
#
# OPTIMIZATIONS (v2):
# - Model tiering: Haiku for Pass 1 (75% cost reduction), Sonnet for analysis
# - Document clustering: Process related docs together in Pass 3 (70% context reduction)
# - Question prioritization: Tier 1-3 questions (~85% reduction in questions)
# - Checkpoint/resume: Save progress for long-running processes
#
# ARCHITECTURE NOTE (v2.1):
# Uses SEPARATE DATABASE SESSIONS to avoid connection timeout during long-running Claude API calls:
# - Session 1: Load DD metadata, create checkpoint, load documents (quick, ~30 seconds)
# - No session: Run all Claude API processing (long, ~10+ minutes)
# - Session 2: Store findings in database (quick, ~30 seconds)
# This prevents PostgreSQL from closing connections that are held too long.

import logging
import os
import json
import sys
import datetime
from typing import List, Dict, Any, Optional, Tuple
import azure.functions as func

from shared.session import transactional_session
from shared.models import (
    Document, DueDiligence, DueDiligenceMember, Folder,
    PerspectiveRisk, PerspectiveRiskFinding, Perspective, DDWizardDraft,
    DDProcessingCheckpoint
)
from shared.dev_adapters.dev_config import get_dev_config

# Add dd_enhanced to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dd_enhanced'))

from config.blueprints.loader import load_blueprint, list_available_blueprints
from dd_enhanced.core.claude_client import ClaudeClient
from dd_enhanced.core.pass1_extract import run_pass1_extraction
from dd_enhanced.core.pass2_analyze import run_pass2_analysis
from dd_enhanced.core.pass3_crossdoc import run_pass3_crossdoc_synthesis
from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis

# NEW: Import optimization modules
from dd_enhanced.core.document_clusters import group_documents_by_cluster, get_cluster_summary
from dd_enhanced.core.pass3_clustered import run_pass3_clustered, run_pass3_hybrid, BATCHING_THRESHOLD
from dd_enhanced.core.question_prioritizer import prioritize_questions, get_summary as get_question_summary

# Phase 4: Import compression and batching modules
from dd_enhanced.core.document_priority import (
    prioritize_all_documents,
    get_priority_stats,
)
from dd_enhanced.core.compression_engine import (
    compress_all_documents,
    get_compression_stats,
)
from dd_enhanced.core.batch_manager import (
    create_batch_plan,
    get_batch_stats,
    should_use_batching,
    BatchStrategy,
)

# Phase 5: Import knowledge graph modules
from dd_enhanced.core.graph import (
    EntityTransformer,
    KnowledgeGraphBuilder,
    RelationshipEnricher,
    GraphQueryEngine,
)

# Phase 6: Import parallel processing orchestrator
from dd_enhanced.core.orchestrator import (
    ParallelOrchestrator,
    OrchestratorConfig,
    ProcessingMode,
    create_orchestrator,
)

# Phase 7: Import calculation engine orchestrator
from dd_enhanced.core.pass_calculations import CalculationOrchestrator

# Phase 7: Import Pass 5 Opus verification
from dd_enhanced.core.pass5_verify import run_pass5_verification, apply_verification_adjustments

# Entity Mapping: Import for loading pre-computed entity map
# Note: Entity mapping should be run as a pre-processing step via DDEntityMapping endpoint
# before DDProcessEnhanced is called. This import is only for loading the results.
from dd_enhanced.core.entity_mapping import get_entity_map_for_dd

# Checkpoint C: Import for validated context in calculations (post-analysis validation)
from DDValidationCheckpoint import get_validated_context

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

# Phase 6: Parallel processing configuration
PARALLEL_THRESHOLD = int(os.environ.get("DD_PARALLEL_THRESHOLD", "100"))
USE_PARALLEL_ORCHESTRATOR = os.environ.get("DD_USE_PARALLEL_ORCHESTRATOR", "true").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Process all documents in a DD project using the enhanced 4-pass architecture.

    ARCHITECTURE (v2.1):
    Uses SEPARATE database sessions to avoid connection timeout during long-running Claude API calls:
    - Phase 1: Load DD metadata, create checkpoint, load documents (quick, fresh session)
    - Phase 2: Run all Claude API processing (long, NO database session held)
    - Phase 3: Store findings in database (quick, fresh session)

    Query params:
        dd_id: The DD project ID (required)
        resume: If "true", resume from checkpoint (optional)
        include_tier3: If "true", include deep-dive questions (optional)
        use_clustered_pass3: If "true", use optimized Pass 3 (default: true)

    Returns:
        JSON with processing results and statistics
    """

    # Only allow in dev mode for now
    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            status_code=403,
            mimetype="application/json"
        )

    dd_id = None
    checkpoint_id = None

    try:
        dd_id = req.params.get('dd_id')
        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse optimization flags
        resume_from_checkpoint = req.params.get('resume', '').lower() == 'true'
        include_tier3 = req.params.get('include_tier3', '').lower() == 'true'
        use_clustered_pass3 = req.params.get('use_clustered_pass3', 'true').lower() != 'false'

        logging.info(f"[DDProcessEnhanced] Starting enhanced processing for DD: {dd_id}")
        logging.info(f"[DDProcessEnhanced] Options: resume={resume_from_checkpoint}, tier3={include_tier3}, clustered_pass3={use_clustered_pass3}")

        # =====================================================================
        # PHASE 1: Load data from database (quick session, ~30 seconds max)
        # =====================================================================
        logging.info("[DDProcessEnhanced] Phase 1: Loading data from database...")

        load_result = _load_dd_data(dd_id, resume_from_checkpoint)
        if load_result.get("error"):
            return func.HttpResponse(
                json.dumps({"error": load_result["error"]}),
                status_code=load_result.get("status_code", 400),
                mimetype="application/json"
            )

        # Extract loaded data
        checkpoint_id = load_result["checkpoint_id"]
        transaction_type_code = load_result["transaction_type_code"]
        transaction_context = load_result["transaction_context"]
        blueprint = load_result["blueprint"]
        doc_dicts = load_result["doc_dicts"]
        reference_docs = load_result["reference_docs"]
        transaction_context_str = load_result["transaction_context_str"]
        dd_name = load_result["dd_name"]
        owned_by = load_result["owned_by"]
        entity_map = load_result.get("entity_map")  # Entity map for party validation

        logging.info(f"[DDProcessEnhanced] Phase 1 complete: {len(doc_dicts)} documents loaded")

        # =====================================================================
        # PHASE 2: Run Claude API processing (NO database session held)
        # This can take 10+ minutes - no DB connection is held during this time
        # =====================================================================
        logging.info("[DDProcessEnhanced] Phase 2: Running Claude API processing (no DB session held)...")

        # Initialize Claude client with cost tracking
        client = ClaudeClient()

        # Run all 4 passes (Phase 6: auto-switches between sequential/parallel)
        processing_result = _run_all_passes(
            checkpoint_id=checkpoint_id,
            doc_dicts=doc_dicts,
            reference_docs=reference_docs,
            blueprint=blueprint,
            transaction_context=transaction_context,
            transaction_context_str=transaction_context_str,
            client=client,
            include_tier3=include_tier3,
            use_clustered_pass3=use_clustered_pass3,
            dd_id=dd_id,  # Phase 6: for parallel orchestrator
            run_id=checkpoint_id,  # Phase 6: use checkpoint as run_id
            entity_map=entity_map,  # Entity map for party validation
        )

        if processing_result.get("error"):
            _save_checkpoint_safely(checkpoint_id, {
                'status': 'failed',
                'last_error': processing_result["error"][:1000]
            })
            return func.HttpResponse(
                json.dumps({"error": processing_result["error"]}),
                status_code=500,
                mimetype="application/json"
            )

        # Extract processing results
        pass1_results = processing_result["pass1_results"]
        pass2_findings = processing_result["pass2_findings"]
        pass3_results = processing_result["pass3_results"]
        pass4_results = processing_result["pass4_results"]
        question_summary = processing_result["question_summary"]
        graph_stats = processing_result.get("graph_stats")
        parallel_stats = processing_result.get("parallel_stats")  # Phase 6
        synthesis_results = processing_result.get("synthesis_results")  # Phase 6
        calculation_aggregates = processing_result.get("calculation_aggregates")  # Phase 7
        calculation_summary = processing_result.get("calculation_summary")  # Phase 7
        verification_result = processing_result.get("verification_result")  # Phase 7

        logging.info("[DDProcessEnhanced] Phase 2 complete: All passes finished")

        # =====================================================================
        # PHASE 3: Store findings in database (quick session, ~30 seconds max)
        # =====================================================================
        logging.info("[DDProcessEnhanced] Phase 3: Storing findings in database...")

        _save_checkpoint_safely(checkpoint_id, {
            'current_stage': 'storing_findings'
        })

        store_result = _store_all_findings(
            dd_id=dd_id,
            owned_by=owned_by,
            doc_dicts=doc_dicts,
            pass4_results=pass4_results,
            pass3_results=pass3_results,
            blueprint=blueprint
        )

        if store_result.get("error"):
            _save_checkpoint_safely(checkpoint_id, {
                'status': 'failed',
                'last_error': store_result["error"][:1000]
            })
            return func.HttpResponse(
                json.dumps({"error": store_result["error"]}),
                status_code=500,
                mimetype="application/json"
            )

        stored_count = store_result["stored_count"]
        cross_doc_stored = store_result["cross_doc_stored"]

        logging.info(f"[DDProcessEnhanced] Phase 3 complete: {stored_count + cross_doc_stored} findings stored")

        # =====================================================================
        # FINALIZE: Mark checkpoint complete and return response
        # =====================================================================
        cost_summary = client.get_cost_summary()
        usage_report = client.get_usage_report()

        _save_checkpoint_safely(checkpoint_id, {
            'status': 'completed',
            'completed_at': datetime.datetime.utcnow(),
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        # Build response
        response_data = {
            "success": True,
            "dd_id": dd_id,
            "transaction_type": transaction_type_code,
            "documents_processed": len(doc_dicts),
            "optimizations": {
                "model_tiering": "Haiku for Pass 1, Sonnet for Pass 2-4",
                "question_prioritization": question_summary,
                "clustered_pass3": use_clustered_pass3,
                "clusters_analyzed": pass3_results.get("clusters_analyzed", 0) if use_clustered_pass3 else None
            },
            "statistics": {
                "pass1": {
                    "key_dates": len(pass1_results.get("key_dates", [])),
                    "financial_figures": len(pass1_results.get("financial_figures", [])),
                    "coc_clauses": len(pass1_results.get("coc_clauses", [])),
                    "consent_requirements": len(pass1_results.get("consent_requirements", []))
                },
                "knowledge_graph": {
                    "vertices": graph_stats.total_vertices if graph_stats else 0,
                    "edges": graph_stats.total_edges if graph_stats else 0,
                    "parties": graph_stats.party_count if graph_stats else 0,
                    "agreements": graph_stats.agreement_count if graph_stats else 0,
                    "triggers": graph_stats.trigger_count if graph_stats else 0
                } if graph_stats else None,
                "pass2": {
                    "findings": len(pass2_findings),
                    "by_severity": _count_by_severity(pass2_findings)
                },
                "pass3": {
                    "cross_doc_findings": len(pass3_results.get("cross_doc_findings", [])),
                    "conflicts": len(pass3_results.get("conflicts", [])),
                    "cascade_items": len(pass3_results.get("cascade_analysis", {}).get("cascade_items", [])),
                    "authorization_issues": len(pass3_results.get("authorization_issues", [])),
                    "consent_matrix": len(pass3_results.get("consent_matrix", []))
                },
                "pass4": {
                    "deal_blockers": len(pass4_results.get("deal_blockers", [])),
                    "conditions_precedent": len(pass4_results.get("conditions_precedent", [])),
                    "total_financial_exposure": pass4_results.get("financial_exposures", {}).get("total", 0)
                }
            },
            "findings_stored": stored_count + cross_doc_stored,
            "deal_blockers": pass4_results.get("deal_blockers", [])[:5],  # Top 5
            "executive_summary": pass4_results.get("executive_summary", "")[:1000],
            "cost_summary": cost_summary,
            "usage_report": usage_report,
            # Phase 6: Parallel processing statistics (if applicable)
            "parallel_processing": parallel_stats if parallel_stats else None,
            "hierarchical_synthesis": synthesis_results if synthesis_results else None,
            # Phase 7: Calculation engine statistics
            "calculation_engine": {
                "total_calculated_exposure": calculation_aggregates.get("total_exposure") if calculation_aggregates else None,
                "exposure_currency": calculation_aggregates.get("currency", "ZAR") if calculation_aggregates else None,
                "calculations_performed": calculation_summary.get("successful", 0) if calculation_summary else 0,
                "calculations_failed": calculation_summary.get("failed", 0) if calculation_summary else 0,
                "by_category": calculation_aggregates.get("by_category") if calculation_aggregates else None,
                "transaction_ratio": calculation_aggregates.get("transaction_ratio") if calculation_aggregates else None,
            } if calculation_summary or calculation_aggregates else None,
            # Phase 7: Opus verification results
            "verification": {
                "passed": verification_result.get("verification_passed", False) if verification_result else None,
                "confidence": verification_result.get("overall_confidence", 0) if verification_result else None,
                "critical_issues": len(verification_result.get("critical_issues", [])) if verification_result else 0,
                "warnings": len(verification_result.get("warnings", [])) if verification_result else 0,
                "deal_blockers_verified": len(verification_result.get("blocker_verification", {}).get("blocker_assessments", [])) if verification_result else 0,
                "calculations_verified": len(verification_result.get("calculation_verification", {}).get("calculation_verifications", [])) if verification_result else 0,
                "final_recommendation": verification_result.get("final_summary", {}).get("final_recommendation", {}).get("deal_status") if verification_result else None,
            } if verification_result else None,
        }

        logging.info(f"[DDProcessEnhanced] Processing complete. Stored {stored_count + cross_doc_stored} findings.")
        logging.info(f"[DDProcessEnhanced] Total cost: ${cost_summary['total_cost_usd']:.4f}")

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception(f"[DDProcessEnhanced] Error: {e}")

        # Try to update checkpoint with error (using safe save)
        if checkpoint_id:
            _save_checkpoint_safely(checkpoint_id, {
                'status': 'failed',
                'last_error': str(e)[:1000],
                'retry_count': 1  # Will be incremented if already set
            })
        elif dd_id:
            # Try to find and update checkpoint by dd_id
            try:
                with transactional_session() as session:
                    checkpoint = session.query(DDProcessingCheckpoint).filter(
                        DDProcessingCheckpoint.dd_id == dd_id
                    ).first()
                    if checkpoint:
                        checkpoint.status = 'failed'
                        checkpoint.last_error = str(e)[:1000]
                        checkpoint.retry_count = (checkpoint.retry_count or 0) + 1
                        session.commit()
            except Exception:
                pass

        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def _load_dd_data(dd_id: str, resume_from_checkpoint: bool) -> Dict[str, Any]:
    """
    Phase 1: Load all DD data from database using a short-lived session.

    Returns dict with all needed data or error information.
    """
    try:
        with transactional_session() as session:
            # Get the DD and validate
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return {"error": "DD not found", "status_code": 404}

            # Store DD info before session closes
            dd_name = dd.name
            dd_briefing = dd.briefing
            owned_by = dd.owned_by

            # Check for existing checkpoint
            checkpoint = session.query(DDProcessingCheckpoint).filter(
                DDProcessingCheckpoint.dd_id == dd_id
            ).first()

            if checkpoint and resume_from_checkpoint and checkpoint.status == 'paused':
                logging.info(f"[DDProcessEnhanced] Resuming from checkpoint: pass {checkpoint.current_pass}, stage {checkpoint.current_stage}")
            elif checkpoint:
                # Reset checkpoint for fresh run
                session.delete(checkpoint)
                session.flush()
                checkpoint = None

            # Create new checkpoint
            if not checkpoint:
                checkpoint = DDProcessingCheckpoint(
                    dd_id=dd_id,
                    status='processing',
                    current_pass=1,
                    current_stage='initialization'
                )
                session.add(checkpoint)
                session.flush()

            checkpoint_id = str(checkpoint.id)

            # Get transaction type from wizard draft
            draft = session.query(DDWizardDraft).filter(
                DDWizardDraft.owned_by == owned_by,
                DDWizardDraft.transaction_name == dd_name
            ).first()

            transaction_type_code = _map_transaction_type_to_code(
                draft.transaction_type if draft and draft.transaction_type else "General"
            )

            logging.info(f"[DDProcessEnhanced] Transaction type: {transaction_type_code}")

            # Build transaction context from wizard draft
            transaction_context = _build_transaction_context_from_draft(draft) if draft else {}

            # Load blueprint for this transaction type
            try:
                blueprint = load_blueprint(transaction_type_code)
                logging.info(f"[DDProcessEnhanced] Loaded blueprint: {blueprint.get('transaction_type')}")
            except ValueError:
                logging.warning(f"[DDProcessEnhanced] No blueprint for {transaction_type_code}, using ma_corporate")
                blueprint = load_blueprint("ma_corporate")

            # Get all documents for this DD
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]
            folder_lookup = {str(f.id): f for f in folders}

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()

            if not documents:
                checkpoint.status = 'failed'
                checkpoint.last_error = 'No documents found'
                session.commit()
                return {
                    "error": "No documents found in this DD project",
                    "status_code": 400
                }

            logging.info(f"[DDProcessEnhanced] Found {len(documents)} documents")
            checkpoint.total_documents = len(documents)

            # Load document content and prepare for processing
            # Store document filenames for later lookup
            doc_filenames = {str(doc.id): doc.original_file_name for doc in documents}

            doc_dicts = []
            for doc in documents:
                content = _extract_document_content(doc)
                if content:
                    folder = folder_lookup.get(str(doc.folder_id))
                    doc_dict = {
                        "id": str(doc.id),
                        "filename": doc.original_file_name,
                        "text": content,
                        "doc_type": _classify_document_type(doc.original_file_name, folder),
                        "word_count": len(content.split()),
                        "char_count": len(content),
                        "folder_path": folder.path if folder else ""
                    }
                    doc_dicts.append(doc_dict)

            if not doc_dicts:
                checkpoint.status = 'failed'
                checkpoint.last_error = 'Could not extract content from any documents'
                session.commit()
                return {
                    "error": "Could not extract content from any documents",
                    "status_code": 400
                }

            logging.info(f"[DDProcessEnhanced] Loaded content from {len(doc_dicts)} documents")

            # Get reference documents based on blueprint
            reference_docs = _identify_reference_documents(doc_dicts, blueprint)
            logging.info(f"[DDProcessEnhanced] Reference docs: {[d['filename'] for d in reference_docs]}")

            # Build transaction context string for prompts
            transaction_context_str = _build_transaction_context(blueprint, dd_name, dd_briefing)

            # Retrieve entity map for party validation during analysis
            # (Entity mapping pass should have been run earlier after classification)
            entity_map = get_entity_map_for_dd(dd_id, session)
            if entity_map:
                logging.info(f"[DDProcessEnhanced] Loaded entity map: {len(entity_map)} entities")
            else:
                logging.info("[DDProcessEnhanced] No entity map found - party validation will be skipped")

            # Commit checkpoint update
            session.commit()

            # Return all loaded data
            return {
                "checkpoint_id": checkpoint_id,
                "transaction_type_code": transaction_type_code,
                "transaction_context": transaction_context,
                "blueprint": blueprint,
                "doc_dicts": doc_dicts,
                "doc_filenames": doc_filenames,
                "reference_docs": reference_docs,
                "transaction_context_str": transaction_context_str,
                "dd_name": dd_name,
                "owned_by": owned_by,
                "entity_map": entity_map
            }

    except Exception as e:
        logging.exception(f"[DDProcessEnhanced] Error loading DD data: {e}")
        return {"error": f"Failed to load DD data: {str(e)}", "status_code": 500}


def _run_all_passes(
    checkpoint_id: str,
    doc_dicts: List[Dict],
    reference_docs: List[Dict],
    blueprint: Dict,
    transaction_context: Dict,
    transaction_context_str: str,
    client: ClaudeClient,
    include_tier3: bool,
    use_clustered_pass3: bool,
    dd_id: Optional[str] = None,
    run_id: Optional[str] = None,
    previous_run_id: Optional[str] = None,
    entity_map: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Phase 2: Run all 4 passes of Claude API processing.

    NO database session is held during this phase - it can take 10+ minutes.
    Checkpoint updates use _save_checkpoint_safely() which opens fresh sessions.

    PHASE 6: Auto-switches between sequential and parallel processing based on
    document count. Threshold is configurable via DD_PARALLEL_THRESHOLD.
    """
    try:
        doc_count = len(doc_dicts)

        # ===== ENTITY MAP STATUS =====
        # Entity mapping should be run as a pre-processing step (DDEntityMapping endpoint)
        # followed by Checkpoint B (entity confirmation) before DDProcessEnhanced is called.
        # If no entity map exists, we log this clearly.
        if entity_map is None or len(entity_map) == 0:
            logging.warning("[DDProcessEnhanced] No entity map found - entity mapping and Checkpoint B "
                          "(entity confirmation) were not completed during pre-processing.")
            _save_checkpoint_safely(checkpoint_id, {
                'entity_map_status': 'missing',
                'entity_map_warning': 'Entity mapping not performed during pre-processing'
            })
        else:
            logging.info(f"[DDProcessEnhanced] Entity map loaded: {len(entity_map)} entities")
            entities_needing_confirmation = sum(1 for e in entity_map if e.get('requires_human_confirmation'))
            if entities_needing_confirmation > 0:
                logging.info(f"[DDProcessEnhanced] {entities_needing_confirmation} entities flagged for user confirmation")
            _save_checkpoint_safely(checkpoint_id, {
                'entity_map_status': 'loaded',
                'entity_count': len(entity_map),
                'entities_needing_confirmation': entities_needing_confirmation
            })

        # Phase 6: Check if we should use parallel orchestrator
        if USE_PARALLEL_ORCHESTRATOR and doc_count >= PARALLEL_THRESHOLD:
            logging.info(f"[DDProcessEnhanced] Using PARALLEL orchestrator for {doc_count} documents "
                        f"(threshold: {PARALLEL_THRESHOLD})")
            return _run_parallel_passes(
                checkpoint_id=checkpoint_id,
                dd_id=dd_id,
                run_id=run_id or checkpoint_id,
                doc_dicts=doc_dicts,
                reference_docs=reference_docs,
                blueprint=blueprint,
                transaction_context_str=transaction_context_str,
                client=client,
                include_tier3=include_tier3,
                previous_run_id=previous_run_id,
                entity_map=entity_map,
            )

        logging.info(f"[DDProcessEnhanced] Using SEQUENTIAL processing for {doc_count} documents "
                    f"(threshold: {PARALLEL_THRESHOLD})")
        # ===== PASS 1: Extract & Index (using Haiku) =====
        _save_checkpoint_safely(checkpoint_id, {
            'current_pass': 1,
            'current_stage': 'pass1_extraction',
            'total_documents': len(doc_dicts)
        })

        logging.info("[DDProcessEnhanced] Starting Pass 1: Extract & Index (Haiku)")
        pass1_results = run_pass1_extraction(doc_dicts, client, verbose=False)

        # Store Pass 1 results in checkpoint
        cost_summary = client.get_cost_summary()
        _save_checkpoint_safely(checkpoint_id, {
            'pass1_extractions': pass1_results,
            'documents_processed': len(doc_dicts),
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        logging.info(f"[DDProcessEnhanced] Pass 1 complete: {len(pass1_results.get('key_dates', []))} dates, "
                    f"{len(pass1_results.get('financial_figures', []))} financials")

        # ===== PHASE 5: Knowledge Graph Building =====
        # Build graph from Pass 1 entities - runs between Pass 1 and Pass 2
        # This enables graph-aware clustering in Pass 3
        graph_stats = None
        try:
            _save_checkpoint_safely(checkpoint_id, {
                'current_stage': 'graph_building'
            })
            logging.info("[DDProcessEnhanced] Phase 5: Building knowledge graph from Pass 1 entities")

            # Transform Pass 1 results to graph entities
            transformer = EntityTransformer()
            all_entities = []
            for doc in doc_dicts:
                doc_id = doc.get('id', '')
                doc_name = doc.get('filename', '')
                # Find Pass 1 extraction for this document
                doc_extraction = _find_doc_extraction(pass1_results, doc_name)
                if doc_extraction:
                    entities = transformer.transform_document(
                        document_id=doc_id,
                        document_name=doc_name,
                        pass1_extraction=doc_extraction
                    )
                    all_entities.append(entities)

            logging.info(f"[DDProcessEnhanced] Transformed {len(all_entities)} documents to graph entities")

            # Run relationship enrichment (lightweight Claude calls for cross-references)
            # Only if we have significant number of documents
            if len(doc_dicts) > 5:
                _save_checkpoint_safely(checkpoint_id, {
                    'current_stage': 'graph_enrichment'
                })
                logging.info("[DDProcessEnhanced] Running relationship enrichment")
                enricher = RelationshipEnricher(client)

                def enrichment_progress(current, total, message):
                    if current % 10 == 0 or current == total:
                        logging.info(f"[DDProcessEnhanced] Enrichment progress: {current}/{total}")

                enrichments = enricher.enrich_all_documents(
                    doc_dicts,
                    progress_callback=enrichment_progress,
                    max_workers=5
                )
                logging.info(f"[DDProcessEnhanced] Enrichment complete: {len(enrichments)} documents enriched")

                # Merge enrichments into entities
                from dd_enhanced.core.graph.relationship_enricher import merge_enrichments
                for entities, enrichment in zip(all_entities, enrichments):
                    if not enrichment.error:
                        merge_enrichments(entities, enrichment)

            # Build graph in database
            # Note: We need a fresh connection for graph building
            from shared.session import engine
            raw_conn = engine.raw_connection()
            try:
                _save_checkpoint_safely(checkpoint_id, {
                    'current_stage': 'graph_populating'
                })

                # Get dd_id from first document's folder or from checkpoint
                # We need to pass dd_id to the graph builder
                dd_id_for_graph = None
                with transactional_session() as session:
                    checkpoint = session.query(DDProcessingCheckpoint).filter(
                        DDProcessingCheckpoint.id == checkpoint_id
                    ).first()
                    if checkpoint:
                        dd_id_for_graph = str(checkpoint.dd_id)

                if dd_id_for_graph and all_entities:
                    builder = KnowledgeGraphBuilder(raw_conn)

                    def build_progress(current, total, message):
                        if current % 20 == 0 or current == total:
                            logging.info(f"[DDProcessEnhanced] Graph build: {message}")

                    graph_stats = builder.build_graph(
                        dd_id=dd_id_for_graph,
                        document_entities=all_entities,
                        progress_callback=build_progress
                    )
                    raw_conn.commit()
                    logging.info(f"[DDProcessEnhanced] Knowledge graph built: "
                                f"{graph_stats.total_vertices} vertices, {graph_stats.total_edges} edges")

                    _save_checkpoint_safely(checkpoint_id, {
                        'graph_vertices': graph_stats.total_vertices,
                        'graph_edges': graph_stats.total_edges
                    })
            finally:
                raw_conn.close()

        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Knowledge graph building failed (non-fatal): {e}")
            # Graph building failure is not fatal - continue with processing

        # ===== PRIORITIZE QUESTIONS for Pass 2 =====
        logging.info("[DDProcessEnhanced] Prioritizing questions based on blueprint and context")
        prioritized_questions = prioritize_questions(
            blueprint=blueprint,
            transaction_context=transaction_context,
            include_tier3=include_tier3,
            max_questions=150
        )
        question_summary = get_question_summary(prioritized_questions)
        logging.info(f"[DDProcessEnhanced] Question prioritization: {question_summary['total_questions']} questions "
                    f"(Tier1: {question_summary['tier1_count']}, Tier2: {question_summary['tier2_count']}, "
                    f"Tier3: {question_summary['tier3_count']})")

        # ===== PASS 2: Per-Document Analysis (Blueprint-Driven) =====
        _save_checkpoint_safely(checkpoint_id, {
            'current_pass': 2,
            'current_stage': 'pass2_analysis',
            'total_questions': question_summary['total_questions']
        })

        logging.info("[DDProcessEnhanced] Starting Pass 2: Per-Document Analysis (Sonnet)")

        # Convert reference_docs to LoadedDocument-like objects for pass2
        class RefDoc:
            def __init__(self, d):
                self.filename = d['filename']
                self.text = d['text']
                self.doc_type = d['doc_type']

        ref_doc_objects = [RefDoc(d) for d in reference_docs]

        pass2_findings = run_pass2_analysis(
            doc_dicts,
            ref_doc_objects,
            blueprint,
            client,
            transaction_context=transaction_context_str,
            prioritized_questions=prioritized_questions,
            verbose=False,
            entity_map=entity_map
        )

        # Save checkpoint with costs after Pass 2
        cost_summary = client.get_cost_summary()
        _save_checkpoint_safely(checkpoint_id, {
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        logging.info(f"[DDProcessEnhanced] Pass 2 complete: {len(pass2_findings)} findings")

        # ===== PASS 2.5: Financial Calculation Engine =====
        # Enrich findings with deterministic calculations (AI extracts → Python calculates)
        _save_checkpoint_safely(checkpoint_id, {
            'current_stage': 'pass2_5_calculations'
        })

        logging.info("[DDProcessEnhanced] Starting Pass 2.5: Financial Calculations (Deterministic)")

        # Get transaction value for validation (from Pass 1 if available)
        transaction_value = None
        for fig in pass1_results.get('financial_figures', []):
            if 'purchase' in str(fig.get('description', '')).lower() or 'transaction' in str(fig.get('description', '')).lower():
                transaction_value = fig.get('amount')
                break

        # Get validated context from Checkpoint C (user-corrected financial values from post-analysis validation)
        validated_context = None
        try:
            validated_result = get_validated_context(checkpoint_id)
            if validated_result.get("has_validated_context"):
                validated_context = validated_result
                corrections_count = len(validated_result.get("financial_corrections", []))
                logging.info(f"[DDProcessEnhanced] Loaded validated context: {corrections_count} financial corrections")
        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Could not load validated context (non-fatal): {e}")

        calc_orchestrator = CalculationOrchestrator(
            transaction_value=transaction_value,
            validated_context=validated_context
        )

        try:
            # Get findings list (pass2_findings may be a dict with 'findings' key or a list)
            if isinstance(pass2_findings, dict):
                findings_list = pass2_findings.get('findings', [])
            else:
                findings_list = pass2_findings

            # Process findings with calculation engine
            enriched_findings = calc_orchestrator.process_pass2_findings(findings_list)

            # Update pass2_findings with enriched data
            if isinstance(pass2_findings, dict):
                pass2_findings['findings'] = enriched_findings
            else:
                pass2_findings = enriched_findings

            calc_summary = calc_orchestrator.get_calculation_summary()
            logging.info(f"[DDProcessEnhanced] Pass 2.5 complete: {calc_summary['successful']} calculations performed, "
                        f"{calc_summary['failed']} failed")

            _save_checkpoint_safely(checkpoint_id, {
                'calculations_performed': calc_summary['successful'],
                'calculations_failed': calc_summary['failed']
            })
        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Pass 2.5 calculation enrichment failed (non-fatal): {e}")

        # ===== PASS 3: Cross-Document Synthesis =====
        _save_checkpoint_safely(checkpoint_id, {
            'current_pass': 3,
            'current_stage': 'pass3_crossdoc'
        })

        # Phase 4: Check if we should use compression + batching
        doc_count = len(doc_dicts)
        use_batching = should_use_batching(doc_count, BATCHING_THRESHOLD)
        compressed_docs = None
        batch_plan = None
        compression_stats = None
        batch_stats = None

        if use_batching:
            # Phase 4: Document Compression + Batching for large document sets
            logging.info(f"[DDProcessEnhanced] Phase 4: Using compression + batching for {doc_count} documents "
                        f"(threshold: {BATCHING_THRESHOLD})")

            # Step 1: Prioritize documents
            _save_checkpoint_safely(checkpoint_id, {
                'current_stage': 'pass3_prioritization',
                'compression_enabled': True,
                'batching_enabled': True
            })

            logging.info("[DDProcessEnhanced] Phase 4 Step 1: Prioritizing documents")
            prioritized_docs = prioritize_all_documents(
                documents=doc_dicts,
                pass2_findings=pass2_findings,
                transaction_type=blueprint.get('transaction_type', 'ma_corporate')
            )
            priority_stats = get_priority_stats(prioritized_docs)
            logging.info(f"[DDProcessEnhanced] Prioritization complete: "
                        f"{priority_stats['by_priority']}")

            # Step 2: Compress documents
            _save_checkpoint_safely(checkpoint_id, {
                'current_stage': 'pass3_compression'
            })

            logging.info("[DDProcessEnhanced] Phase 4 Step 2: Compressing documents with Haiku")

            def compression_progress(current, total, message):
                if current % 10 == 0 or current == total:
                    logging.info(f"[DDProcessEnhanced] Compression progress: {current}/{total}")
                    _save_checkpoint_safely(checkpoint_id, {
                        'current_stage': f'pass3_compression_{current}_of_{total}'
                    })

            compressed_docs = compress_all_documents(
                documents=doc_dicts,
                prioritized_docs=prioritized_docs,
                pass2_findings=pass2_findings,
                claude_client=client,
                progress_callback=compression_progress
            )
            compression_stats = get_compression_stats(compressed_docs)
            logging.info(f"[DDProcessEnhanced] Compression complete: "
                        f"{compression_stats['total_compressed_tokens']:,} tokens "
                        f"({compression_stats['compression_ratio']:.1f}% reduction)")

            # Step 3: Create batch plan
            _save_checkpoint_safely(checkpoint_id, {
                'current_stage': 'pass3_batching',
                'compression_stats': compression_stats
            })

            logging.info("[DDProcessEnhanced] Phase 4 Step 3: Creating batch plan")
            batch_plan = create_batch_plan(
                compressed_docs=compressed_docs,
                strategy=BatchStrategy.MIXED
            )
            batch_stats = get_batch_stats(batch_plan)
            logging.info(f"[DDProcessEnhanced] Batch plan created: "
                        f"{batch_stats['total_batches']} batches, "
                        f"avg {batch_stats['docs_per_batch']['avg']:.1f} docs/batch")

            _save_checkpoint_safely(checkpoint_id, {
                'total_batches': batch_stats['total_batches'],
                'batch_stats': batch_stats
            })

        if use_clustered_pass3:
            # Use hybrid Pass 3 (auto-switches between clustered and batched)
            logging.info("[DDProcessEnhanced] Starting Pass 3: Cross-Document Synthesis (Hybrid)")

            # Group documents into clusters (for non-batched mode)
            clustered_docs = group_documents_by_cluster(doc_dicts)
            cluster_summary = get_cluster_summary(clustered_docs)
            logging.info(f"[DDProcessEnhanced] Document clustering: {cluster_summary['total_clusters']} clusters, "
                        f"{cluster_summary['total_documents']} documents")

            # Define checkpoint callback for progress tracking
            def checkpoint_callback(stage: str = None, data: dict = None):
                cost_summary = client.get_cost_summary()
                update = {
                    'current_stage': f'pass3_{stage}' if stage else 'pass3',
                    'total_input_tokens': cost_summary['total_input_tokens'],
                    'total_output_tokens': cost_summary['total_output_tokens'],
                    'estimated_cost_usd': cost_summary['total_cost_usd'],
                    'cost_by_model': cost_summary['breakdown']
                }
                if data:
                    update.update(data)
                _save_checkpoint_safely(checkpoint_id, update)

            def progress_callback(current, total, message):
                logging.info(f"[DDProcessEnhanced] Pass 3 progress: {current}/{total} - {message}")
                _save_checkpoint_safely(checkpoint_id, {
                    'current_stage': f'pass3_batch_{current}_of_{total}',
                    'batches_completed': current
                })

            pass3_results = run_pass3_hybrid(
                documents=doc_dicts,
                pass1_extractions=pass1_results,
                pass2_findings=pass2_findings,
                blueprint=blueprint,
                client=client,
                compressed_docs=compressed_docs,
                batch_plan=batch_plan,
                checkpoint_callback=checkpoint_callback,
                progress_callback=progress_callback,
                verbose=True,
                force_batching=False  # Let hybrid decide based on doc count
            )

            # Log results based on mode used
            if pass3_results.get('batching_enabled'):
                logging.info(f"[DDProcessEnhanced] Pass 3 (batched) complete: "
                            f"{len(pass3_results.get('all_cross_doc_findings', []))} cross-doc findings, "
                            f"{pass3_results.get('batch_stats', {}).get('total_batches', 0)} batches")
            else:
                logging.info(f"[DDProcessEnhanced] Pass 3 (clustered) complete: "
                            f"{len(pass3_results.get('all_cross_doc_findings', []))} cross-doc findings, "
                            f"{pass3_results.get('clusters_analyzed', 0)} clusters analyzed")
        else:
            # Original Pass 3 (all docs at once)
            logging.info("[DDProcessEnhanced] Starting Pass 3: Cross-Document Synthesis (Original)")
            pass3_results = run_pass3_crossdoc_synthesis(
                doc_dicts,
                pass2_findings,
                blueprint,
                client,
                verbose=False
            )
            logging.info(f"[DDProcessEnhanced] Pass 3 complete: "
                        f"{len(pass3_results.get('conflicts', []))} conflicts, "
                        f"{len(pass3_results.get('cascade_analysis', {}).get('cascade_items', []))} cascade items")

        # Save checkpoint after Pass 3
        cost_summary = client.get_cost_summary()
        _save_checkpoint_safely(checkpoint_id, {
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        # ===== PASS 3.5: Aggregate Financial Calculations =====
        # Aggregate cross-document calculations and resolve dependencies
        calc_aggregates = None
        try:
            _save_checkpoint_safely(checkpoint_id, {
                'current_stage': 'pass3_5_aggregate_calculations'
            })

            logging.info("[DDProcessEnhanced] Starting Pass 3.5: Aggregate Calculations")

            cross_doc_findings = pass3_results.get('cross_doc_findings', []) or pass3_results.get('all_cross_doc_findings', [])
            clusters = pass3_results.get('clusters', [])

            calc_aggregates = calc_orchestrator.process_pass3_aggregates(
                clusters=clusters,
                cross_doc_findings=cross_doc_findings
            )

            logging.info(f"[DDProcessEnhanced] Pass 3.5 complete: Total exposure {calc_aggregates.get('currency', 'ZAR')} "
                        f"{calc_aggregates.get('total_exposure', 0):,.0f}")

            if calc_aggregates.get('transaction_ratio', {}).get('exceeds_transaction'):
                logging.warning("[DDProcessEnhanced] WARNING: Total exposure exceeds transaction value!")

            _save_checkpoint_safely(checkpoint_id, {
                'total_calculated_exposure': calc_aggregates.get('total_exposure', 0),
                'calculation_aggregates': calc_aggregates
            })
        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Pass 3.5 aggregate calculations failed (non-fatal): {e}")

        # ===== PASS 4: Deal Synthesis =====
        _save_checkpoint_safely(checkpoint_id, {
            'current_pass': 4,
            'current_stage': 'pass4_synthesis'
        })

        logging.info("[DDProcessEnhanced] Starting Pass 4: Deal Synthesis (Sonnet)")
        pass4_results = run_pass4_synthesis(
            doc_dicts,
            pass1_results,
            pass2_findings,
            pass3_results,
            client,
            verbose=False,
            validated_context=validated_context
        )

        # Save checkpoint after Pass 4
        cost_summary = client.get_cost_summary()
        _save_checkpoint_safely(checkpoint_id, {
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })
        logging.info("[DDProcessEnhanced] Pass 4 complete")

        # ===== PASS 5: Opus Verification =====
        # Final quality check using Opus to verify deal-blockers and calculations
        verification_result = None
        try:
            _save_checkpoint_safely(checkpoint_id, {
                'current_pass': 5,
                'current_stage': 'pass5_verification'
            })

            logging.info("[DDProcessEnhanced] Starting Pass 5: Opus Verification")

            # Get findings list
            if isinstance(pass2_findings, dict):
                findings_list = pass2_findings.get('findings', [])
            else:
                findings_list = pass2_findings

            # Define checkpoint callback for Pass 5
            def pass5_checkpoint(stage: str):
                _save_checkpoint_safely(checkpoint_id, {
                    'current_stage': f'pass5_{stage}'
                })

            verification_result = run_pass5_verification(
                pass4_results=pass4_results,
                pass3_results=pass3_results,
                pass2_findings=findings_list,
                pass1_results=pass1_results,
                calculation_aggregates=calc_aggregates,
                transaction_context=transaction_context_str,
                client=client,
                verbose=True,
                checkpoint_callback=pass5_checkpoint
            )

            if verification_result and not verification_result.error:
                # Apply verification adjustments to pass4_results
                pass4_results = apply_verification_adjustments(pass4_results, verification_result)

                logging.info(f"[DDProcessEnhanced] Pass 5 complete: "
                            f"{'PASSED' if verification_result.verification_passed else 'FAILED'} "
                            f"({verification_result.overall_confidence:.0%} confidence)")

                if verification_result.critical_issues:
                    logging.warning(f"[DDProcessEnhanced] Pass 5 found {len(verification_result.critical_issues)} critical issues")

                _save_checkpoint_safely(checkpoint_id, {
                    'verification_passed': verification_result.verification_passed,
                    'verification_confidence': verification_result.overall_confidence,
                    'critical_issues_count': len(verification_result.critical_issues)
                })
            else:
                logging.warning(f"[DDProcessEnhanced] Pass 5 verification had error: {verification_result.error if verification_result else 'No result'}")

        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Pass 5 verification failed (non-fatal): {e}")
            # Continue without verification - it's an enhancement, not critical

        # Save final checkpoint after Pass 5
        cost_summary = client.get_cost_summary()
        _save_checkpoint_safely(checkpoint_id, {
            'total_input_tokens': cost_summary['total_input_tokens'],
            'total_output_tokens': cost_summary['total_output_tokens'],
            'estimated_cost_usd': cost_summary['total_cost_usd'],
            'cost_by_model': cost_summary['breakdown']
        })

        return {
            "pass1_results": pass1_results,
            "pass2_findings": pass2_findings,
            "pass3_results": pass3_results,
            "pass4_results": pass4_results,
            "question_summary": question_summary,
            "graph_stats": graph_stats,
            "calculation_aggregates": calc_aggregates,
            "calculation_summary": calc_orchestrator.get_calculation_summary() if calc_orchestrator else None,
            "verification_result": verification_result.to_dict() if verification_result else None
        }

    except Exception as e:
        logging.exception(f"[DDProcessEnhanced] Error in processing passes: {e}")
        return {"error": f"Processing failed: {str(e)}"}


def _run_parallel_passes(
    checkpoint_id: str,
    dd_id: str,
    run_id: str,
    doc_dicts: List[Dict],
    reference_docs: List[Dict],
    blueprint: Dict,
    transaction_context_str: str,
    client: ClaudeClient,
    include_tier3: bool,
    previous_run_id: Optional[str] = None,
    entity_map: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Phase 6: Run all passes using the parallel orchestrator.

    Uses worker pool for parallel document processing, hierarchical synthesis
    for aggregating results, and incremental processing for change detection.
    """
    try:
        # Create orchestrator with client
        orchestrator = create_orchestrator(
            claude_client=client,
            db_session=None,  # We use fresh sessions per operation
            config=OrchestratorConfig.from_env(),
        )

        # Define checkpoint callback
        def checkpoint_callback(stage: str, data: Dict = None):
            update = {'current_stage': f'parallel_{stage}'}
            if data:
                update.update(data)
            _save_checkpoint_safely(checkpoint_id, update)

        # Define progress callback
        def progress_callback(current: int, total: int, message: str):
            logging.info(f"[DDProcessEnhanced] Parallel progress: {current}/{total} - {message}")
            _save_checkpoint_safely(checkpoint_id, {
                'current_stage': message,
                'documents_processed': current
            })

        # Get validated context for parallel orchestrator
        parallel_validated_context = None
        try:
            validated_result = get_validated_context(checkpoint_id)
            if validated_result.get("has_validated_context"):
                parallel_validated_context = validated_result
        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Could not load validated context for parallel (non-fatal): {e}")

        # Run processing through orchestrator
        result = orchestrator.process(
            dd_id=dd_id,
            run_id=run_id,
            documents=doc_dicts,
            blueprint=blueprint,
            transaction_context=transaction_context_str,
            reference_docs=reference_docs,
            previous_run_id=previous_run_id,
            progress_callback=progress_callback,
            checkpoint_callback=checkpoint_callback,
            include_tier3=include_tier3,
            entity_map=entity_map,
            validated_context=parallel_validated_context,
        )

        # Check for errors
        if result.error:
            return {"error": result.error}

        # Build question summary from prioritizer
        from dd_enhanced.core.question_prioritizer import get_summary as get_question_summary
        question_summary = {
            'total_questions': 0,
            'tier1_count': 0,
            'tier2_count': 0,
            'tier3_count': 0,
        }

        # Log parallel processing results
        logging.info(f"[DDProcessEnhanced] Parallel processing complete:")
        logging.info(f"  Mode: {result.mode.value}")
        logging.info(f"  Documents processed: {result.documents_processed}")
        logging.info(f"  Documents from cache: {result.documents_from_cache}")
        logging.info(f"  Documents failed: {result.documents_failed}")
        logging.info(f"  Findings: {len(result.pass2_findings)}")
        logging.info(f"  Duration: {result.duration_seconds:.1f}s")

        if result.partial_results:
            logging.warning(f"[DDProcessEnhanced] Partial results due to {result.documents_failed} failed documents")
            # Save failed document info to checkpoint
            _save_checkpoint_safely(checkpoint_id, {
                'partial_results': True,
                'failed_documents': result.failed_documents[:10],  # Store first 10
                'documents_failed': result.documents_failed
            })

        return {
            "pass1_results": result.pass1_results,
            "pass2_findings": result.pass2_findings,
            "pass3_results": result.pass3_results,
            "pass4_results": result.pass4_results,
            "question_summary": question_summary,
            "graph_stats": result.graph_stats,
            "parallel_stats": {
                "mode": result.mode.value,
                "documents_processed": result.documents_processed,
                "documents_from_cache": result.documents_from_cache,
                "documents_failed": result.documents_failed,
                "duration_seconds": result.duration_seconds,
                "partial_results": result.partial_results,
            },
            "synthesis_results": result.synthesis_results,
        }

    except Exception as e:
        logging.exception(f"[DDProcessEnhanced] Error in parallel processing: {e}")
        return {"error": f"Parallel processing failed: {str(e)}"}


def _store_all_findings(
    dd_id: str,
    owned_by: str,
    doc_dicts: List[Dict],
    pass4_results: Dict,
    pass3_results: Dict,
    blueprint: Dict
) -> Dict[str, Any]:
    """
    Phase 3: Store all findings in database using a fresh session.

    This is a quick operation (~30 seconds max).
    """
    try:
        with transactional_session() as session:
            # Re-query documents to get fresh ORM objects
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()

            # Get or create member and perspective
            member = _get_or_create_member(session, dd_id, owned_by)
            perspective = _get_or_create_perspective(session, member.id, "Enhanced AI Analysis")

            # Create document lookup
            doc_lookup = {doc.original_file_name: doc for doc in documents}

            # Store all findings
            all_findings = pass4_results.get("all_findings", [])
            stored_count = _store_findings(
                session,
                perspective.id,
                all_findings,
                doc_lookup,
                blueprint
            )

            # Store cross-document findings separately
            cross_doc_findings = pass3_results.get("cross_doc_findings", [])
            cross_doc_stored = _store_cross_doc_findings(
                session,
                perspective.id,
                cross_doc_findings,
                doc_lookup
            )

            # Update document processing status
            for doc in documents:
                doc.processing_status = 'processed'

            # Commit all changes
            session.commit()

            return {
                "stored_count": stored_count,
                "cross_doc_stored": cross_doc_stored
            }

    except Exception as e:
        logging.exception(f"[DDProcessEnhanced] Error storing findings: {e}")
        return {"error": f"Failed to store findings: {str(e)}"}


def _update_checkpoint_costs(checkpoint: DDProcessingCheckpoint, client: ClaudeClient):
    """Update checkpoint with current costs from Claude client."""
    cost_summary = client.get_cost_summary()
    checkpoint.total_input_tokens = cost_summary['total_input_tokens']
    checkpoint.total_output_tokens = cost_summary['total_output_tokens']
    checkpoint.estimated_cost_usd = cost_summary['total_cost_usd']
    checkpoint.cost_by_model = cost_summary['breakdown']


def _save_checkpoint_safely(checkpoint_id: str, updates: Dict[str, Any]):
    """
    Save checkpoint updates using a fresh database session.

    This is critical for long-running processes where the main session
    may have timed out during Claude API calls.
    """
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
                logging.info(f"[DDProcessEnhanced] Checkpoint saved: {updates.get('current_stage', 'unknown')}")
    except Exception as e:
        logging.warning(f"[DDProcessEnhanced] Failed to save checkpoint (non-fatal): {e}")


def _build_transaction_context_from_draft(draft: DDWizardDraft) -> Dict[str, Any]:
    """Build transaction context dict from wizard draft for question prioritization."""
    context = {}

    # Parse JSON arrays from text fields
    if draft.known_concerns:
        try:
            context['known_concerns'] = json.loads(draft.known_concerns)
        except (json.JSONDecodeError, TypeError):
            context['known_concerns'] = []

    if draft.critical_priorities:
        try:
            context['critical_priorities'] = json.loads(draft.critical_priorities)
        except (json.JSONDecodeError, TypeError):
            context['critical_priorities'] = []

    if draft.known_deal_breakers:
        try:
            context['known_deal_breakers'] = json.loads(draft.known_deal_breakers)
        except (json.JSONDecodeError, TypeError):
            context['known_deal_breakers'] = []

    if draft.deprioritized_areas:
        try:
            context['deprioritized_areas'] = json.loads(draft.deprioritized_areas)
        except (json.JSONDecodeError, TypeError):
            context['deprioritized_areas'] = []

    return context


def _map_transaction_type_to_code(transaction_type: str) -> str:
    """Map display transaction type to blueprint code."""
    mapping = {
        "Mining & Resources": "mining_resources",
        "Mining/Resources": "mining_resources",
        "M&A / Corporate": "ma_corporate",
        "M&A Corporate": "ma_corporate",
        "Corporate M&A": "ma_corporate",
        "Banking & Finance": "banking_finance",
        "Real Estate & Property": "real_estate",
        "Real Estate": "real_estate",
        "Competition & Regulatory": "competition_regulatory",
        "Employment & Labor": "employment_labor",
        "IP & Technology": "ip_technology",
        "BEE & Transformation": "bee_transformation",
        "Energy & Power": "energy_power",
        "Infrastructure & PPP": "infrastructure_ppp",
        "Capital Markets": "capital_markets",
        "Private Equity / VC": "private_equity_vc",
        "Restructuring & Insolvency": "restructuring_insolvency",
        "Financial Services": "financial_services",
        "General": "ma_corporate"  # Default fallback
    }

    # Try exact match first
    if transaction_type in mapping:
        return mapping[transaction_type]

    # Try case-insensitive partial match
    lower_type = transaction_type.lower()
    for key, code in mapping.items():
        if key.lower() in lower_type or lower_type in key.lower():
            return code

    return "ma_corporate"  # Default


def _extract_document_content(doc: Document) -> str:
    """Extract text content from a document."""
    from DDProcessAllDev import extract_text_from_file_with_extension

    dev_config = get_dev_config()
    local_storage_path = dev_config.get("local_storage_path", "/tmp/dd_storage")
    file_path = os.path.join(local_storage_path, "docs", str(doc.id))

    extension = doc.type if doc.type else os.path.splitext(doc.original_file_name)[1].lstrip('.')

    try:
        return extract_text_from_file_with_extension(file_path, extension)
    except Exception as e:
        logging.warning(f"[DDProcessEnhanced] Could not extract content from {doc.original_file_name}: {e}")
        return ""


def _classify_document_type(filename: str, folder: Optional[Folder]) -> str:
    """Classify document type based on filename and folder."""
    filename_lower = filename.lower()
    folder_path = folder.path.lower() if folder else ""

    # Constitutional documents
    if any(term in filename_lower for term in ['moi', 'memorandum of incorporation', 'articles']):
        return 'constitutional'
    if any(term in filename_lower for term in ['shareholder', 'sha', 'shareholders agreement']):
        return 'constitutional'

    # Governance documents
    if any(term in filename_lower for term in ['board resolution', 'resolution', 'minutes']):
        return 'governance'

    # Regulatory documents
    if any(term in filename_lower for term in ['mining right', 'license', 'permit', 'certificate']):
        return 'regulatory'
    if any(term in filename_lower for term in ['environmental', 'empr', 'water use']):
        return 'regulatory'

    # Financial documents
    if any(term in filename_lower for term in ['financial', 'afs', 'annual report', 'audit']):
        return 'financial'

    # Employment documents
    if any(term in filename_lower for term in ['employment', 'contract of employment', 'service agreement']):
        return 'employment'

    # Default to contract
    return 'contract'


def _identify_reference_documents(doc_dicts: List[Dict], blueprint: Dict) -> List[Dict]:
    """Identify reference documents based on blueprint patterns."""
    reference_docs = []
    patterns = blueprint.get("reference_documents", {}).get("always_include", [])

    for doc in doc_dicts:
        filename_lower = doc["filename"].lower()
        doc_type = doc.get("doc_type", "")

        # Check if document matches any reference pattern
        for pattern_info in patterns:
            pattern = pattern_info.get("pattern", "").lower()
            if pattern and (pattern in filename_lower or doc_type in ["constitutional", "governance"]):
                reference_docs.append(doc)
                break

        # Also include constitutional and governance docs by type
        if doc_type in ["constitutional", "governance"] and doc not in reference_docs:
            reference_docs.append(doc)

    return reference_docs


def _build_transaction_context(blueprint: Dict, dd_name: str, briefing: str) -> str:
    """Build transaction context from blueprint."""
    context_parts = [
        f"This is a {blueprint.get('transaction_type', 'corporate')} transaction.",
        f"Project Name: {dd_name}",
    ]

    if briefing:
        context_parts.append(f"Briefing: {briefing}")

    # Add jurisdiction and legislation from blueprint
    if blueprint.get("jurisdiction"):
        context_parts.append(f"Jurisdiction: {blueprint['jurisdiction']}")

    legislation = blueprint.get("primary_legislation", [])
    if legislation:
        context_parts.append(f"Primary Legislation: {', '.join(legislation[:3])}")

    context_parts.append("\nKey considerations from blueprint:")

    # Add deal blocker definitions
    deal_blockers = blueprint.get("deal_blockers", [])
    if deal_blockers:
        context_parts.append("Deal Blockers to watch for:")
        for blocker in deal_blockers[:5]:
            context_parts.append(f"  - {blocker.get('description', '')}")

    return "\n".join(context_parts)


def _get_or_create_member(session, dd_id: str, email: str) -> DueDiligenceMember:
    """Get or create a DD member."""
    member = session.query(DueDiligenceMember).filter(
        DueDiligenceMember.dd_id == dd_id,
        DueDiligenceMember.member_email == email
    ).first()

    if not member:
        member = DueDiligenceMember(dd_id=dd_id, member_email=email)
        session.add(member)
        session.flush()

    return member


def _get_or_create_perspective(session, member_id: str, lens: str) -> Perspective:
    """Get or create a perspective."""
    perspective = session.query(Perspective).filter(
        Perspective.member_id == member_id,
        Perspective.lens == lens
    ).first()

    if not perspective:
        perspective = Perspective(member_id=member_id, lens=lens)
        session.add(perspective)
        session.flush()

    return perspective


def _store_findings(
    session,
    perspective_id: str,
    findings: List[Dict],
    doc_lookup: Dict[str, Document],
    blueprint: Dict
) -> int:
    """Store findings in the database."""
    stored_count = 0
    risk_cache = {}  # Cache risk categories

    for finding in findings:
        try:
            # Get or create risk category
            category = finding.get("category", "General")
            if category not in risk_cache:
                risk = session.query(PerspectiveRisk).filter(
                    PerspectiveRisk.perspective_id == perspective_id,
                    PerspectiveRisk.category == category
                ).first()

                if not risk:
                    # Get category description from blueprint
                    cat_desc = _get_category_description(blueprint, category)
                    risk = PerspectiveRisk(
                        perspective_id=perspective_id,
                        category=category,
                        detail=cat_desc
                    )
                    session.add(risk)
                    session.flush()

                risk_cache[category] = risk

            risk = risk_cache[category]

            # Get document ID
            source_doc = finding.get("source_document", "")
            doc = doc_lookup.get(source_doc)
            doc_id = doc.id if doc else None

            # Map severity to status
            severity = finding.get("severity", "medium")
            status = _map_severity_to_status(severity)

            # Extract financial exposure
            financial_exposure = finding.get("financial_exposure", {})
            exposure_amount = financial_exposure.get("amount") if isinstance(financial_exposure, dict) else None
            exposure_currency = financial_exposure.get("currency", "ZAR") if isinstance(financial_exposure, dict) else "ZAR"
            exposure_calc = financial_exposure.get("calculation", "") if isinstance(financial_exposure, dict) else ""

            # Extract reasoning (Chain of Thought)
            reasoning_data = finding.get("reasoning")
            reasoning_json = json.dumps(reasoning_data) if reasoning_data else None

            # Create finding with enhanced fields
            db_finding = PerspectiveRiskFinding(
                perspective_risk_id=risk.id,
                document_id=doc_id,
                phrase=finding.get("description", "")[:2000],
                page_number=finding.get("clause_reference", ""),
                actual_page_number=finding.get("actual_page_number"),  # Integer page from [PAGE X] markers
                status=status,
                finding_type=finding.get("finding_type", "negative"),
                confidence_score=0.85,
                requires_action=finding.get("deal_impact") in ["deal_blocker", "condition_precedent"],
                action_priority=_map_deal_impact_to_priority(finding.get("deal_impact")),
                direct_answer=finding.get("action_required", "")[:500] if finding.get("action_required") else "",
                evidence_quote=finding.get("evidence_quote", "")[:500] if finding.get("evidence_quote") else "",
                # Enhanced DD fields
                deal_impact=finding.get("deal_impact", "none") if finding.get("deal_impact") else "none",
                financial_exposure_amount=exposure_amount,
                financial_exposure_currency=exposure_currency,
                financial_exposure_calculation=exposure_calc[:1000] if exposure_calc else None,
                clause_reference=finding.get("clause_reference", "")[:100] if finding.get("clause_reference") else None,
                cross_doc_source=None,  # Not a cross-doc finding
                analysis_pass=finding.get("pass", 2),
                # Chain of Thought reasoning
                reasoning=reasoning_json
            )
            session.add(db_finding)
            stored_count += 1

        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Could not store finding: {e}")

    return stored_count


def _store_cross_doc_findings(
    session,
    perspective_id: str,
    findings: List[Dict],
    doc_lookup: Dict[str, Document]
) -> int:
    """Store cross-document findings with enhanced fields."""
    stored_count = 0

    # Get or create cross-document risk category
    risk = session.query(PerspectiveRisk).filter(
        PerspectiveRisk.perspective_id == perspective_id,
        PerspectiveRisk.category == "Cross-Document Analysis"
    ).first()

    if not risk:
        risk = PerspectiveRisk(
            perspective_id=perspective_id,
            category="Cross-Document Analysis",
            detail="Issues identified by analyzing multiple documents together"
        )
        session.add(risk)
        session.flush()

    for finding in findings:
        try:
            severity = finding.get("severity", "high")
            status = _map_severity_to_status(severity)

            # Extract financial exposure for cross-doc findings
            financial_exposure = finding.get("financial_exposure", {})
            exposure_amount = financial_exposure.get("amount") if isinstance(financial_exposure, dict) else None
            exposure_currency = financial_exposure.get("currency", "ZAR") if isinstance(financial_exposure, dict) else "ZAR"
            exposure_calc = financial_exposure.get("calculation_basis", "") if isinstance(financial_exposure, dict) else ""

            # Build cross_doc_source from source documents
            source_docs = finding.get("source_documents", [])
            cross_doc_source = " vs ".join(source_docs[:3]) if source_docs else finding.get("source_document", "")

            # Extract reasoning (Chain of Thought)
            reasoning_data = finding.get("reasoning")
            reasoning_json = json.dumps(reasoning_data) if reasoning_data else None

            db_finding = PerspectiveRiskFinding(
                perspective_risk_id=risk.id,
                document_id=None,  # Cross-doc findings may not have single source
                phrase=finding.get("description", "")[:2000],
                page_number=finding.get("clause_reference", ""),
                status=status,
                finding_type=finding.get("finding_type", "conflict"),
                confidence_score=0.9,
                requires_action=True,
                action_priority=_map_deal_impact_to_priority(finding.get("deal_impact", "condition_precedent")),
                direct_answer=finding.get("action_required", "")[:500] if finding.get("action_required") else "",
                evidence_quote=finding.get("evidence_quote", "")[:500] if finding.get("evidence_quote") else "",
                # Enhanced DD fields for cross-doc findings
                deal_impact=finding.get("deal_impact", "condition_precedent") if finding.get("deal_impact") else "condition_precedent",
                financial_exposure_amount=exposure_amount,
                financial_exposure_currency=exposure_currency,
                financial_exposure_calculation=exposure_calc[:1000] if exposure_calc else None,
                clause_reference=finding.get("clause_reference", "")[:100] if finding.get("clause_reference") else None,
                cross_doc_source=cross_doc_source[:200] if cross_doc_source else None,
                analysis_pass=3,  # Cross-doc findings are always from Pass 3
                # Chain of Thought reasoning
                reasoning=reasoning_json
            )
            session.add(db_finding)
            stored_count += 1

        except Exception as e:
            logging.warning(f"[DDProcessEnhanced] Could not store cross-doc finding: {e}")

    return stored_count


def _get_category_description(blueprint: Dict, category: str) -> str:
    """Get category description from blueprint."""
    for cat in blueprint.get("risk_categories", []):
        if cat.get("name") == category:
            return cat.get("description", f"Risks related to {category}")
    return f"Risks related to {category}"


def _map_severity_to_status(severity: str) -> str:
    """Map severity to Red/Amber/Green status."""
    mapping = {
        "critical": "Red",
        "high": "Red",
        "medium": "Amber",
        "low": "Green"
    }
    return mapping.get(severity.lower(), "Amber")


def _map_deal_impact_to_priority(deal_impact: str) -> str:
    """Map deal impact to priority."""
    mapping = {
        "deal_blocker": "critical",
        "condition_precedent": "high",
        "price_chip": "medium",
        "warranty_indemnity": "medium",
        "post_closing": "low",
        "noted": "low"
    }
    return mapping.get(deal_impact, "medium")


def _count_by_severity(findings: List[Dict]) -> Dict[str, int]:
    """Count findings by severity."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "medium").lower()
        if sev in counts:
            counts[sev] += 1
    return counts


def _find_doc_extraction(pass1_results: Dict[str, Any], doc_name: str) -> Optional[Dict[str, Any]]:
    """
    Find Pass 1 extraction data for a specific document.

    Pass 1 results are organized by extraction type (key_dates, financial_figures, etc.)
    with each item having a source_document field. We need to reorganize by document.
    """
    doc_extraction = {
        'key_dates': [],
        'financial_figures': [],
        'coc_clauses': [],
        'consent_requirements': [],
        'parties': [],
        'covenants': []
    }

    # Check if pass1_results has the expected structure
    if not pass1_results:
        return None

    # Extract items for this document from each category
    for date_item in pass1_results.get('key_dates', []):
        if date_item.get('source_document') == doc_name:
            doc_extraction['key_dates'].append(date_item)

    for fin_item in pass1_results.get('financial_figures', []):
        if fin_item.get('source_document') == doc_name:
            doc_extraction['financial_figures'].append(fin_item)

    for coc_item in pass1_results.get('coc_clauses', []):
        if coc_item.get('source_document') == doc_name:
            doc_extraction['coc_clauses'].append(coc_item)

    for consent_item in pass1_results.get('consent_requirements', []):
        if consent_item.get('source_document') == doc_name:
            doc_extraction['consent_requirements'].append(consent_item)

    for party_item in pass1_results.get('parties', []):
        if party_item.get('source_document') == doc_name:
            doc_extraction['parties'].append(party_item)

    for covenant_item in pass1_results.get('covenants', []):
        if covenant_item.get('source_document') == doc_name:
            doc_extraction['covenants'].append(covenant_item)

    # Return None if no extractions found for this document
    has_data = any(len(v) > 0 for v in doc_extraction.values())
    return doc_extraction if has_data else None
