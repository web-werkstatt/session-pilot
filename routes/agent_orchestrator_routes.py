"""
Sprint sprint-agent-orchestrator-hardening-phase-1-foundation (2026-04-17):
Minimale REST-API fuer Agent-Orchestrator Phase 1.

Endpunkte v1:
  POST /api/agent-tasks                 -> Task-Contract anlegen
  GET  /api/agent-tasks/<id>            -> Task-Contract lesen
  POST /api/agent-tasks/<id>/preflight  -> Preflight-Gate ausfuehren
  GET  /api/agent-sessions/<sid>/state  -> aktueller Session-State
  POST /api/agent-sessions/<sid>/state  -> Session-State setzen

Tag 3 (2026-04-17) ergaenzt den Handoff-/Marker-Resolver:
  POST /api/agent-tasks/resolve-context -> Resolver (read-only)
  POST /api/agent-tasks/bootstrap       -> Resolver + Task-Contract anlegen
"""
from flask import Blueprint, jsonify, make_response, request

from routes.api_utils import api_route
import services.agent_orchestrator_service as agent_orchestrator_service
import services.agent_verify_service as agent_verify_service
import services.agent_recovery_snapshot as agent_recovery_snapshot
import services.agent_project_config_service as agent_project_config_service
import services.agent_prompt_export_service as agent_prompt_export_service
import services.agent_task_auth as agent_task_auth

agent_orchestrator_bp = Blueprint("agent_orchestrator", __name__)


@agent_orchestrator_bp.route("/api/agent-tasks", methods=["POST"])
@api_route
def api_create_agent_task():
    payload = request.get_json(silent=True) or {}
    try:
        contract = agent_orchestrator_service.create_task(payload)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify(contract), 201


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>", methods=["GET"])
@api_route
def api_get_agent_task(task_id):
    contract = agent_orchestrator_service.get_task(task_id)
    if not contract:
        return jsonify({"error": "task not found"}), 404
    return jsonify(contract)


@agent_orchestrator_bp.route("/api/agent-tasks/resolve-context", methods=["POST"])
@api_route
def api_resolve_agent_context():
    payload = request.get_json(silent=True) or {}
    try:
        result = agent_orchestrator_service.resolve_context(
            payload.get("project_id"),
            plan_id=payload.get("plan_id"),
            marker_id=payload.get("marker_id"),
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify(result)


@agent_orchestrator_bp.route("/api/agent-tasks/bootstrap", methods=["POST"])
@api_route
def api_bootstrap_agent_task():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    if not title or not str(title).strip():
        return jsonify({"error": "title required"}), 400
    try:
        result = agent_orchestrator_service.bootstrap_task(
            project_id=payload.get("project_id"),
            title=title,
            goal=payload.get("goal") or "",
            plan_id=payload.get("plan_id"),
            marker_id=payload.get("marker_id"),
            session_id=payload.get("session_id"),
            overrides=payload.get("overrides") or {},
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify(result), 201


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/prompt", methods=["GET"])
@api_route
def api_get_agent_task_prompt(task_id):
    """Sprint Executor-Handoff Commit 1 (2026-04-17):
    Liefert einen fertig formulierten Markdown-Prompt fuer eine interaktive
    Claude-Session. Der Prompt kann direkt gepastet werden.

    Query-Parameter (optional):
      * project — Resolver-Projekt-Slug
      * plan    — numerische project_plans.id
      * marker  — Marker-Slug

    Ohne Query-Parameter wird der Handoff-Abschnitt als
    "kein Handoff konfiguriert" gefuehrt; der restliche Prompt bleibt
    vollstaendig.

    Auth: Pflicht-Header `X-Agent-Task-Token` gegen `~/.agent-task-token`.
    """
    auth_err = agent_task_auth.check_agent_task_token()
    if auth_err is not None:
        return auth_err

    contract = agent_orchestrator_service.get_task(task_id)
    if not contract:
        return jsonify({"error": "task not found"}), 404

    project_slug = (request.args.get("project") or "").strip()
    plan_id = (request.args.get("plan") or "").strip() or None
    marker_id = (request.args.get("marker") or "").strip() or None

    context = None
    if project_slug:
        try:
            context = agent_orchestrator_service.resolve_context(
                project_slug,
                plan_id=plan_id,
                marker_id=marker_id,
            )
        except ValueError:
            context = None

    markdown = agent_prompt_export_service.build_prompt_markdown(
        contract, context=context
    )
    response = make_response(markdown, 200)
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    return response


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/preflight", methods=["POST"])
@api_route
def api_run_agent_preflight(task_id):
    body = request.get_json(silent=True) or {}
    repo_path = body.get("repo_path") or None
    try:
        result = agent_orchestrator_service.run_preflight(task_id, repo_path=repo_path)
    except ValueError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result)


@agent_orchestrator_bp.route("/api/agent-sessions/<session_id>/state", methods=["GET"])
@api_route
def api_get_agent_session_state(session_id):
    state = agent_orchestrator_service.get_session_state(session_id)
    if not state:
        return jsonify({"session_id": session_id, "state": None}), 200
    return jsonify(state)


@agent_orchestrator_bp.route("/api/agent-sessions/<session_id>/state", methods=["POST"])
@api_route
def api_set_agent_session_state(session_id):
    payload = request.get_json(silent=True) or {}
    state = payload.get("state")
    if not state:
        return jsonify({"error": "state required"}), 400
    try:
        updated = agent_orchestrator_service.set_session_state(
            session_id,
            state,
            reason=payload.get("reason"),
            locked=bool(payload.get("locked", False)),
            blocking_issues=payload.get("blocking_issues") or [],
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify(updated)


# ---------------------------------------------------------------------------
# Phase 2 — Verify-Gate MVP
# ---------------------------------------------------------------------------

@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/execution", methods=["POST"])
@api_route
def api_record_execution(task_id):
    payload = request.get_json(silent=True) or {}
    try:
        result = agent_verify_service.record_execution(task_id, payload)
    except ValueError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result), 201


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/execution", methods=["GET"])
@api_route
def api_get_execution(task_id):
    result = agent_verify_service.get_execution(task_id)
    if not result:
        return jsonify({"error": "no execution_result for task"}), 404
    return jsonify(result)


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/verify", methods=["POST"])
@api_route
def api_run_verify_gate(task_id):
    # In Phase 2 gibt es API-seitig keinen Default-command_runner, damit die
    # Route nie unbeabsichtigt Subprocess-Checks auf dem Server ausloest. Wer
    # echte Commands laufen lassen will, muss das ueber den Service mit
    # explizitem command_runner anstossen.
    try:
        result = agent_verify_service.run_verify_gate(task_id)
    except ValueError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result), 201


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/verify", methods=["GET"])
@api_route
def api_get_verify_gate(task_id):
    result = agent_verify_service.get_verify_gate(task_id)
    if not result:
        return jsonify({"error": "no verify_gate_result for task"}), 404
    return jsonify(result)


