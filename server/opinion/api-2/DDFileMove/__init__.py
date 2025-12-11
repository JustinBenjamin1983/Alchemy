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
        folder_from_id = data["folder_from_id"]
        folder_to_id = data["folder_to_id"]
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        folder_to_path = None
        folder_to_hierarchy = None

        with transactional_session() as session:
            
            folder_from = session.get(Folder, folder_from_id)
            if not folder_from:
                return func.HttpResponse("Cant find folder from", status_code=404)
            folder_to = session.get(Folder, folder_to_id)
            if not folder_to:
                return func.HttpResponse("Cant find folder to", status_code=404)
            
            doc = session.get(Document, doc_id)
            doc.folder_id = folder_to_id
            doc.history.append(DocumentHistory(
                    dd_id = dd_id,
                    original_file_name=doc.original_file_name,
                    previous_folder=folder_from.path,
                    current_folder=folder_to.path,
                    action="Moved",
                    by_user=email,
                    action_at=datetime.datetime.utcnow()
                ))
            session.commit()

            logging.info(f"trying to update_search_index with {doc_id=}, {folder_to.to_dict()}")
            folder_to_path = folder_to.path
            folder_to_hierarchy = folder_to.hierarchy
        
        update_search_index(doc_id, folder_to_path, folder_to_hierarchy, None)

        logging.info("done")

        return func.HttpResponse(json.dumps({
            "doc_id": str(doc_id),
        }), mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
