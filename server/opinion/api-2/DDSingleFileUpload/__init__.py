import logging
import os
import json
import azure.functions as func

from shared.utils import auth_get_email, send_custom_event_to_eventgrid
from shared.uploader import extract_file
from shared.table_storage import sanitize_string
from shared.uploader import write_to_blob_storage
from shared.models import Document, DocumentHistory, DueDiligenceMember
from shared.session import transactional_session
import uuid
import datetime

def main(req: func.HttpRequest) -> func.HttpResponse:
    
    if req.headers.get('function-key') != os.environ["FUNCTION_KEY"]:
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)
    
    try:
        user_is_member_of_dd = False
        dd_id = req.form.get("dd_id")
        folder_id = req.form.get("folder_id")
        
        email, err = auth_get_email(req)
        if err:
            return err
        
        content_type = req.headers.get("content-type")
        if not content_type or "multipart/form-data" not in content_type.lower():
            return func.HttpResponse("Expected multipart/form-data", status_code=400)
        
        safe_filename, extension, uploaded_file_content = extract_file(req)
        safe_filename = sanitize_string(safe_filename)

        logging.info(f"uploading {safe_filename} {len(uploaded_file_content)}")
        
        with transactional_session() as session:
            doc_id = uuid.uuid4()
               
            doc = Document(
                id=doc_id,
                type=extension,
                original_file_name=safe_filename,
                uploaded_at=datetime.datetime.utcnow(),
                processing_status="Not started",
                size_in_bytes= len(uploaded_file_content),
                folder_id=folder_id
            )
            doc.history.append(DocumentHistory(
                dd_id = dd_id,
                original_file_name=doc.original_file_name,
                previous_folder=doc.folder,
                current_folder=doc.folder,
                action="Added",
                by_user=email,
                action_at=datetime.datetime.utcnow()
            ))

            logging.info("writing to blob - single file")
            write_to_blob_storage(
                os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"], 
                os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"], 
                str(doc_id), 
                uploaded_file_content, 
                {
                    "original_file_name" : doc.original_file_name, 
                    "extension" : doc.type,
                    "is_dd": "True",
                    "doc_id": str(doc_id),
                    "dd_id": str(dd_id),
                    "next_chunk_to_process" : "0",
                    "single_file": "True"
                },
                overwrite=True)
            member = session.query(DueDiligenceMember).filter(
                    DueDiligenceMember.dd_id == dd_id,
                    DueDiligenceMember.member_email == email
                ).first()
            user_is_member_of_dd = member is not None

            session.add(doc)
            session.commit()

        if user_is_member_of_dd:
            logging.info("send to eventgrid")
            send_custom_event_to_eventgrid(os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                    topic_key = os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                    subject = str(doc_id),
                    data = {"doc_id":str(doc_id), "dd_id": str(dd_id), "email": email},
                    event_type = "AIShop.DD.BlobMetadataUpdated")
        else:
            logging.info(f"user {email} is not member of DD, not starting ProcessRisk")

        logging.info("done")

        return func.HttpResponse(json.dumps({
            "doc_id": str(doc_id),
        }), mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
