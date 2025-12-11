import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.table_storage import get_user_info, get_opinion_draft

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    logging.info('working')
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        opinion_id = req.params.get('opinion_id')
        draft_id = req.params.get('draft_id')

        email, err = auth_get_email(req)
        if err:
            return err
        
        # safety check
        found = False
        user_info = get_user_info(email)
        clean_payload = user_info.get("clean_payload")
        payload = clean_payload if clean_payload else {}
        logging.info(payload)
        for opinion in payload.get("opinions", []):
                if opinion.get("id") == opinion_id:
                    for draft in opinion.get("drafts", []):
                        if draft.get("draft_id") == draft_id:
                            found = True
        if not found:
            raise ValueError(f"No draft with ID '{draft_id}' found for opinion with ID '{opinion_id}'")
        
        draft = get_opinion_draft(draft_id)

        draft["clean_payload"]["draft_id"] = draft_id
        draft["clean_payload"]["opinion_id"] = opinion_id
        return func.HttpResponse(body=json.dumps(draft["clean_payload"]), mimetype="application/json", status_code=200)
    
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)