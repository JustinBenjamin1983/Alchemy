"""
Configuration and blueprints for DD Enhanced.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


def get_blueprints_dir() -> Path:
    """Get the blueprints directory path."""
    return Path(__file__).parent / "blueprints"


def load_blueprint(name: str) -> Dict[str, Any]:
    """
    Load a DD blueprint by name.

    Args:
        name: Blueprint name (without .yaml extension)

    Returns:
        Blueprint configuration dict
    """
    blueprints_dir = get_blueprints_dir()
    blueprint_path = blueprints_dir / f"{name}.yaml"

    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint not found: {blueprint_path}")

    with open(blueprint_path, "r") as f:
        return yaml.safe_load(f)


def list_blueprints() -> list:
    """List available blueprints."""
    blueprints_dir = get_blueprints_dir()
    return [p.stem for p in blueprints_dir.glob("*.yaml")]


def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables."""
    return {
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY"),
        "default_model": os.environ.get("DD_MODEL", "claude-sonnet-4-20250514"),
        "max_tokens": int(os.environ.get("DD_MAX_TOKENS", "8192")),
        "temperature": float(os.environ.get("DD_TEMPERATURE", "0.1")),
        "verbose": os.environ.get("DD_VERBOSE", "true").lower() == "true",
    }
