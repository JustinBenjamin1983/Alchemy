"""
Document clustering for Pass 3 optimization.

Instead of analyzing ALL documents together (context explosion),
group documents into logical clusters and analyze each cluster separately.

This reduces context size by ~70% while maintaining analysis quality,
because related documents are still analyzed together.

Cluster Strategy:
1. Corporate Governance: MOI, SHA, Board Resolutions - these must be checked together
2. Financial: AFS, loan agreements, guarantees - financial cross-references
3. Operational/Regulatory: Mining rights, leases, licenses - operational dependencies
4. Commercial: Supply contracts, customer agreements - CoC and consent matrix
5. Employment: Employment contracts - severance and retention

Each cluster has specific cross-document questions that only make sense
when comparing those document types together.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class DocumentCluster:
    """Definition of a document cluster for cross-document analysis."""
    name: str
    description: str
    document_types: List[str]  # From classify_document() output
    cross_doc_questions: List[str]
    max_docs: int = 5  # Cap to prevent context explosion


# Define clusters based on document classification
# These map to the doc_type values from document_loader.classify_document()
DOCUMENT_CLUSTERS = {
    "corporate_governance": DocumentCluster(
        name="Corporate Governance",
        description="Constitutional documents and governance decisions - the foundation that controls everything else",
        document_types=["constitutional", "governance"],
        cross_doc_questions=[
            "Does the Board Resolution authorize what the MOI requires for this transaction?",
            "Are the SHA drag-along/tag-along provisions consistent with MOI transfer restrictions?",
            "Is the shareholder approval threshold in the resolution consistent with MOI requirements?",
            "Are there any conflicts between MOI reserved matters and SHA reserved matters?",
            "Does the signing authority in the resolution match MOI requirements?",
            "Are any shareholder consents or waivers required that haven't been obtained?",
            "Do the MOI pre-emptive rights apply to this transaction?",
            "Has proper notice been given as required by MOI/SHA?",
        ],
        max_docs=5
    ),
    "financial": DocumentCluster(
        name="Financial",
        description="Financial statements and financing agreements - financial position and debt obligations",
        document_types=["financial"],
        cross_doc_questions=[
            "Do the financial covenants in loan agreements match the actual ratios in the AFS?",
            "Are all contingent liabilities in the AFS reflected in the disclosed contracts?",
            "Does the change of control in the loan agreement create a cross-default risk?",
            "Are related party transactions in the AFS consistent with disclosed agreements?",
            "Is the debt disclosed in the AFS consistent with the loan facility outstanding balance?",
            "Are there any off-balance-sheet arrangements not disclosed?",
            "What is the total debt service coverage based on AFS cash flows?",
            "Are any covenant cure periods about to expire?",
        ],
        max_docs=5
    ),
    "operational_regulatory": DocumentCluster(
        name="Operational & Regulatory",
        description="Mining rights, environmental permits, and operational leases - the operational foundation",
        document_types=["regulatory"],
        cross_doc_questions=[
            "Does the surface lease term cover the remaining mining right duration?",
            "Are the mining right boundaries consistent with the lease property description?",
            "Are environmental rehabilitation provisions in the lease consistent with the mining right EMPr?",
            "Does the water use license cover all operations described in the mining right?",
            "Are there any compliance deadlines that create operational risk?",
            "Do the mining right conditions require consents not yet obtained?",
            "Is the rehabilitation guarantee amount sufficient based on EMPr requirements?",
            "Are there any Section 11 transfer approvals pending?",
        ],
        max_docs=6
    ),
    "commercial_contracts": DocumentCluster(
        name="Commercial Contracts",
        description="Supply agreements, customer contracts, and key commercial relationships",
        document_types=["contract", "other"],
        cross_doc_questions=[
            "What is the total change of control exposure across all commercial contracts?",
            "Are termination provisions consistent across key contracts?",
            "Do any contracts have exclusivity provisions that conflict with each other?",
            "What is the aggregate liquidated damages exposure across all contracts?",
            "Are there any consent requirements that could block the transaction?",
            "Do any contracts have anti-assignment clauses that this transaction would trigger?",
            "What is the longest notice period required across all CoC clauses?",
            "Are there any most-favored-customer clauses that could be triggered?",
        ],
        max_docs=5
    ),
    "employment": DocumentCluster(
        name="Employment",
        description="Employment contracts and management arrangements - people-related obligations",
        document_types=["employment"],
        cross_doc_questions=[
            "What is the total severance liability on change of control?",
            "Are restraint of trade provisions enforceable and reasonable?",
            "Do any employment contracts conflict with Board Resolution authorizations?",
            "Are key person provisions aligned with company's key person insurance?",
            "What notice periods apply for termination of executive contracts?",
            "Are there any golden parachute provisions that could be triggered?",
            "Do employment contracts reference bonus pools or incentive schemes not separately documented?",
            "Are there any retention bonuses that accelerate on CoC?",
        ],
        max_docs=4
    ),
}


def classify_document_to_cluster(
    doc_type: str,
    filename: str,
    text_preview: str = ""
) -> str:
    """
    Map a document to a cluster based on its type and content.

    Args:
        doc_type: Output from classify_document() - constitutional, governance, etc.
        filename: Original filename for additional hints
        text_preview: First 2000 chars for content-based classification (optional)

    Returns:
        Cluster name (key from DOCUMENT_CLUSTERS)
    """
    # Direct mapping from document type to cluster
    type_to_cluster = {
        "constitutional": "corporate_governance",
        "governance": "corporate_governance",
        "financial": "financial",
        "regulatory": "operational_regulatory",
        "employment": "employment",
        "contract": "commercial_contracts",
        "other": "commercial_contracts",  # Default
    }

    # Content-based overrides using filename
    filename_lower = filename.lower() if filename else ""

    # Loan/financing documents -> financial cluster
    if any(term in filename_lower for term in ["loan", "facility", "bank", "guarantee", "bond", "overdraft", "credit"]):
        return "financial"

    # Lease/property documents -> operational cluster
    if any(term in filename_lower for term in ["lease", "property", "land", "surface right", "servitude"]):
        return "operational_regulatory"

    # Environmental documents -> operational cluster
    if any(term in filename_lower for term in ["environmental", "compliance", "water", "license", "permit", "eia", "empr"]):
        return "operational_regulatory"

    # Mining documents -> operational cluster
    if any(term in filename_lower for term in ["mining", "mineral", "prospecting", "dmre", "dmr"]):
        return "operational_regulatory"

    # Supply/customer agreements -> commercial cluster
    if any(term in filename_lower for term in ["supply", "eskom", "customer", "sales", "offtake", "purchase"]):
        return "commercial_contracts"

    # MOI/SHA/Board -> corporate governance
    if any(term in filename_lower for term in ["moi", "shareholder", "board", "resolution", "minutes"]):
        return "corporate_governance"

    # Employment -> employment cluster
    if any(term in filename_lower for term in ["employment", "executive", "ceo", "cfo", "service agreement"]):
        return "employment"

    return type_to_cluster.get(doc_type, "commercial_contracts")


def group_documents_by_cluster(documents: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group documents into clusters for Pass 3 processing.

    Args:
        documents: List of document dicts with 'filename', 'text', 'doc_type'

    Returns:
        Dict mapping cluster_name -> list of documents
    """
    clusters: Dict[str, List[Dict]] = {name: [] for name in DOCUMENT_CLUSTERS.keys()}

    for doc in documents:
        doc_type = doc.get("doc_type", "other")
        filename = doc.get("filename", "")
        text_preview = doc.get("text", "")[:2000] if doc.get("text") else ""

        cluster_name = classify_document_to_cluster(doc_type, filename, text_preview)
        clusters[cluster_name].append(doc)

    # Remove empty clusters
    return {k: v for k, v in clusters.items() if v}


