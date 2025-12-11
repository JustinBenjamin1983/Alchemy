# ApplyChangesToDraft/__init__.py
import logging
import azure.functions as func
import json
import os
from datetime import datetime, timezone
from shared.utils import auth_get_email, generate_identifier, now
from shared.table_storage import get_user_info, save_user_info, save_opinion_draft, delete_opinion_draft
import time

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ ApplyChangesToDraft function triggered")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("❌ No matching function key in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email failed")
            return err
        
        data = req.get_json()
        
        # Validate required fields
        required_fields = ['opinion_id', 'draft_text']
        for field in required_fields:
            if field not in data:
                return func.HttpResponse(f"Missing required field: {field}", status_code=400)
        
        opinion_id = data["opinion_id"]
        draft_text = data["draft_text"]
        draft_id = data.get("draft_id", "staging")  # Default to staging
        
        # Validate the draft text
        if not validate_draft_text(draft_text):
            logging.warning(f"Invalid draft text for opinion {opinion_id}")
            return func.HttpResponse("Invalid draft text provided", status_code=400)
        
        logging.info(f"Applying changes to draft for opinion {opinion_id}, draft_id: {draft_id}, text length: {len(draft_text)}")
        
        # Get user data with retry logic (same pattern as working function)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user_info = get_user_info(email)
                clean_payload = user_info.get("clean_payload")
                payload = clean_payload if clean_payload else {}
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"⚠️ Attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    raise e
        
        # Find the target opinion
        opinion_found = False
        for opinion in payload.get("opinions", []):
            if opinion.get("id") == opinion_id:
                opinion_found = True
                current_time = now()
                
                # Create backup of existing draft if it exists
                existing_draft = opinion.get("staging_draft")
                if existing_draft:
                    backup = create_draft_backup(existing_draft, opinion_id)
                    logging.info(f"Created backup of existing staging draft for opinion {opinion_id}")
                
                # Handle staging draft updates (use blob storage like the working function)
                if draft_id == "staging" or draft_id is None:
                    # Generate new staging draft ID
                    staging_draft_id = f"staging_{opinion_id}_{generate_identifier()}"
                    
                    # Clean up any existing staging draft from blob storage
                    if "staging_draft" in opinion and opinion["staging_draft"].get("draft_id"):
                        old_draft_id = opinion["staging_draft"]["draft_id"]
                        try:
                            delete_opinion_draft(old_draft_id)
                            logging.info(f"🗑️ Cleaned up old staging draft: {old_draft_id}")
                        except Exception as e:
                            logging.warning(f"⚠️ Failed to cleanup old staging draft: {e}")
                    
                    # Save draft to blob storage (consistent with working function)
                    save_opinion_draft(staging_draft_id, {
                        "draft": draft_text,
                        "created_on": opinion.get("staging_draft", {}).get("created_on", current_time),
                        "updated_on": current_time,
                        "applied_changes": True,  # Flag to indicate this was modified by AI changes
                        "saved_by": email,
                        "version": 0,
                        "name": "Working Draft - AI Modified",
                        "is_staging": True,
                        "opinion_id": opinion_id,
                        "character_count": len(draft_text),
                        "word_count": len(draft_text.split())
                    })
                    
                    # Store reference in user payload (consistent with working function)
                    draft_size = len(json.dumps(draft_text).encode('utf-8'))
                    opinion["staging_draft"] = {
                        "draft_id": staging_draft_id,
                        "draft_size": draft_size,
                        "created_on": opinion.get("staging_draft", {}).get("created_on", current_time),
                        "updated_on": current_time,
                        "saved_by": email,
                        "version_info": "staging_ai_modified",
                        "applied_changes": True
                    }
                    
                    logging.info(f"✅ AI-modified staging draft saved to blob storage: {staging_draft_id}")
                    result_draft_id = "staging"
                
                else:
                    # Handle updating existing versioned drafts by creating a new staging draft
                    # This creates a new staging draft based on the versioned draft with AI changes applied
                    staging_draft_id = f"staging_{opinion_id}_{generate_identifier()}"
                    
                    # Clean up any existing staging draft
                    if "staging_draft" in opinion and opinion["staging_draft"].get("draft_id"):
                        old_draft_id = opinion["staging_draft"]["draft_id"]
                        try:
                            delete_opinion_draft(old_draft_id)
                            logging.info(f"🗑️ Cleaned up old staging draft: {old_draft_id}")
                        except Exception as e:
                            logging.warning(f"⚠️ Failed to cleanup old staging draft: {e}")
                    
                    # Save new staging draft to blob storage
                    save_opinion_draft(staging_draft_id, {
                        "draft": draft_text,
                        "created_on": current_time,
                        "updated_on": current_time,
                        "applied_changes": True,
                        "based_on_draft_id": draft_id,  # Track what this was based on
                        "saved_by": email,
                        "version": 0,
                        "name": f"Working Draft - Based on {draft_id} - AI Modified",
                        "is_staging": True,
                        "opinion_id": opinion_id,
                        "character_count": len(draft_text),
                        "word_count": len(draft_text.split())
                    })
                    
                    # Update opinion reference
                    draft_size = len(json.dumps(draft_text).encode('utf-8'))
                    opinion["staging_draft"] = {
                        "draft_id": staging_draft_id,
                        "draft_size": draft_size,
                        "created_on": current_time,
                        "updated_on": current_time,
                        "saved_by": email,
                        "version_info": f"staging_based_on_{draft_id}_ai_modified",
                        "applied_changes": True,
                        "based_on_draft_id": draft_id
                    }
                    
                    logging.info(f"✅ New AI-modified staging draft created based on {draft_id}: {staging_draft_id}")
                    result_draft_id = "staging"
                
                # Update opinion metadata
                opinion["last_modified"] = current_time
                if "modification_history" not in opinion:
                    opinion["modification_history"] = []
                
                opinion["modification_history"].append({
                    "action": "apply_ai_changes_to_draft",
                    "draft_id": result_draft_id,
                    "timestamp": current_time,
                    "character_count": len(draft_text),
                    "applied_by": "alchemio_ai",
                    "based_on_draft_id": draft_id if draft_id != "staging" else None
                })
                
                # Keep only last 10 modification history entries to prevent bloat
                if len(opinion["modification_history"]) > 10:
                    opinion["modification_history"] = opinion["modification_history"][-10:]
                
                break
        
        if not opinion_found:
            logging.error(f"❌ No opinion found with ID '{opinion_id}'")
            return func.HttpResponse(
                body=json.dumps({
                    "error": f"Opinion with ID '{opinion_id}' not found",
                    "success": False
                }),
                mimetype="application/json", 
                status_code=404
            )
        
        # Save updated user payload (same pattern as working function)
        max_save_retries = 3
        for attempt in range(max_save_retries):
            try:
                save_user_info(email, payload)  # Using save_user_info instead of update_user_info
                logging.info(f"✅ Successfully saved user payload (attempt {attempt + 1})")
                break
            except Exception as e:
                if attempt < max_save_retries - 1:
                    logging.warning(f"⚠️ Save attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    raise e
        
        # Return success response
        return func.HttpResponse(json.dumps({
            "success": True,
            "message": "AI draft changes applied successfully to blob storage",
            "draft_id": result_draft_id,
            "updated_on": current_time,
            "character_count": len(draft_text),
            "word_count": len(draft_text.split()),
            "storage_type": "blob",
            "is_staging": True,
            "applied_changes": True,
            "status": "success"
        }), mimetype="application/json", status_code=200)
        
    except Exception as e:
        logging.error(f"❌ ApplyChangesToDraft error: {str(e)}")
        logging.exception("Full exception details")
        return func.HttpResponse(json.dumps({
            "success": False,
            "message": f"Server error: {str(e)}",
            "status": "error"
        }), mimetype="application/json", status_code=500)

def validate_draft_text(draft_text: str) -> bool:
    """
    Validate the draft text to ensure it's reasonable
    """
    if not draft_text or not draft_text.strip():
        logging.warning("Draft text is empty or whitespace only")
        return False
    
    # Check minimum length (should be a substantial legal opinion)
    if len(draft_text.strip()) < 100:
        logging.warning(f"Draft text too short: {len(draft_text.strip())} characters")
        return False
    
    # Check maximum length (reasonable upper limit)
    if len(draft_text) > 1000000:  # 1MB text limit
        logging.warning(f"Draft text too long: {len(draft_text)} characters")
        return False
    
    # Check for suspicious patterns that might indicate corruption
    if draft_text.count('\x00') > 0:  # Null bytes
        logging.warning("Draft text contains null bytes")
        return False
    
    # Check that it's not just repeated characters
    unique_chars = len(set(draft_text.replace(' ', '').replace('\n', '')))
    if unique_chars < 10:  # Should have at least 10 different characters
        logging.warning(f"Draft text has too few unique characters: {unique_chars}")
        return False
    
    # Basic structure check - should have some common legal opinion elements
    text_lower = draft_text.lower()
    legal_indicators = ['opinion', 'legal', 'court', 'law', 'section', 'act', 'case', 'matter', 'client', 'advice']
    indicator_count = sum(1 for indicator in legal_indicators if indicator in text_lower)
    
    if indicator_count < 2:  # Should have at least 2 legal indicators
        logging.warning(f"Draft text doesn't appear to be a legal opinion (indicators: {indicator_count})")
        # Don't reject, just log warning - might be a draft in progress
    
    return True

def create_draft_backup(original_draft: dict, opinion_id: str) -> dict:
    """
    Create a backup of the original draft before applying changes
    """
    backup = {
        "original_draft": original_draft.copy(),
        "backup_created": datetime.now(timezone.utc).isoformat(),
        "opinion_id": opinion_id,
        "reason": "pre_ai_changes_backup",
        "character_count": len(str(original_draft.get("draft", ""))),
        "word_count": len(str(original_draft.get("draft", "")).split())
    }
    
    logging.info(f"Backup created for opinion {opinion_id}: {backup['character_count']} chars")
    return backup