# claude_synthesis.py - Call Claude for report synthesis (ONE call with all data)

import logging
import json
import os
from typing import List, Dict, Any

# Use the shared Claude LLM adapter
from shared.dev_adapters.claude_llm import call_llm_with


def get_status_value(status) -> str:
    """Safely get status string from status field (may be enum or string)."""
    if status is None:
        return 'New'
    if hasattr(status, 'value'):
        return status.value
    return str(status)


def get_severity_from_status(status) -> str:
    """Map status (Red/Amber/Green) to severity (High/Medium/Low)."""
    status_str = get_status_value(status)
    mapping = {
        'Red': 'High',
        'Amber': 'Medium',
        'Green': 'Low',
        'Info': 'Low',
        'New': 'Medium'
    }
    return mapping.get(status_str, 'Medium')


SYNTHESIS_PROMPT = """You are a senior legal analyst preparing a due diligence report synthesis.

TRANSACTION DETAILS:
- Project Name: {dd_name}
- Transaction Type: {transaction_type}
- Briefing: {briefing}

DOCUMENTS REVIEWED ({doc_count}):
{doc_list}

RISK FINDINGS ({finding_count} total):
{findings_summary}

TASK: Generate a comprehensive synthesis for the DD report. This will be used to populate a professional Word document.

KEY FIELD DEFINITIONS:
- category: The risk category (e.g., Financial, Legal, Operational)
- detail: The due diligence question or risk title from the perspective
- phrase: The specific clause or text found in the document
- status: Risk severity indicator (Red=critical/high, Amber=material/medium, Green=low risk)
- document_name: Source document where finding was identified
- page_number: Page reference in the source document
- requires_action: Whether this finding needs follow-up action

Provide your response in the following JSON structure:

{{
    "executive_summary": {{
        "overview": "2-3 paragraph executive overview of the DD findings",
        "key_findings": ["List of 5-7 most critical findings across all categories"],
        "risk_profile": "Overall risk assessment (High/Medium/Low) with justification"
    }},
    "statistics": {{
        "total_documents": {doc_count},
        "total_findings": {finding_count},
        "high_risk_count": <count of Red/High severity findings>,
        "medium_risk_count": <count of Amber/Medium severity findings>,
        "low_risk_count": <count of Green/Low severity findings>,
        "action_required_count": <count of findings requiring action>
    }},
    "category_summaries": {{
        "<category_name>": {{
            "summary": "1-2 sentence summary of risks in this category",
            "key_issues": ["List of main issues"],
            "recommendation": "Specific recommendation for this category"
        }}
    }},
    "action_items": [
        {{
            "priority": "high|medium|low",
            "description": "Action item description",
            "category": "Related category",
            "source": "Source document name"
        }}
    ],
    "conclusion": {{
        "overall_assessment": "2-3 paragraph overall assessment and deal impact analysis",
        "recommendations": ["List of 3-5 key recommendations"],
        "next_steps": ["List of suggested next steps"]
    }}
}}

Be thorough but concise. Focus on actionable insights. Respond ONLY with valid JSON."""


