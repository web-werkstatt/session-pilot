"""
Scaffold-Routes: Neue Projekte erstellen via Dashboard
"""
from flask import Blueprint, jsonify, request, render_template
from services.scaffolding_service import (
    get_templates, preview_project, create_project, validate_name
)
from routes.api_utils import api_route

scaffold_bp = Blueprint('scaffold', __name__)


@scaffold_bp.route('/scaffold')
def scaffold_page():
    return render_template('scaffold.html', active_page='scaffold')


@scaffold_bp.route('/api/scaffold/templates')
@api_route
def api_scaffold_templates():
    return jsonify(get_templates())


@scaffold_bp.route('/api/scaffold/preview', methods=['POST'])
@api_route
def api_scaffold_preview():
    config = request.get_json()
    if not config:
        return jsonify({"error": "JSON Body erforderlich"}), 400

    error = validate_name(config.get("name", ""))
    if error:
        return jsonify({"error": error}), 400

    files = preview_project(config)
    return jsonify({"files": files})


@scaffold_bp.route('/api/scaffold/create', methods=['POST'])
@api_route
def api_scaffold_create():
    config = request.get_json()
    if not config:
        return jsonify({"error": "JSON Body erforderlich"}), 400

    try:
        path, log = create_project(config)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"success": True, "path": path, "log": log, "name": config["name"]})
