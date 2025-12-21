"""
Pass 2: Per-Document Analysis prompts.

These prompts analyze each document for risks and issues,
with reference documents (MOI, SHA) always in context.

BLUEPRINT-DRIVEN: The analysis prompts now dynamically include questions
from the transaction-type-specific blueprint.
"""
from typing import Dict, List, Optional, Any


def get_analysis_system_prompt(blueprint: Optional[Dict] = None) -> str:
    """
    Generate system prompt, optionally customized based on blueprint.
    Includes Chain-of-Thought (CoT) reasoning methodology.
    """
    transaction_type = blueprint.get("transaction_type", "corporate acquisition") if blueprint else "corporate acquisition"
    jurisdiction = blueprint.get("jurisdiction", "South Africa") if blueprint else "South Africa"

    legislation = ""
    if blueprint and blueprint.get("primary_legislation"):
        legislation = "\n\nKey legislation to consider:\n" + "\n".join(
            f"- {leg}" for leg in blueprint.get("primary_legislation", [])[:5]
        )

    # Get CoT questions if available in blueprint
    cot_section = _build_cot_methodology_section(blueprint)

    return f"""You are a senior M&A lawyer conducting legal due diligence for a {transaction_type}.

Jurisdiction: {jurisdiction}{legislation}

Your task is to identify risks, issues, and concerns that could affect the transaction.

{cot_section}

CLASSIFICATION DEFINITIONS:

**Severity Levels:**
- critical: Could prevent or derail the transaction entirely
- high: Significant issue requiring immediate attention before closing
- medium: Notable issue requiring resolution but manageable
- low: Minor issue for awareness only

**Deal Impact Categories:**
- deal_blocker: Transaction CANNOT close without resolution (e.g., missing shareholder approval, invalid mining right)
- condition_precedent: Must be resolved before closing but is resolvable (e.g., third party consent obtainable)
- price_chip: Should reduce purchase price or require indemnity protection
- warranty_indemnity: Allocate risk via sale agreement warranties/indemnities
- post_closing: Can be addressed after transaction completes
- noted: For information/record only

Always cite the specific clause reference when identifying an issue.
When calculating financial exposures, SHOW YOUR WORKING (e.g., "24 months × R3.2M/month = R76.8M")."""


def _build_cot_methodology_section(blueprint: Optional[Dict] = None) -> str:
    """Build the Chain-of-Thought reasoning methodology section."""

    base_cot = """CHAIN-OF-THOUGHT REASONING METHODOLOGY:

For EACH potential finding, you MUST reason through these steps IN ORDER before classifying:

**Step 1 - IDENTIFICATION:** What specific clause or provision triggers concern? Quote the exact language.

**Step 2 - CONTEXT:** What is the commercial significance of this document/contract? What is the surrounding contractual context?

**Step 3 - TRANSACTION IMPACT:** How does this interact with a 100% share sale / change of control? Does the transaction trigger this provision? What are the consequences if triggered?

**Step 4 - SEVERITY REASONING:** Why is this critical/high/medium/low? What is the worst-case scenario? What is the likelihood?

**Step 5 - DEAL IMPACT REASONING:** Why is this a blocker vs. condition vs. price chip? Can it be resolved before closing? Who needs to act (buyer/seller/third party)?

**Step 6 - FINANCIAL QUANTIFICATION:** Can a specific exposure be calculated? Show all working. What assumptions are being made?

**Step 7 - FINANCIAL TREND ANALYSIS (for financial documents):**
- Calculate year-over-year changes: Revenue, Gross Profit, Net Profit, Cash Position
- Format: "Revenue: R45.2M → R38.6M (-14.6% YoY)" with [FLAGGED] if decline >10%
- Calculate margin trends: "Gross Margin: 12.5% → 1.7% (-10.8pp)" with [FLAGGED] if compression >5pp
- Identify going concern indicators: negative working capital, audit qualifications, cash burn rate
- Flag any declining trend >10% or margin compression >5 percentage points

**Step 8 - BEE/OWNERSHIP ANALYSIS (for South African mining transactions - CRITICAL):**
- Pre-transaction HDSA ownership: Calculate current % held by Historically Disadvantaged South Africans
- Post-transaction HDSA ownership: If buyer is non-HDSA acquiring 100%, what is the new HDSA %?
- Mining Charter III requirement: 30% HDSA minimum (26% under transitional provisions)
- [CRITICAL FLAG] if post-transaction HDSA < 26% = REGULATORY DEAL BLOCKER
- Example calculation format: "Current: [X]% HDSA ([Shareholder A] [Y]% + [Shareholder B] [Z]%). Post-transaction if [Acquirer] is non-HDSA: HDSA = 0%. Mining Charter requires 26% minimum. GAP: [calculated]%"

IMPORTANT: Only assign severity and deal_impact AFTER completing your reasoning. Your reasoning must justify your classification."""

    # Add transaction-type specific CoT questions if available
    if blueprint and blueprint.get("cot_questions"):
        cot_questions = blueprint.get("cot_questions", {})
        specific_questions = []

        for category, questions in cot_questions.items():
            if questions:
                specific_questions.append(f"\n**{category} - Additional Reasoning Questions:**")
                for q in questions[:5]:  # Limit per category
                    specific_questions.append(f"- {q}")

        if specific_questions:
            base_cot += "\n\nTRANSACTION-TYPE SPECIFIC REASONING:\n" + "\n".join(specific_questions)

    return base_cot


