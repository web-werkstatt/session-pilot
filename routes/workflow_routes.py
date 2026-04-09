"""
Sprint Workflow-v2: REST-API fuer Workflow-State-Management.
"""
from flask import Blueprint, jsonify, request

from routes.api_utils import api_route
from services.workflow_state_service import (
    get_allowed_transitions,
    get_transition_history,
    get_workflow_state,
    get_workflow_states_for_project,
    sync_marker_to_workflow,
    transition_workflow,
)

workflow_bp = Blueprint("workflow", __name__)


@workflow_bp.route("/api/project/<path:name>/workflow-states")
@api_route
def get_project_workflow_states(name):
    """Alle Workflow-States eines Projekts."""
    states = get_workflow_states_for_project(name)
    return jsonify(states)


@workflow_bp.route("/api/project/<path:name>/workflow-state/<marker_id>")
@api_route
def get_marker_workflow_state(name, marker_id):
    """Einzelner Workflow-State eines Markers."""
    state = get_workflow_state(name, marker_id)
    if not state:
        return jsonify({"error": "Kein Workflow-State fuer diesen Marker"}), 404
    allowed = get_allowed_transitions(name, marker_id)
    state["allowed_transitions"] = allowed.get("allowed", [])
    return jsonify(state)


@workflow_bp.route("/api/project/<path:name>/workflow-state/<marker_id>/transition", methods=["POST"])
@api_route
def post_workflow_transition(name, marker_id):
    """Statuswechsel fuer einen Marker ausfuehren."""
    data = request.get_json() or {}
    to_status = data.get("to_status", "").strip()
    if not to_status:
        return jsonify({"error": "to_status ist erforderlich"}), 400

    try:
        new_state = transition_workflow(
            name, marker_id, to_status,
            triggered_by=data.get("triggered_by", "user"),
            reason=data.get("reason"),
            owner=data.get("owner"),
            blocked_reason=data.get("blocked_reason"),
            last_session=data.get("last_session"),
        )
        allowed = get_allowed_transitions(name, marker_id)
        new_state["allowed_transitions"] = allowed.get("allowed", [])
        return jsonify(new_state)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@workflow_bp.route("/api/project/<path:name>/workflow-state/<marker_id>/history")
@api_route
def get_workflow_transition_history(name, marker_id):
    """Transition-Historie eines Markers."""
    limit = request.args.get("limit", 20, type=int)
    history = get_transition_history(name, marker_id, limit=min(limit, 100))
    return jsonify(history)


@workflow_bp.route("/api/project/<path:name>/workflow-sync", methods=["POST"])
@api_route
def post_workflow_sync(name):
    """Synchronisiert alle Marker eines Projekts in den Workflow-State.

    Erwartet JSON-Body mit markers: [{marker_id, status, last_session?}, ...]
    """
    data = request.get_json() or {}
    markers = data.get("markers", [])
    if not markers:
        return jsonify({"error": "markers-Array ist erforderlich"}), 400

    results = []
    for m in markers:
        mid = str(m.get("marker_id", "")).strip()
        mstatus = str(m.get("status", "")).strip()
        if not mid or not mstatus:
            continue
        state = sync_marker_to_workflow(name, mid, mstatus, last_session=m.get("last_session"))
        if state:
            results.append(state)

    return jsonify({"synced": len(results), "states": results})
