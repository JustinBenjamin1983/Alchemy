#!/usr/bin/env python3
"""
DD Enhanced POC - Main Entry Point

Demonstrates improved multi-pass DD architecture.

Run with:
    cd /Users/jbenjamin/Web-Dev-Projects/Alchemy/server/opinion/api-2/dd_enhanced
    python run_poc.py

Requirements:
    pip install anthropic python-docx pyyaml rich python-dotenv
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Load .env file if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")
except ImportError:
    # dotenv not installed, will rely on environment variables
    pass

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for better output formatting: pip install rich")

from dd_enhanced.core.document_loader import load_documents, get_reference_documents
from dd_enhanced.core.claude_client import ClaudeClient
from dd_enhanced.core.pass1_extract import run_pass1_extraction
from dd_enhanced.core.pass2_analyze import run_pass2_analysis
from dd_enhanced.core.pass3_crossdoc import run_pass3_crossdoc_synthesis, get_cascade_summary
from dd_enhanced.core.pass4_synthesize import run_pass4_synthesis, format_executive_summary
from dd_enhanced.core.pass_calculations import CalculationOrchestrator
from dd_enhanced.core.pass5_verify import run_pass5_verification, apply_verification_adjustments
from dd_enhanced.config import load_blueprint


def print_header(text: str):
    """Print a formatted header."""
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        console.print(f"[bold blue]{text}[/bold blue]")
        console.print(f"[bold blue]{'='*60}[/bold blue]")
    else:
        print(f"\n{'='*60}")
        print(text)
        print('='*60)


def print_section(text: str):
    """Print a section header."""
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"\n[bold cyan]{text}[/bold cyan]")
    else:
        print(f"\n{text}")


def print_success(text: str):
    """Print success message."""
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"[green]  {text}[/green]")
    else:
        print(f"    {text}")


def print_warning(text: str):
    """Print warning message."""
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"[yellow]  {text}[/yellow]")
    else:
        print(f"  WARNING: {text}")


def print_error(text: str):
    """Print error message."""
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"[red]  {text}[/red]")
    else:
        print(f"  ERROR: {text}")


def main():
    """Run the enhanced DD POC."""

    print_header("KAROO MINING DD - ENHANCED POC")
    print("Multi-Pass Architecture Demonstration")
    print("=" * 60)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print_error("ANTHROPIC_API_KEY environment variable not set")
        print("\nSet it with: export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)

    # Paths
    base_dir = Path(__file__).parent
    # Navigate from dd_enhanced -> api-2 -> opinion -> server -> Alchemy -> test_documents
    doc_dir = base_dir.parent.parent.parent.parent / "test_documents" / "karoo"
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)

    print(f"\nDocument directory: {doc_dir}")
    print(f"Output directory: {output_dir}")

    # Check documents exist
    if not doc_dir.exists():
        print_error(f"Document directory not found: {doc_dir}")
        sys.exit(1)

    # Initialize
    print("\nInitializing...")
    client = ClaudeClient()
    print_success("Claude client initialized")

    # Load blueprint
    try:
        blueprint = load_blueprint("mining_resources")
        print_success("Blueprint loaded: Mining/Resources")
    except Exception as e:
        print_warning(f"Could not load blueprint: {e}")
        blueprint = None

    # Load documents
    print_section("LOADING DOCUMENTS")
    documents = load_documents(doc_dir)
    ref_docs = get_reference_documents(documents)

    print_success(f"Loaded {len(documents)} documents")
    print_success(f"Reference documents: {[d.filename for d in ref_docs]}")

    total_chars = sum(d.char_count for d in documents)
    total_words = sum(d.word_count for d in documents)
    print_success(f"Total content: {total_words:,} words ({total_chars:,} characters)")

    # List documents
    print("\nDocuments loaded:")
    for doc in documents:
        print(f"  - [{doc.doc_type:12}] {doc.filename} ({doc.word_count:,} words)")

    # Convert to dict format for processing
    doc_dicts = [doc.to_dict() for doc in documents]

    # ========================================
    # PASS 1: Extract & Index
    # ========================================
    print_header("PASS 1: EXTRACT & INDEX")

    pass1_results = run_pass1_extraction(doc_dicts, client, verbose=True)

    print_success(f"Extracted {len(pass1_results.get('key_dates', []))} key dates")
    print_success(f"Extracted {len(pass1_results.get('financial_figures', []))} financial figures")
    print_success(f"Found {len(pass1_results.get('coc_clauses', []))} Change of Control clauses")
    print_success(f"Found {len(pass1_results.get('consent_requirements', []))} consent requirements")
    print_success(f"Found {len(pass1_results.get('covenants', []))} covenants")

    # ========================================
    # PASS 2: Per-Document Analysis
    # ========================================
    print_header("PASS 2: PER-DOCUMENT ANALYSIS")
    print("(Reference documents injected into every analysis)")

    pass2_result = run_pass2_analysis(
        doc_dicts,
        ref_docs,
        blueprint,
        client,
        verbose=True
    )

    # Handle dict or list return
    if isinstance(pass2_result, dict):
        pass2_findings = pass2_result.get('findings', [])
    else:
        pass2_findings = pass2_result

    print_success(f"Generated {len(pass2_findings)} per-document findings")

    # Show severity breakdown
    by_severity = {}
    for f in pass2_findings:
        sev = f.get("severity", "medium")
        by_severity[sev] = by_severity.get(sev, 0) + 1
    print(f"  Severity breakdown: {by_severity}")

    # ========================================
    # PASS 2.5: Financial Calculation Engine
    # ========================================
    print_header("PASS 2.5: FINANCIAL CALCULATIONS")
    print("[Deterministic Python calculations - AI extracts, Python calculates]")

    # Get transaction value from Pass 1 if available
    transaction_value = None
    for fig in pass1_results.get('financial_figures', []):
        if 'purchase' in str(fig.get('description', '')).lower() or 'transaction' in str(fig.get('description', '')).lower():
            transaction_value = fig.get('amount')
            break

    calc_orchestrator = CalculationOrchestrator(transaction_value=transaction_value)

    try:
        pass2_findings = calc_orchestrator.process_pass2_findings(pass2_findings)
        calc_summary = calc_orchestrator.get_calculation_summary()
        print_success(f"Calculations performed: {calc_summary['successful']}")
        print_success(f"Calculations failed: {calc_summary['failed']}")
    except Exception as e:
        print_warning(f"Calculation engine error: {e}")
        calc_summary = {"successful": 0, "failed": 0}

    # ========================================
    # PASS 3: Cross-Document Synthesis
    # ========================================
    print_header("PASS 3: CROSS-DOCUMENT SYNTHESIS")
    print("[THIS IS THE KEY ARCHITECTURAL IMPROVEMENT]")

    pass3_results = run_pass3_crossdoc_synthesis(
        doc_dicts,
        pass2_findings,
        blueprint,
        client,
        verbose=True
    )

    conflicts = pass3_results.get("conflicts", [])
    cascade = pass3_results.get("cascade_analysis", {})
    auth_issues = pass3_results.get("authorization_issues", [])
    consents = pass3_results.get("consent_matrix", [])

    print_success(f"Found {len(conflicts)} cross-document CONFLICTS")
    print_success(f"Mapped {len(cascade.get('cascade_items', []))} cascade items")
    print_success(f"Identified {len(auth_issues)} authorization issues")
    print_success(f"Built consent matrix with {len(consents)} items")

    # ========================================
    # PASS 3.5: Aggregate Calculations
    # ========================================
    print_header("PASS 3.5: AGGREGATE CALCULATIONS")
    print("[Cross-document calculation aggregation and dependency resolution]")

    calc_aggregates = None
    try:
        cross_doc_findings = pass3_results.get('cross_doc_findings', [])
        clusters = pass3_results.get('clusters', [])
        calc_aggregates = calc_orchestrator.process_pass3_aggregates(
            clusters=clusters,
            cross_doc_findings=cross_doc_findings
        )
        print_success(f"Total calculated exposure: ZAR {calc_aggregates.get('total_exposure', 0):,.0f}")
        if calc_aggregates.get('transaction_ratio', {}).get('exceeds_transaction'):
            print_warning("WARNING: Total exposure exceeds transaction value!")
    except Exception as e:
        print_warning(f"Aggregate calculation error: {e}")

    # ========================================
    # PASS 4: Deal Synthesis
    # ========================================
    print_header("PASS 4: DEAL SYNTHESIS")

    pass4_results = run_pass4_synthesis(
        doc_dicts,
        pass1_results,
        pass2_findings,
        pass3_results,
        client,
        verbose=True
    )

    # ========================================
    # PASS 5: Opus Verification
    # ========================================
    print_header("PASS 5: OPUS VERIFICATION")
    print("[Final quality check using Claude Opus]")

    verification_result = None
    try:
        # Build transaction context
        transaction_context = f"""
