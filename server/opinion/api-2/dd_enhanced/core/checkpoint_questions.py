"""
Phase 8 & 9: Checkpoint Question Generation

Generates AI-driven questions for human-in-the-loop validation:
- Checkpoint A: Missing documents validation (after classification)
- Checkpoint B: Entity confirmation (after entity mapping) - see DDEntityConfirmation
- Checkpoint C: Combined validation (4-step wizard, after Pass 2)

Key Functions:
- check_missing_documents: Compare docs against blueprint requirements
- generate_understanding_questions: Questions about unclear/ambiguous items
- generate_financial_confirmations: Confirm key financial figures
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def check_missing_documents(
    classified_documents: List[Dict[str, Any]],
    blueprint: Dict[str, Any],
    transaction_type: str = None
) -> Dict[str, Any]:
    """
    Check classified documents against blueprint requirements.

    Compares the documents in the data room against the expected_documents
    defined in the blueprint's folder_structure.

    Args:
        classified_documents: List of classified document dicts
        blueprint: Blueprint dict with folder_structure and expected_documents
        transaction_type: Optional transaction type for context

    Returns:
        Dict with missing_docs list and checkpoint_triggered flag
    """
    folder_structure = blueprint.get("folder_structure", {})
    reference_docs = blueprint.get("reference_documents", {})

    # Get list of present document types (from AI classification)
    present_doc_types = set()
    present_categories = set()

    for doc in classified_documents:
        doc_type = doc.get("ai_document_type", "").lower()
        category = doc.get("ai_category", "").lower()
        subcategory = doc.get("ai_subcategory", "").lower()

        if doc_type:
            present_doc_types.add(doc_type)
        if category:
            present_categories.add(category)
        if subcategory:
            present_doc_types.add(subcategory)

    missing_docs = []
    critical_missing = []

    # Check expected documents for each folder
    for folder_name, folder_config in folder_structure.items():
        relevance = folder_config.get("relevance", "medium")
        expected_docs = folder_config.get("expected_documents", [])

        for expected_doc in expected_docs:
            expected_lower = expected_doc.lower()

            # Check if this document type is present
            found = False
            for present in present_doc_types:
                if _document_match(expected_lower, present):
                    found = True
                    break

            if not found:
                importance = _determine_importance(expected_doc, folder_name, relevance)

                missing_item = {
                    "doc_type": expected_doc,
                    "category": folder_name,
                    "importance": importance,
                    "reason": f"Expected in {folder_name} for {transaction_type or 'this transaction type'}"
                }

                missing_docs.append(missing_item)

                if importance == "critical":
                    critical_missing.append(missing_item)

    # Check critical documents from reference_documents section
    critical_docs = reference_docs.get("critical_documents", [])
    for crit_doc in critical_docs:
        doc_type = crit_doc.get("type", "")
        doc_type_lower = doc_type.lower()
        required = crit_doc.get("required", False)

        if required:
            found = False
            for present in present_doc_types:
                if _document_match(doc_type_lower, present):
                    found = True
                    break

            if not found:
                missing_item = {
                    "doc_type": doc_type,
                    "category": "Critical",
                    "importance": "critical",
                    "reason": crit_doc.get("description", "Required document for this transaction")
                }

                # Avoid duplicates
                if not any(m["doc_type"].lower() == doc_type_lower for m in missing_docs):
                    missing_docs.append(missing_item)
                    critical_missing.append(missing_item)

    # Determine if checkpoint should be triggered
    checkpoint_triggered = len(critical_missing) > 0

    return {
        "missing_docs": missing_docs,
        "critical_missing": critical_missing,
        "total_missing": len(missing_docs),
        "critical_count": len(critical_missing),
        "checkpoint_triggered": checkpoint_triggered,
        "checkpoint_reason": f"{len(critical_missing)} critical documents missing" if checkpoint_triggered else None
    }


def generate_understanding_questions(
    findings: List[Dict[str, Any]],
    transaction_context: Dict[str, Any],
    synthesis_preview: str = None,
    max_questions: int = 10
) -> List[Dict[str, Any]]:
    """
    Generate questions for unclear, vital, or ambiguous items.

    These are dynamically generated based on findings, not a fixed checklist.

    Args:
        findings: List of finding dicts from Pass 2
        transaction_context: Transaction context dict
        synthesis_preview: Optional preliminary synthesis text
        max_questions: Maximum number of questions to generate

    Returns:
        List of question dicts with context and options
    """
    questions = []

    # 1. Questions about critical findings with low confidence
    low_conf_critical = [
        f for f in findings
        if f.get("severity") == "critical"
        and (f.get("confidence_score", 1) < 0.7 or f.get("confidence", {}).get("overall", 1) < 0.7)
    ]

    for finding in low_conf_critical[:3]:
        questions.append({
            "question": f"Please confirm: {finding.get('phrase', finding.get('description', ''))}",
            "context": f"This critical finding has confidence {finding.get('confidence_score', 'unknown')}. "
                       f"Source: {finding.get('document_name', 'Unknown document')}",
            "options": [
                {"label": "Confirmed correct", "value": "confirmed"},
                {"label": "Needs correction", "value": "needs_correction"},
                {"label": "Cannot verify", "value": "cannot_verify"}
            ],
            "finding_id": finding.get("id"),
            "question_type": "finding_confirmation"
        })

    # 2. Questions about deal blockers
    blockers = [f for f in findings if f.get("deal_impact") == "deal_blocker"]

    for blocker in blockers[:2]:
        questions.append({
            "question": f"Deal Blocker Identified: {blocker.get('phrase', blocker.get('description', ''))}. "
                        "Is this accurate?",
            "context": f"Document: {blocker.get('document_name', 'Unknown')}. "
                       f"Recommendation: {blocker.get('recommendation', 'N/A')}",
            "options": [
                {"label": "Yes, this is a deal blocker", "value": "confirmed_blocker"},
                {"label": "No, downgrade to condition precedent", "value": "downgrade_cp"},
                {"label": "No, downgrade to price chip", "value": "downgrade_price"},
                {"label": "This issue doesn't exist", "value": "remove"}
            ],
            "finding_id": blocker.get("id"),
            "question_type": "deal_blocker_validation"
        })

    # 3. Questions about ambiguous entity relationships
    unknown_entities = [
        f for f in findings
        if "unknown" in f.get("responsible_party", "").lower()
        or "unclear" in f.get("analysis", "").lower()
    ]

    for entity_finding in unknown_entities[:2]:
        questions.append({
            "question": f"Who is responsible for: {entity_finding.get('phrase', '')[:100]}?",
            "context": f"The analysis couldn't determine the responsible party. "
                       f"Document: {entity_finding.get('document_name', 'Unknown')}",
            "options": [
                {"label": "Seller's responsibility", "value": "seller"},
                {"label": "Buyer's responsibility", "value": "buyer"},
                {"label": "Third party responsibility", "value": "third_party"},
                {"label": "Not applicable", "value": "not_applicable"}
            ],
            "finding_id": entity_finding.get("id"),
            "question_type": "responsibility_clarification"
        })

    # 4. Questions about transaction understanding
    if transaction_context:
        # Question about deal structure if ambiguous
        deal_structure = transaction_context.get("deal_structure")
        if not deal_structure or deal_structure == "unknown":
            questions.append({
                "question": "What is the deal structure?",
                "context": "The deal structure affects how risks are assessed.",
                "options": [
                    {"label": "Share sale (100%)", "value": "share_sale_100"},
                    {"label": "Share sale (majority)", "value": "share_sale_majority"},
                    {"label": "Asset sale", "value": "asset_sale"},
                    {"label": "Business rescue/restructure", "value": "restructure"}
                ],
                "question_type": "transaction_clarification"
            })

    return questions[:max_questions]


def generate_financial_confirmations(
    findings: List[Dict[str, Any]],
    pass1_extractions: Dict[str, Any] = None,
    max_items: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate financial data confirmations.

    Maximum 5 items - only foundations that affect calculations.

    Args:
        findings: List of finding dicts
        pass1_extractions: Optional Pass 1 extraction results
        max_items: Maximum number of confirmations (default 5)

    Returns:
        List of financial confirmation dicts
    """
    confirmations = []

    # Extract financial figures from findings
    financial_findings = [
        f for f in findings
        if f.get("financial_exposure") or f.get("exposure_amount")
    ]

    # Get unique financial figures
    seen_amounts = set()

    for finding in financial_findings:
        exposure = finding.get("financial_exposure", {})
        amount = exposure.get("amount") if isinstance(exposure, dict) else finding.get("exposure_amount")

        if amount and amount not in seen_amounts and amount > 0:
            seen_amounts.add(amount)

            confirmations.append({
                "metric": finding.get("category", "Financial Exposure"),
                "description": finding.get("phrase", finding.get("description", ""))[:200],
                "extracted_value": amount,
                "currency": exposure.get("currency", "ZAR") if isinstance(exposure, dict) else "ZAR",
                "source_document": finding.get("document_name", "Unknown"),
                "calculation": exposure.get("calculation", "") if isinstance(exposure, dict) else "",
                "confirmation_type": "financial_amount"
            })

    # Add key figures from Pass 1 if available
    if pass1_extractions:
        for fig in pass1_extractions.get("financial_figures", [])[:5]:
            amount = fig.get("amount")
            if amount and amount not in seen_amounts:
                seen_amounts.add(amount)
                confirmations.append({
                    "metric": fig.get("amount_type", "Financial Figure"),
                    "description": fig.get("description", ""),
                    "extracted_value": amount,
                    "currency": fig.get("currency", "ZAR"),
                    "source_document": fig.get("source_document", "Unknown"),
                    "clause_reference": fig.get("clause_reference", ""),
                    "confirmation_type": "extracted_figure"
                })

    # Sort by amount (largest first) and limit
    confirmations.sort(key=lambda x: x.get("extracted_value", 0), reverse=True)

    return confirmations[:max_items]


