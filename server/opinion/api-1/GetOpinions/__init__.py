
import logging
import azure.functions as func
import os

from shared.utils import auth_get_email, get

import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ GetOpinions function triggered. 2")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email", err)
            return err
        
        logging.info(f"email {email}")

        entity = get(email)
        if not entity:
            return func.HttpResponse(body=json.dumps([]),
                mimetype="application/json", status_code=200)
        
        entity_data = json.loads(entity.get("payload", {}))
        titles_and_ids = [
            {"title": item["title"], "id": item["id"]}
            for item in entity_data.get("opinions", [])
        ]

        return func.HttpResponse(body=json.dumps(titles_and_ids),
            mimetype="application/json", status_code=200)
    
    except Exception as e:
        logging.exception("❌ Error occurred", e)
        return func.HttpResponse("Server error", status_code=500)
    