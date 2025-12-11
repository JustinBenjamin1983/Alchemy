# shared/blob_storage.py - UPDATED WITH CORRECT CONTAINER NAME

import json
import logging
import os
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError

def get_blob_storage_client():
    """Get blob service client using connection string"""
    connection_string = os.environ.get("BLOB_STORAGE_CONNECTION_STRING") or os.environ.get("USER_TABLE_STORAGE_CONNECTION_STRING")
    return BlobServiceClient.from_connection_string(connection_string)

def save_opinion_draft_to_blob(draft_id: str, draft_data: dict) -> bool:
    """
    Save opinion draft to blob storage as JSON
    
    Args:
        draft_id: Unique identifier for the draft
        draft_data: Dictionary containing draft content and metadata
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert draft data to JSON
        json_content = json.dumps(draft_data, indent=2)
        json_bytes = json_content.encode('utf-8')
        
        # Get blob client
        blob_service_client = get_blob_storage_client()
        container_name = "opiniondrafts"  # UPDATED: Match your container name
        blob_name = f"{draft_id}.json"
        
        # Create container if it doesn't exist (though yours already exists)
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_client.create_container()
            logging.info(f"📦 Created container: {container_name}")
        except Exception:
            pass  # Container already exists
        
        # Upload blob
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        blob_client.upload_blob(
            data=json_bytes,
            overwrite=True,
            content_type="application/json"
        )
        
        logging.info(f"✅ Saved draft to blob storage: {blob_name} ({len(json_bytes)} bytes)")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error saving draft to blob storage: {e}")
        return False

def get_opinion_draft_from_blob(draft_id: str) -> dict:
    """
    Retrieve opinion draft from blob storage
    
    Args:
        draft_id: Unique identifier for the draft
        
    Returns:
        dict: Draft data, or None if not found
    """
    try:
        # Get blob client
        blob_service_client = get_blob_storage_client()
        container_name = "opiniondrafts"  # UPDATED: Match your container name
        blob_name = f"{draft_id}.json"
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Check if blob exists
        if not blob_client.exists():
            logging.warning(f"⚠️ Draft blob not found: {blob_name}")
            return None
        
        # Download blob content
        blob_data = blob_client.download_blob()
        json_bytes = blob_data.readall()
        
        # Parse JSON
        json_string = json_bytes.decode('utf-8')
        draft_data = json.loads(json_string)
        
        logging.info(f"✅ Retrieved draft from blob storage: {blob_name} ({len(json_bytes)} bytes)")
        return draft_data
        
    except ResourceNotFoundError:
        logging.warning(f"⚠️ Draft not found in blob storage: {draft_id}")
        return None
    except Exception as e:
        logging.error(f"❌ Error retrieving draft from blob storage: {e}")
        return None

def delete_opinion_draft_from_blob(draft_id: str) -> bool:
    """
    Delete opinion draft from blob storage
    
    Args:
        draft_id: Unique identifier for the draft
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        blob_service_client = get_blob_storage_client()
        container_name = "opiniondrafts"  # UPDATED: Match your container name
        blob_name = f"{draft_id}.json"
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        if blob_client.exists():
            blob_client.delete_blob()
            logging.info(f"🗑️ Deleted draft from blob storage: {blob_name}")
            return True
        else:
            logging.warning(f"⚠️ Draft not found for deletion: {blob_name}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Error deleting draft from blob storage: {e}")
        return False

# Updated functions for your existing interface
def save_opinion_draft(draft_id: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    """
    UPDATED: Save opinion draft to BLOB storage instead of table storage
    """
    # Ignore the old table storage parameters for now
    return save_opinion_draft_to_blob(draft_id, data)

def get_opinion_draft(draft_id: str):
    """
    UPDATED: Get opinion draft from BLOB storage instead of table storage
    """
    draft_data = get_opinion_draft_from_blob(draft_id)
    
    if draft_data:
        # Mimic the old table storage format for compatibility
        return {
            'clean_payload': draft_data,
            **draft_data  # Include all the draft data directly
        }
    return None

def delete_opinion_draft(draft_id: str):
    """
    NEW: Delete opinion draft from blob storage
    """
    return delete_opinion_draft_from_blob(draft_id)