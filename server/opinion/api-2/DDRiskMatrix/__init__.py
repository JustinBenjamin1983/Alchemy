"""
API endpoint for risk matrix and dashboard data.
Provides aggregated risk metrics for executive dashboards.

Phase 7: Enterprise Features
"""

import azure.functions as func
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy import text

from shared.session import transactional_session
from shared.audit import log_audit_event, AuditEventType

logger = logging.getLogger(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get risk matrix and dashboard data for a DD project.

    Query params:
        dd_id: DD project ID (required)
        run_id: Analysis run ID (optional, defaults to latest)
    """
    try:
        dd_id = req.params.get('dd_id')
        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        run_id = req.params.get('run_id')

        with transactional_session() as session:
            risk_matrix = build_risk_matrix(session, dd_id, run_id)

            # Log access audit event
            log_audit_event(
                session=session,
                event_type=AuditEventType.DD_ACCESSED.value,
                entity_type='dd',
                entity_id=dd_id,
                dd_id=dd_id,
                details={'action': 'risk_matrix_viewed', 'run_id': run_id}
            )
            session.commit()

        return func.HttpResponse(
            json.dumps(risk_matrix, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error building risk matrix: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def build_risk_matrix(session, dd_id: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build comprehensive risk matrix data.
    """
    # Get latest run if not specified
    if not run_id:
        result = session.execute(
            text("""
                SELECT id FROM dd_analysis_run
                WHERE dd_id = :dd_id
                ORDER BY created_at DESC LIMIT 1
            """),
            {'dd_id': dd_id}
        ).fetchone()
        run_id = str(result.id) if result else None

    if not run_id:
        return {'error': 'No analysis runs found', 'dd_id': dd_id}

    # Get findings by priority (action_priority) and category (folder_category)
    # Note: Using action_priority as severity equivalent
    findings_summary = session.execute(
        text("""
            SELECT
                action_priority as severity,
                COALESCE(risk_category, folder_category, 'General') as risk_category,
                folder_category,
                COUNT(*) as count
            FROM perspective_risk_finding
            WHERE run_id = :run_id
            AND status != 'Deleted'
            GROUP BY action_priority, COALESCE(risk_category, folder_category, 'General'), folder_category
            ORDER BY
                CASE action_priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                count DESC
        """),
        {'run_id': run_id}
    ).fetchall()

    # Build severity breakdown
    severity_breakdown = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'none': 0}
    for row in findings_summary:
        sev = row.severity or 'none'
        if sev in severity_breakdown:
            severity_breakdown[sev] += row.count
        else:
            severity_breakdown['none'] += row.count

    # Build folder breakdown
    folder_breakdown = {}
    for row in findings_summary:
        folder = row.folder_category or 'Unclassified'
        if folder not in folder_breakdown:
            folder_breakdown[folder] = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'total': 0}
        sev = row.severity or 'low'
        if sev in folder_breakdown[folder]:
            folder_breakdown[folder][sev] += row.count
        folder_breakdown[folder]['total'] += row.count

    # Build risk category breakdown
    category_breakdown = {}
    for row in findings_summary:
        category = row.risk_category or 'General'
        if category not in category_breakdown:
            category_breakdown[category] = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'total': 0}
        sev = row.severity or 'low'
        if sev in category_breakdown[category]:
            category_breakdown[category][sev] += row.count
        category_breakdown[category]['total'] += row.count

    # Get deal blockers (critical findings or deal_impact = 'deal_blocker')
    deal_blockers = session.execute(
        text("""
            SELECT
                id,
                COALESCE(title, LEFT(phrase, 100)) as title,
                phrase as description,
                folder_category,
                COALESCE(risk_category, folder_category) as risk_category,
                action_items as recommendation
            FROM perspective_risk_finding
            WHERE run_id = :run_id
            AND (action_priority = 'critical' OR deal_impact = 'deal_blocker')
            AND status != 'Deleted'
            ORDER BY created_at
        """),
        {'run_id': run_id}
    ).fetchall()

    # Get change of control summary from knowledge graph
    coc_summary = session.execute(
        text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN has_change_of_control THEN 1 ELSE 0 END) as with_coc,
                SUM(CASE WHEN has_consent_requirement THEN 1 ELSE 0 END) as with_consent
            FROM kg_agreement
            WHERE dd_id = :dd_id
        """),
        {'dd_id': dd_id}
    ).fetchone()

    # Get financial exposure from knowledge graph
    financial_exposure = session.execute(
        text("""
            SELECT currency, SUM(value) as total_value, COUNT(*) as count
            FROM kg_amount
            WHERE dd_id = :dd_id
            GROUP BY currency
            ORDER BY total_value DESC
        """),
        {'dd_id': dd_id}
    ).fetchall()

    # Also get financial exposure from findings
    findings_exposure = session.execute(
        text("""
            SELECT
                financial_exposure_currency as currency,
                SUM(financial_exposure_amount) as total_value,
                COUNT(*) as count
            FROM perspective_risk_finding
            WHERE run_id = :run_id
            AND financial_exposure_amount IS NOT NULL
            AND financial_exposure_amount > 0
            GROUP BY financial_exposure_currency
            ORDER BY total_value DESC
        """),
        {'run_id': run_id}
    ).fetchall()

    # Calculate overall risk score (0-100)
    risk_score = calculate_risk_score(severity_breakdown, coc_summary)

    # Build risk matrix (likelihood x impact grid)
    risk_matrix = build_likelihood_impact_matrix(findings_summary)

    # Get top 10 risks
    top_risks = get_top_risks(session, run_id, limit=10)

    return {
        'dd_id': dd_id,
        'run_id': run_id,
        'generated_at': datetime.utcnow().isoformat(),

        # Overall metrics
        'risk_score': risk_score,
        'risk_rating': get_risk_rating(risk_score),
        'total_findings': sum(severity_breakdown.values()),

        # Breakdowns
        'severity_breakdown': severity_breakdown,
        'folder_breakdown': folder_breakdown,
        'category_breakdown': category_breakdown,

        # Key risks
        'deal_blockers': [
            {
                'id': str(row.id),
                'title': row.title,
                'description': row.description[:500] if row.description else None,
                'folder_category': row.folder_category,
                'risk_category': row.risk_category,
                'recommendation': row.recommendation
            }
            for row in deal_blockers
        ],
        'deal_blocker_count': len(deal_blockers),

        # Change of control analysis
        'coc_analysis': {
            'total_agreements': coc_summary.total if coc_summary else 0,
            'agreements_with_coc': coc_summary.with_coc if coc_summary else 0,
            'agreements_requiring_consent': coc_summary.with_consent if coc_summary else 0,
            'coc_risk_percentage': round(
                (coc_summary.with_coc / coc_summary.total * 100)
                if coc_summary and coc_summary.total > 0 else 0, 1
            )
        },

        # Financial exposure (combined from graph and findings)
        'financial_exposure': {
            'from_graph': [
                {'currency': row.currency, 'total_value': float(row.total_value), 'count': row.count}
                for row in financial_exposure
            ],
            'from_findings': [
                {'currency': row.currency, 'total_value': float(row.total_value), 'count': row.count}
                for row in findings_exposure
            ]
        },
        'total_exposure': {
            row.currency: float(row.total_value)
            for row in financial_exposure
        },

        # Risk matrix (5x5 grid)
        'risk_matrix': risk_matrix,

        # Top 10 risks
        'top_risks': top_risks
    }


def calculate_risk_score(severity_breakdown: Dict, coc_summary) -> int:
    """
    Calculate overall risk score (0-100).

    Weights:
    - Critical findings: 25 points each (max 50)
    - High findings: 5 points each (max 30)
    - Medium findings: 1 point each (max 10)
    - CoC exposure: up to 10 points
    """
    score = 0

    # Severity contribution
    score += min(50, severity_breakdown.get('critical', 0) * 25)
    score += min(30, severity_breakdown.get('high', 0) * 5)
    score += min(10, severity_breakdown.get('medium', 0) * 1)

    # CoC contribution
    if coc_summary and coc_summary.total and coc_summary.total > 0:
        coc_percentage = (coc_summary.with_coc or 0) / coc_summary.total
        score += int(coc_percentage * 10)

    return min(100, score)


def get_risk_rating(score: int) -> str:
    """Convert risk score to rating."""
    if score >= 75:
        return 'Critical'
    elif score >= 50:
        return 'High'
    elif score >= 25:
        return 'Medium'
    else:
        return 'Low'


def build_likelihood_impact_matrix(findings_summary) -> Dict:
    """
    Build a 5x5 likelihood x impact matrix.
    """
    matrix = {
        'rows': ['Rare', 'Unlikely', 'Possible', 'Likely', 'Almost Certain'],
        'cols': ['Insignificant', 'Minor', 'Moderate', 'Major', 'Catastrophic'],
        'cells': [[0] * 5 for _ in range(5)]
    }

    # Map severity to impact column
    severity_to_impact = {
        'none': 0,
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4
    }

    for row in findings_summary:
        impact = severity_to_impact.get(row.severity or 'low', 2)
        likelihood = 2  # Default to 'Possible'

        # Adjust likelihood based on category
        category = (row.risk_category or '').lower()
        if 'change' in category or 'control' in category or 'termination' in category:
            likelihood = 3  # 'Likely' for transaction-triggered risks
        elif 'compliance' in category or 'regulatory' in category:
            likelihood = 2  # 'Possible' for compliance issues
        elif 'financial' in category:
            likelihood = 3  # 'Likely' for financial risks

        matrix['cells'][likelihood][impact] += row.count

    return matrix


def get_top_risks(session, run_id: str, limit: int = 10) -> List[Dict]:
    """Get top risks ordered by severity and category importance."""
    result = session.execute(
        text("""
            SELECT
                id,
                COALESCE(title, LEFT(phrase, 100)) as title,
                phrase as description,
                action_priority as severity,
                COALESCE(risk_category, folder_category) as risk_category,
                folder_category,
                action_items as recommendation,
                document_id,
                clause_reference,
                deal_impact,
                financial_exposure_amount,
                financial_exposure_currency
            FROM perspective_risk_finding
            WHERE run_id = :run_id
            AND status != 'Deleted'
            ORDER BY
                CASE action_priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                CASE deal_impact
                    WHEN 'deal_blocker' THEN 1
                    WHEN 'condition_precedent' THEN 2
                    WHEN 'price_chip' THEN 3
                    ELSE 4
                END
            LIMIT :limit
        """),
        {'run_id': run_id, 'limit': limit}
    )

    return [
        {
            'id': str(row.id),
            'title': row.title,
            'description': row.description[:300] if row.description else None,
            'severity': row.severity or 'low',
            'risk_category': row.risk_category,
            'folder_category': row.folder_category,
            'recommendation': row.recommendation,
            'document_id': str(row.document_id) if row.document_id else None,
            'clause_reference': row.clause_reference,
            'deal_impact': row.deal_impact,
            'financial_exposure': {
                'amount': float(row.financial_exposure_amount) if row.financial_exposure_amount else None,
                'currency': row.financial_exposure_currency
            } if row.financial_exposure_amount else None
        }
        for row in result.fetchall()
    ]
