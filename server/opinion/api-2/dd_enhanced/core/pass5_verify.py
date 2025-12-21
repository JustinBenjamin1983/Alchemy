"""
Pass 5: Opus Verification
=========================
Final verification pass using Claude Opus to:
1. Verify deal-blockers are truly blocking
2. Validate financial calculations and interpretations
3. Challenge assumptions and flag potential issues
4. Identify inconsistencies across findings
5. Provide confidence scores and recommendations

This pass runs AFTER Pass 4 synthesis and provides a quality assurance layer
before the final report is generated.
"""

import logging
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# Ensure dd_enhanced is in path for imports
_dd_enhanced_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dd_enhanced_path not in sys.path:
    sys.path.insert(0, _dd_enhanced_path)

from .claude_client import ClaudeClient
from prompts.verification import (
    VERIFICATION_SYSTEM_PROMPT,
    build_deal_blocker_verification_prompt,
    build_calculation_verification_prompt,
    build_consistency_verification_prompt,
    build_final_verification_summary_prompt,
)

logger = logging.getLogger(__name__)


class VerificationResult:
    """Container for Pass 5 verification results."""

    def __init__(self):
        self.blocker_verification: Dict = {}
        self.calculation_verification: Dict = {}
        self.consistency_verification: Dict = {}
        self.final_summary: Dict = {}
        self.verification_passed: bool = False
        self.overall_confidence: float = 0.0
        self.critical_issues: List[Dict] = []
        self.warnings: List[str] = []
        self.error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "verification_passed": self.verification_passed,
            "overall_confidence": self.overall_confidence,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "blocker_verification": self.blocker_verification,
            "calculation_verification": self.calculation_verification,
            "consistency_verification": self.consistency_verification,
            "final_summary": self.final_summary,
            "error": self.error,
        }


