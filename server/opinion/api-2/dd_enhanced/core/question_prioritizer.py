"""
Question prioritization to reduce token usage.

Instead of running all 758+ blueprint questions, we:
1. Always run Tier 1 (critical) questions - ~25 universal questions
2. Run transaction-type specific critical/high priority questions - ~50-100 questions
3. Skip Tier 3 (deep dive) unless specifically requested

Result: ~85% reduction in questions processed while maintaining quality
on the issues that actually matter for deal decisions.

Tier Strategy:
- Tier 1: Universal questions every DD must answer (deal blockers, CoC, consents)
- Tier 2: Transaction-specific critical/high priority questions from blueprint
- Tier 3: Comprehensive deep-dive questions (only on request)
"""

from typing import Dict, List, Optional, Set, Any


# Tier 1: Always run these questions regardless of transaction type
# These are the must-answer questions for any M&A transaction
TIER1_UNIVERSAL_QUESTIONS = [
    # Corporate Governance (always critical)
    {
        "question": "Is shareholder approval required for this transaction? If so, has it been obtained?",
        "category": "Corporate Governance",
        "priority": "critical",
        "expected_finding": "Clear confirmation of approval status",
    },
    {
        "question": "What transfer restrictions apply to the shares being acquired?",
        "category": "Corporate Governance",
        "priority": "critical",
        "expected_finding": "List of any pre-emptive rights, tag-along, drag-along",
    },
    {
        "question": "Are there any drag-along or tag-along rights that affect this transaction?",
        "category": "Corporate Governance",
        "priority": "critical",
        "expected_finding": "Details of rights and whether they are triggered",
    },
    {
        "question": "Does the Board Resolution properly authorize the transaction?",
        "category": "Corporate Governance",
        "priority": "critical",
        "expected_finding": "Confirmation of proper authorization scope",
    },

    # Change of Control (always critical)
    {
        "question": "Are there change of control provisions that are triggered by this transaction?",
        "category": "Change of Control",
        "priority": "critical",
        "expected_finding": "List of all CoC triggers and consequences",
    },
    {
        "question": "What consents are required from third parties for this transaction?",
        "category": "Change of Control",
        "priority": "critical",
        "expected_finding": "Complete consent matrix",
    },
    {
        "question": "What are the consequences of not obtaining required consents?",
        "category": "Change of Control",
        "priority": "critical",
        "expected_finding": "Termination rights, acceleration, damages",
    },
    {
        "question": "What is the longest notice period required across all CoC clauses?",
        "category": "Change of Control",
        "priority": "high",
        "expected_finding": "Critical path timeline",
    },

    # Financial (always critical)
    {
        "question": "What is the total debt outstanding and is lender consent required?",
        "category": "Financial",
        "priority": "critical",
        "expected_finding": "Total debt and consent requirements",
    },
    {
        "question": "Are there any financial covenant breaches or defaults?",
        "category": "Financial",
        "priority": "critical",
        "expected_finding": "Covenant compliance status",
    },
    {
        "question": "What contingent liabilities exist that are not on the balance sheet?",
        "category": "Financial",
        "priority": "high",
        "expected_finding": "Off-balance-sheet exposures",
    },
    {
        "question": "What is the total severance exposure on change of control?",
        "category": "Financial",
        "priority": "high",
        "expected_finding": "Quantified severance liability",
    },

    # Regulatory (always critical)
    {
        "question": "Are all material licenses and permits valid and in good standing?",
        "category": "Regulatory",
        "priority": "critical",
        "expected_finding": "Confirmation of license validity",
    },
    {
        "question": "Are there any pending regulatory investigations or enforcement actions?",
        "category": "Regulatory",
        "priority": "critical",
        "expected_finding": "Disclosure of any pending matters",
    },
    {
        "question": "Is regulatory approval required for this transaction?",
        "category": "Regulatory",
        "priority": "critical",
        "expected_finding": "List of required approvals",
    },

    # Contracts (always important)
    {
        "question": "What are the material contracts and do any have change of control provisions?",
        "category": "Contracts",
        "priority": "critical",
        "expected_finding": "Material contract list with CoC analysis",
    },
    {
        "question": "What is the total liquidated damages exposure across all contracts?",
        "category": "Contracts",
        "priority": "high",
        "expected_finding": "Quantified LD exposure",
    },
    {
        "question": "Are there any contracts with exclusivity or non-compete provisions?",
        "category": "Contracts",
        "priority": "high",
        "expected_finding": "Restrictions that could affect buyer",
    },

    # Litigation & Disputes
    {
        "question": "Are there any material pending or threatened legal proceedings?",
        "category": "Litigation",
        "priority": "critical",
        "expected_finding": "List of material litigation",
    },
    {
        "question": "Are there any unresolved disputes with employees, customers, or suppliers?",
        "category": "Litigation",
        "priority": "high",
        "expected_finding": "Disclosure of disputes",
    },

    # Environmental (always important for industrial)
    {
        "question": "Are all environmental permits and authorizations current?",
        "category": "Environmental",
        "priority": "high",
        "expected_finding": "Permit validity confirmation",
    },
    {
        "question": "What is the total environmental rehabilitation liability?",
        "category": "Environmental",
        "priority": "high",
        "expected_finding": "Quantified rehab liability",
    },
    {
        "question": "Are there any pending environmental compliance issues?",
        "category": "Environmental",
        "priority": "high",
        "expected_finding": "Compliance status",
    },

    # Tax
    {
        "question": "Are there any outstanding tax disputes or assessments?",
        "category": "Tax",
        "priority": "high",
        "expected_finding": "Tax dispute disclosure",
    },
    {
        "question": "Are all tax returns filed and taxes paid?",
        "category": "Tax",
        "priority": "high",
        "expected_finding": "Tax compliance confirmation",
    },
]


