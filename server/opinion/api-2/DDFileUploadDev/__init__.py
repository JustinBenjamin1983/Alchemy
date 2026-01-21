"""
Dev mode file upload endpoint.
Saves uploaded files to local storage for development/testing.
"""

import logging
import os
import json
import re
import azure.functions as func

# Only enable in dev mode
DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


def parse_multipart(body: bytes, content_type: str) -> tuple[bytes | None, str | None, str | None]:
    """
    Manually parse multipart form data since Azure Functions can hang on req.files.
    Returns (file_data, filename, local_path)
    """
    # Extract boundary from content type
    boundary_match = re.search(r'boundary=(.+?)(?:;|$)', content_type)
    if not boundary_match:
        return None, None, None

    boundary = boundary_match.group(1).strip('"')
    boundary_bytes = f'--{boundary}'.encode()

    # Split by boundary
    parts = body.split(boundary_bytes)

    file_data = None
    filename = None
    local_path = None

    for part in parts:
        if not part or part == b'--' or part == b'--\r\n':
            continue

        # Split headers from content
        if b'\r\n\r\n' in part:
            header_section, content = part.split(b'\r\n\r\n', 1)
            headers = header_section.decode('utf-8', errors='ignore')

            # Remove trailing boundary markers from content
            if content.endswith(b'\r\n'):
                content = content[:-2]

            # Check if this is the file field
            if 'name="file"' in headers:
                # Extract filename
                filename_match = re.search(r'filename="([^"]+)"', headers)
                if filename_match:
                    filename = filename_match.group(1)
                file_data = content

            # Check if this is the localPath field
            elif 'name="localPath"' in headers:
                local_path = content.decode('utf-8').strip()

    return file_data, filename, local_path


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("DDFileUploadDev function triggered")

    if not DEV_MODE:
        return func.HttpResponse(
            json.dumps({"error": "This endpoint is only available in dev mode"}),
            mimetype="application/json",
            status_code=403
        )

    try:
        content_type = req.headers.get('Content-Type', '')
        logging.info(f"Content-Type: {content_type}")

        # Get raw body and parse manually (Azure Functions hangs on req.files)
        body = req.get_body()
        logging.info(f"Body size: {len(body)} bytes")

        file_data, filename, local_path = parse_multipart(body, content_type)

        if not file_data:
            return func.HttpResponse(
                json.dumps({"error": "No file uploaded or failed to parse multipart data"}),
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
            f.write(file_data)

        logging.info(f"File saved to {local_path}")

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "localPath": local_path,
                "filename": filename,
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
