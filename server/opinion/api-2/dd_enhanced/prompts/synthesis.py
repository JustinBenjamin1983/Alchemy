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
    transaction_value: str = "undisclosed",
    validated_context: dict = None
) -> str:
    """
    Build the final synthesis prompt.

    Consolidates all findings from previous passes into actionable output.
    Incorporates user-validated corrections from Checkpoint B.
    """

    # Build user corrections section if available
    corrections_section = _build_corrections_section(validated_context)

    return f"""Prepare the final Due Diligence synthesis for this acquisition.

TRANSACTION VALUE: {transaction_value}
{corrections_section}

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

    "financial_analysis": {{
        "overview": "2-3 paragraph executive financial summary covering: (1) Overall financial health assessment, (2) Key trends and their implications, (3) Major risks/red flags identified, (4) Quality of earnings concerns if any",

        "profitability_performance": {{
            "margin_analysis": {{
                "gross_margin": {{"current": number, "prior": number, "trend": "improving|declining|stable"}},
                "operating_margin": {{"current": number, "prior": number, "trend": "improving|declining|stable"}},
                "ebitda_margin": {{"current": number, "prior": number, "trend": "improving|declining|stable"}},
                "net_margin": {{"current": number, "prior": number, "trend": "improving|declining|stable"}},
                "notes": "Margin analysis observations - flag if declining >5% or significantly below peers"
            }},
            "return_metrics": {{
                "roe": number or null,
                "roa": number or null,
                "roic": number or null,
                "notes": "Return metrics assessment - high ROE from leverage vs operations = different risk"
            }},
            "revenue_quality": {{
                "recurring_vs_one_off_pct": number or null,
                "customer_concentration": {{"top_customer_pct": number, "top_5_customers_pct": number, "flag": "none|warning|critical"}},
                "geographic_concentration": "Description of geographic revenue mix",
                "contract_backlog": number or null,
                "notes": ">20% from single customer = key-man risk; high one-off revenue inflates current period"
            }}
        }},

        "liquidity_solvency": {{
            "short_term_liquidity": {{
                "current_ratio": number or null,
                "quick_ratio": number or null,
                "cash_ratio": number or null,
                "net_working_capital": number or null,
                "notes": "Current ratio <1.0 signals potential distress; quick ratio critical for manufacturing"
            }},
            "leverage_debt_service": {{
                "debt_to_equity": number or null,
                "net_debt_to_ebitda": number or null,
                "interest_coverage": number or null,
                "debt_maturity_profile": "Description of maturity schedule - wall of maturities = refinancing risk",
                "covenant_compliance": {{"in_compliance": true or false, "headroom_pct": number, "historical_breaches": "none|waived|default"}},
                "notes": "Net Debt/EBITDA >3.5x triggers concerns; Interest coverage <2.0x is distressed"
            }}
        }},

        "cash_flow_health": {{
            "operating_cash_flow": {{
                "ocf_current": number or null,
                "ocf_prior": number or null,
                "ocf_vs_net_income": "Aligned with NI|Gap - investigate|Significant gap - earnings quality concern",
                "notes": "Persistent OCF vs NI gap = earnings quality concern"
            }},
            "cash_conversion_cycle": {{
                "dso": number or null,
                "dio": number or null,
                "dpo": number or null,
                "total_ccc_days": number or null,
                "ccc_trend": "improving|stable|deteriorating",
                "notes": "Rising DSO may indicate collection issues; Rising DIO signals obsolescence risk"
            }},
            "free_cash_flow": {{
                "fcf_current": number or null,
                "capex_maintenance": number or null,
                "capex_growth": number or null,
                "dividend_coverage_ratio": number or null,
                "notes": "Negative FCF with positive NI = red flag; Underspending maintenance = asset quality erosion"
            }}
        }},

        "quality_of_earnings": {{
            "revenue_recognition": {{
                "policy_assessment": "Conservative|Appropriate|Aggressive",
                "accrued_unbilled_revenue_trend": "Stable|Growing|Growing faster than billed AR - concern",
                "deferred_revenue_trend": "Stable|Growing|Declining - may signal churn",
                "notes": "Aggressive POC recognition, bill-and-hold arrangements"
            }},
            "expense_capitalisation": {{
                "capitalised_costs_concern": true or false,
                "rd_capitalisation_rate": number or null,
                "depreciation_policy": "Conservative|Industry standard|Aggressive - longer lives",
                "notes": "Capitalising opex inflates EBITDA; check policy changes"
            }},
            "ebitda_adjustments": [
                {{
                    "adjustment_type": "Description of add-back",
                    "amount": number,
                    "assessment": "Valid one-time|Questionable|Recurring disguised as one-time",
                    "notes": "Assessment rationale"
                }}
            ],
            "related_party_transactions": [
                {{
                    "description": "Transaction description",
                    "amount": number or null,
                    "assessment": "Arm's length|Below market|Above market - concern"
                }}
            ],
            "owner_adjustments": {{
                "above_market_compensation": number or null,
                "personal_expenses_through_business": number or null,
                "notes": "Normalization required for true earnings"
            }}
        }},

        "balance_sheet_integrity": {{
            "asset_quality": {{
                "goodwill_to_equity_pct": number or null,
                "receivables_aging_concern": "None|Moderate - growing >60 day|Significant - growing >90 day",
                "inventory_obsolescence_risk": "Low|Moderate|High - slow-moving stock identified",
                "ppe_condition": "Well maintained|Deferred maintenance concern|Impairment indicators",
                "intercompany_balances_concern": "None|Trapped cash|Transfer pricing adjustment needed",
                "notes": "Goodwill > 50% of equity = acquisition integration risk"
            }},
            "off_balance_sheet": {{
                "operating_lease_commitments": number or null,
                "guarantees_and_commitments": number or null,
                "contingent_liabilities": [
                    {{
                        "description": "Litigation/environmental/tax dispute",
                        "amount": number or null,
                        "probability": "Remote|Possible|Probable",
                        "notes": "Assessment"
                    }}
                ],
                "factoring_securitisation": "None|True sale|Financing with recourse - add to debt",
                "notes": "Off-balance sheet items that affect true leverage"
            }}
        }},

        "trend_analysis": {{
            "historical_performance": {{
                "revenue_3yr_cagr": number or null,
                "ebitda_3yr_cagr": number or null,
                "inflection_points": ["Any significant changes and their causes"],
                "notes": "Historical trend observations"
            }},
            "seasonality_patterns": {{
                "quarterly_pattern": "Even distribution|Q4 heavy|Seasonal pattern described",
                "hockey_stick_risk": true or false,
                "notes": "Hockey-stick Q4 = channel stuffing risk"
            }},
            "forecast_credibility": {{
                "historical_accuracy": "Consistently met|Mixed|Consistently missed",
                "budget_variance_pattern": "On target|Systematic over-performance|Systematic under-performance",
                "notes": "Consistent misses = credibility discount on projections"
            }}
        }},

        "red_flags_summary": [
            {{
                "category": "Profitability|Liquidity|Cash Flow|Quality of Earnings|Balance Sheet|Other",
                "flag": "Clear description of the red flag",
                "severity": "critical|high|medium",
                "source": "Document where identified",
                "impact": "Transaction impact - affects valuation/structure/risk allocation"
            }}
        ],

        "data_gaps": [
            {{
                "missing_item": "What financial information is missing",
                "importance": "critical|high|medium",
                "impact": "How this gap affects the analysis"
            }}
        ]
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

    "warranties_register": [
        {{
            "id": "W-001",
            "category": "Title & Capacity|Mining Rights|Environmental|Financial|Material Contracts|Employment|Tax|BEE",
            "description": "Clear description of the warranty",
            "detailed_wording": "Suggested warranty wording for the sale agreement",
            "typical_cap": "Purchase price|50% of purchase price|Unlimited|Quantified amount",
            "survival_period": "18 months|3 years|5 years|7 years",
            "priority": "critical|high|medium",
            "dd_trigger": "Which DD finding(s) triggered this warranty recommendation",
            "source_document": "Document where issue was identified"
        }}
    ],

    "indemnities_register": [
        {{
            "id": "I-001",
            "category": "Environmental|Mining Rights|Tax|Employment|Third Party Claims|BEE",
            "description": "Clear description of the indemnity",
            "detailed_wording": "Suggested indemnity wording for the sale agreement",
            "trigger": "What triggers this indemnity claim",
            "typical_cap": "Quantified gap amount|Unlimited|As negotiated",
            "survival_period": "3 years|5 years|7 years|Perpetual",
            "priority": "critical|high|medium",
            "escrow_recommendation": "10-20% of purchase price in escrow if applicable",
            "quantified_exposure": {{
                "amount": number or null,
                "currency": "ZAR",
                "calculation": "How the amount was calculated"
            }},
            "dd_trigger": "Which DD finding(s) triggered this indemnity recommendation",
            "source_document": "Document where issue was identified"
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
5. GOVERNANCE - Questions about management, controls, and decision-making

WARRANTIES & INDEMNITIES GUIDANCE:
Generate SEPARATE warranties and indemnities registers based on DD findings.

WARRANTIES (warranties_register):
- Warranties are representations by the Seller about the current state of the target
- Organize by category: Title & Capacity, Mining Rights, Environmental, Financial, Material Contracts, Employment, Tax, BEE
- Include specific suggested wording for the sale agreement
- Specify typical caps (e.g., "Purchase price", "50% of purchase price") and survival periods
- Link each warranty to the specific DD finding that triggered it
- Prioritize: Title/Capacity and Mining Rights should be "critical"; Tax warranties typically 5 years

INDEMNITIES (indemnities_register):
- Indemnities are obligations by Seller to compensate Buyer for specific identified risks
- Indemnities are appropriate for KNOWN issues discovered in DD (not warranties for unknown risks)
- Key triggers for indemnities:
  * Rehabilitation liability gap (provision < estimated liability)
  * Pre-closing environmental contamination
  * SLP arrears requiring catch-up expenditure
  * Pre-closing tax exposures
  * Occupational disease claims (silicosis, etc.)
  * Pre-closing breaches of material contracts
- Quantify the exposure where possible (e.g., "Rehabilitation gap: R45M - R32M = R13M shortfall")
- Recommend escrow for material environmental or rehabilitation indemnities (typically 10-20% of price)
- Specify survival periods: Environmental 5-7 years, Tax 5 years, Occupational disease 10+ years"""


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


