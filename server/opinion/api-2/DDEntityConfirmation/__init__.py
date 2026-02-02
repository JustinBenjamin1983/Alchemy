# DDEntityConfirmation/__init__.py
"""
Checkpoint B: Entity Confirmation Loop

Provides an iterative confirmation loop for entity mapping results.
User reviews entity map, provides corrections, AI updates specific entities,
repeat until user clicks "Confirmed".

Endpoints:
- GET /api/dd-entity-confirmation/{dd_id} - Get current entity map for review
- POST /api/dd-entity-confirmation/correct - Submit corrections, AI updates entities
- POST /api/dd-entity-confirmation/confirm - Confirm entity map as source of truth

Flow:
1. After DDEntityMapping completes, user is presented with entity map
2. User reviews and either:
   a. Provides corrections in text field → AI updates affected entities (Sonnet)
   b. Clicks "Confirmed" → Entity map saved as source of truth
3. Loop continues until confirmation
"""
import logging
import os
import json
import datetime
import azure.functions as func
import uuid as uuid_module
from typing import List, Dict, Any, Optional

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import (
    DueDiligence, DDEntityMap, DDValidationCheckpoint
)

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def get_claude_client():
    """Import and create Claude client (deferred to avoid import errors)."""
    import sys
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from dd_enhanced.core.claude_client import ClaudeClient
    return ClaudeClient()


