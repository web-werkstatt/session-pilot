"""
SPEC-PROJECT-MEMORY-001: Read-only Project Memory Endpoint.
"""
from flask import Blueprint, jsonify
from routes.api_utils import api_route
from services.project_memory_service import get_project_memory

project_memory_bp = Blueprint("project_memory", __name__)


@project_memory_bp.route("/api/projects/<path:project_name>/memory")
@api_route
def api_project_memory(project_name):
    """Aggregiertes Project Memory fuer ein Projekt."""
    memory = get_project_memory(project_name)
    if memory is None:
        return jsonify({"error": "project_not_found", "project": project_name}), 404
    return jsonify(memory)
