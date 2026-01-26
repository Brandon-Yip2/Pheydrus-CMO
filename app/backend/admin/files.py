"""
Admin API endpoints for managing files in blob storage and triggering indexer runs.

Provides endpoints for:
- Listing files by index (internal/public)
- Uploading files to specific index paths
- Deleting files from blob storage
- Triggering Azure Search indexer runs
"""
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from azure.core.credentials_async import AsyncTokenCredential
from azure.search.documents.indexes.aio import SearchIndexerClient
from azure.storage.blob.aio import BlobServiceClient
from quart import Blueprint, current_app, jsonify, request

from config import CONFIG_CREDENTIAL

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def get_blob_service_client() -> BlobServiceClient:
    """Get the blob service client from environment variables."""
    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT")
    credential: AsyncTokenCredential = current_app.config[CONFIG_CREDENTIAL]
    endpoint = f"https://{storage_account}.blob.core.windows.net"
    return BlobServiceClient(account_url=endpoint, credential=credential)


def get_search_indexer_client() -> SearchIndexerClient:
    """Get the search indexer client from environment variables."""
    search_service = os.environ.get("AZURE_SEARCH_SERVICE")
    credential: AsyncTokenCredential = current_app.config[CONFIG_CREDENTIAL]
    endpoint = f"https://{search_service}.search.windows.net"
    return SearchIndexerClient(endpoint=endpoint, credential=credential)


def load_index_config() -> Optional[dict]:
    """Load the index configuration from index_config.json."""
    # Try multiple locations for the config file
    config_paths = [
        Path(__file__).parent.parent / "index_config.json",
        Path(__file__).parent.parent.parent.parent / "data" / "index_config.json",
        Path("data/index_config.json"),
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load index config from {config_path}: {e}")

    return None


@admin_bp.route("/indexes", methods=["GET"])
async def list_indexes():
    """
    List available indexes and their configuration.

    Returns:
        JSON with index configurations from index_config.json
    """
    config = load_index_config()
    if not config:
        return jsonify({"error": "Index configuration not found"}), 404

    return jsonify({
        "indexes": config.get("indexes", {}),
        "available_folders": config.get("available_folders", []),
    })


@admin_bp.route("/files/<index_key>", methods=["GET"])
async def list_files(index_key: str):
    """
    List all files in blob storage for a specific index.

    Args:
        index_key: The index key (e.g., "internal" or "public")

    Returns:
        JSON with hierarchical folder structure and files
    """
    config = load_index_config()
    if not config:
        return jsonify({"error": "Index configuration not found"}), 404

    if index_key not in config.get("indexes", {}):
        return jsonify({"error": f"Unknown index: {index_key}"}), 400

    container_name = os.environ.get("AZURE_STORAGE_CONTAINER", "content")
    blob_path_prefix = config["indexes"][index_key].get("blob_path_prefix", index_key)

    try:
        blob_service = get_blob_service_client()
        container_client = blob_service.get_container_client(container_name)

        # Build folder structure
        folders: dict[str, Any] = {}
        files_list = []

        async for blob in container_client.list_blobs(name_starts_with=f"{blob_path_prefix}/"):
            # Remove the prefix to get relative path
            relative_path = blob.name[len(blob_path_prefix) + 1:]  # +1 for the /

            # Split into parts
            parts = relative_path.split("/")

            if len(parts) == 1:
                # File directly under prefix
                files_list.append({
                    "name": parts[0],
                    "path": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                })
            else:
                # File in a subfolder
                folder_name = parts[0]
                file_name = "/".join(parts[1:])

                if folder_name not in folders:
                    folders[folder_name] = {"files": [], "subfolders": {}}

                folders[folder_name]["files"].append({
                    "name": file_name,
                    "path": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                })

        await blob_service.close()

        return jsonify({
            "index": index_key,
            "blob_path_prefix": blob_path_prefix,
            "folders": folders,
            "root_files": files_list,
        })

    except Exception as e:
        logger.exception("Error listing files")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/files/<index_key>/<path:folder_path>", methods=["POST"])
async def upload_file(index_key: str, folder_path: str):
    """
    Upload a file to a specific folder in blob storage.

    Args:
        index_key: The index key (e.g., "internal" or "public")
        folder_path: The folder path within the index (e.g., "Artist_s Way")

    Request body:
        Multipart form data with 'file' field

    Returns:
        JSON with upload result
    """
    config = load_index_config()
    if not config:
        return jsonify({"error": "Index configuration not found"}), 404

    if index_key not in config.get("indexes", {}):
        return jsonify({"error": f"Unknown index: {index_key}"}), 400

    # Get uploaded file
    files = await request.files
    if "file" not in files:
        return jsonify({"error": "No file provided"}), 400

    uploaded_file = files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "No filename provided"}), 400

    container_name = os.environ.get("AZURE_STORAGE_CONTAINER", "content")
    blob_path_prefix = config["indexes"][index_key].get("blob_path_prefix", index_key)

    # Build the full blob path: {prefix}/{folder_path}/{filename}
    blob_name = f"{blob_path_prefix}/{folder_path}/{uploaded_file.filename}"

    try:
        blob_service = get_blob_service_client()
        container_client = blob_service.get_container_client(container_name)

        # Read file content
        file_content = await uploaded_file.read()

        # Upload to blob storage
        blob_client = container_client.get_blob_client(blob_name)
        await blob_client.upload_blob(io.BytesIO(file_content), overwrite=True)

        await blob_service.close()

        logger.info(f"Uploaded file to {blob_name}")

        return jsonify({
            "success": True,
            "blob_name": blob_name,
            "message": f"File uploaded successfully. Run indexer to make it searchable.",
        })

    except Exception as e:
        logger.exception("Error uploading file")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/files/<index_key>", methods=["DELETE"])
