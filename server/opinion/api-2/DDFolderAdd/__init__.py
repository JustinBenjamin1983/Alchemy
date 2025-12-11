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
        folder_name = data["folder_name"]
        parent_folder_id = data["parent_folder_id"]
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        with transactional_session() as session:
            parent_folder = session.get(Folder, parent_folder_id)
            if not parent_folder:
                logging.info()
                return func.HttpResponse(f"Can't find parent folder {parent_folder_id=}", status_code=404)

            new_folder_id = uuid.uuid4()
            new_folder = Folder(
                id = new_folder_id,
                dd_id=dd_id,
                folder_name=folder_name,
                is_root=False,
                path=f"{parent_folder.path}/{folder_name}",
                hierarchy=f"{parent_folder.hierarchy}/{str(new_folder_id)}"
            )

            session.add(new_folder)
        

        return func.HttpResponse(json.dumps({
            "folder_id": str(new_folder_id),
        }), mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
