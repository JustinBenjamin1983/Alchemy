# DDValidationCheckpoint/__init__.py
"""
Phase 8 & 9: Human-in-the-Loop Validation Checkpoints

Provides endpoints for:
- Checkpoint A: Missing documents validation (after classification)
- Checkpoint B: Entity confirmation (after entity mapping) - see DDEntityConfirmation
- Checkpoint C: Combined validation wizard (after Pass 2, 4-step confirmation)

Endpoints:
- GET /api/dd-validation-checkpoint/{dd_id} - Get pending checkpoint
- POST /api/dd-validation-checkpoint/respond - Submit checkpoint response
- POST /api/dd-validation-checkpoint/upload - Upload docs during checkpoint
- POST /api/dd-validation-checkpoint/skip - Skip checkpoint
- POST /api/dd-validation-checkpoint/regenerate_summary - Regenerate summary with corrections
"""
import logging
import os
import json
import datetime
import azure.functions as func
import uuid as uuid_module

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import (
    Document, Folder, DueDiligence,
    DDValidationCheckpoint, DDAnalysisRun, PerspectiveRiskFinding
)
from dd_enhanced.core.claude_client import ClaudeClient

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def get_pending_checkpoint(dd_id: str) -> dict:
    """
    Get checkpoint for a DD project.

    Returns the most recent checkpoint, prioritizing pending/awaiting_user_input
    but also returning completed/skipped checkpoints so the UI can show status.
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    with transactional_session() as session:
        # First try to find a pending checkpoint that needs action
        checkpoint = (
            session.query(DDValidationCheckpoint)
            .filter(
                DDValidationCheckpoint.dd_id == dd_uuid,
                DDValidationCheckpoint.status.in_(["pending", "awaiting_user_input"])
            )
            .order_by(DDValidationCheckpoint.created_at.asc())
            .first()
        )

        # If no pending checkpoint, get the most recent completed/skipped one
        # so the UI can show the green "completed" state
        if not checkpoint:
            checkpoint = (
                session.query(DDValidationCheckpoint)
                .filter(
                    DDValidationCheckpoint.dd_id == dd_uuid,
                    DDValidationCheckpoint.status.in_(["completed", "skipped"])
                )
                .order_by(DDValidationCheckpoint.created_at.desc())
                .first()
            )

        if not checkpoint:
            return {
                "has_checkpoint": False,
                "dd_id": str(dd_uuid)
            }

        return {
            "has_checkpoint": True,
            "dd_id": str(dd_uuid),
            "checkpoint": {
                "id": str(checkpoint.id),
                "checkpoint_type": checkpoint.checkpoint_type,
                "status": checkpoint.status,
                "preliminary_summary": checkpoint.preliminary_summary,
                "questions": checkpoint.questions,
                "missing_docs": checkpoint.missing_docs,
                "financial_confirmations": checkpoint.financial_confirmations,
                "user_responses": checkpoint.user_responses,
                "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None
            }
        }


def create_checkpoint(
    dd_id: str,
    run_id: str,
    checkpoint_type: str,
    content: dict
) -> dict:
    """
    Create a new validation checkpoint.

    Args:
        dd_id: Due diligence ID
        run_id: Analysis run ID
        checkpoint_type: 'missing_docs' | 'post_analysis' | 'entity_confirmation'
        content: Checkpoint content (questions, missing_docs, etc.)

    Returns:
        Created checkpoint dict
    """
    dd_uuid = uuid_module.UUID(dd_id) if isinstance(dd_id, str) else dd_id
    run_uuid = uuid_module.UUID(run_id) if run_id and isinstance(run_id, str) else run_id

    with transactional_session() as session:
        checkpoint = DDValidationCheckpoint(
            id=uuid_module.uuid4(),
            dd_id=dd_uuid,
            run_id=run_uuid,
            checkpoint_type=checkpoint_type,
            status="awaiting_user_input",
            preliminary_summary=content.get("preliminary_summary"),
            questions=content.get("questions"),
            missing_docs=content.get("missing_docs"),
            financial_confirmations=content.get("financial_confirmations"),
            created_at=datetime.datetime.utcnow()
        )

        session.add(checkpoint)
        session.commit()

        return {
            "checkpoint_id": str(checkpoint.id),
            "checkpoint_type": checkpoint_type,
            "status": "awaiting_user_input"
        }


def submit_checkpoint_response(checkpoint_id: str, responses: dict) -> dict:
    """
    Submit user responses to a checkpoint.

    Args:
        checkpoint_id: Checkpoint UUID
        responses: User responses dict

    Returns:
        Updated checkpoint status
    """
    cp_uuid = uuid_module.UUID(checkpoint_id) if isinstance(checkpoint_id, str) else checkpoint_id

    with transactional_session() as session:
        checkpoint = session.query(DDValidationCheckpoint).filter(
            DDValidationCheckpoint.id == cp_uuid
        ).first()

        if not checkpoint:
            return {"error": f"Checkpoint {checkpoint_id} not found"}

        # Store responses
        existing_responses = checkpoint.user_responses or {}
        existing_responses.update(responses)
        checkpoint.user_responses = existing_responses

        # Store financial confirmations if provided
        if responses.get("financial_confirmations"):
            checkpoint.financial_confirmations = responses["financial_confirmations"]

        # Store manual inputs if provided
        if responses.get("manual_inputs"):
            checkpoint.manual_data_inputs = responses["manual_inputs"]

        # Check if checkpoint is complete
        is_complete = _check_checkpoint_complete(checkpoint, responses)

        if is_complete:
            checkpoint.status = "completed"
            checkpoint.completed_at = datetime.datetime.utcnow()
        else:
            checkpoint.status = "awaiting_user_input"

        session.commit()

        return {
            "checkpoint_id": str(checkpoint.id),
            "status": checkpoint.status,
            "is_complete": is_complete,
            "message": "Responses saved" + (" - checkpoint complete" if is_complete else "")
        }


def skip_checkpoint(checkpoint_id: str, reason: str = None) -> dict:
    """
    Skip a checkpoint and mark it as skipped.

    Args:
        checkpoint_id: Checkpoint UUID
        reason: Optional reason for skipping

    Returns:
        Updated checkpoint status
    """
    cp_uuid = uuid_module.UUID(checkpoint_id) if isinstance(checkpoint_id, str) else checkpoint_id

    with transactional_session() as session:
        checkpoint = session.query(DDValidationCheckpoint).filter(
            DDValidationCheckpoint.id == cp_uuid
        ).first()

        if not checkpoint:
            return {"error": f"Checkpoint {checkpoint_id} not found"}

        checkpoint.status = "skipped"
        checkpoint.completed_at = datetime.datetime.utcnow()
        if reason:
            checkpoint.user_responses = {
                **(checkpoint.user_responses or {}),
                "skip_reason": reason
            }

        session.commit()

        return {
            "checkpoint_id": str(checkpoint.id),
            "status": "skipped",
            "message": "Checkpoint skipped"
        }


def get_validated_context(run_id: str) -> dict:
    """
    Get validated context from completed checkpoints for a run.

    This is used by Pass 2.5 (Calculate) and Pass 4 (Synthesize) to
    incorporate user corrections including entity confirmations.

    Args:
        run_id: Analysis run ID

    Returns:
        Validated context dict with corrections and entity confirmations
    """
    run_uuid = uuid_module.UUID(run_id) if isinstance(run_id, str) else run_id

    with transactional_session() as session:
        checkpoints = (
            session.query(DDValidationCheckpoint)
            .filter(
                DDValidationCheckpoint.run_id == run_uuid,
                DDValidationCheckpoint.status == "completed"
            )
            .all()
        )

        if not checkpoints:
            return {"has_validated_context": False}

        validated_context = {
            "has_validated_context": True,
            "transaction_understanding": [],
            "financial_corrections": [],
            "entity_confirmations": [],  # User-confirmed entity relationships
            "manual_inputs": {},
            "validated_at": None
        }

        for cp in checkpoints:
            if cp.user_responses:
                # Collect understanding responses
                for key, value in cp.user_responses.items():
                    if key.startswith("question_"):
                        validated_context["transaction_understanding"].append({
                            "question_id": key,
                            "response": value
                        })
                    # Collect entity confirmations from user responses
                    elif key.startswith("entity_"):
                        entity_name = key.replace("entity_", "").replace("_", " ")
                        validated_context["entity_confirmations"].append({
                            "entity_name": entity_name,
                            "confirmed_relationship": value.get("relationship") if isinstance(value, dict) else value,
                            "user_notes": value.get("notes") if isinstance(value, dict) else None
                        })

            if cp.financial_confirmations:
                for conf in cp.financial_confirmations:
                    if conf.get("confirmed_value") != conf.get("extracted_value"):
                        validated_context["financial_corrections"].append({
                            "metric": conf.get("metric"),
                            "original_value": conf.get("extracted_value"),
                            "corrected_value": conf.get("confirmed_value"),
                            "source": conf.get("source_document")
                        })

            if cp.manual_data_inputs:
                validated_context["manual_inputs"].update(cp.manual_data_inputs)

            # Handle entity_confirmation checkpoint type specifically
            if cp.checkpoint_type == "entity_confirmation" and cp.questions:
                for entity_q in cp.questions:
                    entity_name = entity_q.get("entity_name", "")
                    entity_key = f"entity_{entity_name.replace(' ', '_').lower()}"

                    # Check if this entity was confirmed in responses
                    if cp.user_responses and entity_key in cp.user_responses:
                        response = cp.user_responses[entity_key]
                        validated_context["entity_confirmations"].append({
                            "entity_name": entity_name,
                            "original_relationship": entity_q.get("detected_relationship"),
                            "confirmed_relationship": response.get("relationship") if isinstance(response, dict) else response,
                            "confidence": entity_q.get("confidence"),
                            "user_notes": response.get("notes") if isinstance(response, dict) else None
                        })

            if cp.completed_at:
                validated_context["validated_at"] = cp.completed_at.isoformat()

        return validated_context


def build_entity_confirmation_content(entity_map: list, dd_id: str = None) -> dict:
    """
    Build checkpoint content for entity confirmation from entity map.

    This is used by Checkpoint B (entity confirmation) to present entities
    for user review. See DDEntityConfirmation for the full loop implementation.

    Args:
        entity_map: List of entity dicts from DDEntityMapping
        dd_id: Optional DD ID for context

    Returns:
        Dict with entity confirmation questions for checkpoint
    """
    if not entity_map:
        return {
            "entity_summary": {
                "status": "missing",
                "message": "Entity mapping was not performed during pre-processing. Please provide key party information.",
                "total_entities": 0,
                "entities_needing_confirmation": 0
            },
            "questions": [{
                "question_type": "entity_input",
                "prompt": "No entities were automatically identified. Please provide the key parties involved in this transaction:",
                "fields": [
                    {"name": "target_entity", "label": "Target Entity Name", "required": True},
                    {"name": "parent_company", "label": "Parent/Holding Company (if any)", "required": False},
                    {"name": "counterparties", "label": "Key Counterparties (comma-separated)", "required": False},
                    {"name": "subsidiaries", "label": "Known Subsidiaries (comma-separated)", "required": False}
                ]
            }]
        }

    # Identify entities needing confirmation
    entities_needing_confirmation = [
        e for e in entity_map if e.get("requires_human_confirmation", False)
    ]

    # Build summary
    summary = {
        "status": "loaded",
        "total_entities": len(entity_map),
        "entities_needing_confirmation": len(entities_needing_confirmation),
        "high_confidence_entities": sum(1 for e in entity_map if e.get("confidence", 0) >= 0.8),
        "relationship_breakdown": {}
    }

    # Count by relationship type
    for entity in entity_map:
        rel = entity.get("relationship_to_target", "unknown")
        summary["relationship_breakdown"][rel] = summary["relationship_breakdown"].get(rel, 0) + 1

    # Build questions for entities needing confirmation
    questions = []
    for entity in entities_needing_confirmation:
        questions.append({
            "question_type": "entity_confirmation",
            "entity_name": entity.get("entity_name", ""),
            "detected_relationship": entity.get("relationship_to_target", "unknown"),
            "confidence": entity.get("confidence", 0),
            "confirmation_reason": entity.get("confirmation_reason", "Requires verification"),
            "documents_appearing_in": entity.get("documents_appearing_in", [])[:5],  # Limit to 5
            "evidence": entity.get("evidence", "")[:500],  # Truncate evidence
            "options": [
                {"value": "subsidiary", "label": "Subsidiary of Target"},
                {"value": "parent", "label": "Parent/Holding Company"},
                {"value": "counterparty", "label": "Counterparty (customer, supplier, lender)"},
                {"value": "related_party", "label": "Related Party"},
                {"value": "target", "label": "This is the Target Entity"},
                {"value": "not_relevant", "label": "Not Relevant to Transaction"},
                {"value": "unknown", "label": "Cannot Determine"}
            ]
        })

    # Add high-confidence entities for reference (not requiring confirmation)
    high_confidence_entities = [
        {
            "entity_name": e.get("entity_name", ""),
            "relationship_to_target": e.get("relationship_to_target", ""),
            "confidence": e.get("confidence", 0)
        }
        for e in entity_map
        if e.get("confidence", 0) >= 0.8 and not e.get("requires_human_confirmation")
    ][:10]  # Limit to top 10

    return {
        "entity_summary": summary,
        "questions": questions,
        "high_confidence_entities": high_confidence_entities,
        "message": f"Found {len(entity_map)} entities. {len(entities_needing_confirmation)} require your confirmation."
            if entities_needing_confirmation else f"Found {len(entity_map)} entities with high confidence. Review if needed."
    }


def _check_checkpoint_complete(checkpoint: DDValidationCheckpoint, responses: dict) -> bool:
    """Check if checkpoint has all required responses."""
    checkpoint_type = checkpoint.checkpoint_type

    if checkpoint_type == "missing_docs":
        # Complete if all missing docs have a response
        missing_docs = checkpoint.missing_docs or []
        for doc in missing_docs:
            doc_key = f"doc_{doc.get('doc_type', '').replace(' ', '_').lower()}"
            if doc_key not in responses:
                return False
        return True

    elif checkpoint_type == "post_analysis":
        # Complete if all steps are marked done
        return responses.get("step_4_confirmed", False)

    elif checkpoint_type == "entity_confirmation":
        # Complete if all flagged entities have confirmation
        questions = checkpoint.questions or []
        for q in questions:
            q_key = f"entity_{q.get('entity_name', '').replace(' ', '_').lower()}"
            if q_key not in responses:
                return False
        return True

    return False


def regenerate_summary_with_corrections(checkpoint_id: str, corrections: dict) -> dict:
    """
    Use Claude AI to regenerate the preliminary summary incorporating user corrections.

    Args:
        checkpoint_id: Checkpoint UUID
        corrections: Dict containing:
            - question_responses: Dict of question responses with correction_text
            - financial_confirmations: List of financial confirmation responses

    Returns:
        Dict with updated_summary and success status
    """
    cp_uuid = uuid_module.UUID(checkpoint_id) if isinstance(checkpoint_id, str) else checkpoint_id

    with transactional_session() as session:
        checkpoint = session.query(DDValidationCheckpoint).filter(
            DDValidationCheckpoint.id == cp_uuid
        ).first()

        if not checkpoint:
            return {"error": f"Checkpoint {checkpoint_id} not found"}

        original_summary = checkpoint.preliminary_summary or ""

        # Extract corrections from user responses
        question_corrections = []
        question_uncertainties = []
        question_responses = corrections.get("question_responses", {})

        for q_id, response in question_responses.items():
            if isinstance(response, dict):
                correction_text = response.get("correction_text", "")
                selected_option = response.get("selected_option", "")

                # Check if this is an uncertainty flag
                if selected_option and selected_option.lower() == "uncertain_check":
                    question_uncertainties.append({
                        "question_id": q_id,
                        "check_note": correction_text
                    })
                # Check if this is a non-confirmation response (i.e., a correction)
                # "accept_ai" means user accepts AI's assessment without reviewing
                elif selected_option:
                    confirm_values = ["correct", "accurate", "agree", "confirmed", "yes",
                                      "confirmed_blocker", "all_addressed", "well_covered",
                                      "no_issues", "not_found", "accept_ai",
                                      "not_relevant", "not_applicable"]
                    if selected_option.lower() not in confirm_values:
                        question_corrections.append({
                            "question_id": q_id,
                            "user_response": selected_option,
                            "correction_details": correction_text
                        })

        # Extract financial corrections and uncertainty flags
        financial_corrections = []
        financial_uncertainties = []
        financial_confirmations = corrections.get("financial_confirmations", [])

        for fin_conf in financial_confirmations:
            if isinstance(fin_conf, dict):
                status = fin_conf.get("status", "")
                if status in ["incorrect", "partial"]:
                    financial_corrections.append({
                        "metric": fin_conf.get("metric", ""),
                        "original_value": fin_conf.get("extracted_value"),
                        "corrected_value": fin_conf.get("confirmed_value"),
                        "currency": fin_conf.get("currency", "ZAR"),
                        "correction_text": fin_conf.get("correction_text", "")
                    })
                elif status == "uncertain_check":
                    financial_uncertainties.append({
                        "metric": fin_conf.get("metric", ""),
                        "value": fin_conf.get("extracted_value"),
                        "currency": fin_conf.get("currency", "ZAR"),
                        "check_note": fin_conf.get("correction_text", "")
                    })

        # If no corrections or uncertainties, return original summary
        has_changes = (question_corrections or question_uncertainties or
                       financial_corrections or financial_uncertainties)
        if not has_changes:
            return {
                "success": True,
                "updated_summary": original_summary,
                "message": "No corrections to incorporate"
            }

        # Build prompt for Claude
        corrections_text = ""

        if question_corrections:
            corrections_text += "\n\nUSER CORRECTIONS TO TRANSACTION UNDERSTANDING:\n"
            for i, corr in enumerate(question_corrections, 1):
                corrections_text += f"\n{i}. Response: {corr['user_response']}"
                if corr['correction_details']:
                    corrections_text += f"\n   Details: {corr['correction_details']}"

        if question_uncertainties:
            corrections_text += "\n\nQUESTIONS FLAGGED FOR EXTRA VERIFICATION:\n"
            corrections_text += "(User is uncertain about these - AI should double-check specifically)\n"
            for i, unc in enumerate(question_uncertainties, 1):
                corrections_text += f"\n{i}. Question ID: {unc['question_id']}"
                if unc.get('check_note'):
                    corrections_text += f"\n   User note: {unc['check_note']}"

        if financial_corrections:
            corrections_text += "\n\nFINANCIAL CORRECTIONS:\n"
            for i, corr in enumerate(financial_corrections, 1):
                corrections_text += f"\n{i}. {corr['metric']}:"
                corrections_text += f"\n   Original: {corr.get('currency', 'ZAR')} {corr['original_value']:,.0f}" if corr['original_value'] else "\n   Original: Not specified"
                corrections_text += f"\n   Corrected: {corr.get('currency', 'ZAR')} {corr['corrected_value']:,.0f}" if corr['corrected_value'] else "\n   Corrected: Not specified"
                if corr.get('correction_text'):
                    corrections_text += f"\n   Note: {corr['correction_text']}"

        if financial_uncertainties:
            corrections_text += "\n\nFINANCIAL ITEMS FLAGGED FOR EXTRA VERIFICATION:\n"
            corrections_text += "(User is uncertain - AI should double-check these specifically)\n"
            for i, unc in enumerate(financial_uncertainties, 1):
                corrections_text += f"\n{i}. {unc['metric']}: {unc.get('currency', 'ZAR')} {unc['value']:,.0f}" if unc['value'] else f"\n{i}. {unc['metric']}: Value not specified"
                if unc.get('check_note'):
                    corrections_text += f"\n   User note: {unc['check_note']}"

        system_prompt = """You are a legal due diligence expert. Your task is to update a transaction summary
