"""
Scaffold-Routes: Neue Projekte erstellen via Dashboard
"""
from flask import Blueprint, jsonify, request, render_template
from services.scaffolding_service import (
    get_templates, preview_project, create_project, validate_name
)

scaffold_bp = Blueprint('scaffold', __name__)


@scaffold_bp.route('/scaffold')
def scaffold_page():
    return render_template('scaffold.html', active_page='scaffold')


@scaffold_bp.route('/api/scaffold/templates')
def api_scaffold_templates():
    try:
        return jsonify(get_templates())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@scaffold_bp.route('/api/scaffold/preview', methods=['POST'])
def api_scaffold_preview():
    try:
        config = request.get_json()
        if not config:
            return jsonify({"error": "JSON Body erforderlich"}), 400

        error = validate_name(config.get("name", ""))
        if error:
            return jsonify({"error": error}), 400

        files = preview_project(config)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@scaffold_bp.route('/api/scaffold/create', methods=['POST'])
def api_scaffold_create():
    try:
        config = request.get_json()
        if not config:
            return jsonify({"error": "JSON Body erforderlich"}), 400

        path, log = create_project(config)
        return jsonify({"success": True, "path": path, "log": log, "name": config["name"]})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
