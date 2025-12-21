import logging
import os
import json
import azure.functions as func
from shared.utils import auth_get_email
from shared.uploader import get_blob_sas_url

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"


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
        connection_string = os.environ["DOCS_BLOB_STORAGE_CONNECTION_STRING"] if not is_dd else os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"]
        sas_url = get_blob_sas_url(connection_string, "docs", doc_id)

        # return func.HttpResponse(json.dumps({"url":sas_url}), status_code=200)
        return func.HttpResponse(body=json.dumps({"url":sas_url}), mimetype="application/json", status_code=200)

    except Exception as e:
        logging.info(e)
        logging.error(str(e))
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