def get_entity_map_for_review(dd_id: str) -> dict:
    """
    Get the current entity map for user review.

    Returns entity map grouped by confirmation status, with summary stats.
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    with transactional_session() as session:
        # Verify DD exists
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
        if not dd:
            return {"error": f"Due diligence {dd_id} not found", "status": "not_found"}

        # Get all entities for this DD
        entities = (
            session.query(DDEntityMap)
            .filter(DDEntityMap.dd_id == dd_uuid)
            .order_by(DDEntityMap.confidence.desc())
            .all()
        )

        if not entities:
            return {
                "dd_id": str(dd_uuid),
                "status": "no_entities",
                "message": "No entities found. Please run Entity Mapping first.",
                "entity_map": [],
                "summary": {
                    "total_entities": 0,
                    "confirmed": 0,
                    "pending_confirmation": 0
                }
            }

        # Check for existing entity confirmation checkpoint
        checkpoint = (
            session.query(DDValidationCheckpoint)
            .filter(
                DDValidationCheckpoint.dd_id == dd_uuid,
                DDValidationCheckpoint.checkpoint_type == "entity_confirmation"
            )
            .order_by(DDValidationCheckpoint.created_at.desc())
            .first()
        )

        # Build entity list with status
        entity_list = []
        confirmed_count = 0
        pending_count = 0

        for entity in entities:
            entity_dict = {
                "id": str(entity.id),
                "entity_name": entity.entity_name,
                "registration_number": entity.registration_number,
                "relationship_to_target": entity.relationship_to_target,
                "relationship_detail": entity.relationship_detail,
                "confidence": entity.confidence,
                "documents_appearing_in": entity.documents_appearing_in or [],
                "evidence": entity.evidence,
                "requires_human_confirmation": entity.requires_human_confirmation,
                "human_confirmed": entity.human_confirmed,
                "human_confirmation_value": entity.human_confirmation_value,
            }
            entity_list.append(entity_dict)

            if entity.human_confirmed:
                confirmed_count += 1
            elif entity.requires_human_confirmation:
                pending_count += 1

        # Get correction history from checkpoint
        correction_history = []
        if checkpoint and checkpoint.user_responses:
            correction_history = checkpoint.user_responses.get("correction_rounds", [])

        return {
            "dd_id": str(dd_uuid),
            "dd_name": dd.name,
            "status": "ready_for_review",
            "checkpoint_id": str(checkpoint.id) if checkpoint else None,
            "checkpoint_status": checkpoint.status if checkpoint else None,
            "entity_map": entity_list,
            "summary": {
                "total_entities": len(entity_list),
                "confirmed": confirmed_count,
                "pending_confirmation": pending_count,
                "high_confidence": sum(1 for e in entity_list if e["confidence"] >= 0.8),
                "low_confidence": sum(1 for e in entity_list if e["confidence"] < 0.5),
            },
            "correction_history": correction_history,
            "by_relationship": _group_by_relationship(entity_list)
        }


def _group_by_relationship(entities: List[Dict]) -> Dict[str, List[Dict]]:
    """Group entities by relationship type for easier review."""
    grouped = {
        "target": [],
        "parent": [],
        "subsidiary": [],
        "counterparty": [],
        "related_party": [],
        "unknown": [],
        "other": []
    }

    for entity in entities:
        rel = entity.get("relationship_to_target", "unknown").lower()
        if rel in grouped:
            grouped[rel].append(entity)
        else:
            grouped["other"].append(entity)

    # Remove empty groups
    return {k: v for k, v in grouped.items() if v}


def submit_entity_corrections(dd_id: str, corrections: str, user_email: str) -> dict:
    """
    Submit corrections for entity map. AI (Sonnet) processes corrections
    and updates only the affected entities.

    Args:
        dd_id: Due diligence ID
        corrections: User's correction text explaining what needs to be fixed
        user_email: Email of user submitting corrections

    Returns:
        Updated entity map with changes highlighted
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    logging.info(f"[DDEntityConfirmation] Processing corrections for DD: {dd_id}")

    with transactional_session() as session:
        # Verify DD exists
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
        if not dd:
            return {"error": f"Due diligence {dd_id} not found"}

        # Get current entity map
        entities = (
            session.query(DDEntityMap)
            .filter(DDEntityMap.dd_id == dd_uuid)
            .all()
        )

        if not entities:
            return {"error": "No entities found to correct"}

        # Get or create checkpoint
        checkpoint = (
            session.query(DDValidationCheckpoint)
            .filter(
                DDValidationCheckpoint.dd_id == dd_uuid,
                DDValidationCheckpoint.checkpoint_type == "entity_confirmation"
            )
            .order_by(DDValidationCheckpoint.created_at.desc())
            .first()
        )

        if not checkpoint:
            checkpoint = DDValidationCheckpoint(
                id=uuid_module.uuid4(),
                dd_id=dd_uuid,
                checkpoint_type="entity_confirmation",
                status="awaiting_user_input",
                created_at=datetime.datetime.utcnow()
            )
            session.add(checkpoint)
            session.flush()

        # Build current entity map for AI
        current_entity_map = [
            {
                "id": str(e.id),
                "entity_name": e.entity_name,
                "relationship_to_target": e.relationship_to_target,
                "relationship_detail": e.relationship_detail,
                "confidence": e.confidence,
            }
            for e in entities
        ]

        # Get target entity info from dd.project_setup (linked by dd_id)
        project_setup = dd.project_setup or {}
        target_name = project_setup.get("targetEntityName") or dd.name

        # Store entity lookup for updates
        entity_lookup = {str(e.id): e for e in entities}

    # Call AI to process corrections (outside session to avoid timeout)
    try:
        client = get_claude_client()
        ai_response = _process_corrections_with_ai(
            client=client,
            corrections=corrections,
            current_entity_map=current_entity_map,
            target_name=target_name
        )

        if ai_response.get("error"):
            return {"error": f"AI processing failed: {ai_response['error']}"}

        updates = ai_response.get("updates", [])
        reasoning = ai_response.get("reasoning", "")

    except Exception as e:
        logging.exception(f"[DDEntityConfirmation] AI correction failed: {e}")
        return {"error": f"Failed to process corrections: {str(e)}"}

    # Apply updates to database
    with transactional_session() as session:
        # Re-fetch entities in new session
        entities = (
            session.query(DDEntityMap)
            .filter(DDEntityMap.dd_id == dd_uuid)
            .all()
        )
        entity_lookup = {str(e.id): e for e in entities}

        # Re-fetch checkpoint
        checkpoint = (
            session.query(DDValidationCheckpoint)
            .filter(
                DDValidationCheckpoint.dd_id == dd_uuid,
                DDValidationCheckpoint.checkpoint_type == "entity_confirmation"
            )
            .order_by(DDValidationCheckpoint.created_at.desc())
            .first()
        )

        applied_updates = []
        for update in updates:
            entity_id = update.get("entity_id")
            if entity_id and entity_id in entity_lookup:
                entity = entity_lookup[entity_id]

                # Track what changed
                changes = {}

                if update.get("new_relationship"):
                    changes["relationship_to_target"] = {
                        "from": entity.relationship_to_target,
                        "to": update["new_relationship"]
                    }
                    entity.relationship_to_target = update["new_relationship"]

                if update.get("new_relationship_detail"):
                    changes["relationship_detail"] = {
                        "from": entity.relationship_detail,
                        "to": update["new_relationship_detail"]
                    }
                    entity.relationship_detail = update["new_relationship_detail"]

                if update.get("new_name"):
                    changes["entity_name"] = {
                        "from": entity.entity_name,
                        "to": update["new_name"]
                    }
                    entity.entity_name = update["new_name"]

                # Mark as user-corrected but not yet confirmed
                entity.human_confirmation_value = json.dumps({
                    "corrected_by": user_email,
                    "corrected_at": datetime.datetime.utcnow().isoformat(),
                    "changes": changes
                })

                applied_updates.append({
                    "entity_id": entity_id,
                    "entity_name": entity.entity_name,
                    "changes": changes
                })

        # Update checkpoint with correction round
        correction_round = {
            "round_number": len((checkpoint.user_responses or {}).get("correction_rounds", [])) + 1,
            "user_corrections": corrections,
            "ai_reasoning": reasoning,
            "updates_applied": applied_updates,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "user_email": user_email
        }

        if not checkpoint.user_responses:
            checkpoint.user_responses = {}

        if "correction_rounds" not in checkpoint.user_responses:
            checkpoint.user_responses["correction_rounds"] = []

        checkpoint.user_responses["correction_rounds"].append(correction_round)
        checkpoint.user_responses = checkpoint.user_responses  # Trigger SQLAlchemy update

        session.commit()

        logging.info(f"[DDEntityConfirmation] Applied {len(applied_updates)} updates")

    # Return updated entity map
    return get_entity_map_for_review(dd_id)


