# DDDeleteDocument/__init__.py
"""
Delete individual document(s) from a DD project.

POST /api/dd-delete-document
{
    "dd_id": "uuid",
    "document_ids": ["uuid1", "uuid2", ...]
}

Returns:
{
    "success": true,
    "deleted_count": 2
}
"""
import logging
import os
import json
import uuid
import azure.functions as func
from shared.utils import auth_get_email
from shared.models import Document, Folder, DueDiligence
from shared.session import transactional_session
from shared.uploader import delete_from_blob_storage

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def delete_documents(dd_id: str, document_ids: list[str], requesting_user_email: str) -> dict:
    """
    Delete specific documents from a DD project.

    Args:
        dd_id: UUID of the due diligence project
        document_ids: List of document UUIDs to delete
        requesting_user_email: Email of user requesting deletion

    Returns:
        Dict with deletion results
    """
    deleted_count = 0
    errors = []

    # Convert dd_id to UUID
    dd_uuid = uuid.UUID(dd_id) if isinstance(dd_id, str) else dd_id

    with transactional_session() as session:
        # Verify DD exists and user has access
        dd = session.query(DueDiligence).filter(DueDiligence.id == dd_uuid).first()
        if not dd:
            raise ValueError("Due diligence not found")

        if not DEV_MODE and dd.owned_by != requesting_user_email:
            raise ValueError("Access denied")

        # Get folder IDs for this DD
        folder_ids = [f.id for f in session.query(Folder).filter(Folder.dd_id == dd_uuid).all()]

        for doc_id_str in document_ids:
            try:
                doc_uuid = uuid.UUID(doc_id_str)

                # Find the document
                doc = session.query(Document).filter(
                    Document.id == doc_uuid,
                    Document.folder_id.in_(folder_ids)
                ).first()

                if not doc:
                    errors.append(f"Document {doc_id_str} not found")
                    continue

                # Don't delete the original ZIP file
                if doc.is_original:
                    errors.append(f"Cannot delete original file {doc_id_str}")
                    continue

                blob_key = str(doc.id)

                # Delete from database
                session.delete(doc)
                session.flush()

                # Delete from storage
                if DEV_MODE:
                    local_storage_path = os.environ.get(
                        "LOCAL_STORAGE_PATH",
                        "/Users/jbenjamin/Web-Dev-Projects/Alchemy/server/opinion/api-2/.local_storage"
                    )
                    docs_path = os.path.join(local_storage_path, "docs")
                    file_path = os.path.join(docs_path, blob_key)
                    meta_path = f"{file_path}.meta.json"

                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if os.path.exists(meta_path):
                        os.remove(meta_path)
                else:
                    try:
                        delete_from_blob_storage(
                            os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
                            os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"],
                            blob_key
                        )
                    except Exception as e:
                        logging.warning(f"Failed to delete blob {blob_key}: {e}")

                deleted_count += 1
                logging.info(f"Deleted document {doc_id_str}")

            except Exception as e:
                errors.append(f"Error deleting {doc_id_str}: {str(e)}")
                logging.error(f"Error deleting document {doc_id_str}: {e}")

        session.commit()

    return {
        "success": deleted_count > 0,
        "deleted_count": deleted_count,
        "errors": errors if errors else None
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        return func.HttpResponse("", status_code=401)

    try:
        # Auth
        if DEV_MODE:
            email = "dev@localhost"
        else:
            email, err = auth_get_email(req)
            if err:
                return err

        req_body = req.get_json()
        dd_id = req_body.get("dd_id")
        document_ids = req_body.get("document_ids", [])

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                mimetype="application/json",
                status_code=400
            )

        if not document_ids:
            return func.HttpResponse(
                json.dumps({"error": "document_ids is required"}),
                mimetype="application/json",
                status_code=400
            )

        result = delete_documents(dd_id, document_ids, email)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error deleting documents: {e}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )
