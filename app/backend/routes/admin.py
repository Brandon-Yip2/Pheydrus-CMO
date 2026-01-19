"""
Admin API routes for the dual-CMO system.

These routes require authentication AND admin privileges (email-based).
Provides endpoints for:
- Index configuration management
- File tree listing
- File upload/delete
- Reindexing triggers
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

from quart import Blueprint, abort, current_app, jsonify, request
from werkzeug.utils import secure_filename

from config import CONFIG_AUTH_CLIENT
from core.authentication import AuthError, is_admin
from core.index_config import (
    IndexConfigError,
    get_allowed_file_types,
    get_folders_for_index,
    get_max_file_size_mb,
    load_index_config,
    save_index_config,
    validate_config,
)

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def get_project_root() -> Path:
    """Get the project root directory (where data/ folder is located)."""
    # This file is in app/backend/routes/, so project root is 3 levels up
    return Path(__file__).parent.parent.parent.parent


def get_config_path() -> Path:
    """Get the path to index_config.json."""
    return get_project_root() / "data" / "index_config.json"


def get_data_root() -> Path:
    """Get the data root directory."""
    return get_project_root() / "data"


_C = TypeVar("_C", bound=Callable[..., Any])


def authenticated_admin(route_fn: _C) -> _C:
    """
    Decorator for admin routes that require both authentication AND admin privileges.
    """

    @wraps(route_fn)
    async def auth_handler(*args, **kwargs):
        auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
        try:
            auth_claims = await auth_helper.get_auth_claims_if_enabled(request.headers)
        except AuthError:
            logger.warning("Admin route access denied: authentication failed")
            abort(403)

        # Check if user is admin
        if not auth_claims:
            logger.warning("Admin route access denied: no auth claims")
            abort(403)

        if not is_admin(auth_claims):
            user_email = auth_claims.get("preferred_username", "unknown")
            logger.warning(f"Admin route access denied: user {user_email} is not an admin")
            abort(403)

        return await route_fn(auth_claims, *args, **kwargs)

    return cast(_C, auth_handler)


# =============================================================================
# Configuration Management Endpoints
# =============================================================================


@admin_bp.route("/config", methods=["GET"])
@authenticated_admin
async def get_config(auth_claims: dict[str, Any]):
    """
    Get the current index configuration.

    Returns:
        JSON object with the full index_config.json contents
    """
    try:
        config_path = get_config_path()
        if not config_path.exists():
            return jsonify({"error": "Configuration file not found"}), 404

        config = load_index_config(str(config_path))
        return jsonify(config)
    except IndexConfigError as e:
        logger.error(f"Error loading config: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception("Unexpected error loading config")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/config", methods=["PUT"])
@authenticated_admin
async def update_config(auth_claims: dict[str, Any]):
    """
    Update the index configuration.

    Expects JSON body with the full or partial configuration.
    Validates the configuration before saving.

    Returns:
        JSON object with success status and the updated configuration
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    try:
        request_json = await request.get_json()
        config_path = get_config_path()

        # Load existing config
        existing_config = {}
        if config_path.exists():
            existing_config = load_index_config(str(config_path))

        # Merge with new config (allow partial updates)
        if "folders" in request_json:
            existing_config["folders"] = request_json["folders"]
        if "indexes" in request_json:
            existing_config["indexes"] = request_json["indexes"]
        if "validation" in request_json:
            existing_config["validation"] = request_json["validation"]
        if "notes" in request_json:
            existing_config["notes"] = request_json["notes"]

        # Update metadata
        existing_config["last_updated"] = datetime.utcnow().isoformat() + "Z"
        existing_config["updated_by"] = auth_claims.get("preferred_username", "admin")

        # Validate the merged config
        errors = validate_config(existing_config)
        if errors:
            return jsonify({"error": "Configuration validation failed", "details": errors}), 400

        # Save the config
        save_index_config(existing_config, str(config_path))

        logger.info(f"Config updated by {auth_claims.get('preferred_username', 'unknown')}")
        return jsonify({"success": True, "config": existing_config})

    except IndexConfigError as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error updating config")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/config/folder/<path:folder_path>", methods=["PUT"])
