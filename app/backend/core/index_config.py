"""
Configuration loader for dual-index CMO system.
Loads and validates the index_config.json file that maps folders to search indexes.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default config path (relative to project root)
DEFAULT_CONFIG_PATH = "data/index_config.json"


class IndexConfigError(Exception):
    """Raised when there's an error with the index configuration."""

    pass


def get_config_path() -> Path:
    """Get the path to the index config file."""
    # Try environment variable first
    config_path = os.getenv("INDEX_CONFIG_PATH")
    if config_path:
        return Path(config_path)

    # Otherwise use default path relative to project root
    # Navigate from app/backend/core to project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent
    return project_root / DEFAULT_CONFIG_PATH


def load_index_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load the index configuration file.

    Args:
        config_path: Optional path to config file. Uses default if not specified.

    Returns:
        Dict containing the configuration.

    Raises:
        IndexConfigError: If config file cannot be loaded or is invalid.
    """
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"Index config file not found at {config_path}, using defaults")
        return get_default_config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"Loaded index config from {config_path}")
        return config
    except json.JSONDecodeError as e:
        raise IndexConfigError(f"Invalid JSON in config file: {e}") from e
    except Exception as e:
        raise IndexConfigError(f"Failed to load config file: {e}") from e


def save_index_config(
    config: dict[str, Any],
    user_email: str | None = None,
    config_path: str | Path | None = None,
) -> None:
    """
    Save the index configuration file.

    Args:
        config: The configuration dict to save.
        user_email: Email of user making the change (for audit).
        config_path: Optional path to config file. Uses default if not specified.
    """
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)

    # Update metadata
    config["last_updated"] = datetime.now().isoformat()
    if user_email:
        config["updated_by"] = user_email

    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    logger.info(f"Saved index config to {config_path}")


def get_default_config() -> dict[str, Any]:
    """Return default configuration if no config file exists."""
    return {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "updated_by": "system",
        "folders": {},
        "indexes": {
            "private": {
                "name": os.getenv("AZURE_SEARCH_INDEX_INTERNAL", "gptkbindex-internal"),
                "description": "Private CMO - full data access",
            },
            "public": {
                "name": os.getenv("AZURE_SEARCH_INDEX_PUBLIC", "gptkbindex-public"),
                "description": "Public CMO - curated subset",
            },
        },
        "validation": {"allowed_file_types": [".pdf", ".docx", ".txt"], "max_file_size_mb": 100},
    }


def get_folders_for_index(config: dict[str, Any], index_type: str) -> list[str]:
    """
    Get list of folder paths that should be included in the specified index.

    Args:
        config: The loaded configuration.
        index_type: Either "private" or "public".

    Returns:
        List of folder paths.
    """
    folders = []
    for folder_path, folder_config in config.get("folders", {}).items():
        if not folder_config.get("enabled", True):
            continue
        if index_type in folder_config.get("indexes", []):
            folders.append(folder_path)
    return folders


def get_index_name(config: dict[str, Any], index_type: str) -> str:
    """
    Get the Azure Search index name for the specified index type.

    Args:
        config: The loaded configuration.
        index_type: Either "private" or "public".

    Returns:
        The Azure Search index name.
    """
    indexes = config.get("indexes", {})
    index_config = indexes.get(index_type, {})

    # Fall back to environment variables if not in config
    if index_type == "private":
        return index_config.get("name", os.getenv("AZURE_SEARCH_INDEX_INTERNAL", "gptkbindex-internal"))
    else:
        return index_config.get("name", os.getenv("AZURE_SEARCH_INDEX_PUBLIC", "gptkbindex-public"))


def validate_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate the configuration structure and content.

    Args:
        config: The configuration to validate.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors = []

    # Check required top-level fields
    if "version" not in config:
        errors.append("Missing 'version' field")

    if "indexes" not in config:
        errors.append("Missing 'indexes' field")
    else:
        # Validate index definitions
        if "private" not in config["indexes"]:
            errors.append("Missing 'private' index definition")
        if "public" not in config["indexes"]:
            errors.append("Missing 'public' index definition")

        for index_type, index_config in config["indexes"].items():
            if "name" not in index_config:
                errors.append(f"Missing 'name' for index '{index_type}'")

    # Validate folders (if present)
    valid_index_types = {"private", "public"}
    for folder_path, folder_config in config.get("folders", {}).items():
        # Check folder exists (warning, not error)
        if not Path(folder_path).exists():
            logger.warning(f"Folder does not exist: {folder_path}")

        # Check indexes field
        if "indexes" not in folder_config:
            errors.append(f"Missing 'indexes' for folder '{folder_path}'")
            continue

        # Check valid index types
        for idx in folder_config["indexes"]:
            if idx not in valid_index_types:
                errors.append(f"Invalid index type '{idx}' for folder '{folder_path}'")

    # Validate file type restrictions (if present)
    validation = config.get("validation", {})
    allowed_types = validation.get("allowed_file_types", [])
    for file_type in allowed_types:
        if not file_type.startswith("."):
            errors.append(f"File type should start with '.': {file_type}")

    return len(errors) == 0, errors


def get_allowed_file_types(config: dict[str, Any]) -> list[str]:
    """Get list of allowed file extensions for upload."""
    validation = config.get("validation", {})
    return validation.get("allowed_file_types", [".pdf", ".docx", ".txt"])


def get_max_file_size_mb(config: dict[str, Any]) -> int:
    """Get maximum file size in MB for upload."""
    validation = config.get("validation", {})
    return validation.get("max_file_size_mb", 100)
