"""
Optimized Pass 3: Clustered cross-document analysis.

Instead of putting ALL documents in one context (expensive, may exceed limits),
this version:
1. Groups documents into logical clusters (corporate, financial, operational, etc.)
2. Analyzes each cluster separately
3. Performs cross-cluster synthesis at the end

Cost savings: ~70% reduction in tokens vs all-at-once approach
Quality improvement: Better focused analysis within related document types

Architecture:
- Each cluster gets its own Claude call with relevant cross-doc questions
- Corporate governance cluster is processed first (provides reference context)
- Findings from earlier clusters inform later cluster analysis
- Final synthesis combines all cluster findings

Phase 3 Enhancement:
- Uses FOLDER_TO_CLUSTER_MAP to group documents by folder category
- Folder-specific cross_doc_checks from blueprint take precedence
- 99_Needs_Review documents are skipped
- Findings include folder context and cross-document metadata
"""

from typing import Dict, List, Any, Optional, Callable
import logging
import json

from .claude_client import ClaudeClient
from .document_clusters import (
    DOCUMENT_CLUSTERS,
    group_documents_by_cluster,
    get_cross_doc_questions_for_cluster,
    get_cluster_processing_order,
    get_cluster_info,
    get_cluster_summary,
)
from config.question_loader import (
    QuestionLoader,
    FOLDER_TO_CLUSTER_MAP,
    get_cluster_for_folder,
    should_skip_folder,
)

# Phase 4 imports for compression + batching
from .compression_engine import CompressedDocument
from .batch_manager import (
    BatchPlan,
    DocumentBatch,
    BatchStrategy,
    should_use_batching,
    create_batch_plan,
    get_batch_stats,
)
from .document_priority import DocumentPriority

# Hybrid switch threshold
BATCHING_THRESHOLD = 75  # Use batching if doc_count >= this value

logger = logging.getLogger(__name__)


def build_cluster_context(
    documents: List[Dict],
    pass1_extractions: Dict[str, Dict],
    max_chars_per_doc: int = 15000
) -> str:
    """
    Build context for a cluster using Pass 1 extractions + truncated full text.

    Instead of full 25k chars per doc, we use:
    - Pass 1 extraction summary (~500 chars)
    - Truncated full text (~10-15k chars)

    This cuts context by ~40% while preserving key information.
    """
    context_parts = []

    for doc in documents:
        doc_id = doc.get("doc_id", doc.get("filename", "unknown"))
        filename = doc.get("filename", "Unknown")
        text = doc.get("text", "")[:max_chars_per_doc]

        # Get Pass 1 extraction if available
        extraction = pass1_extractions.get(str(doc_id), {})

        # Format extraction summary
        extraction_summary = ""
        if extraction:
            parties = extraction.get("parties", [])
            parties_str = ", ".join([p.get("name", "") for p in parties[:3]]) if parties else "Not extracted"

            key_dates = extraction.get("key_dates", [])
            dates_str = "; ".join([f"{d.get('date', '')}: {d.get('description', '')[:50]}" for d in key_dates[:3]]) if key_dates else "Not extracted"

            coc = extraction.get("change_of_control_clauses", [])
            coc_str = "; ".join([f"{c.get('trigger_threshold', '')}: {c.get('consequence', '')[:50]}" for c in coc[:2]]) if coc else "None found"

            consents = extraction.get("consent_requirements", [])
            consent_str = "; ".join([f"{c.get('consent_from', '')}: {c.get('action_requiring_consent', '')[:40]}" for c in consents[:3]]) if consents else "None found"

            extraction_summary = f"""
KEY EXTRACTED DATA (from initial analysis):
- Parties: {parties_str}
- Key Dates: {dates_str}
- Change of Control: {coc_str}
- Consent Requirements: {consent_str}
"""

        doc_context = f"""
{'='*60}
DOCUMENT: {filename}
{'='*60}
{extraction_summary}
FULL TEXT:
{text}
"""
        context_parts.append(doc_context)

    return "\n".join(context_parts)


def group_documents_by_folder_cluster(documents: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Phase 3: Group documents into clusters based on folder_category.

    Uses FOLDER_TO_CLUSTER_MAP to assign folders to clusters.
    Documents without folder_category fall back to doc_type-based clustering.
    99_Needs_Review documents are excluded.

    Args:
        documents: List of document dicts with optional 'folder_category'

    Returns:
        Dict mapping cluster_name -> list of documents
    """
    clusters: Dict[str, List[Dict]] = {name: [] for name in DOCUMENT_CLUSTERS.keys()}

    for doc in documents:
        folder_category = doc.get("folder_category")

        # Phase 3: Skip 99_Needs_Review
        if folder_category and should_skip_folder(folder_category):
            logger.debug(f"Skipping {doc.get('filename')} - in {folder_category}")
            continue

        # Phase 3: Try folder-based clustering first
        if folder_category:
            cluster_name = get_cluster_for_folder(folder_category)
            if cluster_name and cluster_name in clusters:
                clusters[cluster_name].append(doc)
                continue

        # Fall back to doc_type-based clustering
        doc_type = doc.get("doc_type", "other")
        filename = doc.get("filename", "")
        from .document_clusters import classify_document_to_cluster
        cluster_name = classify_document_to_cluster(doc_type, filename)
        clusters[cluster_name].append(doc)

    # Remove empty clusters
    return {k: v for k, v in clusters.items() if v}


def get_folder_cross_doc_checks(
    folder_categories: List[str],
    question_loader: Optional[QuestionLoader] = None
) -> List[str]:
    """
    Phase 3: Get cross-document checks for folders in a cluster.

    Aggregates cross_doc_checks from all folder categories that map to
    the same cluster.

    Args:
        folder_categories: List of folder categories in the cluster
        question_loader: QuestionLoader instance

    Returns:
        List of cross-document check questions
    """
    if not question_loader:
        return []

    checks = []
    seen_checks = set()

    for folder in folder_categories:
        folder_checks = question_loader.get_cross_doc_checks_for_folder(folder)
        for check in folder_checks:
            check_text = check.get("check", "")
            if check_text and check_text not in seen_checks:
                seen_checks.add(check_text)
                # Include related folder context if available
                related = check.get("related_folders", [])
                if related:
                    checks.append(f"{check_text} (involves: {', '.join(related)})")
                else:
                    checks.append(check_text)

    return checks


def build_cluster_analysis_prompt(
    cluster_name: str,
    cluster_context: str,
    questions: List[str],
    reference_findings: Optional[List[Dict]] = None,
    blueprint: Optional[Dict] = None
) -> str:
    """Build the prompt for analyzing a single cluster."""

    cluster_info = get_cluster_info(cluster_name)
    cluster_description = cluster_info.description if cluster_info else cluster_name

    questions_text = "\n".join(f"- {q}" for q in questions)

    # Include findings from previous clusters as context
    prior_context = ""
    if reference_findings:
        prior_findings = "\n".join(
            f"- [{f.get('severity', 'unknown').upper()}] {f.get('description', '')[:150]}"
            for f in reference_findings[:10]  # Limit to top 10
        )
        prior_context = f"""
RELEVANT FINDINGS FROM OTHER DOCUMENT GROUPS:
{prior_findings}

Consider how these findings may relate to or compound issues in this document group.
"""

    # Get deal blockers from blueprint
    deal_blockers_context = ""
    if blueprint and blueprint.get("deal_blockers"):
        blockers = [f"- {b.get('description', '')}" for b in blueprint.get("deal_blockers", [])[:5]]
        deal_blockers_context = f"""
DEAL BLOCKER DEFINITIONS FOR THIS TRANSACTION TYPE:
{chr(10).join(blockers)}
"""

    return f"""You are a senior M&A lawyer conducting cross-document due diligence analysis.

DOCUMENT GROUP: {cluster_name.replace('_', ' ').title()} - {cluster_description}
{deal_blockers_context}
{prior_context}

DOCUMENTS IN THIS GROUP:
{cluster_context}

CROSS-DOCUMENT ANALYSIS QUESTIONS:
{questions_text}

YOUR TASK:
Analyze these documents TOGETHER to identify:
1. CONFLICTS - Where documents contradict each other
2. GAPS - Information missing that should be present
3. CASCADING RISKS - How an issue in one document affects others
4. CUMULATIVE EXPOSURE - Total financial/legal exposure across documents

For each finding, provide:
- Clear description of the issue
- Which documents are involved
- Severity (critical/high/medium/low)
- Financial exposure if quantifiable (SHOW YOUR CALCULATION)
- Recommended action

OUTPUT FORMAT (JSON):
{{
    "cluster_name": "{cluster_name}",
    "cross_doc_findings": [
        {{
            "finding_id": "CD001",
            "finding_type": "conflict|gap|cascade|cumulative",
            "severity": "critical|high|medium|low",
            "description": "Clear description of the cross-document issue",
            "documents_involved": ["doc1.pdf", "doc2.pdf"],
            "clause_references": ["Clause 5.1 of MOI", "Clause 3.2 of SHA"],
            "evidence": "Specific quotes or references from the documents",
            "financial_exposure": {{
                "amount": null,
                "currency": "ZAR",
                "calculation": "How you calculated this amount"
            }},
            "deal_impact": "deal_blocker|condition_precedent|price_chip|warranty_indemnity|noted",
            "action_required": "What needs to be done to resolve this",
            "action_priority": "critical|high|medium|low",
            "responsible_party": "buyer|seller|third_party"
        }}
    ],
    "cluster_summary": "2-3 sentence summary of this document group's key issues",
    "key_risks": ["List of key risks from this cluster"],
    "consent_requirements": [
        {{
            "consent_from": "Who",
            "for_what": "Action requiring consent",
            "source_document": "Which document requires this",
            "is_blocking": true
        }}
    ]
}}
"""


def build_cross_cluster_synthesis_prompt(
    cluster_findings: Dict[str, List[Dict]],
    pass1_summary: str,
    blueprint: Optional[Dict] = None
) -> str:
    """
    Build prompt for final cross-cluster synthesis.
    This identifies issues that span multiple clusters.
    """

    # Summarize findings from each cluster
    cluster_summaries = []
    for cluster_name, findings in cluster_findings.items():
        if findings:
            findings_text = "\n".join(
                f"  - [{f.get('severity', 'unknown').upper()}] {f.get('description', '')[:120]}"
                for f in findings[:8]  # Limit per cluster
            )
            cluster_summaries.append(f"""
{cluster_name.replace('_', ' ').upper()}:
{findings_text}
""")

    all_summaries = "\n".join(cluster_summaries)

    # Get deal blocker definitions from blueprint
    deal_blocker_context = ""
    if blueprint and blueprint.get("deal_blockers"):
        blockers = [f"- {b.get('description', '')}" for b in blueprint.get("deal_blockers", [])[:8]]
        deal_blocker_context = f"""
DEAL BLOCKER DEFINITIONS:
{chr(10).join(blockers)}
"""

    return f"""You are a senior M&A partner synthesizing cross-document due diligence findings.

TRANSACTION OVERVIEW:
{pass1_summary[:3000]}
{deal_blocker_context}

FINDINGS BY DOCUMENT GROUP:
{all_summaries}

YOUR TASK:
Analyze these findings ACROSS document groups to identify:

1. CHANGE OF CONTROL CASCADE
   - Map how CoC triggers in one agreement cascade to others
   - Calculate total notification timeline required
   - Identify which consents are blocking vs parallel

2. TOTAL FINANCIAL EXPOSURE
   - Sum all quantified exposures across clusters
   - Identify any double-counting
   - Flag unquantified but potentially material risks

3. CONDITION PRECEDENT REGISTER
   - List all CPs needed before closing
   - Identify dependencies between CPs
   - Flag any CPs that are deal blockers if not obtained

4. CROSS-CLUSTER CONFLICTS
   - Issues where findings in one cluster conflict with another
   - Example: Employment severance vs Financial covenant headroom

OUTPUT FORMAT (JSON):
{{
    "coc_cascade": {{
        "total_triggers": 0,
        "notification_timeline_days": 0,
        "blocking_consents": ["list of consents that must be obtained"],
        "parallel_consents": ["list of consents that can be obtained in parallel"],
        "cascade_sequence": ["First: X", "Then: Y", "Finally: Z"]
    }},
    "total_financial_exposure": {{
        "quantified_total": 0,
        "currency": "ZAR",
        "breakdown": [
            {{"category": "Severance", "amount": 0, "source": "Employment cluster"}},
            {{"category": "Liquidated damages", "amount": 0, "source": "Commercial cluster"}}
        ],
        "unquantified_risks": ["list of risks that could not be quantified"]
    }},
    "conditions_precedent": [
        {{
            "cp_id": "CP001",
            "description": "Description of the condition",
            "source_document": "Which document requires this",
            "source_cluster": "Which cluster",
            "responsible_party": "buyer|seller|third_party",
            "estimated_timeline_days": 30,
            "dependencies": ["CP002"],
            "is_deal_blocker": true,
            "risk_of_not_obtaining": "What happens if not obtained"
        }}
    ],
    "cross_cluster_conflicts": [
        {{
            "conflict_id": "CC001",
            "description": "Description of the cross-cluster conflict",
            "clusters_involved": ["financial", "employment"],
            "severity": "critical|high|medium|low",
            "resolution_required": "What needs to happen to resolve"
        }}
    ],
    "deal_assessment": {{
        "proceed": "yes|conditional|no",
        "rationale": "Brief explanation of the recommendation",
        "key_blockers": ["list of items that must be resolved"],
        "critical_actions": ["list of critical actions before closing"]
    }},
    "executive_summary": "2-3 paragraph executive summary of key cross-document findings"
}}
"""


def analyze_cluster(
    cluster_name: str,
    cluster_docs: List[Dict],
    pass1_extractions: Dict[str, Dict],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    reference_findings: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Analyze a single cluster of documents for cross-document issues.

    Args:
        cluster_name: Name of the cluster (e.g., 'corporate_governance', 'finance')
        cluster_docs: List of documents in this cluster
        pass1_extractions: Output from Pass 1 (for context compression)
        blueprint: Transaction-type blueprint
        client: Claude client instance
        reference_findings: Findings from previously processed clusters (optional)

    Returns:
        Dict with 'cross_doc_findings' list
    """
    if not cluster_docs:
        return {"cross_doc_findings": []}

    system_prompt = """You are a senior M&A lawyer conducting cross-document due diligence.
Focus on issues that are only visible when comparing documents together.
Be specific with clause references and quantify financial exposure where possible.
Always show your calculation for any financial figures.
Output valid JSON only."""

    # Build context (using Pass 1 extractions for efficiency)
    context = build_cluster_context(cluster_docs, pass1_extractions)

    # Get questions for this cluster
    questions = get_cross_doc_questions_for_cluster(cluster_name, blueprint)

    # Build and execute prompt
    prompt = build_cluster_analysis_prompt(
        cluster_name,
        context,
        questions,
        reference_findings,
        blueprint
    )

    result = client.complete_crossdoc(prompt, system_prompt)

    if "error" in result:
        logger.warning(f"Cluster '{cluster_name}' analysis failed: {result.get('error')}")
        return {"cross_doc_findings": []}

    findings = result.get("cross_doc_findings", [])

    # Add cluster name to each finding for tracking
    for f in findings:
        f["source_cluster"] = cluster_name
        f["analysis_pass"] = 3

    return {"cross_doc_findings": findings}


def run_pass3_clustered(
    documents: List[Dict],
    pass1_extractions: Dict[str, Dict],
    pass2_findings: List[Dict],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    checkpoint_callback: Optional[Callable] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run optimized Pass 3 with document clustering.

    Phase 3 Enhancement:
    - Uses folder-based clustering when documents have folder_category
    - Folder-specific cross_doc_checks from blueprint take precedence
    - 99_Needs_Review documents are automatically excluded
    - Findings include folder context and is_cross_document metadata

    Args:
        documents: All documents with text content (with optional 'folder_category')
        pass1_extractions: Output from Pass 1 (for context compression)
        pass2_findings: Output from Pass 2 (for reference)
        blueprint: Transaction-type blueprint
        client: Claude client instance
        checkpoint_callback: Optional callback to save progress after each cluster
        verbose: Print progress messages

    Returns:
        Combined Pass 3 results with cross-doc findings
    """
    logger.info("Starting Pass 3: Clustered cross-document analysis")

    # Phase 3: Initialize QuestionLoader for folder-aware cross-doc checks
    question_loader = QuestionLoader(blueprint) if blueprint else None
    use_folder_clustering = any(doc.get("folder_category") for doc in documents)

    if use_folder_clustering:
        logger.info("Phase 3: Using folder-based clustering")
        clusters = group_documents_by_folder_cluster(documents)
    else:
        # Fall back to doc_type-based clustering
        clusters = group_documents_by_cluster(documents)

    if verbose:
        summary = get_cluster_summary(clusters)
        logger.info(f"Documents grouped into {summary['total_clusters']} clusters")
        for name, info in summary['clusters'].items():
            logger.info(f"  {name}: {info['document_count']} docs, ~{info['estimated_context_chars']:,} chars")

    # Process each cluster
    cluster_findings: Dict[str, List[Dict]] = {}
    processing_order = get_cluster_processing_order()

    # Track corporate governance findings as reference for other clusters
    reference_findings: List[Dict] = []

    system_prompt = """You are a senior M&A lawyer conducting cross-document due diligence.
Focus on issues that are only visible when comparing documents together.
Be specific with clause references and quantify financial exposure where possible.
Always show your calculation for any financial figures.
Output valid JSON only."""

    for cluster_name in processing_order:
        if cluster_name not in clusters:
            continue

        cluster_docs = clusters[cluster_name]
        if verbose:
            logger.info(f"[Pass 3] Processing cluster '{cluster_name}' with {len(cluster_docs)} documents")

        # Build context (using Pass 1 extractions for efficiency)
        context = build_cluster_context(cluster_docs, pass1_extractions)

        # Phase 3: Get folder-based cross-doc checks if available
        folder_categories = list(set(
            doc.get("folder_category") for doc in cluster_docs
            if doc.get("folder_category") and not should_skip_folder(doc.get("folder_category"))
        ))

        if folder_categories and question_loader:
            # Use folder-specific cross-doc checks
            folder_checks = get_folder_cross_doc_checks(folder_categories, question_loader)
            if folder_checks:
                logger.debug(f"Using {len(folder_checks)} folder-specific cross-doc checks for {cluster_name}")
                # Combine with cluster-based questions
                base_questions = get_cross_doc_questions_for_cluster(cluster_name, blueprint)
                # Folder checks take precedence, add unique base questions
                questions = folder_checks + [q for q in base_questions if q not in folder_checks]
            else:
                questions = get_cross_doc_questions_for_cluster(cluster_name, blueprint)
        else:
            # Fall back to cluster-based questions
            questions = get_cross_doc_questions_for_cluster(cluster_name, blueprint)

        # Build and execute prompt
        prompt = build_cluster_analysis_prompt(
            cluster_name,
            context,
            questions,
            reference_findings if cluster_name != "corporate_governance" else None,
            blueprint
        )

        result = client.complete_crossdoc(prompt, system_prompt)

        if "error" in result:
            logger.warning(f"Cluster '{cluster_name}' analysis failed: {result.get('error')}")
            cluster_findings[cluster_name] = []
        else:
            findings = result.get("cross_doc_findings", [])
            cluster_findings[cluster_name] = findings

            # Add cluster name and Phase 3 metadata to each finding
            for f in findings:
                f["source_cluster"] = cluster_name
                f["analysis_pass"] = 3
                f["is_cross_document"] = True
                # Store related document IDs as JSON
                docs_involved = f.get("documents_involved", [])
                if docs_involved:
                    f["related_document_ids"] = json.dumps(docs_involved)
                # Add folder context if available
                if folder_categories:
                    f["folder_category"] = folder_categories[0] if len(folder_categories) == 1 else None

            # Add to reference findings for subsequent clusters
            reference_findings.extend(findings)

            if verbose:
                logger.info(f"  Cluster '{cluster_name}' complete: {len(findings)} findings")

        # Checkpoint if callback provided
        if checkpoint_callback:
            checkpoint_callback(
                stage=f"pass3_{cluster_name}",
                data={"cluster_findings": cluster_findings}
            )

    # Cross-cluster synthesis
    if verbose:
        logger.info("[Pass 3] Running cross-cluster synthesis")

    # Build summary from Pass 1 for synthesis context
    pass1_summary_parts = []
    for doc in documents[:10]:  # Limit to first 10 docs
        doc_id = doc.get("doc_id", doc.get("filename"))
        extraction = pass1_extractions.get(str(doc_id), {})
        if extraction:
            pass1_summary_parts.append(
                f"- {doc.get('filename', 'Unknown')}: "
                f"{len(extraction.get('parties', []))} parties, "
                f"{len(extraction.get('change_of_control_clauses', []))} CoC clauses"
            )
    pass1_summary = "\n".join(pass1_summary_parts)

    synthesis_prompt = build_cross_cluster_synthesis_prompt(
        cluster_findings,
        pass1_summary,
        blueprint
    )

    synthesis_result = client.complete_crossdoc(synthesis_prompt, system_prompt)

    if "error" in synthesis_result:
        logger.warning(f"Cross-cluster synthesis failed: {synthesis_result.get('error')}")
        synthesis_result = {}

    # Combine all findings
    all_cross_doc_findings = []
    for findings in cluster_findings.values():
        all_cross_doc_findings.extend(findings)

    # Add synthesis findings
    for cp in synthesis_result.get("conditions_precedent", []):
        all_cross_doc_findings.append({
            "finding_id": cp.get("cp_id", ""),
            "finding_type": "condition_precedent",
            "severity": "critical" if cp.get("is_deal_blocker") else "high",
            "description": cp.get("description", ""),
            "deal_impact": "deal_blocker" if cp.get("is_deal_blocker") else "condition_precedent",
            "source_cluster": "synthesis",
            "analysis_pass": 3,
        })

    for conflict in synthesis_result.get("cross_cluster_conflicts", []):
        all_cross_doc_findings.append({
            "finding_id": conflict.get("conflict_id", ""),
            "finding_type": "cross_cluster_conflict",
            "severity": conflict.get("severity", "medium"),
            "description": conflict.get("description", ""),
            "source_cluster": "synthesis",
            "analysis_pass": 3,
        })

    if verbose:
        logger.info(f"[Pass 3] Complete: {len(all_cross_doc_findings)} total cross-doc findings")

    return {
        "cluster_findings": cluster_findings,
        "cross_cluster_synthesis": synthesis_result,
        "all_cross_doc_findings": all_cross_doc_findings,
        "coc_cascade": synthesis_result.get("coc_cascade", {}),
        "total_financial_exposure": synthesis_result.get("total_financial_exposure", {}),
        "conditions_precedent": synthesis_result.get("conditions_precedent", []),
        "cross_cluster_conflicts": synthesis_result.get("cross_cluster_conflicts", []),
        "deal_assessment": synthesis_result.get("deal_assessment", {}),
        "executive_summary": synthesis_result.get("executive_summary", ""),
    }


def convert_to_finding_format(pass3_results: Dict[str, Any]) -> List[Dict]:
    """
    Convert Pass 3 results to standard finding format for database storage.

    This maps the cross-doc findings to the format expected by
    create_finding_objects_from_data() in the main orchestrator.
    """
    findings = []

    for finding in pass3_results.get("all_cross_doc_findings", []):
        # Map severity to status
        severity_to_status = {
            "critical": "Red",
            "high": "Red",
            "medium": "Amber",
            "low": "Green"
        }

        # Map deal_impact
        deal_impact_map = {
            "deal_blocker": "deal_blocker",
            "condition_precedent": "condition_precedent",
            "price_chip": "price_chip",
            "warranty_indemnity": "warranty_indemnity",
            "noted": "noted",
        }

        financial = finding.get("financial_exposure", {})

        findings.append({
            "finding_id": finding.get("finding_id", ""),
            "category": "cross_document",
            "detail": finding.get("finding_type", ""),
            "phrase": finding.get("description", ""),
            "page_number": "N/A",
            "status": severity_to_status.get(finding.get("severity", "medium"), "Amber"),
            "finding_type": "negative" if finding.get("severity") in ["critical", "high"] else "neutral",
            "confidence_score": 0.85,
            "requires_action": finding.get("action_required") is not None,
            "action_priority": finding.get("action_priority", "medium"),
            "direct_answer": finding.get("description", ""),
            "evidence_quote": finding.get("evidence", ""),
            "deal_impact": deal_impact_map.get(finding.get("deal_impact", ""), "noted"),
            "financial_exposure_amount": financial.get("amount") if financial else None,
            "financial_exposure_currency": financial.get("currency", "ZAR") if financial else "ZAR",
            "financial_exposure_calculation": financial.get("calculation") if financial else None,
            "clause_reference": ", ".join(finding.get("clause_references", [])) if finding.get("clause_references") else None,
            "cross_doc_source": ", ".join(finding.get("documents_involved", [])) if finding.get("documents_involved") else None,
            "analysis_pass": 3,
            "source_cluster": finding.get("source_cluster", ""),
        })

    return findings


# =============================================================================
# Phase 4: Batched Execution Functions
# =============================================================================

def build_batch_context(
    batch: DocumentBatch,
    cross_batch_findings: List[Dict[str, Any]] = None
) -> str:
    """
    Build context for a batch using compressed document summaries.

    Args:
        batch: DocumentBatch with compressed documents
        cross_batch_findings: Critical/high findings from prior batches

    Returns:
        Formatted context string for the batch
    """
    context_parts = []

    # Add cross-batch context if available
    if cross_batch_findings:
        prior_context = "\n".join(
            f"- [{f.get('severity', 'unknown').upper()}] {f.get('description', '')[:150]}"
            for f in cross_batch_findings[:20]
        )
        context_parts.append(f"""
CRITICAL FINDINGS FROM PRIOR BATCHES (for cross-reference):
{prior_context}
""")

    # Add document summaries
    for doc in batch.documents:
        # Build structured document context from compressed data
        provisions = "\n  ".join(f"• {p}" for p in doc.key_provisions[:5]) if doc.key_provisions else "None extracted"
        parties = ", ".join(doc.key_parties[:5]) if doc.key_parties else "Not specified"
        dates = ", ".join(doc.key_dates[:3]) if doc.key_dates else "None noted"
        amounts = ", ".join(doc.key_amounts[:3]) if doc.key_amounts else "None specified"
        risks = "\n  ".join(f"⚠ {r}" for r in doc.risk_flags[:3]) if doc.risk_flags else "None flagged"

        priority_label = doc.priority.name
        if doc.priority == DocumentPriority.CRITICAL:
            priority_marker = "🔴 CRITICAL"
        elif doc.priority == DocumentPriority.HIGH:
            priority_marker = "🟠 HIGH PRIORITY"
        else:
            priority_marker = f"[{priority_label}]"

        doc_context = f"""
{'='*60}
{priority_marker} DOCUMENT: {doc.document_name}
Folder: {doc.folder_category} | Type: {doc.document_type}
{'='*60}

SUMMARY:
{doc.summary}

KEY PROVISIONS:
  {provisions}

PARTIES: {parties}
KEY DATES: {dates}
KEY AMOUNTS: {amounts}

PASS 2 FINDINGS: {doc.finding_count} issues identified
{doc.pass2_finding_summary if doc.pass2_finding_summary else "No significant findings"}

RISK FLAGS:
  {risks}
"""
        context_parts.append(doc_context)

    return "\n".join(context_parts)


def build_batch_analysis_prompt(
    batch: DocumentBatch,
    batch_context: str,
    blueprint: Optional[Dict] = None,
    is_final_batch: bool = False
) -> str:
    """Build the prompt for analyzing a batch of compressed documents."""

    # Get deal blockers from blueprint
    deal_blockers_context = ""
    if blueprint and blueprint.get("deal_blockers"):
        blockers = [f"- {b.get('description', '')}" for b in blueprint.get("deal_blockers", [])[:5]]
        deal_blockers_context = f"""
DEAL BLOCKER DEFINITIONS FOR THIS TRANSACTION TYPE:
{chr(10).join(blockers)}
"""

    folder_list = ", ".join(batch.folders) if batch.folders else "Mixed"
    final_batch_note = """
NOTE: This is the FINAL batch. Provide a comprehensive synthesis of all findings.
""" if is_final_batch else ""

    return f"""You are a senior M&A lawyer conducting cross-document due diligence analysis.

BATCH ANALYSIS: Batch {batch.batch_id + 1}
Documents: {batch.document_count} | Folders: {folder_list}
Priority composition: {batch.critical_count} critical, {batch.high_count} high priority
{deal_blockers_context}
{final_batch_note}

DOCUMENTS IN THIS BATCH:
{batch_context}

CROSS-DOCUMENT ANALYSIS FOCUS:
1. CONFLICTS - Where documents contradict each other
2. GAPS - Information missing that should be present
3. CASCADING RISKS - How an issue in one document affects others
4. CUMULATIVE EXPOSURE - Total financial/legal exposure across documents
5. CONSENT REQUIREMENTS - Change of control and approval requirements
6. CROSS-REFERENCE ISSUES - Referenced documents or provisions not found

For each finding, provide:
- Clear description of the issue
- Which documents are involved
- Severity (critical/high/medium/low)
- Financial exposure if quantifiable (SHOW YOUR CALCULATION)
- Recommended action

OUTPUT FORMAT (JSON):
{{
    "batch_id": {batch.batch_id},
    "cross_doc_findings": [
        {{
            "finding_id": "BD{batch.batch_id:02d}-001",
            "finding_type": "conflict|gap|cascade|cumulative|consent|cross_reference",
            "severity": "critical|high|medium|low",
            "description": "Clear description of the cross-document issue",
            "documents_involved": ["doc1.pdf", "doc2.pdf"],
            "clause_references": ["Clause 5.1 of MOI", "Clause 3.2 of SHA"],
            "evidence": "Specific quotes or references from the documents",
            "financial_exposure": {{
                "amount": null,
                "currency": "ZAR",
                "calculation": "How you calculated this amount"
            }},
            "deal_impact": "deal_blocker|condition_precedent|price_chip|warranty_indemnity|noted",
            "action_required": "What needs to be done to resolve this",
            "action_priority": "critical|high|medium|low",
            "responsible_party": "buyer|seller|third_party"
        }}
    ],
    "batch_summary": "2-3 sentence summary of this batch's key issues",
    "consent_requirements": [
        {{
            "consent_from": "Who",
            "for_what": "Action requiring consent",
            "source_document": "Which document requires this",
            "is_blocking": true
        }}
    ],
    "unresolved_cross_references": ["List any referenced documents not in this batch"]
}}
"""


def analyze_batch(
    batch: DocumentBatch,
    client: ClaudeClient,
    blueprint: Optional[Dict] = None,
    cross_batch_findings: List[Dict[str, Any]] = None,
    is_final_batch: bool = False
) -> Dict[str, Any]:
    """
    Analyze a single batch of compressed documents.

    Args:
        batch: DocumentBatch with compressed documents
        client: Claude client instance
        blueprint: Transaction-type blueprint
        cross_batch_findings: Critical/high findings from prior batches
        is_final_batch: Whether this is the final batch

    Returns:
        Dict with 'cross_doc_findings' and batch metadata
    """
    if not batch.documents:
        return {"cross_doc_findings": [], "batch_id": batch.batch_id}

    system_prompt = """You are a senior M&A lawyer conducting cross-document due diligence.
You are analyzing compressed document summaries for cross-document issues.
Focus on issues that are only visible when comparing documents together.
Be specific with clause references and quantify financial exposure where possible.
Always show your calculation for any financial figures.
Output valid JSON only."""

    # Build context from compressed documents
    context = build_batch_context(batch, cross_batch_findings)

    # Build prompt
    prompt = build_batch_analysis_prompt(
        batch=batch,
        batch_context=context,
        blueprint=blueprint,
        is_final_batch=is_final_batch
    )

    result = client.complete_crossdoc(prompt, system_prompt)

    if "error" in result:
        logger.warning(f"Batch {batch.batch_id} analysis failed: {result.get('error')}")
        return {
            "cross_doc_findings": [],
            "batch_id": batch.batch_id,
            "error": result.get("error")
        }

    findings = result.get("cross_doc_findings", [])

    # Add batch metadata to each finding
    for f in findings:
        f["source_batch"] = batch.batch_id
        f["analysis_pass"] = 3
        f["is_cross_document"] = True
        f["source_cluster"] = f"batch_{batch.batch_id}"
        # Add primary folder context
        if batch.primary_folder:
            f["folder_category"] = batch.primary_folder

    return {
        "cross_doc_findings": findings,
        "batch_id": batch.batch_id,
        "batch_summary": result.get("batch_summary", ""),
        "consent_requirements": result.get("consent_requirements", []),
        "unresolved_cross_references": result.get("unresolved_cross_references", []),
    }


def run_pass3_batched(
    compressed_docs: List[CompressedDocument],
    batch_plan: BatchPlan,
    pass2_findings: List[Dict],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    checkpoint_callback: Optional[Callable] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run Pass 3 with batched execution on compressed documents.

    Phase 4 Implementation:
    - Processes documents in batches from the batch plan
    - Maintains cross-batch context for critical/high findings
    - Performs final synthesis after all batches
    - Tracks progress per batch

    Args:
        compressed_docs: List of CompressedDocument from compression engine
        batch_plan: BatchPlan from batch manager
        pass2_findings: Findings from Pass 2 (for reference)
        blueprint: Transaction-type blueprint
        client: Claude client instance
        progress_callback: Optional callback(current, total, message)
        checkpoint_callback: Optional callback to save progress
        verbose: Print progress messages

    Returns:
        Combined Pass 3 results with cross-doc findings
    """
    logger.info(f"Starting Pass 3 Batched: {batch_plan.batch_count} batches, {batch_plan.total_documents} documents")

    if verbose:
        stats = get_batch_stats(batch_plan)
        logger.info(f"  Total tokens: {stats['total_tokens']:,}")
        logger.info(f"  Avg batch size: {stats['docs_per_batch']['avg']:.1f} docs")
        logger.info(f"  Strategy: {batch_plan.strategy.value}")

    all_batch_findings: List[Dict] = []
    batch_results: Dict[int, Dict] = {}
    cross_batch_findings: List[Dict] = []

    total_batches = len(batch_plan.batches)

    for i, batch in enumerate(batch_plan.batches):
        is_final = (i == total_batches - 1)

        if verbose:
            logger.info(f"[Pass 3 Batched] Processing batch {i + 1}/{total_batches} "
                       f"({batch.document_count} docs, {batch.total_tokens:,} tokens)")

        # Get cross-batch context for this batch
        batch_cross_context = batch_plan.get_cross_batch_context(i)

        # Analyze batch
        result = analyze_batch(
            batch=batch,
            client=client,
            blueprint=blueprint,
            cross_batch_findings=batch_cross_context,
            is_final_batch=is_final
        )

        batch_results[i] = result
        findings = result.get("cross_doc_findings", [])
        all_batch_findings.extend(findings)

        # Add findings to batch plan for cross-batch context
        batch_plan.add_batch_findings(findings)

        # Track critical/high findings for cross-batch analysis
        for f in findings:
            if f.get("severity", "").lower() in ["critical", "high"]:
                cross_batch_findings.append(f)

        # Update progress
        batch_plan.completed_batches = i + 1

        if progress_callback:
            progress_callback(
                i + 1,
                total_batches,
                f"Completed batch {i + 1}: {len(findings)} findings"
            )

        if checkpoint_callback:
            checkpoint_callback(
                stage=f"pass3_batch_{i}",
                data={
                    "batch_id": i,
                    "findings_count": len(findings),
                    "completed_batches": i + 1,
                    "total_batches": total_batches
                }
            )

        if verbose:
            logger.info(f"  Batch {i + 1} complete: {len(findings)} findings "
                       f"({len([f for f in findings if f.get('severity') == 'critical'])} critical)")

    # Final synthesis across all batches
    if verbose:
        logger.info("[Pass 3 Batched] Running cross-batch synthesis")

    synthesis_result = _run_cross_batch_synthesis(
        batch_results=batch_results,
        cross_batch_findings=cross_batch_findings,
        blueprint=blueprint,
        client=client
    )

    # Add synthesis findings
    for cp in synthesis_result.get("conditions_precedent", []):
        all_batch_findings.append({
            "finding_id": cp.get("cp_id", ""),
            "finding_type": "condition_precedent",
            "severity": "critical" if cp.get("is_deal_blocker") else "high",
            "description": cp.get("description", ""),
            "deal_impact": "deal_blocker" if cp.get("is_deal_blocker") else "condition_precedent",
            "source_cluster": "synthesis",
            "source_batch": "synthesis",
            "analysis_pass": 3,
        })

    for conflict in synthesis_result.get("cross_batch_conflicts", []):
        all_batch_findings.append({
            "finding_id": conflict.get("conflict_id", ""),
            "finding_type": "cross_batch_conflict",
            "severity": conflict.get("severity", "medium"),
            "description": conflict.get("description", ""),
            "source_cluster": "synthesis",
            "source_batch": "synthesis",
            "analysis_pass": 3,
        })

    if verbose:
        logger.info(f"[Pass 3 Batched] Complete: {len(all_batch_findings)} total findings across {total_batches} batches")

    return {
        "batch_results": batch_results,
        "all_cross_doc_findings": all_batch_findings,
        "cross_batch_synthesis": synthesis_result,
        "coc_cascade": synthesis_result.get("coc_cascade", {}),
        "total_financial_exposure": synthesis_result.get("total_financial_exposure", {}),
        "conditions_precedent": synthesis_result.get("conditions_precedent", []),
        "cross_batch_conflicts": synthesis_result.get("cross_batch_conflicts", []),
        "deal_assessment": synthesis_result.get("deal_assessment", {}),
        "executive_summary": synthesis_result.get("executive_summary", ""),
        "batch_stats": get_batch_stats(batch_plan),
        "batching_enabled": True,
    }


def _run_cross_batch_synthesis(
    batch_results: Dict[int, Dict],
    cross_batch_findings: List[Dict],
    blueprint: Optional[Dict],
    client: ClaudeClient
) -> Dict[str, Any]:
    """
    Run final synthesis across all batches.

    Identifies issues that span multiple batches and creates
    comprehensive deal assessment.
    """
    # Build summary of findings from each batch
    batch_summaries = []
    for batch_id, result in sorted(batch_results.items()):
        findings = result.get("cross_doc_findings", [])
        if findings:
            findings_text = "\n".join(
                f"  - [{f.get('severity', 'unknown').upper()}] {f.get('description', '')[:120]}"
                for f in findings[:8]
            )
            batch_summaries.append(f"""
BATCH {batch_id + 1} ({len(findings)} findings):
{result.get('batch_summary', 'No summary')}

Key findings:
{findings_text}
""")

    all_summaries = "\n".join(batch_summaries)

    # Get deal blocker definitions from blueprint
    deal_blocker_context = ""
    if blueprint and blueprint.get("deal_blockers"):
        blockers = [f"- {b.get('description', '')}" for b in blueprint.get("deal_blockers", [])[:8]]
        deal_blocker_context = f"""
DEAL BLOCKER DEFINITIONS:
{chr(10).join(blockers)}
"""

    # Build critical findings summary
    critical_findings_text = "\n".join(
        f"- {f.get('description', '')[:150]}"
        for f in cross_batch_findings
        if f.get("severity") == "critical"
    )[:2000]

    prompt = f"""You are a senior M&A partner synthesizing cross-document due diligence findings from batched analysis.

{deal_blocker_context}

CRITICAL FINDINGS ACROSS ALL BATCHES:
{critical_findings_text}

BATCH ANALYSIS SUMMARIES:
{all_summaries}

YOUR TASK:
Synthesize findings across ALL batches to identify:

1. CHANGE OF CONTROL CASCADE
   - Map how CoC triggers cascade across documents
   - Calculate total notification timeline required
   - Identify which consents are blocking vs parallel

2. TOTAL FINANCIAL EXPOSURE
   - Sum all quantified exposures
   - Flag unquantified but potentially material risks

3. CONDITION PRECEDENT REGISTER
   - List all CPs needed before closing
   - Flag any CPs that are deal blockers

4. CROSS-BATCH CONFLICTS
   - Issues where findings in one batch conflict with another

OUTPUT FORMAT (JSON):
{{
    "coc_cascade": {{
        "total_triggers": 0,
        "notification_timeline_days": 0,
        "blocking_consents": ["list"],
        "parallel_consents": ["list"]
    }},
    "total_financial_exposure": {{
        "quantified_total": 0,
        "currency": "ZAR",
        "unquantified_risks": ["list"]
    }},
    "conditions_precedent": [
        {{
            "cp_id": "CP001",
            "description": "Description",
            "is_deal_blocker": true
        }}
    ],
    "cross_batch_conflicts": [
        {{
            "conflict_id": "CB001",
            "description": "Description",
            "batches_involved": [0, 2],
            "severity": "high"
        }}
    ],
    "deal_assessment": {{
        "proceed": "yes|conditional|no",
        "rationale": "Brief explanation",
        "key_blockers": ["list"],
        "critical_actions": ["list"]
    }},
    "executive_summary": "2-3 paragraph executive summary"
}}
"""

    system_prompt = """You are synthesizing batched due diligence analysis.
Focus on cross-batch patterns and cumulative risks.
Output valid JSON only."""

    result = client.complete_crossdoc(prompt, system_prompt)

    if "error" in result:
        logger.warning(f"Cross-batch synthesis failed: {result.get('error')}")
        return {}

    return result


def run_pass3_hybrid(
    documents: List[Dict],
    pass1_extractions: Dict[str, Dict],
    pass2_findings: List[Dict],
    blueprint: Optional[Dict],
    client: ClaudeClient,
    compressed_docs: Optional[List[CompressedDocument]] = None,
    batch_plan: Optional[BatchPlan] = None,
    checkpoint_callback: Optional[Callable] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    verbose: bool = True,
    force_batching: bool = False
) -> Dict[str, Any]:
    """
    Hybrid Pass 3 that automatically switches between clustered and batched execution.

    Phase 4 Implementation:
    - < 75 documents: Uses original clustered approach (run_pass3_clustered)
    - >= 75 documents: Uses batched approach with compression (run_pass3_batched)

    Args:
        documents: All documents with text content
        pass1_extractions: Output from Pass 1
        pass2_findings: Output from Pass 2
        blueprint: Transaction-type blueprint
        client: Claude client instance
        compressed_docs: Pre-compressed documents (required for batched mode)
        batch_plan: Pre-computed batch plan (required for batched mode)
        checkpoint_callback: Optional callback to save progress
        progress_callback: Optional callback(current, total, message)
        verbose: Print progress messages
        force_batching: Force batched mode regardless of document count

    Returns:
        Pass 3 results (format depends on mode used)
    """
    doc_count = len(documents)
    use_batched = force_batching or should_use_batching(doc_count, BATCHING_THRESHOLD)

    if use_batched:
        if not compressed_docs or not batch_plan:
            raise ValueError(
                "Batched mode requires compressed_docs and batch_plan. "
                f"Got: compressed_docs={bool(compressed_docs)}, batch_plan={bool(batch_plan)}"
            )

        logger.info(f"[Pass 3] Using BATCHED mode for {doc_count} documents "
                   f"(threshold: {BATCHING_THRESHOLD})")

        return run_pass3_batched(
            compressed_docs=compressed_docs,
            batch_plan=batch_plan,
            pass2_findings=pass2_findings,
            blueprint=blueprint,
            client=client,
            progress_callback=progress_callback,
            checkpoint_callback=checkpoint_callback,
            verbose=verbose
        )
    else:
        logger.info(f"[Pass 3] Using CLUSTERED mode for {doc_count} documents "
                   f"(threshold: {BATCHING_THRESHOLD})")

        return run_pass3_clustered(
            documents=documents,
            pass1_extractions=pass1_extractions,
            pass2_findings=pass2_findings,
            blueprint=blueprint,
            client=client,
            checkpoint_callback=checkpoint_callback,
            verbose=verbose
        )
