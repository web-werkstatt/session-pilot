"""
Marker- und Sprint-Import-Routen fuer Copilot.
"""
from flask import Blueprint, jsonify, request

from services.copilot_marker_service import (
    MarkerActivationError,
    MarkerCloseError,
    _get_handoff_path,
    activate_marker,
    close_marker,
    get_marker_context,
    get_marker_execution_rating,
    is_activatable,
    list_markers_for_plan,
    plan_to_marker,
    read_marker_context,
    sprinttomarkers,
    sprinttomarkers_from_content,
    update_execution_rating,
    update_marker_fields,
    update_marker_status,
)
from services.db_service import execute


copilot_marker_bp = Blueprint("copilot_marker", __name__)


def _resolve_project_id(project_id=None, plan_id=None):
    if project_id:
        return str(project_id).strip()
    if plan_id is None:
        return None
    row = execute("SELECT project_name FROM project_plans WHERE id = %s", (plan_id,), fetchone=True)
    if not row or not row.get("project_name"):
        return None
    return str(row["project_name"]).strip()


@copilot_marker_bp.route("/api/copilot/markers")
def api_copilot_markers():
    plan_id = request.args.get("plan_id")
    project_id = _resolve_project_id(request.args.get("project_id"), plan_id)
    if not plan_id:
        return jsonify({"error": "plan_id ist erforderlich"}), 400
    if not project_id:
        return jsonify({"error": "project_id konnte nicht aufgeloest werden"}), 400
    try:
        markers = list_markers_for_plan(project_id, plan_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"markers": markers})


