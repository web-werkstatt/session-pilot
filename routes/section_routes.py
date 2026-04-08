"""
Sprint H: Plan-Sections + Section-Chat API.
"""
from flask import Blueprint, jsonify, request
from services.plan_section_service import (
    create_plan_section,
    list_plan_sections,
    get_plan_section,
    update_plan_section,
    get_or_create_thread,
    create_message,
    list_messages,
    chat_with_section,
)

section_bp = Blueprint("sections", __name__)


# --- Plan-Sections CRUD ---

@section_bp.route("/api/plans/<int:plan_id>/sections")
def api_list_sections(plan_id):
    """Liefert alle Sections eines Plans fuer das Board."""
    try:
        sections = list_plan_sections(plan_id)
    except Exception:
        return jsonify({"sections": []}), 200
    return jsonify({"sections": sections})


@section_bp.route("/api/plans/<int:plan_id>/sections", methods=["POST"])
def api_create_section(plan_id):
    """Erstellt eine neue Section/Spec innerhalb eines Plans."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    title = data.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title ist erforderlich"}), 400

    kind = data.get("kind", "section")
    try:
        result = create_plan_section(
            plan_id=plan_id,
            kind=kind,
            title=title.strip(),
            project_id=data.get("project_id"),
            parent_section_id=data.get("parent_section_id"),
            slug=data.get("slug"),
            summary=data.get("summary"),
            content=data.get("content"),
            status=data.get("status", "backlog"),
            workflow_stage=data.get("workflow_stage", "idea"),
            position=data.get("position"),
            spec_ref=data.get("spec_ref"),
            owner_id=data.get("owner_id"),
            meta=data.get("meta"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(result), 201


@section_bp.route("/api/plan-sections/<int:section_id>", methods=["PUT"])
def api_update_section(section_id):
    """Aktualisiert eine Section (Status, Workflow, Position, etc.)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    try:
        result = update_plan_section(section_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if result is None:
        return jsonify({"error": "Section not found"}), 404
    return jsonify(result)


@section_bp.route("/api/plan-sections/<int:section_id>")
def api_get_section(section_id):
    """Laedt eine einzelne Section."""
    try:
        section = get_plan_section(section_id)
    except Exception:
        return jsonify({"error": "Section not found"}), 404
    if not section:
        return jsonify({"error": "Section not found"}), 404
    return jsonify(section)


# --- Copilot-Threads ---

@section_bp.route("/api/copilot/threads")
def api_get_thread():
    """Liefert den Thread fuer eine Section (erstellt bei Bedarf)."""
    section_id = request.args.get("section_id", type=int)
    if not section_id:
        return jsonify({"error": "section_id ist erforderlich"}), 400

    plan_id = request.args.get("plan_id", type=int) or 0
    project_id = request.args.get("project_id", type=int)

    try:
        result = get_or_create_thread(project_id, plan_id, section_id)
    except Exception:
        result = {"thread_id": None, "project_id": project_id, "plan_id": plan_id, "section_id": section_id}
    return jsonify(result)


# --- Copilot-Messages ---

@section_bp.route("/api/copilot/messages")
def api_list_messages():
    """Liefert Messages eines Threads."""
    thread_id = request.args.get("thread_id", type=int)
    if not thread_id:
        return jsonify({"error": "thread_id ist erforderlich"}), 400

    limit = request.args.get("limit", 50, type=int)
    try:
        msgs = list_messages(thread_id, limit=limit)
    except Exception:
        msgs = []
    return jsonify({"messages": msgs})


# --- Section-Chat (POST /api/copilot/chat erweitern) ---

@section_bp.route("/api/copilot/ai-previews")
def api_ai_previews():
    """Liefert AI-Preview-Daten für mehrere Sections (last message, count)."""
    section_ids_str = request.args.get("section_ids", "")
    if not section_ids_str:
        return jsonify({"previews": {}})

    try:
        section_ids = [int(x) for x in section_ids_str.split(",") if x]
    except ValueError:
        return jsonify({"error": "Ungültige section_ids"}), 400

    from services.plan_section_service import get_section_ai_preview
    previews = {}
    for sid in section_ids:
        preview = get_section_ai_preview(sid)
        if preview:
            previews[sid] = preview

    return jsonify({"previews": previews})


@section_bp.route("/api/copilot/section-chat", methods=["POST"])
def api_section_chat():
    """Chat im Kontext einer Section. Nutzt copilot_threads + copilot_messages."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    message = data.get("message")
    if not message or not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message ist erforderlich"}), 400

    section_id = data.get("section_id")
    if not section_id:
        return jsonify({"error": "section_id ist erforderlich"}), 400

    plan_id = data.get("plan_id")
    if not plan_id:
        return jsonify({"error": "plan_id ist erforderlich"}), 400

    project_id = data.get("project_id")
    thread_id = data.get("thread_id")
    images = data.get("images")

    if images is not None and not isinstance(images, list):
        return jsonify({"error": "images muss eine Liste sein"}), 400

    try:
        result = chat_with_section(
            message=message.strip(),
            project_id=project_id,
            plan_id=plan_id,
            section_id=section_id,
            thread_id=thread_id,
            images=images,
        )
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {e}"}), 500

    status_code = 200 if result.get("status") == "success" else 422
    return jsonify(result), status_code
