"""
Dev mode file upload endpoint.
Saves uploaded files to local storage for development/testing.
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
        # Get the uploaded file
        file = req.files.get("file")
        local_path = req.form.get("localPath")

        if not file:
            return func.HttpResponse(
                json.dumps({"error": "No file uploaded"}),
                mimetype="application/json",
                status_code=400
            )

        if not local_path:
            return func.HttpResponse(
                json.dumps({"error": "localPath is required"}),
                mimetype="application/json",
                status_code=400
            )

        # Ensure the directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Save the file
        with open(local_path, "wb") as f:
            f.write(file.read())

        logging.info(f"File saved to {local_path}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "localPath": local_path,
                "filename": file.filename,
                "size": os.path.getsize(local_path)
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