def run_pass5_verification(
    pass4_results: Dict,
    pass3_results: Dict,
    pass2_findings: List[Dict],
    pass1_results: Dict,
    calculation_aggregates: Optional[Dict],
    transaction_context: str,
    client: ClaudeClient,
    verbose: bool = True,
    checkpoint_callback: Optional[callable] = None,
) -> VerificationResult:
    """
    Run Pass 5: Opus Verification of deal-blockers, calculations, and consistency.

    This pass uses Claude Opus to provide a final quality check on the analysis.

    Args:
        pass4_results: Results from Pass 4 synthesis
        pass3_results: Results from Pass 3 cross-document analysis
        pass2_findings: Findings from Pass 2 per-document analysis
        pass1_results: Extractions from Pass 1
        calculation_aggregates: Aggregate calculation results from Pass 3.5
        transaction_context: Transaction context string
        client: Claude API client
        verbose: Print progress
        checkpoint_callback: Optional callback for progress updates

    Returns:
        VerificationResult with all verification findings
    """
    result = VerificationResult()

    try:
        # ===== Step 1: Verify Deal Blockers =====
        if verbose:
            logger.info("[Pass 5] Step 1: Verifying deal blockers with Opus...")
        if checkpoint_callback:
            checkpoint_callback("pass5_verify_blockers")

        deal_blockers = pass4_results.get("deal_blockers", [])
        executive_summary = pass4_results.get("executive_summary", "")

        if deal_blockers:
            blocker_prompt = build_deal_blocker_verification_prompt(
                deal_blockers=deal_blockers,
                transaction_context=transaction_context,
                executive_summary=executive_summary
            )

            blocker_response = client.complete_verification(
                prompt=blocker_prompt,
                system=VERIFICATION_SYSTEM_PROMPT,
                max_tokens=4096,
                temperature=0.1
            )

            if "error" not in blocker_response:
                result.blocker_verification = blocker_response
                if verbose:
                    blocker_count = len(blocker_response.get("blocker_assessments", []))
                    missing_count = len(blocker_response.get("missing_blockers", []))
                    logger.info(f"[Pass 5] Verified {blocker_count} blockers, identified {missing_count} potentially missing")
            else:
                logger.warning(f"[Pass 5] Blocker verification failed: {blocker_response.get('error')}")
        else:
            if verbose:
                logger.info("[Pass 5] No deal blockers to verify")
            result.blocker_verification = {
                "blocker_assessments": [],
                "missing_blockers": [],
                "overall_deal_risk": "low",
                "recommendation": "No blockers identified - verify this is correct"
            }

        # ===== Step 2: Verify Calculations =====
        if verbose:
            logger.info("[Pass 5] Step 2: Verifying financial calculations with Opus...")
        if checkpoint_callback:
            checkpoint_callback("pass5_verify_calculations")

        # Gather calculation data
        calculations = []
        if calculation_aggregates:
            for cat, cat_data in calculation_aggregates.get("by_category", {}).items():
                for item in cat_data.get("items", []):
                    calculations.append({
                        "formula_id": item.get("formula_id"),
                        "description": f"{cat} exposure",
                        "amount": item.get("amount"),
                        "currency": "ZAR",
                        "confidence": item.get("confidence"),
                    })

        # Also check findings with calculated exposures
        findings_list = pass2_findings if isinstance(pass2_findings, list) else pass2_findings.get("findings", [])
        for finding in findings_list:
            calc_exp = finding.get("calculated_exposure")
            if calc_exp and calc_exp.get("result_value"):
                calculations.append({
                    "formula_id": calc_exp.get("formula_id"),
                    "description": finding.get("description", "")[:100],
                    "amount": calc_exp.get("result_value"),
                    "currency": calc_exp.get("result_currency", "ZAR"),
                    "inputs": calc_exp.get("inputs", {}),
                    "steps": calc_exp.get("calculation_steps", []),
                    "source_document": finding.get("source_document"),
                    "clause_reference": finding.get("clause_reference"),
                })

        financial_figures = pass1_results.get("financial_figures", [])

        # Get transaction value
        transaction_value = None
        if calculation_aggregates and calculation_aggregates.get("transaction_ratio"):
            # Back-calculate from ratio if available
            ratio = calculation_aggregates["transaction_ratio"].get("value", 0)
            total_exposure = calculation_aggregates.get("total_exposure", 0)
            if ratio > 0:
                transaction_value = total_exposure / ratio

        if calculations or financial_figures:
            calc_prompt = build_calculation_verification_prompt(
                calculations=calculations,
                financial_figures=financial_figures,
                transaction_value=transaction_value
            )

            calc_response = client.complete_verification(
                prompt=calc_prompt,
                system=VERIFICATION_SYSTEM_PROMPT,
                max_tokens=4096,
                temperature=0.1
            )

            if "error" not in calc_response:
                result.calculation_verification = calc_response
                if verbose:
                    verified_count = len(calc_response.get("calculation_verifications", []))
                    errors = sum(1 for c in calc_response.get("calculation_verifications", [])
                                if not c.get("is_correct", True))
                    logger.info(f"[Pass 5] Verified {verified_count} calculations, found {errors} errors")
            else:
                logger.warning(f"[Pass 5] Calculation verification failed: {calc_response.get('error')}")
        else:
            if verbose:
                logger.info("[Pass 5] No calculations to verify")
            result.calculation_verification = {
                "calculation_verifications": [],
                "missing_calculations": [],
                "total_verified_exposure": {"amount": 0, "currency": "ZAR", "confidence": 0.5}
            }

        # ===== Step 3: Verify Consistency =====
        if verbose:
            logger.info("[Pass 5] Step 3: Verifying consistency across findings with Opus...")
        if checkpoint_callback:
            checkpoint_callback("pass5_verify_consistency")

        cross_doc_findings = pass3_results.get("cross_doc_findings", []) or pass3_results.get("all_cross_doc_findings", [])
        conflicts = pass3_results.get("conflicts", [])

        consistency_prompt = build_consistency_verification_prompt(
            findings=findings_list,
            cross_doc_findings=cross_doc_findings,
            conflicts=conflicts
        )

        consistency_response = client.complete_verification(
            prompt=consistency_prompt,
            system=VERIFICATION_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.1
        )

        if "error" not in consistency_response:
            result.consistency_verification = consistency_response
            if verbose:
                issues = len(consistency_response.get("consistency_issues", []))
                score = consistency_response.get("overall_consistency_score", 0)
                logger.info(f"[Pass 5] Found {issues} consistency issues, score: {score:.0%}")
        else:
            logger.warning(f"[Pass 5] Consistency verification failed: {consistency_response.get('error')}")

        # ===== Step 4: Generate Final Summary =====
        if verbose:
            logger.info("[Pass 5] Step 4: Generating final verification summary with Opus...")
        if checkpoint_callback:
            checkpoint_callback("pass5_final_summary")

        summary_prompt = build_final_verification_summary_prompt(
            blocker_verification=result.blocker_verification,
            calculation_verification=result.calculation_verification,
            consistency_verification=result.consistency_verification,
            transaction_context=transaction_context
        )

        summary_response = client.complete_verification(
            prompt=summary_prompt,
            system=VERIFICATION_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.1
        )

        if "error" not in summary_response:
            result.final_summary = summary_response
            result.verification_passed = summary_response.get("verification_passed", False)
            result.overall_confidence = summary_response.get("overall_confidence", 0.0)
            result.critical_issues = summary_response.get("critical_issues", [])
            result.warnings = summary_response.get("warnings", [])

            if verbose:
                status = "PASSED" if result.verification_passed else "FAILED"
                logger.info(f"[Pass 5] Verification {status} with {result.overall_confidence:.0%} confidence")
                logger.info(f"[Pass 5] Critical issues: {len(result.critical_issues)}, Warnings: {len(result.warnings)}")
        else:
            logger.warning(f"[Pass 5] Final summary generation failed: {summary_response.get('error')}")
            # Still try to compile a result from partial data
            result.verification_passed = False
            result.overall_confidence = 0.5
            result.critical_issues = [{"issue": "Verification incomplete", "category": "system", "action_required": "Manual review needed"}]

        # Add metadata
        result.final_summary["verification_metadata"] = {
            "verification_date": datetime.utcnow().isoformat(),
            "areas_verified": ["deal_blockers", "calculations", "consistency"],
            "documents_reviewed": len(set(f.get("source_document", "") for f in findings_list)),
            "findings_reviewed": len(findings_list),
            "deal_blockers_reviewed": len(deal_blockers),
            "calculations_reviewed": len(calculations),
        }

        if verbose:
            logger.info("[Pass 5] Verification complete")

        return result

    except Exception as e:
        logger.exception(f"[Pass 5] Verification failed with error: {e}")
        result.error = str(e)
        result.verification_passed = False
        result.overall_confidence = 0.0
        result.critical_issues = [{
            "issue": f"Verification failed: {str(e)}",
            "category": "system",
            "action_required": "Manual review required"
        }]
        return result