def generate_checkpoint_c_content(
    findings: List[Dict[str, Any]],
    pass1_results: Dict[str, Any],
    transaction_context: Dict[str, Any],
    synthesis_preview: str = None
) -> Dict[str, Any]:
    """
    Generate all content for Checkpoint C (4-step post-analysis wizard).

    Returns content for all 4 steps:
    1. Confirm Transaction Understanding
    2. Confirm Financial Foundations
    3. Missing Documents
    4. Review & Confirm

    Args:
        findings: List of finding dicts
        pass1_results: Pass 1 extraction results
        transaction_context: Transaction context dict
        synthesis_preview: Optional preliminary synthesis

    Returns:
        Dict with content for each wizard step
    """
    # Step 1: Transaction Understanding
    understanding_questions = generate_understanding_questions(
        findings=findings,
        transaction_context=transaction_context,
        synthesis_preview=synthesis_preview,
        max_questions=8
    )

    # Generate preliminary summary
    preliminary_summary = _generate_preliminary_summary(findings, transaction_context)

    # Step 2: Financial Confirmations
    financial_confirmations = generate_financial_confirmations(
        findings=findings,
        pass1_extractions=pass1_results,
        max_items=5
    )

    # Step 3: Missing Documents (from document references)
    missing_from_analysis = _extract_missing_from_analysis(findings, pass1_results)

    # Step 4: Review data (will be populated after user completes steps 1-3)

    return {
        "step_1_understanding": {
            "preliminary_summary": preliminary_summary,
            "questions": understanding_questions,
            "total_questions": len(understanding_questions)
        },
        "step_2_financial": {
            "confirmations": financial_confirmations,
            "total_confirmations": len(financial_confirmations),
            "instructions": "Confirm or correct these key financial figures. "
                           "Your corrections will be used in the final calculations."
        },
        "step_3_missing_docs": {
            "missing_documents": missing_from_analysis,
            "total_missing": len(missing_from_analysis),
            "instructions": "Upload any missing documents identified during analysis. "
                           "New documents will be processed and findings merged."
        },
        "step_4_review": {
            "instructions": "Review the updated summary with your corrections before proceeding."
        }
    }


