# File: server/opinion/api-2/DDStart/__init__.py

import logging
import os
import json
import io
import azure.functions as func
import zipfile
import tempfile
from shared.utils import auth_get_email, generate_identifier, now, send_custom_event_to_eventgrid
from shared.uploader import extract_file, get_file_type, write_to_blob_storage
from shared.table_storage import sanitize_string
from shared.models import DueDiligence, Folder, Document, DocumentHistory
from shared.session import transactional_session
import uuid
import datetime
import requests


FORBIDDEN_FILES = ["__MACOSX", ".DS_Store"]

def write_to_local_storage(key: str, blob: bytes, meta_data: dict = None):
    """Write file to local storage for dev mode."""
    local_storage_path = os.environ.get("LOCAL_STORAGE_PATH", "/tmp/dd_storage")
    os.makedirs(local_storage_path, exist_ok=True)

    # Create subdirectory for extracted docs
    docs_path = os.path.join(local_storage_path, "docs")
    os.makedirs(docs_path, exist_ok=True)

    file_path = os.path.join(docs_path, key)
    with open(file_path, "wb") as f:
        f.write(blob)

    # Save metadata as JSON sidecar file
    if meta_data:
        meta_path = f"{file_path}.meta.json"
        with open(meta_path, "w") as f:
            json.dump(meta_data, f)

    logging.info(f"[DEV MODE] Saved file to {file_path}")
    return file_path
def inject_hierarchy(folders_dict: dict):
    # Step 1: Build a folder name → ID lookup table
    name_to_id = {
        data["folder_name"]: folder_id
        for folder_id, data in folders_dict.items()
        if data["folder_name"] is not None
    }

    for folder_id, folder_data in folders_dict.items():
        path = folder_data.get("path", "")
        path_parts = path.split("/") if path != "." else []

        # Map folder names to GUIDs for the special_path prefix
        special_path_parts = []
        for part in path_parts:
            folder_guid = name_to_id.get(part)
            if not folder_guid:
                raise ValueError(f"No GUID found for folder part '{part}' in path '{path}'")
            special_path_parts.append(folder_guid)
        folder_data["hierarchy"] = "/".join(special_path_parts) if special_path_parts else "" 

    return folders_dict

def get_folder_and_file_structure(root_folder_name: str, folder_path: str, root_path: str):
    """
    Recursively builds a structured dictionary representing folder and file hierarchy.

    Args:
        root_folder_name (str): The top-level folder name (used to suppress root folder duplication).
        folder_path (str): Full path of the current directory.

    Returns:
        dict: Folder structure keyed by unique IDs.
    """
    folders_dict = {}
    uploaded_at = now()
    abs_folder_path = os.path.abspath(folder_path)

    try:
        # Assign a unique ID for the current folder
        current_folder_id = generate_identifier()
        current_folder_name = os.path.basename(abs_folder_path)
        relative_folder_path = os.path.relpath(folder_path, start=root_path)

        folders_dict[current_folder_id] = {
            "folder_name": "root" if current_folder_name == root_folder_name else current_folder_name,
            "is_root": current_folder_name == root_folder_name,
            "path": "." if relative_folder_path == "." else relative_folder_path,
            "items": []
        }

        for entry in sorted(os.listdir(folder_path)):
            entry_path = os.path.join(folder_path, entry)
            
            if any(forbidden_file in entry for forbidden_file in FORBIDDEN_FILES):
                logging.info(f"Skipping forbidden file or folder: {entry_path}")
                continue

            if os.path.isdir(entry_path):
                # Recursively process subfolder
                subfolder_dict = get_folder_and_file_structure(root_folder_name, entry_path, root_path)
                folders_dict.update(subfolder_dict)

            elif os.path.isfile(entry_path):
                file_id = generate_identifier()
                file_type = get_file_type(entry)
                # relative_entry_path = os.path.relpath(entry_path, start=root_path)

                folders_dict[current_folder_id]["items"].append({
                    "type": file_type,
                    "original_file_name": sanitize_string(entry),
                    # "path": relative_entry_path, # not needed
                    "id": file_id,
                    "uploaded_at": uploaded_at,
                    "processing_status": "Not started",
                    "size_in_bytes": 0
                })
        return folders_dict
    except Exception as e:
        logging.error(f"Error accessing {folder_path}: {e}")
        return None
    

