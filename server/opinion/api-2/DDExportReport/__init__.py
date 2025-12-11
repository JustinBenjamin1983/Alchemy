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
from shared.models import DueDiligence, Document, Folder, PerspectiveRiskFinding, PerspectiveRisk, Perspective, DueDiligenceMember, DDWizardDraft
from .report_generator import generate_dd_report
from .claude_synthesis import get_report_synthesis

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Generate Word document DD report from analyzed findings."""

    try:
        dd_id = req.params.get('dd_id')
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

        logging.info(f"[DDExportReport] Starting report generation for DD: {dd_id}, user: {email}")

        with transactional_session() as session:
            # Fetch DD metadata
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": "DD not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get transaction type from wizard draft
            draft = session.query(DDWizardDraft).filter(
                DDWizardDraft.owned_by == dd.owned_by,
                DDWizardDraft.transaction_name == dd.name
            ).first()
            transaction_type = draft.transaction_type if draft and draft.transaction_type else "General"

            # Fetch all folders and documents for this DD
            folders = session.query(Folder).filter(Folder.dd_id == dd_id).all()
            folder_ids = [f.id for f in folders]

            documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids)
            ).all()

            logging.info(f"[DDExportReport] Found {len(documents)} documents")

            # Use the SAME query pattern as DDRisksResultsGet to ensure we get ALL findings
            # This joins through the proper chain: PerspectiveRisk -> Perspective -> DueDiligenceMember -> DueDiligence
            results = (
                session.query(
                    PerspectiveRisk.id.label("perspective_risk_id"),
                    PerspectiveRisk.category.label("category"),
                    PerspectiveRisk.detail.label("detail"),
                    PerspectiveRisk.question_type.label("question_type"),
                    PerspectiveRiskFinding.id.label("finding_id"),
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
                .join(Document, Document.id == PerspectiveRiskFinding.document_id)
                .join(Folder, Folder.id == Document.folder_id)
                .filter(
                    DueDiligence.id == dd_id,
                    DueDiligenceMember.member_email == email,
                    PerspectiveRiskFinding.status != 'Deleted'
                )
                .all()
            )

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

            # Get document list for synthesis
            doc_list = [d.original_file_name for d in documents]

            # Call Claude for synthesis (ONE call with all data)
            logging.info("[DDExportReport] Calling Claude for synthesis...")
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
