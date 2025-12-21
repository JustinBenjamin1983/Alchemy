"""
Pass 2: Per-Document Analysis

Analyzes each document for risks and issues.

KEY IMPROVEMENT: Reference documents (MOI, SHA, Board Resolution) are
ALWAYS included in the context, so analysis can validate against
constitutional requirements.

PHASE 3: Folder-aware processing - documents are analyzed with folder-specific
questions from the blueprint's folder_questions section.
"""
from typing import List, Dict, Any, Optional
import os
import sys
import logging

# Ensure dd_enhanced is in path for imports
_dd_enhanced_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _dd_enhanced_path not in sys.path:
    sys.path.insert(0, _dd_enhanced_path)

from .claude_client import ClaudeClient
from .document_loader import LoadedDocument
from prompts.analysis import get_analysis_system_prompt, build_analysis_prompt
from config.question_loader import QuestionLoader, should_skip_folder

logger = logging.getLogger(__name__)


# Default transaction context for Karoo Mining
DEFAULT_TRANSACTION_CONTEXT = """
This is a 100% share sale acquisition of Karoo Mining (Pty) Ltd.
The buyer will acquire all issued shares from the current shareholders.
This constitutes a change of control for all purposes.

Key considerations:
- All change of control provisions will be triggered
- All consents for assignment/change of control are required
- The buyer will inherit all obligations and liabilities
"""


def analyze_document(
    doc: Dict,
    reference_docs: List[LoadedDocument],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    transaction_context: str = DEFAULT_TRANSACTION_CONTEXT,
    prioritized_questions: Optional[List[Dict]] = None,
    question_loader: Optional[QuestionLoader] = None
) -> List[Dict]:
    """
    Analyze a single document for risks and issues.

    Args:
        doc: Document dict with 'filename', 'text', 'doc_type', 'folder_category' (optional)
        reference_docs: Constitutional/governance docs to include in context
        blueprint: DD blueprint with risk categories (optional)
        client: Claude API client
        transaction_context: Context about the transaction
        prioritized_questions: Tier 1-3 questions from question_prioritizer (optional)
        question_loader: QuestionLoader for folder-specific questions (Phase 3)

    Returns:
        List of findings from this document
    """
    filename = doc.get("filename", "unknown")
    doc_type = doc.get("doc_type", "")
    folder_category = doc.get("folder_category", None)  # Phase 3: folder context

    # Skip reference docs in per-doc analysis (they're already in context)
    if doc_type in ("constitutional", "governance"):
        return []

    # Phase 3: Skip 99_Needs_Review documents
    if folder_category and should_skip_folder(folder_category):
        logger.info(f"Skipping {filename} - folder {folder_category} needs manual review")
        return []

    # Phase 3: Get folder-specific questions if available
    folder_questions = None
    if question_loader and folder_category:
        folder_questions = question_loader.get_questions_for_folder(folder_category)
        if folder_questions:
            logger.debug(f"Using {len(folder_questions)} folder-specific questions for {folder_category}")

    # Build reference documents context
    ref_context = _build_reference_context(reference_docs)

    # Build analysis prompt with reference context, blueprint, and prioritized questions
    # Phase 3: Include folder-specific questions when available
    prompt = build_analysis_prompt(
        document_text=doc.get("text", "")[:40000],  # Limit per-doc text
        document_name=filename,
        doc_type=doc_type,
        reference_docs_text=ref_context,
        transaction_context=transaction_context,
        blueprint=blueprint,
        prioritized_questions=prioritized_questions,
        folder_category=folder_category,
        folder_questions=folder_questions
    )

    # Get blueprint-aware system prompt
    system_prompt = get_analysis_system_prompt(blueprint)

    # Call Claude (uses complete_analysis which uses Sonnet)
    response = client.complete_analysis(
        prompt=prompt,
        system=system_prompt,
        max_tokens=8192,
        temperature=0.1
    )

    if "error" in response:
        return []

    # Process findings (risks/issues)
    findings = response.get("findings", [])
    for finding in findings:
        finding["source_document"] = filename
        finding["pass"] = 2
        # Phase 3: Add folder context to findings
        if folder_category:
            finding["folder_category"] = folder_category
        # Link finding to question if it answered a specific question
        if finding.get("blueprint_question_answered"):
            finding["question_id"] = _generate_question_id(
                folder_category, finding.get("blueprint_question_answered")
            )

    # Also include positive confirmations as findings with finding_type="positive"
    # This ensures compliant/green findings are shown alongside issues
    positive_confirmations = response.get("positive_confirmations", [])
    for i, positive in enumerate(positive_confirmations):
        positive_finding = {
            "finding_id": f"P{i+1:03d}",
            "category": folder_category.replace("_", " ").lstrip("0123456789").strip() if folder_category else "General",
            "description": positive.get("description", ""),
            "clause_reference": positive.get("clause_reference", ""),
            "evidence_quote": positive.get("clause_reference", ""),  # Use clause as evidence
            "severity": "low",  # Positive findings are low severity (informational)
            "finding_type": "positive",
            "deal_impact": "noted",
            "source_document": filename,
            "pass": 2,
        }
        if folder_category:
            positive_finding["folder_category"] = folder_category
        findings.append(positive_finding)

    return findings


