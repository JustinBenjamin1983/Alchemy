"""
DD Enhanced Blueprints Library

A comprehensive library of Due Diligence blueprints for all major transaction types.
These blueprints encode institutional knowledge about what to look for in each type of deal.

Available blueprints:
    - mining_resources: Mining & Resources acquisitions
    - ma_corporate: General M&A / Corporate
    - banking_finance: Banking & Finance facilities
    - real_estate: Property transactions
    - competition_regulatory: Competition & Regulatory
    - employment_labor: Employment & Labor
    - ip_technology: IP & Technology
    - bee_transformation: BEE & Transformation
    - energy_power: Energy & Power (IPP, PPA)
    - infrastructure_ppp: Infrastructure & PPP

Usage:
    from dd_enhanced.config.blueprints import load_blueprint, list_available_blueprints

    # Load a specific blueprint
    blueprint = load_blueprint("mining_resources")

    # List all available blueprints
    blueprints = list_available_blueprints()

    # Get summary of a blueprint
    summary = get_blueprint_summary("ma_corporate")
"""

from .loader import (
    load_blueprint,
    list_available_blueprints,
    get_blueprint_summary,
    get_questions_for_category,
    get_critical_questions,
    get_deal_blockers,
    get_cp_patterns,
)

__all__ = [
    "load_blueprint",
    "list_available_blueprints",
    "get_blueprint_summary",
    "get_questions_for_category",
    "get_critical_questions",
    "get_deal_blockers",
    "get_cp_patterns",
]
