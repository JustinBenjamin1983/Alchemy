import logging
import os
import json

import azure.functions as func

from shared.utils import auth_get_email

from shared.rag import create_chunks_and_embeddings_from_text
from shared.ddsearch import search_similar_dd_documents, format_search_results_for_prompt

from shared.session import transactional_session
from shared.models import Folder

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        email, err = auth_get_email(req)
        if err:
            return err
        
        data = req.get_json()

        prompt = data["prompt"]
        dd_id = data["dd_id"]
        keyword_only = data["keyword_only"]
        folder_id = data.get("folder_id", None)
        
        hierarchy = None
        with transactional_session() as session:
           
            if folder_id is not None:
                folder = session.get(Folder, folder_id)
                if folder is None:
                        return func.HttpResponse("Can't find folder", status_code=401)
                hierarchy = folder.hierarchy

        chunks_and_embeddings = create_chunks_and_embeddings_from_text(prompt)

        embeddings = [value for item in chunks_and_embeddings for value in item["embedding"]]
        logging.info(f"searching - using hierarchy {hierarchy}")
        found_results = search_similar_dd_documents(dd_id, hierarchy, None, embeddings, prompt, keyword_only, os.environ["AISearch_K"])
        
        formatted_results = format_search_results_for_prompt(found_results["value"])

        return func.HttpResponse(json.dumps(formatted_results), mimetype="application/json", status_code=200)
    
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
