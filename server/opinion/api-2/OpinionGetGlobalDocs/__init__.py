import logging
import json
import os
import azure.functions as func
from shared.utils import auth_get_email
from shared.table_storage import get_opinions_settings

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("test 2")
  
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
   
    try:
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        logging.info("got email")
        opinion_settings = get_opinions_settings()
        logging.info("got opinion settings")
        return func.HttpResponse(body=json.dumps({"global_documents":opinion_settings.get("clean_payload", {}).get("global_documents", [])}), mimetype="application/json", status_code=200)
    
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
