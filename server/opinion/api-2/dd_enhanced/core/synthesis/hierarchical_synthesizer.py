"""
Hierarchical synthesis engine for aggregating findings from parallel processing.

Synthesizes findings in layers:
- Batch → Cluster → Cross-Cluster → Deal

This approach:
1. Manages context window constraints
2. Enables parallel batch processing
3. Produces coherent, deduplicated findings
4. Generates executive-level summaries

Model selection:
- Sonnet by default
- Opus for 300+ docs or when explicitly requested
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging
import os

logger = logging.getLogger(__name__)


class SynthesisLevel(Enum):
    BATCH = "batch"
    CLUSTER = "cluster"
    CROSS_CLUSTER = "cross_cluster"
    DEAL = "deal"


@dataclass
class SynthesisResult:
    """Result from a synthesis operation."""
    level: SynthesisLevel
    source_ids: List[str]
    summary: str
    key_risks: List[Dict[str, Any]] = field(default_factory=list)
    deal_blockers: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    findings_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model_used: str = "sonnet"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level.value,
            'source_ids': self.source_ids,
            'summary': self.summary,
            'key_risks': self.key_risks,
            'deal_blockers': self.deal_blockers,
            'recommendations': self.recommendations,
            'patterns': self.patterns,
            'gaps': self.gaps,
            'findings_count': self.findings_count,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'model_used': self.model_used,
            'created_at': self.created_at.isoformat()
        }


class HierarchicalSynthesizer:
    """
    Synthesizes findings in hierarchical layers to manage context window.

    Flow:
    1. Batch synthesis - Aggregate findings within each batch
    2. Cluster synthesis - Aggregate batches within each document cluster
    3. Cross-cluster synthesis - Find issues spanning clusters
    4. Deal synthesis - Final executive summary
    """

    def __init__(self, claude_client):
        self.claude_client = claude_client
        self.default_model = "sonnet"
        self.large_doc_threshold = int(os.environ.get("DD_OPUS_THRESHOLD", "300"))

    def _get_model(
        self,
        document_count: int = 0,
        synthesis_model: Optional[str] = None
    ) -> str:
        """Determine which model to use based on doc count and preference."""
        if synthesis_model and synthesis_model.lower() in ['opus', 'sonnet']:
            return synthesis_model.lower()

        if document_count >= self.large_doc_threshold:
            return "opus"

        return self.default_model

    def synthesize_batch(
        self,
        batch_id: str,
        findings: List[Dict[str, Any]],
        batch_context: Dict[str, Any]
    ) -> SynthesisResult:
        """
        Synthesize findings from a single batch.
        This is typically done within the batch analysis job itself.
        """
        # Group findings by severity
        by_severity = {'critical': [], 'high': [], 'medium': [], 'low': []}
        for f in findings:
            severity = f.get('severity', 'medium').lower()
            if severity in by_severity:
                by_severity[severity].append(f)

        # Deduplicate within batch
        deduplicated = self._deduplicate_findings(findings)

        prompt = f"""You are synthesizing due diligence findings from a document batch.

BATCH: {batch_id}
DOCUMENTS IN BATCH: {batch_context.get('document_count', len(batch_context.get('documents', [])))}
CLUSTER: {batch_context.get('cluster', 'Unknown')}

FINDINGS BY SEVERITY:
- Critical: {len(by_severity['critical'])}
- High: {len(by_severity['high'])}
- Medium: {len(by_severity['medium'])}
- Low: {len(by_severity['low'])}
- Total (after deduplication): {len(deduplicated)}

DETAILED FINDINGS:
{self._format_findings(deduplicated[:30])}

SYNTHESIS INSTRUCTIONS:
1. Identify the TOP 5 most significant findings in this batch
2. Flag any potential DEAL BLOCKERS
3. Note any PATTERNS (recurring issues, common themes)
4. Identify any GAPS (expected issues not found)

