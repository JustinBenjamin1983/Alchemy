# Dev Config - Environment configuration for local development
import os
import logging

def is_dev_mode() -> bool:
    """Check if running in local development mode"""
    return os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes", "local")

def get_dev_config() -> dict:
    """Get development configuration"""
    return {
        "dev_mode": is_dev_mode(),
        "firebase_credentials_path": os.environ.get(
            "FIREBASE_CREDENTIALS_PATH",
            "/Users/jbenjamin/Web-Dev-Projects/Alchemy/alchemy-aishop-firebase-adminsdk-fbsvc-4dd93c4c05.json"
        ),
        "firebase_storage_bucket": os.environ.get(
            "FIREBASE_STORAGE_BUCKET",
            "alchemy-aishop.firebasestorage.app"
        ),
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY"),
        "local_storage_path": os.environ.get(
            "LOCAL_STORAGE_PATH",
            "/Users/jbenjamin/Web-Dev-Projects/Alchemy/server/opinion/api-2/.local_storage"
        ),
    }

def log_dev_mode_status():
    """Log whether dev mode is active"""
    if is_dev_mode():
        logging.info("🔧 DEV MODE ACTIVE - Using local/Firebase adapters instead of Azure")
    else:
        logging.info("☁️ PRODUCTION MODE - Using Azure services")