# Legacy constant for backwards compatibility
ANALYSIS_SYSTEM_PROMPT = get_analysis_system_prompt()


def build_analysis_prompt(
    document_text: str,
    document_name: str,
    doc_type: str,
    reference_docs_text: str,
    transaction_context: str,
    blueprint: Optional[Dict] = None,
    prioritized_questions: Optional[List[Dict]] = None,
    folder_category: Optional[str] = None,
    folder_questions: Optional[List[Dict]] = None
) -> str:
    """
    Build the analysis prompt for a single document.

    KEY IMPROVEMENTS:
    1. Reference documents (MOI, SHA) are always included for validation
    2. Blueprint questions are injected to guide specific analysis
    3. Deal blocker definitions from blueprint are included
    4. Financial calculation templates are provided
    5. Prioritized questions from question_prioritizer take precedence
    6. Chain-of-Thought (CoT) reasoning questions guide analysis methodology
    7. Phase 3: Folder-specific questions for targeted analysis
    """

    # Build questions section - use folder questions, then prioritized, then blueprint
    questions_section = _build_questions_section(
        blueprint, doc_type, prioritized_questions, folder_category, folder_questions
    )

    # Build deal blocker awareness section
    deal_blockers_section = _build_deal_blockers_section(blueprint)

    # Build calculation templates section
    calculations_section = _build_calculations_section(blueprint)

    # Build CoT reasoning questions section based on document type
    cot_questions_section = _build_cot_questions_section(blueprint, doc_type)

    return f"""Analyze this document for the transaction described below.

TRANSACTION CONTEXT:
{transaction_context}

---

REFERENCE DOCUMENTS (Constitutional/Governance - use these to validate requirements):
{reference_docs_text}

---

DOCUMENT BEING ANALYZED: {document_name} ({doc_type})
{document_text}

---
{questions_section}
---
{deal_blockers_section}
---
{cot_questions_section}
---

Conduct a thorough analysis using the Chain-of-Thought methodology. For EACH potential issue:

1. **REASON FIRST**: Complete all 6 reasoning steps before classifying
2. **THEN CLASSIFY**: Only after reasoning, assign severity and deal_impact
3. **SHOW YOUR WORK**: The reasoning field must justify your classification

For each issue found, classify:

1. **Severity**:
   - critical: Could prevent or derail the transaction
   - high: Significant issue requiring immediate attention
   - medium: Notable issue requiring resolution
   - low: Minor issue for awareness

2. **Deal Impact**:
   - deal_blocker: Transaction CANNOT close without resolution (e.g., missing shareholder approval)
   - condition_precedent: Must be resolved before closing (e.g., third party consent)
   - price_chip: Should reduce purchase price or require indemnity
   - warranty_indemnity: Allocate risk via sale agreement warranties
   - post_closing: Can be addressed after transaction completes
   - noted: For information/record only
{calculations_section}
---

Return JSON:
{{
    "document_summary": "Brief summary of document and its relevance to transaction",

    "findings": [
        {{
            "finding_id": "F001",
            "category": "change_of_control|consent|financial|covenant|governance|employment|regulatory|contractual|mining_rights|environmental",

            "reasoning": {{
                "step_1_identification": "What specific clause triggers concern? Quote exact text: 'In the event of...'",
                "step_2_context": "What is the commercial significance? E.g., 'This is the primary surface lease covering the main mining pit...'",
                "step_3_transaction_impact": "How does 100% share sale interact with this? Does it trigger the provision?",
                "step_4_severity_reasoning": "Why this severity level? What is worst case? E.g., 'CRITICAL because loss of surface access halts operations...'",
                "step_5_deal_impact_reasoning": "Why blocker vs CP vs price chip? Can it be resolved? E.g., 'CONDITION PRECEDENT because consent is obtainable...'",
                "step_6_financial_quantification": "Show calculation: 24 months × R3.2M/month = R76.8M. State assumptions."
            }},

            "description": "Clear description of the issue (derived from your reasoning)",
            "clause_reference": "Clause X.X",
            "evidence_quote": "Exact quote from document (max 200 chars)",
            "severity": "critical|high|medium|low",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|warranty_indemnity|post_closing|noted",
            "financial_exposure": {{
                "amount": number or null,
                "currency": "ZAR",
                "calculation": "Show your working: e.g., 24 months × R3.2M = R76.8M",
                "type": "liquidated_damages|acceleration|penalty|fee|rehabilitation|regulatory"
            }},
            "financial_extraction": {{
                "has_calculable_exposure": true,
                "formula_pattern": "PEN_001|EMP_001|LSE_001|DBT_001|etc",
                "variables": {{
                    "var_name_1": {{"value": 500000, "unit": "tonnes", "source_clause": "1.1"}},
                    "var_name_2": {{"value": 927, "unit": "ZAR", "source_clause": "2.3"}}
                }},
                "interpretation_notes": "How you interpreted the contract terms"
            }},
            "action_required": "What needs to be done to address this",
            "responsible_party": "buyer|seller|third_party|dmre|lender",
            "deadline": "When this needs to be resolved if applicable",
            "blueprint_question_answered": "The specific question from the checklist this finding addresses (if applicable)"
        }}
    ],

    "questions_answered": [
        {{
            "question": "The question from the checklist",
            "answer": "Brief answer based on document analysis",
            "finding_refs": ["F001", "F002"]
        }}
    ],

    "positive_confirmations": [
        {{
            "description": "Positive aspect of this document for the transaction",
            "clause_reference": "Clause X.X if applicable"
        }}
    ],

    "missing_information": [
        "List of information that should be in this document but is missing or unclear"
    ],

    "cross_reference_needed": [
        "Other documents that should be checked in relation to findings in this document"
    ],

    "compliance_deadlines": [
        {{
            "deadline": "Date or timeframe",
            "description": "What must be done",
            "source_clause": "Clause X.X",
            "consequence_of_missing": "What happens if deadline is missed"
        }}
    ]
}}

Be thorough - a good lawyer would rather flag something unnecessary than miss something important."""


