"""
Unified Cockpit API — Aggregierter Projekt-Endpoint.

Liefert alles was das Cockpit fuer ein Projekt braucht:
Marker, Workflow-Daten, aktive Plaene.
"""
from dataclasses import asdict

from flask import Blueprint, jsonify

from routes.api_utils import api_route

cockpit_bp = Blueprint("cockpit", __name__)


@cockpit_bp.route("/api/cockpit/project/<path:name>")
@api_route
def get_cockpit_project_data(name):
    """Aggregierter Endpoint fuer das Cockpit.

    Liefert:
    - markers: Alle Marker des Projekts (als Dicts)
    - workflow: Workflow-Loop-Daten (Steps, Groups, Signals, Current/Next)
    - plans: Aktive Plaene fuer den Plan-Filter
    """
    from services.workflow_core_service import get_markers
    from services.workflow_loop_service import build_workflow_loop_data

    name = str(name or "").strip()
    if not name:
        return jsonify({"error": "Projektname fehlt"}), 400

    # Marker als Dicts
    raw_markers = get_markers(name)
    markers = [asdict(m) for m in raw_markers if m]

    # Workflow-Loop-Daten (Steps, Groups, Signals)
    try:
        workflow = build_workflow_loop_data(name)
    except FileNotFoundError:
        workflow = {}

    # Aktive Plaene fuer dieses Projekt
    plans = _get_project_plans(name)

    # Aktive Assignments (Dispatch) fuer dieses Projekt
    assignments = _get_active_assignments(name)

    return jsonify({
        "project_id": name,
        "markers": markers,
        "marker_count": len(markers),
        "workflow": workflow,
        "plans": plans,
        "assignments": assignments,
    })


def _get_active_assignments(project_name):
    """Aktive Dispatch-Assignments als dict {marker_id: assignment}."""
    try:
        from services.dispatch_service import list_assignments
        rows = list_assignments(project_name=project_name)
        result = {}
        for row in rows:
            state = row.get("approval_state", "")
            if state in ("proposed", "approved", "claimed"):
                mid = str(row.get("marker_id") or "")
                if mid and mid not in result:
                    result[mid] = {
                        "executor_tool": row.get("executor_tool", ""),
                        "approval_state": state,
                        "role_id": row.get("role_id", ""),
                    }
        return result
    except Exception:
        return {}


def _get_project_plans(project_name):
    """Aktive Plaene eines Projekts aus der DB."""
    try:
        from services.db_service import execute
        rows = execute(
            """
            SELECT id, title, status, category, updated_at
            FROM project_plans
            WHERE project_name = %s
              AND status IN ('active', 'draft')
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 50
            """,
            (project_name,),
            fetch=True,
        )
        return [dict(r) for r in rows] if rows else []
    except Exception:
        return []
