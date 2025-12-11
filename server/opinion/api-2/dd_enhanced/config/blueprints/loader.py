"""
Blueprint loader utility.
Loads and merges transaction-specific blueprints with base questions.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional

BLUEPRINTS_DIR = Path(__file__).parent


def load_blueprint(transaction_type: str) -> Dict:
    """
    Load a transaction-specific blueprint.

    Args:
        transaction_type: One of: mining_resources, ma_corporate, banking_finance,
                         real_estate, competition_regulatory, employment_labor,
                         ip_technology, bee_transformation, energy_power,
                         infrastructure_ppp

    Returns:
        Complete blueprint dict with base questions merged in
    """
    # Load base questions
    base_path = BLUEPRINTS_DIR / "_base_questions.yaml"
    base = {}
    if base_path.exists():
        with open(base_path) as f:
            base = yaml.safe_load(f) or {}

    # Load transaction-specific blueprint
    blueprint_path = BLUEPRINTS_DIR / f"{transaction_type}.yaml"
    if not blueprint_path.exists():
        raise ValueError(f"Unknown transaction type: {transaction_type}")

    with open(blueprint_path) as f:
        blueprint = yaml.safe_load(f)

    # Merge base questions into blueprint
    blueprint["base_questions"] = base.get("common_questions", {})
    blueprint["cross_document_validations"] = base.get("cross_document_validations", [])

    return blueprint


def list_available_blueprints() -> List[str]:
    """List all available blueprint types."""
    return [
        "mining_resources",
        "ma_corporate",
        "banking_finance",
        "real_estate",
        "competition_regulatory",
        "employment_labor",
        "ip_technology",
        "bee_transformation",
        "energy_power",
        "infrastructure_ppp"
    ]


def get_blueprint_summary(transaction_type: str) -> Dict:
    """Get a summary of a blueprint without loading full content."""
    try:
        blueprint = load_blueprint(transaction_type)
        return {
            "transaction_type": blueprint.get("transaction_type"),
            "code": blueprint.get("code"),
            "description": blueprint.get("description", "")[:100] + "...",
            "risk_categories": [c["name"] for c in blueprint.get("risk_categories", [])],
            "total_questions": sum(
                len(c.get("standard_questions", []))
                for c in blueprint.get("risk_categories", [])
            ),
            "deal_blockers": len(blueprint.get("deal_blockers", []))
        }
    except Exception as e:
        return {
            "transaction_type": transaction_type,
            "error": str(e)
        }


def get_questions_for_category(blueprint: Dict, category_name: str) -> List[Dict]:
    """Get all questions for a specific risk category."""
    for category in blueprint.get("risk_categories", []):
        if category.get("name") == category_name:
            return category.get("standard_questions", [])
    return []


def get_critical_questions(blueprint: Dict) -> List[Dict]:
    """Get all critical priority questions from a blueprint."""
    critical = []
    for category in blueprint.get("risk_categories", []):
        for question in category.get("standard_questions", []):
            if question.get("priority") == "critical":
                critical.append({
                    "category": category.get("name"),
                    **question
                })
    return critical


def get_deal_blockers(blueprint: Dict) -> List[Dict]:
    """Get all deal blocker definitions from a blueprint."""
    return blueprint.get("deal_blockers", [])


def get_cp_patterns(blueprint: Dict) -> List[Dict]:
    """Get conditions precedent patterns from a blueprint."""
    return blueprint.get("conditions_precedent_patterns", [])
