"""
Pass 4: Deal Synthesis

Final pass that:
1. Consolidates all findings from Passes 2 & 3
2. Calculates financial exposures
3. Classifies deal-blockers
4. Generates conditions precedent register
5. Creates executive summary

This produces the actionable DD output.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
import json
import os
import sys

# Ensure dd_enhanced is in path for imports
_dd_enhanced_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dd_enhanced_path not in sys.path:
    sys.path.insert(0, _dd_enhanced_path)

from .claude_client import ClaudeClient
from prompts.synthesis import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_prompt


def run_pass4_synthesis(
    documents: List[Dict],
    pass1_extracts: Dict,
    pass2_findings: List[Dict],
    pass3_results: Dict,
    client: ClaudeClient,
    transaction_value: str = "undisclosed",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Pass 4: Final synthesis and deal analysis.

    Args:
        documents: Original document list
        pass1_extracts: Structured extractions from Pass 1
        pass2_findings: Findings from Pass 2
        pass3_results: Cross-document analysis from Pass 3
        client: Claude API client
        transaction_value: Transaction value for context
        verbose: Print progress

    Returns:
        Complete synthesis with deal-blockers, exposures, CP register, summary
    """

    results = {
        "all_findings": [],
        "financial_exposures": {},
        "deal_blockers": [],
        "conditions_precedent": [],
        "executive_summary": "",
        "recommendations": [],
    }

    # 4.1 Calculate Financial Exposures
    if verbose:
        print("  [4.1] Calculating financial exposures...")
    results["financial_exposures"] = _calculate_exposures(
        pass1_extracts,
        pass3_results.get("cascade_analysis", {})
    )

    # 4.2 Consolidate all findings
    if verbose:
        print("  [4.2] Consolidating findings...")
    all_findings = _consolidate_findings(pass2_findings, pass3_results)
    results["all_findings"] = all_findings

    # 4.3 Generate synthesis via Claude
    if verbose:
        print("  [4.3] Generating deal synthesis...")

    synthesis = _generate_synthesis(
        pass2_findings,
        pass3_results,
        client,
        transaction_value
    )

    # 4.4 Extract deal-blockers
    results["deal_blockers"] = synthesis.get("deal_blockers", [])
    if not results["deal_blockers"]:
        # Also check from our findings
        results["deal_blockers"] = [
            f for f in all_findings
            if f.get("deal_impact") == "deal_blocker"
        ]

    # 4.5 Build CP register
    results["conditions_precedent"] = synthesis.get("conditions_precedent_register", [])
    if not results["conditions_precedent"]:
        results["conditions_precedent"] = _build_cp_register(
            all_findings,
            pass3_results.get("consent_matrix", [])
        )

    # 4.6 Executive summary
    results["executive_summary"] = synthesis.get("executive_summary", "")
    results["deal_assessment"] = synthesis.get("deal_assessment", {})
    results["recommendations"] = synthesis.get("key_recommendations", [])

    if verbose:
        blockers = len(results["deal_blockers"])
        cps = len(results["conditions_precedent"])
        print(f"       Deal blockers: {blockers}")
        print(f"       Conditions precedent: {cps}")

    return results


def _calculate_exposures(
    extracts: Dict,
    cascade: Dict
) -> Dict[str, Any]:
    """
    Calculate all financial exposures from extracted data and cascade analysis.

    KEY IMPROVEMENT: Actually performs calculations instead of just quoting clauses.
    """

    exposures = {
        "items": [],
        "total": Decimal("0"),
        "currency": "ZAR",
        "calculation_notes": [],
    }

    # Process cascade items for financial exposure
    for item in cascade.get("cascade_items", []):
        fin_exp = item.get("financial_exposure", {})
        if fin_exp and fin_exp.get("amount"):
            try:
                amount = Decimal(str(fin_exp.get("amount", 0)))
                exposures["items"].append({
                    "source": item.get("document", "Unknown"),
                    "type": fin_exp.get("exposure_type", fin_exp.get("type", "other")),
                    "amount": float(amount),
                    "calculation": fin_exp.get("calculation_basis", "As stated"),
                    "triggered_by": "Change of control",
                    "risk_level": item.get("risk_level", "medium"),
                })
                exposures["total"] += amount
            except (ValueError, TypeError) as e:
                exposures["calculation_notes"].append(
                    f"Could not parse amount from {item.get('document')}: {e}"
                )

    # Look for specific calculations we can derive
    # Example: Eskom liquidated damages
    financial_figures = extracts.get("financial_figures", [])
    coc_clauses = extracts.get("coc_clauses", [])

    for coc in coc_clauses:
        financial_consequence = coc.get("financial_consequence") or ""
        if "liquidated" in financial_consequence.lower():
            # Try to find related financial figure
            source_doc = coc.get("source_document", "")
            related_figures = [
                f for f in financial_figures
                if f.get("source_document") == source_doc
            ]

            # Attempt to calculate if we have the inputs
            for fig in related_figures:
                if fig.get("amount_type") in ["revenue", "loan_principal", "limit"]:
                    # This is a value we might use for calculation
                    exposures["calculation_notes"].append(
                        f"Potential calculation input: {source_doc} has {fig.get('amount_type')} of {fig.get('amount')} {fig.get('currency', 'ZAR')}"
                    )

    # Format total
    exposures["total"] = float(exposures["total"])

    return exposures