Respond in JSON format:
{{
    "batch_summary": "<2-3 sentence summary of this batch>",
    "top_findings": [
        {{
            "title": "<finding title>",
            "severity": "<critical|high|medium>",
            "description": "<brief description>",
            "document": "<source document>"
        }}
    ],
    "deal_blockers": ["<any potential deal blockers>"],
    "patterns": ["<recurring issues>"],
    "recommendations": ["<batch-specific recommendations>"]
}}
"""

        response = self.claude_client.complete(
            prompt=prompt,
            system="You are a legal due diligence analyst synthesizing findings. Output valid JSON only.",
            max_tokens=2000
        )

        parsed = self._parse_json_response(response)

        return SynthesisResult(
            level=SynthesisLevel.BATCH,
            source_ids=[batch_id],
            summary=parsed.get('batch_summary', ''),
            key_risks=parsed.get('top_findings', []),
            deal_blockers=parsed.get('deal_blockers', []),
            recommendations=parsed.get('recommendations', []),
            patterns=parsed.get('patterns', []),
            findings_count=len(deduplicated)
        )

    def synthesize_cluster(
        self,
        cluster_id: str,
        batch_results: List[SynthesisResult],
        cluster_context: Dict[str, Any]
    ) -> SynthesisResult:
        """
        Synthesize findings from multiple batches within a single cluster.
        """
        # Aggregate from batch results
        all_risks = []
        all_deal_blockers = []
        all_patterns = []
        all_recommendations = []
        total_findings = 0

        batch_summaries = []
        for result in batch_results:
            batch_summaries.append(f"**{result.source_ids[0]}**: {result.summary}")
            all_risks.extend(result.key_risks)
            all_deal_blockers.extend(result.deal_blockers)
            all_patterns.extend(result.patterns)
            all_recommendations.extend(result.recommendations)
            total_findings += result.findings_count

        # Deduplicate across batches
        unique_blockers = list(set(all_deal_blockers))
        unique_patterns = list(set(all_patterns))

        prompt = f"""You are synthesizing due diligence findings for a document cluster.

CLUSTER: {cluster_id}
CLUSTER TYPE: {cluster_context.get('cluster_type', 'Unknown')}
TOTAL DOCUMENTS: {cluster_context.get('document_count', 'Unknown')}
BATCHES ANALYZED: {len(batch_results)}
TOTAL FINDINGS: {total_findings}

BATCH SUMMARIES:
{chr(10).join(batch_summaries)}

KEY RISKS FROM BATCHES:
{self._format_risks(all_risks[:20])}

DEAL BLOCKERS IDENTIFIED:
{chr(10).join([f"- {b}" for b in unique_blockers]) if unique_blockers else "None identified"}

PATTERNS OBSERVED:
{chr(10).join([f"- {p}" for p in unique_patterns]) if unique_patterns else "None identified"}

CLUSTER SYNTHESIS INSTRUCTIONS:
1. Identify the TOP 5 most significant risks across all batches in this cluster
2. Confirm or refine DEAL BLOCKERS after cross-batch review
3. Identify SYSTEMIC PATTERNS (issues appearing across multiple batches)
4. Note any GAPS (expected issues not found, suspicious absences)
5. Provide cluster-level RECOMMENDATIONS

Respond in JSON format:
{{
    "cluster_summary": "<2-3 sentence summary of this cluster's risk profile>",
    "top_risks": [
        {{
            "risk": "<description>",
            "severity": "<critical|high|medium>",
            "batches_affected": ["<batch IDs>"],
            "mitigation": "<suggested mitigation>"
        }}
    ],
    "confirmed_deal_blockers": ["<confirmed deal blockers>"],
    "systemic_patterns": ["<patterns across batches>"],
    "gaps": ["<expected issues not found>"],
    "recommendations": ["<cluster-specific recommendations>"]
}}
"""

        response = self.claude_client.complete(
            prompt=prompt,
            system="You are a senior legal analyst synthesizing cluster-level findings. Output valid JSON only.",
            max_tokens=3000
        )

        parsed = self._parse_json_response(response)

        return SynthesisResult(
            level=SynthesisLevel.CLUSTER,
            source_ids=[cluster_id],
            summary=parsed.get('cluster_summary', ''),
            key_risks=parsed.get('top_risks', []),
            deal_blockers=parsed.get('confirmed_deal_blockers', []),
            recommendations=parsed.get('recommendations', []),
            patterns=parsed.get('systemic_patterns', []),
            gaps=parsed.get('gaps', []),
            findings_count=total_findings
        )

    def synthesize_cross_cluster(
        self,
        cluster_results: List[SynthesisResult],
        graph_insights: Dict[str, Any],
        transaction_type: str = "M&A"
    ) -> SynthesisResult:
        """
        Synthesize findings across all clusters to find cross-cutting issues.
        """
        cluster_summaries = []
        all_deal_blockers = []
        all_key_risks = []
        all_patterns = []
        total_findings = 0

        for result in cluster_results:
            cluster_summaries.append(f"**{result.source_ids[0]}**: {result.summary}")
            all_deal_blockers.extend(result.deal_blockers)
            all_key_risks.extend(result.key_risks)
            all_patterns.extend(result.patterns)
            total_findings += result.findings_count

        # Build graph insights section
        graph_section = self._format_graph_insights(graph_insights)

        prompt = f"""You are performing cross-cluster synthesis for a {transaction_type} due diligence review.

