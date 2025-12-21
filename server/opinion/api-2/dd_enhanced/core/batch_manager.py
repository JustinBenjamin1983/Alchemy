"""
Batch Manager for Phase 4: Summary Compression + Batching

Groups compressed documents into context-safe batches for Pass 3 analysis.
Uses MIXED strategy: balance folder coherence with size optimization.

Key features:
- ~100K tokens per batch (Claude 200K context - system/output buffer)
- Folder-aware grouping to maintain analysis coherence
- Cross-batch analysis for critical/high findings
- Priority-aware batching (critical docs processed first)

Usage:
    batch_plan = create_batch_plan(
        compressed_docs=compressed_docs,
        target_batch_tokens=100000,
        strategy=BatchStrategy.MIXED
    )
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import logging

from .compression_engine import CompressedDocument
from .document_priority import DocumentPriority

logger = logging.getLogger(__name__)

# Batching configuration
DEFAULT_TARGET_TOKENS = 100000  # ~100K tokens per batch
MAX_BATCH_TOKENS = 150000      # Hard limit per batch
MIN_BATCH_DOCS = 3             # Minimum docs per batch (avoid tiny batches)
CROSS_BATCH_FINDING_CAP = 50   # Max findings for cross-batch context


class BatchStrategy(Enum):
    """Strategy for grouping documents into batches."""
    BY_FOLDER = "by_folder"     # Group by folder category first
    BY_SIZE = "by_size"         # Pack by token count (bin-packing)
    MIXED = "mixed"             # Folder grouping with size optimization


@dataclass
class DocumentBatch:
    """A batch of documents ready for Pass 3 analysis."""
    batch_id: int
    documents: List[CompressedDocument] = field(default_factory=list)
    total_tokens: int = 0

    # Folder composition
    folders: Set[str] = field(default_factory=set)
    primary_folder: str = ""

    # Priority composition
    critical_count: int = 0
    high_count: int = 0

    # Cross-batch context (populated during execution)
    prior_batch_findings: List[Dict[str, Any]] = field(default_factory=list)

    def add_document(self, doc: CompressedDocument) -> None:
        """Add a document to this batch."""
        self.documents.append(doc)
        self.total_tokens += doc.summary_tokens
        self.folders.add(doc.folder_category)

        if doc.priority == DocumentPriority.CRITICAL:
            self.critical_count += 1
        elif doc.priority == DocumentPriority.HIGH:
            self.high_count += 1

    def can_fit(self, doc: CompressedDocument, max_tokens: int) -> bool:
        """Check if document can fit in this batch."""
        return (self.total_tokens + doc.summary_tokens) <= max_tokens

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging/storage."""
        return {
            'batch_id': self.batch_id,
            'document_count': len(self.documents),
            'total_tokens': self.total_tokens,
            'folders': list(self.folders),
            'primary_folder': self.primary_folder,
            'critical_count': self.critical_count,
            'high_count': self.high_count,
            'document_ids': [d.document_id for d in self.documents],
        }


@dataclass
class BatchPlan:
    """A complete plan for batched Pass 3 execution."""
    batches: List[DocumentBatch] = field(default_factory=list)
    total_documents: int = 0
    total_tokens: int = 0
    strategy: BatchStrategy = BatchStrategy.MIXED

    # Execution tracking
    completed_batches: int = 0
    current_batch: int = 0

    # Cross-batch findings (accumulated during execution)
    accumulated_findings: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def batch_count(self) -> int:
        return len(self.batches)

    @property
    def avg_batch_size(self) -> float:
        if not self.batches:
            return 0.0
        return self.total_documents / len(self.batches)

    @property
    def avg_batch_tokens(self) -> float:
        if not self.batches:
            return 0.0
        return self.total_tokens / len(self.batches)

    def get_cross_batch_context(self, batch_index: int) -> List[Dict[str, Any]]:
        """
        Get relevant findings from prior batches for cross-batch analysis.

        Only includes CRITICAL and HIGH severity findings up to the cap.
        """
        if batch_index == 0:
            return []

        relevant_findings = [
            f for f in self.accumulated_findings
            if f.get('severity', '').lower() in ['critical', 'high']
        ]

        # Cap findings to prevent context overflow
        return relevant_findings[:CROSS_BATCH_FINDING_CAP]

    def add_batch_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Add findings from a completed batch to accumulated findings."""
        self.accumulated_findings.extend(findings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging/storage."""
        return {
            'batch_count': len(self.batches),
            'total_documents': self.total_documents,
            'total_tokens': self.total_tokens,
            'strategy': self.strategy.value,
            'avg_batch_size': self.avg_batch_size,
            'avg_batch_tokens': self.avg_batch_tokens,
            'batches': [b.to_dict() for b in self.batches],
        }