def get_report_synthesis(
    dd_name: str,
    transaction_type: str,
    findings: List[Dict],
    documents: List[str],
    briefing: str = ""
) -> Dict[str, Any]:
    """
    Call Claude ONCE to synthesize all findings into a cohesive report structure.

    This is the SINGLE Claude call for the entire report - it aggregates and
    synthesizes all the individual findings into executive summary, category
    summaries, action items, and conclusions.

    The findings dict has these keys (from __init__.py mapping):
    - category: Risk category (from perspective_risk.category)
    - detail: Risk title/question (from perspective_risk.detail)
    - severity: Mapped severity (High/Medium/Low from status)
    - status: Raw status (Red/Amber/Green/New/Info)
    - phrase: The finding text/clause
    - page_number: Page in document
    - document_name: Source document name
    - requires_action: Boolean
    - action_priority: Priority if action required
    - direct_answer: Answer to the DD question
    - evidence_quote: Supporting quote
    """

    logging.info(f"[claude_synthesis] Generating synthesis for {len(findings)} findings")

    # Prepare document list
    doc_list = "\n".join([f"- {doc}" for doc in documents[:50]])  # Limit to 50 docs
    if len(documents) > 50:
        doc_list += f"\n... and {len(documents) - 50} more documents"

    # Prepare findings summary grouped by category
    categories = {}
    for f in findings:
        cat = f.get('category', 'Uncategorized') or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)

    findings_summary_parts = []
    for cat, cat_findings in categories.items():
        # Count by severity (already mapped in __init__.py)
        high = sum(1 for f in cat_findings if f.get('severity') == 'High')
        medium = sum(1 for f in cat_findings if f.get('severity') == 'Medium')
        low = sum(1 for f in cat_findings if f.get('severity') == 'Low')

        findings_summary_parts.append(f"\n## {cat} ({len(cat_findings)} findings: {high} High, {medium} Medium, {low} Low)")

        # Include top findings from each category
        for f in cat_findings[:5]:  # Limit to 5 per category for context
            severity = f.get('severity', 'Medium')
            status = get_status_value(f.get('status', 'New'))
            # Use 'detail' for the risk question/title, 'phrase' for the actual finding text
            risk_title = f.get('detail', '') or 'Unspecified Risk'
            finding_text = f.get('phrase', '') or ''
            doc_name = f.get('document_name', 'Unknown') or 'Unknown'
            page = f.get('page_number', '')

            # Build a clear finding description
            finding_desc = risk_title[:150]
            if finding_text and finding_text != risk_title:
                finding_desc += f" - '{finding_text[:100]}'"

            page_ref = f" (p.{page})" if page else ""
            findings_summary_parts.append(f"  - [{severity}/{status}] {finding_desc} (Source: {doc_name[:40]}{page_ref})")

        if len(cat_findings) > 5:
            findings_summary_parts.append(f"  ... and {len(cat_findings) - 5} more findings in this category")

    findings_summary = "\n".join(findings_summary_parts)

    # Calculate statistics for prompt (severity already mapped in __init__.py)
    high_count = sum(1 for f in findings if f.get('severity') == 'High')
    medium_count = sum(1 for f in findings if f.get('severity') == 'Medium')
    low_count = sum(1 for f in findings if f.get('severity') == 'Low')
    action_count = sum(1 for f in findings if f.get('requires_action'))

    # Build the prompt
    prompt = SYNTHESIS_PROMPT.format(
        dd_name=dd_name,
        transaction_type=transaction_type,
        briefing=briefing or "No specific briefing provided",
        doc_count=len(documents),
        doc_list=doc_list,
        finding_count=len(findings),
        findings_summary=findings_summary
    )

    messages = [
        {"role": "system", "content": "You are a senior legal due diligence analyst. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = call_llm_with(
            messages=messages,
            temperature=0.3,  # Slightly higher for more natural prose
            max_tokens=4000
        )

        # Parse JSON from response
        start = response.find('{')
        end = response.rfind('}') + 1

        if start != -1 and end > start:
            json_str = response[start:end]
            synthesis = json.loads(json_str)

            # Ensure statistics are populated even if Claude didn't calculate them
            if 'statistics' not in synthesis:
                synthesis['statistics'] = {}

            synthesis['statistics']['total_documents'] = len(documents)
            synthesis['statistics']['total_findings'] = len(findings)
            synthesis['statistics']['high_risk_count'] = high_count
            synthesis['statistics']['medium_risk_count'] = medium_count
            synthesis['statistics']['low_risk_count'] = low_count
            synthesis['statistics']['action_required_count'] = action_count

            logging.info("[claude_synthesis] Synthesis generated successfully")
            return synthesis
        else:
            logging.warning("[claude_synthesis] No JSON found in response, using defaults")
            return get_default_synthesis(dd_name, findings, documents)

    except json.JSONDecodeError as e:
        logging.error(f"[claude_synthesis] JSON parse error: {e}")
        return get_default_synthesis(dd_name, findings, documents)
    except Exception as e:
        logging.error(f"[claude_synthesis] Error: {e}")
        return get_default_synthesis(dd_name, findings, documents)


def get_default_synthesis(dd_name: str, findings: List[Dict], documents: List[str]) -> Dict[str, Any]:
    """
    Generate default synthesis structure when Claude call fails.
    Uses the findings data to populate basic statistics and summaries.
    """

    # Calculate statistics using mapped severity field
    high_count = sum(1 for f in findings if f.get('severity') == 'High')
    medium_count = sum(1 for f in findings if f.get('severity') == 'Medium')
    low_count = sum(1 for f in findings if f.get('severity') == 'Low')
    action_count = sum(1 for f in findings if f.get('requires_action'))

    # Get top high-risk findings - use 'detail' for risk title, 'phrase' for finding text
    high_findings = [f for f in findings if f.get('severity') == 'High']
    key_findings = []
    for f in high_findings[:5]:
        risk_title = f.get('detail', '') or ''
        phrase = f.get('phrase', '') or ''
        # Prefer detail (risk question) but fall back to phrase
        text = risk_title if risk_title else phrase
        if text:
            key_findings.append(text[:100])

    if not key_findings:
        key_findings = ["No critical findings identified"]

    # Determine overall risk profile
    if high_count >= 5:
        risk_profile = "High - Multiple critical issues identified requiring immediate attention"
    elif high_count >= 1:
        risk_profile = "Medium-High - Some critical issues identified that require attention"
    elif medium_count >= 5:
        risk_profile = "Medium - Several notable concerns identified"
    else:
        risk_profile = "Low - No significant issues identified"

    # Build category summaries
    categories = {}
    for f in findings:
        cat = f.get('category', 'Uncategorized') or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)

    category_summaries = {}
    for cat, cat_findings in categories.items():
        high = sum(1 for f in cat_findings if f.get('severity') == 'High')
        # Get key issues from detail field
        key_issues = []
        for f in cat_findings[:3]:
            detail = f.get('detail', '') or f.get('phrase', '') or ''
            if detail:
                key_issues.append(detail[:100])

        category_summaries[cat] = {
            "summary": f"{len(cat_findings)} findings identified in {cat} ({high} high risk)",
            "key_issues": key_issues if key_issues else ["Review findings in this category"],
            "recommendation": "Review findings and assess impact on transaction"
        }

    # Build action items from high-risk findings
    action_items = []
    for f in high_findings[:10]:
        detail = f.get('detail', '') or f.get('phrase', '') or 'Review this finding'
        action_items.append({
            "priority": "high",
            "description": detail[:150],
            "category": f.get('category', 'General') or 'General',
            "source": (f.get('document_name', 'Unknown') or 'Unknown')[:50]
        })

    return {
        "executive_summary": {
            "overview": f"This due diligence report presents findings from the review of {dd_name}. "
                       f"A total of {len(documents)} documents were analyzed, yielding {len(findings)} findings. "
                       f"Of these, {high_count} are classified as high risk (Red), {medium_count} as medium risk (Amber), "
                       f"and {low_count} as low risk (Green).",
            "key_findings": key_findings,
            "risk_profile": risk_profile
        },
        "statistics": {
            "total_documents": len(documents),
            "total_findings": len(findings),
            "high_risk_count": high_count,
            "medium_risk_count": medium_count,
            "low_risk_count": low_count,
            "action_required_count": action_count
        },
        "category_summaries": category_summaries,
        "action_items": action_items,
        "conclusion": {
            "overall_assessment": f"Based on the review of {len(documents)} documents, we have identified "
                                 f"{len(findings)} findings that require attention. The overall risk profile "
                                 f"is {risk_profile.split(' - ')[0]}. Further analysis may be required for "
                                 f"specific areas flagged as high risk.",
            "recommendations": [
                "Review all high-risk (Red) findings with legal counsel",
                "Address medium-risk (Amber) items in transaction documentation",
                "Consider further investigation of flagged regulatory matters",
                "Update due diligence checklist based on findings"
            ],
            "next_steps": [
                "Complete review of any outstanding documents",
                "Discuss findings with transaction team",
                "Prepare queries for counterparty on flagged issues",
                "Consider additional specialist reviews if warranted"
            ]
        }
    }