@agent_orchestrator_bp.route("/api/agent-sessions/<session_id>/recover", methods=["POST"])
@api_route
def api_recover_agent_session(session_id):
    """Phase 3: setzt Session auf `recovery` und speichert Snapshot.

    Optionales JSON-Body:
      {
        "repo_path": "...",         # optional, sonst Projekt-Root
        "reason": "...",            # optional, Default "recovery snapshot captured"
        "snapshot": {...}           # optional, ueberschreibt automatisch erzeugten Snapshot
      }
    """
    payload = request.get_json(silent=True) or {}
    snapshot = payload.get("snapshot")
    if snapshot is None:
        snapshot = agent_recovery_snapshot.build_recovery_snapshot(
            repo_path=payload.get("repo_path"),
        )
    try:
        state = agent_recovery_snapshot.persist_recovery_snapshot(
            session_id,
            snapshot,
            reason=payload.get("reason"),
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({
        "session_state": state,
        "snapshot": snapshot,
    }), 201


# ---------------------------------------------------------------------------
# Sprint Project-Config: Admin-API
# ---------------------------------------------------------------------------

@agent_orchestrator_bp.route(
    "/api/agent-projects/<int:project_id>/config", methods=["GET"]
)
@api_route
def api_get_agent_project_config(project_id):
    """Liefert die effektive Config (inkl. Default-Fallback je Feld)."""
    cfg = agent_project_config_service.get_config(project_id)
    return jsonify(cfg)


@agent_orchestrator_bp.route(
    "/api/agent-projects/<int:project_id>/config", methods=["PUT"]
)
@api_route
def api_set_agent_project_config(project_id):
    """Upsertet uebergebene Felder. Unbekannte Felder -> 400."""
    payload = request.get_json(silent=True) or {}
    try:
        cfg = agent_project_config_service.set_config(project_id, **payload)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify(cfg)


@agent_orchestrator_bp.route("/api/agent-tasks/<int:task_id>/close", methods=["POST"])
@api_route
def api_close_task(task_id):
    payload = request.get_json(silent=True) or {}
    try:
        result = agent_verify_service.close_task(
            task_id,
            session_id=payload.get("session_id"),
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 404
    decision = result["decision"]
    status_code = 200 if decision.get("can_close") else 409
    return jsonify(result), status_code