This is a 100% share sale acquisition of Karoo Mining (Pty) Ltd.
The buyer will acquire all issued shares from the current shareholders.
Transaction type: Mining acquisition
"""
        verification_result = run_pass5_verification(
            pass4_results=pass4_results,
            pass3_results=pass3_results,
            pass2_findings=pass2_findings,
            pass1_results=pass1_results,
            calculation_aggregates=calc_aggregates,
            transaction_context=transaction_context,
            client=client,
            verbose=True
        )

        if verification_result and not verification_result.error:
            # Apply verification adjustments
            pass4_results = apply_verification_adjustments(pass4_results, verification_result)

            status = "PASSED" if verification_result.verification_passed else "FAILED"
            print_success(f"Verification {status} ({verification_result.overall_confidence:.0%} confidence)")

            if verification_result.critical_issues:
                print_warning(f"Critical issues found: {len(verification_result.critical_issues)}")
                for issue in verification_result.critical_issues[:3]:
                    print_error(f"  - {issue.get('issue', 'Unknown')[:80]}")

            if verification_result.warnings:
                print_warning(f"Warnings: {len(verification_result.warnings)}")
        else:
            print_warning(f"Verification had error: {verification_result.error if verification_result else 'No result'}")
    except Exception as e:
        print_warning(f"Pass 5 verification error (non-fatal): {e}")

    # ========================================
    # DISPLAY RESULTS
    # ========================================
    print_header("RESULTS SUMMARY")

    # Deal Blockers
    print_section("DEAL BLOCKERS")
    deal_blockers = pass4_results.get("deal_blockers", [])
    if deal_blockers:
        for i, blocker in enumerate(deal_blockers, 1):
            if RICH_AVAILABLE:
                console = Console()
                console.print(f"[bold red]{i}. {blocker.get('issue', blocker.get('description', 'Unknown'))}[/bold red]")
            else:
                print(f"{i}. {blocker.get('issue', blocker.get('description', 'Unknown'))}")
            source = blocker.get("source", blocker.get("source_document", ""))
            if source:
                print(f"   Source: {source}")
            resolution = blocker.get("resolution_path", blocker.get("action_required", ""))
            if resolution:
                print(f"   Resolution: {resolution}")
    else:
        print("  No deal blockers identified (review authorization issues)")

    # Authorization Issues (these are often the real deal blockers)
    if auth_issues:
        print_section("AUTHORIZATION ISSUES")
        for issue in auth_issues:
            print(f"  - {issue.get('description', str(issue))}")

    # Conflicts
    print_section("CROSS-DOCUMENT CONFLICTS")
    if conflicts:
        for conflict in conflicts:
            print(f"\n  [{conflict.get('severity', 'medium').upper()}] {conflict.get('description')}")
            print(f"    {conflict.get('document_a')}: {conflict.get('document_a_provision', '')[:80]}")
            print(f"    {conflict.get('document_b')}: {conflict.get('document_b_provision', '')[:80]}")
    else:
        print("  No cross-document conflicts identified")

    # Financial Exposures
    print_section("FINANCIAL EXPOSURE CALCULATIONS")
    exposures = pass4_results.get("financial_exposures", {})
    exposure_items = exposures.get("items", [])

    if exposure_items:
        if RICH_AVAILABLE:
            console = Console()
            table = Table(show_header=True)
            table.add_column("Source")
            table.add_column("Type")
            table.add_column("Amount (ZAR)", justify="right")
            table.add_column("Calculation")

            for item in exposure_items:
                table.add_row(
                    str(item.get("source", "")),
                    str(item.get("type", "")),
                    f"R{item.get('amount', 0):,.0f}",
                    str(item.get("calculation", ""))[:40]
                )

            total = exposures.get("total", 0)
            table.add_row("[bold]TOTAL[/bold]", "", f"[bold]R{total:,.0f}[/bold]", "")
            console.print(table)
        else:
            for item in exposure_items:
                print(f"  {item.get('source')}: R{item.get('amount', 0):,.0f} ({item.get('type')})")
            print(f"\n  TOTAL: R{exposures.get('total', 0):,.0f}")
    else:
        print("  No financial exposures calculated")

    # Cascade summary
    print_section("CHANGE OF CONTROL CASCADE")
    print(get_cascade_summary(cascade))

    # Conditions Precedent
    print_section("CONDITIONS PRECEDENT REGISTER")
    cps = pass4_results.get("conditions_precedent", [])
    if cps:
        for cp in cps[:10]:  # Show first 10
            status = "[ ]" if cp.get("status") != "complete" else "[x]"
            blocker = "[BLOCKER]" if cp.get("is_deal_blocker") else ""
            print(f"  {status} {cp.get('cp_number', '')}. {cp.get('description', '')[:60]} {blocker}")
        if len(cps) > 10:
            print(f"  ... and {len(cps) - 10} more")
    else:
        print("  No conditions precedent identified")

    # Executive Summary
    if pass4_results.get("executive_summary"):
        print_section("EXECUTIVE SUMMARY")
        print(pass4_results["executive_summary"][:1500])

    # ========================================
    # SAVE REPORT
    # ========================================
    print_header("SAVING REPORT")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON
    json_path = output_dir / f"dd_results_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump({
            "pass1_extracts": pass1_results,
            "pass2_findings": pass2_findings,
            "pass3_results": {
                "conflicts": conflicts,
                "cascade_analysis": cascade,
                "authorization_issues": auth_issues,
                "consent_matrix": consents,
            },
            "pass4_synthesis": pass4_results,
        }, f, indent=2, default=str)
    print_success(f"JSON results saved to: {json_path}")

    # Save Markdown report
    md_path = output_dir / f"dd_report_{timestamp}.md"
    with open(md_path, "w") as f:
        f.write(generate_markdown_report(
            pass1_results, pass2_findings, pass3_results, pass4_results
        ))
    print_success(f"Markdown report saved to: {md_path}")

    # Usage report
    print_section("TOKEN USAGE")
    print(client.get_usage_report())

    print_header("POC COMPLETE")


def generate_markdown_report(pass1, pass2, pass3, pass4) -> str:
    """Generate a markdown report of the DD analysis."""

    lines = [
        "# Karoo Mining Due Diligence Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        pass4.get("executive_summary", "No summary generated."),
        "",
        "---",
        "",
        "## Deal Assessment",
        "",
    ]

    assessment = pass4.get("deal_assessment", {})
    can_proceed = assessment.get("can_proceed", "Unknown")
    lines.append(f"**Can Proceed:** {'Yes (subject to conditions)' if can_proceed else 'No - blocking issues identified'}")
    lines.append(f"**Risk Rating:** {assessment.get('overall_risk_rating', 'Unknown').upper()}")
    lines.append("")

    # Deal Blockers
    lines.append("## Deal Blockers")
    lines.append("")
    blockers = pass4.get("deal_blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"### {blocker.get('issue', blocker.get('description', 'Unknown'))}")
            lines.append(f"- **Source:** {blocker.get('source', 'Unknown')}")
            lines.append(f"- **Resolution:** {blocker.get('resolution_path', 'TBD')}")
            lines.append("")
    else:
        lines.append("No deal blockers identified.")
        lines.append("")

    # Cross-Document Conflicts
    lines.append("## Cross-Document Conflicts")
    lines.append("")
    conflicts = pass3.get("conflicts", [])
    if conflicts:
        for conflict in conflicts:
            lines.append(f"### {conflict.get('description', 'Conflict')}")
            lines.append(f"- **Severity:** {conflict.get('severity', 'Unknown')}")
            lines.append(f"- **Document A ({conflict.get('document_a', '')}):** {conflict.get('document_a_provision', '')}")
            lines.append(f"- **Document B ({conflict.get('document_b', '')}):** {conflict.get('document_b_provision', '')}")
            lines.append(f"- **Resolution Required:** {conflict.get('resolution_required', 'TBD')}")
            lines.append("")
    else:
        lines.append("No cross-document conflicts identified.")
        lines.append("")

    # Financial Exposures
    lines.append("## Financial Exposures")
    lines.append("")
    exposures = pass4.get("financial_exposures", {})
    items = exposures.get("items", [])
    if items:
        lines.append("| Source | Type | Amount (ZAR) | Calculation |")
        lines.append("|--------|------|-------------|-------------|")
        for item in items:
            lines.append(f"| {item.get('source', '')} | {item.get('type', '')} | R{item.get('amount', 0):,.0f} | {item.get('calculation', '')[:30]} |")
        lines.append(f"| **TOTAL** | | **R{exposures.get('total', 0):,.0f}** | |")
        lines.append("")
    else:
        lines.append("No financial exposures calculated.")
        lines.append("")

    # Conditions Precedent
    lines.append("## Conditions Precedent Register")
    lines.append("")
    cps = pass4.get("conditions_precedent", [])
    if cps:
        lines.append("| # | Description | Category | Source | Blocker |")
        lines.append("|---|-------------|----------|--------|---------|")
        for cp in cps:
            blocker = "Yes" if cp.get("is_deal_blocker") else "No"
            lines.append(f"| {cp.get('cp_number', '')} | {cp.get('description', '')[:40]} | {cp.get('category', '')} | {cp.get('source', '')} | {blocker} |")
        lines.append("")
    else:
        lines.append("No conditions precedent identified.")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    recs = pass4.get("recommendations", [])
    if recs:
        for rec in recs:
            lines.append(f"- {rec}")
    else:
        lines.append("No specific recommendations generated.")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