CLUSTERS ANALYZED: {len(cluster_results)}
TOTAL FINDINGS: {total_findings}

CLUSTER SUMMARIES:
{chr(10).join(cluster_summaries)}

AGGREGATED DEAL BLOCKERS:
{chr(10).join([f"- {b}" for b in list(set(all_deal_blockers))]) if all_deal_blockers else "None identified"}

TOP RISKS ACROSS CLUSTERS:
{self._format_risks(all_key_risks[:25])}

{graph_section}

CROSS-CLUSTER ANALYSIS INSTRUCTIONS:
1. Identify issues that SPAN MULTIPLE CLUSTERS
2. Assess CUMULATIVE RISK - how do issues compound?
3. Identify INTERDEPENDENCIES between clusters
4. Prioritize the OVERALL TOP 10 risks
5. Confirm final DEAL BLOCKERS after cross-cluster review
6. Provide TRANSACTION-LEVEL recommendations

Respond in JSON format:
{{
    "cross_cluster_issues": [
        {{
            "issue": "<cross-cutting issue>",
            "affected_clusters": ["<cluster IDs>"],
            "severity": "<critical|high|medium>",
            "cumulative_impact": "<how issues compound>"
        }}
    ],
    "top_10_risks": [
        {{
            "rank": 1,
            "risk": "<description>",
            "severity": "<critical|high>",
            "clusters_affected": ["<cluster IDs>"],
            "mitigation": "<recommendation>"
        }}
    ],
    "confirmed_deal_blockers": ["<final confirmed deal blockers>"],
    "transaction_recommendations": ["<overall recommendations>"],
    "overall_risk_assessment": "<low|medium|high|critical>"
}}
"""

        response = self.claude_client.complete(
            prompt=prompt,
            system="You are a partner-level legal analyst performing transaction-wide synthesis. Output valid JSON only.",
            max_tokens=4000
        )

        parsed = self._parse_json_response(response)

        return SynthesisResult(
            level=SynthesisLevel.CROSS_CLUSTER,
            source_ids=[r.source_ids[0] for r in cluster_results],
            summary=f"Overall risk: {parsed.get('overall_risk_assessment', 'Unknown')}",
            key_risks=parsed.get('top_10_risks', []),
            deal_blockers=parsed.get('confirmed_deal_blockers', []),
            recommendations=parsed.get('transaction_recommendations', []),
            patterns=parsed.get('cross_cluster_issues', []),
            findings_count=total_findings
        )

    def synthesize_deal(
        self,
        cross_cluster_result: SynthesisResult,
        transaction_context: Dict[str, Any],
        document_stats: Dict[str, Any],
        synthesis_model: Optional[str] = None
    ) -> SynthesisResult:
        """
        Final deal-level synthesis - executive summary for the DD report.
        """
        total_docs = document_stats.get('total_documents', 0)
        model = self._get_model(total_docs, synthesis_model)

        prompt = f"""You are preparing the executive summary for a due diligence report.

TRANSACTION: {transaction_context.get('transaction_type', 'M&A')}
TARGET: {transaction_context.get('target_name', 'Target Company')}
TRANSACTION VALUE: {transaction_context.get('value', 'Not disclosed')}
CLIENT: {transaction_context.get('client_name', 'Client')}

DOCUMENT STATISTICS:
- Total Documents Reviewed: {total_docs}
- Document Categories: {document_stats.get('categories', 'Various')}
- Clusters Analyzed: {len(cross_cluster_result.source_ids)}
- Total Findings: {cross_cluster_result.findings_count}

OVERALL RISK ASSESSMENT: {cross_cluster_result.summary}

TOP 10 RISKS IDENTIFIED:
{self._format_ranked_risks(cross_cluster_result.key_risks[:10])}

DEAL BLOCKERS:
{chr(10).join([f"- {b}" for b in cross_cluster_result.deal_blockers]) if cross_cluster_result.deal_blockers else "None identified"}

