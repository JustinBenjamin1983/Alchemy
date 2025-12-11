# File: server/opinion/api-2/DDWizardDraft/__init__.py
"""
DD Wizard Draft API - Save and load wizard progress
Supports: GET (list/get drafts), POST (create draft), PUT (update draft), DELETE (delete draft)
"""

import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import DDWizardDraft
from shared.session import transactional_session
import uuid
import datetime

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("DDWizardDraft function triggered")

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get("function-key") != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("Unauthorized", status_code=401)

    # In dev mode, use mock email
    if DEV_MODE:
        email = "dev@localhost"
        logging.info(f"[DEV MODE] Using mock email: {email}")
    else:
        email, err = auth_get_email(req)
        if err:
            return err

    method = req.method.upper()

    try:
        if method == "GET":
            return handle_get(req, email)
        elif method == "POST":
            return handle_post(req, email)
        elif method == "PUT":
            return handle_put(req, email)
        elif method == "DELETE":
            return handle_delete(req, email)
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {method} not allowed"}),
                mimetype="application/json",
                status_code=405
            )
    except Exception as e:
        logging.error(f"Error in DDWizardDraft: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def handle_get(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """Get all drafts for user, or a specific draft by ID."""
    draft_id = req.params.get("draft_id")

    with transactional_session() as session:
        if draft_id:
            # Get specific draft
            draft = session.query(DDWizardDraft).filter(
                DDWizardDraft.id == uuid.UUID(draft_id),
                DDWizardDraft.owned_by == email
            ).first()

            if not draft:
                return func.HttpResponse(
                    json.dumps({"error": "Draft not found"}),
                    mimetype="application/json",
                    status_code=404
                )

            return func.HttpResponse(
                json.dumps(draft_to_dict(draft)),
                mimetype="application/json",
                status_code=200
            )
        else:
            # Get all drafts for user
            drafts = session.query(DDWizardDraft).filter(
                DDWizardDraft.owned_by == email
            ).order_by(DDWizardDraft.updated_at.desc()).all()

            return func.HttpResponse(
                json.dumps({"drafts": [draft_to_dict(d) for d in drafts]}),
                mimetype="application/json",
                status_code=200
            )


def handle_post(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """Create a new wizard draft."""
    req_body = req.get_json()

    draft = DDWizardDraft(
        id=uuid.uuid4(),
        owned_by=email,
        current_step=req_body.get("currentStep", 1),
        transaction_type=req_body.get("transactionType"),
        transaction_name=req_body.get("transactionName", ""),
        client_role=req_body.get("clientRole"),
        deal_structure=req_body.get("dealStructure"),
        estimated_value=req_body.get("estimatedValue"),
        target_closing_date=parse_date(req_body.get("targetClosingDate")),
        deal_rationale=req_body.get("dealRationale", ""),
        known_concerns=json.dumps(req_body.get("knownConcerns", [])),
        critical_priorities=json.dumps(req_body.get("criticalPriorities", [])),
        known_deal_breakers=json.dumps(req_body.get("knownDealBreakers", [])),
        deprioritized_areas=json.dumps(req_body.get("deprioritizedAreas", [])),
        target_company_name=req_body.get("targetCompanyName", ""),
        key_persons=json.dumps(req_body.get("keyPersons", [])),
        counterparties=json.dumps(req_body.get("counterparties", [])),
        key_lenders=json.dumps(req_body.get("keyLenders", [])),
        key_regulators=json.dumps(req_body.get("keyRegulators", [])),
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )

    with transactional_session() as session:
        session.add(draft)
        session.commit()

        return func.HttpResponse(
            json.dumps(draft_to_dict(draft)),
            mimetype="application/json",
            status_code=201
        )


def handle_put(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """Update an existing wizard draft."""
    req_body = req.get_json()
    draft_id = req_body.get("draftId") or req.params.get("draft_id")

    if not draft_id:
        return func.HttpResponse(
            json.dumps({"error": "draft_id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        draft = session.query(DDWizardDraft).filter(
            DDWizardDraft.id == uuid.UUID(draft_id),
            DDWizardDraft.owned_by == email
        ).first()

        if not draft:
            return func.HttpResponse(
                json.dumps({"error": "Draft not found"}),
                mimetype="application/json",
                status_code=404
            )

        # Update fields if provided
        if "currentStep" in req_body:
            draft.current_step = req_body["currentStep"]
        if "transactionType" in req_body:
            draft.transaction_type = req_body["transactionType"]
        if "transactionName" in req_body:
            draft.transaction_name = req_body["transactionName"]
        if "clientRole" in req_body:
            draft.client_role = req_body["clientRole"]
        if "dealStructure" in req_body:
            draft.deal_structure = req_body["dealStructure"]
        if "estimatedValue" in req_body:
            draft.estimated_value = req_body["estimatedValue"]
        if "targetClosingDate" in req_body:
            draft.target_closing_date = parse_date(req_body["targetClosingDate"])
        if "dealRationale" in req_body:
            draft.deal_rationale = req_body["dealRationale"]
        if "knownConcerns" in req_body:
            draft.known_concerns = json.dumps(req_body["knownConcerns"])
        if "criticalPriorities" in req_body:
            draft.critical_priorities = json.dumps(req_body["criticalPriorities"])
        if "knownDealBreakers" in req_body:
            draft.known_deal_breakers = json.dumps(req_body["knownDealBreakers"])
        if "deprioritizedAreas" in req_body:
            draft.deprioritized_areas = json.dumps(req_body["deprioritizedAreas"])
        if "targetCompanyName" in req_body:
            draft.target_company_name = req_body["targetCompanyName"]
        if "keyPersons" in req_body:
            draft.key_persons = json.dumps(req_body["keyPersons"])
        if "counterparties" in req_body:
            draft.counterparties = json.dumps(req_body["counterparties"])
        if "keyLenders" in req_body:
            draft.key_lenders = json.dumps(req_body["keyLenders"])
        if "keyRegulators" in req_body:
            draft.key_regulators = json.dumps(req_body["keyRegulators"])

        draft.updated_at = datetime.datetime.utcnow()
        session.commit()

        return func.HttpResponse(
            json.dumps(draft_to_dict(draft)),
            mimetype="application/json",
            status_code=200
        )


def handle_delete(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """Delete a wizard draft."""
    draft_id = req.params.get("draft_id")

    if not draft_id:
        return func.HttpResponse(
            json.dumps({"error": "draft_id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        draft = session.query(DDWizardDraft).filter(
            DDWizardDraft.id == uuid.UUID(draft_id),
            DDWizardDraft.owned_by == email
        ).first()

        if not draft:
            return func.HttpResponse(
                json.dumps({"error": "Draft not found"}),
                mimetype="application/json",
                status_code=404
            )

        session.delete(draft)
        session.commit()

        return func.HttpResponse(
            json.dumps({"success": True, "deleted_id": draft_id}),
            mimetype="application/json",
            status_code=200
        )


def parse_date(date_str):
    """Parse ISO date string to datetime object."""
    if not date_str:
        return None
    try:
        return datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        return None


def draft_to_dict(draft: DDWizardDraft) -> dict:
    """Convert draft model to frontend-compatible dict."""
    return {
        "id": str(draft.id),
        "currentStep": draft.current_step,
        "transactionType": draft.transaction_type,
        "transactionName": draft.transaction_name or "",
        "clientRole": draft.client_role,
        "dealStructure": draft.deal_structure,
        "estimatedValue": draft.estimated_value,
        "targetClosingDate": draft.target_closing_date.isoformat() if draft.target_closing_date else None,
        "dealRationale": draft.deal_rationale or "",
        "knownConcerns": json.loads(draft.known_concerns) if draft.known_concerns else [],
        "criticalPriorities": json.loads(draft.critical_priorities) if draft.critical_priorities else [],
        "knownDealBreakers": json.loads(draft.known_deal_breakers) if draft.known_deal_breakers else [],
        "deprioritizedAreas": json.loads(draft.deprioritized_areas) if draft.deprioritized_areas else [],
        "targetCompanyName": draft.target_company_name or "",
        "keyPersons": json.loads(draft.key_persons) if draft.key_persons else [],
        "counterparties": json.loads(draft.counterparties) if draft.counterparties else [],
        "keyLenders": json.loads(draft.key_lenders) if draft.key_lenders else [],
        "keyRegulators": json.loads(draft.key_regulators) if draft.key_regulators else [],
        "createdAt": draft.created_at.isoformat() if draft.created_at else None,
        "updatedAt": draft.updated_at.isoformat() if draft.updated_at else None,
    }
