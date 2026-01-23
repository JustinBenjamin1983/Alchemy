"""
Pass 1: Extract & Index

Extracts structured data from all documents:
- Key dates (effective, expiry, deadlines)
- Financial figures
- Parties and their roles
- Change of control clauses
- Consent requirements

This creates a structured index that informs later analysis.
"""
from typing import List, Dict, Any
import os
import sys

# Ensure dd_enhanced is in path for imports
_dd_enhanced_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dd_enhanced_path not in sys.path:
    sys.path.insert(0, _dd_enhanced_path)

from .claude_client import ClaudeClient
from prompts.extraction import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt


def extract_document(
    doc: Dict[str, Any],
    client: ClaudeClient
) -> Dict[str, Any]:
    """
    Extract structured data from a single document.

    Args:
        doc: Document dict with 'filename', 'text', 'doc_type'
        client: Claude API client

    Returns:
        Dict with extracted data: key_dates, financial_figures, coc_clauses,
        consent_requirements, key_parties, summary
    """
    filename = doc.get("filename", "unknown")

    # Build extraction prompt
    prompt = build_extraction_prompt(
        document_text=doc.get("text", "")[:50000],  # Limit to ~50k chars
        document_name=filename,
        doc_type=doc.get("doc_type", "")
    )

    # Call Claude
    response = client.complete(
        prompt=prompt,
        system=EXTRACTION_SYSTEM_PROMPT,
        json_mode=True,
        max_tokens=4096,
        temperature=0.1
    )

    if "error" in response:
        return {
            "key_dates": [],
            "financial_figures": [],
            "coc_clauses": [],
            "consent_requirements": [],
            "key_parties": [],
            "document_references": [],  # Phase 1 Enhancement
            "summary": f"Extraction failed: {response.get('error')}"
        }

    # Normalize field names to match expected format
    return {
        "key_dates": response.get("key_dates", []),
        "financial_figures": response.get("financial_figures", []),
        "coc_clauses": response.get("change_of_control_clauses", []),
        "consent_requirements": response.get("consent_requirements", []),
        "key_parties": response.get("parties", []),
        "document_references": response.get("document_references", []),  # Phase 1 Enhancement
        "summary": response.get("summary", "")
    }


