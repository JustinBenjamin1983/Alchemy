"""
Pass 1: Extraction prompts.

These prompts extract structured data from documents:
- Key dates (effective, expiry, deadlines)
- Financial figures (amounts, calculations)
- Parties and their roles
- Change of control clauses
- Consent requirements
"""

EXTRACTION_SYSTEM_PROMPT = """You are a senior legal analyst specializing in M&A due diligence.
Your task is to extract structured data from legal documents.

Be precise and accurate. Only extract information that is explicitly stated.
Do not infer or speculate. If information is unclear, note it as such.

Always provide the specific clause reference when available."""


def build_extraction_prompt(document_text: str, document_name: str, doc_type: str) -> str:
    """Build the extraction prompt for a single document."""

    return f"""Extract key structured data from this {doc_type} document.

DOCUMENT: {document_name}

{document_text}

---

Extract and return as JSON:

{{
    "document_summary": "2-3 sentence summary of what this document is and its key purpose",

    "parties": [
        {{
            "name": "Full legal name of party",
            "role": "borrower|lender|lessor|lessee|employer|employee|supplier|customer|shareholder|company",
            "description": "Brief description of their role in this document"
        }}
    ],

    "key_dates": [
        {{
            "date": "YYYY-MM-DD or descriptive if exact date not given",
            "date_type": "effective|expiry|execution|deadline|renewal|termination",
            "description": "What this date relates to",
            "is_critical": true/false,
            "clause_reference": "Clause X.X if applicable"
        }}
    ],

    "financial_figures": [
        {{
            "amount": numeric value (no currency symbols),
            "currency": "ZAR|USD|EUR",
            "amount_type": "loan_principal|revenue|liability|fee|penalty|deposit|limit",
            "description": "What this amount represents",
            "calculation_formula": "If this can be calculated from other values, show the formula",
            "clause_reference": "Clause X.X"
        }}
    ],

    "change_of_control_clauses": [
        {{
            "clause_reference": "Clause X.X",
            "trigger_definition": "What constitutes change of control per this document",
            "trigger_threshold": "Percentage or condition that triggers (e.g., >50%)",
            "consequence": "What happens when triggered",
            "consent_required": true/false,
            "consent_from": "Who must consent",
            "notice_period_days": number or null,
            "termination_right": true/false,
            "financial_consequence": "Any liquidated damages, acceleration, etc.",
            "can_be_waived": true/false
        }}
    ],

    "consent_requirements": [
        {{
            "trigger": "What triggers the consent requirement",
            "consent_from": "Who must provide consent",
            "consent_type": "written|verbal|notification_only",
            "consequence_if_not_obtained": "What happens without consent",
            "clause_reference": "Clause X.X"
        }}
    ],

    "assignment_restrictions": [
        {{
            "restriction_type": "prohibited|consent_required|permitted",
            "description": "Description of the restriction",
            "clause_reference": "Clause X.X"
        }}
    ],

    "governing_law": "Jurisdiction governing this document",

    "key_obligations": [
        {{
            "obligor": "Party with the obligation",
            "obligation": "Description of the obligation",
            "deadline": "When it must be performed if applicable",
            "consequence_of_breach": "What happens if breached"
        }}
    ],

    "covenants": [
        {{
            "covenant_type": "financial|operational|reporting|restrictive",
            "description": "Description of the covenant",
            "threshold": "Specific threshold if applicable (e.g., DSCR > 1.5x)",
            "testing_frequency": "When tested",
            "current_status": "compliant|breach|waiver if mentioned in document",
            "clause_reference": "Clause X.X"
        }}
    ],

    // PHASE 1 ENHANCEMENT: Document References
    // Extract references to OTHER documents mentioned in this document
    "document_references": [
        {{
            "referenced_document": "Name or description of referenced document (e.g., 'the Shareholders Agreement dated 15 March 2020')",
            "reference_context": "Why this document is referenced (e.g., 'defines the pre-emptive rights that apply')",
            "reference_type": "agreement|legal_opinion|report|certificate|schedule|correspondence|annexure|exhibit",
            "criticality": "critical|important|minor",
            "clause_reference": "Where in THIS document the reference appears (e.g., 'Clause 5.2')",
            "quote": "Exact quote mentioning the reference (max 200 chars)"
        }}
    ]
}}

Only include sections where you find relevant information. Empty arrays are fine.
Be precise with financial figures - include the exact numbers from the document.

IMPORTANT FOR DOCUMENT REFERENCES:
- Extract ALL references to other documents, agreements, certificates, reports, etc.
- Mark as 'critical' if the referenced document defines key terms, rights, or obligations
- Mark as 'important' if it provides supporting information
- Mark as 'minor' if it's mentioned in passing
- This helps identify missing documents in the data room"""
