"""
Materiality Thresholds

Calculates materiality thresholds based on transaction value and applies
classifications to findings. Enables prioritization based on financial
significance. Note: ALL findings are included in the report - this module
classifies them, it does NOT filter/exclude documents or findings.

Thresholds (with transaction value):
- Material: >= 5% of transaction value
- Potentially Material: 1-5% of transaction value
- Likely Immaterial: < 1% of transaction value

Thresholds (without transaction value):
- Material: > R10,000,000
- Potentially Material: R1,000,000 - R10,000,000
- Likely Immaterial: < R1,000,000

Qualitative Overrides:
Certain categories are always material regardless of amount:
- Criminal liability risk
- License/permit risk
- Regulatory sanctions
- Deal blockers
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# Categories that are always material regardless of amount
ALWAYS_MATERIAL_CATEGORIES = [
    "criminal",
    "license_risk",
    "regulatory",
    "deal_blocker",
    "environmental_criminal",
    "dmre_sanction",
    "mining_right_invalidity",
    "tax_fraud",
    "bribery",
    "money_laundering",
]

# Deal impacts that are always material
ALWAYS_MATERIAL_DEAL_IMPACTS = [
    "deal_blocker",
]


def calculate_materiality_thresholds(
    transaction_value: Optional[float],
    currency: str = "ZAR"
) -> Dict[str, Any]:
    """
    Calculate materiality thresholds based on transaction value.

    Args:
        transaction_value: Transaction value in the specified currency (or None)
        currency: Currency code (default: ZAR)

    Returns:
        Dict with threshold values and metadata:
        {
            "has_transaction_value": bool,
            "transaction_value": float | None,
            "currency": str,
            "thresholds": {
                "material": float,           # >= this is material
                "potentially_material": float,  # >= this is potentially material
                "likely_immaterial": float,  # < this is likely immaterial
            },
            "percentages": {
                "material": float,  # Percentage threshold (e.g., 0.05 = 5%)
                "potentially_material": float,
                "likely_immaterial": float,
            }
        }
    """
    if transaction_value and transaction_value > 0:
        # Percentage-based thresholds
        material_threshold = transaction_value * 0.05  # 5%
        potentially_material_threshold = transaction_value * 0.01  # 1%

        return {
            "has_transaction_value": True,
            "transaction_value": transaction_value,
            "currency": currency,
            "thresholds": {
                "material": material_threshold,
                "potentially_material": potentially_material_threshold,
                "likely_immaterial": potentially_material_threshold,  # Below 1%
            },
            "percentages": {
                "material": 0.05,
                "potentially_material": 0.01,
                "likely_immaterial": 0.01,
            },
            "description": (
                f"Material >= {_format_currency(material_threshold, currency)} (5% of transaction value), "
                f"Potentially Material >= {_format_currency(potentially_material_threshold, currency)} (1%), "
                f"Likely Immaterial < {_format_currency(potentially_material_threshold, currency)}"
            )
        }
    else:
        # Fixed thresholds when no transaction value available
        # Using South African market norms
        return {
            "has_transaction_value": False,
            "transaction_value": None,
            "currency": currency,
            "thresholds": {
                "material": 10_000_000,  # R10M
                "potentially_material": 1_000_000,  # R1M
                "likely_immaterial": 1_000_000,
            },
            "percentages": {
                "material": None,
                "potentially_material": None,
                "likely_immaterial": None,
            },
            "description": (
                "Material > R10,000,000, "
                "Potentially Material R1,000,000 - R10,000,000, "
                "Likely Immaterial < R1,000,000"
            )
        }


def classify_finding_materiality(
    finding: Dict[str, Any],
    thresholds: Dict[str, Any],
    override_categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Classify a single finding's materiality.

    Args:
        finding: Finding dict with 'financial_exposure', 'category', 'deal_impact'
        thresholds: Thresholds from calculate_materiality_thresholds()
        override_categories: Additional categories to treat as always material

    Returns:
        Materiality classification dict:
        {
            "classification": "material" | "potentially_material" | "likely_immaterial" | "unquantified",
            "ratio_to_deal": float | None,
            "threshold_applied": str,
            "qualitative_override": str | None
        }
    """
    override_cats = override_categories or []
    all_override_categories = ALWAYS_MATERIAL_CATEGORIES + override_cats

    # Check for qualitative overrides first
    category = finding.get("category", "").lower()
    deal_impact = finding.get("deal_impact", "").lower()

    # Check if category matches any always-material category
    for override_cat in all_override_categories:
        if override_cat.lower() in category:
            return {
                "classification": "material",
                "ratio_to_deal": None,
                "threshold_applied": "Qualitative override",
                "qualitative_override": f"Category '{category}' is always material"
            }

    # Check if deal impact is always material
    if deal_impact in ALWAYS_MATERIAL_DEAL_IMPACTS:
        return {
            "classification": "material",
            "ratio_to_deal": None,
            "threshold_applied": "Qualitative override",
            "qualitative_override": f"Deal impact '{deal_impact}' is always material"
        }

    # Get financial exposure amount
    financial_exposure = finding.get("financial_exposure", {})
    if isinstance(financial_exposure, dict):
        amount = financial_exposure.get("amount")
    else:
        amount = finding.get("exposure_amount") or finding.get("financial_exposure_amount")

    # If no amount, mark as unquantified
    if amount is None or amount == 0:
        return {
            "classification": "unquantified",
            "ratio_to_deal": None,
            "threshold_applied": "No financial amount available",
            "qualitative_override": None
        }

    # Calculate ratio if transaction value available
    transaction_value = thresholds.get("transaction_value")
    ratio = amount / transaction_value if transaction_value else None

    # Apply thresholds
    material_threshold = thresholds["thresholds"]["material"]
    potentially_material_threshold = thresholds["thresholds"]["potentially_material"]

    if amount >= material_threshold:
        classification = "material"
        threshold_desc = f"Amount {_format_currency(amount)} >= {_format_currency(material_threshold)} (material threshold)"
    elif amount >= potentially_material_threshold:
        classification = "potentially_material"
        threshold_desc = f"Amount {_format_currency(amount)} >= {_format_currency(potentially_material_threshold)} (potentially material threshold)"
    else:
        classification = "likely_immaterial"
        threshold_desc = f"Amount {_format_currency(amount)} < {_format_currency(potentially_material_threshold)} (below potentially material threshold)"

    return {
        "classification": classification,
        "ratio_to_deal": ratio,
        "threshold_applied": threshold_desc,
        "qualitative_override": None
    }


