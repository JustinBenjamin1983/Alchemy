# Firebase Storage Adapter - Replaces Azure Blob Storage for local dev
import json
import logging
import os
from typing import Optional
from .dev_config import get_dev_config

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, storage

_firebase_initialized = False

def _init_firebase():
    """Initialize Firebase Admin SDK if not already done"""
    global _firebase_initialized
    if _firebase_initialized:
        return

    config = get_dev_config()
    cred_path = config["firebase_credentials_path"]

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credentials not found at: {cred_path}")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': config["firebase_storage_bucket"]
    })
    _firebase_initialized = True
    logging.info("🔥 Firebase initialized for storage")

def get_bucket():
    """Get Firebase Storage bucket"""
    _init_firebase()
    return storage.bucket()

def save_opinion_draft_to_blob(draft_id: str, draft_data: dict) -> bool:
    """
    Save opinion draft to Firebase Storage as JSON

    Args:
        draft_id: Unique identifier for the draft
        draft_data: Dictionary containing draft content and metadata

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        json_content = json.dumps(draft_data, indent=2)
        json_bytes = json_content.encode('utf-8')

        bucket = get_bucket()
        blob_name = f"opiniondrafts/{draft_id}.json"
        blob = bucket.blob(blob_name)

        blob.upload_from_string(
            json_bytes,
            content_type="application/json"
        )

        logging.info(f"✅ [Firebase] Saved draft: {blob_name} ({len(json_bytes)} bytes)")
        return True

    except Exception as e:
        logging.error(f"❌ [Firebase] Error saving draft: {e}")
        return False

def get_opinion_draft_from_blob(draft_id: str) -> Optional[dict]:
    """
    Retrieve opinion draft from Firebase Storage

    Args:
        draft_id: Unique identifier for the draft

    Returns:
        dict: Draft data, or None if not found
    """
    try:
        bucket = get_bucket()
        blob_name = f"opiniondrafts/{draft_id}.json"
        blob = bucket.blob(blob_name)

        if not blob.exists():
            logging.warning(f"⚠️ [Firebase] Draft not found: {blob_name}")
            return None

        json_bytes = blob.download_as_bytes()
        json_string = json_bytes.decode('utf-8')
        draft_data = json.loads(json_string)

        logging.info(f"✅ [Firebase] Retrieved draft: {blob_name} ({len(json_bytes)} bytes)")
        return draft_data

    except Exception as e:
        logging.error(f"❌ [Firebase] Error retrieving draft: {e}")
        return None

def delete_opinion_draft_from_blob(draft_id: str) -> bool:
    """
    Delete opinion draft from Firebase Storage

    Args:
        draft_id: Unique identifier for the draft

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        bucket = get_bucket()
        blob_name = f"opiniondrafts/{draft_id}.json"
        blob = bucket.blob(blob_name)

        if blob.exists():
            blob.delete()
            logging.info(f"🗑️ [Firebase] Deleted draft: {blob_name}")
            return True
        else:
            logging.warning(f"⚠️ [Firebase] Draft not found for deletion: {blob_name}")
            return False

    except Exception as e:
        logging.error(f"❌ [Firebase] Error deleting draft: {e}")
        return False

def upload_file_to_storage(container_name: str, file_name: str, file_data: bytes, content_type: str = None) -> bool:
    """
    Generic file upload to Firebase Storage

    Args:
        container_name: Container/folder name
        file_name: File name
        file_data: File content as bytes
        content_type: MIME type

    Returns:
        bool: True if successful
    """
    try:
        bucket = get_bucket()
        blob_name = f"{container_name}/{file_name}"
        blob = bucket.blob(blob_name)

        blob.upload_from_string(file_data, content_type=content_type)

        logging.info(f"✅ [Firebase] Uploaded: {blob_name}")
        return True

    except Exception as e:
        logging.error(f"❌ [Firebase] Upload error: {e}")
        return False

def download_file_from_storage(container_name: str, file_name: str) -> Optional[bytes]:
    """
    Generic file download from Firebase Storage

    Args:
        container_name: Container/folder name
        file_name: File name

    Returns:
        bytes: File content, or None if not found
    """
    try:
        bucket = get_bucket()
        blob_name = f"{container_name}/{file_name}"
        blob = bucket.blob(blob_name)

        if not blob.exists():
            return None

        return blob.download_as_bytes()

    except Exception as e:
        logging.error(f"❌ [Firebase] Download error: {e}")
        return None

def generate_signed_url(container_name: str, file_name: str, expiration_minutes: int = 60) -> Optional[str]:
    """
    Generate a signed URL for temporary access to a file

    Args:
        container_name: Container/folder name
        file_name: File name
        expiration_minutes: URL expiration time in minutes

    Returns:
        str: Signed URL, or None on error
    """
    try:
        from datetime import timedelta

        bucket = get_bucket()
        blob_name = f"{container_name}/{file_name}"
        blob = bucket.blob(blob_name)

        if not blob.exists():
            return None

        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method='GET'
        )

        return url

    except Exception as e:
        logging.error(f"❌ [Firebase] Signed URL error: {e}")
        return None
