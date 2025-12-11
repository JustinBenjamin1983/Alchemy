"""
Pass 3: Cross-Document Synthesis prompts.

THIS IS THE KEY ARCHITECTURAL IMPROVEMENT.

The original system processes documents in isolation.
These prompts put ALL documents in context together to find:
- Conflicts between documents
- Cascade effects across contracts
- Authorization gaps
- Consent matrices

BLUEPRINT-DRIVEN: The cross-doc prompts now dynamically include:
- cross_doc_validations from each risk category
- deal_blockers definitions
- conditions_precedent_patterns
"""
from typing import Optional, Dict, List


def get_crossdoc_system_prompt(blueprint: Optional[Dict] = None) -> str:
    """Generate system prompt, optionally customized based on blueprint."""
    transaction_type = blueprint.get("transaction_type", "corporate acquisition") if blueprint else "corporate acquisition"
    jurisdiction = blueprint.get("jurisdiction", "South Africa") if blueprint else "South Africa"

    return f"""You are a senior M&A partner conducting final review of due diligence for a {transaction_type}.

Jurisdiction: {jurisdiction}

Your task is to look ACROSS all documents to find issues that only become
apparent when comparing multiple documents together:
- Conflicts: Document A says X, but Document B says Y
- Cascades: A single event (like change of control) triggers consequences across multiple contracts
- Authorization gaps: Constitutional documents require something that wasn't done
- Consent matrices: Multiple consents needed from different parties

This cross-document analysis is what separates thorough DD from checkbox DD."""


# Legacy constant for backwards compatibility
CROSSDOC_SYSTEM_PROMPT = get_crossdoc_system_prompt()


def _build_cross_doc_validations_section(blueprint: Optional[Dict]) -> str:
    """Build cross-document validations section from blueprint."""
    if not blueprint:
        return ""

    validations = []
    for category in blueprint.get("risk_categories", []):
        cat_name = category.get("name", "")
        for validation in category.get("cross_doc_validations", []):
            check = validation.get("check", "")
            desc = validation.get("description", "")
            validations.append(f"- {check}: {desc}")

    if not validations:
        return ""

    return f"""
TRANSACTION-SPECIFIC CROSS-DOCUMENT VALIDATIONS:
(Check these specific cross-references for this transaction type)

{chr(10).join(validations[:20])}
"""


def _build_deal_blockers_awareness_section(blueprint: Optional[Dict]) -> str:
    """Build deal blockers section from blueprint for cross-doc awareness."""
    if not blueprint or not blueprint.get("deal_blockers"):
        return ""

    blockers = blueprint.get("deal_blockers", [])
    blocker_lines = []

    for blocker in blockers[:10]:
        desc = blocker.get("description", "")
        severity = blocker.get("severity", "conditional")
        consequence = blocker.get("consequence", "")

        marker = "[ABSOLUTE]" if severity == "absolute" else "[CONDITIONAL]"
        blocker_lines.append(f"- {marker} {desc}")
        if consequence:
            blocker_lines.append(f"    → {consequence}")

    return f"""
DEAL BLOCKER DEFINITIONS:
(Flag as DEAL_BLOCKER if cross-document analysis reveals any of these)

{chr(10).join(blocker_lines)}
"""


def _build_cp_patterns_section(blueprint: Optional[Dict]) -> str:
    """Build conditions precedent patterns section from blueprint."""
    if not blueprint or not blueprint.get("conditions_precedent_patterns"):
        return ""

    patterns = blueprint.get("conditions_precedent_patterns", [])
    pattern_lines = []

    for p in patterns[:10]:
        pattern = p.get("pattern", "")
        cp_type = p.get("cp_type", "")
        pattern_lines.append(f"- Pattern: \"{pattern}\" → {cp_type}")

    return f"""
CONDITION PRECEDENT PATTERNS TO IDENTIFY:
(Look for these patterns across documents)

{chr(10).join(pattern_lines)}
"""