def apply_materiality_to_findings(
    findings: List[Dict[str, Any]],
    thresholds: Dict[str, Any],
    override_categories: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Apply materiality classification to all findings.

    Args:
        findings: List of finding dicts
        thresholds: Thresholds from calculate_materiality_thresholds()
        override_categories: Additional categories to treat as always material

    Returns:
        Findings list with materiality fields added to each finding
    """
    enriched_findings = []

    for finding in findings:
        materiality = classify_finding_materiality(
            finding, thresholds, override_categories
        )

        # Add materiality fields to finding
        enriched_finding = {**finding}
        enriched_finding["materiality_classification"] = materiality["classification"]
        enriched_finding["materiality_ratio"] = materiality["ratio_to_deal"]
        enriched_finding["materiality_threshold"] = materiality["threshold_applied"]
        enriched_finding["materiality_qualitative_override"] = materiality["qualitative_override"]

        enriched_findings.append(enriched_finding)

    # Log summary
    classifications = {}
    for f in enriched_findings:
        cls = f.get("materiality_classification", "unknown")
        classifications[cls] = classifications.get(cls, 0) + 1

    logger.info(f"Materiality classification summary: {classifications}")

    return enriched_findings


def filter_findings_by_materiality(
    findings: List[Dict[str, Any]],
    min_classification: str = "potentially_material",
    include_unquantified: bool = True
) -> List[Dict[str, Any]]:
    """
    Filter findings to only include those at or above minimum materiality.

    Args:
        findings: List of findings with materiality_classification
        min_classification: Minimum classification to include
        include_unquantified: Whether to include unquantified findings

    Returns:
        Filtered list of findings
    """
    classification_order = ["likely_immaterial", "potentially_material", "material"]

    if min_classification not in classification_order:
        min_classification = "likely_immaterial"

    min_index = classification_order.index(min_classification)

    filtered = []
    for finding in findings:
        classification = finding.get("materiality_classification", "unquantified")

        if classification == "unquantified":
            if include_unquantified:
                filtered.append(finding)
        elif classification in classification_order:
            if classification_order.index(classification) >= min_index:
                filtered.append(finding)

    return filtered


def get_materiality_summary(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for materiality classifications.

    Args:
        findings: List of findings with materiality fields

    Returns:
        Summary dict with counts, totals, and breakdowns
    """
    summary = {
        "total_findings": len(findings),
        "by_classification": {
            "material": 0,
            "potentially_material": 0,
            "likely_immaterial": 0,
            "unquantified": 0,
        },
        "total_exposure_by_classification": {
            "material": 0,
            "potentially_material": 0,
            "likely_immaterial": 0,
            "unquantified": 0,
        },
        "qualitative_overrides": 0,
    }

    for finding in findings:
        classification = finding.get("materiality_classification", "unquantified")
        summary["by_classification"][classification] = (
            summary["by_classification"].get(classification, 0) + 1
        )

        # Sum exposure amounts
        financial_exposure = finding.get("financial_exposure", {})
        if isinstance(financial_exposure, dict):
            amount = financial_exposure.get("amount", 0) or 0
        else:
            amount = finding.get("exposure_amount", 0) or 0

        summary["total_exposure_by_classification"][classification] = (
            summary["total_exposure_by_classification"].get(classification, 0) + amount
        )

        if finding.get("materiality_qualitative_override"):
            summary["qualitative_overrides"] += 1

    return summary


def _format_currency(amount: float, currency: str = "ZAR") -> str:
    """Format amount as currency string."""
    if amount is None:
        return "N/A"

    if amount >= 1_000_000_000:
        return f"{currency} {amount / 1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"{currency} {amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"{currency} {amount / 1_000:.0f}K"
    else:
        return f"{currency} {amount:.0f}"
