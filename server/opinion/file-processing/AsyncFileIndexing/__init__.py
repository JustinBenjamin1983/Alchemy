import os
import logging
import azure.functions as func
import json

from shared.uploader import handle_file, get_blob_metadata, read_from_blob_storage, set_blob_metadata, delete_from_blob_storage
from shared.table_storage import save_user_info, get_user_info, get_opinions_settings, save_opinion_settings
from shared.utils import send_custom_event_to_eventgrid, now

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.params.get('function-key') != os.environ["FUNCTION_KEY"]:
        return func.HttpResponse("", status_code=401)
       
    try:
        events = req.get_json()

        if isinstance(events, list):
            first_event = events[0]
            event_type = first_event.get("eventType")

            # Handle validation
            if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = first_event["data"]["validationCode"]
                
                return func.HttpResponse(
                    json.dumps({"validationResponse": validation_code}),
                    status_code=200,
                    mimetype="application/json"
                )

            # Handle actual blob-created events
            elif event_type == "Microsoft.Storage.BlobCreated" or event_type == "AIShop.Opinion.BlobMetadataUpdated":
                
                blob_url = first_event["data"]["url"]

                logging.info(f"New blob created: {blob_url}")
                doc_id = blob_url.strip("/").split("/")[-1]
                
                metadata = get_blob_metadata(os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["INDEXING_CONTAINER_NAME"], doc_id)
                
                file_contents = read_from_blob_storage(os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["INDEXING_CONTAINER_NAME"], doc_id)
                next_chunk_to_process = int(metadata["next_chunk_to_process"])
                
                chunk_stop, pages_chunked = handle_file(file_contents, metadata["safe_filename"], metadata["extension"], doc_id, next_chunk_to_process)
                
                logging.info(f"{chunk_stop} {pages_chunked=}")
                if chunk_stop < pages_chunked:
                    metadata["next_chunk_to_process"] = str(chunk_stop)
                    logging.info("more work to do")
                    set_blob_metadata(os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["INDEXING_CONTAINER_NAME"], doc_id, metadata)
                    send_custom_event_to_eventgrid(os.environ["INDEXING_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"], 
                                   topic_key = os.environ["INDEXING_DOC_METADATA_CHANGED_TOPIC_KEY"], 
                                   subject = doc_id, 
                                   data = {"url":f"docs/{doc_id}"}, 
                                   event_type = "AIShop.Opinion.BlobMetadataUpdated")
                    return func.HttpResponse("Processed", status_code=200)
                
                logging.info("DONE WITH CHUNKING")
                
                # TODO 
                delete_from_blob_storage(os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"], os.environ["INDEXING_CONTAINER_NAME"], doc_id)

                if metadata["save_type"] == "save_for_opinion":
                    
                    opinion_id = metadata['opinion_id']
                    doc_id = doc_id
                    user_info = get_user_info(metadata["user_email"])
                    clean_payload = user_info.get("clean_payload")
                    payload = clean_payload if clean_payload else {}
                    updated = False
                    for opinion in payload.get("opinions", []):
                        if opinion.get("id") == opinion_id:
                            for doc in opinion.get("documents", []):
                                if doc.get("doc_id") == doc_id:
                                    doc["enabled"] = not doc.get("enabled", True)
                                    doc["was_indexed"] = True # TODO ?
                                    doc["indexing_finished_at"] = now()
                                    updated = True
                                    break
                            break
                            
                    if not updated:
                        return func.HttpResponse(f"No opinion found with ID '{opinion_id}' or no doc with {doc_id}", status_code=500)
                    
                    save_user_info(metadata["user_email"], payload)
                else: # Global opinion docs

                    opinions_settings = get_opinions_settings()

                    clean_payload = opinions_settings.get("clean_payload")
                    payload = clean_payload if clean_payload else {}
                    payload.setdefault("global_documents", [])
                    
                    for doc in payload["global_documents"]:
                        if doc["doc_id"] == doc_id:
                            doc["was_indexed"] = True
                            doc["indexing_finished_at"] = now()
                            updated = True
                            break
                    
                    save_opinion_settings(payload, None)
                    if not updated:
                        return func.HttpResponse(f"didn't find global doc to update", status_code=500)
                    
                return func.HttpResponse("Processed", status_code=200)

        return func.HttpResponse("Unhandled event", status_code=200) #TODO

    except Exception as e:
        logging.exception("Function failed to process Event Grid event")
        return func.HttpResponse("Error", status_code=500)