def apply_verification_adjustments(
    pass4_results: Dict,
    verification_result: VerificationResult
) -> Dict:
    """
    Apply verification adjustments to Pass 4 results.

    Updates deal blocker classifications, adds verification warnings,
    and enriches the synthesis with verification insights.

    Args:
        pass4_results: Original Pass 4 results
        verification_result: Results from Pass 5 verification

    Returns:
        Enriched Pass 4 results with verification data
    """
    enriched = pass4_results.copy()

    # Add verification summary to results
    enriched["verification"] = {
        "passed": verification_result.verification_passed,
        "confidence": verification_result.overall_confidence,
        "critical_issues": verification_result.critical_issues,
        "warnings": verification_result.warnings,
    }

    # Adjust deal blockers based on verification
    if verification_result.blocker_verification.get("blocker_assessments"):
        adjusted_blockers = []
        for i, blocker in enumerate(enriched.get("deal_blockers", [])):
            # Find matching verification assessment
            for assessment in verification_result.blocker_verification["blocker_assessments"]:
                if assessment.get("blocker_index") == i + 1:
                    # Add verification data to blocker
                    blocker["verified"] = True
                    blocker["verified_classification"] = assessment.get("recommended_classification")
                    blocker["verification_reasoning"] = assessment.get("reasoning")
                    blocker["is_truly_blocking"] = assessment.get("is_truly_blocking", True)
                    blocker["severity_assessment"] = assessment.get("severity_assessment")
                    break
            adjusted_blockers.append(blocker)

        enriched["deal_blockers"] = adjusted_blockers

        # Add missing blockers identified by verification
        missing_blockers = verification_result.blocker_verification.get("missing_blockers", [])
        if missing_blockers:
            enriched["potential_missing_blockers"] = missing_blockers

    # Add calculation verification data
    if verification_result.calculation_verification.get("calculation_verifications"):
        enriched["verified_calculations"] = verification_result.calculation_verification["calculation_verifications"]
        enriched["verified_total_exposure"] = verification_result.calculation_verification.get("total_verified_exposure", {})

        # Flag any calculation errors
        calc_errors = [c for c in verification_result.calculation_verification["calculation_verifications"]
                      if not c.get("is_correct", True)]
        if calc_errors:
            enriched["calculation_errors"] = calc_errors

    # Add consistency issues
    if verification_result.consistency_verification.get("consistency_issues"):
        enriched["consistency_issues"] = verification_result.consistency_verification["consistency_issues"]

    # Add final recommendation from verification
    if verification_result.final_summary.get("final_recommendation"):
        enriched["verified_recommendation"] = verification_result.final_summary["final_recommendation"]

    return enriched
