"""
Document Registry & Auto-Classification System

Provides:
1. Expected document lists per transaction type
2. Auto-classification of uploaded documents
3. Folder structure templates
4. Missing document detection
"""
import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

DOCS_DIR = Path(__file__).parent

# Map similar transaction types to their base registry
# This allows multiple frontend transaction types to share the same document registry
TRANSACTION_TYPE_ALIASES = {
    "mining_acquisition": "mining_resources",  # Mining acquisition uses mining_resources registry
}


class DocumentPriority(Enum):
    CRITICAL = "critical"      # Must have - deal cannot proceed without
    REQUIRED = "required"      # Should have - significant gap if missing
    RECOMMENDED = "recommended"  # Nice to have - request if available
    OPTIONAL = "optional"      # Situational - only if applicable


@dataclass
class ExpectedDocument:
    """An expected document in the data room."""
    name: str
    category: str
    folder: str
    priority: DocumentPriority
    description: str
    classification_patterns: List[str] = field(default_factory=list)
    common_filenames: List[str] = field(default_factory=list)
    request_template: str = ""


@dataclass
class DocumentFolder:
    """A folder in the data room structure."""
    name: str
    path: str
    description: str
    document_types: List[str] = field(default_factory=list)
    subfolders: List['DocumentFolder'] = field(default_factory=list)


def load_document_registry(transaction_type: str) -> Dict:
    """
    Load the document registry for a transaction type.
    Merges common documents with transaction-specific ones.
    """
    # Resolve transaction type alias if one exists
    resolved_type = TRANSACTION_TYPE_ALIASES.get(transaction_type, transaction_type)

    # Load common documents
    common_path = DOCS_DIR / "_common_documents.yaml"
    with open(common_path) as f:
        common = yaml.safe_load(f) or {}

    # Load transaction-specific documents
    specific_path = DOCS_DIR / f"{resolved_type}_docs.yaml"
    if not specific_path.exists():
        raise ValueError(f"No document registry for: {transaction_type}")

    with open(specific_path) as f:
        specific = yaml.safe_load(f) or {}

    # Merge: specific overrides common where there's conflict
    merged = {
        "transaction_type": transaction_type,
        "folder_structure": specific.get("folder_structure", []),
        "categories": {},
        "documents": []
    }

    # Merge categories
    for cat in common.get("categories", []):
        merged["categories"][cat["name"]] = cat
    for cat in specific.get("categories", []):
        merged["categories"][cat["name"]] = cat

    # Merge documents (common first, then specific)
    merged["documents"] = common.get("documents", []) + specific.get("documents", [])

    return merged


def classify_document(
    filename: str,
    content_preview: str,
    transaction_type: str
) -> Tuple[str, str, float]:
    """
    Auto-classify a document based on filename and content.

    Returns:
        Tuple of (category, suggested_folder, confidence_score)
    """
    registry = load_document_registry(transaction_type)

    filename_lower = filename.lower()
    content_lower = content_preview.lower()[:5000]  # First 5000 chars

    best_match = None
    best_score = 0.0

    for doc in registry["documents"]:
        score = 0.0

        # Check filename patterns
        for pattern in doc.get("classification_patterns", []):
            try:
                if re.search(pattern, filename_lower):
                    score += 0.4
                if re.search(pattern, content_lower):
                    score += 0.3
            except re.error:
                # Invalid regex pattern, skip
                continue

        # Check common filenames
        for common_name in doc.get("common_filenames", []):
            if common_name.lower() in filename_lower:
                score += 0.5

        # Check content keywords
        for keyword in doc.get("content_keywords", []):
            if keyword.lower() in content_lower:
                score += 0.1

        if score > best_score:
            best_score = score
            best_match = doc

    if best_match and best_score >= 0.3:
        return (
            best_match["category"],
            best_match["folder"],
            min(best_score, 1.0)
        )

    # Default classification
    return ("Uncategorized", "99. Other Documents", 0.1)


