"""
Pass 5: Opus Verification Prompts
=================================
Final verification pass using Claude Opus to:
1. Verify deal-blockers are truly blocking
2. Validate financial calculations and interpretations
3. Challenge assumptions and flag potential issues
4. Identify inconsistencies across findings
5. Provide confidence scores and recommendations
"""

VERIFICATION_SYSTEM_PROMPT = """You are a senior M&A partner performing final quality control on a due diligence report.
Your role is to be the "skeptical reviewer" - challenging findings, verifying calculations,
and ensuring the analysis is bulletproof before it goes to the client.

You have decades of experience and have seen deals fail due to:
- Overlooked deal-blockers that seemed minor
- Miscalculated financial exposures (off by orders of magnitude)
- Assumptions that weren't validated
- Missing regulatory requirements
- Inconsistent information across documents

Your job is NOT to redo the analysis, but to:
1. VERIFY - Are the conclusions supported by the evidence?
2. CHALLENGE - What assumptions might be wrong?
3. QUANTIFY - Are the financial calculations mathematically correct?
4. PRIORITIZE - Are the deal-blockers truly blocking?
5. FLAG - What's missing or inconsistent?

Be direct and specific. If something is wrong, say so clearly."""


def build_deal_blocker_verification_prompt(
    deal_blockers: list,
    transaction_context: str,
    executive_summary: str
) -> str:
    """
    Build prompt to verify deal-blockers are truly blocking.
    """
    blockers_text = ""
    for i, blocker in enumerate(deal_blockers, 1):
        blockers_text += f"""
BLOCKER {i}:
- Title: {blocker.get('title', blocker.get('issue', 'Unknown'))}
- Category: {blocker.get('category', 'Unknown')}
- Source: {blocker.get('source_document', blocker.get('source', 'Unknown'))}
- Description: {blocker.get('description', blocker.get('why_blocking', ''))}
- Resolution Path: {blocker.get('resolution_path', 'Not specified')}
"""

    return f"""TRANSACTION CONTEXT:
{transaction_context}

EXECUTIVE SUMMARY:
{executive_summary[:2000]}

---

IDENTIFIED DEAL BLOCKERS:
{blockers_text}

---

For each deal blocker, provide your assessment:

1. Is this TRULY a deal-blocker, or could it be downgraded to a condition precedent?
   - A TRUE deal-blocker means the transaction CANNOT proceed at all without resolution
   - A condition precedent means the transaction can proceed but this must be resolved by closing

2. Is the severity assessment correct?
   - Could this be resolved more easily than stated?
   - Or is it actually MORE severe than described?

3. Are there any MISSING deal-blockers?
   - Based on the executive summary, what critical issues might have been missed?
   - What regulatory or structural issues are commonly overlooked?

Return JSON:
{{
    "blocker_assessments": [
        {{
            "blocker_index": 1,
            "original_title": "Title of blocker",
            "is_truly_blocking": true/false,
            "recommended_classification": "deal_blocker|condition_precedent|price_chip|noted",
            "severity_assessment": "correct|understated|overstated",
            "reasoning": "Clear explanation of your assessment",
            "resolution_difficulty": "high|medium|low",
            "estimated_resolution_time": "Before signing|Before closing|Post-closing|Unknown"
        }}
    ],
    "missing_blockers": [
        {{
            "issue": "Description of potentially missed deal-blocker",
            "why_blocking": "Why this could block the deal",
            "likelihood": "high|medium|low",
            "recommended_action": "What should be done to investigate"
        }}
    ],
    "overall_deal_risk": "high|medium|low",
    "recommendation": "Proceed with caution|Resolve blockers first|Further investigation needed|Deal appears sound"
}}"""


