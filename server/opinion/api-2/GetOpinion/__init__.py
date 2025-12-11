# GetOpinion/__init__.py - COMPLETE IMPLEMENTATION WITH BLOB STORAGE
import logging
import azure.functions as func
import os
import json
from shared.utils import auth_get_email
from shared.table_storage import get, get_opinion_draft

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ GetOpinion function triggered.")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("❌ No matching function key in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email failed", err)
            return err
            
        logging.info(f"✅ Authenticated user: {email}")
        
        # Get user entity
        entity = get(email, os.environ["USER_TABLE_STORAGE_CONNECTION_STRING"], os.environ["USER_TABLE_NAME"], os.environ["USER_TABLE_PARTITION_KEY"])
        if not entity:
            logging.error(f"❌ No entity found for user: {email}")
            return func.HttpResponse("User not found", status_code=404)
        
        # Parse entity data
        entity_data = json.loads(entity.get("payload", "{}"))
        opinions = entity_data.get("opinions", [])
        
        logging.info(f"📊 User has {len(opinions)} opinions total")
        
        # Get opinion ID filter from query string
        filter_id = req.params.get("id")
        if not filter_id:
            logging.error("❌ No opinion ID provided in query string")
            return func.HttpResponse("Id not supplied", status_code=404)
        
        logging.info(f"🔍 Looking for opinion ID: {filter_id}")
        
        # Find matching opinion
        matched = next((item for item in opinions if item.get("id") == filter_id), None)
        
        if not matched:
            logging.error(f"❌ Opinion not found: {filter_id}")
            available_ids = [op.get("id") for op in opinions[:5]]  # Show first 5 IDs
            logging.info(f"📋 Available opinion IDs: {available_ids}")
            return func.HttpResponse("Opinion not found", status_code=404)
        
        # Make a copy to avoid modifying the original
        opinion_response = matched.copy()
        
        # ✅ CRITICAL: Handle staging draft - retrieve from blob storage if it exists
        if "staging_draft" in opinion_response:
            staging_draft = opinion_response["staging_draft"]
            draft_id = staging_draft.get("draft_id")
            
            logging.info(f"📄 Found staging draft reference: {staging_draft}")
            
            if draft_id:
                logging.info(f"📦 Loading staging draft from blob storage: {draft_id}")
                try:
                    # ✅ RETRIEVE THE STAGING DRAFT FROM BLOB STORAGE
                    blob_draft_data = get_opinion_draft(draft_id)
                    
                    if blob_draft_data and "draft" in blob_draft_data:
                        # Add the actual draft content to the staging_draft object
                        staging_draft["draft"] = blob_draft_data["draft"]
                        
                        # Also include other metadata from blob if available
                        if "created_on" in blob_draft_data:
                            staging_draft["blob_created_on"] = blob_draft_data["created_on"]
                        if "saved_by" in blob_draft_data:
                            staging_draft["blob_saved_by"] = blob_draft_data["saved_by"]
                        
                        draft_size = len(json.dumps(blob_draft_data["draft"]))
                        logging.info(f"✅ Loaded staging draft from blob storage ({draft_size} bytes)")
                        
                        # Update the draft_size in the reference if it wasn't set
                        if "draft_size" not in staging_draft:
                            staging_draft["draft_size"] = draft_size
                        
                    else:
                        logging.warning(f"⚠️ Staging draft {draft_id} not found in blob storage")
                        staging_draft["draft_error"] = "Draft content not found in blob storage"
                        staging_draft["draft_not_found"] = True
                        
                except Exception as e:
                    logging.error(f"❌ Error loading staging draft from blob storage: {e}")
                    staging_draft["draft_error"] = f"Error loading draft: {str(e)}"
            else:
                logging.warning("⚠️ Staging draft reference found but no draft_id")
                staging_draft["draft_error"] = "Missing draft_id reference"
        
        # Log opinion details for debugging
        opinion_details = {
            "id": opinion_response.get("id"),
            "title": opinion_response.get("title", "No title"),
            "has_staging_draft": "staging_draft" in opinion_response,
            "staging_draft_has_content": bool(opinion_response.get("staging_draft", {}).get("draft")) if "staging_draft" in opinion_response else False,
            "staging_draft_size": opinion_response.get("staging_draft", {}).get("draft_size", 0) if "staging_draft" in opinion_response else 0,
            "total_drafts": len(opinion_response.get("drafts", [])),
            "has_documents": len(opinion_response.get("documents", [])) > 0
        }
        
        logging.info(f"✅ Returning opinion: {opinion_details}")
        
        # If there's a staging draft with an error, log it
        if "staging_draft" in opinion_response:
            staging_draft = opinion_response["staging_draft"]
            if staging_draft.get("draft_error"):
                logging.warning(f"⚠️ Staging draft has error: {staging_draft['draft_error']}")
            elif staging_draft.get("draft"):
                draft_length = len(staging_draft["draft"])
                logging.info(f"📄 Staging draft content loaded: {draft_length} characters")
        
        # Return the complete opinion with staging draft content
        logging.info(f"📤 Returning opinion data for: {filter_id}")
        return func.HttpResponse(
            body=json.dumps(opinion_response), 
            mimetype="application/json", 
            status_code=200
        )
    
    except json.JSONDecodeError as e:
        logging.error(f"❌ JSON decode error: {str(e)}")
        return func.HttpResponse("Invalid data format", status_code=500)
    except Exception as e:
        logging.exception(f"❌ Unexpected error in GetOpinion: {str(e)}")
        return func.HttpResponse("Server error", status_code=500)