def _build_questions_section(
    blueprint: Optional[Dict],
    doc_type: str,
    prioritized_questions: Optional[List[Dict]] = None,
    folder_category: Optional[str] = None,
    folder_questions: Optional[List[Dict]] = None
) -> str:
    """
    Build the questions section from folder questions, prioritized questions, or blueprint.

    Priority order:
    1. Folder-specific questions (Phase 3) - most targeted
    2. Prioritized questions from question_prioritizer
    3. Blueprint risk_categories questions
    4. Default standard questions
    """

    # Phase 3: If we have folder-specific questions, use those as primary
    if folder_questions:
        return _build_folder_questions_section(folder_category, folder_questions)

    # If we have prioritized questions from question_prioritizer, use those
    if prioritized_questions:
        return _build_prioritized_questions_section(prioritized_questions, doc_type)

    # Fall back to blueprint-based questions
    if not blueprint:
        return """
STANDARD QUESTIONS TO ADDRESS:
1. Does this document contain change of control provisions?
2. What consents are required for assignment or transfer?
3. Are there any financial exposures (penalties, damages, fees)?
4. What are the key dates and deadlines?
5. Are there any restrictive covenants?
6. What happens on termination?
7. Are there any compliance deadlines that could be missed?
8. What is the total financial exposure if things go wrong?
"""

    questions = []

    # Get relevant questions from risk categories
    for category in blueprint.get("risk_categories", []):
        cat_name = category.get("name", "")

        # Include all questions for critical/high categories
        weight = category.get("weight", "medium")
        if weight in ["critical", "high"]:
            for q in category.get("standard_questions", [])[:10]:  # Limit per category
                # Handle both string questions and dict questions
                if isinstance(q, str):
                    # Blueprint format: questions are plain strings
                    questions.append(f"[{weight.upper()}] {q}")
                elif isinstance(q, dict):
                    # Dict format with priority/question/detail
                    priority = q.get("priority", "medium")
                    question_text = q.get("question", "")
                    detail = q.get("detail", "")

                    if priority in ["critical", "high"]:
                        questions.append(f"[{priority.upper()}] {question_text}")
                        if detail:
                            questions.append(f"    ({detail})")

    # Add base questions from blueprint
    base_questions = blueprint.get("base_questions", {})
    for group_name, group_questions in base_questions.items():
        for q in group_questions[:3]:  # Limit per group
            # Handle both string and dict formats
            if isinstance(q, str):
                questions.append(f"[HIGH] {q}")
            elif isinstance(q, dict) and q.get("priority") in ["critical", "high"]:
                questions.append(f"[{q.get('priority', 'medium').upper()}] {q.get('question', '')}")

    if not questions:
        return """
STANDARD QUESTIONS TO ADDRESS:
1. Does this document contain change of control provisions?
2. What consents are required for assignment or transfer?
3. Are there any financial exposures (penalties, damages, fees)?
4. What are the key dates and deadlines?
5. Are there any restrictive covenants?
"""

    return f"""
QUESTIONS TO ADDRESS FOR THIS TRANSACTION TYPE:
(Answer these questions where relevant to this document)

{chr(10).join(questions[:30])}
"""