def get_missing_documents(
    transaction_type: str,
    uploaded_docs: List[str],
    priority_threshold: DocumentPriority = DocumentPriority.REQUIRED
) -> List[ExpectedDocument]:
    """
    Identify missing documents based on what's been uploaded.

    Args:
        transaction_type: The transaction type
        uploaded_docs: List of uploaded document filenames
        priority_threshold: Minimum priority to report as missing

    Returns:
        List of expected documents that appear to be missing
    """
    registry = load_document_registry(transaction_type)
    uploaded_lower = [d.lower() for d in uploaded_docs]

    missing = []
    priority_order = [
        DocumentPriority.CRITICAL,
        DocumentPriority.REQUIRED,
        DocumentPriority.RECOMMENDED,
        DocumentPriority.OPTIONAL
    ]

    for doc in registry["documents"]:
        doc_priority = DocumentPriority(doc.get("priority", "optional"))

        # Skip if below threshold
        if priority_order.index(doc_priority) > priority_order.index(priority_threshold):
            continue

        # Check if any uploaded doc matches
        is_present = False
        for pattern in doc.get("classification_patterns", []):
            for uploaded in uploaded_lower:
                try:
                    if re.search(pattern, uploaded):
                        is_present = True
                        break
                except re.error:
                    continue
            if is_present:
                break

        if not is_present:
            missing.append(ExpectedDocument(
                name=doc["name"],
                category=doc["category"],
                folder=doc["folder"],
                priority=doc_priority,
                description=doc.get("description", ""),
                request_template=doc.get("request_template", "")
            ))

    return missing


def generate_document_request_list(
    transaction_type: str,
    priority_threshold: DocumentPriority = DocumentPriority.REQUIRED
) -> str:
    """
    Generate a formatted document request list for sending to the target.
    """
    registry = load_document_registry(transaction_type)

    # Group by category
    by_category = {}
    priority_order = [
        DocumentPriority.CRITICAL,
        DocumentPriority.REQUIRED,
        DocumentPriority.RECOMMENDED,
        DocumentPriority.OPTIONAL
    ]

    for doc in registry["documents"]:
        doc_priority = DocumentPriority(doc.get("priority", "optional"))

        if priority_order.index(doc_priority) > priority_order.index(priority_threshold):
            continue

        cat = doc["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(doc)

    # Format output
    lines = [
        f"# Document Request List",
        f"## Transaction Type: {registry['transaction_type']}",
        "",
        "Please provide the following documents:",
        ""
    ]

    for category, docs in sorted(by_category.items()):
        lines.append(f"### {category}")
        lines.append("")
        for doc in docs:
            priority_marker = {
                "critical": "[CRITICAL]",
                "required": "[REQUIRED]",
                "recommended": "[RECOMMENDED]",
                "optional": "[OPTIONAL]"
            }.get(doc.get("priority", "optional"), "[OPTIONAL]")

            lines.append(f"{priority_marker} **{doc['name']}**")
            if doc.get("description"):
                lines.append(f"   _{doc['description']}_")
            if doc.get("request_template"):
                lines.append(f"   Request: {doc['request_template']}")
            lines.append("")

    lines.append("")
    lines.append("---")
    lines.append("Priority Legend: [CRITICAL] Must have | [REQUIRED] Should have | [RECOMMENDED] Nice to have | [OPTIONAL] If applicable")

    return "\n".join(lines)


def get_folder_structure(transaction_type: str) -> List[Dict]:
    """Get the recommended folder structure for a transaction type."""
    registry = load_document_registry(transaction_type)
    return registry.get("folder_structure", [])


def get_document_count_by_priority(transaction_type: str) -> Dict[str, int]:
    """Get count of expected documents by priority."""
    registry = load_document_registry(transaction_type)
    counts = {
        "critical": 0,
        "required": 0,
        "recommended": 0,
        "optional": 0
    }
    for doc in registry["documents"]:
        priority = doc.get("priority", "optional")
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def list_available_registries() -> List[str]:
    """List all available document registries."""
    registries = []
    for file in DOCS_DIR.glob("*_docs.yaml"):
        name = file.stem.replace("_docs", "")
        registries.append(name)
    return registries