@authenticated_admin
async def update_folder_assignment(auth_claims: dict[str, Any], folder_path: str):
    """
    Update the index assignment for a specific folder.

    Expects JSON body with:
    - indexes: list of index names (e.g., ["private"], ["public"], ["private", "public"])
    - enabled: boolean (optional)
    - description: string (optional)

    Returns:
        JSON object with success status
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    try:
        request_json = await request.get_json()
        config_path = get_config_path()

        config = load_index_config(str(config_path))

        # Normalize folder path
        folder_path = folder_path.replace("\\", "/")

        # Validate indexes
        indexes = request_json.get("indexes", [])
        valid_indexes = list(config.get("indexes", {}).keys())
        for idx in indexes:
            if idx not in valid_indexes:
                return jsonify({"error": f"Invalid index: {idx}. Valid indexes: {valid_indexes}"}), 400

        # Update or create folder entry
        if "folders" not in config:
            config["folders"] = {}

        config["folders"][folder_path] = {
            "indexes": indexes,
            "enabled": request_json.get("enabled", True),
            "description": request_json.get("description", ""),
        }

        # Update metadata
        config["last_updated"] = datetime.utcnow().isoformat() + "Z"
        config["updated_by"] = auth_claims.get("preferred_username", "admin")

        # Save
        save_index_config(config, str(config_path))

        logger.info(f"Folder {folder_path} assignment updated by {auth_claims.get('preferred_username', 'unknown')}")
        return jsonify({"success": True, "folder": folder_path, "indexes": indexes})

    except Exception as e:
        logger.exception("Error updating folder assignment")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# File Tree Endpoints
# =============================================================================


def build_file_tree(root_path: Path, config: dict) -> dict:
    """
    Build a file tree structure from the data directory.

    Returns a nested dictionary representing the folder structure with
    index assignment information from the config.
    """
    data_root = get_data_root()

    def get_folder_info(rel_path: str) -> dict:
        """Get index assignment info for a folder."""
        folder_config = config.get("folders", {}).get(rel_path, {})
        return {
            "indexes": folder_config.get("indexes", []),
            "enabled": folder_config.get("enabled", False),
            "description": folder_config.get("description", ""),
        }

    def scan_directory(path: Path, rel_prefix: str = "") -> dict:
        """Recursively scan directory and build tree structure."""
        result = {
            "name": path.name,
            "type": "directory",
            "path": rel_prefix + path.name if rel_prefix else path.name,
            "children": [],
        }

        # Add folder assignment info
        folder_rel_path = f"data/{result['path']}" if result["path"] else "data"
        info = get_folder_info(folder_rel_path)
        result["indexes"] = info["indexes"]
        result["enabled"] = info["enabled"]
        result["description"] = info["description"]

        try:
            for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name.startswith("."):
                    continue  # Skip hidden files/folders

                if item.is_dir():
                    child_rel = f"{result['path']}/" if result["path"] else ""
                    child = scan_directory(item, child_rel)
                    result["children"].append(child)
                else:
                    # File
                    file_info = {
                        "name": item.name,
                        "type": "file",
                        "path": f"{result['path']}/{item.name}" if result["path"] else item.name,
                        "size": item.stat().st_size,
                        "extension": item.suffix.lower(),
                    }
                    result["children"].append(file_info)
        except PermissionError:
            logger.warning(f"Permission denied accessing {path}")

        return result

    return scan_directory(root_path)


@admin_bp.route("/files", methods=["GET"])
@authenticated_admin
async def list_files(auth_claims: dict[str, Any]):
    """
    Get the file tree for the data directory.

    Query parameters:
    - path: specific subdirectory to list (optional, defaults to data root)

    Returns:
        JSON object with nested file/folder structure including index assignments
    """
    try:
        config_path = get_config_path()
        config = {}
        if config_path.exists():
            config = load_index_config(str(config_path))

        data_root = get_data_root()

        # Optional: filter to specific subdirectory
        sub_path = request.args.get("path", "")
        if sub_path:
            target_path = data_root / sub_path
            if not target_path.exists() or not target_path.is_dir():
                return jsonify({"error": "Directory not found"}), 404
            if not str(target_path.resolve()).startswith(str(data_root.resolve())):
                return jsonify({"error": "Invalid path"}), 400
        else:
            target_path = data_root

        tree = build_file_tree(target_path, config)
        return jsonify(tree)

    except Exception as e:
        logger.exception("Error listing files")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/files/flat", methods=["GET"])
@authenticated_admin
async def list_files_flat(auth_claims: dict[str, Any]):
    """
    Get a flat list of all folders with their index assignments.

    Returns:
        JSON object with a list of folders and their configurations
    """
    try:
        config_path = get_config_path()
        config = {}
        if config_path.exists():
            config = load_index_config(str(config_path))

        data_root = get_data_root()
        folders = []

        def scan_folders(path: Path, rel_prefix: str = "data"):
            """Recursively scan for folders."""
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    rel_path = f"{rel_prefix}/{item.name}"
                    folder_config = config.get("folders", {}).get(rel_path, {})
                    folders.append({
                        "path": rel_path,
                        "name": item.name,
                        "indexes": folder_config.get("indexes", []),
                        "enabled": folder_config.get("enabled", False),
                        "description": folder_config.get("description", ""),
                    })
                    scan_folders(item, rel_path)

        scan_folders(data_root)
        return jsonify({"folders": folders, "indexes": config.get("indexes", {})})

    except Exception as e:
        logger.exception("Error listing folders flat")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# File Upload/Delete Endpoints
# =============================================================================


@admin_bp.route("/upload", methods=["POST"])
@authenticated_admin
async def upload_file(auth_claims: dict[str, Any]):
    """
    Upload a file to the data directory.

    Expects multipart/form-data with:
    - file: the file to upload
    - path: the target directory path (relative to data root)

    Returns:
        JSON object with success status and file info
    """
    try:
        config_path = get_config_path()
        config = {}
        if config_path.exists():
            config = load_index_config(str(config_path))

        files = await request.files
        form = await request.form

        if "file" not in files:
            return jsonify({"error": "No file provided"}), 400

        file = files["file"]
        target_path = form.get("path", "")

        if not file.filename:
            return jsonify({"error": "No filename provided"}), 400

        # Validate file extension
        allowed_types = get_allowed_file_types(config)
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_types:
            return jsonify({
                "error": f"File type {file_ext} not allowed. Allowed types: {allowed_types}"
            }), 400

        # Validate file size
        max_size_mb = get_max_file_size_mb(config)
        # Read file content to check size
        file_content = file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return jsonify({
                "error": f"File too large ({file_size_mb:.2f} MB). Maximum size: {max_size_mb} MB"
            }), 400

        # Construct safe file path
        safe_filename = secure_filename(file.filename)
        data_root = get_data_root()
        target_dir = data_root / target_path if target_path else data_root

        # Security check: ensure target is within data root
        if not str(target_dir.resolve()).startswith(str(data_root.resolve())):
            return jsonify({"error": "Invalid target path"}), 400

        # Create directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = target_dir / safe_filename
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File uploaded: {file_path} by {auth_claims.get('preferred_username', 'unknown')}")

        return jsonify({
            "success": True,
            "filename": safe_filename,
            "path": str(file_path.relative_to(data_root)),
            "size": len(file_content),
        })

    except Exception as e:
        logger.exception("Error uploading file")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/delete", methods=["POST"])
@authenticated_admin
async def delete_file(auth_claims: dict[str, Any]):
    """
    Delete a file from the data directory.

    Expects JSON body with:
    - path: the file path to delete (relative to data root)

    Returns:
        JSON object with success status
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    try:
        request_json = await request.get_json()
        file_path = request_json.get("path", "")

        if not file_path:
            return jsonify({"error": "No file path provided"}), 400

        data_root = get_data_root()
        full_path = data_root / file_path

        # Security check: ensure path is within data root
        if not str(full_path.resolve()).startswith(str(data_root.resolve())):
            return jsonify({"error": "Invalid file path"}), 400

        if not full_path.exists():
            return jsonify({"error": "File not found"}), 404

        if full_path.is_dir():
            return jsonify({"error": "Cannot delete directories through this endpoint"}), 400

        # Delete the file
        full_path.unlink()

        logger.info(f"File deleted: {file_path} by {auth_claims.get('preferred_username', 'unknown')}")

        return jsonify({"success": True, "path": file_path})

    except Exception as e:
        logger.exception("Error deleting file")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Reindexing Endpoints
