"""
Pass 2: Per-Document Analysis

Analyzes each document for risks and issues.

KEY IMPROVEMENT: Reference documents (MOI, SHA, Board Resolution) are
ALWAYS included in the context, so analysis can validate against
constitutional requirements.
"""
from typing import List, Dict, Any, Optional
import os
import sys

# Ensure dd_enhanced is in path for imports
_dd_enhanced_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dd_enhanced_path not in sys.path:
    sys.path.insert(0, _dd_enhanced_path)

from .claude_client import ClaudeClient
from .document_loader import LoadedDocument
from prompts.analysis import get_analysis_system_prompt, build_analysis_prompt


# Default transaction context for Karoo Mining
DEFAULT_TRANSACTION_CONTEXT = """
This is a 100% share sale acquisition of Karoo Mining (Pty) Ltd.
The buyer will acquire all issued shares from the current shareholders.
This constitutes a change of control for all purposes.

Key considerations:
- All change of control provisions will be triggered
- All consents for assignment/change of control are required
- The buyer will inherit all obligations and liabilities
"""


def run_pass2_analysis(
    documents: List[Dict],
    reference_docs: List[LoadedDocument],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    transaction_context: str = DEFAULT_TRANSACTION_CONTEXT,
    prioritized_questions: Optional[List[Dict]] = None,
    verbose: bool = True
) -> List[Dict]:
    """
    Run Pass 2: Analyze each document with reference context.

    KEY IMPROVEMENTS:
    - Reference documents are always in context
    - Prioritized questions from question_prioritizer guide the analysis

    Args:
        documents: List of document dicts
        reference_docs: Constitutional/governance docs to include in every analysis
        blueprint: DD blueprint with risk categories (optional)
        client: Claude API client
        transaction_context: Context about the transaction
        prioritized_questions: Tier 1-3 questions from question_prioritizer (optional)
        verbose: Print progress

    Returns:
        List of all findings from all documents
    """

    all_findings = []

    # Build reference documents context (always included)
    ref_context = _build_reference_context(reference_docs)
    if verbose and reference_docs:
        print(f"  Reference docs in context: {[d.filename for d in reference_docs]}")

    for i, doc in enumerate(documents, 1):
        filename = doc["filename"]
        doc_type = doc["doc_type"]

        # Skip reference docs in per-doc analysis (they're already in context)
        if doc_type in ("constitutional", "governance"):
            if verbose:
                print(f"  [{i}/{len(documents)}] Skipping {filename} (reference doc)")
            continue

        if verbose:
            print(f"  [{i}/{len(documents)}] Analyzing {filename}...")

        # Build analysis prompt with reference context, blueprint, and prioritized questions
        prompt = build_analysis_prompt(
            document_text=doc["text"][:40000],  # Limit per-doc text
            document_name=filename,
            doc_type=doc_type,
            reference_docs_text=ref_context,
            transaction_context=transaction_context,
            blueprint=blueprint,  # Pass blueprint for question injection
            prioritized_questions=prioritized_questions  # NEW: Pass prioritized questions
        )

        # Get blueprint-aware system prompt
        system_prompt = get_analysis_system_prompt(blueprint)

        # Call Claude (uses complete_analysis which uses Sonnet)
        response = client.complete_analysis(
            prompt=prompt,
            system=system_prompt,
            max_tokens=8192,
            temperature=0.1
        )

        if "error" in response:
            print(f"    Warning: Analysis failed for {filename}: {response.get('error')}")
            continue

        # Process findings
        findings = response.get("findings", [])
        for finding in findings:
            finding["source_document"] = filename
            finding["pass"] = 2
            all_findings.append(finding)

        if verbose:
            print(f"    Found {len(findings)} issues")

    return all_findings


def _build_reference_context(reference_docs: List[LoadedDocument]) -> str:
    """Build context string from reference documents."""
    if not reference_docs:
        return "[No reference documents provided]"

    sections = []
    for doc in reference_docs:
        # Include full text of reference docs (they're critical)
        sections.append(f"""
--- REFERENCE: {doc.filename} ({doc.doc_type.upper()}) ---
{doc.text[:30000]}
--- END {doc.filename} ---
""")

    return "\n\n".join(sections)


def filter_findings_by_severity(
    findings: List[Dict],
    min_severity: str = "medium"
) -> List[Dict]:
    """Filter findings to only include those at or above minimum severity."""
    severity_order = ["low", "medium", "high", "critical"]
    min_index = severity_order.index(min_severity)

    return [
        f for f in findings
        if severity_order.index(f.get("severity", "low")) >= min_index
    ]


def filter_findings_by_deal_impact(
    findings: List[Dict],
    deal_impacts: List[str]
) -> List[Dict]:
    """Filter findings by deal impact classification."""
    return [
        f for f in findings
        if f.get("deal_impact") in deal_impacts
    ]


def group_findings_by_category(findings: List[Dict]) -> Dict[str, List[Dict]]:
    """Group findings by category."""
    by_category = {}
    for finding in findings:
        category = finding.get("category", "other")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(finding)
    return by_category


def group_findings_by_document(findings: List[Dict]) -> Dict[str, List[Dict]]:
    """Group findings by source document."""
    by_doc = {}
    for finding in findings:
        doc = finding.get("source_document", "unknown")
        if doc not in by_doc:
            by_doc[doc] = []
        by_doc[doc].append(finding)
    return by_doc


def get_deal_blockers(findings: List[Dict]) -> List[Dict]:
    """Get findings classified as deal blockers."""
    return [f for f in findings if f.get("deal_impact") == "deal_blocker"]


def get_conditions_precedent(findings: List[Dict]) -> List[Dict]:
    """Get findings classified as conditions precedent."""
    return [f for f in findings if f.get("deal_impact") == "condition_precedent"]


def summarize_findings(findings: List[Dict]) -> Dict[str, Any]:
    """Generate summary statistics for findings."""
    return {
        "total": len(findings),
        "by_severity": {
            "critical": len([f for f in findings if f.get("severity") == "critical"]),
            "high": len([f for f in findings if f.get("severity") == "high"]),
            "medium": len([f for f in findings if f.get("severity") == "medium"]),
            "low": len([f for f in findings if f.get("severity") == "low"]),
        },
        "by_deal_impact": {
            "deal_blocker": len([f for f in findings if f.get("deal_impact") == "deal_blocker"]),
            "condition_precedent": len([f for f in findings if f.get("deal_impact") == "condition_precedent"]),
            "price_chip": len([f for f in findings if f.get("deal_impact") == "price_chip"]),
            "warranty_indemnity": len([f for f in findings if f.get("deal_impact") == "warranty_indemnity"]),
            "post_closing": len([f for f in findings if f.get("deal_impact") == "post_closing"]),
            "noted": len([f for f in findings if f.get("deal_impact") == "noted"]),
        },
        "by_category": {
            cat: len(items)
            for cat, items in group_findings_by_category(findings).items()
        },
    }
