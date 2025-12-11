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