def create_batch_plan(
    compressed_docs: List[CompressedDocument],
    target_batch_tokens: int = DEFAULT_TARGET_TOKENS,
    max_batch_tokens: int = MAX_BATCH_TOKENS,
    strategy: BatchStrategy = BatchStrategy.MIXED
) -> BatchPlan:
    """
    Create a batch plan from compressed documents.

    Args:
        compressed_docs: List of CompressedDocument from compression engine
        target_batch_tokens: Target tokens per batch (soft limit)
        max_batch_tokens: Maximum tokens per batch (hard limit)
        strategy: Batching strategy to use

    Returns:
        BatchPlan with documents grouped into batches
    """
    if not compressed_docs:
        return BatchPlan(strategy=strategy)

    if strategy == BatchStrategy.BY_FOLDER:
        batches = _create_batches_by_folder(
            compressed_docs, target_batch_tokens, max_batch_tokens
        )
    elif strategy == BatchStrategy.BY_SIZE:
        batches = _create_batches_by_size(
            compressed_docs, target_batch_tokens, max_batch_tokens
        )
    else:  # MIXED
        batches = _create_batches_mixed(
            compressed_docs, target_batch_tokens, max_batch_tokens
        )

    # Calculate totals
    total_docs = sum(b.document_count for b in batches)
    total_tokens = sum(b.total_tokens for b in batches)

    plan = BatchPlan(
        batches=batches,
        total_documents=total_docs,
        total_tokens=total_tokens,
        strategy=strategy,
    )

    logger.info(f"Created batch plan:")
    logger.info(f"  Strategy: {strategy.value}")
    logger.info(f"  Total batches: {len(batches)}")
    logger.info(f"  Total documents: {total_docs}")
    logger.info(f"  Total tokens: {total_tokens:,}")
    logger.info(f"  Avg batch size: {plan.avg_batch_size:.1f} docs")
    logger.info(f"  Avg batch tokens: {plan.avg_batch_tokens:,.0f}")

    return plan


def _create_batches_by_folder(
    docs: List[CompressedDocument],
    target_tokens: int,
    max_tokens: int
) -> List[DocumentBatch]:
    """
    Create batches grouped primarily by folder category.

    Documents from the same folder stay together when possible.
    """
    # Group by folder
    by_folder: Dict[str, List[CompressedDocument]] = {}
    for doc in docs:
        folder = doc.folder_category
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(doc)

    batches = []
    current_batch = DocumentBatch(batch_id=len(batches))

    for folder, folder_docs in by_folder.items():
        # Sort folder docs by priority within folder
        folder_docs.sort(key=lambda d: (d.priority.value, -d.summary_tokens))

        for doc in folder_docs:
            if not current_batch.can_fit(doc, target_tokens):
                # Start new batch
                if current_batch.documents:
                    _finalize_batch(current_batch)
                    batches.append(current_batch)
                current_batch = DocumentBatch(batch_id=len(batches))

            current_batch.add_document(doc)

    # Add final batch
    if current_batch.documents:
        _finalize_batch(current_batch)
        batches.append(current_batch)

    return batches


def _create_batches_by_size(
    docs: List[CompressedDocument],
    target_tokens: int,
    max_tokens: int
) -> List[DocumentBatch]:
    """
    Create batches using first-fit decreasing bin packing.

    Optimizes for token utilization but ignores folder coherence.
    """
    # Sort by token count descending (FFD algorithm)
    sorted_docs = sorted(docs, key=lambda d: -d.summary_tokens)

    batches: List[DocumentBatch] = []

    for doc in sorted_docs:
        # Find first batch that can fit this document
        placed = False
        for batch in batches:
            if batch.can_fit(doc, target_tokens):
                batch.add_document(doc)
                placed = True
                break

        if not placed:
            # Create new batch
            new_batch = DocumentBatch(batch_id=len(batches))
            new_batch.add_document(doc)
            batches.append(new_batch)

    # Finalize all batches
    for batch in batches:
        _finalize_batch(batch)

    return batches


