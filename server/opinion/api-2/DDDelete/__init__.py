import logging
import os
import json
import uuid
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import (
    DueDiligence, DueDiligenceMember, Folder, Document, DocumentHistory,
    Perspective, PerspectiveRisk, PerspectiveRiskFinding,
    DDQuestion, DDQuestionReferencedDoc
)
from shared.session import transactional_session
from shared.uploader import delete_from_blob_storage
from sqlalchemy.orm import joinedload
import requests

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def delete_from_dd_search_index_by_dd_id(dd_id: str):
    """
    Delete all search index entries for a specific due diligence ID.
    """
    logging.info(f"Deleting search index entries for DD: {dd_id}")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    
    # Search for all documents with this dd_id
    search_body = {
        "search": "*",
        "filter": f"dd_id eq '{dd_id}'",
        "select": "id",
        "top": 1000  # TODO: may need to handle paging for very large DDs
    }
    
    search_url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01"
    
    try:
        search_response = requests.post(search_url, headers=headers, json=search_body)
        search_response.raise_for_status()
        
        docs = search_response.json().get("value", [])
        if not docs:
            logging.info(f"No search index documents found for DD: {dd_id}")
            return
        
        # Create delete payload
        delete_payload = {
            "value": [
                {
                    "@search.action": "delete",
                    "id": doc["id"]
                }
                for doc in docs
            ]
        }
        
        # Delete from search index
        index_url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01"
        response = requests.post(index_url, headers=headers, json=delete_payload)
        response.raise_for_status()
        
        logging.info(f"Successfully deleted {len(docs)} search index entries for DD: {dd_id}")
        
    except Exception as e:
        logging.error(f"Failed to delete search index entries for DD {dd_id}: {e}")
        raise


