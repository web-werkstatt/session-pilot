"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Copilot-Chat Routes.
POST /api/copilot/chat, GET /api/copilot/runs.
"""
from flask import Blueprint, jsonify, request, render_template
from services.copilot_service import call_copilot, list_copilot_runs

copilot_bp = Blueprint("copilot", __name__)


@copilot_bp.route("/copilot")
def copilot_page():
    return render_template("copilot.html", active_page="copilot")


@copilot_bp.route("/api/copilot/chat", methods=["POST"])
def api_copilot_chat():
    """Sendet eine Nachricht an den Copilot und speichert die Antwort."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request-Body muss JSON sein"}), 400

    message = data.get("message")
    if not message or not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message ist erforderlich (nicht-leerer String)"}), 400

    project_id = data.get("project_id")
    thread_id = data.get("thread_id")
    context = data.get("context")
    plan_id = data.get("plan_id")

    if context is not None and not isinstance(context, dict):
        return jsonify({"error": "context muss ein Objekt sein oder null"}), 400

    try:
        result = call_copilot(
            message=message.strip(),
            project_id=project_id,
            thread_id=thread_id,
            context=context,
            plan_id=plan_id,
        )
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {str(e)}"}), 500

    status_code = 200 if result.get("status") == "success" else 422
    return jsonify(result), status_code


@copilot_bp.route("/api/copilot/runs")
def api_copilot_runs():
    """Laedt Copilot-Chat-Verlauf."""
    project_id = request.args.get("project_id")
    thread_id = request.args.get("thread_id")
    limit = request.args.get("limit", 50, type=int)

    try:
        runs = list_copilot_runs(
            project_id=project_id,
            thread_id=thread_id,
            limit=limit,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"runs": runs})