# =============================================================================

# Simple in-memory job tracking (in production, use a proper job queue)
_reindex_jobs: dict[str, dict] = {}


@admin_bp.route("/reindex", methods=["POST"])
@authenticated_admin
async def trigger_reindex(auth_claims: dict[str, Any]):
    """
    Trigger a reindexing job.

    Expects JSON body with:
    - index: which index to reindex ("private", "public", or "both")

    Returns:
        JSON object with job ID and status
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    try:
        request_json = await request.get_json()
        index_type = request_json.get("index", "both")

        if index_type not in ["private", "public", "both"]:
            return jsonify({"error": "Invalid index type. Must be 'private', 'public', or 'both'"}), 400

        # Create job ID
        job_id = f"reindex_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{index_type}"

        # Store job info
        _reindex_jobs[job_id] = {
            "id": job_id,
            "index": index_type,
            "status": "pending",
            "started_by": auth_claims.get("preferred_username", "unknown"),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "error": None,
        }

        # Start async reindexing task
        asyncio.create_task(_run_reindex_job(job_id, index_type))

        logger.info(f"Reindex job {job_id} started by {auth_claims.get('preferred_username', 'unknown')}")

        return jsonify({
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": f"Reindexing job started for {index_type} index(es)",
        })

    except Exception as e:
        logger.exception("Error triggering reindex")
        return jsonify({"error": str(e)}), 500


async def _run_reindex_job(job_id: str, index_type: str):
    """
    Run the actual reindexing job asynchronously.

    This is a simplified implementation. In production, you would use
    a proper job queue like Celery or Azure Queue Storage.
    """
    try:
        _reindex_jobs[job_id]["status"] = "running"

        # Import and run the dual prepdocs script
        # Note: This is a simplified approach. In production, you might want to
        # run this as a separate process or use Azure Functions.
        import subprocess
        import sys

        project_root = get_project_root()
        script_path = project_root / "app" / "backend" / "prepdocs_dual.py"

        if not script_path.exists():
            raise FileNotFoundError(f"Prepdocs script not found: {script_path}")

        # Run the script
        cmd = [sys.executable, str(script_path), "--index", index_type, "--verbose"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            _reindex_jobs[job_id]["status"] = "completed"
            _reindex_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
            logger.info(f"Reindex job {job_id} completed successfully")
        else:
            _reindex_jobs[job_id]["status"] = "failed"
            _reindex_jobs[job_id]["error"] = stderr.decode() if stderr else "Unknown error"
            _reindex_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
            logger.error(f"Reindex job {job_id} failed: {stderr.decode() if stderr else 'Unknown error'}")

    except Exception as e:
        _reindex_jobs[job_id]["status"] = "failed"
        _reindex_jobs[job_id]["error"] = str(e)
        _reindex_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
        logger.exception(f"Reindex job {job_id} failed with exception")


@admin_bp.route("/reindex/<job_id>", methods=["GET"])
@authenticated_admin
async def get_reindex_status(auth_claims: dict[str, Any], job_id: str):
    """
    Get the status of a reindexing job.

    Returns:
        JSON object with job status details
    """
    if job_id not in _reindex_jobs:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(_reindex_jobs[job_id])


@admin_bp.route("/reindex", methods=["GET"])
@authenticated_admin
async def list_reindex_jobs(auth_claims: dict[str, Any]):
    """
    List all reindexing jobs.

    Returns:
        JSON object with list of all jobs
    """
    jobs = list(_reindex_jobs.values())
    # Sort by started_at descending
    jobs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return jsonify({"jobs": jobs})


# =============================================================================
# Admin Info Endpoint
# =============================================================================


@admin_bp.route("/info", methods=["GET"])
@authenticated_admin
async def admin_info(auth_claims: dict[str, Any]):
    """
    Get admin user info and system status.

    Returns:
        JSON object with admin info and available indexes
    """
    try:
        config_path = get_config_path()
        config = {}
        if config_path.exists():
            config = load_index_config(str(config_path))

        return jsonify({
            "user": {
                "email": auth_claims.get("preferred_username", "unknown"),
                "name": auth_claims.get("name", ""),
                "is_admin": True,
            },
            "config": {
                "version": config.get("version", "unknown"),
                "last_updated": config.get("last_updated"),
                "updated_by": config.get("updated_by"),
            },
            "indexes": config.get("indexes", {}),
            "validation": config.get("validation", {}),
        })

    except Exception as e:
        logger.exception("Error getting admin info")
        return jsonify({"error": str(e)}), 500
