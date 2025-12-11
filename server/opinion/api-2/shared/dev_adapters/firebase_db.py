# Firebase Firestore Adapter - Replaces Azure Table Storage for local dev
import json
import logging
import os
from typing import Optional, Any
from .dev_config import get_dev_config

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

_firebase_initialized = False
_db = None

def _init_firebase():
    """Initialize Firebase Admin SDK if not already done"""
    global _firebase_initialized, _db
    if _firebase_initialized:
        return _db

    config = get_dev_config()
    cred_path = config["firebase_credentials_path"]

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credentials not found at: {cred_path}")

    # Check if already initialized (might be initialized by storage adapter)
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': config.get("firebase_storage_bucket", "alchemy-aishop.firebasestorage.app")
        })

    _db = firestore.client()
    _firebase_initialized = True
    logging.info("🔥 Firebase Firestore initialized")
    return _db

def get_db():
    """Get Firestore database client"""
    global _db
    if _db is None:
        _init_firebase()
    return _db

# ============== Generic Table Storage Replacement ==============

def get(row_key: str, connection_string: str, table_name: str, partition_key: str) -> dict:
    """
    Get entity from Firestore (replaces Azure Table Storage get)

    Args:
        row_key: Document ID
        connection_string: Ignored (for compatibility)
        table_name: Firestore collection name
        partition_key: Sub-collection or field (stored as metadata)

    Returns:
        dict: Entity data with 'clean_payload' field
    """
    try:
        db = get_db()
        # Use collection/document structure: {table_name}/{partition_key}_{row_key}
        doc_id = f"{partition_key}_{row_key}"
        doc_ref = db.collection(table_name).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            logging.warning(f"[Firestore] No entity found: {table_name}/{doc_id}")
            raise ValueError("No entity found")

        data = doc.to_dict()
        # Parse payload if it exists (for compatibility with Azure Table format)
        if 'payload' in data:
            data['clean_payload'] = json.loads(data['payload'])
        else:
            data['clean_payload'] = data

        logging.info(f"✅ [Firestore] Retrieved: {table_name}/{doc_id}")
        return data

    except ValueError:
        raise
    except Exception as e:
        logging.error(f"❌ [Firestore] Get error: {e}")
        raise ValueError(f"Error retrieving entity: {e}")

def save(row_key: str, data: dict, allowed_keys: list, connection_string: str,
         table_name: str, partition_key: str, add_to_item: str = None):
    """
    Save entity to Firestore (replaces Azure Table Storage save)

    Args:
        row_key: Document ID
        data: Data to save
        allowed_keys: Ignored (for compatibility)
        connection_string: Ignored (for compatibility)
        table_name: Firestore collection name
        partition_key: Sub-collection or field (stored as metadata)
        add_to_item: If set, append data to this array field
    """
    try:
        db = get_db()
        doc_id = f"{partition_key}_{row_key}"
        doc_ref = db.collection(table_name).document(doc_id)

        # Check if document exists
        doc = doc_ref.get()

        if doc.exists and add_to_item:
            # Append to existing array
            existing_data = doc.to_dict()
            payload = json.loads(existing_data.get('payload', '{}'))

            if add_to_item in payload and isinstance(payload[add_to_item], list):
                payload[add_to_item].append(data)
            else:
                payload[add_to_item] = [data]

            doc_ref.set({
                'PartitionKey': partition_key,
                'RowKey': row_key,
                'payload': json.dumps(payload)
            })
        elif add_to_item:
            # Create new with array
            doc_ref.set({
                'PartitionKey': partition_key,
                'RowKey': row_key,
                'payload': json.dumps({add_to_item: [data]})
            })
        else:
            # Simple set
            doc_ref.set({
                'PartitionKey': partition_key,
                'RowKey': row_key,
                'payload': json.dumps(data)
            })

        logging.info(f"✅ [Firestore] Saved: {table_name}/{doc_id}")

    except Exception as e:
        logging.error(f"❌ [Firestore] Save error: {e}")
        raise

# ============== Specific Table Functions (for compatibility) ==============

def get_user_info(email: str) -> dict:
    """Get user info from Firestore"""
    return get(email, "", "users", "user_info")

def save_user_info(row_key: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    """Save user info to Firestore"""
    return save(row_key, data, allowed_keys, "", "users", "user_info", add_to_item)

def get_opinions_settings() -> dict:
    """Get opinions settings from Firestore"""
    try:
        return get("settings", "", "opinions_settings", "settings")
    except ValueError:
        # Return default settings if not found
        return {'clean_payload': {}}

def save_opinion_settings(data: dict, allowed_keys: list = None, add_to_item: str = None):
    """Save opinions settings to Firestore"""
    return save("settings", data, allowed_keys, "", "opinions_settings", "settings", add_to_item)

def get_dds(row_key: str) -> dict:
    """Get due diligence data from Firestore"""
    return get(row_key, "", "due_diligence", "dds")

def save_dds(row_key: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    """Save due diligence data to Firestore"""
    return save(row_key, data, allowed_keys, "", "due_diligence", "dds", add_to_item)

def get_dd_mapping() -> Optional[dict]:
    """Get DD mapping from Firestore"""
    try:
        return get("all", "", "dd_mapping", "dd_mapping")
    except ValueError:
        return None

def save_dd_mapping(data: dict, allowed_keys: list = None, add_to_item: str = None):
    """Save DD mapping to Firestore"""
    return save("all", data, allowed_keys, "", "dd_mapping", "dd_mapping", add_to_item)

def get_docs_history(row_key: str) -> dict:
    """Get docs history from Firestore"""
    return get(row_key, "", "docs_history", "docs_history")

def save_docs_history(row_key: str, data: dict, allowed_keys: list = None, add_to_item: str = None):
    """Save docs history to Firestore"""
    return save(row_key, data, allowed_keys, "", "docs_history", "docs_history", add_to_item)

# ============== Opinion Draft Functions ==============

def get_opinion_draft(draft_id: str) -> Optional[dict]:
    """Get opinion draft from Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection("opinion_drafts").document(draft_id)
        doc = doc_ref.get()

        if not doc.exists:
            logging.warning(f"⚠️ [Firestore] Draft not found: {draft_id}")
            return None

        data = doc.to_dict()
        logging.info(f"✅ [Firestore] Retrieved draft: {draft_id}")
        return data

    except Exception as e:
        logging.error(f"❌ [Firestore] Error getting draft: {e}")
        return None

def save_opinion_draft(draft_id: str, data: dict, allowed_keys: list = None, add_to_item: str = None) -> bool:
    """Save opinion draft to Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection("opinion_drafts").document(draft_id)
        doc_ref.set(data)

        logging.info(f"✅ [Firestore] Saved draft: {draft_id}")
        return True

    except Exception as e:
        logging.error(f"❌ [Firestore] Error saving draft: {e}")
        raise Exception(f"Failed to save draft: {e}")

def delete_opinion_draft(draft_id: str) -> bool:
    """Delete opinion draft from Firestore"""
    try:
        db = get_db()
        doc_ref = db.collection("opinion_drafts").document(draft_id)
        doc_ref.delete()

        logging.info(f"🗑️ [Firestore] Deleted draft: {draft_id}")
        return True

    except Exception as e:
        logging.error(f"❌ [Firestore] Error deleting draft: {e}")
        return False
