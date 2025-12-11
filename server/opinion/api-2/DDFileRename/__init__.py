import logging
import os
import json

import azure.functions as func

from shared.utils import auth_get_email
from shared.models import Folder, Document, DocumentHistory
from shared.session import transactional_session
from shared.ddsearch import update_search_index
import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        data = req.get_json()

        dd_id = data["dd_id"]
        doc_id = data["doc_id"]
        new_doc_name = data["new_doc_name"]
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        with transactional_session() as session:
            
            doc = session.get(Document, doc_id)
            doc.original_file_name = new_doc_name
            doc.history.append(DocumentHistory(
                    dd_id = dd_id,
                    original_file_name=new_doc_name,
                    previous_folder=doc.folder.path,
                    current_folder=doc.folder.path,
                    action="File Renamed",
                    by_user=email,
                    action_at=datetime.datetime.utcnow()
                ))
            session.commit()

            logging.info(f"trying to update_search_index with {doc_id=}, rename doc to {new_doc_name=}")
            
        update_search_index(doc_id, None, None, new_doc_name)

        logging.info("done")

        return func.HttpResponse(json.dumps({
            "doc_id": str(doc_id),
        }), mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
