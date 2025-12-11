import os
import jwt
import uuid
import json
import logging
import azure.functions as func
from azure.data.tables import TableServiceClient, TableEntity
from azure.core.exceptions import ResourceNotFoundError

def generate_identifier():
    """
    Generates a UUID-based identifier.
    """
    return str(uuid.uuid4())

def auth_get_email(req: func.HttpRequest):
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
    return email, None

def get(email: str):
    table_service = TableServiceClient.from_connection_string(os.environ["TABLE_STORAGE_CONNECTION_STRING"])
    table_client = table_service.get_table_client(table_name=os.environ["TABLE_NAME"])
    try:
        entity = table_client.get_entity(partition_key="UserData", row_key=email)
        entity['clean_payload'] = json.loads(entity['payload'])
        return entity
    except ResourceNotFoundError:
        logging.warning(f"No entity found for email: {email}")
        raise ValueError("No email found")

def save(row_key: str, data: dict, allowed_keys: list, add_to_item: str = None):
    """
    Save data to Azure Table Storage
    
    Args:
        row_key: Email of the user
        data: Data to save
        allowed_keys: List of allowed keys (currently not used but kept for compatibility)
        add_to_item: If specified, adds data to an array within the payload (e.g., "opinions")
    """
    try:
        filtered_data = data  # Keep all data for now
        
        table_service = TableServiceClient.from_connection_string(os.environ["TABLE_STORAGE_CONNECTION_STRING"])
        table_client = table_service.get_table_client(table_name=os.environ["TABLE_NAME"])

        # Create table if it doesn't exist
        try:
            table_client.create_table()
        except Exception:
            pass  # Table already exists
        
        # Prepare entity
        entity = TableEntity()
        
        try:
            # Try to get existing entity
            entity = table_client.get_entity(partition_key="UserData", row_key=str(row_key))
            payload = json.loads(entity["payload"])
            
            if add_to_item:
                # Adding to an array (like opinions)
                if add_to_item not in payload:
                    payload[add_to_item] = []
                
                # Append the new item to the array
                payload[add_to_item].append(filtered_data)
                logging.info(f"Added new {add_to_item} item. Total count: {len(payload[add_to_item])}")
                
                # Save the complete payload structure
                entity["payload"] = json.dumps(payload)
            else:
                # Updating entire payload (used by SaveOpinion)
                logging.info(f"Updating entire payload: {filtered_data}")
                entity["payload"] = json.dumps(filtered_data)
                
        except ResourceNotFoundError:
            # Entity doesn't exist, create new one
            logging.info(f"Creating new entity for {row_key}")
            entity["PartitionKey"] = "UserData"
            entity["RowKey"] = row_key
            
            if add_to_item:
                # Create new payload with the item in an array
                new_payload = {add_to_item: [filtered_data]}
                entity["payload"] = json.dumps(new_payload)
            else:
                # Create new payload with just the data
                entity["payload"] = json.dumps(filtered_data)
        
        # Save entity
        table_client.upsert_entity(entity)
        logging.info(f"Successfully saved data for {row_key}")

    except Exception as e:
        logging.error(f"Error in save function: {str(e)}")
        logging.exception("Error storing JSON data")
        raise e