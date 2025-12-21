"""
Pass Calculations Orchestrator
==============================
Integrates the deterministic calculation engine with the DD pipeline.

Called at two points:
- After Pass 2: Process single-document calculations (Pass 2.5)
- After Pass 3: Process cross-document aggregate calculations (Pass 3.5)

Architecture:
    AI extracts → Python calculates → AI validates
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from .calculation_engine import (
    CalculationEngine,
    CalculationResult,
    CalculationStatus,
    ValidationSeverity,
)

logger = logging.getLogger(__name__)


# Formula pattern mapping - maps common finding patterns to formula IDs
FORMULA_PATTERN_MAP = {
    # Penalty patterns
    "liquidated_damages": "PEN_001",
    "daily_penalty": "PEN_002",
    "double_damages": "PEN_003",
    "treble_damages": "PEN_003",
    "percentage_penalty": "PEN_004",
    "capped_penalty": "PEN_005",

    # Employment patterns
    "severance": "EMP_001",
    "notice_period": "EMP_001",
    "total_remuneration": "EMP_002",
    "change_of_control": "EMP_004",
    "coc_severance": "EMP_004",
    "golden_parachute": "EMP_004",
    "lti_acceleration": "EMP_005",
    "phantom_shares": "EMP_005",

    # Lease patterns
    "remaining_lease": "LSE_001",
    "lease_obligation": "LSE_001",
    "royalty": "LSE_003",
    "production_royalty": "LSE_003",

    # Environmental patterns
    "rehabilitation": "ENV_001",
    "closure_cost": "ENV_001",
    "provision_shortfall": "ENV_002",
    "environmental_guarantee": "ENV_004",

    # Debt patterns
    "prepayment_penalty": "DBT_001",
    "make_whole": "DBT_001",
    "accrued_interest": "DBT_002",
    "default_interest": "DBT_002",

    # Transaction patterns
    "break_fee": "TXN_001",
    "termination_fee": "TXN_001",
    "escrow": "TXN_005",
    "holdback": "TXN_005",

    # Regulatory patterns (NEW)
    "bee_dilution": "REG_001",
    "bee_shareholding": "REG_001",
    "bee_compliance": "REG_001",
    "equity_dilution": "REG_001",
    "shareholding_dilution": "REG_001",
    "covenant_compliance": "REG_002",
    "financial_covenant": "REG_002",
    "interest_cover": "REG_002",
    "debt_ebitda": "REG_002",
    "document_expiry": "REG_003",
    "certificate_expiry": "REG_003",
    "tax_clearance": "REG_003",
    "license_expiry": "REG_003",
}


class CalculationOrchestrator:
    """
    Orchestrates financial calculations between AI passes.

    Handles:
    - Converting AI findings to calculation extractions
    - Running deterministic calculations
    - Enriching findings with calculated values
    - Aggregating cross-document exposures
    """

    def __init__(self, transaction_value: Optional[float] = None):
        """
        Initialize the orchestrator.

        Args:
            transaction_value: Transaction value for validation (e.g., 850000000 for R850M)
        """
        config = {}
        if transaction_value:
            config["transaction_value"] = transaction_value

        self.engine = CalculationEngine(config=config)
        self.transaction_value = Decimal(str(transaction_value)) if transaction_value else None

        # Track calculations for cross-doc aggregation
        self._calculations: Dict[str, CalculationResult] = {}
        self._pending_dependencies: Dict[str, List[Dict]] = {}

    def process_pass2_findings(self, findings: List[Dict]) -> List[Dict]:
        """
        Process findings after Pass 2, enriching with calculations.

        Called after Pass 2 analysis to add calculated financial exposures
        to findings that have calculable amounts.

        Args:
            findings: List of finding dictionaries from Pass 2

        Returns:
            Enriched findings with calculated_exposure field added
        """
        enriched_findings = []

        for finding in findings:
            enriched = self._process_single_finding(finding)
            enriched_findings.append(enriched)

        return enriched_findings

    def _process_single_finding(self, finding: Dict) -> Dict:
        """Process a single finding for calculable exposure."""
        # Check if finding has calculable exposure data
        extraction_data = finding.get("financial_extraction")

        if not extraction_data:
            # Try to detect calculable exposure from finding content
            extraction_data = self._detect_calculable_exposure(finding)

        if not extraction_data or not extraction_data.get("has_calculable_exposure"):
            return finding

        # Convert to extraction format and calculate
        try:
            extraction = self._convert_to_extraction(finding, extraction_data)
            result = self.engine.calculate(extraction)

            # Store for potential cross-doc aggregation
            self._calculations[extraction["extraction_id"]] = result

            # Enrich finding with calculation result
            finding["calculated_exposure"] = self._result_to_dict(result)

            # Update financial_exposure field for report
            if result.result_value and result.status != CalculationStatus.ERROR:
                finding["financial_exposure"] = {
                    "amount": float(result.result_value),
                    "currency": result.result_currency,
                    "calculation": self._format_calculation_summary(result),
                    "formula_id": result.formula_id,
                    "confidence": result.confidence_score,
                    "validation_passed": result.validation_passed,
                }

                # Add warnings if any
                if result.warnings:
                    finding["financial_exposure"]["warnings"] = result.warnings

            logger.info(
                f"Calculated exposure for finding: {result.formula_id} = "
                f"{result.result_currency} {result.result_value:,.2f}"
            )

        except Exception as e:
            logger.warning(f"Failed to calculate exposure for finding: {e}")
            finding["calculation_error"] = str(e)

        return finding

    def _detect_calculable_exposure(self, finding: Dict) -> Optional[Dict]:
        """
        Attempt to detect calculable exposure from finding content.

        Looks for patterns in the finding that match known formula types.
        """
        # Get text content to analyze
        detail = finding.get("detail", "").lower()
        phrase = finding.get("phrase", "").lower()
        direct_answer = finding.get("direct_answer", "").lower()
        combined_text = f"{detail} {phrase} {direct_answer}"

        # Look for formula pattern matches
        matched_formula = None
        for pattern, formula_id in FORMULA_PATTERN_MAP.items():
            if pattern.replace("_", " ") in combined_text or pattern in combined_text:
                matched_formula = formula_id
                break

        if not matched_formula:
            return None

        # Try to extract variables from the text
        # This is a simplified extraction - the AI should ideally provide structured data
        variables = self._extract_variables_from_text(combined_text, matched_formula)

        if not variables:
            return None

        return {
            "has_calculable_exposure": True,
            "formula_pattern": matched_formula,
            "variables": variables,
            "confidence": 0.6,  # Lower confidence for auto-detected
        }

    def _extract_variables_from_text(self, text: str, formula_id: str) -> Optional[Dict]:
        """
        Extract variables from text for a given formula.

        This is a fallback when AI doesn't provide structured extraction.
        Returns None if required variables cannot be extracted.
        """
        import re

        # Common patterns for extracting amounts
        amount_pattern = r'R\s*([\d,]+(?:\.\d{2})?)\s*(?:million|m)?'
        months_pattern = r'(\d+)\s*months?'
        percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'

        # Get required variables for formula
        formula = self.engine.formula_registry.get(formula_id)
        if not formula:
            return None

        variables = {"primary": []}

        # Extract based on formula requirements
        for var_name in formula.required_variables:
            value = None
            unit = "ZAR"

            if var_name in ["monthly_salary", "base_salary", "base_monthly", "monthly_rent"]:
                matches = re.findall(amount_pattern, text, re.IGNORECASE)
                if matches:
                    value = float(matches[0].replace(",", ""))

            elif var_name in ["months", "period", "severance_months", "remaining_months"]:
                matches = re.findall(months_pattern, text, re.IGNORECASE)
                if matches:
                    value = int(matches[0])
                    unit = "months"

            elif var_name in ["percentage", "break_fee_percentage", "escrow_percentage", "penalty_rate"]:
                matches = re.findall(percentage_pattern, text)
                if matches:
                    value = float(matches[0])
                    unit = "percent"

            if value is not None:
                variables["primary"].append({
                    "name": var_name,
                    "value": value,
                    "unit": unit,
                    "source": "Auto-extracted from text",
                    "confidence": 0.5,
                })

        # Check if we got all required variables
        extracted_names = {v["name"] for v in variables["primary"]}
        required_names = set(formula.required_variables)

        if not required_names.issubset(extracted_names):
            return None

        return variables

    def _convert_to_extraction(self, finding: Dict, extraction_data: Dict) -> Dict:
        """Convert finding + extraction data to calculation engine format."""
        extraction_id = f"calc-{finding.get('id', uuid.uuid4())}"

        return {
            "extraction_id": extraction_id,
            "document_source": {
                "document_id": finding.get("document_id", "unknown"),
                "document_name": finding.get("document_name", "Unknown Document"),
                "section_reference": finding.get("clause_reference", finding.get("page_number", "")),
                "extracted_text": finding.get("phrase", finding.get("direct_answer", "")),
            },
            "formula_classification": {
                "formula_id": extraction_data.get("formula_pattern", "UNKNOWN"),
                "formula_category": self._get_category_from_formula(extraction_data.get("formula_pattern", "")),
                "confidence": extraction_data.get("confidence", 0.8),
            },
            "variables": extraction_data.get("variables", {"primary": []}),
            "currency": {
                "primary": extraction_data.get("currency", "ZAR"),
                "conversion_required": False,
            },
            "calculation_modifiers": extraction_data.get("modifiers", {
                "cap": {"exists": False},
                "floor": {"exists": False},
            }),
            "cross_document_dependencies": extraction_data.get("dependencies", []),
        }

    def _get_category_from_formula(self, formula_id: str) -> str:
        """Get category name from formula ID prefix."""
        prefix_map = {
            "PEN": "penalty",
            "EMP": "employment",
            "LSE": "lease",
            "DBT": "debt",
            "ENV": "environmental",
            "REG": "regulatory",
            "TXN": "transaction",
        }
        if formula_id and len(formula_id) >= 3:
            prefix = formula_id[:3]
            return prefix_map.get(prefix, "custom")
        return "custom"

    def _result_to_dict(self, result: CalculationResult) -> Dict:
        """Convert CalculationResult to dictionary."""
        return result.to_dict()

    def _format_calculation_summary(self, result: CalculationResult) -> str:
        """Format a brief calculation summary for the report."""
        if not result.calculation_steps:
            return "No calculation steps recorded"

        # Get key inputs from first step
        first_step = result.calculation_steps[0]

        # Get formula description
        formula_desc = result.metadata.get("formula_description", result.formula_id)

        # Build summary
        summary_parts = [f"Formula: {formula_desc}"]

        # Add key inputs
        if "=" in first_step.calculation:
            inputs = first_step.calculation
            summary_parts.append(f"Inputs: {inputs}")

        return " | ".join(summary_parts)

    def process_pass3_aggregates(
        self,
        clusters: List[Dict],
        cross_doc_findings: List[Dict]
    ) -> Dict[str, Any]:
        """
        Process cross-document aggregate calculations after Pass 3.

        Handles:
        - Resolving cross-document dependencies
        - Aggregating related exposures
        - Calculating totals by category

        Args:
            clusters: Clustered findings from Pass 3
            cross_doc_findings: Cross-document analysis findings

        Returns:
            Aggregate calculation results
        """
        aggregates = {
            "total_exposure": Decimal("0"),
            "currency": "ZAR",
            "by_category": {},
            "by_status": {
                "calculated": [],
                "pending_review": [],
                "errors": [],
            },
            "validation_summary": {
                "passed": 0,
                "warnings": 0,
                "errors": 0,
            },
            "transaction_ratio": None,
        }

        # Process all stored calculations
        for extraction_id, result in self._calculations.items():
            if result.result_value is None:
                aggregates["by_status"]["errors"].append({
                    "extraction_id": extraction_id,
                    "formula_id": result.formula_id,
                    "errors": result.errors,
                })
                aggregates["validation_summary"]["errors"] += 1
                continue

            category = result.metadata.get("formula_category", "other")

            # Add to category totals
            if category not in aggregates["by_category"]:
                aggregates["by_category"][category] = {
                    "total": Decimal("0"),
                    "count": 0,
                    "items": [],
                }

            aggregates["by_category"][category]["total"] += result.result_value
            aggregates["by_category"][category]["count"] += 1
            aggregates["by_category"][category]["items"].append({
                "extraction_id": extraction_id,
                "formula_id": result.formula_id,
                "amount": float(result.result_value),
                "confidence": result.confidence_score,
            })

            # Add to overall total
            aggregates["total_exposure"] += result.result_value

            # Track validation status
            if result.validation_passed:
                aggregates["validation_summary"]["passed"] += 1
                aggregates["by_status"]["calculated"].append({
                    "extraction_id": extraction_id,
                    "formula_id": result.formula_id,
                    "amount": float(result.result_value),
                })
            else:
                aggregates["validation_summary"]["warnings"] += 1
                aggregates["by_status"]["pending_review"].append({
                    "extraction_id": extraction_id,
                    "formula_id": result.formula_id,
                    "amount": float(result.result_value),
                    "warnings": result.warnings,
                })

        # Calculate transaction ratio
        if self.transaction_value and aggregates["total_exposure"]:
            ratio = aggregates["total_exposure"] / self.transaction_value
            aggregates["transaction_ratio"] = {
                "value": float(ratio),
                "percentage": f"{float(ratio) * 100:.1f}%",
                "exceeds_transaction": ratio > 1,
            }

        # Convert Decimals to floats for JSON serialization
        aggregates["total_exposure"] = float(aggregates["total_exposure"])
        for cat_data in aggregates["by_category"].values():
            cat_data["total"] = float(cat_data["total"])

        return aggregates

    def get_calculation_summary(self) -> Dict[str, Any]:
        """Get a summary of all calculations performed."""
        successful = []
        failed = []

        for extraction_id, result in self._calculations.items():
            item = {
                "extraction_id": extraction_id,
                "formula_id": result.formula_id,
                "status": result.status.value,
            }

            if result.result_value is not None:
                item["amount"] = float(result.result_value)
                item["currency"] = result.result_currency
                successful.append(item)
            else:
                item["errors"] = result.errors
                failed.append(item)

        return {
            "total_calculations": len(self._calculations),
            "successful": len(successful),
            "failed": len(failed),
            "calculations": successful,
            "errors": failed,
        }

    def clear(self):
        """Clear stored calculations (call between DD runs)."""
        self._calculations.clear()
        self._pending_dependencies.clear()


def format_exposure_for_report(
    result: CalculationResult,
    document_name: str = "",
    clause_ref: str = "",
    condition: str = "",
) -> str:
    """
    Format a calculation result for the Word report.

    Returns compact format:
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║ CALCULATED EXPOSURE: [Description]                                     ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║ RESULT:    R 927,000,000    (Confidence: HIGH)    ⚠️ Warning          ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║ FORMULA:   [Formula description]                                      ║
    ║ INPUTS:    [Key input values]                                         ║
    ║ SOURCE:    [Document and clause reference]                            ║
    ║ CONDITION: [Trigger condition if any]                                 ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """
    if not result.result_value:
        return ""

    formula_desc = result.metadata.get("formula_description", result.formula_id)

    # Get confidence level
    if result.confidence_score >= 0.9:
        confidence = "HIGH"
    elif result.confidence_score >= 0.7:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Build warning string
    warning_str = ""
    if result.warnings:
        warning_str = f"  ⚠️ {result.warnings[0][:30]}"

    # Get inputs from first step
    inputs_str = ""
    if result.calculation_steps and len(result.calculation_steps) > 0:
        first_step = result.calculation_steps[0]
        if "=" in first_step.calculation:
            inputs_str = first_step.calculation.split("=")[1].strip() if "=" in first_step.calculation else first_step.calculation

    # Build source string
    source_parts = []
    if document_name:
        source_parts.append(document_name)
    if clause_ref:
        source_parts.append(clause_ref)
    source_str = " - ".join(source_parts) if source_parts else "See document"

    # Format the output
    lines = [
        f"CALCULATED EXPOSURE: {formula_desc}",
        f"RESULT: {result.result_currency} {result.result_value:,.2f}  (Confidence: {confidence}){warning_str}",
        f"FORMULA: {formula_desc} ({result.formula_id})",
    ]

    if inputs_str:
        lines.append(f"INPUTS: {inputs_str}")

    lines.append(f"SOURCE: {source_str}")

    if condition:
        lines.append(f"CONDITION: {condition}")

    return "\n".join(lines)
