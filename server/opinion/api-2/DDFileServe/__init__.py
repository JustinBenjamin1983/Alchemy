"""
DDFileServe - Serve DD documents from local storage (dev mode only)

This endpoint serves PDF files directly from local storage for the DocumentViewer.
Only available in DEV_MODE with LOCAL_STORAGE_PATH configured.
"""
import logging
import os
import azure.functions as func
from shared.utils import auth_get_email

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "")


def main(req: func.HttpRequest) -> func.HttpResponse:
    # Only available in dev mode
    if not DEV_MODE:
        return func.HttpResponse("Not available in production", status_code=403)

    if not LOCAL_STORAGE_PATH:
        return func.HttpResponse("LOCAL_STORAGE_PATH not configured", status_code=500)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        doc_id = req.params.get('doc_id')
        if not doc_id:
            return func.HttpResponse("Missing 'doc_id' parameter", status_code=400)

        # Try to find the file in dd-docs folder
        local_path = os.path.join(LOCAL_STORAGE_PATH, "dd-docs", doc_id)

        if not os.path.exists(local_path):
            # Also try docs folder
            local_path = os.path.join(LOCAL_STORAGE_PATH, "docs", doc_id)

        if not os.path.exists(local_path):
            logging.warning(f"File not found: {local_path}")
            return func.HttpResponse(f"Document not found: {doc_id}", status_code=404)

        # Read the file
        with open(local_path, 'rb') as f:
            file_content = f.read()

        # Determine content type based on file inspection or default to PDF
        content_type = "application/pdf"
        if file_content[:4] == b'%PDF':
            content_type = "application/pdf"
        elif file_content[:4] == b'PK\x03\x04':
            content_type = "application/zip"

        logging.info(f"Serving local file: {local_path} ({len(file_content)} bytes)")

        return func.HttpResponse(
            body=file_content,
            mimetype=content_type,
            status_code=200,
            headers={
                "Content-Disposition": f'inline; filename="{doc_id}.pdf"',
                "Access-Control-Allow-Origin": "*"
            }
        )

    except Exception as e:
        logging.error(f"Error serving file: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
