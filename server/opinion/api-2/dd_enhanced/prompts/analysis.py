"""
Pass 2: Per-Document Analysis prompts.

These prompts analyze each document for risks and issues,
with reference documents (MOI, SHA) always in context.
"""

ANALYSIS_SYSTEM_PROMPT = """You are a senior M&A lawyer conducting legal due diligence for an acquisition.

You are analyzing documents for a proposed 100% share sale transaction.
Your task is to identify risks, issues, and concerns that could affect the transaction.

Be thorough but precise. Classify each finding by:
1. Severity: critical, high, medium, low
2. Deal Impact: deal_blocker, condition_precedent, price_chip, warranty_indemnity, post_closing, noted

A "deal_blocker" means the transaction CANNOT close without resolution.
A "condition_precedent" means it must be resolved before closing but is resolvable.
A "price_chip" affects the purchase price or requires indemnity protection.

Always cite the specific clause reference when identifying an issue."""


def build_analysis_prompt(
    document_text: str,
    document_name: str,
    doc_type: str,
    reference_docs_text: str,
    transaction_context: str
) -> str:
    """
    Build the analysis prompt for a single document.

    KEY IMPROVEMENT: Reference documents (MOI, SHA) are always included
    so the analysis can validate against constitutional requirements.
    """

    return f"""Analyze this document for a 100% share acquisition transaction.

TRANSACTION CONTEXT:
{transaction_context}

---

REFERENCE DOCUMENTS (Constitutional/Governance - use these to validate requirements):
{reference_docs_text}

---

DOCUMENT BEING ANALYZED: {document_name} ({doc_type})
{document_text}

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

SPECIFICALLY CHECK:
1. Change of control triggers and their consequences
2. Consent requirements for assignment/change of control
3. Any inconsistencies with the MOI or Shareholders Agreement
4. Financial exposures (liquidated damages, termination fees, acceleration)
5. Covenant compliance issues
6. Expiry dates or renewal requirements
7. Key person dependencies
8. Unusual or onerous terms

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
                "calculation": "How calculated",
                "type": "liquidated_damages|acceleration|penalty|fee"
            }},
            "action_required": "What needs to be done to address this",
            "responsible_party": "buyer|seller|third_party",
            "deadline": "When this needs to be resolved if applicable"
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
    ]
}}

Be thorough - a good lawyer would rather flag something unnecessary than miss something important."""