def _build_folder_questions_section(
    folder_category: Optional[str],
    folder_questions: List[Dict]
) -> str:
    """
    Build questions section from folder-specific questions (Phase 3).

    These are the most targeted questions, derived from the blueprint's
    folder_questions section for the document's folder category.
    """
    if not folder_questions:
        return ""

    # Format folder name for display
    folder_display = folder_category.replace("_", " ").lstrip("0123456789") if folder_category else "Document"
    folder_display = folder_display.strip()

    # Organize questions by priority
    critical_questions = []
    high_questions = []
    other_questions = []

    for q in folder_questions:
        question_text = q.get("question", "")
        priority = q.get("priority", "medium")
        detail = q.get("detail", "")
        cot_hint = q.get("cot_hint", "")

        formatted = f"[{priority.upper()}] {question_text}"
        if detail:
            formatted += f"\n    Detail: {detail}"
        if cot_hint:
            formatted += f"\n    Reasoning: {cot_hint}"

        if priority == "critical":
            critical_questions.append(formatted)
        elif priority == "high":
            high_questions.append(formatted)
        else:
            other_questions.append(formatted)

    lines = []
    if critical_questions:
        lines.append("**CRITICAL PRIORITY - Must Address:**")
        lines.extend(critical_questions)

    if high_questions:
        lines.append("\n**HIGH PRIORITY:**")
        lines.extend(high_questions)

    if other_questions:
        lines.append("\n**Standard Questions:**")
        lines.extend(other_questions[:5])  # Limit other questions

    return f"""
FOLDER-SPECIFIC QUESTIONS FOR {folder_display.upper()}:
(These are targeted questions for documents in the {folder_category} folder)

{chr(10).join(lines)}

IMPORTANT: For each question you can address with this document, include the question
in your 'blueprint_question_answered' field so we can track question coverage.
"""


