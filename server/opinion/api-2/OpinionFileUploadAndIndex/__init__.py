import logging
import os
import json
import requests
# import tiktoken
import azure.functions as func
from shared.utils import auth_get_email, now, generate_identifier
from shared.uploader import extract_file, write_to_blob_storage, handle_file
from shared.table_storage import save_opinion_settings, save_user_info, get_user_info, sanitize_string

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('working')
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            return err
        
        content_type = req.headers.get("content-type")
        if not content_type or "multipart/form-data" not in content_type.lower():
            return func.HttpResponse("Expected multipart/form-data", status_code=400)
        
        safe_filename, extension, uploaded_file_content = extract_file(req)
        safe_filename = sanitize_string(safe_filename)
        doc_id = generate_identifier()
        logging.info(f"Uploaded file: {safe_filename} {doc_id=}")
        
        write_to_blob_storage(
            os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], 
            os.environ["DOCS_STORAGE_CONTAINER_NAME"], 
            doc_id, 
            uploaded_file_content, 
            {
                "original_file_name" : safe_filename, 
                "extension" : extension
            }, 
            overwrite=True)
        
        was_indexed = handle_file(uploaded_file_content, safe_filename, extension, doc_id)
        
        logging.info(f"{safe_filename=} {was_indexed=}")
        type = req.form.get('type') # save for opinion; save for all
        
        tags = req.form.get('tags', '')
        logging.info(f"{tags=}")
        
        if not was_indexed:
            write_to_blob_storage(
                os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], 
                os.environ["INDEXING_CONTAINER_NAME"], 
                doc_id, 
                uploaded_file_content, 
                {
                    "safe_filename" : safe_filename, 
                    "extension" : extension, 
                    "doc_id" : doc_id, 
                    "save_type" : type, 
                    "opinion_id" : req.form.get('opinion_id', ''), 
                    "user_email" : email, 
                    "next_chunk_to_process" : "0", 
                    "added_at": now(),
                    "tags" : tags
                }, 
                overwrite=True)
        
        if type == "save_for_opinion":
            opinion_id = req.form.get('opinion_id')
            user_info = get_user_info(email)
            clean_payload = user_info.get("clean_payload")
            
            # FIX: Ensure payload has the correct structure
            if clean_payload is None:
                payload = {"opinions": []}
            else:
                payload = clean_payload
                
            # FIX: Ensure opinions array exists
            if "opinions" not in payload or payload["opinions"] is None:
                payload["opinions"] = []
            
            updated = False
            for opinion in payload['opinions']:
                if opinion.get("id") == opinion_id:
                    if "documents" not in opinion:
                        opinion["documents"] = []
                    opinion["documents"].append({
                        "doc_id": doc_id,
                        "doc_name": safe_filename,
                        "enabled": True,
                        "date_added": now(),
                        "added_by": email,
                        "was_indexed" : was_indexed,
                        "tags": tags.split(',') if tags else []
                    })
                    updated = True
                    break
                    
            if not updated:
                raise ValueError(f"No opinion found with ID '{opinion_id}'")
            
            save_user_info(email, payload)
            
        elif type == "save_for_global_opinion":
            settings = {
                "doc_id": doc_id,
                "doc_name": safe_filename,
                "date_added": now(),
                "added_by": email,
                "was_indexed" : was_indexed,
                "tags": tags.split(',') if tags else []
            }
            save_opinion_settings(settings, None, "global_documents")
            
        else:
            return func.HttpResponse(f"Unsupported request of {type}.", status_code=400)
        
        return func.HttpResponse(json.dumps({"doc_id": doc_id, "was_indexed": was_indexed}), mimetype="application/json", status_code=200)
        
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
