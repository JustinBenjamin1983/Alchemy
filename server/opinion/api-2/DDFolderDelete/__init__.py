import logging
import os
import json

import azure.functions as func

from shared.utils import auth_get_email
from shared.models import Folder
from shared.session import transactional_session
import uuid

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        data = req.get_json()

        dd_id = data["dd_id"]
        folder_id = data["folder_id"]
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        with transactional_session() as session:
            folder = session.get(Folder, folder_id)
            if not folder:
                return func.HttpResponse(f"Can't find folder {folder_id=}", status_code=404)
            if len(folder.documents) > 0:
                return func.HttpResponse(f"{folder_id=} has documents and can't be deleted", status_code=500)
            
            session.delete(folder)

        return func.HttpResponse("", mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
