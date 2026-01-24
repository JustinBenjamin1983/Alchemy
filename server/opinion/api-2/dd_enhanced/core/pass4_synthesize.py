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
    verbose: bool = True,
    validated_context: Optional[Dict] = None
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
        validated_context: User-validated corrections from Checkpoint B containing:
            - transaction_understanding: User corrections to structure, parties, deal type
            - financial_corrections: Corrected financial values
            - manual_inputs: Manually entered data

    Returns:
        Complete synthesis with deal-blockers, exposures, CP register, summary
    """

    # Defensive: ensure inputs are not None
    documents = documents or []
    pass1_extracts = pass1_extracts or {}
    pass2_findings = pass2_findings or []
    pass3_results = pass3_results or {}

    results = {
        "all_findings": [],
        "financial_exposures": {},
        "deal_blockers": [],
        "conditions_precedent": [],
        "warranties_register": [],
        "indemnities_register": [],
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
    # Defensive: ensure inputs are not None before consolidation
    all_findings = _consolidate_findings(pass2_findings or [], pass3_results or {})
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

    # 4.5b Extract warranties register
    results["warranties_register"] = synthesis.get("warranties_register", [])
    if not results["warranties_register"]:
        # Fallback: generate basic warranties from findings with deal_impact = 'warranty_indemnity'
        warranty_findings = [f for f in all_findings if f.get("deal_impact") == "warranty_indemnity"]
        results["warranties_register"] = [
            {
                "id": f"W-{i+1:03d}",
                "category": f.get("category", "General"),
                "description": f.get("description", ""),
                "detailed_wording": f"The Seller warrants that {f.get('description', '').lower()}",
                "typical_cap": "50% of purchase price",
                "survival_period": "3 years",
                "priority": f.get("severity", "medium"),
                "dd_trigger": f.get("description", ""),
                "source_document": f.get("source_document", "")
            }
            for i, f in enumerate(warranty_findings[:20])  # Limit to first 20
        ]

    # 4.5c Extract indemnities register
    results["indemnities_register"] = synthesis.get("indemnities_register", [])
    if not results["indemnities_register"]:
        # Fallback: generate indemnities from critical/high severity findings with quantified exposure
        indemnity_findings = [
            f for f in all_findings
            if f.get("severity") in ("critical", "high")
            and f.get("financial_exposure", {}).get("amount")
        ]
        results["indemnities_register"] = [
            {
                "id": f"I-{i+1:03d}",
                "category": f.get("category", "General"),
                "description": f.get("description", ""),
                "detailed_wording": f"The Seller shall indemnify the Buyer against all Losses arising from {f.get('description', '').lower()}",
                "trigger": f.get("action_required", "Pre-closing issue identified"),
                "typical_cap": "Quantified amount",
                "survival_period": "5 years",
                "priority": f.get("severity", "high"),
                "escrow_recommendation": None,
                "quantified_exposure": f.get("financial_exposure", {}),
                "dd_trigger": f.get("description", ""),
                "source_document": f.get("source_document", "")
            }
            for i, f in enumerate(indemnity_findings[:15])  # Limit to first 15
        ]

    # 4.6 Executive summary
    results["executive_summary"] = synthesis.get("executive_summary", "")
    results["deal_assessment"] = synthesis.get("deal_assessment", {})
    results["recommendations"] = synthesis.get("key_recommendations", [])

    # 4.7 Financial analysis (from synthesis)
    results["financial_analysis"] = synthesis.get("financial_analysis", {})

    if verbose:
        blockers = len(results["deal_blockers"])
        cps = len(results["conditions_precedent"])
        warranties = len(results["warranties_register"])
        indemnities = len(results["indemnities_register"])
        print(f"       Deal blockers: {blockers}")
        print(f"       Conditions precedent: {cps}")
        print(f"       Warranties: {warranties}")
        print(f"       Indemnities: {indemnities}")

    return results


def _calculate_exposures(
    extracts: Dict,
    cascade: Dict
) -> Dict[str, Any]:
    """
    Calculate all financial exposures from extracted data and cascade analysis.

    KEY IMPROVEMENT: Actually performs calculations instead of just quoting clauses.
    """

    # Defensive: handle None inputs
    extracts = extracts or {}
    cascade = cascade or {}

    exposures = {
        "items": [],
        "total": Decimal("0"),
        "currency": "ZAR",
        "calculation_notes": [],
    }

    # Process cascade items for financial exposure (defensive: handle None)
    cascade_items = cascade.get("cascade_items") or []
    for item in cascade_items:
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
    financial_figures = extracts.get("financial_figures") or []
    coc_clauses = extracts.get("coc_clauses") or []

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
    """Consolidate findings from Pass 2 and Pass 3 with deduplication."""

    all_findings = []

    # Add Pass 2 findings (defensive: handle None)
    for finding in (pass2_findings or []):
        finding["pass"] = 2
        all_findings.append(finding)

    # Add Pass 3 cross-doc findings (defensive: handle None or missing key)
    cross_doc = pass3_results.get("cross_doc_findings") if pass3_results else []
    for finding in (cross_doc or []):
        finding["pass"] = 3
        all_findings.append(finding)

    # Deduplicate findings - merge similar findings about the same issue
    all_findings = _deduplicate_findings(all_findings)

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


def _deduplicate_findings(findings: List[Dict]) -> List[Dict]:
    """
    Deduplicate findings that cover the same issue.

    Enhanced strategy:
    1. Extract key entities (companies, clauses, amounts) from descriptions
    2. Group findings by category + key entities + semantic similarity
    3. For each group, keep the most severe/detailed finding
    4. Merge document references into the kept finding
    """
    if not findings:
        return []

    import re

    # Normalize text for comparison
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by',
                     'from', 'this', 'that', 'these', 'those', 'which', 'who',
                     'whom', 'whose', 'and', 'or', 'but', 'if', 'then', 'than',
                     'document', 'finding', 'issue', 'risk', 'concern', 'noted',
                     'identified', 'found', 'contains', 'includes', 'requires'}
        words = [w for w in text.split() if w not in stop_words and len(w) > 2]
        return ' '.join(sorted(set(words)))

    def extract_key_entities(text: str) -> set:
        """Extract key entities like company names, clause refs, amounts."""
        if not text:
            return set()
        entities = set()
        # Clause references (e.g., "clause 12.3", "section 5.2")
        clause_refs = re.findall(r'(?:clause|section|article)\s*[\d.]+', text.lower())
        entities.update(clause_refs)
        # Amounts (e.g., "R450M", "R2.4 billion")
        amounts = re.findall(r'r[\d,.]+\s*(?:m|bn|billion|million)?', text.lower())
        entities.update(amounts)
        # Company names (capitalized words that might be names)
        company_patterns = re.findall(r'[A-Z][a-z]+(?:\s+(?:Pty|Ltd|Inc|Holdings|Capital|Bank))?', text)
        entities.update([c.lower() for c in company_patterns])
        return entities

    def similarity_score(desc1: str, desc2: str) -> float:
        """Calculate Jaccard similarity between two descriptions."""
        words1 = set(normalize(desc1).split())
        words2 = set(normalize(desc2).split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    # First pass: group by category + key entities
    groups: Dict[str, List[Dict]] = {}

    for finding in findings:
        category = finding.get("category", "other")
        desc = finding.get("description", "")
        clause_ref = finding.get("clause_reference", "")

        # Create a key from category + key entities
        entities = extract_key_entities(desc + " " + clause_ref)
        desc_normalized = normalize(desc)
        desc_words = desc_normalized.split()[:7]  # First 7 significant words

        # Primary key: category + clause ref (if available)
        if clause_ref:
            key = f"{category}:{clause_ref.lower().replace(' ', '')}"
        else:
            key = f"{category}:{' '.join(desc_words)}"

        if key not in groups:
            groups[key] = []
        groups[key].append(finding)

    # Second pass: merge groups with high similarity
    merged_groups = {}
    processed_keys = set()

    for key1, group1 in groups.items():
        if key1 in processed_keys:
            continue

        merged_group = list(group1)
        processed_keys.add(key1)

        # Check similarity with other groups
        for key2, group2 in groups.items():
            if key2 in processed_keys or key1 == key2:
                continue

            # Same category check
            cat1 = key1.split(':')[0]
            cat2 = key2.split(':')[0]
            if cat1 != cat2:
                continue

            # Check description similarity
            desc1 = group1[0].get("description", "")
            desc2 = group2[0].get("description", "")
            sim = similarity_score(desc1, desc2)

            if sim > 0.5:  # High similarity threshold
                merged_group.extend(group2)
                processed_keys.add(key2)

        merged_groups[key1] = merged_group

    groups = merged_groups

    # For each group, keep the best finding
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    impact_rank = {"deal_blocker": 0, "condition_precedent": 1, "price_chip": 2,
                   "warranty_indemnity": 3, "post_closing": 4, "noted": 5}

    deduplicated = []

    for key, group in groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
            continue

        # Sort by severity + impact + description length (more detail = better)
        group.sort(key=lambda f: (
            severity_rank.get(f.get("severity", "medium"), 2),
            impact_rank.get(f.get("deal_impact", "noted"), 5),
            -len(f.get("description", ""))  # Longer descriptions first
        ))

        # Keep the best finding
        best = group[0].copy()

        # Merge document references from all findings in group
        all_docs = set()
        all_clauses = set()
        for f in group:
            if f.get("document"):
                all_docs.add(f.get("document"))
            if f.get("clause_reference"):
                all_clauses.add(f.get("clause_reference"))

        if len(all_docs) > 1:
            best["merged_from_documents"] = list(all_docs)
        if len(all_clauses) > 1:
            best["all_clause_references"] = list(all_clauses)

        best["duplicate_count"] = len(group)

        deduplicated.append(best)

    return deduplicated


def _generate_synthesis(
    pass2_findings: List[Dict],
    pass3_results: Dict,
    client: ClaudeClient,
    transaction_value: str
) -> Dict[str, Any]:
    """Generate final synthesis via Claude."""

    # Defensive: handle None inputs
    pass2_findings = pass2_findings or []
    pass3_results = pass3_results or {}

    # Prepare inputs as strings
    pass2_str = json.dumps(pass2_findings[:20], indent=2)  # Limit for context
    conflicts_str = json.dumps(pass3_results.get("conflicts") or [], indent=2)
    cascade_str = json.dumps(pass3_results.get("cascade_analysis") or {}, indent=2)
    auth_str = json.dumps(pass3_results.get("authorization_issues") or [], indent=2)
    consents = pass3_results.get("consent_matrix") or []
    consents_str = json.dumps(consents[:15], indent=2)

    prompt = build_synthesis_prompt(
        pass2_findings=pass2_str,
        pass3_conflicts=conflicts_str,
        pass3_cascade=cascade_str,
        pass3_authorization=auth_str,
        pass3_consents=consents_str,
        transaction_value=transaction_value,
        validated_context=validated_context
    )

    # Note: complete_critical already sets json_mode=True internally
    response = client.complete_critical(
        prompt=prompt,
        system=SYNTHESIS_SYSTEM_PROMPT,
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

    # Add CPs from consent matrix (defensive: handle None)
    for consent in (consent_matrix or []):
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

    # Add CPs from findings (defensive: handle None)
    for finding in (findings or []):
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