def prioritize_questions(
    blueprint: Optional[Dict] = None,
    transaction_context: Optional[Dict] = None,
    include_tier3: bool = False,
    max_questions: int = 150
) -> List[Dict]:
    """
    Filter and prioritize blueprint questions.

    Args:
        blueprint: Transaction-type blueprint
        transaction_context: Optional context with known_concerns, focus_areas
        include_tier3: Whether to include deep-dive (low priority) questions
        max_questions: Maximum questions to return

    Returns:
        Prioritized list of questions with tier and priority info
    """
    prioritized = []
    seen_questions: Set[str] = set()

    # Tier 1: Universal questions (always include)
    for q in TIER1_UNIVERSAL_QUESTIONS:
        question_text = q["question"]
        if question_text.lower() not in seen_questions:
            prioritized.append({
                "question": question_text,
                "tier": 1,
                "priority": q.get("priority", "critical"),
                "category": q.get("category", "General"),
                "detail": "",
                "expected_finding": q.get("expected_finding", ""),
                "source": "universal"
            })
            seen_questions.add(question_text.lower())

    # Tier 2: Blueprint-specific critical and high priority questions
    if blueprint:
        for risk_category in blueprint.get("risk_categories", []):
            category_name = risk_category.get("name", "General")
            category_weight = risk_category.get("weight", "medium")

            for question in risk_category.get("standard_questions", []):
                q_text = question.get("question", "")
                q_priority = question.get("priority", "medium")

                if q_text.lower() in seen_questions:
                    continue

                # Include if critical or high priority, or if category is critical
                include = False
                if q_priority in ["critical", "high"]:
                    include = True
                elif category_weight == "critical":
                    include = True
                elif include_tier3 and q_priority == "medium":
                    include = True

                if include:
                    prioritized.append({
                        "question": q_text,
                        "tier": 2 if q_priority in ["critical", "high"] else 3,
                        "priority": q_priority,
                        "category": category_name,
                        "detail": question.get("detail", ""),
                        "expected_finding": question.get("expected_finding", ""),
                        "source": "blueprint"
                    })
                    seen_questions.add(q_text.lower())

    # Add transaction-specific focus areas if provided
    if transaction_context:
        # Known concerns become critical questions
        for concern in transaction_context.get("known_concerns", []):
            if isinstance(concern, str) and concern.strip():
                q_text = f"What are the risks and issues related to: {concern}?"
                if q_text.lower() not in seen_questions:
                    prioritized.append({
                        "question": q_text,
                        "tier": 1,
                        "priority": "critical",
                        "category": "User Specified",
                        "detail": f"User flagged this as a known concern: {concern}",
                        "expected_finding": "Detailed analysis of this specific concern",
                        "source": "known_concern"
                    })
                    seen_questions.add(q_text.lower())

        # Critical priorities from wizard
        for priority in transaction_context.get("critical_priorities", []):
            if isinstance(priority, str) and priority.strip():
                q_text = f"What is the status and any issues with: {priority}?"
                if q_text.lower() not in seen_questions:
                    prioritized.append({
                        "question": q_text,
                        "tier": 1,
                        "priority": "critical",
                        "category": "User Specified",
                        "detail": f"User flagged this as critical priority: {priority}",
                        "expected_finding": "Status and issues for this priority area",
                        "source": "critical_priority"
                    })
                    seen_questions.add(q_text.lower())

        # Known deal breakers
        for blocker in transaction_context.get("known_deal_breakers", []):
            if isinstance(blocker, str) and blocker.strip():
                q_text = f"Is there evidence of the following potential deal breaker: {blocker}?"
                if q_text.lower() not in seen_questions:
                    prioritized.append({
                        "question": q_text,
                        "tier": 1,
                        "priority": "critical",
                        "category": "Deal Breakers",
                        "detail": f"User flagged as potential deal breaker: {blocker}",
                        "expected_finding": "Confirmation or denial with evidence",
                        "source": "deal_breaker"
                    })
                    seen_questions.add(q_text.lower())

    # Sort by tier, then priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    prioritized.sort(key=lambda x: (x["tier"], priority_order.get(x["priority"], 4)))

    # Limit to max questions
    return prioritized[:max_questions]


