import logging
import os
import json

import azure.functions as func
from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import DocumentHistory

from sqlalchemy.orm import noload
from sqlalchemy import desc

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        with transactional_session() as session:
            email, err = auth_get_email(req)
            if err:
                return err
            
            dd_id = req.params.get("dd_id")
            logging.info(f"trying to get_docs_history for {dd_id}")
            
            doc_histories = session.query(DocumentHistory).options(noload(DocumentHistory.document)).filter_by(dd_id=dd_id).order_by(desc(DocumentHistory.action_at)).all()

            logging.info("doc_histories")
            logging.info([h.to_dict() for h in doc_histories])
            
            # logging.info(json.dumps([h.to_dict() for h in doc_histories]))

            # docs_history = get_docs_history(dd_id).get("clean_payload")
            # logging.info("got get_docs_history")

            return func.HttpResponse(json.dumps({"history":[h.to_dict() for h in doc_histories]}), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
