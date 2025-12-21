"""
Pass 4: Synthesis prompts.

Final pass that consolidates all findings, calculates exposures,
classifies deal-blockers, and generates executive summary.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are a senior M&A partner preparing the final due diligence summary
for presentation to the client and transaction team.

Your role is to:
1. Synthesize all findings into a coherent picture
2. Clearly identify deal-blockers vs manageable issues
3. Quantify financial exposures with VERIFIED calculations
4. Provide actionable recommendations
5. Present information in order of importance
6. Generate STRATEGIC QUESTIONS that probe deeper than the documents

The client needs to understand:
- Can we do this deal?
- What are the key risks?
- How much will it really cost?
- What do we need to close?
- What questions should we be asking that we haven't yet?

CRITICAL: When you identify issues, think like a skeptical partner:
- Challenge the valuation assumptions
- Question why financial performance is declining
- Ask what management isn't telling us
- Probe the real likelihood of adverse scenarios
- Consider what information is missing from the data room"""


def build_synthesis_prompt(
    pass2_findings: str,
    pass3_conflicts: str,
    pass3_cascade: str,
    pass3_authorization: str,
    pass3_consents: str,
    transaction_value: str = "undisclosed"
) -> str:
    """
    Build the final synthesis prompt.

    Consolidates all findings from previous passes into actionable output.
    """

    return f"""Prepare the final Due Diligence synthesis for this acquisition.

TRANSACTION VALUE: {transaction_value}

---

FINDINGS FROM DOCUMENT ANALYSIS (Pass 2):
{pass2_findings}

---

CROSS-DOCUMENT CONFLICTS IDENTIFIED (Pass 3):
{pass3_conflicts}

---

CHANGE OF CONTROL CASCADE ANALYSIS (Pass 3):
{pass3_cascade}

---

AUTHORIZATION CHECK (Pass 3):
{pass3_authorization}

---

CONSENT MATRIX (Pass 3):
{pass3_consents}

---

Synthesize all the above into a final DD summary.

Return JSON:
{{
    "executive_summary": "3-5 paragraph executive summary suitable for client presentation",

    "deal_assessment": {{
        "can_proceed": true/false,
        "blocking_issues": ["List of issues that MUST be resolved before closing"],
        "key_risks": ["Top 3-5 risks in order of importance"],
        "overall_risk_rating": "high|medium|low"
    }},

    "financial_exposure_summary": {{
        "total_quantified_exposure": number,
        "currency": "ZAR",
        "exposure_breakdown": [
            {{
                "category": "change_of_control|acceleration|termination|other",
                "amount": number,
                "description": "Brief description",
                "likelihood": "high|medium|low"
            }}
        ],
        "unquantified_risks": ["Risks that couldn't be quantified but are material"]
    }},

    "deal_blockers": [
        {{
            "issue": "Clear description",
            "source": "Document where found",
            "why_blocking": "Why this prevents closing",
            "resolution_path": "How to resolve",
            "resolution_timeline": "Estimated time to resolve",
            "owner": "Who is responsible for resolution"
        }}
    ],

    "conditions_precedent_register": [
        {{
            "cp_number": 1,
            "description": "Description of condition",
            "category": "consent|approval|regulatory|document|other",
            "source": "Contract requiring this",
            "responsible_party": "buyer|seller|third_party",
            "target_date": "When needed",
            "status": "not_started|in_progress|complete",
            "is_deal_blocker": true/false
        }}
    ],

    "price_adjustment_items": [
        {{
            "item": "Description",
            "amount": number or null,
            "basis": "Why this affects price"
        }}
    ],

    "warranty_indemnity_items": [
        {{
            "item": "Description",
            "suggested_protection": "Specific warranty/indemnity wording or cap suggestion"
        }}
    ],

    "post_closing_items": [
        {{
            "item": "Description",
            "deadline": "When to complete",
            "owner": "Who is responsible"
        }}
    ],

    "key_recommendations": [
        "Top 5 recommendations for the transaction team"
    ],

    "next_steps": [
        "Immediate actions required"
    ],

    "strategic_questions": [
        {{
            "question": "Full question text - must probe WHY not just WHAT",
            "category": "valuation|commercial|strategic|risk|regulatory|governance",
            "priority": "critical|high|medium",
            "context": "Why this question matters for the transaction",
            "who_should_answer": "Target management|Seller|Advisor|Regulatory body",
            "documents_needed": ["Documents that would help answer this"]
        }}
    ]
}}

IMPORTANT:
1. Be decisive - clearly state if issues are deal-blocking
2. Quantify everything possible with ZAR amounts
3. Prioritize by importance, not by document order
4. Focus on what the client needs to DECIDE and DO
5. Flag any areas where further investigation is needed

STRATEGIC QUESTIONS GUIDANCE:
Generate 8-12 strategic questions that a senior M&A partner would ask the client or target.
These should NOT be simple document requests - they should be INVESTIGATIVE questions that probe deeper issues.

Examples of GOOD strategic questions:
- "What caused the 14.5% revenue decline and is this trend continuing into the current year?"
- "Is the R850M valuation justified given the going concern qualification and negative working capital?"
- "What is Eskom's historical approach to enforcing CoC termination clauses in coal supply agreements?"
- "Should the transaction be structured to preserve existing BEE shareholding to maintain Mining Charter compliance?"
- "What retention mechanisms are needed for the MD given his R15M severance entitlement?"

Examples of BAD questions (too simple - avoid these):
- "Obtain the latest management accounts" (this is a document request, not a question)
- "Confirm the water license status" (this is an action item, not an investigative question)

Categories to cover:
1. VALUATION & COMMERCIAL - Questions that challenge whether the price is right
2. STRATEGIC & OPERATIONAL - Questions about integration and business sustainability
3. RISK & LIABILITY - Questions about worst-case scenarios and protection mechanisms
4. REGULATORY & COMPLIANCE - Questions about ongoing compliance obligations
5. GOVERNANCE - Questions about management, controls, and decision-making"""


def build_calculation_verification_prompt(extracted_figures: str, cascade_exposures: str) -> str:
    """
    Prompt to verify and reconcile financial calculations.
    """

    return f"""Verify and reconcile all financial figures and calculations.

EXTRACTED FIGURES FROM DOCUMENTS:
{extracted_figures}

CALCULATED EXPOSURES FROM CASCADE ANALYSIS:
{cascade_exposures}

---

Check:
1. Are all calculations mathematically correct?
2. Do the figures reconcile with what's in the documents?
3. Are there any exposures that should be calculated but weren't?
4. What is the TOTAL financial exposure if all adverse events occur?

Return JSON:
{{
    "verified_calculations": [
        {{
            "description": "What was calculated",
            "formula": "The calculation formula",
            "inputs": {{"var1": value, "var2": value}},
            "result": number,
            "verified": true/false,
            "notes": "Any issues or clarifications"
        }}
    ],
    "reconciliation_issues": [
        "Any figures that don't reconcile or seem incorrect"
    ],
    "missing_calculations": [
        "Exposures that should be calculated but weren't"
    ],
    "total_worst_case_exposure": {{
        "amount": number,
        "currency": "ZAR",
        "breakdown": "Summary of components"
    }}
}}"""