def get_all_files(folder_path):
    """
    Recursively gets all files within a directory, including subfolders.
    """
    all_files = []
    
    for root, _, files in os.walk(folder_path):  # Recursively traverse
        for file in files:
            if any(forbidden_file in file for forbidden_file in FORBIDDEN_FILES):
                logging.info(f"found forbidden file in {file}")
                continue
                
            all_files.append(os.path.join(root, file))  # Store full path

    return all_files

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('working')

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        dd_id = uuid.uuid4()
        created_at = now()
        email, err = auth_get_email(req)
        if err:
            return err

        req_body = req.get_json()
        name = req_body.get("name")
        blob_url = req_body.get("blobUrl")

        if not name or not blob_url:
            return func.HttpResponse(
                json.dumps({"error": "name and blobUrl are required"}),
                mimetype="application/json",
                status_code=400
            )

        # Handle local file URLs in dev mode
        if blob_url.startswith("local://"):
            local_path = blob_url.replace("local://", "")
            if not os.path.exists(local_path):
                return func.HttpResponse(
                    json.dumps({"error": f"Local file not found: {local_path}"}),
                    mimetype="application/json",
                    status_code=404
                )
            with open(local_path, "rb") as f:
                uploaded_file_content = f.read()
            safe_filename = os.path.basename(local_path)
        else:
            # Download blob from Azure
            response = requests.get(blob_url)
            if response.status_code != 200:
                return func.HttpResponse(
                    json.dumps({"error": f"Failed to download blob: {response.status_code}"}),
                    mimetype="application/json",
                    status_code=500
                )
            uploaded_file_content = response.content
            safe_filename = os.path.basename(blob_url)

        extension = safe_filename.split('.')[-1].lower()

        
        with transactional_session() as session:
            original_file_doc_id = uuid.uuid4()
            dd = DueDiligence(
                id=dd_id,
                name=name,
                briefing=req_body.get("briefing"),
                owned_by=email,
                original_file_name=safe_filename,
                original_file_doc_id=original_file_doc_id,
                created_at=datetime.datetime.utcnow()
            )
            docs = []

            new_dd: dict = {} # TODO probably can remove
            new_dd["id"] = str(dd_id)
            new_dd["owned_by"] = email
            new_dd["original_file_name"] = safe_filename
            new_dd["original_file_doc_id"] = str(original_file_doc_id)
            new_dd["created_at"] = created_at

            new_dd["name"] = name
            new_dd["briefing"] = req_body.get("briefing")

            event_subject = None
            event_data = None

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_folder_name = os.path.basename(os.path.normpath(tmpdir))
                with zipfile.ZipFile(io.BytesIO(uploaded_file_content), 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                root_folder_path = os.path.abspath(tmpdir)
                structure = get_folder_and_file_structure(
                    root_folder_name=tmp_folder_name, 
                    folder_path=tmpdir,
                    root_path=root_folder_path)
                structure_with_hierarchy = inject_hierarchy(structure)
                logging.info(f"{structure_with_hierarchy=}")
                
                # save original ZIP
                if DEV_MODE:
                    write_to_local_storage(
                        new_dd["original_file_doc_id"],
                        uploaded_file_content,
                        {
                            "original_file_name" : safe_filename,
                            "extension" : extension,
                            "is_dd": "True",
                            "doc_id": new_dd["original_file_doc_id"],
                            "dd_id": new_dd["id"]
                        })
                else:
                    write_to_blob_storage(
                        os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                        os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                        new_dd["original_file_doc_id"],
                        uploaded_file_content,
                        {
                            "original_file_name" : safe_filename,
                            "extension" : extension,
                            "is_dd": "True",
                            "doc_id": new_dd["original_file_doc_id"],
                            "dd_id": new_dd["id"]
                        },
                        overwrite=True)
                db_doc_history = []
                
                original_doc = Document(
                    id=original_file_doc_id,
                    type=extension,
                    original_file_name=safe_filename,
                    uploaded_at=datetime.datetime.utcnow(),
                    processing_status="Not started",
                    size_in_bytes= len(uploaded_file_content),
                    is_original=True
                )
                original_doc.history.append(DocumentHistory(
                    dd_id = dd_id,
                    original_file_name=original_doc.original_file_name,
                    previous_folder=original_doc.folder,
                    current_folder=original_doc.folder,
                    action="Added",
                    by_user=email,
                    action_at=datetime.datetime.utcnow()
                ))
                original_doc_folder = Folder(
                            id = uuid.uuid4(),
                            dd_id=dd_id,
                            folder_name="root",
                            is_root=True,
                            path=".",
                            hierarchy=""
                        )
                original_doc_folder.documents.append(original_doc)
                logging.info("done with save original ZIP")

                is_first_item = True
                for folder_id, folder_data in structure_with_hierarchy.items():
                    dd.folders.append(
                        Folder(
                            id=uuid.UUID(folder_id),
                            folder_name=folder_data['folder_name'],
                            is_root=False,
                            path=folder_data['path'],
                            hierarchy=folder_data['hierarchy']
                        )
                    )
                    for item in folder_data["items"]:
                        file_path = f"{tmpdir}/{folder_data['path']}/{item['original_file_name']}"
                        
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                            item["size_in_bytes"] = len(file_bytes)
                            logging.info("writing to storage")
                            file_metadata = {
                                "original_file_name" : item['original_file_name'],
                                "extension" : item['type'],
                                "is_dd": "True",
                                "doc_id": item['id'],
                                "dd_id": new_dd["id"],
                                "next_chunk_to_process" : "0",
                            }
                            if DEV_MODE:
                                write_to_local_storage(item['id'], file_bytes, file_metadata)
                            else:
                                write_to_blob_storage(
                                    os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                                    os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                                    item['id'],
                                    file_bytes,
                                    file_metadata,
                                    overwrite=True)
                            logging.info("file saved")
                           
                            docs.append(Document(
                                id=uuid.UUID(item['id']),
                                folder_id=uuid.UUID(folder_id),
                                type=item['type'],
                                original_file_name=item['original_file_name'],
                                uploaded_at=datetime.datetime.utcnow(),
                                processing_status="Queued",
                                size_in_bytes=len(file_bytes)
                            ))
                            db_doc_history.append(DocumentHistory(
                                doc_id=uuid.UUID(item['id']),
                                dd_id=dd_id,
                                original_file_name=item['original_file_name'],
                                previous_folder="",
                                current_folder=folder_data['path'],
                                action="Added",
                                by_user=email,
                                action_at=datetime.datetime.utcnow()
                            ))
                            if is_first_item:
                                event_subject = item['id']
                                event_data = {"doc_id": item['id'], "dd_id": new_dd["id"], "email": email}

                        is_first_item = False
                            
                session.add(original_doc_folder)
                session.add(dd)
                session.add_all(docs)
                session.add_all(db_doc_history)
                session.commit()

                # add first doc to queue for processing
                if DEV_MODE:
                    logging.info(f"[DEV MODE] Skipping EventGrid notification. Would send: subject:{event_subject} data:{event_data}")
                else:
                    logging.info(f"send_custom_event_to_eventgrid subject:{event_subject} data {event_data=}")
                    send_custom_event_to_eventgrid(os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_ENDPOINT"],
                            topic_key = os.environ["INDEXING_DD_DOC_METADATA_CHANGED_TOPIC_KEY"],
                            subject = event_subject, # doc_id
                            data = event_data, # {doc_id", "dd_id"}
                            event_type = "AIShop.DD.BlobMetadataUpdated")

                new_dd["files"] = structure_with_hierarchy
                
                logging.info("done")

            return func.HttpResponse(json.dumps({
                "dd_id": str(dd_id),
                "name": name,
                "created_at": created_at
            }), mimetype="application/json", status_code=200)
           

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