def _generate_question_id(folder_category: Optional[str], question_text: str) -> str:
    """Generate a stable question ID from folder category and question text."""
    import hashlib
    prefix = folder_category or "general"
    # Create a short hash of the question text
    question_hash = hashlib.md5(question_text.encode()).hexdigest()[:8]
    return f"{prefix}_{question_hash}"


def run_pass2_analysis(
    documents: List[Dict],
    reference_docs: List[LoadedDocument],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    transaction_context: str = DEFAULT_TRANSACTION_CONTEXT,
    prioritized_questions: Optional[List[Dict]] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run Pass 2: Analyze each document with reference context.

    KEY IMPROVEMENTS:
    - Reference documents are always in context
    - Prioritized questions from question_prioritizer guide the analysis
    - Phase 3: Folder-aware analysis with folder-specific questions
    - Gap tracking: Identifies unanswered questions and generates gap findings

    Args:
        documents: List of document dicts (with optional 'folder_category')
        reference_docs: Constitutional/governance docs to include in every analysis
        blueprint: DD blueprint with risk categories (optional)
        client: Claude API client
        transaction_context: Context about the transaction
        prioritized_questions: Tier 1-3 questions from question_prioritizer (optional)
        verbose: Print progress

    Returns:
        Dict with 'findings' list and 'gap_findings' list
    """

    all_findings = []

    # Track questions asked vs answered for gap detection
    questions_asked: Dict[str, List[Dict]] = {}  # folder_category -> list of questions
    questions_answered: Dict[str, set] = {}  # folder_category -> set of answered question texts
    folder_docs_analyzed: Dict[str, List[str]] = {}  # folder_category -> list of doc filenames
    missing_info_by_folder: Dict[str, List[str]] = {}  # folder_category -> missing info items

    # Phase 3: Initialize QuestionLoader for folder-aware analysis
    question_loader = QuestionLoader(blueprint) if blueprint else None
    if question_loader and question_loader.has_folder_questions():
        if verbose:
            logger.info("Using folder-aware analysis with blueprint folder_questions")

    # Build reference documents context (always included)
    ref_context = _build_reference_context(reference_docs)
    if verbose and reference_docs:
        print(f"  Reference docs in context: {[d.filename for d in reference_docs]}")

    for i, doc in enumerate(documents, 1):
        filename = doc["filename"]
        doc_type = doc["doc_type"]
        folder_category = doc.get("folder_category")  # Phase 3: folder context

        # Skip reference docs in per-doc analysis (they're already in context)
        if doc_type in ("constitutional", "governance"):
            if verbose:
                print(f"  [{i}/{len(documents)}] Skipping {filename} (reference doc)")
            continue

        # Phase 3: Skip 99_Needs_Review documents
        if folder_category and should_skip_folder(folder_category):
            if verbose:
                print(f"  [{i}/{len(documents)}] Skipping {filename} (needs manual review)")
            continue

        if verbose:
            folder_info = f" [{folder_category}]" if folder_category else ""
            print(f"  [{i}/{len(documents)}] Analyzing {filename}{folder_info}...")

        # Phase 3: Get folder-specific questions
        folder_questions = None
        if question_loader and folder_category:
            folder_questions = question_loader.get_questions_for_folder(folder_category)
            # Track questions asked for this folder category
            if folder_questions and folder_category not in questions_asked:
                questions_asked[folder_category] = folder_questions
            # Track which docs were analyzed per folder
            if folder_category not in folder_docs_analyzed:
                folder_docs_analyzed[folder_category] = []
            folder_docs_analyzed[folder_category].append(filename)

        # Build analysis prompt with reference context, blueprint, and prioritized questions
        prompt = build_analysis_prompt(
            document_text=doc["text"][:40000],  # Limit per-doc text
            document_name=filename,
            doc_type=doc_type,
            reference_docs_text=ref_context,
            transaction_context=transaction_context,
            blueprint=blueprint,  # Pass blueprint for question injection
            prioritized_questions=prioritized_questions,  # Pass prioritized questions
            folder_category=folder_category,  # Phase 3
            folder_questions=folder_questions  # Phase 3
        )

        # Get blueprint-aware system prompt
        system_prompt = get_analysis_system_prompt(blueprint)

        # Call Claude (uses complete_analysis which uses Sonnet)
        response = client.complete_analysis(
            prompt=prompt,
            system=system_prompt,
            max_tokens=8192,
            temperature=0.1
        )

        if "error" in response:
            print(f"    Warning: Analysis failed for {filename}: {response.get('error')}")
            continue

        # Process findings (risks/issues)
        findings = response.get("findings", [])
        for finding in findings:
            finding["source_document"] = filename
            finding["pass"] = 2
            # Phase 3: Add folder context to findings
            if folder_category:
                finding["folder_category"] = folder_category
            # Link finding to question if it answered a specific question
            if finding.get("blueprint_question_answered"):
                finding["question_id"] = _generate_question_id(
                    folder_category, finding.get("blueprint_question_answered")
                )
            all_findings.append(finding)

        # Also include positive confirmations as findings with finding_type="positive"
        positive_confirmations = response.get("positive_confirmations", [])
        for idx, positive in enumerate(positive_confirmations):
            positive_finding = {
                "finding_id": f"P{idx+1:03d}",
                "category": folder_category.replace("_", " ").lstrip("0123456789").strip() if folder_category else "General",
                "description": positive.get("description", ""),
                "clause_reference": positive.get("clause_reference", ""),
                "evidence_quote": positive.get("clause_reference", ""),
                "severity": "low",
                "finding_type": "positive",
                "deal_impact": "noted",
                "source_document": filename,
                "pass": 2,
            }
            if folder_category:
                positive_finding["folder_category"] = folder_category
            all_findings.append(positive_finding)

        # Track questions answered for gap detection
        answered = response.get("questions_answered", [])
        if folder_category and answered:
            if folder_category not in questions_answered:
                questions_answered[folder_category] = set()
            for qa in answered:
                question_text = qa.get("question", "")
                if question_text:
                    questions_answered[folder_category].add(question_text.lower().strip())

        # Track missing information for gap findings
        missing_info = response.get("missing_information", [])
        if folder_category and missing_info:
            if folder_category not in missing_info_by_folder:
                missing_info_by_folder[folder_category] = []
            missing_info_by_folder[folder_category].extend(missing_info)

        if verbose:
            positive_count = len(positive_confirmations)
            answered_count = len(answered)
            print(f"    Found {len(findings)} issues, {positive_count} compliant, {answered_count} questions answered")

    # Generate gap findings for unanswered questions
    gap_findings = _generate_gap_findings(
        questions_asked=questions_asked,
        questions_answered=questions_answered,
        folder_docs_analyzed=folder_docs_analyzed,
        missing_info_by_folder=missing_info_by_folder,
        blueprint=blueprint
    )

    if verbose and gap_findings:
        print(f"  Generated {len(gap_findings)} gap findings for unanswered questions")

    return {
        "findings": all_findings,
        "gap_findings": gap_findings
    }


def _generate_gap_findings(
    questions_asked: Dict[str, List[Dict]],
    questions_answered: Dict[str, set],
    folder_docs_analyzed: Dict[str, List[str]],
    missing_info_by_folder: Dict[str, List[str]],
    blueprint: Optional[Dict] = None
) -> List[Dict]:
    """
    Generate gap findings for unanswered questions.

    Gap reasons:
    1. "documents_not_provided" - No documents were analyzed for this folder category
    2. "information_not_found" - Documents were analyzed but don't contain the answer
    3. "inconclusive" - Documents were analyzed, may reference the topic, but answer unclear

    Args:
        questions_asked: Dict of folder_category -> list of question dicts
        questions_answered: Dict of folder_category -> set of answered question texts (lowercase)
        folder_docs_analyzed: Dict of folder_category -> list of doc filenames analyzed
        missing_info_by_folder: Dict of folder_category -> list of missing info items
        blueprint: Blueprint for additional context

    Returns:
        List of gap findings
    """
    gap_findings = []
    gap_id = 1

    for folder_category, questions in questions_asked.items():
        docs_analyzed = folder_docs_analyzed.get(folder_category, [])
        answered_set = questions_answered.get(folder_category, set())
        missing_info = missing_info_by_folder.get(folder_category, [])

        # Format folder name for display
        folder_display = folder_category.replace("_", " ").lstrip("0123456789").strip() if folder_category else "General"

        for question in questions:
            question_text = question.get("question", "")
            if not question_text:
                continue

            # Check if this question was answered
            question_lower = question_text.lower().strip()
            was_answered = any(
                question_lower in ans or ans in question_lower
                for ans in answered_set
            )

            if was_answered:
                continue  # Question was answered, no gap

            # Determine gap reason
            if not docs_analyzed:
                gap_reason = "documents_not_provided"
                gap_description = f"No {folder_display} documents were included in the analysis"
                action_required = f"Upload and include {folder_display} documents to answer this question"
            else:
                # Documents were analyzed but question not answered
                # Check if it's in missing_info (explicit gap)
                is_missing_info = any(
                    question_lower in mi.lower() or mi.lower() in question_lower
                    for mi in missing_info
                )

                if is_missing_info:
                    gap_reason = "information_not_found"
                    gap_description = f"The analyzed {folder_display} documents do not contain information to answer this question"
                    action_required = f"Request additional documents or clarification from the data room"
                else:
                    gap_reason = "inconclusive"
                    gap_description = f"Unable to conclusively answer from the {len(docs_analyzed)} {folder_display} document(s) analyzed"
                    action_required = f"Manual review required - documents may partially address this but need human verification"

            # Create gap finding
            gap_finding = {
                "finding_id": f"GAP{gap_id:03d}",
                "category": folder_display,
                "description": f"UNANSWERED: {question_text}",
                "gap_reason": gap_reason,
                "gap_detail": gap_description,
                "severity": "low",  # Will map to "gap" in frontend
                "finding_type": "gap",
                "deal_impact": "noted",
                "action_required": action_required,
                "source_document": ", ".join(docs_analyzed[:3]) if docs_analyzed else "No documents",
                "pass": 2,
                "folder_category": folder_category,
                "question_priority": question.get("priority", "medium"),
                "documents_analyzed_count": len(docs_analyzed),
            }

            gap_findings.append(gap_finding)
            gap_id += 1

    # Also create gap findings from explicit missing_information items
    for folder_category, missing_items in missing_info_by_folder.items():
        folder_display = folder_category.replace("_", " ").lstrip("0123456789").strip() if folder_category else "General"
        docs_analyzed = folder_docs_analyzed.get(folder_category, [])

        for missing_item in missing_items:
            # Avoid duplicates - check if we already have a gap for this
            already_covered = any(
                missing_item.lower() in gf.get("description", "").lower()
                for gf in gap_findings
            )
            if already_covered:
                continue

            gap_finding = {
                "finding_id": f"GAP{gap_id:03d}",
                "category": folder_display,
                "description": f"MISSING INFO: {missing_item}",
                "gap_reason": "information_not_found",
                "gap_detail": f"Information identified as missing from analyzed documents",
                "severity": "low",
                "finding_type": "gap",
                "deal_impact": "noted",
                "action_required": "Request this information from the data room or counterparty",
                "source_document": ", ".join(docs_analyzed[:3]) if docs_analyzed else "No documents",
                "pass": 2,
                "folder_category": folder_category,
                "documents_analyzed_count": len(docs_analyzed),
            }

            gap_findings.append(gap_finding)
            gap_id += 1

    return gap_findings


def _build_reference_context(reference_docs: List[LoadedDocument]) -> str:
    """Build context string from reference documents."""
    if not reference_docs:
        return "[No reference documents provided]"

    sections = []
    for doc in reference_docs:
        # Include full text of reference docs (they're critical)
        sections.append(f"""
--- REFERENCE: {doc.filename} ({doc.doc_type.upper()}) ---
{doc.text[:30000]}
--- END {doc.filename} ---
""")

    return "\n\n".join(sections)


def filter_findings_by_severity(
    findings: List[Dict],
    min_severity: str = "medium"
) -> List[Dict]:
    """Filter findings to only include those at or above minimum severity."""
    severity_order = ["low", "medium", "high", "critical"]
    min_index = severity_order.index(min_severity)

    return [
        f for f in findings
        if severity_order.index(f.get("severity", "low")) >= min_index
    ]


def filter_findings_by_deal_impact(
    findings: List[Dict],
    deal_impacts: List[str]
) -> List[Dict]:
    """Filter findings by deal impact classification."""
    return [
        f for f in findings
        if f.get("deal_impact") in deal_impacts
    ]


def group_findings_by_category(findings: List[Dict]) -> Dict[str, List[Dict]]:
    """Group findings by category."""
    by_category = {}
    for finding in findings:
        category = finding.get("category", "other")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(finding)
    return by_category


def group_findings_by_document(findings: List[Dict]) -> Dict[str, List[Dict]]:
    """Group findings by source document."""
    by_doc = {}
    for finding in findings:
        doc = finding.get("source_document", "unknown")
        if doc not in by_doc:
            by_doc[doc] = []
        by_doc[doc].append(finding)
    return by_doc


def get_deal_blockers(findings: List[Dict]) -> List[Dict]:
    """Get findings classified as deal blockers."""
    return [f for f in findings if f.get("deal_impact") == "deal_blocker"]


def get_conditions_precedent(findings: List[Dict]) -> List[Dict]:
    """Get findings classified as conditions precedent."""
    return [f for f in findings if f.get("deal_impact") == "condition_precedent"]


def summarize_findings(findings: List[Dict]) -> Dict[str, Any]:
    """Generate summary statistics for findings."""
    return {
        "total": len(findings),
        "by_severity": {
            "critical": len([f for f in findings if f.get("severity") == "critical"]),
            "high": len([f for f in findings if f.get("severity") == "high"]),
            "medium": len([f for f in findings if f.get("severity") == "medium"]),
            "low": len([f for f in findings if f.get("severity") == "low"]),
        },
        "by_deal_impact": {
            "deal_blocker": len([f for f in findings if f.get("deal_impact") == "deal_blocker"]),
            "condition_precedent": len([f for f in findings if f.get("deal_impact") == "condition_precedent"]),
            "price_chip": len([f for f in findings if f.get("deal_impact") == "price_chip"]),
            "warranty_indemnity": len([f for f in findings if f.get("deal_impact") == "warranty_indemnity"]),
            "post_closing": len([f for f in findings if f.get("deal_impact") == "post_closing"]),
            "noted": len([f for f in findings if f.get("deal_impact") == "noted"]),
        },
        "by_category": {
            cat: len(items)
            for cat, items in group_findings_by_category(findings).items()
        },
    }


# Alias for parallel processing compatibility
analyze_single_document = analyze_document
