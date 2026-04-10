"""
ADR-001: Zentrale Domaenenschicht fuer Marker-Zugriff (DB-first).

Alle Marker-Lese- und Schreiboperationen laufen ueber diesen Service.
workflow_loop_service und copilot_marker_service delegieren hierher.
"""
import json
import logging
from dataclasses import asdict

from services.copilot_marker_format import Marker
from services.db_service import ensure_marker_schema, execute
from services.marker_importer import import_markers_from_handoff
from services.workflow_state_service import (
    get_workflow_state,
    sync_marker_to_workflow,
)

log = logging.getLogger(__name__)


def get_markers(project_name, plan_id=None):
    """Liest alle Marker eines Projekts aus der DB.

    Falls die DB leer ist und eine handoff.md existiert, wird automatisch
    ein Import angestossen (Uebergangsphase).

    Returns:
        list[Marker]
    """
    ensure_marker_schema()
    project_name = str(project_name or "").strip()
    if not project_name:
        return []

    markers = _fetch_markers_from_db(project_name, plan_id=plan_id)

    # Uebergangsphase: Fallback auf handoff.md-Import
    if not markers:
        result = import_markers_from_handoff(project_name)
        if result["created"] > 0:
            log.info("Auto-Import aus handoff.md: %d Marker fuer %s",
                     result["created"], project_name)
            markers = _fetch_markers_from_db(project_name, plan_id=plan_id)

    return markers


def get_marker(project_name, marker_id):
    """Liest einen einzelnen Marker aus der DB.

    Returns:
        Marker oder None
    """
    ensure_marker_schema()
    row = execute(
        "SELECT * FROM markers WHERE project_name = %s AND marker_id = %s",
        (project_name, marker_id),
        fetchone=True,
    )
    return _row_to_marker(row) if row else None


def update_marker_field(project_name, marker_id, **fields):
    """Aktualisiert einzelne Felder eines Markers in der DB.

    Erlaubte Felder: titel, ziel, naechster_schritt, prompt, prompt_suggestion,
    risiko, checks, status, execution_score, execution_comment, last_session,
    sprint_tag, spec_tag.
    """
    ensure_marker_schema()
    allowed = {
        "titel", "ziel", "naechster_schritt", "prompt", "prompt_suggestion",
        "risiko", "checks", "status", "execution_score", "execution_comment",
        "last_session", "sprint_tag", "spec_tag", "sprint_plan_id", "spec_id",
    }
    update_parts = []
    params = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "checks":
            update_parts.append("checks = %s::jsonb")
            params.append(json.dumps(value or [], ensure_ascii=True))
        else:
            update_parts.append(f"{key} = %s")
            params.append(value)

    if not update_parts:
        return None

    update_parts.append("updated_at = NOW()")
    params.extend([project_name, marker_id])

    execute(
        f"""UPDATE markers SET {', '.join(update_parts)}
            WHERE project_name = %s AND marker_id = %s""",
        tuple(params),
    )
    return get_marker(project_name, marker_id)


def update_marker_state(project_name, marker_id, new_status, executor_tool=None):
    """Aktualisiert den Marker-Status und synchronisiert den Workflow-State.

    Aendert sowohl `markers.status` als auch den persistierten Workflow-State.
    """
    ensure_marker_schema()

    # Marker-Status in markers-Tabelle aktualisieren
    update_marker_field(project_name, marker_id, status=new_status)

    # Workflow-State synchronisieren
    marker = get_marker(project_name, marker_id)
    if marker:
        gate_ready = bool(
            (marker.prompt or "").strip()
            and len(marker.checks or []) >= 1
        )
        sync_marker_to_workflow(
            project_name, marker_id, new_status,
            last_session=marker.last_session or None,
            gate_ready=gate_ready,
            execution_score=marker.execution_score,
        )

        # executor_tool setzen falls angegeben
        if executor_tool:
            execute(
                """UPDATE marker_workflow_states SET executor_tool = %s
                   WHERE project_name = %s AND marker_id = %s""",
                (executor_tool, project_name, marker_id),
            )

    return marker


def get_handoff_view(project_name):
    """Read-Model fuer handoff.md-Regenerierung.

    Liefert alle Marker eines Projekts als Dicts mit allen Feldern,
    sortiert nach plan_id und marker_id.
    """
    markers = get_markers(project_name)
    result = []
    for m in markers:
        data = asdict(m)
        # Workflow-State anreichern
        state = get_workflow_state(project_name, m.marker_id)
        if state:
            data["workflow_status"] = state.get("workflow_status", "planned")
            data["owner"] = state.get("owner", "")
            data["blocked_reason"] = state.get("blocked_reason", "")
            data["executor_tool"] = state.get("executor_tool", "")
        result.append(data)
    return result


def _fetch_markers_from_db(project_name, plan_id=None):
    """Liest Marker aus der DB und konvertiert zu Marker-Dataclass-Instanzen."""
    if plan_id:
        rows = execute(
            """SELECT * FROM markers
               WHERE project_name = %s AND plan_id = %s
               ORDER BY marker_id""",
            (project_name, str(plan_id)),
            fetch=True,
        ) or []
    else:
        rows = execute(
            """SELECT * FROM markers
               WHERE project_name = %s
               ORDER BY marker_id""",
            (project_name,),
            fetch=True,
        ) or []

    return [_row_to_marker(row) for row in rows if row]


def _row_to_marker(row):
    """Konvertiert eine DB-Row in eine Marker-Dataclass-Instanz."""
    if not row:
        return None
    row = dict(row)

    checks = row.get("checks") or []
    if isinstance(checks, str):
        checks = json.loads(checks)

    last_execution_at = row.get("last_execution_at")
    if last_execution_at and hasattr(last_execution_at, "isoformat"):
        last_execution_at = last_execution_at.isoformat()
    else:
        last_execution_at = str(last_execution_at or "")

    updated_at = row.get("updated_at")
    if updated_at and hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    else:
        updated_at = str(updated_at or "")

    return Marker(
        marker_id=row["marker_id"],
        titel=row["titel"],
        plan_id=str(row["plan_id"]),
        status=row["status"],
        ziel=row.get("ziel") or "",
        naechster_schritt=row.get("naechster_schritt") or "",
        prompt=row.get("prompt") or "",
        prompt_suggestion=row.get("prompt_suggestion") or "",
        risiko=row.get("risiko") or "",
        checks=checks,
        last_session=row.get("last_session") or "",
        updated_at=updated_at,
        execution_score=row.get("execution_score"),
        execution_comment=row.get("execution_comment") or "",
        last_execution_at=last_execution_at,
        sprint_tag=row.get("sprint_tag") or "",
        spec_tag=row.get("spec_tag") or "",
        sprint_plan_id=row.get("sprint_plan_id"),
        spec_id=row.get("spec_id"),
    )