def get_cross_doc_questions_for_cluster(
    cluster_name: str,
    blueprint: Optional[Dict] = None
) -> List[str]:
    """
    Get cross-document questions for a cluster, optionally enhanced by blueprint.

    Args:
        cluster_name: Name of the cluster
        blueprint: Optional transaction-type blueprint with additional validations

    Returns:
        List of cross-document questions to analyze
    """
    cluster = DOCUMENT_CLUSTERS.get(cluster_name)
    if not cluster:
        return []

    questions = list(cluster.cross_doc_questions)

    # Add blueprint-specific cross-doc validations if available
    if blueprint:
        for category in blueprint.get("risk_categories", []):
            for validation in category.get("cross_doc_validations", []):
                check = validation.get("check", "")
                if check and check not in questions:
                    questions.append(check)

    return questions


def get_cluster_processing_order() -> List[str]:
    """
    Return optimal order for processing clusters.

    Corporate governance first (reference docs), then others.
    This order matters because findings from earlier clusters
    can inform analysis of later clusters.
    """
    return [
        "corporate_governance",  # MOI/SHA needed as reference - process first
        "financial",             # Financial context useful for others
        "operational_regulatory",# Mining rights etc.
        "commercial_contracts",  # Bulk of contracts
        "employment",            # Usually fewer, process last
    ]


def get_cluster_info(cluster_name: str) -> Optional[DocumentCluster]:
    """Get cluster definition by name."""
    return DOCUMENT_CLUSTERS.get(cluster_name)


def estimate_cluster_context_size(documents: List[Dict], max_chars_per_doc: int = 15000) -> int:
    """
    Estimate total context size for a cluster.

    Args:
        documents: List of documents in the cluster
        max_chars_per_doc: Maximum chars per document (will be truncated)

    Returns:
        Estimated total characters
    """
    total = 0
    for doc in documents:
        text_len = len(doc.get("text", ""))
        total += min(text_len, max_chars_per_doc)
        total += 500  # Overhead for document headers
    return total


def should_split_cluster(documents: List[Dict], max_context_chars: int = 100000) -> bool:
    """
    Determine if a cluster should be split due to size.

    Args:
        documents: Documents in the cluster
        max_context_chars: Maximum allowed context size

    Returns:
        True if cluster should be split
    """
    estimated_size = estimate_cluster_context_size(documents)
    return estimated_size > max_context_chars


def split_large_cluster(
    documents: List[Dict],
    max_docs_per_batch: int = 3
) -> List[List[Dict]]:
    """
    Split a large cluster into smaller batches.

    Args:
        documents: Documents to split
        max_docs_per_batch: Maximum documents per batch

    Returns:
        List of document batches
    """
    batches = []
    for i in range(0, len(documents), max_docs_per_batch):
        batches.append(documents[i:i + max_docs_per_batch])
    return batches


def get_cluster_summary(clustered_docs: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Get summary of document clustering.

    Args:
        clustered_docs: Result from group_documents_by_cluster()

    Returns:
        Summary dict with counts and estimated sizes
    """
    summary = {
        "total_documents": sum(len(docs) for docs in clustered_docs.values()),
        "total_clusters": len(clustered_docs),
        "clusters": {}
    }

    for cluster_name, docs in clustered_docs.items():
        cluster_info = DOCUMENT_CLUSTERS.get(cluster_name)
        summary["clusters"][cluster_name] = {
            "document_count": len(docs),
            "documents": [d.get("filename", "unknown") for d in docs],
            "estimated_context_chars": estimate_cluster_context_size(docs),
            "cross_doc_questions": len(cluster_info.cross_doc_questions) if cluster_info else 0,
        }

    return summary
