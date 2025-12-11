# OpinionDelete/__init__.py
import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.table_storage import get_user_info, save_user_info, delete_opinion_draft

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('✅ DeleteOpinion function triggered')
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("❌ No matching function key in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email failed")
            return err
        
        # Get opinion_id from URL parameters
        opinion_id = req.route_params.get('opinion_id')
        if not opinion_id:
            return func.HttpResponse(
                body=json.dumps({"error": "opinion_id parameter is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        logging.info(f"🗑️ Attempting to delete opinion: {opinion_id} for user: {email}")
        
        # Get user info
        user_info = get_user_info(email)
        clean_payload = user_info.get("clean_payload")
        payload = clean_payload if clean_payload else {}
        
        # Find the opinion to delete
        opinions = payload.get("opinions", [])
        opinion_to_delete = None
        opinion_index = -1
        
        for i, opinion in enumerate(opinions):
            if opinion.get("id") == opinion_id:
                opinion_to_delete = opinion
                opinion_index = i
                break
        
        if not opinion_to_delete:
            logging.warning(f"⚠️ Opinion not found: {opinion_id}")
            return func.HttpResponse(
                body=json.dumps({
                    "error": f"Opinion with ID '{opinion_id}' not found",
                    "success": False
                }),
                mimetype="application/json",
                status_code=404
            )
        
        logging.info(f"📋 Found opinion to delete: '{opinion_to_delete.get('title', 'Untitled')}'")
        
        # Clean up associated drafts from blob storage
        drafts_deleted = 0
        draft_errors = []
        
        # Delete staging draft if exists
        if "staging_draft" in opinion_to_delete and opinion_to_delete["staging_draft"].get("draft_id"):
            staging_draft_id = opinion_to_delete["staging_draft"]["draft_id"]
            try:
                delete_opinion_draft(staging_draft_id)
                drafts_deleted += 1
                logging.info(f"🗑️ Deleted staging draft: {staging_draft_id}")
            except Exception as e:
                error_msg = f"Failed to delete staging draft {staging_draft_id}: {str(e)}"
                draft_errors.append(error_msg)
                logging.warning(f"⚠️ {error_msg}")
        
        # Delete versioned drafts if they exist
        versioned_drafts = opinion_to_delete.get("drafts", [])
        for draft_info in versioned_drafts:
            draft_id = draft_info.get("draft_id")
            if draft_id:
                try:
                    delete_opinion_draft(draft_id)
                    drafts_deleted += 1
                    logging.info(f"🗑️ Deleted versioned draft: {draft_id} (v{draft_info.get('version', 'unknown')})")
                except Exception as e:
                    error_msg = f"Failed to delete draft {draft_id}: {str(e)}"
                    draft_errors.append(error_msg)
                    logging.warning(f"⚠️ {error_msg}")
        
        # Remove opinion from user's opinions array
        opinions.pop(opinion_index)
        
        # Save updated user payload
        save_user_info(email, payload)
        
        logging.info(f"✅ Successfully deleted opinion: {opinion_id}")
        logging.info(f"📊 Cleanup summary: {drafts_deleted} drafts deleted, {len(draft_errors)} errors")
        
        response_data = {
            "success": True,
            "message": f"Opinion '{opinion_to_delete.get('title', 'Untitled')}' deleted successfully",
            "opinion_id": opinion_id,
            "drafts_deleted": drafts_deleted,
            "cleanup_errors": draft_errors if draft_errors else None
        }
        
        return func.HttpResponse(
            body=json.dumps(response_data),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"❌ Error deleting opinion: {str(e)}")
        logging.exception("Delete opinion failed")
        return func.HttpResponse(
            body=json.dumps({
                "error": f"Failed to delete opinion: {str(e)}",
                "success": False
            }),
            mimetype="application/json",
            status_code=500
        )