def _build_corrections_section(validated_context: dict) -> str:
    """
    Build a section containing user corrections from Checkpoint B.

    Includes:
    - Transaction understanding corrections (structure, parties, deal type)
    - Financial corrections (corrected figures)
    - Manual inputs (user-provided data)
    """
    if not validated_context or not validated_context.get("has_validated_context"):
        return ""

    lines = ["\n", "=" * 70]
    lines.append("USER-VALIDATED CORRECTIONS (from Checkpoint B)")
    lines.append("=" * 70)
    lines.append("""
IMPORTANT: The following corrections were provided by the user during
validation. These MUST be incorporated into the synthesis and take
precedence over AI-extracted information.
""")

    # Transaction understanding corrections
    understanding = validated_context.get("transaction_understanding", [])
    if understanding:
        lines.append("\n**TRANSACTION UNDERSTANDING CORRECTIONS:**")
        for item in understanding:
            question_id = item.get("question_id", "")
            response = item.get("response", {})

            # Handle different response formats
            if isinstance(response, dict):
                status = response.get("status", "")
                clarification = response.get("clarification", "")
                if status == "partially_correct" and clarification:
                    lines.append(f"  - {question_id}: PARTIALLY CORRECT")
                    lines.append(f"    Clarification: {clarification}")
                elif status == "incorrect" and clarification:
                    lines.append(f"  - {question_id}: INCORRECT")
                    lines.append(f"    Correction: {clarification}")
            elif isinstance(response, str) and response:
                lines.append(f"  - {question_id}: {response}")

    # Financial corrections
    corrections = validated_context.get("financial_corrections", [])
    if corrections:
        lines.append("\n**FINANCIAL VALUE CORRECTIONS:**")
        lines.append("  Use these corrected values instead of AI-extracted values:")
        for corr in corrections:
            metric = corr.get("metric", "Unknown")
            original = corr.get("original_value", "N/A")
            corrected = corr.get("corrected_value", "N/A")
            lines.append(f"  - {metric}: {original} → {corrected} (USER CORRECTED)")

    # Manual inputs
    manual_inputs = validated_context.get("manual_inputs", {})
    if manual_inputs:
        lines.append("\n**USER-PROVIDED DATA (not in documents):**")
        for key, value in manual_inputs.items():
            if value:  # Only include non-empty values
                lines.append(f"  - {key}: {value}")

    lines.append("\n" + "=" * 70)

    return "\n".join(lines)