based on user corrections and uncertainty flags. Maintain the professional tone and structure of the original
summary while incorporating the corrections accurately.

CRITICAL FORMATTING RULES:
- Use PLAIN TEXT only - NO markdown, NO asterisks (*), NO bold formatting
- Use UPPERCASE for section headers (e.g., TRANSACTION OVERVIEW, KEY PARTIES)
- Use simple dashes (-) for bullet points
- Use line breaks to separate sections clearly

Content Guidelines:
- Keep the same overall structure (TRANSACTION OVERVIEW, KEY PARTIES, etc.)
- Incorporate corrections naturally into the narrative
- If financial figures were corrected, use the corrected values
- For items flagged as UNCERTAIN: add a brief note in parentheses like "(requires verification)"
- Keep the summary concise but comprehensive
- Do NOT add speculative information - only incorporate what the user provided"""

        user_prompt = f"""Please update the following transaction summary by incorporating the user's corrections.

ORIGINAL SUMMARY:
{original_summary}

{corrections_text}

Provide an updated summary incorporating these corrections. Use the EXACT same plain text format as the original -
NO markdown formatting, NO asterisks for bold. Use UPPERCASE for headers and simple dashes for bullets."""

        try:
            # Use Claude to regenerate the summary
            client = ClaudeClient()
            response = client.complete(
                prompt=user_prompt,
                system=system_prompt,
                model="sonnet",  # Use Sonnet for cost-effectiveness
                max_tokens=2048,
                temperature=0.3,  # Low temperature for consistency
                json_mode=False
            )

            if "error" in response:
                logging.error(f"Claude API error: {response.get('error')}")
                return {
                    "success": False,
                    "error": f"AI regeneration failed: {response.get('error')}",
                    "updated_summary": original_summary
                }

            updated_summary = response.get("text", original_summary)

            # Store the updated summary in the checkpoint
            checkpoint.preliminary_summary = updated_summary
            checkpoint.user_responses = checkpoint.user_responses or {}
            checkpoint.user_responses["summary_regenerated"] = True
            checkpoint.user_responses["summary_regenerated_at"] = datetime.datetime.utcnow().isoformat()

            session.commit()

            return {
                "success": True,
                "updated_summary": updated_summary,
                "corrections_applied": {
                    "question_corrections": len(question_corrections),
                    "financial_corrections": len(financial_corrections)
                },
                "message": f"Summary updated with {len(question_corrections)} understanding corrections and {len(financial_corrections)} financial corrections"
            }

        except Exception as e:
            logging.error(f"Error regenerating summary: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "updated_summary": original_summary
            }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validation checkpoint endpoints.

    GET /api/dd-validation-checkpoint/{dd_id}
    - Returns pending checkpoint if exists

    POST /api/dd-validation-checkpoint/respond
    Body: {
        "checkpoint_id": "uuid",
        "responses": {...}
    }

    POST /api/dd-validation-checkpoint/skip
    Body: {
        "checkpoint_id": "uuid",
        "reason": "optional reason"
    }

    POST /api/dd-validation-checkpoint/create
    Body: {
        "dd_id": "uuid",
        "run_id": "uuid",
        "checkpoint_type": "missing_docs|post_analysis|entity_confirmation",
        "content": {...}
    }
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        method = req.method
        route = req.route_params.get("action", "")

        # GET - Get pending checkpoint
        if method == "GET":
            dd_id = req.route_params.get("dd_id") or req.params.get("dd_id")
            if not dd_id:
                return func.HttpResponse(
                    json.dumps({"error": "dd_id is required"}),
                    status_code=400,
                    mimetype="application/json"
                )

            result = get_pending_checkpoint(dd_id)
            return func.HttpResponse(
                json.dumps(result, default=str),
                status_code=200,
                mimetype="application/json"
            )

        # POST - Handle various actions
        if method == "POST":
            try:
                req_body = req.get_json()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid JSON body"}),
                    status_code=400,
                    mimetype="application/json"
                )

            action = req_body.get("action", route)

            if action == "respond":
                checkpoint_id = req_body.get("checkpoint_id")
                responses = req_body.get("responses", {})

                if not checkpoint_id:
                    return func.HttpResponse(
                        json.dumps({"error": "checkpoint_id is required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = submit_checkpoint_response(checkpoint_id, responses)

            elif action == "skip":
                checkpoint_id = req_body.get("checkpoint_id")
                reason = req_body.get("reason")

                if not checkpoint_id:
                    return func.HttpResponse(
                        json.dumps({"error": "checkpoint_id is required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = skip_checkpoint(checkpoint_id, reason)

            elif action == "create":
                dd_id = req_body.get("dd_id")
                run_id = req_body.get("run_id")
                checkpoint_type = req_body.get("checkpoint_type")
                content = req_body.get("content", {})

                if not dd_id or not checkpoint_type:
                    return func.HttpResponse(
                        json.dumps({"error": "dd_id and checkpoint_type are required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = create_checkpoint(dd_id, run_id, checkpoint_type, content)

            elif action == "validated_context":
                run_id = req_body.get("run_id")
                if not run_id:
                    return func.HttpResponse(
                        json.dumps({"error": "run_id is required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = get_validated_context(run_id)

            elif action == "regenerate_summary":
                checkpoint_id = req_body.get("checkpoint_id")
                corrections = req_body.get("corrections", {})

                if not checkpoint_id:
                    return func.HttpResponse(
                        json.dumps({"error": "checkpoint_id is required"}),
                        status_code=400,
                        mimetype="application/json"
                    )

                result = regenerate_summary_with_corrections(checkpoint_id, corrections)

            else:
                return func.HttpResponse(
                    json.dumps({"error": f"Unknown action: {action}"}),
                    status_code=400,
                    mimetype="application/json"
                )

            if "error" in result:
                return func.HttpResponse(
                    json.dumps(result),
                    status_code=400 if "not found" not in result.get("error", "") else 404,
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
        logging.error(f"[DDValidationCheckpoint] Error: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