def run_pass1_extraction(
    documents: List[Dict],
    client: ClaudeClient,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run Pass 1: Extract structured data from all documents.

    Args:
        documents: List of document dicts with 'filename', 'text', 'doc_type'
        client: Claude API client
        verbose: Print progress

    Returns:
        Dict with aggregated extractions and per-document results
    """

    results = {
        "document_extractions": {},  # Per-document results
        "key_dates": [],
        "financial_figures": [],
        "coc_clauses": [],
        "consent_requirements": [],
        "parties": [],
        "covenants": [],
        "document_references": [],  # Phase 1 Enhancement: References to other docs
    }

    for i, doc in enumerate(documents, 1):
        filename = doc["filename"]
        if verbose:
            print(f"  [{i}/{len(documents)}] Extracting from {filename}...")

        # Build extraction prompt
        prompt = build_extraction_prompt(
            document_text=doc["text"][:50000],  # Limit to ~50k chars
            document_name=filename,
            doc_type=doc["doc_type"]
        )

        # Call Claude
        response = client.complete(
            prompt=prompt,
            system=EXTRACTION_SYSTEM_PROMPT,
            json_mode=True,
            max_tokens=4096,
            temperature=0.1
        )

        if "error" in response:
            print(f"    Warning: Extraction failed for {filename}: {response.get('error')}")
            continue

        # Store per-document result
        results["document_extractions"][filename] = response

        # Aggregate across documents
        _aggregate_extractions(results, response, filename)

    # Add summary stats
    results["summary"] = {
        "documents_processed": len(results["document_extractions"]),
        "total_dates": len(results["key_dates"]),
        "total_financial_figures": len(results["financial_figures"]),
        "total_coc_clauses": len(results["coc_clauses"]),
        "total_consent_requirements": len(results["consent_requirements"]),
        "total_covenants": len(results["covenants"]),
        "total_document_references": len(results["document_references"]),  # Phase 1 Enhancement
        "critical_document_references": len([
            r for r in results["document_references"]
            if r.get("criticality") == "critical"
        ]),
    }

    return results


def _aggregate_extractions(
    results: Dict[str, Any],
    doc_extraction: Dict[str, Any],
    filename: str
) -> None:
    """Aggregate extractions from a single document into overall results."""

    # Key dates
    for date_item in doc_extraction.get("key_dates", []):
        date_item["source_document"] = filename
        results["key_dates"].append(date_item)

    # Financial figures
    for fig in doc_extraction.get("financial_figures", []):
        fig["source_document"] = filename
        results["financial_figures"].append(fig)

    # Change of control clauses
    for coc in doc_extraction.get("change_of_control_clauses", []):
        coc["source_document"] = filename
        results["coc_clauses"].append(coc)

    # Consent requirements
    for consent in doc_extraction.get("consent_requirements", []):
        consent["source_document"] = filename
        results["consent_requirements"].append(consent)

    # Parties
    for party in doc_extraction.get("parties", []):
        party["source_document"] = filename
        results["parties"].append(party)

    # Covenants
    for covenant in doc_extraction.get("covenants", []):
        covenant["source_document"] = filename
        results["covenants"].append(covenant)

    # Phase 1 Enhancement: Document References
    for doc_ref in doc_extraction.get("document_references", []):
        doc_ref["source_document"] = filename
        results["document_references"].append(doc_ref)


def get_critical_dates(results: Dict[str, Any]) -> List[Dict]:
    """Get dates marked as critical."""
    return [d for d in results.get("key_dates", []) if d.get("is_critical")]


def get_coc_summary(results: Dict[str, Any]) -> str:
    """Generate a summary of change of control provisions."""
    coc_clauses = results.get("coc_clauses", [])
    if not coc_clauses:
        return "No change of control clauses identified."

    lines = [f"Found {len(coc_clauses)} change of control provisions:"]
    for coc in coc_clauses:
        doc = coc.get("source_document", "Unknown")
        clause = coc.get("clause_reference", "")
        consequence = coc.get("consequence", "")
        lines.append(f"  - {doc} ({clause}): {consequence[:100]}")

    return "\n".join(lines)


def get_financial_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize financial figures by type."""
    figures = results.get("financial_figures", [])

    by_type = {}
    for fig in figures:
        fig_type = fig.get("amount_type", "other")
        if fig_type not in by_type:
            by_type[fig_type] = []
        by_type[fig_type].append(fig)

    return {
        "total_figures": len(figures),
        "by_type": by_type,
    }


# ============================================================================
# PHASE 1 ENHANCEMENT: Document Reference Functions
# ============================================================================

def get_document_references(results: Dict[str, Any]) -> List[Dict]:
    """Get all document references extracted from Pass 1."""
    return results.get("document_references", [])


def get_critical_document_references(results: Dict[str, Any]) -> List[Dict]:
    """Get document references marked as critical."""
    return [
        ref for ref in results.get("document_references", [])
        if ref.get("criticality") == "critical"
    ]


def get_document_reference_summary(results: Dict[str, Any]) -> str:
    """Generate a summary of document references for Pass 3 gap analysis."""
    doc_refs = results.get("document_references", [])
    if not doc_refs:
        return "No document references identified."

    critical = [r for r in doc_refs if r.get("criticality") == "critical"]
    important = [r for r in doc_refs if r.get("criticality") == "important"]
    minor = [r for r in doc_refs if r.get("criticality") == "minor"]

    lines = [f"Found {len(doc_refs)} document references:"]
    lines.append(f"  - {len(critical)} critical (must verify presence)")
    lines.append(f"  - {len(important)} important")
    lines.append(f"  - {len(minor)} minor")

    if critical:
        lines.append("\nCritical referenced documents:")
        for ref in critical[:10]:  # Limit to top 10
            doc_name = ref.get("referenced_document", "Unknown")
            source = ref.get("source_document", "Unknown")
            context = ref.get("reference_context", "")[:100]
            lines.append(f"  - \"{doc_name}\" (from {source})")
            if context:
                lines.append(f"      Context: {context}")

    return "\n".join(lines)


def match_references_to_dataroom(
    document_references: List[Dict],
    available_documents: List[Dict]
) -> Dict[str, Any]:
    """
    Match extracted document references against available documents.

    Args:
        document_references: List of extracted references from Pass 1
        available_documents: List of documents in the data room (with 'filename' key)

    Returns:
        Dict with matched and unmatched references
    """
    available_names = {doc.get("filename", "").lower() for doc in available_documents}

    matched = []
    unmatched = []

    for ref in document_references:
        ref_name = ref.get("referenced_document", "").lower()

        # Simple fuzzy matching - check if any available doc contains keywords
        found = False
        for avail_name in available_names:
            # Check for substantial keyword overlap
            ref_words = set(ref_name.split())
            avail_words = set(avail_name.split())
            overlap = ref_words & avail_words

            # If more than 2 words match, consider it a potential match
            if len(overlap) >= 2 or ref_name in avail_name or avail_name in ref_name:
                matched_ref = {**ref, "matched_to": avail_name}
                matched.append(matched_ref)
                found = True
                break

        if not found:
            unmatched.append(ref)

    return {
        "matched": matched,
        "unmatched": unmatched,
        "total_references": len(document_references),
        "match_rate": len(matched) / len(document_references) if document_references else 0,
        "critical_unmatched": [
            r for r in unmatched if r.get("criticality") == "critical"
        ],
    }