def _document_match(expected: str, present: str) -> bool:
    """Check if a present document matches an expected document type."""
    expected_words = set(expected.lower().split())
    present_words = set(present.lower().split())

    # Direct substring match
    if expected.lower() in present.lower() or present.lower() in expected.lower():
        return True

    # Significant word overlap (at least 2 words or 50% overlap)
    overlap = expected_words & present_words
    if len(overlap) >= 2:
        return True
    if len(overlap) / max(len(expected_words), 1) >= 0.5:
        return True

    # Common abbreviation mappings
    abbrev_map = {
        "moi": "memorandum of incorporation",
        "sha": "shareholders agreement",
        "spa": "sale and purchase agreement",
        "afs": "annual financial statements",
        "empr": "environmental management programme",
        "wul": "water use license",
        "slp": "social and labour plan",
        "bee": "broad-based black economic empowerment",
    }

    for abbrev, full in abbrev_map.items():
        if abbrev in expected.lower() and abbrev in present.lower():
            return True
        if abbrev in expected.lower() and full in present.lower():
            return True
        if full in expected.lower() and abbrev in present.lower():
            return True

    return False


def _determine_importance(doc_type: str, folder: str, relevance: str) -> str:
    """Determine the importance of a missing document."""
    doc_lower = doc_type.lower()

    # Critical documents
    critical_keywords = [
        "mining right", "environmental authorization", "water use license",
        "moi", "memorandum of incorporation", "shareholders agreement",
        "facility agreement", "loan agreement", "title deed"
    ]

    for keyword in critical_keywords:
        if keyword in doc_lower:
            return "critical"

    # Folder relevance
    if relevance == "critical":
        return "critical" if "right" in doc_lower or "license" in doc_lower else "important"

    if relevance == "high":
        return "important"

    return "minor"