def build_calculation_verification_prompt(
    calculations: list,
    financial_figures: list,
    transaction_value: float = None
) -> str:
    """
    Build prompt to verify financial calculations.
    """
    calc_text = ""
    for i, calc in enumerate(calculations, 1):
        calc_text += f"""
CALCULATION {i}:
- Formula ID: {calc.get('formula_id', 'Unknown')}
- Description: {calc.get('description', '')}
- Result: {calc.get('currency', 'ZAR')} {calc.get('amount', 0):,.2f}
- Inputs: {calc.get('inputs', {})}
- Calculation Steps: {calc.get('steps', 'Not provided')}
- Source Document: {calc.get('source_document', 'Unknown')}
- Clause Reference: {calc.get('clause_reference', 'Unknown')}
"""

    figures_text = ""
    for fig in financial_figures[:20]:
        figures_text += f"- {fig.get('description', 'Unknown')}: {fig.get('currency', 'ZAR')} {fig.get('amount', 0):,.0f} (Source: {fig.get('source_document', 'Unknown')})\n"

    transaction_info = f"TRANSACTION VALUE: ZAR {transaction_value:,.0f}" if transaction_value else "TRANSACTION VALUE: Not specified"

    return f"""{transaction_info}

EXTRACTED FINANCIAL FIGURES:
{figures_text}

---

CALCULATED EXPOSURES:
{calc_text}

---

For each calculation, verify:

1. MATHEMATICAL ACCURACY
   - Are the arithmetic operations correct?
   - Do the inputs match the source documents?
   - Are the units consistent (months, years, percentage points)?

2. INTERPRETATION ACCURACY
   - Is the formula appropriate for this type of exposure?
   - Are there alternative interpretations of the contract language?
   - Could the exposure be higher or lower under different readings?

3. MATERIALITY
   - Is this exposure material relative to the transaction value?
   - Should this affect deal pricing or structure?

4. MISSING EXPOSURES
   - Based on the financial figures, are there exposures that should have been calculated but weren't?

Return JSON:
{{
    "calculation_verifications": [
        {{
            "calculation_index": 1,
            "formula_id": "PEN_001",
            "original_amount": 927000000,
            "verified_amount": 927000000,
            "is_correct": true/false,
            "mathematical_accuracy": "correct|error_found|needs_review",
            "interpretation_accuracy": "correct|alternative_reading|ambiguous",
            "error_description": "If error found, describe it here",
            "alternative_calculation": "If different interpretation, show alternative",
            "materiality": "material|immaterial",
            "confidence": 0.0-1.0
        }}
    ],
    "missing_calculations": [
        {{
            "description": "What exposure is missing",
            "estimated_range": {{"low": 0, "high": 0, "currency": "ZAR"}},
            "source": "Where this should come from",
            "priority": "high|medium|low"
        }}
    ],
    "total_verified_exposure": {{
        "amount": 0,
        "currency": "ZAR",
        "confidence": 0.0-1.0
    }},
    "exposure_vs_transaction": {{
        "ratio": 0.0,
        "assessment": "acceptable|concerning|deal_threatening",
        "recommendation": "Recommendation for handling"
    }}
}}"""


def build_consistency_verification_prompt(
    findings: list,
    cross_doc_findings: list,
    conflicts: list
) -> str:
    """
    Build prompt to verify consistency across findings.
    """
    # Summarize key findings by category
    findings_by_category = {}
    for f in findings[:50]:
        cat = f.get('category', 'General')
        if cat not in findings_by_category:
            findings_by_category[cat] = []
        findings_by_category[cat].append({
            'title': f.get('direct_answer', f.get('description', ''))[:100],
            'severity': f.get('severity', 'medium'),
            'source': f.get('source_document', 'Unknown')
        })

    findings_text = ""
    for cat, items in findings_by_category.items():
        findings_text += f"\n{cat.upper()}:\n"
        for item in items[:5]:
            findings_text += f"  - [{item['severity']}] {item['title']} (Source: {item['source']})\n"

    cross_doc_text = ""
    for i, cd in enumerate(cross_doc_findings[:10], 1):
        cross_doc_text += f"{i}. {cd.get('description', 'Unknown')[:150]}\n"
        cross_doc_text += f"   Sources: {', '.join(cd.get('source_documents', [])[:3])}\n"

    conflicts_text = ""
    for i, conf in enumerate(conflicts[:10], 1):
        conflicts_text += f"{i}. {conf.get('description', 'Unknown')[:150]}\n"

    return f"""FINDINGS BY CATEGORY:
{findings_text}

---

CROSS-DOCUMENT FINDINGS:
{cross_doc_text}

---

IDENTIFIED CONFLICTS:
{conflicts_text if conflicts_text else "No conflicts identified"}

---

Review the findings for consistency and completeness:

1. INTERNAL CONSISTENCY
   - Do findings contradict each other?
   - Are severity ratings consistent across similar issues?
   - Do financial figures reconcile?

2. LOGICAL CONSISTENCY
   - Do the conclusions follow from the evidence?
   - Are there findings that seem inconsistent with the transaction type?
   - Are there gaps in the logical chain?

3. COMPLETENESS
   - Are there obvious areas not covered?
   - Based on the transaction type, what analysis is typically expected but missing?
   - Are there standard risks for this type of deal that weren't addressed?

4. PRIORITIZATION
   - Are the highest-severity items truly the most important?
   - Should any items be escalated or de-escalated?

Return JSON:
{{
    "consistency_issues": [
        {{
            "issue_type": "contradiction|gap|misprioritization|incomplete",
            "description": "Clear description of the issue",
            "affected_findings": ["Finding 1", "Finding 2"],
            "severity": "high|medium|low",
            "recommendation": "How to resolve"
        }}
    ],
    "missing_analysis_areas": [
        {{
            "area": "Name of missing analysis area",
            "typical_risks": "What risks are typically found here",
            "priority": "high|medium|low"
        }}
    ],
    "prioritization_adjustments": [
        {{
            "finding": "Description of finding",
            "current_severity": "critical|high|medium|low",
            "recommended_severity": "critical|high|medium|low",
            "reasoning": "Why this should change"
        }}
    ],
    "overall_consistency_score": 0.0-1.0,
    "confidence_in_analysis": "high|medium|low",
    "key_concerns": [
        "Top 3-5 concerns about the analysis quality"
    ]
}}"""