def delete_due_diligence(dd_id: str, requesting_user_email: str):
    """
    Deletes a due diligence and all associated data.

    Args:
        dd_id: UUID of the due diligence to delete
        requesting_user_email: Email of user requesting deletion (for authorization)
    """

    with transactional_session() as session:
        # 1. Verify permissions - user must own the DD (skip in dev mode)
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
        if not dd:
            raise ValueError("Due diligence not found")

        if not DEV_MODE and dd.owned_by != requesting_user_email:
            raise ValueError("Only the owner can delete a due diligence")
        
        logging.info(f"Starting deletion of DD: {dd_id} owned by: {dd.owned_by}")
        
        # 2. Collect all blob keys BEFORE deletion
        blob_keys_to_delete = []
        document_ids = []
        
        # Get original file blob key
        if dd.original_file_doc_id:
            blob_keys_to_delete.append(str(dd.original_file_doc_id))
            logging.info(f"Added original file blob to delete list: {dd.original_file_doc_id}")
        
        # Get all document blob keys
        documents = (session.query(Document)
                    .join(Folder)
                    .filter(Folder.dd_id == dd_id)
                    .all())
        
        for doc in documents:
            document_ids.append(str(doc.id))
            blob_keys_to_delete.append(str(doc.id))
        
        logging.info(f"Found {len(documents)} documents to delete")
        logging.info(f"Total blob keys to delete: {len(blob_keys_to_delete)}")
        
        # 3. Delete records that might have FK constraints not handled by CASCADE
        
        # Delete perspective risk findings first (references both perspective_risk and document)
        perspective_risk_findings = (session.query(PerspectiveRiskFinding)
                                   .join(PerspectiveRisk)
                                   .join(Perspective)
                                   .join(DueDiligenceMember)
                                   .filter(DueDiligenceMember.dd_id == dd_id)
                                   .all())
        
        logging.info(f"Deleting {len(perspective_risk_findings)} perspective risk findings")
        for finding in perspective_risk_findings:
            session.delete(finding)
        
        # Delete DD questions and referenced docs
        dd_questions = session.query(DDQuestion).filter(DDQuestion.dd_id == dd_id).all()
        logging.info(f"Deleting {len(dd_questions)} DD questions")
        
        for question in dd_questions:
            # Delete referenced docs first
            for ref_doc in question.referenced_documents:
                session.delete(ref_doc)
            session.delete(question)
        
        session.flush()  # Ensure FK constraint deletes are committed
        
        # 4. Delete main DueDiligence record (CASCADE will handle the rest)
        logging.info("Deleting main DueDiligence record")
        session.delete(dd)
        session.commit()
        
        logging.info("Database deletion completed successfully")
        
        # 5. Clean up external resources (after DB commit succeeds)

        # Delete from blob storage or local storage
        blob_delete_errors = []
        if DEV_MODE:
            # In dev mode, delete from local storage
            local_storage_path = os.environ.get(
                "LOCAL_STORAGE_PATH",
                "/Users/jbenjamin/Web-Dev-Projects/Alchemy/server/opinion/api-2/.local_storage"
            )
            docs_path = os.path.join(local_storage_path, "docs")
            for blob_key in blob_keys_to_delete:
                try:
                    file_path = os.path.join(docs_path, blob_key)
                    meta_path = f"{file_path}.meta.json"
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logging.info(f"Deleted local file: {file_path}")
                    if os.path.exists(meta_path):
                        os.remove(meta_path)
                        logging.info(f"Deleted local meta file: {meta_path}")
                except Exception as e:
                    error_msg = f"Failed to delete local file {blob_key}: {e}"
                    logging.error(error_msg)
                    blob_delete_errors.append(error_msg)
        else:
            for blob_key in blob_keys_to_delete:
                try:
                    delete_from_blob_storage(
                        os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                        os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                        blob_key
                    )
                    logging.info(f"Deleted blob: {blob_key}")
                except Exception as e:
                    error_msg = f"Failed to delete blob {blob_key}: {e}"
                    logging.error(error_msg)
                    blob_delete_errors.append(error_msg)
                    # Continue with other deletions even if one fails

        # 6. Clean up search index (skip in dev mode as we use local search)
        if DEV_MODE:
            # Clean up local search index
            try:
                from shared.dev_adapters.local_search import clear_index
                clear_index(f"dd_{dd_id}")
                logging.info(f"Removed local search index for DD {dd_id}")
            except Exception as e:
                logging.warning(f"Failed to remove local search index for DD {dd_id}: {e}")
        else:
            try:
                delete_from_dd_search_index_by_dd_id(dd_id)
                logging.info(f"Removed DD {dd_id} from search index")
            except Exception as e:
                error_msg = f"Failed to remove DD {dd_id} from search index: {e}"
                logging.error(error_msg)
                # Don't fail the whole operation for search index errors
        
        # 7. Clean up any table storage entries (if applicable)
        try:
            # Based on your table_storage.py, there doesn't seem to be DD-specific data
            # but if there is, clean it here
            # clean_dd_table_storage(dd_id)
            pass
        except Exception as e:
            logging.error(f"Failed to clean table storage for DD {dd_id}: {e}")
        
        success_msg = f"Successfully deleted due diligence {dd_id}"
        if blob_delete_errors:
            success_msg += f" (with {len(blob_delete_errors)} blob deletion errors)"
        
        logging.info(success_msg)
        
        return {
            "success": True,
            "message": success_msg,
            "deleted_documents": len(documents),
            "deleted_blobs": len(blob_keys_to_delete) - len(blob_delete_errors),
            "blob_errors": blob_delete_errors
        }


def main(req: func.HttpRequest) -> func.HttpResponse:
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("Invalid function key provided")
        return func.HttpResponse("", status_code=401)

    try:
        # Authenticate user - in dev mode use a mock email
        if DEV_MODE:
            email = "dev@localhost"
            logging.info(f"[DEV MODE] Using mock email: {email}")
        else:
            email, err = auth_get_email(req)
            if err:
                return err

        req_body = req.get_json()
        dd_id_str = req_body.get("dd_id")
        
        if not dd_id_str:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                mimetype="application/json",
                status_code=400
            )
        
        # Validate UUID format
        try:
            dd_id = uuid.UUID(dd_id_str)
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid dd_id format"}),
                mimetype="application/json",
                status_code=400
            )
        
        logging.info(f"Delete request for DD {dd_id} by user {email}")
        
        # Perform deletion
        result = delete_due_diligence(str(dd_id), email)
        
        return func.HttpResponse(
            json.dumps({
                "message": "Due diligence deleted successfully",
                "details": result
            }),
            mimetype="application/json",
            status_code=200
        )
        
    except ValueError as e:
        logging.warning(f"Validation error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error deleting due diligence: {str(e)}")
        logging.exception("Full exception details")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )