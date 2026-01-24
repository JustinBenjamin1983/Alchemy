# File: server/opinion/api-2/DDEntityConfirmationSave/__init__.py
"""
DD Entity Confirmation Auto-Save API

Saves entity confirmation decisions immediately (auto-save).
Each confirmation is saved individually without waiting for the modal to close.
"""

import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.session import transactional_session
from sqlalchemy import text
import uuid
import datetime

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("DDEntityConfirmationSave function triggered")

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get("function-key") != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("Unauthorized", status_code=401)

    # Auth
    if DEV_MODE:
        email = "dev@alchemy.local"
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
        logging.error(f"Error in DDEntityConfirmationSave: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def handle_get(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    GET /api/dd-entity-confirmation-save?dd_id=<uuid>

    Get all entity confirmations for a DD.
    """
    dd_id = req.params.get("dd_id")
    if not dd_id:
        return func.HttpResponse(
            json.dumps({"error": "dd_id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        result = session.execute(text("""
            SELECT id, dd_id, checkpoint_id, entity_a_name, entity_a_type,
                   entity_b_name, entity_b_type, relationship_type, relationship_detail,
                   ai_confidence, user_decision, user_correction, user_notes,
                   source_document_ids, evidence_text, created_at, confirmed_at, confirmed_by
            FROM dd_entity_confirmation
            WHERE dd_id = :dd_id
            ORDER BY created_at DESC
        """), {"dd_id": dd_id})

        confirmations = []
        for row in result:
            confirmations.append({
                "id": str(row[0]),
                "dd_id": str(row[1]),
                "checkpoint_id": str(row[2]) if row[2] else None,
                "entity_a_name": row[3],
                "entity_a_type": row[4],
                "entity_b_name": row[5],
                "entity_b_type": row[6],
                "relationship_type": row[7],
                "relationship_detail": row[8],
                "ai_confidence": row[9],
                "user_decision": row[10],
                "user_correction": row[11],
                "user_notes": row[12],
                "source_document_ids": row[13] or [],
                "evidence_text": row[14],
                "created_at": row[15].isoformat() if row[15] else None,
                "confirmed_at": row[16].isoformat() if row[16] else None,
                "confirmed_by": row[17],
            })

        return func.HttpResponse(
            json.dumps({"confirmations": confirmations}),
            mimetype="application/json",
            status_code=200
        )


def handle_post(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    POST /api/dd-entity-confirmation-save
    Body: {
        dd_id, checkpoint_id?, entity_a_name, entity_a_type?, entity_b_name?, entity_b_type?,
        relationship_type?, relationship_detail?, ai_confidence?, user_decision,
        user_correction?, user_notes?, source_document_ids?, evidence_text?
    }

    Save a new entity confirmation (auto-save).
    Uses UPSERT to update if entity pair already exists.
    """
    req_body = req.get_json()
    dd_id = req_body.get("dd_id")
    entity_a_name = req_body.get("entity_a_name")

    if not dd_id or not entity_a_name:
        return func.HttpResponse(
            json.dumps({"error": "dd_id and entity_a_name are required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        # UPSERT: Insert or update based on unique constraint (dd_id, entity_a_name, entity_b_name)
        confirmation_id = str(uuid.uuid4())
        entity_b_name = req_body.get("entity_b_name") or ""

        session.execute(text("""
            INSERT INTO dd_entity_confirmation (
                id, dd_id, checkpoint_id, entity_a_name, entity_a_type,
                entity_b_name, entity_b_type, relationship_type, relationship_detail,
                ai_confidence, user_decision, user_correction, user_notes,
                source_document_ids, evidence_text, created_at, confirmed_at, confirmed_by
            ) VALUES (
                :id, :dd_id, :checkpoint_id, :entity_a_name, :entity_a_type,
                :entity_b_name, :entity_b_type, :relationship_type, :relationship_detail,
                :ai_confidence, :user_decision, :user_correction, :user_notes,
                :source_document_ids, :evidence_text, NOW(), :confirmed_at, :confirmed_by
            )
            ON CONFLICT (dd_id, entity_a_name, entity_b_name)
            DO UPDATE SET
                checkpoint_id = EXCLUDED.checkpoint_id,
                entity_a_type = EXCLUDED.entity_a_type,
                entity_b_type = EXCLUDED.entity_b_type,
                relationship_type = EXCLUDED.relationship_type,
                relationship_detail = EXCLUDED.relationship_detail,
                ai_confidence = EXCLUDED.ai_confidence,
                user_decision = EXCLUDED.user_decision,
                user_correction = EXCLUDED.user_correction,
                user_notes = EXCLUDED.user_notes,
                source_document_ids = EXCLUDED.source_document_ids,
                evidence_text = EXCLUDED.evidence_text,
                confirmed_at = EXCLUDED.confirmed_at,
                confirmed_by = EXCLUDED.confirmed_by
        """), {
            "id": confirmation_id,
            "dd_id": dd_id,
            "checkpoint_id": req_body.get("checkpoint_id"),
            "entity_a_name": entity_a_name,
            "entity_a_type": req_body.get("entity_a_type"),
            "entity_b_name": entity_b_name,
            "entity_b_type": req_body.get("entity_b_type"),
            "relationship_type": req_body.get("relationship_type"),
            "relationship_detail": req_body.get("relationship_detail"),
            "ai_confidence": req_body.get("ai_confidence"),
            "user_decision": req_body.get("user_decision"),
            "user_correction": req_body.get("user_correction"),
            "user_notes": req_body.get("user_notes"),
            "source_document_ids": json.dumps(req_body.get("source_document_ids", [])),
            "evidence_text": req_body.get("evidence_text"),
            "confirmed_at": datetime.datetime.utcnow() if req_body.get("user_decision") else None,
            "confirmed_by": email if req_body.get("user_decision") else None,
        })

        session.commit()

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": "Entity confirmation saved",
                "entity_pair": f"{entity_a_name} - {entity_b_name or '(standalone)'}",
            }),
            mimetype="application/json",
            status_code=200
        )


def handle_put(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    PUT /api/dd-entity-confirmation-save
    Body: { id, user_decision, user_correction?, user_notes? }

    Update an existing entity confirmation by ID.
    """
    req_body = req.get_json()
    confirmation_id = req_body.get("id")

    if not confirmation_id:
        return func.HttpResponse(
            json.dumps({"error": "id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        # Build update query dynamically based on provided fields
        update_fields = []
        params = {"id": confirmation_id}

        if "user_decision" in req_body:
            update_fields.append("user_decision = :user_decision")
            params["user_decision"] = req_body["user_decision"]
            # Also set confirmed_at and confirmed_by when decision is made
            if req_body["user_decision"]:
                update_fields.append("confirmed_at = NOW()")
                update_fields.append("confirmed_by = :confirmed_by")
                params["confirmed_by"] = email

        if "user_correction" in req_body:
            update_fields.append("user_correction = :user_correction")
            params["user_correction"] = req_body["user_correction"]

        if "user_notes" in req_body:
            update_fields.append("user_notes = :user_notes")
            params["user_notes"] = req_body["user_notes"]

        if not update_fields:
            return func.HttpResponse(
                json.dumps({"error": "No fields to update"}),
                mimetype="application/json",
                status_code=400
            )

        query = f"""
            UPDATE dd_entity_confirmation
            SET {', '.join(update_fields)}
            WHERE id = :id
        """
        session.execute(text(query), params)
        session.commit()

        return func.HttpResponse(
            json.dumps({"success": True, "message": "Confirmation updated"}),
            mimetype="application/json",
            status_code=200
        )


def handle_delete(req: func.HttpRequest, email: str) -> func.HttpResponse:
    """
    DELETE /api/dd-entity-confirmation-save?id=<uuid>

    Delete an entity confirmation.
    """
    confirmation_id = req.params.get("id")
    if not confirmation_id:
        return func.HttpResponse(
            json.dumps({"error": "id is required"}),
            mimetype="application/json",
            status_code=400
        )

    with transactional_session() as session:
        session.execute(text("""
            DELETE FROM dd_entity_confirmation WHERE id = :id
        """), {"id": confirmation_id})
        session.commit()

        return func.HttpResponse(
            json.dumps({"success": True, "message": "Confirmation deleted"}),
            mimetype="application/json",
            status_code=200
        )
