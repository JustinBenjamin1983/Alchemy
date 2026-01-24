"""
Parallel processing orchestrator for DD analysis.

Auto-switches between sequential and parallel processing based on document count.
Threshold is configurable via DD_PARALLEL_THRESHOLD environment variable.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class OrchestratorConfig:
    """Configuration for the parallel orchestrator."""
    # Processing thresholds
    parallel_threshold: int = 100  # Switch to parallel for 100+ docs

    # Worker configuration
    max_workers: int = 10

    # Rate limiting
    requests_per_minute: int = 50
    tokens_per_minute: int = 100000
    max_concurrent: int = 10

    # Synthesis configuration
    opus_threshold: int = 300  # Use Opus for 300+ docs
    batch_size: int = 20  # Documents per synthesis batch

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    # Incremental processing
    enable_incremental: bool = True

    @classmethod
    def from_env(cls) -> 'OrchestratorConfig':
        """Load configuration from environment variables."""
        return cls(
            parallel_threshold=int(os.environ.get("DD_PARALLEL_THRESHOLD", "100")),
            max_workers=int(os.environ.get("DD_PARALLEL_WORKERS", "10")),
            requests_per_minute=int(os.environ.get("CLAUDE_REQUESTS_PER_MINUTE", "50")),
            tokens_per_minute=int(os.environ.get("CLAUDE_TOKENS_PER_MINUTE", "100000")),
            max_concurrent=int(os.environ.get("CLAUDE_MAX_CONCURRENT", "10")),
            opus_threshold=int(os.environ.get("DD_OPUS_THRESHOLD", "300")),
            batch_size=int(os.environ.get("DD_BATCH_SIZE", "20")),
            max_retries=int(os.environ.get("DD_MAX_RETRIES", "3")),
            enable_incremental=os.environ.get("DD_ENABLE_INCREMENTAL", "true").lower() == "true",
        )


@dataclass
class ProcessingResult:
    """Result from processing a DD project."""
    success: bool
    mode: ProcessingMode

    # Pass results
    pass1_results: Dict[str, Any] = field(default_factory=dict)
    pass2_findings: List[Dict] = field(default_factory=list)
    pass3_results: Dict[str, Any] = field(default_factory=dict)
    pass4_results: Dict[str, Any] = field(default_factory=dict)
    pass5_results: Dict[str, Any] = field(default_factory=dict)  # Verification results

    # Graph stats
    graph_stats: Optional[Any] = None

    # Synthesis results (for parallel mode)
    synthesis_results: Optional[Dict[str, Any]] = None

    # Statistics
    documents_processed: int = 0
    documents_from_cache: int = 0
    documents_failed: int = 0
    failed_documents: List[Dict] = field(default_factory=list)

    # Cost tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Error handling
    error: Optional[str] = None
    partial_results: bool = False

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of processing results."""
        return {
            'success': self.success,
            'mode': self.mode.value,
            'documents_processed': self.documents_processed,
            'documents_from_cache': self.documents_from_cache,
            'documents_failed': self.documents_failed,
            'partial_results': self.partial_results,
            'findings_count': len(self.pass2_findings),
            'duration_seconds': self.duration_seconds,
            'cost_usd': self.estimated_cost_usd,
        }


