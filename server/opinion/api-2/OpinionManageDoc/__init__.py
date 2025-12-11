import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.uploader import delete_from_blob_storage
from shared.table_storage import save_opinion_settings, get_opinions_settings, save_user_info, get_user_info
from shared.search import delete_from_search_index

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('working')
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        body = req.get_json()
        type = body['type'] 

        if type == "toggle_doc":
            
            opinion_id = body['opinion_id']
            doc_id = body['doc_id']
            user_info = get_user_info(email)
            clean_payload = user_info.get("clean_payload")
            payload = clean_payload if clean_payload else {}
            updated = False
            for opinion in payload.get("opinions", []):
                if opinion.get("id") == opinion_id:
                    for doc in opinion.get("documents", []):
                        if doc.get("doc_id") == doc_id:
                            doc["enabled"] = not doc.get("enabled", True)
                            updated = True
                            break
                    break
                    
            if not updated:
                raise ValueError(f"No opinion found with ID '{opinion_id}'")
            
            save_user_info(email, payload)
        
            return func.HttpResponse(json.dumps({"doc_id": doc_id}), status_code=200)
        elif type == "toggle_global_docs":
            
            opinion_id = body['opinion_id']
            doc_id = body['doc_id']
            doc_name = body['doc_name'] 
            user_info = get_user_info(email)
            clean_payload = user_info.get("clean_payload")
            payload = clean_payload if clean_payload else {}
            updated = False
            for opinion in payload.get("opinions", []):
                if opinion.get("id") == opinion_id:
                    logging.info(f"got opinion {opinion_id}")
                    for doc in opinion.get("documents", []):
                        if doc.get("doc_id") == doc_id:
                            logging.info(f"got doc {doc_id}")
                            doc["enabled"] = not doc.get("enabled", True)
                            updated = True
                            break
                    if updated:
                        opinion.setdefault("documents", [])
                        opinion["documents"] = [doc for doc in opinion["documents"] if not (not doc["enabled"] and doc.get("is_global", False))] # remove any is_global that are not active
                    else:
                        logging.info(f"no doc but adding")
                        opinion.setdefault("documents", []).append({"doc_id": doc_id, "doc_name": doc_name, "enabled": True, "is_global": True})
                        updated = True
                    break
                    
            if not updated:
                raise ValueError(f"No opinion found with ID '{opinion_id}'")
            
            save_user_info(email, payload)
        
            return func.HttpResponse(json.dumps({"doc_id": doc_id}), status_code=200)
        elif type == "delete_doc": # not global
            # remove doc from user store
            opinion_id = body['opinion_id']
            doc_id = body['doc_id']
            user_info = get_user_info(email)
            clean_payload = user_info.get("clean_payload")
            payload = clean_payload if clean_payload else {}
            is_user_doc_global = False
            for opinion in payload.get("opinions", []):
                if opinion.get("id") == opinion_id:
                    matched_doc = next((doc for doc in opinion["documents"] if doc["doc_id"] == doc_id), None)
                    is_user_doc_global = matched_doc.get("is_global")
                    opinion["documents"] = [doc for doc in opinion["documents"] if not doc["doc_id"] == doc_id]
                    
            save_user_info(email, payload)

            # remove doc from blob storage
            if not is_user_doc_global:
                logging.info("user doc is not global so del from blog, search")
                delete_from_blob_storage(os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], "docs", doc_id)
                # remove doc from Search index
                delete_from_search_index(doc_id)
            else:
                logging.info("user doc IS global so don't del from blog, search")

            return func.HttpResponse('deleted doc from user store', status_code=200)
        elif type == "delete_global_doc":
            # remove doc from global store
            logging.info("delete_global_doc")
           
            opinions_settings = get_opinions_settings()
            doc_id = body['doc_id']
            clean_payload = opinions_settings.get("clean_payload")
            payload = clean_payload if clean_payload else {}
            payload.setdefault("global_documents", [])
            
            payload["global_documents"] = [doc for doc in payload["global_documents"] if not doc["doc_id"] == doc_id]
            # TODO need to check if it's being used
            logging.info(2)
            save_opinion_settings(payload, None)
            # remove doc from blob storage
            logging.info(3)
            delete_from_blob_storage(os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], "docs", doc_id)
            # remove doc from Search index
            logging.info(4)
            delete_from_search_index(doc_id)

            return func.HttpResponse('deleted doc from global store', status_code=200)
        else:
            return func.HttpResponse(f"Unsupported request. {type}", status_code=400)
        
        # else:
        #     settings = {
        #         "id": generate_identifier(),
        #         "test": 1
        #     }
        #     save_opinion_settings(settings, None, "all_settings")
        

        #     return func.HttpResponse("Unsupported file type.", status_code=400)
       
        

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