def _process_corrections_with_ai(
    client: Any,
    corrections: str,
    current_entity_map: List[Dict],
    target_name: str
) -> Dict[str, Any]:
    """
    Use Sonnet to interpret user corrections and determine entity updates.

    Only updates entities that need changing based on user feedback.
    """
    from dd_enhanced.prompts.entity_mapping import ENTITY_CORRECTION_SYSTEM_PROMPT

    prompt = f"""You are reviewing an entity map for a due diligence transaction.

TARGET ENTITY: {target_name}

CURRENT ENTITY MAP:
{json.dumps(current_entity_map, indent=2)}

USER'S CORRECTIONS:
{corrections}

Based on the user's corrections, identify which specific entities need to be updated.
Only update entities that the user has indicated are incorrect.

Respond in JSON format:
{{
    "reasoning": "Brief explanation of what you understood from the corrections",
    "updates": [
        {{
            "entity_id": "id of entity to update",
            "entity_name": "current name for reference",
            "new_relationship": "new relationship_to_target value (only if changing)",
            "new_relationship_detail": "new detail (only if changing)",
            "new_name": "corrected name (only if changing)"
        }}
    ]
}}

Valid relationship_to_target values: target, parent, subsidiary, counterparty, related_party, unknown

If no updates are needed based on the corrections, return empty updates array.
"""

    system_prompt = """You are an expert legal analyst helping to correct entity mapping in due diligence.
Your task is to interpret user corrections and identify the minimal set of entity updates needed.
Be precise - only update what the user has indicated is wrong.
Always respond with valid JSON."""

    response = client.complete(
        prompt=prompt,
        system=system_prompt,
        model="sonnet",  # Explicitly use Sonnet for accuracy
        json_mode=True,
        max_tokens=2000,
        temperature=0.1
    )

    if "error" in response:
        return {"error": response["error"]}

    return response


