"""
Sprint sprint-task-entity-und-drilldown (2026-04-15):
API-Endpunkte fuer plan_tasks. Lesen erfolgt direkt aus DB; Schreiben
beschraenkt sich auf Inline-Rename und das Erzeugen eines Markers aus
einem Task (mit task_id-Backlink).
"""
from flask import Blueprint, jsonify, request

from routes.api_utils import api_route
from services.copilot_marker_format import Marker, parse_markers, _write_marker
from services.copilot_marker_import_flow import _build_sprint_marker_id, _sync_to_db
from services.copilot_marker_service import _get_handoff_path
from services.db_service import execute
from services.plan_task_service import (
    get_markers_for_task,
    get_task,
    list_tasks_for_plan,
    list_tasks_for_section,
    rename_task,
)


plan_task_bp = Blueprint("plan_task", __name__)


@plan_task_bp.route("/api/plans/<int:plan_id>/tasks", methods=["GET"])
@api_route
def api_list_plan_tasks(plan_id):
    tasks = list_tasks_for_plan(plan_id, include_status=True)
    return jsonify({"ok": True, "plan_id": plan_id, "count": len(tasks), "tasks": tasks})


@plan_task_bp.route("/api/plans/<int:plan_id>/sections/<section_key>/tasks", methods=["GET"])
@api_route
def api_list_section_tasks(plan_id, section_key):
    tasks = list_tasks_for_section(plan_id, section_key, include_status=True)
    return jsonify({
        "ok": True,
        "plan_id": plan_id,
        "section_key": section_key,
        "count": len(tasks),
        "tasks": tasks,
    })


@plan_task_bp.route("/api/tasks/<int:task_id>", methods=["GET"])
@api_route
def api_get_task(task_id):
    task = get_task(task_id)
    if not task:
        return jsonify({"ok": False, "error": "task_not_found"}), 404
    return jsonify({"ok": True, "task": task})


@plan_task_bp.route("/api/tasks/<int:task_id>/markers", methods=["GET"])
@api_route
def api_get_task_markers(task_id):
    task = get_task(task_id)
    if not task:
        return jsonify({"ok": False, "error": "task_not_found"}), 404
    markers = get_markers_for_task(task_id)
    return jsonify({"ok": True, "task_id": task_id, "count": len(markers), "markers": markers})


@plan_task_bp.route("/api/tasks/<int:task_id>", methods=["PATCH"])
@api_route
def api_patch_task(task_id):
    data = request.get_json(silent=True) or {}
    new_title = data.get("title")
    if new_title is None:
        return jsonify({"ok": False, "error": "title_required"}), 400
    updated = rename_task(task_id, new_title)
    if not updated:
        return jsonify({"ok": False, "error": "task_not_found_or_invalid_title"}), 404
    return jsonify({"ok": True, "task": updated})


@plan_task_bp.route("/api/tasks/<int:task_id>/to-marker", methods=["POST"])
def api_task_to_marker(task_id):
    """Erzeugt einen Marker aus einem Task und setzt markers.task_id.

    Body (optional):
      - status: initialer Marker-Status (Default: 'todo')
      - prompt_suggestion: ueberschreibt den generierten Vorschlag
    """
    task = get_task(task_id)
    if not task:
        return jsonify({"ok": False, "error": "task_not_found"}), 404

    plan_row = execute(
        "SELECT id, project_name, title FROM project_plans WHERE id = %s",
        (task["plan_id"],),
        fetchone=True,
    )
    if not plan_row or not plan_row.get("project_name"):
        return jsonify({"ok": False, "error": "plan_or_project_missing"}), 400

    project_name = str(plan_row["project_name"]).strip()
    handoff_path = _get_handoff_path(project_name)
    if not handoff_path:
        return jsonify({"ok": False, "error": "handoff_path_missing"}), 400

    body = request.get_json(silent=True) or {}
    status = str(body.get("status") or "todo").strip() or "todo"
    section_key = task.get("section_key") or ""
    spec_key = task.get("spec_key") or ""
    title = task.get("title") or f"Task {task_id}"

    marker_plan_id = section_key or f"plan-{task['plan_id']}"
    marker_id = _build_sprint_marker_id(marker_plan_id, title)

    existing = next((m for m in parse_markers(handoff_path) if m.marker_id == marker_id), None)
    if existing:
        marker = existing
    else:
        from datetime import datetime, timezone
        prompt_suggestion = str(body.get("prompt_suggestion") or f"Arbeite an: {title}").strip()
        marker = Marker(
            marker_id=marker_id,
            titel=title,
            plan_id=marker_plan_id,
            status=status,
            ziel=title,
            naechster_schritt="Task umsetzen",
            prompt="",
            prompt_suggestion=prompt_suggestion,
            risiko="",
            checks=["Ergebnis gegen Task-Beschreibung pruefen"],
            last_session="",
            updated_at=datetime.now(timezone.utc).isoformat(),
            sprint_tag=section_key,
            spec_tag=spec_key,
        )
        _write_marker(handoff_path, marker)
        _sync_to_db(handoff_path)

    # Backlink: markers.task_id setzen (DB-only, handoff.md hat kein task_id-Feld)
    execute(
        "UPDATE markers SET task_id = %s WHERE project_name = %s AND marker_id = %s",
        (task_id, project_name, marker_id),
    )

    return jsonify({
        "ok": True,
        "task_id": task_id,
        "marker_id": marker_id,
        "project_name": project_name,
        "created": existing is None,
    })