def build_conflict_detection_prompt(
    all_documents_text: str,
    blueprint: Optional[Dict] = None
) -> str:
    """
    Prompt to detect conflicts between documents.

    KEY IMPROVEMENT: All documents in single context.
    BLUEPRINT-DRIVEN: Includes cross_doc_validations from blueprint.
    """
    cross_doc_section = _build_cross_doc_validations_section(blueprint)
    deal_blockers_section = _build_deal_blockers_awareness_section(blueprint)

    return f"""Review ALL documents below and identify CONFLICTS between them.
{cross_doc_section}
{deal_blockers_section}

A CONFLICT exists when:
1. Document A requires something that Document B shows wasn't done
2. Document A says X but Document B says Y or contradicts it
3. Terms or definitions differ materially between documents
4. Obligations in one document conflict with rights in another
5. Approval thresholds or processes differ between documents

This is CROSS-DOCUMENT analysis - you must compare documents against each other.

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{{
    "conflicts": [
        {{
            "conflict_id": "C001",
            "conflict_type": "authorization_gap|inconsistent_terms|conflicting_obligations|definitional_mismatch|procedural_conflict",
            "severity": "critical|high|medium",
            "description": "Clear description of the conflict",
            "document_a": "First document name",
            "document_a_provision": "What Document A says (with clause ref)",
            "document_b": "Second document name",
            "document_b_provision": "What Document B says or doesn't say (with clause ref)",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|requires_resolution",
            "resolution_required": "What needs to happen to resolve this conflict",
            "which_prevails": "Which document should prevail if conflicting, or 'unclear'"
        }}
    ],
    "summary": "Brief summary of key conflicts found"
}}

If no conflicts are found, return {{"conflicts": [], "summary": "No material conflicts identified between documents."}}

IMPORTANT: Look specifically for:
1. MOI/SHA approval requirements vs what Board Resolution actually approved
2. Change of control definitions that differ between contracts
3. Consent requirements that may conflict
4. Financial terms that don't reconcile"""


def build_cascade_mapping_prompt(
    all_documents_text: str,
    trigger_event: str = "100% share acquisition",
    blueprint: Optional[Dict] = None
) -> str:
    """
    Prompt to map how a trigger event cascades across all documents.

    KEY IMPROVEMENT: Links related findings as a single cascade.
    BLUEPRINT-DRIVEN: Includes deal_blockers and CP patterns from blueprint.
    """
    deal_blockers_section = _build_deal_blockers_awareness_section(blueprint)
    cp_patterns_section = _build_cp_patterns_section(blueprint)

    # Get calculations from blueprint for financial exposure guidance
    calculation_guidance = ""
    if blueprint:
        calcs = []
        for category in blueprint.get("risk_categories", []):
            for calc in category.get("calculations", []):
                name = calc.get("name", "")
                formula = calc.get("formula", calc.get("description", ""))
                calcs.append(f"- {name}: {formula}")
        if calcs:
            calculation_guidance = f"""
CALCULATION TEMPLATES FOR THIS TRANSACTION TYPE:
{chr(10).join(calcs[:10])}
"""

    return f"""This is an acquisition where {trigger_event} will occur.
{deal_blockers_section}
{cp_patterns_section}
{calculation_guidance}

Map how this change of control event CASCADES through ALL contracts and documents.

For each document, identify:
1. Whether it contains a change of control trigger
2. What threshold triggers it
3. What happens when triggered (consent needed, termination right, payment, etc.)
4. The financial exposure if triggered adversely

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{{
    "trigger_event": "{trigger_event}",
    "trigger_analysis": "Analysis of whether this transaction triggers change of control provisions",
    "cascade_items": [
        {{
            "sequence": 1,
            "document": "Document name",
            "clause_reference": "Clause X.X",
            "trigger_threshold": "What % or event triggers this (e.g., >50% shares)",
            "is_triggered": true/false,
            "consequence": "What happens when triggered",
            "consent_required": true/false,
            "consent_from": "Who must consent",
            "notice_period_days": number or null,
            "termination_right": true/false,
            "can_refuse_consent": true/false,
            "financial_exposure": {{
                "amount": number or null,
                "currency": "ZAR",
                "calculation_basis": "How the amount is calculated (show the math)",
                "exposure_type": "liquidated_damages|termination_fee|acceleration|penalty|other"
            }},
            "can_be_waived": true/false,
            "waiver_obtained": true/false/null,
            "risk_level": "critical|high|medium|low",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|noted"
        }}
    ],
    "total_financial_exposure": {{
        "amount": number,
        "currency": "ZAR",
        "breakdown": "Summary of how total was calculated"
    }},
    "critical_path": [
        "Ordered list of actions/consents needed before closing can occur"
    ],
    "deal_blockers": [
        "List any items that would prevent the deal from closing if not resolved"
    ],
    "summary": "Executive summary of the cascade analysis"
}}

IMPORTANT CALCULATIONS:
- For Eskom-type coal supply agreements: Calculate liquidated damages as X months × monthly contract value
- For loan facilities: Show the full acceleration amount at risk
- For leases: Calculate any early termination penalties

Show your calculation working for any financial exposure figures."""


