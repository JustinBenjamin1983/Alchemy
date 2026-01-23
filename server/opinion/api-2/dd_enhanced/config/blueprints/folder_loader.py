"""
Folder Structure Loader for Blueprint-Based Organisation

Loads folder_structure from blueprint YAMLs and provides helper functions
for determining which folder a document should be assigned to.

Phase 2: Blueprint Folder Organisation
"""
from typing import Dict, Any, Optional, List
import yaml
import os
import logging

logger = logging.getLogger(__name__)

BLUEPRINT_DIR = os.path.dirname(__file__)

# Confidence threshold for routing to 99_Needs_Review
CONFIDENCE_THRESHOLD = 70.0


def get_default_folder_structure() -> Dict[str, Any]:
    """
    Default folder structure when no blueprint-specific one exists.
    All folders have 'medium' relevance by default.
    """
    return {
        "01_Corporate": {
            "relevance": "medium",
            "subcategories": ["Constitutional", "Governance", "Resolutions", "Shareholding"],
            "expected_documents": ["MOI", "Shareholders Agreement", "Board Resolution", "Share Certificate", "Company Registration"]
        },
        "02_Commercial": {
            "relevance": "medium",
            "subcategories": ["Supply Agreements", "Offtake", "Service Contracts", "JV Agreements"],
            "expected_documents": ["Supply Agreement", "Offtake Agreement", "Service Level Agreement", "Joint Venture Agreement"]
        },
        "03_Financial": {
            "relevance": "medium",
            "subcategories": ["Loan Agreements", "Security", "Guarantees", "Financial Statements"],
            "expected_documents": ["Loan Agreement", "Mortgage Bond", "Guarantee", "Financial Statement", "Audit Report"]
        },
        "04_Regulatory": {
            "relevance": "medium",
            "subcategories": ["Licenses", "Permits", "Environmental", "Compliance"],
            "expected_documents": ["License", "Permit", "Environmental Authorisation", "Compliance Certificate"]
        },
        "05_Employment": {
            "relevance": "medium",
            "subcategories": ["Executive Contracts", "Policies", "Union Agreements", "Benefit Plans"],
            "expected_documents": ["Employment Contract", "HR Policy", "Recognition Agreement", "Pension Fund Rules"]
        },
        "06_Property": {
            "relevance": "medium",
            "subcategories": ["Owned", "Leased", "Servitudes", "Surface Rights"],
            "expected_documents": ["Title Deed", "Lease Agreement", "Servitude Agreement", "Surface Right Agreement"]
        },
        "07_Insurance": {
            "relevance": "low",
            "subcategories": ["Policies", "Claims"],
            "expected_documents": ["Insurance Policy", "Certificate of Insurance", "Claims Record"]
        },
        "08_Litigation": {
            "relevance": "medium",
            "subcategories": ["Pending", "Threatened", "Settled"],
            "expected_documents": ["Summons", "Pleading", "Settlement Agreement", "Court Order", "Legal Opinion"]
        },
        "09_Tax": {
            "relevance": "medium",
            "subcategories": ["Returns", "Assessments", "Rulings", "Disputes"],
            "expected_documents": ["Tax Return", "Tax Assessment", "Tax Ruling", "Tax Clearance Certificate"]
        },
        "99_Needs_Review": {
            "relevance": "n/a",
            "subcategories": ["Unclassified", "Low Confidence", "Multiple Categories"],
            "expected_documents": []
        }
    }