KEY RECOMMENDATIONS:
{chr(10).join([f"- {r}" for r in cross_cluster_result.recommendations[:10]])}

EXECUTIVE SUMMARY INSTRUCTIONS:
Write a professional executive summary suitable for senior management and the board.

The summary should include:
1. **Overall Risk Rating** - With brief justification
2. **Key Findings Summary** - 2-3 paragraphs covering major issues
3. **Critical Issues** - Items requiring immediate attention
4. **Conditions Precedent** - Recommended conditions for the transaction
5. **Further Investigation Required** - Areas needing additional review
6. **Overall Recommendation** - Proceed / Proceed with Conditions / Do Not Proceed

Write in professional legal prose. Be direct and clear. Quantify where possible.
"""

        response = self.claude_client.complete(
            prompt=prompt,
            system="You are a senior partner preparing an executive summary for a major transaction. "
                   "Write in clear, professional legal prose suitable for board presentation.",
            max_tokens=6000,
            model=model
        )

        return SynthesisResult(
            level=SynthesisLevel.DEAL,
            source_ids=['deal'],
            summary=response,  # Full executive summary
            key_risks=cross_cluster_result.key_risks,
            deal_blockers=cross_cluster_result.deal_blockers,
            recommendations=cross_cluster_result.recommendations,
            findings_count=cross_cluster_result.findings_count,
            model_used=model
        )

    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate similar findings based on title and description."""
        seen_signatures = set()
        unique = []

        for finding in findings:
            # Create signature from key fields
            title = finding.get('title', finding.get('description', ''))[:50].lower()
            finding_type = finding.get('finding_type', finding.get('type', ''))
            signature = f"{finding_type}:{title}"

            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique.append(finding)

        return unique

    def _format_findings(self, findings: List[Dict[str, Any]]) -> str:
        """Format findings for prompt inclusion."""
        lines = []
        for f in findings:
            severity = f.get('severity', 'medium').upper()
            title = f.get('title', f.get('description', 'Unknown'))[:100]
            doc = f.get('source_document', f.get('document', 'Unknown'))
            lines.append(f"- [{severity}] {title} (Source: {doc})")
        return "\n".join(lines) if lines else "No findings to display"

    def _format_risks(self, risks: List[Dict[str, Any]]) -> str:
        """Format risks for prompt inclusion."""
        lines = []
        for r in risks[:20]:  # Limit to avoid context overflow
            risk = r.get('risk', r.get('title', 'Unknown risk'))
            severity = r.get('severity', 'medium').upper()
            lines.append(f"- [{severity}] {risk}")
        return "\n".join(lines) if lines else "No risks to display"

    def _format_ranked_risks(self, risks: List[Dict[str, Any]]) -> str:
        """Format ranked risks for prompt inclusion."""
        lines = []
        for i, r in enumerate(risks, 1):
            risk = r.get('risk', r.get('title', 'Unknown risk'))
            severity = r.get('severity', 'high').upper()
            lines.append(f"{i}. [{severity}] {risk}")
        return "\n".join(lines) if lines else "No risks identified"

    def _format_graph_insights(self, graph_insights: Dict[str, Any]) -> str:
        """Format knowledge graph insights for prompt inclusion."""
        if not graph_insights:
            return ""

        sections = ["KNOWLEDGE GRAPH INSIGHTS:"]

        coc = graph_insights.get('change_of_control', {})
        if coc:
            clauses = coc.get('clauses', [])
            sections.append(f"- Change of Control Clauses: {len(clauses)} found")
            if clauses:
                sections.append(f"  Top clause: {clauses[0].get('description', 'N/A')[:100]}")

        cascade = graph_insights.get('cascade_effects', {})
        if cascade:
            affected = cascade.get('affected_agreements', [])
            sections.append(f"- Cascade Effects: {len(affected)} agreements affected")

        consent = graph_insights.get('consent_requirements', {})
        if consent:
            requirements = consent.get('requirements', [])
            sections.append(f"- Consent Requirements: {len(requirements)} found")

        parties = graph_insights.get('key_parties', {})
        if parties:
            count = parties.get('count', 0)
            sections.append(f"- Key Parties Identified: {count}")

        return "\n".join(sections) if len(sections) > 1 else ""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from Claude."""
        try:
            # Handle markdown code blocks
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]

            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {'summary': response, 'parse_error': str(e)}


def create_synthesis_pipeline(
    claude_client,
    db_session=None
) -> 'SynthesisPipeline':
    """Create a synthesis pipeline with database persistence."""
    return SynthesisPipeline(
        synthesizer=HierarchicalSynthesizer(claude_client),
        db_session=db_session
    )


class SynthesisPipeline:
    """
    Orchestrates the full hierarchical synthesis process with database persistence.
    """

    def __init__(self, synthesizer: HierarchicalSynthesizer, db_session=None):
        self.synthesizer = synthesizer
        self.db_session = db_session

    def run_full_synthesis(
        self,
        run_id: str,
        batch_findings: Dict[str, List[Dict]],  # batch_id -> findings
        cluster_config: Dict[str, List[str]],    # cluster_id -> [batch_ids]
        graph_insights: Dict[str, Any],
        transaction_context: Dict[str, Any],
        document_stats: Dict[str, Any],
        synthesis_model: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> SynthesisResult:
        """
        Run the complete hierarchical synthesis process.
        """
        # Step 1: Synthesize each batch
        if progress_callback:
            progress_callback("Synthesizing batches...")

        batch_results = {}
        for batch_id, findings in batch_findings.items():
            batch_context = {
                'batch_id': batch_id,
                'document_count': len(set(f.get('source_document') for f in findings))
            }
            result = self.synthesizer.synthesize_batch(batch_id, findings, batch_context)
            batch_results[batch_id] = result
            self._save_synthesis_result(run_id, result)

        # Step 2: Synthesize each cluster
        if progress_callback:
            progress_callback("Synthesizing clusters...")

        cluster_results = []
        for cluster_id, batch_ids in cluster_config.items():
            cluster_batch_results = [
                batch_results[bid] for bid in batch_ids
                if bid in batch_results
            ]
            if cluster_batch_results:
                cluster_context = {
                    'cluster_type': cluster_id,
                    'document_count': sum(r.findings_count for r in cluster_batch_results)
                }
                result = self.synthesizer.synthesize_cluster(
                    cluster_id, cluster_batch_results, cluster_context
                )
                cluster_results.append(result)
                self._save_synthesis_result(run_id, result)

        # Step 3: Cross-cluster synthesis
        if progress_callback:
            progress_callback("Synthesizing across clusters...")

        transaction_type = transaction_context.get('transaction_type', 'M&A')
        cross_cluster_result = self.synthesizer.synthesize_cross_cluster(
            cluster_results, graph_insights, transaction_type
        )
        self._save_synthesis_result(run_id, cross_cluster_result)

        # Step 4: Deal synthesis
        if progress_callback:
            progress_callback("Generating executive summary...")

        deal_result = self.synthesizer.synthesize_deal(
            cross_cluster_result,
            transaction_context,
            document_stats,
            synthesis_model
        )
        self._save_synthesis_result(run_id, deal_result)

        return deal_result

    def _save_synthesis_result(self, run_id: str, result: SynthesisResult):
        """Save synthesis result to database."""
        if not self.db_session:
            return

        try:
            self.db_session.execute("""
                INSERT INTO dd_synthesis_result
                (run_id, synthesis_level, source_id, source_ids, summary,
                 key_risks, deal_blockers, recommendations, patterns, gaps,
                 findings_count, model_used)
                VALUES (%(run_id)s, %(level)s, %(source_id)s, %(source_ids)s, %(summary)s,
                        %(key_risks)s, %(deal_blockers)s, %(recommendations)s,
                        %(patterns)s, %(gaps)s, %(findings_count)s, %(model_used)s)
            """, {
                'run_id': run_id,
                'level': result.level.value,
                'source_id': result.source_ids[0] if result.source_ids else None,
                'source_ids': json.dumps(result.source_ids),
                'summary': result.summary[:10000] if result.summary else None,
                'key_risks': json.dumps(result.key_risks),
                'deal_blockers': json.dumps(result.deal_blockers),
                'recommendations': json.dumps(result.recommendations),
                'patterns': json.dumps(result.patterns),
                'gaps': json.dumps(result.gaps),
                'findings_count': result.findings_count,
                'model_used': result.model_used
            })
            self.db_session.commit()
        except Exception as e:
            logger.warning(f"Failed to save synthesis result: {e}")
            try:
                self.db_session.rollback()
            except Exception:
                pass