def build_final_verification_summary_prompt(
    blocker_verification: dict,
    calculation_verification: dict,
    consistency_verification: dict,
    transaction_context: str
) -> str:
    """
    Build prompt for final verification summary.
    """
    return f"""TRANSACTION CONTEXT:
{transaction_context}

---

DEAL BLOCKER VERIFICATION RESULTS:
- Overall Deal Risk: {blocker_verification.get('overall_deal_risk', 'Unknown')}
- Blockers Verified: {len(blocker_verification.get('blocker_assessments', []))}
- Missing Blockers Identified: {len(blocker_verification.get('missing_blockers', []))}
- Recommendation: {blocker_verification.get('recommendation', 'Unknown')}

---

CALCULATION VERIFICATION RESULTS:
- Calculations Verified: {len(calculation_verification.get('calculation_verifications', []))}
- Errors Found: {sum(1 for c in calculation_verification.get('calculation_verifications', []) if not c.get('is_correct', True))}
- Total Verified Exposure: {calculation_verification.get('total_verified_exposure', {}).get('currency', 'ZAR')} {calculation_verification.get('total_verified_exposure', {}).get('amount', 0):,.0f}
- Exposure Assessment: {calculation_verification.get('exposure_vs_transaction', {}).get('assessment', 'Unknown')}

---

CONSISTENCY VERIFICATION RESULTS:
- Consistency Issues Found: {len(consistency_verification.get('consistency_issues', []))}
- Missing Analysis Areas: {len(consistency_verification.get('missing_analysis_areas', []))}
- Overall Consistency Score: {consistency_verification.get('overall_consistency_score', 0):.0%}
- Confidence in Analysis: {consistency_verification.get('confidence_in_analysis', 'Unknown')}

---

Based on all verification results, provide a FINAL VERIFICATION SUMMARY:

Return JSON:
{{
    "verification_passed": true/false,
    "overall_confidence": 0.0-1.0,
    "critical_issues": [
        {{
            "issue": "Description of critical issue that must be addressed",
            "category": "deal_blocker|calculation|consistency|missing",
            "action_required": "Specific action to take",
            "owner": "Who should address this"
        }}
    ],
    "warnings": [
        "Non-critical issues to be aware of"
    ],
    "strengths": [
        "What was done well in the analysis"
    ],
    "final_recommendation": {{
        "deal_status": "proceed|proceed_with_caution|hold|do_not_proceed",
        "key_conditions": ["Conditions for proceeding"],
        "estimated_total_exposure": {{
            "amount": 0,
            "currency": "ZAR",
            "confidence": 0.0-1.0
        }},
        "next_steps": ["Immediate actions required"]
    }},
    "verification_metadata": {{
        "verification_date": "ISO date",
        "areas_verified": ["deal_blockers", "calculations", "consistency"],
        "documents_reviewed": 0,
        "findings_reviewed": 0
    }}
}}"""