def _consolidate_findings(
    pass2_findings: List[Dict],
    pass3_results: Dict
) -> List[Dict]:
    """Consolidate findings from Pass 2 and Pass 3."""

    all_findings = []

    # Add Pass 2 findings
    for finding in pass2_findings:
        finding["pass"] = 2
        all_findings.append(finding)

    # Add Pass 3 cross-doc findings
    for finding in pass3_results.get("cross_doc_findings", []):
        finding["pass"] = 3
        all_findings.append(finding)

    # Sort by severity (critical first) then by deal impact
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    impact_order = {
        "deal_blocker": 0,
        "condition_precedent": 1,
        "price_chip": 2,
        "warranty_indemnity": 3,
        "post_closing": 4,
        "noted": 5,
    }

    all_findings.sort(key=lambda f: (
        severity_order.get(f.get("severity", "medium"), 2),
        impact_order.get(f.get("deal_impact", "noted"), 5)
    ))

    return all_findings


def _generate_synthesis(
    pass2_findings: List[Dict],
    pass3_results: Dict,
    client: ClaudeClient,
    transaction_value: str
) -> Dict[str, Any]:
    """Generate final synthesis via Claude."""

    # Prepare inputs as strings
    pass2_str = json.dumps(pass2_findings[:20], indent=2)  # Limit for context
    conflicts_str = json.dumps(pass3_results.get("conflicts", []), indent=2)
    cascade_str = json.dumps(pass3_results.get("cascade_analysis", {}), indent=2)
    auth_str = json.dumps(pass3_results.get("authorization_issues", []), indent=2)
    consents_str = json.dumps(pass3_results.get("consent_matrix", [])[:15], indent=2)

    prompt = build_synthesis_prompt(
        pass2_findings=pass2_str,
        pass3_conflicts=conflicts_str,
        pass3_cascade=cascade_str,
        pass3_authorization=auth_str,
        pass3_consents=consents_str,
        transaction_value=transaction_value
    )

    response = client.complete_critical(
        prompt=prompt,
        system=SYNTHESIS_SYSTEM_PROMPT,
        json_mode=True,
        max_tokens=8192
    )

    if "error" in response:
        print(f"    Warning: Synthesis generation failed: {response.get('error')}")
        return {}

    return response


def _build_cp_register(
    findings: List[Dict],
    consent_matrix: List[Dict]
) -> List[Dict]:
    """Build conditions precedent register from findings and consents."""

    cp_register = []
    cp_num = 1

    # Add CPs from consent matrix
    for consent in consent_matrix:
        if consent.get("is_deal_blocker") or consent.get("consequence_if_not_obtained"):
            cp_register.append({
                "cp_number": cp_num,
                "description": f"Obtain {consent.get('consent_type', 'consent')} from {consent.get('counterparty', 'counterparty')}",
                "category": "consent",
                "source": consent.get("contract", "Unknown"),
                "responsible_party": consent.get("responsible_party", "seller"),
                "status": consent.get("status", "not_started"),
                "is_deal_blocker": consent.get("is_deal_blocker", False),
            })
            cp_num += 1

    # Add CPs from findings
    for finding in findings:
        if finding.get("deal_impact") == "condition_precedent":
            cp_register.append({
                "cp_number": cp_num,
                "description": finding.get("action_required") or finding.get("description", ""),
                "category": finding.get("category", "other"),
                "source": finding.get("source_document", "Unknown"),
                "responsible_party": finding.get("responsible_party", "seller"),
                "status": "not_started",
                "is_deal_blocker": False,
            })
            cp_num += 1

    return cp_register


def format_executive_summary(synthesis: Dict) -> str:
    """Format executive summary for display."""

    lines = []

    # Deal assessment
    assessment = synthesis.get("deal_assessment", {})
    can_proceed = assessment.get("can_proceed", "unknown")
    risk_rating = assessment.get("overall_risk_rating", "unknown")

    lines.append("=" * 60)
    lines.append("EXECUTIVE SUMMARY")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Can Proceed: {'YES (subject to conditions)' if can_proceed else 'NO - blocking issues'}")
    lines.append(f"Overall Risk Rating: {risk_rating.upper()}")
    lines.append("")

    # Summary text
    if synthesis.get("executive_summary"):
        lines.append(synthesis["executive_summary"])
        lines.append("")

    # Blocking issues
    blockers = assessment.get("blocking_issues", [])
    if blockers:
        lines.append("BLOCKING ISSUES:")
        for blocker in blockers:
            lines.append(f"  - {blocker}")
        lines.append("")

    # Key risks
    risks = assessment.get("key_risks", [])
    if risks:
        lines.append("KEY RISKS:")
        for risk in risks:
            lines.append(f"  - {risk}")
        lines.append("")

    # Recommendations
    recs = synthesis.get("key_recommendations", [])
    if recs:
        lines.append("RECOMMENDATIONS:")
        for rec in recs:
            lines.append(f"  - {rec}")

    return "\n".join(lines)
