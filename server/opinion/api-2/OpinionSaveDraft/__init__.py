# OpinionSaveDraft/__init__.py
import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email, generate_identifier, now
from shared.table_storage import save_user_info, get_user_info, save_opinion_draft, delete_opinion_draft
import time

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('✅ SaveDraft function triggered')
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("❌ No matching function key in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        body = req.get_json()
        email, err = auth_get_email(req)
        if err:
            return err
        
        opinion_id = body['opinion_id']
        draft = body['draft']
        version_name = body.get('version_name', None)  # Optional - if None, it's a staging draft
        
        # Determine if this is a staging draft or versioned draft
        is_staging = version_name is None
        
        if is_staging:
            logging.info(f"💾 Saving STAGING draft for opinion {opinion_id}")
        else:
            logging.info(f"💾 Saving VERSIONED draft for opinion {opinion_id} - Version: {version_name}")
        
        # Calculate draft size for logging
        draft_size = len(json.dumps(draft).encode('utf-8'))
        logging.info(f"📊 Draft size: {draft_size} bytes - using BLOB STORAGE")
        
        # Get user info with retry logic
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
        
        # Find the opinion
        opinion_found = False
        for opinion in payload.get("opinions", []):
            if opinion.get("id") == opinion_id:
                opinion_found = True
                
                if is_staging:
                    # STAGING DRAFT: Store in blob storage
                    staging_draft_id = f"staging_{opinion_id}_{generate_identifier()}"
                    
                    # Clean up any existing staging draft from blob storage
                    if "staging_draft" in opinion and opinion["staging_draft"].get("draft_id"):
                        old_draft_id = opinion["staging_draft"]["draft_id"]
                        try:
                            delete_opinion_draft(old_draft_id)
                            logging.info(f"🗑️ Cleaned up old staging draft: {old_draft_id}")
                        except Exception as e:
                            logging.warning(f"⚠️ Failed to cleanup old staging draft: {e}")
                    
                    # Save to blob storage
                    save_opinion_draft(staging_draft_id, {
                        "draft": draft,
                        "created_on": now(),
                        "saved_by": email,
                        "version": 0,
                        "name": "Working Draft",
                        "is_staging": True,
                        "opinion_id": opinion_id
                    })
                    
                    # Store reference in user payload
                    opinion["staging_draft"] = {
                        "draft_id": staging_draft_id,
                        "draft_size": draft_size,
                        "created_on": now(),
                        "saved_by": email,
                        "version_info": "staging"
                    }
                    
                    logging.info(f"✅ Staging draft saved to blob storage: {staging_draft_id}")
                    
                else:
                    # VERSIONED DRAFT: Store in blob storage
                    new_draft_id = generate_identifier()
                    opinion.setdefault("drafts", [])
                    current_highest_version = max(
                        (item["version"] for item in opinion["drafts"]), 
                        default=-1
                    )
                    next_version = current_highest_version + 1
                    opinion["drafts"].append({
                        "draft_id": new_draft_id, 
                        "version": next_version, 
                        "name": version_name
                    })
                    
                    # Save to blob storage
                    save_opinion_draft(new_draft_id, {
                        "draft": draft,
                        "created_on": now(),
                        "saved_by": email,
                        "version": next_version,
                        "name": version_name,
                        "is_staging": False
                    })
                    
                    # CLEAR STAGING DRAFT when saving as version
                    if "staging_draft" in opinion:
                        # Clean up staging draft from blob storage
                        staging_draft_id = opinion["staging_draft"].get("draft_id")
                        if staging_draft_id:
                            try:
                                delete_opinion_draft(staging_draft_id)
                                logging.info(f"🗑️ Cleaned up staging draft: {staging_draft_id}")
                            except Exception as e:
                                logging.warning(f"⚠️ Failed to cleanup staging draft: {e}")
                        
                        del opinion["staging_draft"]
                        logging.info("✅ Cleared staging draft when saving as version")
                    
                    logging.info(f"✅ Version {next_version} saved to blob storage: {new_draft_id}")
                
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
        
        # Save updated user payload
        max_save_retries = 3
        for attempt in range(max_save_retries):
            try:
                save_user_info(email, payload)
                logging.info(f"✅ Successfully saved user payload (attempt {attempt + 1})")
                break
            except Exception as e:
                if attempt < max_save_retries - 1:
                    logging.warning(f"⚠️ Save attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    raise e
        
        # Return appropriate response
        if is_staging:
            return func.HttpResponse(
                body=json.dumps({
                    "success": True, 
                    "message": "Staging draft saved successfully to blob storage",
                    "draft_id": staging_draft_id,
                    "opinion_id": opinion_id,
                    "draft_size": draft_size,
                    "storage_type": "blob",
                    "is_staging": True,
                    "saved_at": now()
                }), 
                mimetype="application/json", 
                status_code=200
            )
        else:
            return func.HttpResponse(
                body=json.dumps({
                    "success": True,
                    "message": "Version saved successfully to blob storage", 
                    "new_draft_id": new_draft_id,
                    "version": next_version,
                    "storage_type": "blob",
                    "is_staging": False
                }), 
                mimetype="application/json", 
                status_code=200
            )
        
    except Exception as e:
        logging.error(f"❌ Error saving draft: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({
                "error": str(e),
                "success": False
            }),
            mimetype="application/json", 
            status_code=500
        )