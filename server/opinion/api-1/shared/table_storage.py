# shared/table_storage.py - UPDATED TO USE BLOB STORAGE FOR DRAFTS
import uuid
import json
import os
import logging
import re

from azure.data.tables import TableServiceClient, TableEntity
from azure.core.exceptions import ResourceNotFoundError

# Import the new blob storage functions
from .blob_storage import save_opinion_draft_to_blob, get_opinion_draft_from_blob, delete_opinion_draft_from_blob

def generate_identifier():
    """
    Generates a UUID-based identifier.
    """
    return str(uuid.uuid4())

def sanitize_string(value: str) -> str:
    """
    Removes non-ASCII printable characters from a string.
    This is safe for use in Azure Blob Storage metadata.

    Args:
        value (str): The input string

    Returns:
        str: Cleaned string with only ASCII printable characters
    """
    return re.sub(r"[^\x20-\x7E]", "", value)

def get(email: str, connection_string: str, table_name: str, partition_key: str):
    table_service = TableServiceClient.from_connection_string(connection_string)
    table_client = table_service.get_table_client(table_name=table_name)

    try:
        entity = table_client.get_entity(partition_key=partition_key, row_key=email)
        entity['clean_payload'] = json.loads(entity['payload'])

        return entity
    except ResourceNotFoundError:
        logging.warning(f"No entity found for key: {email} {table_name=} {partition_key=}")
        raise ValueError("No email found")

def save(row_key: str, data: dict, allowed_keys: list, connection_string: str, table_name: str, partition_key: str, add_to_item: str = None):
    # TODO: check if payload is str or obj
    try:
        filtered_data = data # TODO {k: v for k, v in data.items() if k in allowed_keys}
        # email = filtered_data.pop("email", None)
        logging.info("filtered_data")
        logging.info(filtered_data)
        # if not email:
        #     logging.exception("No email found")
        #     raise ValueError("No email found")

        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client(table_name=table_name)

        # Create table if it doesn't exist
        try:
            table_client.create_table()
        except Exception:
            pass  # Table already exists
        
        # Prepare entity
        entity = TableEntity()
        try:
            entity = table_client.get_entity(partition_key=partition_key, row_key=str(row_key))
            payload = json.loads(entity["payload"])
            
            if add_to_item:
                logging.info("payload")
                logging.info(payload)
                logging.info(add_to_item)
                if add_to_item in payload and isinstance(payload[add_to_item], list):
                    logging.info("payload[add_to_item]")
                    logging.info(payload[add_to_item])
                    #payload[add_to_item] = payload[add_to_item] + filtered_data
                    logging.info("filtered_data")
                    logging.info(filtered_data)
                    payload[add_to_item].append(filtered_data)
                    logging.info("adding")
                    entity["payload"] = json.dumps(payload)
                else:
                    entity["payload"] = json.dumps([filtered_data])
            else:
                # logging.info(f" save - saving to payload {filtered_data}")
                entity["payload"] = json.dumps(filtered_data)
        except Exception as e:
            logging.info(e)
            entity["PartitionKey"] = partition_key
            entity["RowKey"] = row_key
            if add_to_item:
                entity["payload"] = json.dumps({add_to_item:[filtered_data]})
            else:
                entity["payload"] = json.dumps(filtered_data)
        
        # Save entity
        table_client.upsert_entity(entity)

        # logging.info("done with save")

    except Exception as e:
        logging.info(e)
        logging.exception("Error storing JSON data")

# UPDATED FUNCTIONS FOR OPINION DRAFTS - NOW USE BLOB STORAGE
def get_opinion_draft(draft_id: str):
    """
    UPDATED: Get opinion draft from BLOB storage instead of table storage
    """
    logging.info(f"📦 Retrieving draft from blob storage: {draft_id}")
    
    draft_data = get_opinion_draft_from_blob(draft_id)
    
    if draft_data:
        logging.info(f"✅ Successfully retrieved draft from blob storage")
        # Return in the expected format for compatibility
        return draft_data
    else:
        logging.warning(f"⚠️ Draft not found in blob storage: {draft_id}")
        return None

def save_opinion_draft(draft_id: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    """
    UPDATED: Save opinion draft to BLOB storage instead of table storage
    """
    logging.info(f"📦 Saving draft to blob storage: {draft_id}")
    logging.info(f"📊 Draft size: {len(json.dumps(data))} bytes")
    
    success = save_opinion_draft_to_blob(draft_id, data)
    
    if success:
        logging.info(f"✅ Successfully saved draft to blob storage")
    else:
        logging.error(f"❌ Failed to save draft to blob storage")
        raise Exception("Failed to save draft to blob storage")
    
    return success

def delete_opinion_draft(draft_id: str):
    """
    NEW: Delete opinion draft from blob storage
    """
    logging.info(f"🗑️ Deleting draft from blob storage: {draft_id}")
    return delete_opinion_draft_from_blob(draft_id)

# EXISTING FUNCTIONS REMAIN THE SAME (for user data, settings, etc.)
def get_user_info(email: str):
    return get(email, os.environ["USER_TABLE_STORAGE_CONNECTION_STRING"], os.environ["USER_TABLE_NAME"], os.environ["USER_TABLE_PARTITION_KEY"])

def save_user_info(row_key: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    return save(row_key, data, allowed_keys, os.environ["USER_TABLE_STORAGE_CONNECTION_STRING"], os.environ["USER_TABLE_NAME"], os.environ["USER_TABLE_PARTITION_KEY"], add_to_item)

def get_opinions_settings():
    temp = get("settings", os.environ["OPINIONS_SETTINGS_TABLE_STORAGE_CONNECTION_STRING"], os.environ["OPINIONS_SETTINGS_TABLE_NAME"], os.environ["OPINIONS_SETTINGS_PARTITION_KEY"])
    logging.info(f"get_opinions_settings: {temp=}")
    return temp

def save_opinion_settings(data: dict, allowed_keys: list, add_to_item: str = None):
    return save("settings", data, allowed_keys, os.environ["OPINIONS_SETTINGS_TABLE_STORAGE_CONNECTION_STRING"], os.environ["OPINIONS_SETTINGS_TABLE_NAME"], os.environ["OPINIONS_SETTINGS_PARTITION_KEY"], add_to_item)