def _create_batches_mixed(
    docs: List[CompressedDocument],
    target_tokens: int,
    max_tokens: int
) -> List[DocumentBatch]:
    """
    Create batches with MIXED strategy: folder coherence + size optimization.

    Algorithm:
    1. Sort documents by priority (critical first) then by folder
    2. Process critical/high priority docs first
    3. Fill batches by folder when possible
    4. Use bin-packing to fill remaining space
    """
    # Separate by priority tier
    critical_high = [d for d in docs if d.priority.value <= 2]  # CRITICAL, HIGH
    medium_low = [d for d in docs if d.priority.value > 2]  # MEDIUM, LOW, ROUTINE

    # Sort critical/high by folder then tokens
    critical_high.sort(key=lambda d: (d.folder_category, -d.summary_tokens))

    # Sort medium/low by tokens descending (for bin-packing)
    medium_low.sort(key=lambda d: -d.summary_tokens)

    batches: List[DocumentBatch] = []
    current_batch = DocumentBatch(batch_id=0)

    # First pass: place critical/high docs with folder coherence
    current_folder = None
    for doc in critical_high:
        # Try to keep same folder together
        if (current_folder and
            doc.folder_category == current_folder and
            current_batch.can_fit(doc, target_tokens)):
            current_batch.add_document(doc)
        elif current_batch.can_fit(doc, target_tokens):
            current_batch.add_document(doc)
            current_folder = doc.folder_category
        else:
            # Start new batch
            if current_batch.documents:
                _finalize_batch(current_batch)
                batches.append(current_batch)
            current_batch = DocumentBatch(batch_id=len(batches))
            current_batch.add_document(doc)
            current_folder = doc.folder_category

    # Save the batch with critical/high docs
    if current_batch.documents:
        _finalize_batch(current_batch)
        batches.append(current_batch)

    # Second pass: fill remaining docs using bin-packing
    for doc in medium_low:
        # Find best batch that can fit this document
        # Prefer batches with same folder
        best_batch = None
        best_score = -1

        for batch in batches:
            if batch.can_fit(doc, max_tokens):  # Use max_tokens for filling
                # Score based on folder match and remaining space
                folder_bonus = 10 if doc.folder_category in batch.folders else 0
                space_score = (target_tokens - batch.total_tokens) / target_tokens
                score = folder_bonus + space_score

                if score > best_score:
                    best_score = score
                    best_batch = batch

        if best_batch:
            best_batch.add_document(doc)
        else:
            # Create new batch
            new_batch = DocumentBatch(batch_id=len(batches))
            new_batch.add_document(doc)
            _finalize_batch(new_batch)
            batches.append(new_batch)

    # Re-number batch IDs
    for i, batch in enumerate(batches):
        batch.batch_id = i

    return batches


def _finalize_batch(batch: DocumentBatch) -> None:
    """Set the primary folder for a batch based on document composition."""
    if not batch.folders:
        return

    # Primary folder is the one with most documents
    folder_counts: Dict[str, int] = {}
    for doc in batch.documents:
        folder_counts[doc.folder_category] = folder_counts.get(doc.folder_category, 0) + 1

    batch.primary_folder = max(folder_counts.keys(), key=lambda f: folder_counts[f])


def get_batch_stats(batch_plan: BatchPlan) -> Dict[str, Any]:
    """
    Get detailed statistics about a batch plan.

    Returns:
        Dict with batch metrics for monitoring/logging
    """
    if not batch_plan.batches:
        return {'total_batches': 0}

    token_counts = [b.total_tokens for b in batch_plan.batches]
    doc_counts = [b.document_count for b in batch_plan.batches]

    # Priority distribution across batches
    priority_dist = {
        'critical': sum(b.critical_count for b in batch_plan.batches),
        'high': sum(b.high_count for b in batch_plan.batches),
        'other': sum(
            b.document_count - b.critical_count - b.high_count
            for b in batch_plan.batches
        ),
    }

    # Folder distribution
    all_folders: Set[str] = set()
    for batch in batch_plan.batches:
        all_folders.update(batch.folders)

    return {
        'total_batches': batch_plan.batch_count,
        'total_documents': batch_plan.total_documents,
        'total_tokens': batch_plan.total_tokens,
        'strategy': batch_plan.strategy.value,
        'tokens': {
            'min': min(token_counts),
            'max': max(token_counts),
            'avg': sum(token_counts) / len(token_counts),
        },
        'docs_per_batch': {
            'min': min(doc_counts),
            'max': max(doc_counts),
            'avg': sum(doc_counts) / len(doc_counts),
        },
        'priority_distribution': priority_dist,
        'unique_folders': len(all_folders),
        'folders': list(all_folders),
    }


def estimate_batch_count(
    total_tokens: int,
    target_batch_tokens: int = DEFAULT_TARGET_TOKENS
) -> int:
    """
    Estimate number of batches needed for a given token count.

    Useful for progress tracking and time estimation.
    """
    if total_tokens <= 0:
        return 0
    return max(1, (total_tokens + target_batch_tokens - 1) // target_batch_tokens)


def should_use_batching(doc_count: int, threshold: int = 75) -> bool:
    """
    Determine if batching should be used based on document count.

    Implements hybrid auto-switch:
    - < threshold docs: use original Pass 3 (no batching)
    - >= threshold docs: use compression + batching
    """
    return doc_count >= threshold
