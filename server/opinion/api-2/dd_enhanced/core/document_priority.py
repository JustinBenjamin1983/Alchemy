"""
Document Priority System for Phase 4: Summary Compression + Batching

Assigns priority scores to documents for compression decisions.
Higher priority documents get more detailed summaries and are processed first.

Priority Factors:
1. Folder relevance from blueprint (critical/high/medium/low)
2. Document type importance (Mining Right > general contract)
3. Pass 2 findings (docs with critical findings get higher priority)
4. Transaction trigger keywords (change of control, consent, etc.)
5. Document size (larger docs may have more content)

Usage:
    prioritized = prioritize_all_documents(documents, pass2_findings, transaction_type)
    # Returns list sorted by priority (CRITICAL first)
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class DocumentPriority(Enum):
    """Priority tiers for document compression."""
    CRITICAL = 1    # Full content in summaries, first in batches
    HIGH = 2        # Detailed summaries
    MEDIUM = 3      # Standard summaries
    LOW = 4         # Minimal summaries
    ROUTINE = 5     # Ultra-compressed, may skip in tight batches


# Token targets by priority tier
TOKEN_TARGETS: Dict[DocumentPriority, int] = {
    DocumentPriority.CRITICAL: 800,   # Detailed summary
    DocumentPriority.HIGH: 500,       # Good summary
    DocumentPriority.MEDIUM: 300,     # Standard summary
    DocumentPriority.LOW: 150,        # Brief summary
    DocumentPriority.ROUTINE: 75      # Minimal summary
}


# Critical document types that should always get high priority
CRITICAL_DOC_TYPES = [
    'Mining Right', 'Mining Permit', 'Prospecting Right',
    'Environmental Authorisation', 'Environmental Authorization',
    'Water Use License', 'Water Use Licence',
    'Shareholders Agreement', 'SHA',
    'Loan Agreement', 'Facility Agreement', 'Credit Agreement',
    'Share Purchase Agreement', 'SPA',
    'Memorandum of Incorporation', 'MOI',
    'Constitution', 'Articles of Association',
]

# High priority document types
HIGH_DOC_TYPES = [
    'Board Resolution', 'Directors Resolution',
    'Guarantee', 'Suretyship',
    'Lease Agreement', 'Surface Lease', 'Mining Lease',
    'Employment Contract', 'Executive Employment',
    'Supply Agreement', 'Offtake Agreement',
    'Title Deed', 'Deed of Transfer',
    'Social and Labour Plan', 'SLP',
    'BEE Certificate', 'B-BBEE Certificate',
    'Environmental Management Programme', 'EMPr',
]

# Keywords that indicate transaction-critical content
TRIGGER_KEYWORDS = [
    'change of control',
    'consent required',
    'consent of',
    'prior written consent',
    'termination',
    'event of default',
    'default',
    'material adverse',
    'acceleration',
    'assignment',
    'transfer restriction',
    'pre-emptive right',
    'tag along',
    'drag along',
    'put option',
    'call option',
]

# Folder relevance scores (matches blueprint folder_structure)
FOLDER_RELEVANCE_SCORES: Dict[str, int] = {
    'critical': 30,
    'high': 20,
    'medium': 10,
    'low': 0,
    'n/a': -10,
}


@dataclass
class PrioritizedDocument:
    """A document with its priority score and compression target."""
    document_id: str
    document_name: str
    folder_category: str
    document_type: str
    priority: DocumentPriority
    priority_score: float  # 0-100, for fine-grained sorting
    priority_reasons: List[str] = field(default_factory=list)
    estimated_tokens: int = 1000
    compressed_token_target: int = 300

    # Additional context for compression
    has_critical_findings: bool = False
    finding_count: int = 0
    triggers_found: List[str] = field(default_factory=list)


def calculate_document_priority(
    document: Dict[str, Any],
    folder_category: str,
    folder_relevance: str,
    transaction_type: str,
    pass2_findings: List[Dict[str, Any]]
) -> PrioritizedDocument:
    """
    Calculate priority for a document based on multiple factors.

    Args:
        document: Document dict with id, original_file_name, ai_document_type, etc.
        folder_category: e.g., "01_Corporate", "02_Commercial"
        folder_relevance: e.g., "critical", "high", "medium", "low"
        transaction_type: e.g., "mining_acquisition", "share_sale"
        pass2_findings: List of findings from Pass 2 analysis

    Returns:
        PrioritizedDocument with priority tier and score
    """
    priority_score = 50.0  # Start at medium
    reasons = []

    doc_id = str(document.get('id', ''))
    doc_name = document.get('original_file_name', document.get('filename', 'Unknown'))
    doc_type = document.get('ai_document_type', document.get('doc_type', ''))

    # Factor 1: Folder relevance from blueprint
    relevance_score = FOLDER_RELEVANCE_SCORES.get(folder_relevance.lower(), 0)
    priority_score += relevance_score
    if folder_relevance.lower() == 'critical':
        reasons.append(f"Critical folder: {folder_category}")
    elif folder_relevance.lower() == 'high':
        reasons.append(f"High-priority folder: {folder_category}")

    # Factor 2: Document type importance
    doc_type_upper = doc_type.upper() if doc_type else ''
    doc_name_upper = doc_name.upper() if doc_name else ''

    is_critical_type = any(
        ctype.upper() in doc_type_upper or ctype.upper() in doc_name_upper
        for ctype in CRITICAL_DOC_TYPES
    )
    is_high_type = any(
        htype.upper() in doc_type_upper or htype.upper() in doc_name_upper
        for htype in HIGH_DOC_TYPES
    )

    if is_critical_type:
        priority_score += 25
        reasons.append(f"Critical document type: {doc_type}")
    elif is_high_type:
        priority_score += 15
        reasons.append(f"High-priority document type: {doc_type}")

    # Factor 3: Has critical/high findings from Pass 2
    doc_findings = [
        f for f in pass2_findings
        if str(f.get('document_id', '')) == doc_id or
           f.get('source_document', '') == doc_name
    ]
    critical_findings = [
        f for f in doc_findings
        if f.get('severity', '').lower() in ['critical', 'high']
    ]

    has_critical = len(critical_findings) > 0
    if has_critical:
        priority_score += 20
        reasons.append(f"{len(critical_findings)} critical/high findings")
    elif len(doc_findings) > 3:
        priority_score += 10
        reasons.append(f"{len(doc_findings)} findings identified")

    # Factor 4: Contains key transaction triggers
    doc_text = document.get('extracted_text', document.get('text', '')).lower()
    triggers_found = [kw for kw in TRIGGER_KEYWORDS if kw in doc_text]

    if triggers_found:
        trigger_bonus = min(len(triggers_found) * 5, 20)  # Cap at 20
        priority_score += trigger_bonus
        reasons.append(f"Contains triggers: {', '.join(triggers_found[:3])}")

    # Factor 5: Document size (larger docs may have more content)
    estimated_tokens = document.get('token_count', 0)
    if not estimated_tokens:
        # Estimate from text length (rough: 4 chars per token)
        text_len = len(doc_text)
        estimated_tokens = text_len // 4 if text_len else 1000

    if estimated_tokens > 5000:
        priority_score += 5  # Larger docs often more important
        reasons.append("Large document (5000+ tokens)")

    # Factor 6: Transaction-type specific boosts
    if transaction_type and 'mining' in transaction_type.lower():
        mining_keywords = ['mining right', 'dmre', 'mineral', 'section 11', 'mprda']
        if any(kw in doc_text for kw in mining_keywords):
            priority_score += 10
            reasons.append("Mining-specific content")

    # Determine priority tier
    priority_score = min(100, max(0, priority_score))  # Clamp to 0-100

    if priority_score >= 80:
        priority = DocumentPriority.CRITICAL
    elif priority_score >= 65:
        priority = DocumentPriority.HIGH
    elif priority_score >= 45:
        priority = DocumentPriority.MEDIUM
    elif priority_score >= 30:
        priority = DocumentPriority.LOW
    else:
        priority = DocumentPriority.ROUTINE

    return PrioritizedDocument(
        document_id=doc_id,
        document_name=doc_name,
        folder_category=folder_category,
        document_type=doc_type,
        priority=priority,
        priority_score=priority_score,
        priority_reasons=reasons,
        estimated_tokens=estimated_tokens,
        compressed_token_target=TOKEN_TARGETS[priority],
        has_critical_findings=has_critical,
        finding_count=len(doc_findings),
        triggers_found=triggers_found[:5],  # Limit stored triggers
    )


def prioritize_all_documents(
    documents: List[Dict[str, Any]],
    pass2_findings: List[Dict[str, Any]],
    transaction_type: str,
    folder_relevance_map: Optional[Dict[str, str]] = None
) -> List[PrioritizedDocument]:
    """
    Prioritize all documents and return sorted by priority.

    Args:
        documents: List of document dicts
        pass2_findings: List of findings from Pass 2
        transaction_type: Transaction type from blueprint
        folder_relevance_map: Optional map of folder_category -> relevance level

    Returns:
        List of PrioritizedDocument, sorted by priority (CRITICAL first)
    """
    # Default folder relevance if not provided
    if folder_relevance_map is None:
        folder_relevance_map = {
            '01_Corporate': 'high',
            '02_Commercial': 'critical',
            '03_Financial': 'critical',
            '04_Regulatory': 'critical',
            '05_Employment': 'high',
            '06_Property': 'critical',
            '07_Insurance': 'medium',
            '08_Litigation': 'high',
            '09_Tax': 'medium',
            '99_Needs_Review': 'n/a',
        }

    prioritized = []

    for doc in documents:
        folder_category = doc.get('folder_category', '99_Needs_Review')
        folder_relevance = folder_relevance_map.get(folder_category, 'medium')

        try:
            prioritized_doc = calculate_document_priority(
                document=doc,
                folder_category=folder_category,
                folder_relevance=folder_relevance,
                transaction_type=transaction_type,
                pass2_findings=pass2_findings
            )
            prioritized.append(prioritized_doc)
        except Exception as e:
            logger.warning(f"Failed to prioritize document {doc.get('id')}: {e}")
            # Create default priority for failed docs
            prioritized.append(PrioritizedDocument(
                document_id=str(doc.get('id', '')),
                document_name=doc.get('original_file_name', 'Unknown'),
                folder_category=folder_category,
                document_type=doc.get('ai_document_type', ''),
                priority=DocumentPriority.MEDIUM,
                priority_score=50.0,
                priority_reasons=['Default priority (calculation failed)'],
                estimated_tokens=1000,
                compressed_token_target=TOKEN_TARGETS[DocumentPriority.MEDIUM],
            ))

    # Sort by priority (CRITICAL first) then by score within tier
    prioritized.sort(key=lambda x: (x.priority.value, -x.priority_score))

    logger.info(f"Prioritized {len(prioritized)} documents:")
    priority_counts = {}
    for p in prioritized:
        priority_counts[p.priority.name] = priority_counts.get(p.priority.name, 0) + 1
    for name, count in priority_counts.items():
        logger.info(f"  {name}: {count} documents")

    return prioritized


def get_priority_stats(prioritized_docs: List[PrioritizedDocument]) -> Dict[str, Any]:
    """
    Get statistics about prioritized documents.

    Returns:
        Dict with counts, token estimates, and compression targets
    """
    stats = {
        'total_documents': len(prioritized_docs),
        'by_priority': {},
        'total_estimated_tokens': 0,
        'total_target_tokens': 0,
        'compression_ratio': 0.0,
    }

    for doc in prioritized_docs:
        tier = doc.priority.name
        if tier not in stats['by_priority']:
            stats['by_priority'][tier] = {
                'count': 0,
                'estimated_tokens': 0,
                'target_tokens': 0,
            }

        stats['by_priority'][tier]['count'] += 1
        stats['by_priority'][tier]['estimated_tokens'] += doc.estimated_tokens
        stats['by_priority'][tier]['target_tokens'] += doc.compressed_token_target

        stats['total_estimated_tokens'] += doc.estimated_tokens
        stats['total_target_tokens'] += doc.compressed_token_target

    if stats['total_estimated_tokens'] > 0:
        stats['compression_ratio'] = (
            1 - (stats['total_target_tokens'] / stats['total_estimated_tokens'])
        ) * 100

    return stats
