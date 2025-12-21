# File: server/opinion/api-2/DDRisksGet/__init__.py

import logging
import os
import json

import azure.functions as func
from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import DueDiligence, PerspectiveRisk, Perspective, DueDiligenceMember

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

def main(req: func.HttpRequest) -> func.HttpResponse:

    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        dd_id = req.params.get("dd_id")

        risk_items = None
        with transactional_session() as session:
            results = (
                session.query(
                    PerspectiveRisk.id.label("perspective_risk_id"),
                    PerspectiveRisk.category.label("category"),
                    PerspectiveRisk.detail.label("detail")
                )
                .join(Perspective, Perspective.id == PerspectiveRisk.perspective_id)
                .join(DueDiligenceMember, DueDiligenceMember.id == Perspective.member_id)
                .join(DueDiligence, DueDiligence.id == DueDiligenceMember.dd_id)
                .filter(DueDiligence.id == dd_id, DueDiligenceMember.member_email == email)
                .all()
            )
            logging.info(f"found {len(results)}")
            risk_items = [
                {
                    "perspective_risk_id": str(r.perspective_risk_id),
                    "category": r.category,
                    "detail": r.detail
                }
                for r in results
            ]
        
        
        return func.HttpResponse(json.dumps(risk_items), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)