def _build_prioritized_questions_section(
    prioritized_questions: List[Dict],
    doc_type: str
) -> str:
    """Build questions section from prioritized questions (from question_prioritizer)."""

    # Map document types to relevant categories
    type_to_categories = {
        "constitutional": ["Corporate Governance", "Change of Control"],
        "governance": ["Corporate Governance"],
        "financial": ["Financial", "Tax"],
        "regulatory": ["Regulatory", "Environmental"],
        "employment": ["Employment", "Financial"],
        "contract": ["Contracts", "Change of Control"],
        "other": [],
    }

    relevant_categories = type_to_categories.get(doc_type, [])

    # Filter questions relevant to this document type
    # Always include Tier 1 and user-specified questions
    filtered_questions = []
    for q in prioritized_questions:
        tier = q.get("tier", 3)
        source = q.get("source", "")
        category = q.get("category", "")

        # Include if:
        # 1. Tier 1 (universal questions)
        # 2. User-specified (known_concern, critical_priority, deal_breaker)
        # 3. Category matches document type
        if tier == 1:
            filtered_questions.append(q)
        elif source in ["known_concern", "critical_priority", "deal_breaker"]:
            filtered_questions.append(q)
        elif category in relevant_categories:
            filtered_questions.append(q)
        elif not relevant_categories:  # For 'other' docs, include all
            filtered_questions.append(q)

    # Format questions by category
    questions_by_category: Dict[str, List[str]] = {}
    for q in filtered_questions[:50]:  # Limit to 50 questions per document
        category = q.get("category", "General")
        if category not in questions_by_category:
            questions_by_category[category] = []

        priority = q.get("priority", "medium")
        question_text = q.get("question", "")
        tier = q.get("tier", 3)

        # Format with priority marker
        if priority == "critical":
            marker = "[CRITICAL]"
        elif priority == "high":
            marker = "[HIGH]"
        else:
            marker = ""

        formatted = f"{marker} {question_text}".strip()
        questions_by_category[category].append(formatted)

    # Build output
    lines = []
    for category, qs in questions_by_category.items():
        lines.append(f"\n### {category}")
        for question in qs[:10]:  # Limit per category
            lines.append(f"- {question}")

    if not lines:
        return """
STANDARD QUESTIONS TO ADDRESS:
1. Does this document contain change of control provisions?
2. What consents are required for assignment or transfer?
3. Are there any financial exposures (penalties, damages, fees)?
"""

    return f"""
PRIORITIZED QUESTIONS TO ADDRESS:
(Answer these questions where relevant to this document - organized by importance)
{chr(10).join(lines)}
"""


def _build_deal_blockers_section(blueprint: Optional[Dict]) -> str:
    """Build deal blocker awareness section from blueprint."""
    if not blueprint or not blueprint.get("deal_blockers"):
        return """
DEAL BLOCKER AWARENESS:
Flag as DEAL_BLOCKER if you find:
- Missing required shareholder/board approval
- Untransferable rights or licenses without consent that cannot be obtained
- Material covenant breaches with acceleration notices
- Unresolved regulatory prohibitions
"""

    blockers = blueprint.get("deal_blockers", [])
    blocker_lines = []

    for blocker in blockers[:8]:
        desc = blocker.get("description", "")
        severity = blocker.get("severity", "conditional")
        consequence = blocker.get("consequence", "")

        if severity == "absolute":
            blocker_lines.append(f"- [ABSOLUTE] {desc}")
        else:
            blocker_lines.append(f"- [CONDITIONAL] {desc}")

        if consequence:
            blocker_lines.append(f"    Consequence: {consequence}")

    return f"""
DEAL BLOCKER DEFINITIONS FOR THIS TRANSACTION TYPE:
(Flag as DEAL_BLOCKER if any of these are present)

{chr(10).join(blocker_lines)}
"""


def _build_calculations_section(blueprint: Optional[Dict]) -> str:
    """Build calculation templates and structured extraction instructions from blueprint."""

    # Core extraction instructions - always included
    extraction_instructions = """
FINANCIAL EXPOSURE EXTRACTION (IMPORTANT):

When you identify a finding with quantifiable financial exposure, include a
structured "financial_extraction" block. DO NOT calculate the final amount yourself -
only extract the variables. The calculation engine will compute the result.

Formula Pattern IDs to use:
- PEN_001: volume × rate × period (e.g., liquidated damages per tonne/month)
- PEN_002: daily_rate × days (e.g., daily penalties)
- PEN_004: contract_value × percentage (e.g., 5% termination fee)
- EMP_001: monthly_salary × months (e.g., notice period severance)
- EMP_004: base × months + bonus + benefits (e.g., change of control package)
- EMP_005: unvested_units × unit_value (e.g., LTI acceleration)
- LSE_001: monthly_rent × remaining_months (e.g., lease obligation)
- LSE_003: production × rate_per_unit (e.g., royalty payments)
- ENV_001: area × rate_per_hectare (e.g., rehabilitation costs)
- ENV_002: required_provision - actual_provision (e.g., shortfall)
- DBT_001: principal × penalty_rate (e.g., prepayment penalty)
- DBT_002: outstanding × rate × days/365 (e.g., default interest)
- TXN_001: purchase_price × break_fee_percentage (e.g., break fee)

CRITICAL: Extract ONLY the raw values - do not perform arithmetic. The Python
calculation engine will perform all arithmetic to avoid errors.
"""

    calculation_templates = []

    if blueprint:
        # Extract calculations from risk categories
        for category in blueprint.get("risk_categories", []):
            for calc in category.get("calculations", []):
                name = calc.get("name", "")
                formula = calc.get("formula", calc.get("description", ""))
                calculation_templates.append(f"- {name}: {formula}")

    template_section = ""
    if calculation_templates:
        template_section = f"""
CALCULATION TEMPLATES FOR THIS TRANSACTION TYPE:
{chr(10).join(calculation_templates[:10])}
"""

    return f"""
{extraction_instructions}
{template_section}
"""


