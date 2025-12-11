"""
DD Findings Stream Endpoint

Server-Sent Events (SSE) endpoint for streaming live findings
during DD processing. Falls back to long-polling for Azure Functions
which doesn't support true SSE.
"""
import azure.functions as func
import json
from datetime import datetime
from shared.session import transactional_session
from sqlalchemy import text


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get recent findings for a DD.

    Since Azure Functions doesn't support true SSE, this endpoint
    returns the most recent findings since a given timestamp.
    The frontend can poll this endpoint to get new findings.

    Query params:
        dd_id: UUID of the due diligence
        since: ISO timestamp to get findings after (optional)
        limit: Max number of findings to return (default 20)
    """
    try:
        dd_id = req.params.get("dd_id")
        since = req.params.get("since")
        limit = int(req.params.get("limit", "20"))

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        with transactional_session() as session:
            # Query findings from perspective_risk_finding table
            # Join through the perspective -> member -> dd chain
            # Note: Only using columns that exist in the database schema
            base_query = """
                SELECT
                    prf.id::text,
                    prf.id::text as finding_id,
                    prf.phrase as description,
                    prf.status::text as severity,
                    prf.finding_type::text,
                    prf.confidence_score,
                    prf.requires_action,
                    prf.action_priority::text,
                    prf.direct_answer,
                    prf.evidence_quote,
                    d.original_file_name as source_document,
                    pr.category
                FROM perspective_risk_finding prf
                JOIN perspective_risk pr ON prf.perspective_risk_id = pr.id
                JOIN perspective p ON pr.perspective_id = p.id
                JOIN due_diligence_member ddm ON p.member_id = ddm.id
                JOIN document d ON prf.document_id = d.id
                WHERE ddm.dd_id = :dd_id
            """

            if since:
                # Note: perspective_risk_finding doesn't have created_at, so we use id ordering
                # For now, just return latest findings
                findings_query = text(base_query + """
                    ORDER BY prf.id DESC
                    LIMIT :limit
                """)
                results = session.execute(
                    findings_query,
                    {"dd_id": dd_id, "limit": limit}
                ).fetchall()
            else:
                findings_query = text(base_query + """
                    ORDER BY prf.id DESC
                    LIMIT :limit
                """)
                results = session.execute(
                    findings_query,
                    {"dd_id": dd_id, "limit": limit}
                ).fetchall()

            # Map status to severity
            status_to_severity = {
                "Red": "high",
                "Amber": "medium",
                "Green": "low",
                "Info": "info",
                "New": "medium",
                "Deleted": "low"
            }

            # Map finding_type to deal impact
            finding_type_to_impact = {
                "negative": "noted",
                "positive": "none",
                "neutral": "none",
                "gap": "condition_precedent",
                "informational": "none"
            }

            # Map action_priority to severity
            action_priority_to_severity = {
                "critical": "high",
                "high": "high",
                "medium": "medium",
                "low": "low",
                "none": "low"
            }

            findings = []
            for row in results:
                # Use status for severity, fall back to action_priority
                severity = status_to_severity.get(row.severity, "medium")
                if row.action_priority:
                    severity = action_priority_to_severity.get(row.action_priority, severity)

                finding = {
                    "id": row.id,
                    "findingId": row.finding_id or row.id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "sourceDocument": row.source_document or "Unknown",
                    "category": row.category or "other",
                    "severity": severity,
                    "dealImpact": finding_type_to_impact.get(row.finding_type, "noted") if row.finding_type else "noted",
                    "description": row.description or "",
                    "pass": "analyze",  # Default to analyze pass
                    "clauseReference": None,
                    "requiresAction": row.requires_action or False,
                    "confidenceScore": float(row.confidence_score) if row.confidence_score else 0.5,
                    "directAnswer": row.direct_answer,
                    "evidenceQuote": row.evidence_quote
                }

                findings.append(finding)

            # Return as JSON array
            return func.HttpResponse(
                json.dumps({
                    "findings": findings,
                    "count": len(findings),
                    "timestamp": datetime.utcnow().isoformat()
                }),
                mimetype="application/json"
            )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