async def delete_file(index_key: str):
    """
    Delete a file from blob storage.

    Args:
        index_key: The index key (e.g., "internal" or "public")

    Request body:
        JSON with "blob_path" field (full path to blob)

    Returns:
        JSON with deletion result
    """
    config = load_index_config()
    if not config:
        return jsonify({"error": "Index configuration not found"}), 404

    if index_key not in config.get("indexes", {}):
        return jsonify({"error": f"Unknown index: {index_key}"}), 400

    data = await request.get_json()
    if not data or "blob_path" not in data:
        return jsonify({"error": "blob_path is required"}), 400

    blob_path = data["blob_path"]
    blob_path_prefix = config["indexes"][index_key].get("blob_path_prefix", index_key)

    # Security check: ensure the blob path starts with the correct prefix
    if not blob_path.startswith(f"{blob_path_prefix}/"):
        return jsonify({"error": "Invalid blob path for this index"}), 403

    container_name = os.environ.get("AZURE_STORAGE_CONTAINER", "content")

    try:
        blob_service = get_blob_service_client()
        container_client = blob_service.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_path)

        await blob_client.delete_blob()
        await blob_service.close()

        logger.info(f"Deleted blob: {blob_path}")

        return jsonify({
            "success": True,
            "message": f"File deleted. Run indexer to update search index.",
        })

    except Exception as e:
        logger.exception("Error deleting file")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/indexer/<index_key>/run", methods=["POST"])
async def run_indexer(index_key: str):
    """
    Trigger the Azure Search indexer to run for a specific index.

    Args:
        index_key: The index key (e.g., "internal" or "public")

    Returns:
        JSON with indexer run result
    """
    config = load_index_config()
    if not config:
        return jsonify({"error": "Index configuration not found"}), 404

    if index_key not in config.get("indexes", {}):
        return jsonify({"error": f"Unknown index: {index_key}"}), 400

    index_name = config["indexes"][index_key].get("name")
    if not index_name:
        return jsonify({"error": "Index name not configured"}), 500

    # Build the indexer name (follows the naming convention from integratedvectorizerstrategy.py)
    embedding_field = os.environ.get("AZURE_SEARCH_FIELD_NAME_EMBEDDING", "embedding")
    indexer_name = f"{index_name}-{embedding_field}-indexer"

    try:
        indexer_client = get_search_indexer_client()

        # Check if indexer exists
        try:
            indexer = await indexer_client.get_indexer(indexer_name)
            logger.info(f"Found indexer: {indexer.name}")
        except Exception:
            await indexer_client.close()
            return jsonify({"error": f"Indexer '{indexer_name}' not found"}), 404

        # Run the indexer
        await indexer_client.run_indexer(indexer_name)
        await indexer_client.close()

        logger.info(f"Triggered indexer run: {indexer_name}")

        return jsonify({
            "success": True,
            "indexer_name": indexer_name,
            "message": "Indexer run triggered. Check Azure Portal for status.",
        })

    except Exception as e:
        logger.exception("Error running indexer")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/indexer/<index_key>/status", methods=["GET"])
async def get_indexer_status(index_key: str):
    """
    Get the status of the Azure Search indexer for a specific index.

    Args:
        index_key: The index key (e.g., "internal" or "public")

    Returns:
        JSON with indexer status
    """
    config = load_index_config()
    if not config:
        return jsonify({"error": "Index configuration not found"}), 404

    if index_key not in config.get("indexes", {}):
        return jsonify({"error": f"Unknown index: {index_key}"}), 400

    index_name = config["indexes"][index_key].get("name")
    if not index_name:
        return jsonify({"error": "Index name not configured"}), 500

    embedding_field = os.environ.get("AZURE_SEARCH_FIELD_NAME_EMBEDDING", "embedding")
    indexer_name = f"{index_name}-{embedding_field}-indexer"

    try:
        indexer_client = get_search_indexer_client()

        # Get indexer status
        status = await indexer_client.get_indexer_status(indexer_name)
        await indexer_client.close()

        # Extract relevant status info
        last_result = status.last_result
        execution_history = []

        if status.execution_history:
            for execution in status.execution_history[:5]:  # Last 5 executions
                execution_history.append({
                    "status": str(execution.status) if execution.status else None,
                    "start_time": execution.start_time.isoformat() if execution.start_time else None,
                    "end_time": execution.end_time.isoformat() if execution.end_time else None,
                    "items_processed": execution.item_count,
                    "items_failed": execution.failed_item_count,
                    "errors": [str(e) for e in (execution.errors or [])][:3],
                })

        return jsonify({
            "indexer_name": indexer_name,
            "status": str(status.status) if status.status else "unknown",
            "last_result": {
                "status": str(last_result.status) if last_result and last_result.status else None,
                "start_time": last_result.start_time.isoformat() if last_result and last_result.start_time else None,
                "end_time": last_result.end_time.isoformat() if last_result and last_result.end_time else None,
                "items_processed": last_result.item_count if last_result else 0,
                "items_failed": last_result.failed_item_count if last_result else 0,
            } if last_result else None,
            "execution_history": execution_history,
        })

    except Exception as e:
        logger.exception("Error getting indexer status")
        return jsonify({"error": str(e)}), 500
