# File: server/opinion/api_2/shared/utils.py

import os
import uuid
import jwt
from datetime import datetime, timezone
import logging
import azure.functions as func
import requests
import time
import random

# Dev mode detection
DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"

def send_custom_event_to_eventgrid(topic_endpoint , 
                                   topic_key, 
                                   subject, 
                                   data, 
                                   event_type = "MyApp.BlobMetadataUpdated"):
    """
    Send a custom event to an Azure Event Grid topic.

    :param topic_endpoint: The full URL of the Event Grid topic (e.g. https://mytopic.westeurope-1.eventgrid.azure.net/api/events)
    :param topic_key: The access key for the Event Grid topic
    :param subject: Logical subject of the event (e.g. blob path)
    :param data: A dictionary payload to include in the event
    :param event_type: The custom event type name
    """
    headers = {
        "Content-Type": "application/json",
        "aeg-sas-key": topic_key
    }

    event = {
        "id": generate_identifier(),
        "eventType": event_type,
        "subject": subject,
        "eventTime": now(),
        "data": data,
        "dataVersion": "1.0"
    }

    response = requests.post(topic_endpoint, headers=headers, json=[event])
    response.raise_for_status()
    return response.status_code

def generate_identifier():
    """
    Generates a UUID-based identifier.
    """
    return str(uuid.uuid4())

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def auth_get_email(req: func.HttpRequest):
    # Bypass auth in dev mode
    if DEV_MODE:
        logging.info("Dev mode: bypassing auth, using dev@alchemy.local")
        return "dev@alchemy.local", None

    auth_header = req.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None, func.HttpResponse("Unauthorized", status_code=401)

    token = auth_header[len("Bearer "):]
    decoded_token = jwt.decode(token, options={"verify_signature": False})
    email = (
        decoded_token.get("email")
        or decoded_token.get("preferred_username")
        or (decoded_token.get("emails")[0] if "emails" in decoded_token else None)
        or "Unknown"
    )
    # TODO raise if not valid?

    return email, None



def sleep_random_time(min: int = 1, max: int = 10):
    print(f"Sleeping seconds...")
    time.sleep(random.randint(min, max))
    print("Done sleeping.")