class ParallelOrchestrator:
    """
    Orchestrates DD processing with adaptive sequential/parallel mode selection.

    Features:
    - Auto-switches based on document count
    - Parallel document processing with job queue
    - Hierarchical synthesis for large document sets
    - Incremental processing with change detection
    - Graceful degradation on failures
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        claude_client: Optional[Any] = None,
        db_session: Optional[Any] = None,
    ):
        self.config = config or OrchestratorConfig.from_env()
        self.claude_client = claude_client
        self.db_session = db_session

        # Initialize components lazily
        self._job_queue = None
        self._rate_limiter = None
        self._worker_pool = None
        self._change_detector = None
        self._synthesizer = None

        # Processing state
        self._lock = threading.Lock()
        self._cancelled = False

    def determine_mode(self, doc_count: int) -> ProcessingMode:
        """Determine processing mode based on document count."""
        if doc_count >= self.config.parallel_threshold:
            logger.info(f"Document count {doc_count} >= threshold {self.config.parallel_threshold}, using PARALLEL mode")
            return ProcessingMode.PARALLEL
        else:
            logger.info(f"Document count {doc_count} < threshold {self.config.parallel_threshold}, using SEQUENTIAL mode")
            return ProcessingMode.SEQUENTIAL

    def process(
        self,
        dd_id: str,
        run_id: str,
        documents: List[Dict[str, Any]],
        blueprint: Dict[str, Any],
        transaction_context: str,
        reference_docs: List[Dict[str, Any]],
        previous_run_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        checkpoint_callback: Optional[Callable[[str, Dict], None]] = None,
        include_tier3: bool = False,
        entity_map: Optional[List[Dict[str, Any]]] = None,
        validated_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        Process all documents in a DD project.

        Automatically selects sequential or parallel mode based on document count.

        Args:
            dd_id: DD project ID
            run_id: Current processing run ID
            documents: List of document dicts to process
            blueprint: Transaction type blueprint
            transaction_context: Context string for prompts
            reference_docs: Reference documents for analysis
            previous_run_id: Optional previous run ID for incremental processing
            progress_callback: Optional callback(current, total, message)
            checkpoint_callback: Optional callback(stage, data)
            include_tier3: Whether to include tier 3 questions
            entity_map: Optional list of entity dicts for party validation
            validated_context: User-validated corrections from Checkpoint C (post-analysis)

        Returns:
            ProcessingResult with all findings and statistics
        """
        started_at = datetime.utcnow()
        doc_count = len(documents)
        mode = self.determine_mode(doc_count)

        result = ProcessingResult(
            success=False,
            mode=mode,
            started_at=started_at,
            documents_processed=0,
        )

        try:
            if checkpoint_callback:
                checkpoint_callback('mode_selected', {
                    'mode': mode.value,
                    'document_count': doc_count,
                    'parallel_threshold': self.config.parallel_threshold,
                })

            if mode == ProcessingMode.SEQUENTIAL:
                result = self._process_sequential(
                    dd_id=dd_id,
                    run_id=run_id,
                    documents=documents,
                    blueprint=blueprint,
                    transaction_context=transaction_context,
                    reference_docs=reference_docs,
                    previous_run_id=previous_run_id,
                    progress_callback=progress_callback,
                    checkpoint_callback=checkpoint_callback,
                    include_tier3=include_tier3,
                    entity_map=entity_map,
                    validated_context=validated_context,
                )
            else:
                result = self._process_parallel(
                    dd_id=dd_id,
                    run_id=run_id,
                    documents=documents,
                    blueprint=blueprint,
                    transaction_context=transaction_context,
                    reference_docs=reference_docs,
                    previous_run_id=previous_run_id,
                    progress_callback=progress_callback,
                    checkpoint_callback=checkpoint_callback,
                    include_tier3=include_tier3,
                    entity_map=entity_map,
                    validated_context=validated_context,
                )

            result.completed_at = datetime.utcnow()
            result.duration_seconds = (result.completed_at - started_at).total_seconds()

            return result

        except Exception as e:
            logger.exception(f"Processing failed: {e}")
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (result.completed_at - started_at).total_seconds()
            return result

    def _process_sequential(
        self,
        dd_id: str,
        run_id: str,
        documents: List[Dict[str, Any]],
        blueprint: Dict[str, Any],
        transaction_context: str,
        reference_docs: List[Dict[str, Any]],
        previous_run_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        checkpoint_callback: Optional[Callable] = None,
        include_tier3: bool = False,
        entity_map: Optional[List[Dict[str, Any]]] = None,
        validated_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        Process documents sequentially (existing behavior).

        This is the standard processing path for smaller document sets.
        Delegates to existing pass functions.
        """
        from dd_enhanced.core.pass1_extract import run_pass1_extraction
        from dd_enhanced.core.pass2_analyze import run_pass2_analysis
        from dd_enhanced.core.pass3_clustered import run_pass3_hybrid
        from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis
        from dd_enhanced.core.pass5_verify import run_pass5_verification
        from dd_enhanced.core.question_prioritizer import prioritize_questions

        result = ProcessingResult(
            success=False,
            mode=ProcessingMode.SEQUENTIAL,
            started_at=datetime.utcnow(),
        )

        doc_count = len(documents)

        # Check for incremental processing
        documents_to_process = documents
        cached_results = {}

        if self.config.enable_incremental and previous_run_id and self.db_session:
            if checkpoint_callback:
                checkpoint_callback('change_detection', {})

            from dd_enhanced.core.incremental import ChangeDetector
            detector = ChangeDetector(self.db_session)
            change_set = detector.detect_changes(
                dd_id=dd_id,
                current_run_id=run_id,
                previous_run_id=previous_run_id,
                current_documents=documents
            )

            if not change_set.has_changes:
                logger.info("No changes detected, using cached results")
                # Return cached results
                cached_results = detector.get_reusable_results(
                    previous_run_id,
                    [d.document_id for d in change_set.unchanged_documents]
                )
                result.documents_from_cache = len(cached_results)
            else:
                # Only process changed documents
                documents_to_process = [
                    d for d in documents
                    if str(d.get('id')) in change_set.documents_to_process
                ]
                result.documents_from_cache = len(change_set.unchanged_documents)
                logger.info(f"Processing {len(documents_to_process)} changed documents, "
                           f"reusing {result.documents_from_cache} cached results")

        # Pass 1: Extract & Index
        if checkpoint_callback:
            checkpoint_callback('pass1_extraction', {'document_count': len(documents_to_process)})

        if progress_callback:
            progress_callback(0, 5, "Running Pass 1: Extract & Index")

        pass1_results = run_pass1_extraction(
            documents_to_process,
            self.claude_client,
            verbose=False
        )
        result.pass1_results = pass1_results

        # Build knowledge graph
        if checkpoint_callback:
            checkpoint_callback('graph_building', {})

        graph_stats = self._build_knowledge_graph(
            dd_id, documents_to_process, pass1_results, checkpoint_callback
        )
        result.graph_stats = graph_stats

        # Prioritize questions
        from dd_enhanced.core.question_prioritizer import get_summary as get_question_summary
        prioritized_questions = prioritize_questions(
            blueprint=blueprint,
            transaction_context={},
            include_tier3=include_tier3,
            max_questions=150
        )

        # Pass 2: Per-Document Analysis
        if checkpoint_callback:
            checkpoint_callback('pass2_analysis', {})

        if progress_callback:
            progress_callback(1, 5, "Running Pass 2: Per-Document Analysis")

        # Create reference doc objects
        class RefDoc:
            def __init__(self, d):
                self.filename = d['filename']
                self.text = d['text']
                self.doc_type = d.get('doc_type', '')

        ref_doc_objects = [RefDoc(d) for d in reference_docs]

        pass2_findings = run_pass2_analysis(
            documents_to_process,
            ref_doc_objects,
            blueprint,
            self.claude_client,
            transaction_context=transaction_context,
            prioritized_questions=prioritized_questions,
            verbose=False,
            entity_map=entity_map
        )
        result.pass2_findings = pass2_findings

        # Pass 3: Cross-Document Synthesis
        if checkpoint_callback:
            checkpoint_callback('pass3_crossdoc', {})

        if progress_callback:
            progress_callback(2, 5, "Running Pass 3: Cross-Document Synthesis")

        pass3_results = run_pass3_hybrid(
            documents=documents,  # Use all documents for cross-doc
            pass1_extractions=pass1_results,
            pass2_findings=pass2_findings,
            blueprint=blueprint,
            client=self.claude_client,
            verbose=False
        )
        result.pass3_results = pass3_results

        # Pass 4: Deal Synthesis
        if checkpoint_callback:
            checkpoint_callback('pass4_synthesis', {})

        if progress_callback:
            progress_callback(3, 5, "Running Pass 4: Deal Synthesis")

        pass4_results = run_pass4_synthesis(
            documents,
            pass1_results,
            pass2_findings,
            pass3_results,
            self.claude_client,
            verbose=False,
            validated_context=validated_context
        )
        result.pass4_results = pass4_results

        # Pass 5: Verification (QC)
        if checkpoint_callback:
            checkpoint_callback('pass5_verification', {})

        if progress_callback:
            progress_callback(4, 5, "Running Pass 5: Verification")

        pass5_result = run_pass5_verification(
            pass4_results=pass4_results,
            pass3_results=pass3_results,
            pass2_findings=pass2_findings,
            pass1_results=pass1_results,
            calculation_aggregates=pass3_results.get('calculation_aggregates'),
            transaction_context=transaction_context,
            client=self.claude_client,
            verbose=False,
            checkpoint_callback=checkpoint_callback,
        )
        result.pass5_results = pass5_result.to_dict() if hasattr(pass5_result, 'to_dict') else pass5_result

        # Update cost tracking
        if self.claude_client:
            cost_summary = self.claude_client.get_cost_summary()
            result.total_input_tokens = cost_summary.get('total_input_tokens', 0)
            result.total_output_tokens = cost_summary.get('total_output_tokens', 0)
            result.estimated_cost_usd = cost_summary.get('total_cost_usd', 0.0)

        result.success = True
        result.documents_processed = len(documents_to_process)

        if progress_callback:
            progress_callback(5, 5, "Processing complete")

        return result

    def _process_parallel(
        self,
        dd_id: str,
        run_id: str,
        documents: List[Dict[str, Any]],
        blueprint: Dict[str, Any],
        transaction_context: str,
        reference_docs: List[Dict[str, Any]],
        previous_run_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        checkpoint_callback: Optional[Callable] = None,
        include_tier3: bool = False,
        entity_map: Optional[List[Dict[str, Any]]] = None,
        validated_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        Process documents in parallel using worker pool.

        Uses job queue for document distribution and hierarchical
        synthesis for aggregating results.
        """
        from dd_enhanced.core.queue import create_job_queue, RateLimiter, RateLimitConfig
        from dd_enhanced.core.queue.worker_pool import WorkerPool, WorkerConfig
        from dd_enhanced.core.synthesis import create_synthesis_pipeline, SynthesisLevel
        from dd_enhanced.core.pass1_extract import run_pass1_extraction
        from dd_enhanced.core.question_prioritizer import prioritize_questions

        result = ProcessingResult(
            success=False,
            mode=ProcessingMode.PARALLEL,
            started_at=datetime.utcnow(),
        )

        doc_count = len(documents)

        # Initialize rate limiter
        rate_config = RateLimitConfig(
            requests_per_minute=self.config.requests_per_minute,
            tokens_per_minute=self.config.tokens_per_minute,
            max_concurrent=self.config.max_concurrent,
        )
        rate_limiter = RateLimiter(rate_config)

        # Initialize job queue
        job_queue = create_job_queue()

        # Check for incremental processing
        documents_to_process = documents
        cached_pass1 = {}
        cached_pass2 = {}

        if self.config.enable_incremental and previous_run_id and self.db_session:
            if checkpoint_callback:
                checkpoint_callback('change_detection', {'mode': 'parallel'})

            from dd_enhanced.core.incremental import ChangeDetector
            detector = ChangeDetector(self.db_session)
            change_set = detector.detect_changes(
                dd_id=dd_id,
                current_run_id=run_id,
                previous_run_id=previous_run_id,
                current_documents=documents
            )

            unchanged_ids = [d.document_id for d in change_set.unchanged_documents]
            if unchanged_ids:
                reusable = detector.get_reusable_results(previous_run_id, unchanged_ids)
                for doc_id, results in reusable.items():
                    if results.get('pass1_completed'):
                        cached_pass1[doc_id] = results.get('pass1_result', {})
                    if results.get('pass2_completed'):
                        cached_pass2[doc_id] = results.get('pass2_findings', [])

                result.documents_from_cache = len(reusable)

            # Only process changed documents
            documents_to_process = [
                d for d in documents
                if str(d.get('id')) in change_set.documents_to_process
            ]

            logger.info(f"Parallel processing: {len(documents_to_process)} changed, "
                       f"{result.documents_from_cache} cached")

        # ===== PASS 1: Parallel Extraction =====
        if checkpoint_callback:
            checkpoint_callback('pass1_parallel', {
                'documents_to_process': len(documents_to_process),
                'cached': result.documents_from_cache
            })

        if progress_callback:
            progress_callback(0, 6, f"Running Pass 1: Parallel extraction ({len(documents_to_process)} docs)")

        # For Pass 1, we still run sequentially but could parallelize in future
        # The main bottleneck is Pass 2 which we parallelize below
        pass1_results = run_pass1_extraction(
            documents_to_process,
            self.claude_client,
            verbose=False
        )
        result.pass1_results = pass1_results

        # Merge cached Pass 1 results
        for doc_id, cached_result in cached_pass1.items():
            # Merge into pass1_results structure
            for key in ['key_dates', 'financial_figures', 'coc_clauses', 'consent_requirements', 'parties']:
                if key in cached_result:
                    if key not in pass1_results:
                        pass1_results[key] = []
                    pass1_results[key].extend(cached_result.get(key, []))

        # ===== Build Knowledge Graph =====
        if checkpoint_callback:
            checkpoint_callback('graph_building', {'mode': 'parallel'})

        graph_stats = self._build_knowledge_graph(
            dd_id, documents, pass1_results, checkpoint_callback
        )
        result.graph_stats = graph_stats

        # Prioritize questions
        prioritized_questions = prioritize_questions(
            blueprint=blueprint,
            transaction_context={},
            include_tier3=include_tier3,
            max_questions=150
        )

        # ===== PASS 2: Parallel Analysis =====
        if checkpoint_callback:
            checkpoint_callback('pass2_parallel', {
                'documents': len(documents_to_process),
                'workers': self.config.max_workers
            })

        if progress_callback:
            progress_callback(1, 6, f"Running Pass 2: Parallel analysis ({self.config.max_workers} workers)")

        # Create reference doc objects
        class RefDoc:
            def __init__(self, d):
                self.filename = d['filename']
                self.text = d['text']
                self.doc_type = d.get('doc_type', '')

        ref_doc_objects = [RefDoc(d) for d in reference_docs]

        # Parallel Pass 2 processing
        all_findings = []
        failed_docs = []
        processed_count = 0

        def process_document(doc: Dict) -> Dict[str, Any]:
            """Process a single document through Pass 2."""
            from dd_enhanced.core.pass2_analyze import analyze_single_document

            try:
                with rate_limiter:
                    findings = analyze_single_document(
                        doc,
                        ref_doc_objects,
                        blueprint,
                        self.claude_client,
                        transaction_context=transaction_context,
                        prioritized_questions=prioritized_questions,
                        entity_map=entity_map,
                    )
                    return {
                        'success': True,
                        'doc_id': doc.get('id'),
                        'findings': findings
                    }
            except Exception as e:
                logger.error(f"Failed to process document {doc.get('filename')}: {e}")
                return {
                    'success': False,
                    'doc_id': doc.get('id'),
                    'error': str(e)
                }

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(process_document, doc): doc
                for doc in documents_to_process
            }

            for future in as_completed(futures):
                doc = futures[future]
                try:
                    result_data = future.result()
                    if result_data['success']:
                        all_findings.extend(result_data['findings'])
                        processed_count += 1
                    else:
                        failed_docs.append({
                            'doc_id': result_data['doc_id'],
                            'error': result_data.get('error', 'Unknown error')
                        })
                except Exception as e:
                    failed_docs.append({
                        'doc_id': doc.get('id'),
                        'error': str(e)
                    })

                # Update progress
                total = len(documents_to_process)
                current = processed_count + len(failed_docs)
                if progress_callback and current % 10 == 0:
                    progress_callback(1, 5, f"Pass 2: {current}/{total} documents processed")

        # Merge cached Pass 2 findings
        for doc_id, cached_findings in cached_pass2.items():
            if isinstance(cached_findings, list):
                all_findings.extend(cached_findings)

        result.pass2_findings = all_findings
        result.documents_processed = processed_count
        result.documents_failed = len(failed_docs)
        result.failed_documents = failed_docs

        if failed_docs:
            logger.warning(f"Failed to process {len(failed_docs)} documents")
            result.partial_results = True

        # ===== PASS 3: Hierarchical Cross-Document Synthesis =====
        if checkpoint_callback:
            checkpoint_callback('pass3_hierarchical', {
                'findings_count': len(all_findings),
                'batch_size': self.config.batch_size
            })

        if progress_callback:
            progress_callback(2, 6, "Running Pass 3: Hierarchical cross-document synthesis")

        # Use hierarchical synthesis for large document sets
        pass3_results = self._run_hierarchical_pass3(
            dd_id=dd_id,
            documents=documents,
            pass1_results=pass1_results,
            pass2_findings=all_findings,
            blueprint=blueprint,
            doc_count=doc_count,
            checkpoint_callback=checkpoint_callback,
        )
        result.pass3_results = pass3_results

        # ===== PASS 4: Deal Synthesis =====
        if checkpoint_callback:
            checkpoint_callback('pass4_synthesis', {'mode': 'parallel'})

        if progress_callback:
            progress_callback(3, 6, "Running Pass 4: Deal Synthesis")

        from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis
        from dd_enhanced.core.pass5_verify import run_pass5_verification

        pass4_results = run_pass4_synthesis(
            documents,
            pass1_results,
            all_findings,
            pass3_results,
            self.claude_client,
            verbose=False,
            validated_context=validated_context
        )
        result.pass4_results = pass4_results

        # ===== PASS 5: Verification =====
        if checkpoint_callback:
            checkpoint_callback('pass5_verification', {'mode': 'parallel'})

        if progress_callback:
            progress_callback(4, 6, "Running Pass 5: Verification")

        pass5_result = run_pass5_verification(
            pass4_results=pass4_results,
            pass3_results=pass3_results,
            pass2_findings=all_findings,
            pass1_results=pass1_results,
            calculation_aggregates=pass3_results.get('calculation_aggregates'),
            transaction_context=transaction_context,
            client=self.claude_client,
            verbose=False,
            checkpoint_callback=checkpoint_callback,
        )
        result.pass5_results = pass5_result.to_dict() if hasattr(pass5_result, 'to_dict') else pass5_result

        # ===== Hierarchical Synthesis (for parallel mode) =====
        if checkpoint_callback:
            checkpoint_callback('hierarchical_synthesis', {'doc_count': doc_count})

        if progress_callback:
            progress_callback(5, 6, "Running hierarchical synthesis")

        synthesis_results = self._run_hierarchical_synthesis(
            dd_id=dd_id,
            run_id=run_id,
            documents=documents,
            pass2_findings=all_findings,
            pass3_results=pass3_results,
            pass4_results=pass4_results,
            blueprint=blueprint,
            checkpoint_callback=checkpoint_callback,
        )
        result.synthesis_results = synthesis_results

        # Update cost tracking
        if self.claude_client:
            cost_summary = self.claude_client.get_cost_summary()
            result.total_input_tokens = cost_summary.get('total_input_tokens', 0)
            result.total_output_tokens = cost_summary.get('total_output_tokens', 0)
            result.estimated_cost_usd = cost_summary.get('total_cost_usd', 0.0)

        # Save processing state for incremental reuse
        if self.config.enable_incremental and self.db_session:
            self._save_processing_state(run_id, documents, pass1_results, all_findings)

        result.success = len(failed_docs) < len(documents) * 0.5  # Success if <50% failed

        if progress_callback:
            progress_callback(6, 6, "Parallel processing complete")

        return result

    def _build_knowledge_graph(
        self,
        dd_id: str,
        documents: List[Dict],
        pass1_results: Dict,
        checkpoint_callback: Optional[Callable] = None,
    ) -> Optional[Any]:
        """Build knowledge graph from Pass 1 results."""
        try:
            from dd_enhanced.core.graph import (
                EntityTransformer,
                KnowledgeGraphBuilder,
                RelationshipEnricher,
            )
            from shared.session import engine

            # Transform Pass 1 results to graph entities
            transformer = EntityTransformer()
            all_entities = []

            for doc in documents:
                doc_id = doc.get('id', '')
                doc_name = doc.get('filename', '')
                doc_extraction = self._find_doc_extraction(pass1_results, doc_name)
                if doc_extraction:
                    entities = transformer.transform_document(
                        document_id=doc_id,
                        document_name=doc_name,
                        pass1_extraction=doc_extraction
                    )
                    all_entities.append(entities)

            if not all_entities:
                return None

            # Run relationship enrichment for larger sets
            if len(documents) > 5 and self.claude_client:
                if checkpoint_callback:
                    checkpoint_callback('graph_enrichment', {})

                enricher = RelationshipEnricher(self.claude_client)
                enrichments = enricher.enrich_all_documents(
                    documents,
                    max_workers=min(5, self.config.max_workers)
                )

                from dd_enhanced.core.graph.relationship_enricher import merge_enrichments
                for entities, enrichment in zip(all_entities, enrichments):
                    if not enrichment.error:
                        merge_enrichments(entities, enrichment)

            # Build graph in database
            raw_conn = engine.raw_connection()
            try:
                builder = KnowledgeGraphBuilder(raw_conn)
                graph_stats = builder.build_graph(
                    dd_id=dd_id,
                    document_entities=all_entities,
                )
                raw_conn.commit()
                return graph_stats
            finally:
                raw_conn.close()

        except Exception as e:
            logger.warning(f"Knowledge graph building failed (non-fatal): {e}")
            return None

    def _run_hierarchical_pass3(
        self,
        dd_id: str,
        documents: List[Dict],
        pass1_results: Dict,
        pass2_findings: List[Dict],
        blueprint: Dict,
        doc_count: int,
        checkpoint_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run Pass 3 with hierarchical batching for large document sets."""
        from dd_enhanced.core.pass3_clustered import run_pass3_hybrid

        # Use batched mode for large document sets
        force_batching = doc_count >= self.config.parallel_threshold

        return run_pass3_hybrid(
            documents=documents,
            pass1_extractions=pass1_results,
            pass2_findings=pass2_findings,
            blueprint=blueprint,
            client=self.claude_client,
            checkpoint_callback=checkpoint_callback,
            verbose=False,
            force_batching=force_batching,
        )

    def _run_hierarchical_synthesis(
        self,
        dd_id: str,
        run_id: str,
        documents: List[Dict],
        pass2_findings: List[Dict],
        pass3_results: Dict,
        pass4_results: Dict,
        blueprint: Dict,
        checkpoint_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run hierarchical synthesis for large document sets."""
        try:
            from dd_enhanced.core.synthesis import create_synthesis_pipeline
            from dd_enhanced.core.graph import GraphQueryEngine
            from shared.session import engine

            doc_count = len(documents)

            # Determine model based on document count
            use_opus = doc_count >= self.config.opus_threshold
            model = "opus" if use_opus else "sonnet"

            # Create graph query engine for insights
            raw_conn = engine.raw_connection()
            try:
                graph_engine = GraphQueryEngine(raw_conn)
                graph_insights = graph_engine.get_graph_insights_for_synthesis(dd_id)
            finally:
                raw_conn.close()

            # Create synthesis pipeline
            pipeline = create_synthesis_pipeline(
                claude_client=self.claude_client,
                model=model,
                batch_size=self.config.batch_size,
            )

            # Prepare findings for synthesis
            # Group findings by document for batch synthesis
            findings_by_doc = {}
            for finding in pass2_findings:
                doc_name = finding.get('source_document', 'unknown')
                if doc_name not in findings_by_doc:
                    findings_by_doc[doc_name] = []
                findings_by_doc[doc_name].append(finding)

            # Run synthesis pipeline
            synthesis_results = pipeline.run_full_synthesis(
                dd_id=dd_id,
                findings_by_document=findings_by_doc,
                cross_doc_findings=pass3_results.get('cross_doc_findings', []),
                deal_synthesis=pass4_results,
                graph_insights=graph_insights,
                transaction_type=blueprint.get('transaction_type', 'general'),
            )

            return synthesis_results

        except Exception as e:
            logger.warning(f"Hierarchical synthesis failed (non-fatal): {e}")
            return {}

    def _save_processing_state(
        self,
        run_id: str,
        documents: List[Dict],
        pass1_results: Dict,
        pass2_findings: List[Dict],
    ):
        """Save processing state for incremental reuse."""
        try:
            from dd_enhanced.core.incremental import ChangeDetector

            detector = ChangeDetector(self.db_session)
            detector.save_state(run_id, documents)

            # Save per-document results
            for doc in documents:
                doc_id = doc.get('id')
                doc_name = doc.get('filename', '')

                # Find Pass 1 extraction for this document
                doc_pass1 = self._find_doc_extraction(pass1_results, doc_name)

                # Find Pass 2 findings for this document
                doc_pass2 = [
                    f for f in pass2_findings
                    if f.get('source_document') == doc_name
                ]

                if doc_pass1 or doc_pass2:
                    detector.update_processing_state(
                        run_id=run_id,
                        document_id=doc_id,
                        pass1_result=doc_pass1,
                        pass2_findings=doc_pass2,
                    )

        except Exception as e:
            logger.warning(f"Failed to save processing state: {e}")

    def _find_doc_extraction(self, pass1_results: Dict, doc_name: str) -> Optional[Dict]:
        """Find Pass 1 extraction data for a specific document."""
        doc_extraction = {
            'key_dates': [],
            'financial_figures': [],
            'coc_clauses': [],
            'consent_requirements': [],
            'parties': [],
            'covenants': []
        }

        if not pass1_results:
            return None

        for key in doc_extraction.keys():
            for item in pass1_results.get(key, []):
                if item.get('source_document') == doc_name:
                    doc_extraction[key].append(item)

        has_data = any(len(v) > 0 for v in doc_extraction.values())
        return doc_extraction if has_data else None

    def cancel(self):
        """Cancel ongoing processing."""
        with self._lock:
            self._cancelled = True
        logger.info("Processing cancellation requested")


def create_orchestrator(
    claude_client: Optional[Any] = None,
    db_session: Optional[Any] = None,
    config: Optional[OrchestratorConfig] = None,
) -> ParallelOrchestrator:
    """
    Create a parallel orchestrator with default configuration.

    Args:
        claude_client: Optional ClaudeClient instance
        db_session: Optional database session for incremental processing
        config: Optional custom configuration

    Returns:
        Configured ParallelOrchestrator instance
    """
    config = config or OrchestratorConfig.from_env()
    return ParallelOrchestrator(
        config=config,
        claude_client=claude_client,
        db_session=db_session,
    )
