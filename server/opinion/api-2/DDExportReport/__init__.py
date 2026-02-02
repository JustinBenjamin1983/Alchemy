# DDExportReport - Generate Word document DD report
# This endpoint generates a professional Word document from analyzed DD findings

import logging
import json
import os
from io import BytesIO
from datetime import datetime
from collections import defaultdict
import azure.functions as func
from shared.session import transactional_session
from shared.utils import auth_get_email
from shared.models import DueDiligence, Document, Folder, PerspectiveRiskFinding, PerspectiveRisk, Perspective, DueDiligenceMember, DDAnalysisRun
from .report_generator import generate_dd_report
from .claude_synthesis import get_report_synthesis

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Generate Word document DD report from analyzed findings."""

    try:
        dd_id = req.params.get('dd_id')
        run_id = req.params.get('run_id')  # Optional: filter by specific analysis run

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id parameter required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Get user email for filtering (same as UI does)
        # auth_get_email handles DEV_MODE internally, returning "dev@alchemy.local" in dev mode
        email, err = auth_get_email(req)
        if err:
            return err

        logging.info(f"[DDExportReport] Starting report generation for DD: {dd_id}, run: {run_id}, user: {email}")

        with transactional_session() as session:
            # Fetch DD metadata
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": "DD not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get transaction type from dd.project_setup (linked by dd_id)
            project_setup = dd.project_setup or {}
            transaction_type = project_setup.get("transactionType") or "General"

            # Fetch all folders and documents for this DD
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()

            logging.info(f"[DDExportReport] Found {len(documents)} documents")

            # Use the SAME query pattern as DDRisksResultsGet to ensure we get the right findings
            # This joins through the proper chain: PerspectiveRisk -> Perspective -> DueDiligenceMember -> DueDiligence
            query = (
                session.query(
                    PerspectiveRisk.id.label("perspective_risk_id"),
                    PerspectiveRisk.category.label("category"),
                    PerspectiveRisk.detail.label("detail"),
                    PerspectiveRisk.question_type.label("question_type"),
                    PerspectiveRiskFinding.id.label("finding_id"),
                    PerspectiveRiskFinding.run_id.label("run_id"),
                    PerspectiveRiskFinding.phrase.label("phrase"),
                    PerspectiveRiskFinding.status.label("status"),
                    PerspectiveRiskFinding.is_reviewed.label("is_reviewed"),
                    PerspectiveRiskFinding.page_number.label("page_number"),
                    PerspectiveRiskFinding.finding_type.label("finding_type"),
                    PerspectiveRiskFinding.confidence_score.label("confidence_score"),
                    PerspectiveRiskFinding.requires_action.label("requires_action"),
                    PerspectiveRiskFinding.action_priority.label("action_priority"),
                    PerspectiveRiskFinding.direct_answer.label("direct_answer"),
                    PerspectiveRiskFinding.evidence_quote.label("evidence_quote"),
                    PerspectiveRiskFinding.missing_documents.label("missing_documents"),
                    PerspectiveRiskFinding.action_items.label("action_items"),
                    PerspectiveRiskFinding.deal_impact.label("deal_impact"),
                    PerspectiveRiskFinding.financial_exposure_amount.label("financial_exposure_amount"),
                    PerspectiveRiskFinding.financial_exposure_currency.label("financial_exposure_currency"),
                    PerspectiveRiskFinding.financial_exposure_calculation.label("financial_exposure_calculation"),
                    PerspectiveRiskFinding.clause_reference.label("clause_reference"),
                    PerspectiveRiskFinding.cross_doc_source.label("cross_doc_source"),
                    PerspectiveRiskFinding.analysis_pass.label("analysis_pass"),
                    Document.id.label("document_id"),
                    Document.original_file_name.label("original_file_name"),
                    Folder.path.label("folder_path")
                )
                .join(Perspective, Perspective.id == PerspectiveRisk.perspective_id)
                .join(DueDiligenceMember, DueDiligenceMember.id == Perspective.member_id)
                .join(DueDiligence, DueDiligence.id == DueDiligenceMember.dd_id)
                .join(PerspectiveRiskFinding, PerspectiveRiskFinding.perspective_risk_id == PerspectiveRisk.id)
                .outerjoin(Document, Document.id == PerspectiveRiskFinding.document_id)
                .outerjoin(Folder, Folder.id == Document.folder_id)
                .filter(
                    DueDiligence.id == dd_id,
                    DueDiligenceMember.member_email == email,
                    PerspectiveRiskFinding.status != 'Deleted'
                )
            )

            # Filter by run_id if provided (CRITICAL: only get findings from selected run)
            if run_id:
                query = query.filter(PerspectiveRiskFinding.run_id == run_id)
                logging.info(f"[DDExportReport] Filtering by run_id: {run_id}")

            results = query.all()

            logging.info(f"[DDExportReport] Found {len(results)} findings via proper join chain")

            # Group by category for logging
            categories_found = defaultdict(int)
            for row in results:
                categories_found[row.category] += 1
            logging.info(f"[DDExportReport] Categories found: {dict(categories_found)}")

            if not results:
                return func.HttpResponse(
                    json.dumps({"error": "No findings available for this DD. Process documents first."}),
                    status_code=400,
                    mimetype="application/json"
                )

            # Build findings_data directly from query results (already has all joined data)
            findings_data = []
            for row in results:
                # Build financial exposure dict if amount exists
                financial_exposure = None
                if row.financial_exposure_amount:
                    financial_exposure = {
                        'amount': row.financial_exposure_amount,
                        'currency': row.financial_exposure_currency or 'ZAR',
                        'calculation': row.financial_exposure_calculation
                    }

                finding_dict = {
                    'id': str(row.finding_id),
                    'category': row.category or 'Uncategorized',
                    'detail': row.detail or '',
                    'severity': map_status_to_severity(row.status),
                    'status': row.status,
                    'phrase': row.phrase,
                    'page_number': row.page_number,
                    'finding_type': row.finding_type,
                    'confidence_score': row.confidence_score,
                    'direct_answer': row.direct_answer,
                    'evidence_quote': row.evidence_quote,
                    'requires_action': row.requires_action,
                    'action_priority': row.action_priority,
                    'document_name': row.original_file_name or 'Cross-Document Analysis',
                    'document_id': str(row.document_id) if row.document_id else None,
                    'folder_path': row.folder_path or '',
                    # Enhanced DD fields
                    'deal_impact': row.deal_impact,
                    'financial_exposure': financial_exposure,
                    'clause_reference': row.clause_reference,
                    'cross_doc_source': row.cross_doc_source,
                    'analysis_pass': row.analysis_pass or 2,
                    'is_cross_doc': row.document_id is None
                }
                findings_data.append(finding_dict)

            # Get ALL documents from the DD folder (not just ones with findings)
            # This ensures all documents are listed in the report
            doc_list = [doc.original_file_name for doc in documents if doc.original_file_name]
            logging.info(f"[DDExportReport] Total documents in DD: {len(doc_list)}")

            # PRIORITY: Use stored synthesis from DDAnalysisRun if run_id provided
            synthesis = None
            if run_id:
                analysis_run = session.query(DDAnalysisRun).filter(
                    DDAnalysisRun.id == run_id
                ).first()

                if analysis_run and analysis_run.synthesis_data:
                    logging.info(f"[DDExportReport] Using stored synthesis from run {run_id}")
                    stored_synthesis = analysis_run.synthesis_data
                    logging.info(f"[DDExportReport] Stored synthesis keys: {list(stored_synthesis.keys())}")

                    # Normalize stored synthesis to match expected report format
                    synthesis = normalize_synthesis_for_report(stored_synthesis, findings_data, doc_list)
                    logging.info(f"[DDExportReport] Normalized synthesis keys: {list(synthesis.keys())}")
                else:
                    logging.info(f"[DDExportReport] No stored synthesis found for run {run_id}")

            # FALLBACK: Call Claude for synthesis only if no stored synthesis available
            if not synthesis:
                logging.info("[DDExportReport] Calling Claude for synthesis (no stored synthesis)...")
                synthesis = get_report_synthesis(
                    dd_name=dd.name,
                    transaction_type=transaction_type,
                    findings=findings_data,
                    documents=doc_list,
                    briefing=dd.briefing
                )
                logging.info("[DDExportReport] Synthesis complete")

            # Generate Word document
            logging.info("[DDExportReport] Generating Word document...")
            doc_buffer = generate_dd_report(
                dd_name=dd.name,
                transaction_type=transaction_type,
                briefing=dd.briefing,
                findings=findings_data,
                documents=doc_list,
                synthesis=synthesis
            )
            logging.info("[DDExportReport] Word document generated")

            # Generate filename
            safe_name = "".join(c if c.isalnum() or c in "_ -" else "_" for c in dd.name)
            filename = f"DD_Report_{safe_name}_{datetime.now().strftime('%Y%m%d')}.docx"

            return func.HttpResponse(
                doc_buffer.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Access-Control-Expose-Headers': 'Content-Disposition'
                }
            )

    except Exception as e:
        logging.exception(f"[DDExportReport] Error: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def map_status_to_severity(status):
    """Map finding status to severity level."""
    mapping = {
        'Red': 'High',
        'Amber': 'Medium',
        'Green': 'Low',
        'Info': 'Low',
        'New': 'Medium'
    }
    return mapping.get(status, 'Medium')


def normalize_synthesis_for_report(stored: dict, findings: list, documents: list) -> dict:
    """
    Transform stored synthesis (from pass 4 analysis) to match report generator format.

    Stored synthesis format (from DDAnalysisRun.synthesis_data):
    - executive_summary: string
    - deal_assessment: {can_proceed, overall_risk_rating, key_risks, blocking_issues}
    - deal_blockers: [{issue, owner, source, why_blocking, resolution_path, resolution_timeline}]
    - conditions_precedent: [{cp_number, description, category, responsible_party, status, target_date, source, is_deal_blocker}]
    - financial_exposures: {total, currency, items, calculation_notes}
    - recommendations: [string, ...]

    Report generator expects:
    - executive_summary: {overview, key_findings, risk_profile}
    - deal_assessment: {overall_viability, key_concerns, mitigating_factors, negotiation_points, deal_structure_recommendations}
    - deal_blockers: {summary, blockers: [{title, category, description, source_document, resolution_path, criticality}]}
    - conditions_precedent: {summary, conditions: [{title, category, description, responsible_party, estimated_timeline, risk_if_not_met}]}
    - financial_exposures: {total_quantified_exposure, exposure_breakdown, unquantified_risks, recommended_provisions}
    - statistics, category_summaries, action_items, recommendations, conclusion
    """

    # Calculate statistics from findings
    high_count = sum(1 for f in findings if f.get('severity') == 'High')
    medium_count = sum(1 for f in findings if f.get('severity') == 'Medium')
    low_count = sum(1 for f in findings if f.get('severity') == 'Low')
    action_count = sum(1 for f in findings if f.get('requires_action'))
    deal_blocker_count = len(stored.get('deal_blockers', []))
    cp_count = len(stored.get('conditions_precedent', []))

    # Build executive_summary from stored string
    exec_summary_str = stored.get('executive_summary', '')
    deal_assessment = stored.get('deal_assessment', {})
    key_risks = deal_assessment.get('key_risks', [])

    normalized = {
        'executive_summary': {
            'overview': exec_summary_str,
            'key_findings': key_risks[:7] if key_risks else ['See detailed findings below'],
            'risk_profile': f"{deal_assessment.get('overall_risk_rating', 'Medium').title()} - Based on analysis"
        },
        'deal_assessment': {
            'overall_viability': 'Go' if deal_assessment.get('can_proceed') else 'Conditional Go - Issues must be resolved',
            'key_concerns': deal_assessment.get('blocking_issues', []) or key_risks[:5],
            'mitigating_factors': ['See detailed analysis for mitigating factors'],
            'negotiation_points': ['Address identified blocking issues', 'Negotiate warranty protection for key risks'],
            'deal_structure_recommendations': 'Consider escrow, indemnities, and conditions precedent to address identified risks'
        },
        'financial_exposures': {
            'total_quantified_exposure': f"{stored.get('financial_exposures', {}).get('currency', 'ZAR')} {stored.get('financial_exposures', {}).get('total', 0):,.0f}" if stored.get('financial_exposures', {}).get('total') else 'See detailed findings',
            'exposure_breakdown': [
                {
                    'category': item.get('type', 'General'),
                    'amount': f"{item.get('amount', 0):,.0f}",
                    'description': item.get('description', ''),
                    'source_document': item.get('source', ''),
                    'mitigation': 'Consider warranty/indemnity coverage'
                }
                for item in stored.get('financial_exposures', {}).get('items', [])
            ],
            'unquantified_risks': stored.get('financial_exposures', {}).get('calculation_notes', []) or ['Some exposures may not be fully quantified'],
            'recommended_provisions': 'Standard indemnity and escrow provisions recommended'
        },
        'deal_blockers': {
            'summary': f"{deal_blocker_count} deal-blocking issues identified" if deal_blocker_count > 0 else 'No absolute deal blockers identified',
            'blockers': [
                {
                    'title': blocker.get('issue', 'Deal Blocker'),
                    'category': blocker.get('owner', 'General'),
                    'description': blocker.get('why_blocking', ''),
                    'source_document': blocker.get('source', ''),
                    'resolution_path': blocker.get('resolution_path', 'Resolution required'),
                    'criticality': f"Timeline: {blocker.get('resolution_timeline', 'To be determined')}"
                }
                for blocker in stored.get('deal_blockers', [])
            ],
            'resolution_timeline': 'See individual blockers for timelines'
        },
        'conditions_precedent': {
            'summary': f"{cp_count} conditions precedent identified" if cp_count > 0 else 'Standard conditions precedent apply',
            'conditions': [
                {
                    'title': cp.get('description', 'Condition'),
                    'category': cp.get('category', 'General'),
                    'description': cp.get('description', ''),
                    'responsible_party': cp.get('responsible_party', 'To be determined'),
                    'estimated_timeline': cp.get('target_date', 'Before closing'),
                    'risk_if_not_met': 'Transaction cannot proceed' if cp.get('is_deal_blocker') else 'May delay closing'
                }
                for cp in stored.get('conditions_precedent', [])
            ],
            'critical_path_items': [cp.get('description', '') for cp in stored.get('conditions_precedent', []) if cp.get('is_deal_blocker')]
        },
        'statistics': {
            'total_documents': len(documents),
            'total_findings': len(findings),
            'high_risk_count': high_count,
            'medium_risk_count': medium_count,
            'low_risk_count': low_count,
            'action_required_count': action_count,
            'deal_blocker_count': deal_blocker_count,
            'condition_precedent_count': cp_count
        },
        'category_summaries': {},  # Will be generated from findings if needed
        'action_items': [],  # Will be generated from findings if needed
        'recommendations': [
            {'priority': i + 1, 'title': f'Recommendation {i + 1}', 'description': rec, 'category': 'General', 'implementation': 'See recommendation details'}
            for i, rec in enumerate(stored.get('recommendations', []))
        ] if stored.get('recommendations') else [],
        'conclusion': {
            'overall_assessment': exec_summary_str or 'See executive summary above',
            'deal_recommendation': 'Go with conditions' if deal_assessment.get('can_proceed') else 'Further review required',
            'key_negotiation_items': deal_assessment.get('blocking_issues', [])[:5] or ['Standard deal protections'],
            'next_steps': ['Resolve identified blocking issues', 'Complete due diligence on outstanding items', 'Prepare transaction documentation']
        }
    }

    return normalized
