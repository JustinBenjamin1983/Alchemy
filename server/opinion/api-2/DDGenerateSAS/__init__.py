import logging
import os
import json
import uuid
import azure.functions as func
from datetime import datetime, timedelta

# Dev mode detection
DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("DDGenerateSAS function triggered")

    # Skip function-key check in dev mode
    if not DEV_MODE:
        if req.headers.get("function-key") != os.environ.get("FUNCTION_KEY"):
            logging.info("Unauthorized request: missing or invalid function key")
            return func.HttpResponse(status_code=401)

    try:
        req_body = req.get_json()
        filename = req_body.get("filename")
        if not filename:
            return func.HttpResponse(
                json.dumps({"error": "filename is required"}),
                mimetype="application/json",
                status_code=400
            )

        if DEV_MODE:
            # In dev mode, use local storage path
            local_storage_path = os.environ.get("LOCAL_STORAGE_PATH", "/tmp/dd_storage")
            os.makedirs(local_storage_path, exist_ok=True)

            # Generate a unique blob name
            blob_name = f"{uuid.uuid4()}_{filename}"
            local_path = os.path.join(local_storage_path, blob_name)

            # Return a local file URL (will be handled by frontend differently in dev)
            return func.HttpResponse(
                json.dumps({
                    "sasUrl": f"local://{local_path}",
                    "blobUrl": f"local://{local_path}",
                    "devMode": True,
                    "localPath": local_path
                }),
                mimetype="application/json",
                status_code=200
            )
        else:
            # Production: Use Azure Blob Storage
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions

            account_name = os.environ["STORAGE_ACCOUNT_NAME"]
            account_key = os.environ["STORAGE_ACCOUNT_KEY"]
            container_name = os.environ["DD_DOCS_STORAGE_CONTAINER_NAME"]

            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=filename,
                account_key=account_key,
                permission=BlobSasPermissions(write=True, create=True, read=True),
                expiry=datetime.utcnow() + timedelta(hours=1)
            )

            blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{filename}"
            sas_url = f"{blob_url}?{sas_token}"

            return func.HttpResponse(
                json.dumps({
                    "sasUrl": sas_url,
                    "blobUrl": blob_url
                }),
                mimetype="application/json",
                status_code=200
            )

    except Exception as e:
        logging.error("Exception occurred", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
