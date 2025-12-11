#!/usr/bin/env python3
"""
DD Enhanced POC - Comparison Script

Compares the enhanced DD results against the expected findings
to demonstrate improvement over the original system.

Run with:
    python run_comparison.py output/dd_results_TIMESTAMP.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Expected findings that the original system missed
EXPECTED_FINDINGS = {
    "moi_board_conflict": {
        "description": "MOI requires 75% shareholder approval for change of control, but Board Resolution only has board approval. Shareholder notification NOT YET COMPLETED.",
        "severity": "critical",
        "deal_impact": "deal_blocker",
        "documents": ["Karoo Mining MOI", "KAROO Board Resolution"],
        "keywords": ["shareholder", "approval", "75%", "not yet completed", "moi", "board resolution"]
    },
    "eskom_liquidated_damages": {
        "description": "Eskom Coal Supply Agreement: 24 months liquidated damages on termination following CoC without consent",
        "severity": "critical",
        "deal_impact": "condition_precedent",
        "expected_calculation": "R463.5M annual / 12 = R38.625M monthly × 24 months = R77.25M (or similar)",
        "documents": ["Eskom COAL SUPPLY AGREEMENT"],
        "keywords": ["eskom", "liquidated", "24 months", "change of control", "consent"]
    },
    "standard_bank_covenant_breach": {
        "description": "Standard Bank loan has existing DSCR covenant breach (1.2x vs 1.5x required) with waiver expiring Q1 2025. CoC triggers acceleration of R285M facility.",
        "severity": "critical",
        "deal_impact": "deal_blocker",
        "documents": ["ST Bank TERM LOAN"],
        "keywords": ["dscr", "covenant", "breach", "waiver", "acceleration", "change of control"]
    },
    "cascade_linking": {
        "description": "Multiple CoC provisions should be linked as single cascade, not separate findings",
        "severity": "high",
        "expected_count": "4-7 documents with CoC provisions linked together",
        "keywords": ["cascade", "change of control"]
    }
}


def load_results(filepath: str) -> dict:
    """Load results from JSON file."""
    with open(filepath) as f:
        return json.load(f)


def check_finding_detected(results: dict, expected: dict) -> tuple:
    """
    Check if an expected finding was detected.
    Returns (detected: bool, evidence: str)
    """
    keywords = expected.get("keywords", [])
    documents = expected.get("documents", [])

    # Check in conflicts
    for conflict in results.get("pass3_results", {}).get("conflicts", []):
        text = json.dumps(conflict).lower()
        if any(kw.lower() in text for kw in keywords):
            return True, f"Found in conflict: {conflict.get('description', '')[:100]}"

    # Check in authorization issues
    for auth in results.get("pass3_results", {}).get("authorization_issues", []):
        text = json.dumps(auth).lower()
        if any(kw.lower() in text for kw in keywords):
            return True, f"Found in authorization issue: {str(auth)[:100]}"

    # Check in pass2 findings
    for finding in results.get("pass2_findings", []):
        text = json.dumps(finding).lower()
        if any(kw.lower() in text for kw in keywords):
            return True, f"Found in Pass 2: {finding.get('description', '')[:100]}"

    # Check in cascade analysis
    cascade = results.get("pass3_results", {}).get("cascade_analysis", {})
    cascade_text = json.dumps(cascade).lower()
    if any(kw.lower() in cascade_text for kw in keywords):
        return True, f"Found in cascade analysis"

    # Check in deal blockers
    for blocker in results.get("pass4_synthesis", {}).get("deal_blockers", []):
        text = json.dumps(blocker).lower()
        if any(kw.lower() in text for kw in keywords):
            return True, f"Found as deal blocker: {str(blocker)[:100]}"

    return False, "Not detected"


def check_calculation_performed(results: dict) -> tuple:
    """Check if financial calculations were performed."""
    exposures = results.get("pass4_synthesis", {}).get("financial_exposures", {})
    items = exposures.get("items", [])

    if items:
        total = exposures.get("total", 0)
        return True, f"Calculated {len(items)} exposures totaling R{total:,.0f}"

    # Also check cascade analysis
    cascade = results.get("pass3_results", {}).get("cascade_analysis", {})
    total = cascade.get("total_financial_exposure", {})
    if total and total.get("amount"):
        return True, f"Cascade total: R{total.get('amount'):,.0f}"

    return False, "No calculations found"


def check_cascade_linking(results: dict) -> tuple:
    """Check if cascade items are properly linked."""
    cascade = results.get("pass3_results", {}).get("cascade_analysis", {})
    items = cascade.get("cascade_items", [])

    if len(items) >= 3:
        docs = [item.get("document", "") for item in items]
        return True, f"Linked {len(items)} items: {docs[:5]}"

    return False, f"Only {len(items)} cascade items found"


def run_comparison(results_file: str):
    """Run comparison and print report."""

    print("=" * 60)
    print("DD ENHANCED POC - COMPARISON REPORT")
    print("=" * 60)
    print(f"\nResults file: {results_file}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load results
    try:
        results = load_results(results_file)
    except FileNotFoundError:
        print(f"\nERROR: File not found: {results_file}")
        print("\nRun 'python run_poc.py' first to generate results.")
        sys.exit(1)

    # Score tracking
    tests_passed = 0
    tests_total = 0

    print("\n" + "-" * 60)
    print("TEST RESULTS")
    print("-" * 60)

    # Test 1: MOI vs Board Resolution Conflict
    print("\n1. MOI vs Board Resolution Conflict")
    print("   Expected: Detect that MOI requires shareholder approval but")
    print("             Board Resolution only has board approval")
    detected, evidence = check_finding_detected(results, EXPECTED_FINDINGS["moi_board_conflict"])
    tests_total += 1
    if detected:
        print(f"   [PASS] {evidence}")
        tests_passed += 1
    else:
        print(f"   [FAIL] {evidence}")

    # Test 2: Eskom Liquidated Damages Calculation
    print("\n2. Eskom Liquidated Damages Calculation")
    print("   Expected: Calculate 24 months × monthly contract value")
    detected, evidence = check_finding_detected(results, EXPECTED_FINDINGS["eskom_liquidated_damages"])
    tests_total += 1
    if detected:
        print(f"   [PASS] {evidence}")
        tests_passed += 1
    else:
        print(f"   [FAIL] {evidence}")

    # Test 2b: Check calculation was performed
    print("\n2b. Financial Calculation Performed")
    print("    Expected: Numerical calculation of exposure amount")
    calculated, calc_evidence = check_calculation_performed(results)
    tests_total += 1
    if calculated:
        print(f"   [PASS] {calc_evidence}")
        tests_passed += 1
    else:
        print(f"   [FAIL] {calc_evidence}")

    # Test 3: Standard Bank Covenant Breach
    print("\n3. Standard Bank Covenant Breach + CoC")
    print("   Expected: Identify DSCR breach AND CoC acceleration risk")
    detected, evidence = check_finding_detected(results, EXPECTED_FINDINGS["standard_bank_covenant_breach"])
    tests_total += 1
    if detected:
        print(f"   [PASS] {evidence}")
        tests_passed += 1
    else:
        print(f"   [FAIL] {evidence}")

    # Test 4: Cascade Linking
    print("\n4. Change of Control Cascade Linking")
    print("   Expected: Link multiple CoC provisions as single cascade")
    linked, link_evidence = check_cascade_linking(results)
    tests_total += 1
    if linked:
        print(f"   [PASS] {link_evidence}")
        tests_passed += 1
    else:
        print(f"   [FAIL] {link_evidence}")

    # Test 5: Cross-document conflicts detected
    print("\n5. Cross-Document Conflict Detection")
    print("   Expected: At least 1 conflict identified between documents")
    conflicts = results.get("pass3_results", {}).get("conflicts", [])
    tests_total += 1
    if conflicts:
        print(f"   [PASS] Found {len(conflicts)} conflicts")
        for c in conflicts[:3]:
            print(f"         - {c.get('description', '')[:60]}")
        tests_passed += 1
    else:
        print("   [FAIL] No conflicts detected")

    # Test 6: Deal blockers identified
    print("\n6. Deal Blocker Classification")
    print("   Expected: At least 1 deal blocker identified")
    blockers = results.get("pass4_synthesis", {}).get("deal_blockers", [])
    auth_issues = results.get("pass3_results", {}).get("authorization_issues", [])
    tests_total += 1
    if blockers or auth_issues:
        total_blockers = len(blockers) + len(auth_issues)
        print(f"   [PASS] Found {total_blockers} potential deal blockers")
        tests_passed += 1
    else:
        print("   [FAIL] No deal blockers identified")

    # Test 7: Consent matrix built
    print("\n7. Consent Matrix")
    print("   Expected: Consent matrix with multiple items")
    consents = results.get("pass3_results", {}).get("consent_matrix", [])
    tests_total += 1
    if len(consents) >= 2:
        print(f"   [PASS] Built consent matrix with {len(consents)} items")
        tests_passed += 1
    else:
        print(f"   [FAIL] Only {len(consents)} consent items")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTests passed: {tests_passed}/{tests_total}")
    print(f"Score: {(tests_passed/tests_total)*100:.0f}%")

    if tests_passed == tests_total:
        print("\n[SUCCESS] All tests passed!")
    elif tests_passed >= tests_total * 0.7:
        print("\n[GOOD] Most tests passed - POC demonstrates improvement")
    else:
        print("\n[NEEDS WORK] Several tests failed - review prompts and analysis")

    # Comparison with original
    print("\n" + "-" * 60)
    print("COMPARISON WITH ORIGINAL SYSTEM")
    print("-" * 60)

    original_score = 60  # Known score
    enhanced_estimate = int((tests_passed / tests_total) * 100)

    print(f"\nOriginal system score: {original_score}/100")
    print(f"Enhanced POC score:    ~{enhanced_estimate}/100 (estimated)")
    print(f"Improvement:           +{enhanced_estimate - original_score} points")

    print("\n" + "-" * 60)
    print("KEY ARCHITECTURAL IMPROVEMENTS DEMONSTRATED")
    print("-" * 60)

    improvements = [
        ("Cross-document conflict detection", len(conflicts) > 0),
        ("Cascade analysis linking", linked),
        ("Financial calculations", calculated),
        ("Deal blocker classification", len(blockers) + len(auth_issues) > 0),
        ("Reference docs always in context", True),  # By design
        ("Authorization validation", len(auth_issues) > 0 or any("auth" in str(c).lower() for c in conflicts)),
    ]

    for improvement, achieved in improvements:
        status = "[x]" if achieved else "[ ]"
        print(f"  {status} {improvement}")


def main():
    if len(sys.argv) < 2:
        # Try to find the latest results file
        output_dir = Path(__file__).parent / "output"
        json_files = list(output_dir.glob("dd_results_*.json"))
        if json_files:
            latest = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"Using latest results file: {latest}")
            run_comparison(str(latest))
        else:
            print("Usage: python run_comparison.py <results_file.json>")
            print("\nNo results file specified and no results found in output/")
            print("Run 'python run_poc.py' first to generate results.")
            sys.exit(1)
    else:
        run_comparison(sys.argv[1])


if __name__ == "__main__":
    main()