def _generate_preliminary_summary(
    findings: List[Dict[str, Any]],
    transaction_context: Dict[str, Any]
) -> str:
    """Generate a preliminary summary for Checkpoint C Step 1."""
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    high_count = sum(1 for f in findings if f.get("severity") == "high")
    blocker_count = sum(1 for f in findings if f.get("deal_impact") == "deal_blocker")

    total_exposure = sum(
        f.get("exposure_amount", 0) or
        (f.get("financial_exposure", {}).get("amount", 0) if isinstance(f.get("financial_exposure"), dict) else 0)
        for f in findings
    )

    summary = f"""PRELIMINARY ANALYSIS SUMMARY

Transaction: {transaction_context.get('transaction_name', 'Unknown')}
Target: {transaction_context.get('target_entity_name', 'Unknown')}

FINDINGS OVERVIEW:
- {len(findings)} total findings identified
- {critical_count} critical severity
- {high_count} high severity
- {blocker_count} potential deal blockers

ESTIMATED TOTAL EXPOSURE: R{total_exposure:,.0f}

Please review the questions below to help us refine our understanding."""

    return summary


def _extract_missing_from_analysis(
    findings: List[Dict[str, Any]],
    pass1_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Extract documents identified as missing during analysis."""
    missing = []

    # From document references (Pass 1)
    doc_refs = pass1_results.get("document_references", [])
    for ref in doc_refs:
        if ref.get("criticality") == "critical" and not ref.get("found_in_data_room"):
            missing.append({
                "doc_type": ref.get("referenced_document", "Unknown document"),
                "reason": ref.get("reference_context", "Referenced in analyzed documents"),
                "source": ref.get("source_document", "Unknown"),
                "importance": "critical"
            })

    # From findings mentioning missing documents
    for finding in findings:
        if "missing" in finding.get("analysis", "").lower() or \
           "not provided" in finding.get("analysis", "").lower():
            missing.append({
                "doc_type": finding.get("category", "Unknown document type"),
                "reason": finding.get("phrase", finding.get("description", ""))[:200],
                "source": finding.get("document_name", "Analysis"),
                "importance": "important" if finding.get("severity") in ["critical", "high"] else "minor"
            })

    # Deduplicate by doc_type
    seen = set()
    unique_missing = []
    for m in missing:
        key = m["doc_type"].lower()
        if key not in seen:
            seen.add(key)
            unique_missing.append(m)

    return unique_missing[:10]  # Limit to 10