def _build_cot_questions_section(blueprint: Optional[Dict], doc_type: str) -> str:
    """
    Build Chain-of-Thought reasoning questions section based on document type.

    Maps document types to relevant CoT question categories from the blueprint.
    """
    if not blueprint or not blueprint.get("cot_questions"):
        return _get_default_cot_questions(doc_type)

    cot_questions = blueprint.get("cot_questions", {})

    # Map document types to relevant CoT question categories
    # NOTE: Category names must match those in the blueprint's cot_questions section
    doc_type_to_categories = {
        "constitutional": ["change_of_control", "ownership_regulatory", "bee_mining_charter"],
        "governance": ["change_of_control", "ownership_regulatory"],
        "mining_right": ["mining_rights"],
        "regulatory": ["mining_rights", "environmental"],
        "environmental": ["environmental"],
        "financial": ["financial_banking", "ownership_regulatory"],  # Added ownership for BEE verification
        "banking": ["financial_banking"],
        "contract": ["offtake_contracts", "change_of_control"],
        "offtake": ["offtake_contracts", "change_of_control"],
        "lease": ["change_of_control"],
        "property": ["change_of_control"],
        "employment": ["change_of_control"],
        "bee": ["ownership_regulatory", "bee_mining_charter"],
        "slp": ["mining_rights", "bee_mining_charter"],
        "shareholder": ["ownership_regulatory", "bee_mining_charter", "change_of_control"],
        "other": ["change_of_control"],
    }

    # Get relevant categories for this document type
    relevant_categories = doc_type_to_categories.get(doc_type.lower(), ["change_of_control"])

    # Always include change_of_control as it applies broadly
    if "change_of_control" not in relevant_categories:
        relevant_categories.append("change_of_control")

    # Build questions section
    questions_lines = []
    for category in relevant_categories:
        cat_questions = cot_questions.get(category, [])
        if cat_questions:
            # Format category name nicely
            cat_display = category.replace("_", " ").title()
            questions_lines.append(f"\n**{cat_display} - Reasoning Questions:**")
            for q in cat_questions:
                questions_lines.append(f"- {q}")

    if not questions_lines:
        return _get_default_cot_questions(doc_type)

    return f"""
CHAIN-OF-THOUGHT REASONING QUESTIONS FOR THIS DOCUMENT:
(Answer these questions as part of your reasoning for each finding)
{chr(10).join(questions_lines)}
"""