def load_folder_structure(transaction_type: str) -> Dict[str, Any]:
    """
    Load folder_structure from blueprint YAML for given transaction type.

    Args:
        transaction_type: The transaction type code (e.g., 'mining_resources', 'ma_corporate')

    Returns:
        Dictionary of folder configurations with relevance and expected documents
    """
    # Map common variations to blueprint filenames
    type_mapping = {
        "mining": "mining_resources",
        "mining_resources": "mining_resources",
        "mining_acquisition": "mining_resources",  # Consolidated into mining_resources
        "m&a": "ma_corporate",
        "ma": "ma_corporate",
        "ma_corporate": "ma_corporate",
        "real_estate": "real_estate",
        "energy": "energy_power",
        "energy_power": "energy_power",
        "private_equity": "private_equity_vc",
        "private_equity_vc": "private_equity_vc",
        "financial_services": "financial_services",
        "banking": "banking_finance",
        "banking_finance": "banking_finance",
        "ip": "ip_technology",
        "ip_technology": "ip_technology",
        "infrastructure": "infrastructure_ppp",
        "infrastructure_ppp": "infrastructure_ppp",
        "bee": "bee_transformation",
        "bee_transformation": "bee_transformation",
        "restructuring": "restructuring_insolvency",
        "restructuring_insolvency": "restructuring_insolvency",
        "competition": "competition_regulatory",
        "competition_regulatory": "competition_regulatory",
        "employment": "employment_labor",
        "employment_labor": "employment_labor",
        "capital_markets": "capital_markets",
    }

    # Normalize transaction type
    normalized_type = transaction_type.lower().replace(" ", "_").replace("-", "_")
    blueprint_name = type_mapping.get(normalized_type, normalized_type)

    blueprint_file = os.path.join(BLUEPRINT_DIR, f"{blueprint_name}.yaml")

    if not os.path.exists(blueprint_file):
        logger.warning(f"Blueprint file not found: {blueprint_file}, using default folder structure")
        return get_default_folder_structure()

    try:
        with open(blueprint_file, 'r') as f:
            blueprint = yaml.safe_load(f)

        folder_structure = blueprint.get('folder_structure')
        if folder_structure:
            return folder_structure
        else:
            logger.info(f"No folder_structure in {blueprint_name}.yaml, using default")
            return get_default_folder_structure()

    except Exception as e:
        logger.error(f"Error loading blueprint {blueprint_file}: {e}")
        return get_default_folder_structure()


def get_folder_for_category(
    ai_category: str,
    ai_confidence: float,
    confidence_threshold: float = CONFIDENCE_THRESHOLD
) -> str:
    """
    Determine which folder a document should go to based on AI classification.

    Args:
        ai_category: The AI-assigned category (e.g., "01_Corporate", "Commercial")
        ai_confidence: Confidence score from 0-100
        confidence_threshold: Minimum confidence to use AI category (default 70.0)

    Returns:
        Folder category string (e.g., "01_Corporate") or "99_Needs_Review" if low confidence
    """
    # Route low confidence to Needs Review
    if ai_confidence is None or ai_confidence < confidence_threshold:
        return "99_Needs_Review"

    # If already in correct format (XX_Name), return as-is
    if ai_category and ai_category[:2].isdigit() and ai_category[2] == '_':
        return ai_category

    # Map unformatted categories to standard format
    CATEGORY_MAP = {
        "corporate": "01_Corporate",
        "commercial": "02_Commercial",
        "financial": "03_Financial",
        "regulatory": "04_Regulatory",
        "employment": "05_Employment",
        "property": "06_Property",
        "insurance": "07_Insurance",
        "litigation": "08_Litigation",
        "tax": "09_Tax",
        "needs_review": "99_Needs_Review",
        "unclassified": "99_Needs_Review",
    }

    if ai_category:
        normalized = ai_category.lower().replace(" ", "_")
        # Check for partial matches
        for key, value in CATEGORY_MAP.items():
            if key in normalized:
                return value

    return "99_Needs_Review"


def get_all_folder_categories() -> List[str]:
    """Return list of all standard folder categories in sort order."""
    return [
        "01_Corporate",
        "02_Commercial",
        "03_Financial",
        "04_Regulatory",
        "05_Employment",
        "06_Property",
        "07_Insurance",
        "08_Litigation",
        "09_Tax",
        "99_Needs_Review",
    ]


def extract_sort_order(folder_category: str) -> int:
    """
    Extract numeric sort order from folder category.

    Args:
        folder_category: e.g., "01_Corporate", "99_Needs_Review"

    Returns:
        Integer sort order (1, 2, 3... or 99 for Needs Review)
    """
    try:
        return int(folder_category.split('_')[0])
    except (ValueError, IndexError):
        return 99


def get_folder_display_name(folder_category: str) -> str:
    """
    Get human-readable display name for folder category.

    Args:
        folder_category: e.g., "01_Corporate"

    Returns:
        Display name: e.g., "Corporate"
    """
    if not folder_category:
        return "Unknown"

    parts = folder_category.split('_', 1)
    if len(parts) > 1:
        return parts[1].replace('_', ' ')
    return folder_category
