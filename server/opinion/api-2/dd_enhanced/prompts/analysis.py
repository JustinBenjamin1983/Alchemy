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
    """
    transaction_type = blueprint.get("transaction_type", "corporate acquisition") if blueprint else "corporate acquisition"
    jurisdiction = blueprint.get("jurisdiction", "South Africa") if blueprint else "South Africa"

    legislation = ""
    if blueprint and blueprint.get("primary_legislation"):
        legislation = "\n\nKey legislation to consider:\n" + "\n".join(
            f"- {leg}" for leg in blueprint.get("primary_legislation", [])[:5]
        )

    return f"""You are a senior M&A lawyer conducting legal due diligence for a {transaction_type}.

Jurisdiction: {jurisdiction}{legislation}

Your task is to identify risks, issues, and concerns that could affect the transaction.

Be thorough but precise. Classify each finding by:
1. Severity: critical, high, medium, low
2. Deal Impact: deal_blocker, condition_precedent, price_chip, warranty_indemnity, post_closing, noted

A "deal_blocker" means the transaction CANNOT close without resolution.
A "condition_precedent" means it must be resolved before closing but is resolvable.
A "price_chip" affects the purchase price or requires indemnity protection.

Always cite the specific clause reference when identifying an issue.
When calculating financial exposures, SHOW YOUR WORKING (e.g., "24 months × R3.2M/month = R77M")."""


# Legacy constant for backwards compatibility
ANALYSIS_SYSTEM_PROMPT = get_analysis_system_prompt()


def build_analysis_prompt(
    document_text: str,
    document_name: str,
    doc_type: str,
    reference_docs_text: str,
    transaction_context: str,
    blueprint: Optional[Dict] = None,
    prioritized_questions: Optional[List[Dict]] = None
) -> str:
    """
    Build the analysis prompt for a single document.

    KEY IMPROVEMENTS:
    1. Reference documents (MOI, SHA) are always included for validation
    2. Blueprint questions are injected to guide specific analysis
    3. Deal blocker definitions from blueprint are included
    4. Financial calculation templates are provided
    5. Prioritized questions from question_prioritizer take precedence
    """

    # Build questions section - use prioritized questions if available
    questions_section = _build_questions_section(blueprint, doc_type, prioritized_questions)

    # Build deal blocker awareness section
    deal_blockers_section = _build_deal_blockers_section(blueprint)

    # Build calculation templates section
    calculations_section = _build_calculations_section(blueprint)

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

Conduct a thorough analysis and identify ALL issues. For each issue found, classify:

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
            "category": "change_of_control|consent|financial|covenant|governance|employment|regulatory|contractual",
            "description": "Clear description of the issue",
            "clause_reference": "Clause X.X",
            "evidence_quote": "Exact quote from document (max 200 chars)",
            "severity": "critical|high|medium|low",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|warranty_indemnity|post_closing|noted",
            "financial_exposure": {{
                "amount": number or null,
                "currency": "ZAR",
                "calculation": "Show your working: e.g., 24 months × R3.2M = R77M",
                "type": "liquidated_damages|acceleration|penalty|fee"
            }},
            "action_required": "What needs to be done to address this",
            "responsible_party": "buyer|seller|third_party",
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
    prioritized_questions: Optional[List[Dict]] = None
) -> str:
    """Build the questions section from prioritized questions or blueprint."""

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

        # Include all questions for critical categories
        weight = category.get("weight", "medium")
        if weight in ["critical", "high"]:
            for q in category.get("standard_questions", [])[:10]:  # Limit per category
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
            if q.get("priority") in ["critical", "high"]:
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
    """Build calculation templates from blueprint."""
    if not blueprint:
        return """
FINANCIAL CALCULATIONS:
When you identify a financial exposure, CALCULATE THE AMOUNT:
- Liquidated damages: X months × monthly value
- Debt acceleration: Total outstanding principal + accrued interest
- Termination penalties: As specified in contract
- Severance: Notice period + bonus + benefits

ALWAYS SHOW YOUR WORKING in the calculation field.
"""

    calculation_templates = []

    # Extract calculations from risk categories
    for category in blueprint.get("risk_categories", []):
        for calc in category.get("calculations", []):
            name = calc.get("name", "")
            formula = calc.get("formula", calc.get("description", ""))
            calculation_templates.append(f"- {name}: {formula}")

    if not calculation_templates:
        return """
FINANCIAL CALCULATIONS:
When you identify a financial exposure, CALCULATE THE AMOUNT:
- Liquidated damages: X months × monthly value
- Debt acceleration: Total outstanding principal + accrued interest
ALWAYS SHOW YOUR WORKING.
"""

    return f"""
FINANCIAL CALCULATION TEMPLATES:
(Use these formulas when calculating exposures)

{chr(10).join(calculation_templates[:10])}

ALWAYS SHOW YOUR WORKING in the calculation field.
"""