@copilot_marker_bp.route("/api/copilot/markers/<marker_id>")
def api_copilot_marker(marker_id):
    project_id = _resolve_project_id(request.args.get("project_id"), request.args.get("plan_id"))
    if not project_id:
        return jsonify({"error": "project_id ist erforderlich"}), 400
    try:
        marker = get_marker_context(project_id, marker_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(marker) if marker else (jsonify({"error": "Marker nicht gefunden"}), 404)


@copilot_marker_bp.route("/api/copilot/markers/<marker_id>/status", methods=["PATCH"])
def api_copilot_marker_status(marker_id):
    data = request.get_json(silent=True) or {}
    project_id = _resolve_project_id(data.get("project_id"), data.get("plan_id"))
    if not project_id:
        return jsonify({"error": "project_id ist erforderlich"}), 400
    if not data.get("status"):
        return jsonify({"error": "status ist erforderlich"}), 400
    try:
        marker = update_marker_status(project_id, marker_id, data.get("status"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not marker:
        return jsonify({"error": "Marker nicht gefunden"}), 404
    return jsonify({"ok": True, "marker_id": marker["marker_id"], "status": marker["status"], "updated_at": marker["updated_at"]})


@copilot_marker_bp.route("/api/copilot/markers/<marker_id>/fields", methods=["PATCH"])
def api_copilot_marker_fields(marker_id):
    data = request.get_json(silent=True) or {}
    project_id = _resolve_project_id(data.get("project_id"), data.get("plan_id"))
    if not project_id:
        return jsonify({"error": "project_id ist erforderlich"}), 400
    if data.get("fields") is None:
        return jsonify({"error": "fields ist erforderlich"}), 400
    try:
        marker = update_marker_fields(project_id, marker_id, data.get("fields"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(marker) if marker else (jsonify({"error": "Marker nicht gefunden"}), 404)


@copilot_marker_bp.route("/api/copilot/markers/<marker_id>/activate", methods=["POST"])
def api_copilot_marker_activate(marker_id):
    data = request.get_json(silent=True) or {}
    project_id = _resolve_project_id(data.get("project_id"), data.get("plan_id"))
    if not project_id:
        return jsonify({"error": "project_id ist erforderlich"}), 400
    handoff_path = data.get("handoff_path")
    context_path = data.get("context_path") or "marker-context.md"
    try:
        if handoff_path:
            activatable, gate_reason = is_activatable(handoff_path, marker_id)
            if not activatable:
                return jsonify({"ok": False, "error": "gate_blocked", "reason": gate_reason}), 409
        result = activate_marker(project_id, marker_id, context_path)
    except MarkerActivationError as e:
        if getattr(e, "gate_reason", "") and str(e) == "gate_blocked":
            return jsonify({"ok": False, "error": "gate_blocked", "reason": e.gate_reason}), 409
        return jsonify({"error": str(e)}), 404 if str(e) == "Marker nicht gefunden" else 400
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    marker = result["marker"]
    return jsonify({"ok": True, "marker_id": marker["marker_id"], "status": marker["status"], "updated_at": marker["updated_at"], "context_path": result["context_path"]})


@copilot_marker_bp.route("/api/copilot/markers/<marker_id>/close", methods=["POST"])
def api_copilot_marker_close(marker_id):
    data = request.get_json(silent=True) or {}
    project_id = _resolve_project_id(data.get("project_id"), data.get("plan_id"))
    handoff_path = data.get("handoff_path")
    context_path = data.get("context_path")
    if not handoff_path and not project_id and context_path:
        try:
            context = read_marker_context(context_path=context_path)
            project_id = _resolve_project_id(context.get("project_id"), context.get("plan_id"))
        except FileNotFoundError:
            pass
    if not handoff_path:
        if not project_id:
            return jsonify({"ok": False, "error": "project_id ist erforderlich"}), 400
        handoff_path = _get_handoff_path(project_id)
    if context_path is None and project_id:
        context_path = "marker-context.md"
    try:
        marker = close_marker(handoff_path, marker_id, project_id=project_id, status=data.get("status"), naechster_schritt=data.get("naechster_schritt"), last_session=data.get("last_session"), context_path=context_path)
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "handoff_missing"}), 404
    except MarkerCloseError as e:
        return jsonify({"ok": False, "error": str(e)}), 404 if str(e) == "marker_not_found" else 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "marker_id": marker.marker_id, "status": marker.status, "updated_at": marker.updated_at})


@copilot_marker_bp.route("/api/marker/<marker_id>/execution-rating", methods=["GET"])
def api_marker_execution_rating_get(marker_id):
    project_id = _resolve_project_id(request.args.get("project_id"), request.args.get("plan_id"))
    if not project_id:
        return jsonify({"error": "project_id ist erforderlich"}), 400
    try:
        rating = get_marker_execution_rating(_get_handoff_path(project_id), marker_id)
    except FileNotFoundError:
        return jsonify({"error": "handoff_missing"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(rating) if rating else (jsonify({"error": "marker_not_found"}), 404)


@copilot_marker_bp.route("/api/marker/<marker_id>/execution-rating", methods=["POST"])
def api_marker_execution_rating_post(marker_id):
    data = request.get_json(silent=True) or {}
    project_id = _resolve_project_id(data.get("project_id"), data.get("plan_id"))
    if not project_id:
        return jsonify({"error": "project_id ist erforderlich"}), 400
    if "execution_score" not in data:
        return jsonify({"error": "execution_score ist erforderlich"}), 400
    try:
        rating = update_execution_rating(_get_handoff_path(project_id), marker_id, data.get("execution_score"), execution_comment=data.get("execution_comment"), sessionid=data.get("sessionid"))
    except FileNotFoundError:
        return jsonify({"error": "handoff_missing"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 404 if str(e) == "marker_not_found" else 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(rating)


@copilot_marker_bp.route("/api/sprint/<plan_id>/to-markers", methods=["POST"])
def api_sprint_to_markers(plan_id):
    data = request.get_json(silent=True) or {}
    project_id = _resolve_project_id(data.get("project_id"), data.get("db_plan_id"))
    sprint_path = data.get("sprint_path") or plan_id
    handoff_path = data.get("handoff_path") or (_get_handoff_path(project_id) if project_id else None)
    db_plan_id = data.get("db_plan_id")
    if not handoff_path:
        return jsonify({"ok": False, "error": "project_id ist erforderlich"}), 400
    try:
        markers = sprinttomarkers(sprint_path, plan_id, handoff_path)
    except FileNotFoundError:
        if not db_plan_id:
            return jsonify({"ok": False, "error": "sprint_missing"}), 404
        row = execute("SELECT content, filename, title FROM project_plans WHERE id = %s", (db_plan_id,), fetchone=True)
        if not row or not row.get("content"):
            return jsonify({"ok": False, "error": "sprint_missing"}), 404
        try:
            markers = sprinttomarkers_from_content(row.get("content"), plan_id, handoff_path, source_label=row.get("filename") or row.get("title") or f"plan:{db_plan_id}")
        except ValueError as e:
            if str(e) not in ("plan_id_not_found", "tasks_not_found"):
                return jsonify({"ok": False, "error": str(e)}), 400
            markers = plan_to_marker(plan_id, handoff_path, title=row.get("title") or plan_id, context_summary=row.get("content", "").split("\n", 1)[0].lstrip("# ").strip(), next_action="Plan im Detail ausarbeiten", source_label=row.get("filename") or row.get("title") or f"plan:{db_plan_id}")
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 404 if str(e) in ("plan_id_not_found", "tasks_not_found") else 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "plan_id": plan_id, "count": len(markers), "markers": [marker.__dict__ for marker in markers]})
