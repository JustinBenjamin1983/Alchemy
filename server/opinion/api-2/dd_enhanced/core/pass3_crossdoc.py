"""
Pass 3: Cross-Document Synthesis

THIS IS THE KEY ARCHITECTURAL IMPROVEMENT.

The original system processes documents in isolation.
This pass puts ALL documents in context together to find:
- Conflicts between documents
- Cascade effects across contracts
- Authorization gaps
- Consent matrices

This is what separates thorough DD from checkbox DD.
"""
from typing import List, Dict, Any, Optional
import os
import sys

# Ensure dd_enhanced is in path for imports
_dd_enhanced_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dd_enhanced_path not in sys.path:
    sys.path.insert(0, _dd_enhanced_path)

from .claude_client import ClaudeClient
from prompts.crossdoc import (
    get_crossdoc_system_prompt,
    build_conflict_detection_prompt,
    build_cascade_mapping_prompt,
    build_authorization_check_prompt,
    build_consent_matrix_prompt,
    build_missing_document_prompt,
)


def run_pass3_crossdoc_synthesis(
    documents: List[Dict],
    pass2_findings: List[Dict],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Pass 3: Cross-document synthesis.

    THIS IS THE KEY IMPROVEMENT over the original system.

    This pass:
    1. Puts ALL documents in a single context
    2. Looks for CONFLICTS between documents
    3. Maps change of control CASCADE across all contracts
    4. Validates governance (does Board Resolution authorize what MOI requires?)
    5. Builds consent matrix

    Args:
        documents: List of document dicts
        pass2_findings: Findings from Pass 2
        blueprint: DD blueprint (optional)
        client: Claude API client
        verbose: Print progress

    Returns:
        Dict with conflicts, cascade, authorization issues, consent matrix
    """

    results = {
        "conflicts": [],
        "cascade_analysis": {},
        "authorization_issues": [],
        "consent_matrix": [],
        "missing_documents": [],
        "cross_doc_findings": [],
    }

    # Build combined document context
    # This is the key: ALL documents in ONE context
    doc_context = _build_full_document_context(documents)

    if verbose:
        total_chars = len(doc_context)
        print(f"  Total context size: {total_chars:,} characters (~{total_chars//4:,} tokens)")

    # Get blueprint-aware system prompt
    system_prompt = get_crossdoc_system_prompt(blueprint)

    # 3.1 Conflict Detection
    if verbose:
        print("  [3.1] Detecting cross-document conflicts...")
    results["conflicts"] = _detect_conflicts(doc_context, client, blueprint, system_prompt)
    if verbose:
        print(f"       Found {len(results['conflicts'])} conflicts")

    # 3.2 Change of Control Cascade Mapping
    if verbose:
        print("  [3.2] Mapping change of control cascade...")
    results["cascade_analysis"] = _map_coc_cascade(doc_context, client, blueprint, system_prompt)
    cascade_items = results["cascade_analysis"].get("cascade_items", [])
    if verbose:
        print(f"       Mapped {len(cascade_items)} cascade items")

    # 3.3 Authorization Validation (MOI vs Board Resolution)
    if verbose:
        print("  [3.3] Validating governance authorizations...")
    results["authorization_issues"] = _validate_authorizations(doc_context, client, blueprint, system_prompt)
    if verbose:
        print(f"       Found {len(results['authorization_issues'])} authorization issues")

    # 3.4 Consent Matrix
    if verbose:
        print("  [3.4] Building consent matrix...")
    results["consent_matrix"] = _build_consent_matrix_result(doc_context, client, blueprint, system_prompt)
    if verbose:
        print(f"       Identified {len(results['consent_matrix'])} consent requirements")

    # 3.5 Missing Document Detection
    if verbose:
        print("  [3.5] Detecting missing documents...")
    document_names = [doc.get('filename', doc.get('original_file_name', 'Unknown')) for doc in documents]
    results["missing_documents"] = _detect_missing_documents(doc_context, document_names, client, blueprint, system_prompt)
    if verbose:
        missing_count = len(results["missing_documents"].get("missing_documents", []))
        print(f"       Found {missing_count} missing/referenced documents")

    # Convert to cross-doc findings
    results["cross_doc_findings"] = _convert_to_findings(results)

    return results


def _build_full_document_context(documents: List[Dict]) -> str:
    """
    Build a single context string with ALL documents.

    This is the key difference from the original system which
    processed documents one at a time.
    """
    sections = []

    # Sort by document type to put constitutional docs first
    type_order = {"constitutional": 0, "governance": 1, "regulatory": 2,
                  "contract": 3, "financial": 4, "employment": 5, "other": 6}

    sorted_docs = sorted(
        documents,
        key=lambda d: type_order.get(d.get("doc_type", "other"), 6)
    )

    for doc in sorted_docs:
        sections.append(f"""
{'='*70}
DOCUMENT: {doc['filename']}
TYPE: {doc.get('doc_type', 'unknown').upper()}
WORDS: {doc.get('word_count', len(doc.get('text', '').split())):,}
{'='*70}

{doc['text'][:25000]}
""")

    return "\n\n".join(sections)


def _detect_conflicts(
    doc_context: str,
    client: ClaudeClient,
    blueprint: Optional[Dict],
    system_prompt: str
) -> List[Dict]:
    """Detect conflicts between documents."""

    prompt = build_conflict_detection_prompt(doc_context, blueprint)

    response = client.complete_critical(
        prompt=prompt,
        system=system_prompt,
        json_mode=True,
        max_tokens=4096
    )

    if "error" in response:
        print(f"    Warning: Conflict detection failed: {response.get('error')}")
        return []

    return response.get("conflicts", [])


def _map_coc_cascade(
    doc_context: str,
    client: ClaudeClient,
    blueprint: Optional[Dict],
    system_prompt: str
) -> Dict[str, Any]:
    """Map how change of control cascades across all documents."""

    prompt = build_cascade_mapping_prompt(
        doc_context,
        trigger_event="100% share acquisition",
        blueprint=blueprint
    )

    response = client.complete_critical(
        prompt=prompt,
        system=system_prompt,
        json_mode=True,
        max_tokens=8192
    )

    if "error" in response:
        print(f"    Warning: Cascade mapping failed: {response.get('error')}")
        return {}

    return response


def _validate_authorizations(
    doc_context: str,
    client: ClaudeClient,
    blueprint: Optional[Dict],
    system_prompt: str
) -> List[Dict]:
    """Check if Board Resolution authorizes what MOI/SHA require."""

    prompt = build_authorization_check_prompt(doc_context, blueprint)

    response = client.complete_critical(
        prompt=prompt,
        system=system_prompt,
        json_mode=True,
        max_tokens=4096
    )

    if "error" in response:
        print(f"    Warning: Authorization check failed: {response.get('error')}")
        return []

    # Extract authorization gaps
    gaps = response.get("authorization_gaps", [])

    # If the response itself indicates a gap, add it
    if response.get("authorization_gaps") is None:
        # Check if there's an overall gap indicated
        auth_gap = response.get("authorization_gap", {})
        if auth_gap.get("exists"):
            gaps = [auth_gap]

    return gaps


def _build_consent_matrix_result(
    doc_context: str,
    client: ClaudeClient,
    blueprint: Optional[Dict],
    system_prompt: str
) -> List[Dict]:
    """Build comprehensive consent matrix."""

    prompt = build_consent_matrix_prompt(doc_context, blueprint)

    response = client.complete_critical(
        prompt=prompt,
        system=system_prompt,
        json_mode=True,
        max_tokens=4096
    )

    if "error" in response:
        print(f"    Warning: Consent matrix failed: {response.get('error')}")
        return []

    return response.get("consent_matrix", [])


def _detect_missing_documents(
    doc_context: str,
    document_names: List[str],
    client: ClaudeClient,
    blueprint: Optional[Dict],
    system_prompt: str
) -> Dict:
    """Detect documents referenced but not provided in the data room."""

    prompt = build_missing_document_prompt(doc_context, document_names, blueprint)

    response = client.complete_critical(
        prompt=prompt,
        system=system_prompt,
        json_mode=True,
        max_tokens=4096
    )

    if "error" in response:
        print(f"    Warning: Missing document detection failed: {response.get('error')}")
        return {"missing_documents": [], "incomplete_documents": [], "summary": {}}

    return response


def _convert_to_findings(results: Dict[str, Any]) -> List[Dict]:
    """Convert Pass 3 results to finding format for consistency."""

    findings = []
    finding_id = 1

    # Conflicts become findings
    for conflict in results.get("conflicts", []):
        findings.append({
            "finding_id": f"CONFLICT-{finding_id:03d}",
            "finding_type": "conflict",
            "category": "cross_document",
            "description": conflict.get("description", ""),
            "source_document": f"{conflict.get('document_a')} vs {conflict.get('document_b')}",
            "source_documents": [conflict.get("document_a"), conflict.get("document_b")],
            "severity": conflict.get("severity", "high"),
            "deal_impact": conflict.get("deal_impact", "requires_resolution"),
            "evidence_quote": f"Doc A: {conflict.get('document_a_provision', '')[:100]} | Doc B: {conflict.get('document_b_provision', '')[:100]}",
            "action_required": conflict.get("resolution_required"),
            "pass": 3,
        })
        finding_id += 1

    # Authorization gaps become findings
    for gap in results.get("authorization_issues", []):
        findings.append({
            "finding_id": f"AUTH-{finding_id:03d}",
            "finding_type": "authorization_gap",
            "category": "governance",
            "description": gap.get("description", ""),
            "source_document": "MOI / Board Resolution",
            "severity": gap.get("severity", "critical"),
            "deal_impact": gap.get("deal_impact", "deal_blocker"),
            "action_required": gap.get("remediation"),
            "pass": 3,
        })
        finding_id += 1

    # Cascade items that are deal blockers become findings
    cascade = results.get("cascade_analysis", {})
    for item in cascade.get("cascade_items", []):
        if item.get("risk_level") in ["critical", "high"]:
            financial = item.get("financial_exposure", {})
            findings.append({
                "finding_id": f"CASCADE-{finding_id:03d}",
                "finding_type": "cascade",
                "category": "change_of_control",
                "description": f"{item.get('document')}: {item.get('consequence', '')}",
                "source_document": item.get("document", ""),
                "clause_reference": item.get("clause_reference"),
                "severity": "critical" if item.get("risk_level") == "critical" else "high",
                "deal_impact": item.get("deal_impact", "condition_precedent"),
                "financial_exposure": financial,
                "action_required": f"Obtain consent from {item.get('consent_from')}" if item.get("consent_required") else None,
                "pass": 3,
            })
            finding_id += 1

    # Missing documents become findings
    missing_docs = results.get("missing_documents", {})
    for missing in missing_docs.get("missing_documents", []):
        severity_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
        findings.append({
            "finding_id": f"MISSING-{finding_id:03d}",
            "finding_type": "missing_document",
            "category": "document_gap",
            "description": f"Missing document: {missing.get('referenced_as', 'Unknown document')}. {missing.get('why_needed', '')}",
            "source_document": missing.get("referenced_in", "Multiple documents"),
            "clause_reference": missing.get("clause_reference"),
            "severity": severity_map.get(missing.get("criticality", "medium"), "medium"),
            "deal_impact": "deal_blocker" if missing.get("is_deal_blocker") else "condition_precedent",
            "action_required": f"Request {missing.get('referenced_as')} from seller",
            "evidence_quote": f"Referenced in {missing.get('referenced_in')} as '{missing.get('referenced_as')}'",
            "pass": 3,
        })
        finding_id += 1

    # Incomplete documents (missing annexures/schedules)
    for incomplete in missing_docs.get("incomplete_documents", []):
        findings.append({
            "finding_id": f"INCOMPLETE-{finding_id:03d}",
            "finding_type": "incomplete_document",
            "category": "document_gap",
            "description": f"Incomplete document: {incomplete.get('document_name')} - missing {incomplete.get('missing_attachment')}",
            "source_document": incomplete.get("document_name", "Unknown"),
            "severity": "medium",
            "deal_impact": "requires_resolution",
            "action_required": f"Obtain {incomplete.get('missing_attachment')} for {incomplete.get('document_name')}",
            "pass": 3,
        })
        finding_id += 1

    return findings


def get_cascade_summary(cascade_analysis: Dict) -> str:
    """Generate human-readable cascade summary."""

    items = cascade_analysis.get("cascade_items", [])
    if not items:
        return "No change of control cascade identified."

    lines = [
        f"CHANGE OF CONTROL CASCADE ANALYSIS",
        f"Trigger: {cascade_analysis.get('trigger_event', 'Share acquisition')}",
        f"",
        f"Affected Contracts ({len(items)}):",
    ]

    for item in items:
        doc = item.get("document", "Unknown")
        consequence = item.get("consequence", "")
        risk = item.get("risk_level", "medium")
        consent = "Consent required" if item.get("consent_required") else "No consent needed"

        lines.append(f"  - [{risk.upper()}] {doc}")
        lines.append(f"    {consequence[:100]}")
        lines.append(f"    {consent}")

        financial = item.get("financial_exposure", {})
        if financial and financial.get("amount"):
            lines.append(f"    Exposure: R{financial['amount']:,.0f}")

    total = cascade_analysis.get("total_financial_exposure", {})
    if total and total.get("amount"):
        lines.append(f"")
        lines.append(f"TOTAL FINANCIAL EXPOSURE: R{total['amount']:,.0f}")

    return "\n".join(lines)