def build_authorization_check_prompt(
    all_documents_text: str,
    blueprint: Optional[Dict] = None
) -> str:
    """
    Prompt to validate that governance actions comply with constitutional documents.

    KEY IMPROVEMENT: Validates Board Resolution against MOI/SHA requirements.
    BLUEPRINT-DRIVEN: Includes deal_blockers related to authorization.
    """
    deal_blockers_section = _build_deal_blockers_awareness_section(blueprint)

    # Get reference documents that should always be present
    ref_docs_guidance = ""
    if blueprint and blueprint.get("reference_documents", {}).get("always_include"):
        refs = blueprint["reference_documents"]["always_include"]
        ref_lines = [f"- {r.get('pattern', '')}: {r.get('reason', '')}" for r in refs]
        ref_docs_guidance = f"""
KEY REFERENCE DOCUMENTS FOR THIS TRANSACTION TYPE:
{chr(10).join(ref_lines)}
"""

    return f"""Verify that governance actions (Board Resolutions, shareholder actions) comply with
constitutional documents (MOI, Shareholders Agreement).
{deal_blockers_section}
{ref_docs_guidance}

This is a critical cross-document check: Does the Board Resolution properly authorize
what the MOI and Shareholders Agreement require?

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{{
    "moi_requirements": {{
        "for_share_sale": "What MOI requires for a change of control/share sale",
        "approval_threshold": "Required majority/percentage",
        "special_resolution_needed": true/false,
        "clause_reference": "Clause X.X"
    }},
    "sha_requirements": {{
        "additional_requirements": "What Shareholders Agreement adds to MOI requirements",
        "tag_along_rights": true/false,
        "drag_along_rights": true/false,
        "right_of_first_refusal": true/false,
        "clause_reference": "Clause X.X"
    }},
    "board_resolution_analysis": {{
        "what_was_approved": "What the Board Resolution authorizes",
        "approved_by": "Who approved (directors present/voting)",
        "date": "Date of resolution",
        "quorum_met": true/false/unknown,
        "proper_notice_given": true/false/unknown
    }},
    "shareholder_resolution_analysis": {{
        "exists": true/false,
        "what_was_approved": "What shareholders approved if applicable",
        "approval_percentage": "Percentage that approved",
        "date": "Date of resolution"
    }},
    "authorization_gaps": [
        {{
            "gap_id": "AG001",
            "description": "Clear description of what's missing or deficient",
            "required_by": "Which document requires this",
            "requirement_clause": "Clause X.X",
            "current_status": "What has been done (or not done)",
            "severity": "critical|high|medium",
            "deal_impact": "deal_blocker|condition_precedent",
            "remediation": "What needs to happen to fix this"
        }}
    ],
    "summary": "Overall assessment of authorization status"
}}

PAY SPECIAL ATTENTION TO:
1. Whether shareholder approval was obtained if required by MOI
2. Whether the resolution covers the specific transaction contemplated
3. Any procedural defects (quorum, notice, voting)
4. Whether conditions in the resolution have been or can be met"""


def build_consent_matrix_prompt(
    all_documents_text: str,
    blueprint: Optional[Dict] = None
) -> str:
    """
    Prompt to build a comprehensive consent matrix.

    BLUEPRINT-DRIVEN: Includes CP patterns for consent identification.
    """
    cp_patterns_section = _build_cp_patterns_section(blueprint)
    deal_blockers_section = _build_deal_blockers_awareness_section(blueprint)

    # Get critical documents that typically require consents
    critical_docs_guidance = ""
    if blueprint and blueprint.get("reference_documents", {}).get("critical_documents"):
        docs = blueprint["reference_documents"]["critical_documents"]
        doc_lines = [f"- {d.get('type', '')}: {d.get('description', '')}" for d in docs if d.get("required")]
        if doc_lines:
            critical_docs_guidance = f"""
CRITICAL DOCUMENTS FOR THIS TRANSACTION TYPE:
(These documents often contain consent requirements)

{chr(10).join(doc_lines)}
"""

    return f"""Build a comprehensive CONSENT MATRIX for this transaction.
{cp_patterns_section}
{deal_blockers_section}
{critical_docs_guidance}

Identify every consent, approval, or notification required across all documents.

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{{
    "consent_matrix": [
        {{
            "consent_id": "CON001",
            "contract": "Contract/document name",
            "counterparty": "Who must provide consent",
            "consent_type": "written_consent|approval|notification|acknowledgment",
            "trigger": "What triggers this requirement",
            "clause_reference": "Clause X.X",
            "timing": "When consent must be obtained (before/after closing)",
            "deadline_days": number or null,
            "consequence_if_not_obtained": "What happens without consent",
            "is_deal_blocker": true/false,
            "likelihood_of_obtaining": "high|medium|low|unknown",
            "cost_to_obtain": "Any fee or cost associated",
            "status": "not_started|in_progress|obtained|refused|waived",
            "responsible_party": "buyer|seller",
            "notes": "Any additional relevant information"
        }}
    ],
    "summary": {{
        "total_consents_required": number,
        "deal_blocking_consents": number,
        "estimated_timeline": "How long to obtain all consents",
        "key_risks": ["List of key consent risks"]
    }}
}}

Include consents required for:
1. Change of control clauses
2. Assignment restrictions
3. Banking/loan facilities
4. Material contracts
5. Regulatory approvals (if any)
6. Employment contracts (if they require notification)"""
