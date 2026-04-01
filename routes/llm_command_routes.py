"""
Sprint D: LLM Command Hub Routes.
POST /api/llm/commands/run, GET /api/llm/commands, GET /api/llm/commands/runs.
"""
from flask import Blueprint, jsonify, request, render_template
from routes.api_utils import api_route
from services.llm_command_service import (
    list_commands,
    run_command,
    get_recent_runs,
)

llm_commands_bp = Blueprint("llm_commands", __name__)


@llm_commands_bp.route("/llm-commands")
def llm_commands_page():
    return render_template("llm_commands.html", active_page="llm_commands")


@llm_commands_bp.route("/api/llm/commands")
@api_route
def api_list_commands():
    """Listet alle verfuegbaren Commands."""
    commands = list_commands()
    return jsonify({"commands": commands})


@llm_commands_bp.route("/api/llm/commands/run", methods=["POST"])
def api_run_command():
    """Fuehrt einen Command aus."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request-Body muss JSON sein"}), 400

    command_id = data.get("command_id")
    context = data.get("context", {})
    user_text = data.get("user_text")

    if not command_id or not isinstance(command_id, str):
        return jsonify({"error": "command_id ist erforderlich"}), 400
    if not isinstance(context, dict):
        return jsonify({"error": "context muss ein Objekt sein"}), 400

    try:
        result = run_command(command_id.strip(), context, user_text)
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {str(e)}"}), 500

    status_code = 200 if result.get("status") == "success" else 422
    return jsonify(result), status_code


@llm_commands_bp.route("/api/llm/commands/runs")
@api_route
def api_recent_runs():
    """Listet die letzten Command-Runs."""
    limit = request.args.get("limit", 20, type=int)
    runs = get_recent_runs(min(limit, 100))
    return jsonify({"runs": runs})
