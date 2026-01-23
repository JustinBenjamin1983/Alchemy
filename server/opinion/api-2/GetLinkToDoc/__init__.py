import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.uploader import get_blob_sas_url

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "")


def main(req: func.HttpRequest) -> func.HttpResponse:

    # Skip function-key check in dev mode
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("no matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        doc_id = req.params.get('doc_id')
        is_dd = req.params.get('is_dd', 'false').lower() == 'true'

        if not doc_id:
            return func.HttpResponse(
                "Missing 'doc_id' query parameter.",
                status_code=400
            )

        logging.info(f"trying to find doc {doc_id} {is_dd=}")

        # In dev mode, try local storage first if blob storage isn't configured
        if DEV_MODE:
            # Check if blob storage connection string is available
            connection_string_key = "DD_DOCS_BLOB_STORAGE_CONNECTION_STRING" if is_dd else "DOCS_BLOB_STORAGE_CONNECTION_STRING"
            connection_string = os.environ.get(connection_string_key, "")

            if not connection_string and LOCAL_STORAGE_PATH:
                # Serve from local storage via a local file endpoint
                # Try docs folder first (where extracted files are stored)
                local_path = os.path.join(LOCAL_STORAGE_PATH, "docs", doc_id)
                if not os.path.exists(local_path):
                    # Also try dd-docs folder
                    local_path = os.path.join(LOCAL_STORAGE_PATH, "dd-docs", doc_id)

                if os.path.exists(local_path):
                    # Return a local file URL that the frontend can use
                    local_url = f"/api/dd-file-serve?doc_id={doc_id}"
                    logging.info(f"Serving local file via: {local_url}")
                    return func.HttpResponse(
                        body=json.dumps({"url": local_url, "local": True}),
                        mimetype="application/json",
                        status_code=200
                    )
                else:
                    logging.warning(f"Local file not found in docs or dd-docs: {doc_id}")

            # If we have a connection string, use blob storage
            if connection_string:
                sas_url = get_blob_sas_url(connection_string, "dd-docs" if is_dd else "docs", doc_id)
                return func.HttpResponse(body=json.dumps({"url": sas_url}), mimetype="application/json", status_code=200)

            # No storage configured
            return func.HttpResponse(
                body=json.dumps({"error": "No storage configured", "message": "Neither blob storage nor local storage is configured"}),
                mimetype="application/json",
                status_code=500
            )

        # Production mode: use blob storage
        connection_string = os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"] if not is_dd else os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"]
        sas_url = get_blob_sas_url(connection_string, "docs", doc_id)

        return func.HttpResponse(body=json.dumps({"url":sas_url}), mimetype="application/json", status_code=200)

    except FileNotFoundError as e:
        logging.error(f"Document not found: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Document not found", "message": str(e)}),
            mimetype="application/json",
            status_code=404
        )
    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(
            body=json.dumps({"error": "Failed to get document link", "message": str(e)}),
            mimetype="application/json",
            status_code=500
        )
