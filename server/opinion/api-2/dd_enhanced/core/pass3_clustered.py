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
"""

from typing import Dict, List, Any, Optional, Callable
import logging

from .claude_client import ClaudeClient
from .document_clusters import (
    DOCUMENT_CLUSTERS,
    group_documents_by_cluster,
    get_cross_doc_questions_for_cluster,
    get_cluster_processing_order,
    get_cluster_info,
    get_cluster_summary,
)

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

    Args:
        documents: All documents with text content
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

    # Group documents into clusters
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

        # Get questions for this cluster
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

            # Add cluster name to each finding for tracking
            for f in findings:
                f["source_cluster"] = cluster_name
                f["analysis_pass"] = 3

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