def get_questions_for_document_type(
    questions: List[Dict],
    doc_type: str
) -> List[Dict]:
    """
    Filter questions relevant to a specific document type.

    Args:
        questions: Full prioritized question list
        doc_type: Document type (constitutional, governance, financial, etc.)

    Returns:
        Questions relevant to this document type
    """
    # Map document types to relevant categories
    type_to_categories = {
        "constitutional": ["Corporate Governance", "Change of Control"],
        "governance": ["Corporate Governance"],
        "financial": ["Financial", "Tax"],
        "regulatory": ["Regulatory", "Environmental"],
        "employment": ["Employment", "Financial"],
        "contract": ["Contracts", "Change of Control"],
        "other": [],  # Will get universal questions only
    }

    relevant_categories = type_to_categories.get(doc_type, [])

    # Always include universal questions and user-specified
    filtered = [
        q for q in questions
        if q["source"] in ["universal", "known_concern", "critical_priority", "deal_breaker"]
        or q["category"] in relevant_categories
        or q["tier"] == 1  # All tier 1 questions
    ]

    return filtered


def get_question_count_by_tier(questions: List[Dict]) -> Dict[str, int]:
    """Return count of questions by tier."""
    counts = {
        "tier1": 0,
        "tier2": 0,
        "tier3": 0,
        "total": len(questions),
        "by_category": {},
        "by_source": {}
    }

    for q in questions:
        tier = f"tier{q.get('tier', 3)}"
        counts[tier] = counts.get(tier, 0) + 1

        category = q.get("category", "Other")
        counts["by_category"][category] = counts["by_category"].get(category, 0) + 1

        source = q.get("source", "unknown")
        counts["by_source"][source] = counts["by_source"].get(source, 0) + 1

    return counts


def format_questions_for_prompt(
    questions: List[Dict],
    include_details: bool = True,
    max_questions: int = 50
) -> str:
    """
    Format questions for inclusion in a Claude prompt.

    Args:
        questions: List of question dicts
        include_details: Whether to include detail hints
        max_questions: Maximum questions to include

    Returns:
        Formatted string for prompt injection
    """
    lines = []
    current_category = None

    for q in questions[:max_questions]:
        category = q.get("category", "General")

        # Add category header if changed
        if category != current_category:
            if current_category is not None:
                lines.append("")  # Blank line between categories
            lines.append(f"### {category}")
            current_category = category

        # Format question with priority indicator
        priority = q.get("priority", "medium")
        priority_marker = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "",
            "low": ""
        }.get(priority, "")

        question_line = f"- {priority_marker} {q['question']}".strip()
        lines.append(question_line)

        # Add detail hint if available
        if include_details and q.get("detail"):
            lines.append(f"  (Hint: {q['detail'][:100]})")

    return "\n".join(lines)


def get_summary(questions: List[Dict]) -> Dict[str, Any]:
    """
    Get a summary of the prioritized questions.

    Returns:
        Summary dict with counts and breakdown
    """
    counts = get_question_count_by_tier(questions)

    return {
        "total_questions": counts["total"],
        "tier1_count": counts["tier1"],
        "tier2_count": counts["tier2"],
        "tier3_count": counts["tier3"],
        "categories": list(counts["by_category"].keys()),
        "category_breakdown": counts["by_category"],
        "source_breakdown": counts["by_source"],
        "estimated_token_reduction": f"{max(0, 100 - (counts['total'] / 7.58)):.0f}%"  # vs 758 full questions
    }
