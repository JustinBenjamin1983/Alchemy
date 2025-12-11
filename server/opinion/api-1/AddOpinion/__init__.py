
import logging
import azure.functions as func
import json
import os

from shared.utils import auth_get_email, save, generate_identifier

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ AddOpinion function triggered.")
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            logging.exception("❌ auth_get_email", err)
            return err
        logging.info(f"email {email}")

        data = req.get_json()
        id = generate_identifier()
        data["id"] = id
        save(email, data, ["id", "title", "facts", "questions", "assumptions", "client_name", "client_address"], "opinions")
        
        return func.HttpResponse(json.dumps({"id":id}), status_code=200)
    
        
    except Exception as e:
        logging.info(f"failed")
        logging.info(e)
        logging.exception("❌ Error occurred", e)
        return func.HttpResponse("Server error", status_code=500)
    