def confirm_entity_map(dd_id: str, user_email: str) -> dict:
    """
    Confirm entity map as source of truth.

    Marks all entities as human_confirmed and completes the checkpoint.
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    logging.info(f"[DDEntityConfirmation] Confirming entity map for DD: {dd_id}")

    with transactional_session() as session:
        # Verify DD exists
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
        if not dd:
            return {"error": f"Due diligence {dd_id} not found"}

        # Get all entities
        entities = (
            session.query(DDEntityMap)
            .filter(DDEntityMap.dd_id == dd_uuid)
            .all()
        )

        if not entities:
            return {"error": "No entities found to confirm"}

        # Mark all entities as confirmed
        confirmed_at = datetime.datetime.utcnow()
        for entity in entities:
            entity.human_confirmed = True
            if not entity.human_confirmation_value:
                entity.human_confirmation_value = json.dumps({
                    "confirmed_by": user_email,
                    "confirmed_at": confirmed_at.isoformat(),
                    "confirmed_as_is": True
                })

        # Complete checkpoint
        checkpoint = (
            session.query(DDValidationCheckpoint)
            .filter(
                DDValidationCheckpoint.dd_id == dd_uuid,
                DDValidationCheckpoint.checkpoint_type == "entity_confirmation"
            )
            .order_by(DDValidationCheckpoint.created_at.desc())
            .first()
        )

        if checkpoint:
            checkpoint.status = "completed"
            checkpoint.completed_at = confirmed_at
            if not checkpoint.user_responses:
                checkpoint.user_responses = {}
            checkpoint.user_responses["final_confirmation"] = {
                "confirmed_by": user_email,
                "confirmed_at": confirmed_at.isoformat(),
                "total_entities": len(entities)
            }
            checkpoint.user_responses = checkpoint.user_responses  # Trigger update
        else:
            # Create completed checkpoint if none exists
            checkpoint = DDValidationCheckpoint(
                id=uuid_module.uuid4(),
                dd_id=dd_uuid,
                checkpoint_type="entity_confirmation",
                status="completed",
                created_at=confirmed_at,
                completed_at=confirmed_at,
                user_responses={
                    "final_confirmation": {
                        "confirmed_by": user_email,
                        "confirmed_at": confirmed_at.isoformat(),
                        "total_entities": len(entities)
                    }
                }
            )
            session.add(checkpoint)

        session.commit()

        logging.info(f"[DDEntityConfirmation] Confirmed {len(entities)} entities")

        return {
            "dd_id": str(dd_uuid),
            "status": "confirmed",
            "message": f"Entity map confirmed with {len(entities)} entities",
            "checkpoint_id": str(checkpoint.id),
            "confirmed_at": confirmed_at.isoformat(),
            "confirmed_by": user_email,
            "total_entities": len(entities)
        }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Entity Confirmation endpoints (Checkpoint B).

    GET /api/dd-entity-confirmation/{dd_id}
    - Returns current entity map for review with summary stats

    POST /api/dd-entity-confirmation/correct
    Body: {
        "dd_id": "uuid",
        "corrections": "User's correction text"
    }
    - AI processes corrections and updates affected entities
    - Returns updated entity map

    POST /api/dd-entity-confirmation/confirm
    Body: {
        "dd_id": "uuid"
    }
    - Marks entity map as confirmed (source of truth)
    - Completes Checkpoint B
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        method = req.method

        # GET - Get entity map for review
        if method == "GET":
            dd_id = req.route_params.get("dd_id") or req.params.get("dd_id")
            if not dd_id:
                return func.HttpResponse(
                    json.dumps({"error": "dd_id is required"}),
                    status_code=400,
                    mimetype="application/json"
                )

            result = get_entity_map_for_review(dd_id)

            if result.get("status") == "not_found":
                return func.HttpResponse(
                    json.dumps(result),
                    status_code=404,
                    mimetype="application/json"
                )

            return func.HttpResponse(
                json.dumps(result, default=str),
                status_code=200,
                mimetype="application/json"
            )

        # POST - Handle corrections or confirmation
        if method == "POST":
            try:
                req_body = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON body"}),
                    status_code=400,
                    mimetype="application/json"
                )

            action = req_body.get("action", "")
            dd_id = req_body.get("dd_id")

            if not dd_id:
                return func.HttpResponse(
                    json.dumps({"error": "dd_id is required"}),
                    status_code=400,
                    mimetype="application/json"
                )

            if action == "correct":
                corrections = req_body.get("corrections", "")
                if not corrections:
                    return func.HttpResponse(
                        json.dumps({"error": "corrections text is required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = submit_entity_corrections(dd_id, corrections, email)

            elif action == "confirm":
                result = confirm_entity_map(dd_id, email)

            else:
                return func.HttpResponse(
                    json.dumps({"error": f"Unknown action: {action}. Use 'correct' or 'confirm'"}),
                    status_code=400,
                    mimetype="application/json"
                )

            if "error" in result:
                status_code = 404 if "not found" in result.get("error", "") else 400
                return func.HttpResponse(
                    json.dumps(result),
                    status_code=status_code,
                    mimetype="application/json"
                )

            return func.HttpResponse(
                json.dumps(result, default=str),
                status_code=200,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"error": "Method not allowed"}),
            status_code=405,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"[DDEntityConfirmation] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