def _get_default_cot_questions(doc_type: str) -> str:
    """Return default CoT questions when blueprint doesn't have specific ones."""

    # Default questions that apply to most document types
    default_questions = {
        "contract": """
CHAIN-OF-THOUGHT REASONING QUESTIONS:
- What is the exact CoC/assignment restriction language in this contract?
- Does a 100% share sale trigger this provision?
- What is the commercial value of this contract to the business?
- Is termination automatic or discretionary upon CoC?
- Can consent realistically be obtained? What leverage does counterparty have?
- What are the financial consequences (liquidated damages, lost revenue)?
""",
        "financial": """
CHAIN-OF-THOUGHT REASONING QUESTIONS:
- What is the exact CoC/event of default trigger language?
- What covenants exist and are they currently in compliance?
- Does the transaction trigger mandatory prepayment or acceleration?
- What is the total exposure (principal + interest + fees)?
- Are there cross-default provisions?
- What are refinancing options and break costs?

═══════════════════════════════════════════════════════════════════════════════
MANDATORY FINANCIAL TREND ANALYSIS - YOU MUST CREATE FINDINGS FOR EACH:
═══════════════════════════════════════════════════════════════════════════════

For Annual Financial Statements, you MUST analyze and create findings for:

1. **REVENUE TREND** (CREATE FINDING IF DECLINE >5%):
   - Extract: Current year revenue, Prior year revenue
   - Calculate: Change % = ((Current - Prior) / Prior) × 100
   - Output format: "Revenue declined from R[X]M to R[Y]M ([Z]% decrease)"
   - SEVERITY: critical if >15% decline, high if >10%, medium if >5%

2. **MARGIN ANALYSIS** (CREATE FINDING IF COMPRESSION >3pp):
   - Gross margin = Gross Profit / Revenue × 100
   - Operating margin = Operating Profit / Revenue × 100
   - Net margin = Net Profit / Revenue × 100
   - Calculate for BOTH years and show change in percentage points
   - Output: "Operating margin collapsed from [X]% to [Y]% (-[Z] percentage points)"
   - SEVERITY: critical if margin now <5% OR compression >8pp

3. **CASH POSITION** (CREATE FINDING IF DECLINE >30%):
   - Extract: Cash & equivalents for both years
   - Calculate: % change
   - Output: "Cash depleted from R[X]M to R[Y]M ([Z]% decrease)"
   - SEVERITY: high if >50% decline

4. **WORKING CAPITAL** (CREATE FINDING IF NEGATIVE):
   - Calculate: Current Assets - Current Liabilities
   - SEVERITY: critical if negative working capital

5. **GOING CONCERN** (CREATE FINDING IF ANY INDICATORS):
   - Check for audit qualifications, emphasis of matter
   - Accumulated losses > share capital
   - Negative operating cash flow
   - SEVERITY: critical - always flag going concern

═══════════════════════════════════════════════════════════════════════════════
MANDATORY GOVERNANCE CHECKS - YOU MUST CREATE FINDINGS FOR EACH:
═══════════════════════════════════════════════════════════════════════════════

6. **BONUSES IN LOSS YEAR** (CREATE FINDING IF FOUND):
   - Check: Were bonuses/incentives paid in a year the company made a loss?
   - Look for: Director remuneration, executive bonuses, performance payments
   - If company made net loss but bonuses were paid:
     Output: "R[X]M in bonuses/incentives paid despite net loss of R[Y]M"
   - SEVERITY: high - governance red flag

7. **RELATED PARTY TRANSACTIONS DURING DISTRESS** (CREATE FINDING IF FOUND):
   - Check: Were related party payments made while company was in financial distress?
   - Look for: Management fees, consulting fees, loans to related parties
   - Output: "Related party payments of R[X]M during period of [financial distress indicator]"
   - SEVERITY: high - governance red flag

8. **DIRECTOR LOANS OR DRAWINGS** (CREATE FINDING IF >R500K):
   - Check: Loans to directors, shareholder accounts
   - Output: "Director/shareholder loan accounts totaling R[X]M"
   - SEVERITY: medium if secured, high if unsecured
""",
        "regulatory": """
CHAIN-OF-THOUGHT REASONING QUESTIONS:
- What is the current status of this authorization/license?
- What conditions are attached and are they being complied with?
- Does the transaction require regulatory consent?
- What is the typical processing time for consent?
- What happens if consent is refused or delayed?
- What are the compliance costs and penalties for non-compliance?
""",
        "employment": """
CHAIN-OF-THOUGHT REASONING QUESTIONS:
- What are the CoC provisions in this contract?
- What is the severance exposure on CoC?
- Are there key person dependencies?
- What retention arrangements exist?
- Are there any pending disputes or issues?
""",
    }

    # Match doc_type to closest default
    for key in default_questions:
        if key in doc_type.lower():
            return default_questions[key]

    # Generic fallback
    return """
CHAIN-OF-THOUGHT REASONING QUESTIONS:
- What specific clause or provision triggers concern?
- What is the commercial significance of this issue?
- How does this interact with a 100% share sale / change of control?
- What is the worst-case scenario if this issue is not addressed?
- Can this be resolved before closing? Who needs to act?
- What is the financial exposure? Show your calculation.
"""
