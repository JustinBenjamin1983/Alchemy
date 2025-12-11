import logging
import os
import json

import azure.functions as func
from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import DueDiligence, PerspectiveRisk, PerspectiveRiskFinding, Document, Perspective, DueDiligenceMember, Folder

from collections import defaultdict


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            return err
        
        dd_id = req.params.get("dd_id")
       
        with transactional_session() as session:
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
                    PerspectiveRiskFinding.reviewed_by.label("reviewed_by"),
                    PerspectiveRiskFinding.page_number.label("page_number"),
                    PerspectiveRiskFinding.finding_type.label("finding_type"),
                    PerspectiveRiskFinding.confidence_score.label("confidence_score"),
                    PerspectiveRiskFinding.requires_action.label("requires_action"),
                    PerspectiveRiskFinding.action_priority.label("action_priority"),
                    PerspectiveRiskFinding.direct_answer.label("direct_answer"),
                    PerspectiveRiskFinding.evidence_quote.label("evidence_quote"),
                    PerspectiveRiskFinding.missing_documents.label("missing_documents"),
                    PerspectiveRiskFinding.action_items.label("action_items"),
                    Document.id.label("document_id"),
                    Document.original_file_name.label("original_file_name"),
                    Document.type.label("document_type"),
                    Folder.path.label("folder_path")
                )
                .join(Perspective, Perspective.id == PerspectiveRisk.perspective_id)
                .join(DueDiligenceMember, DueDiligenceMember.id == Perspective.member_id)
                .join(DueDiligence, DueDiligence.id == DueDiligenceMember.dd_id)
                .join(PerspectiveRiskFinding, PerspectiveRiskFinding.perspective_risk_id == PerspectiveRisk.id)
                .join(Document, Document.id == PerspectiveRiskFinding.document_id)
                .join(Folder, Folder.id == Document.folder_id)
                .filter(DueDiligence.id == dd_id, DueDiligenceMember.member_email == email)
                .all()
            )
            
        grouped = defaultdict(list)
        for row in results:
            category = row.category
            finding = {
                "perspective_risk_id": str(row.perspective_risk_id),
                "finding_id": str(row.finding_id),
                "finding_status": row.status,
                "finding_type": row.finding_type or "neutral",
                "finding_is_reviewed": row.is_reviewed,
                "finding_reviewed_by": row.reviewed_by,
                "detail": row.detail,
                "question_type": row.question_type or "risk_search",
                "phrase": row.phrase,
                "page_number": row.page_number,
                "confidence_score": row.confidence_score or 0.5,
                "requires_action": row.requires_action or False,
                "action_priority": row.action_priority or "none",
                "direct_answer": row.direct_answer,
                "evidence_quote": row.evidence_quote,
                "missing_documents": row.missing_documents,
                "action_items": row.action_items,
                "document": {
                    "id": str(row.document_id),
                    "original_file_name": row.original_file_name,
                    "type": row.document_type,
                    "folder": {
                        "path": row.folder_path
                    }
                },
                "category": category
            }
            grouped[category].append(finding)
        
        result = [
            {
                "category": category,
                "findings": sorted(findings, key=lambda f: (
                    f["finding_type"] == "negative",  # Negative findings first
                    -f["confidence_score"],  # Then by confidence
                    f["finding_id"]
                ))
            }
            for category, findings in grouped.items()
        ]
        
        return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=200)
        
    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)