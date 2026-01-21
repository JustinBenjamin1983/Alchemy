"""
Dev mode file upload endpoint.
Saves uploaded files to local storage for development/testing.

Uses raw binary PUT request instead of multipart form-data because
Azure Functions Python worker hangs on large multipart bodies.
"""

import logging
import os
import json
import azure.functions as func

# Only enable in dev mode
DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("DDFileUploadDev function triggered")

    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            mimetype="application/json",
            status_code=403
        )

    try:
        # Get localPath from header (avoids multipart parsing issues)
        local_path = req.headers.get("X-Local-Path")
        filename = req.headers.get("X-Filename", "unknown")

        if not local_path:
            return func.HttpResponse(
                json.dumps({"error": "X-Local-Path header is required"}),
                mimetype="application/json",
                status_code=400
            )

        logging.info(f"Receiving file: {filename} -> {local_path}")

        # Get raw body directly (no multipart parsing needed)
        file_data = req.get_body()
        logging.info(f"Body size: {len(file_data)} bytes")

        if not file_data:
            return func.HttpResponse(
                json.dumps({"error": "No file data received"}),
                mimetype="application/json",
                status_code=400
            )

        # Ensure the directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Save the file
        with open(local_path, "wb") as f:
            f.write(file_data)

        logging.info(f"File saved to {local_path} ({len(file_data)} bytes)")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "localPath": local_path,
                "filename": filename,
                "size": len(file_data)
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
