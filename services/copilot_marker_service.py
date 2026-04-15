"""
Marker-Service fuer das handoff.md Dual-Format.
"""
import os
from dataclasses import asdict
from datetime import datetime, timezone

from config import PROJECTS_DIR
from services.copilot_marker_format import (
    VALID_STATUSES,
    Marker,
    MarkerActivationError,
    MarkerCloseError,
    _compute_gate,
    _marker_to_dict,
    _serialize_marker,  # Re-Export fuer project_handoff_service
    _validate_execution_score,
    _write_marker,
    parse_markers,
    parse_markers_with_errors,
)
from services.copilot_marker_import_flow import (  # Re-Exports fuer copilot_marker_routes
    buildsuggestion, plan_to_marker, sprinttomarkers, sprinttomarkers_from_content,
)
from services.db_service import ensure_session_review_schema, execute
from services.path_resolver import resolve_project_path
from services.workflow_core_service import (
    get_markers as core_get_markers,
    get_marker as core_get_marker,
    update_marker_field as core_update_marker_field,
    update_marker_state as core_update_marker_state,
)


def _get_handoff_path(project_id):
    project_id = str(project_id).strip()
    direct_root = os.path.join(PROJECTS_DIR, project_id)
    if os.path.isdir(direct_root):
        return os.path.join(direct_root, "handoff.md")
    project_root = resolve_project_path(project_id)
    if project_root:
        return os.path.join(project_root, "handoff.md")
    return os.path.join(PROJECTS_DIR, project_id, "handoff.md")


def _resolve_context_path(project_id, context_path):
    project_id = str(project_id).strip()
    direct_root = os.path.join(PROJECTS_DIR, project_id)
    project_root = direct_root if os.path.isdir(direct_root) else resolve_project_path(project_id)
    if not project_root:
        raise FileNotFoundError(f"Projektpfad konnte nicht aufgeloest werden: {project_id}")
    context_name = str(context_path or "marker-context.md").strip() or "marker-context.md"
    return context_name if os.path.isabs(context_name) else os.path.join(project_root, context_name)


def read_marker_context(project_id=None, context_path="marker-context.md"):
    resolved_path = _resolve_context_path(project_id, context_path) if project_id else (context_path if os.path.isabs(context_path) else os.path.abspath(str(context_path or "marker-context.md").strip() or "marker-context.md"))
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(resolved_path)
    metadata = {"context_path": resolved_path}
    with open(resolved_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith("- ") and ":" in line:
                key, value = line[2:].split(":", 1)
                metadata[key.strip()] = value.strip()
    return metadata


def _project_from_handoff(handoff_path):
    """Leitet project_id aus handoff_path ab: /mnt/projects/<project>/handoff.md"""
    return os.path.basename(os.path.dirname(handoff_path)) if handoff_path else ""


def _resolve_marker(project_id, marker_id, handoff_path=None):
    """DB-first Marker-Lookup mit Fallback auf handoff.md."""
    try:
        marker = core_get_marker(project_id, marker_id)
        if marker:
            return marker
    except Exception:
        pass
    hp = handoff_path or _get_handoff_path(project_id)
    for m in parse_markers(hp):
        if m.marker_id == marker_id:
            return m
    return None


def _resolve_markers(project_id, handoff_path=None, plan_id=None):
    """DB-first Marker-Liste mit Fallback auf handoff.md."""
    try:
        markers = core_get_markers(project_id, plan_id=plan_id)
        if markers:
            return markers
    except Exception:
        pass
    hp = handoff_path or _get_handoff_path(project_id)
    all_markers = parse_markers(hp)
    if not all_markers and os.path.exists(hp):
        try:
            from services.project_handoff_service import write_handoff
            filepath, _ = write_handoff(project_id)
            all_markers = parse_markers(filepath) if filepath else []
        except Exception:
            pass
    if plan_id:
        plan_id_str = str(plan_id).strip()
        return [m for m in all_markers if m.plan_id == plan_id_str]
    return all_markers


def _render_marker_context(marker, project_id=""):
    checks_text = "\n".join(f"- {item}" for item in (marker.checks or [])) if marker.checks else "- _(keine checks definiert)_"
    return (
        "# Marker-Kontext\n\n"
        f"- marker_id: {marker.marker_id}\n- plan_id: {marker.plan_id}\n- sprint_tag: {marker.sprint_tag}\n- spec_tag: {marker.spec_tag}\n"
        f"{('- project_id: ' + project_id + chr(10)) if project_id else ''}"
        f"- titel: {marker.titel}\n- ziel: {marker.ziel}\n- naechster_schritt: {marker.naechster_schritt}\n- risiko: {marker.risiko}\n- status: {marker.status}\n- last_session: {marker.last_session or ''}\n\n"
        "## Prompt\n\n"
        f"{marker.prompt or ''}\n\n"
        "## Checks (Definition of Done)\n\n"
        f"{checks_text}\n"
    )


def is_activatable(handoff_path, marker_id):
    marker_id = str(marker_id).strip()
    project_id = _project_from_handoff(handoff_path)
    marker = _resolve_marker(project_id, marker_id, handoff_path) if project_id else None
    if not marker:
        for m in parse_markers(handoff_path):
            if m.marker_id == marker_id:
                marker = m
                break
    if marker:
        return _compute_gate(marker)
    raise MarkerActivationError("Marker nicht gefunden")


def activate_marker(project_id, marker_id, context_path):
    handoff_path = _get_handoff_path(project_id)
    resolved_context_path = _resolve_context_path(project_id, context_path)
    marker_id = str(marker_id).strip()
    marker = _resolve_marker(project_id, marker_id, handoff_path)
    if not marker:
        raise MarkerActivationError("Marker nicht gefunden")
    activatable, gate_reason = _compute_gate(marker)
    if not activatable:
        raise MarkerActivationError("gate_blocked", gate_reason=gate_reason)
    marker.status = "in_progress"
    marker.updated_at = datetime.now(timezone.utc).isoformat()
    marker = Marker(**asdict(marker))
    with open(resolved_context_path, "w", encoding="utf-8") as f:
        f.write(_render_marker_context(marker, project_id=project_id))
    _write_marker(handoff_path, marker)
    # DB synchron halten
    try:
        core_update_marker_state(project_id, marker_id, "in_progress")
    except Exception:
        pass
    return {"marker": _marker_to_dict(marker, include_gate=True), "context_path": resolved_context_path}


def list_markers_for_plan(project_id, plan_id):
    markers = _resolve_markers(project_id, plan_id=str(plan_id).strip())
    return [_marker_to_dict(marker, include_gate=True) for marker in markers]


def list_markers_for_plan_with_errors(project_id, plan_id):
    """Wie list_markers_for_plan, gibt zusaetzlich Parser-Fehler aus handoff.md zurueck.

    Returns:
        (markers_list, errors_list) - errors_list enthaelt nur Fehler aus der
        handoff.md des Projekts (kein Plan-Filter, da fehlerhafte Bloecke keine
        plan_id haben).
    """
    plan_id_str = str(plan_id).strip()
    handoff_path = _get_handoff_path(project_id)
    markers = _resolve_markers(project_id, handoff_path, plan_id=plan_id_str)
    # Parser-Fehler aus handoff.md pruefen (fuer UI-Anzeige)
    _, errors = parse_markers_with_errors(handoff_path) if os.path.exists(handoff_path) else ([], [])
    filtered = [_marker_to_dict(marker, include_gate=True) for marker in markers]
    return filtered, errors


def get_marker_context(project_id, marker_id):
    marker_id = str(marker_id).strip()
    marker = _resolve_marker(project_id, marker_id)
    return _marker_to_dict(marker, include_gate=True) if marker else None


def get_marker_by_last_session(project_id, session_uuid):
    session_uuid = str(session_uuid or "").strip()
    if not session_uuid:
        return None
    for marker in _resolve_markers(project_id):
        if marker.last_session == session_uuid:
            return _marker_to_dict(marker, include_gate=True)
    return None


def get_marker_execution_rating(handoff_path, marker_id):
    marker_id = str(marker_id or "").strip()
    project_id = _project_from_handoff(handoff_path)
    marker = _resolve_marker(project_id, marker_id, handoff_path) if project_id else None
    if not marker:
        for m in parse_markers(handoff_path):
            if m.marker_id == marker_id:
                marker = m
                break
    if marker:
        return {"marker_id": marker.marker_id, "execution_score": marker.execution_score, "execution_comment": marker.execution_comment, "last_execution_at": marker.last_execution_at}
    return None


def update_execution_rating(handoff_path, marker_id, execution_score, execution_comment=None, sessionid=None):
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("handoff_missing")
    marker_id = str(marker_id or "").strip()
    if not marker_id:
        raise ValueError("marker_id ist erforderlich")
    score = _validate_execution_score(execution_score)
    comment = "" if execution_comment is None else str(execution_comment).strip()
    now_iso = datetime.now(timezone.utc).isoformat()
    project_id = _project_from_handoff(handoff_path)
    marker = _resolve_marker(project_id, marker_id, handoff_path) if project_id else None
    if not marker:
        for m in parse_markers(handoff_path):
            if m.marker_id == marker_id:
                marker = m
                break
    if not marker:
        raise ValueError("marker_not_found")
    marker.execution_score = score
    marker.execution_comment = comment
    marker.last_execution_at = now_iso
    marker.updated_at = now_iso
    _write_marker(handoff_path, marker)
    if sessionid:
        ensure_session_review_schema()
        execute("UPDATE sessions SET execution_score = %s, execution_comment = %s, updated_at = NOW() WHERE session_uuid = %s", (score, comment or None, str(sessionid).strip()))
    # DB synchron halten
    if project_id:
        try:
            core_update_marker_field(project_id, marker_id, execution_score=score, execution_comment=comment)
        except Exception:
            pass
    return {"marker_id": marker.marker_id, "execution_score": marker.execution_score, "execution_comment": marker.execution_comment, "last_execution_at": marker.last_execution_at}


def update_marker_status(project_id, marker_id, status):
    status = str(status or "").strip()
    if status not in VALID_STATUSES:
        raise ValueError(f"ungueltiger status: {status}")
    handoff_path = _get_handoff_path(project_id)
    marker_id = str(marker_id).strip()
    marker = _resolve_marker(project_id, marker_id, handoff_path)
    if marker:
        marker.status = status
        marker.updated_at = datetime.now(timezone.utc).isoformat()
        _write_marker(handoff_path, marker)
        # DB synchron halten
        core_update_marker_field(project_id, marker_id, status=status)
        return _marker_to_dict(marker, include_gate=True)
    return None


def update_marker_fields(project_id, marker_id, fields):
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields muss ein nicht-leeres Objekt sein")
    allowed_fields = {"titel", "plan_id", "status", "ziel", "naechster_schritt", "prompt", "prompt_suggestion", "risiko", "checks", "last_session", "updated_at", "execution_score", "execution_comment", "last_execution_at", "sprint_tag", "spec_tag", "sprint_plan_id", "spec_id"}
    handoff_path = _get_handoff_path(project_id)
    marker_id = str(marker_id).strip()
    marker = _resolve_marker(project_id, marker_id, handoff_path)
    if not marker:
        return None
    for key, value in fields.items():
        if key not in allowed_fields:
            raise ValueError(f"ungueltiges feld: {key}")
        setattr(marker, key, value)
    marker.updated_at = datetime.now(timezone.utc).isoformat()
    marker = Marker(**asdict(marker))
    _write_marker(handoff_path, marker)
    # DB synchron halten
    db_fields = {k: v for k, v in fields.items() if k in allowed_fields and k != "updated_at"}
    if db_fields:
        core_update_marker_field(project_id, marker_id, **db_fields)
    return _marker_to_dict(marker, include_gate=True)


def close_marker(handoff_path, marker_id, *, project_id=None, status=None, naechster_schritt=None, last_session=None, updated_at=None, context_path=None, execution_score=None, execution_comment=None):
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("handoff_missing")
    marker_id = str(marker_id).strip()
    if not marker_id:
        raise MarkerCloseError("marker_not_found")
    pid = project_id or _project_from_handoff(handoff_path)
    marker = _resolve_marker(pid, marker_id, handoff_path) if pid else None
    if not marker:
        for m in parse_markers(handoff_path):
            if m.marker_id == marker_id:
                marker = m
                break
    if not marker:
        raise MarkerCloseError("marker_not_found")
    # Rating-Pflicht beim Abschluss: wer einen Marker auf done setzt, muss
    # frisch bewerten (Score 0-5). Retrospektives Rating ist wertlos, weil
    # die Erinnerung weg ist — siehe RATING_PENDING_WINDOW in workflow_loop_service.
    if status is not None and str(status).strip() == "done" and execution_score is None:
        raise MarkerCloseError("rating_required")
    if status is not None:
        next_status = str(status).strip()
        if next_status not in VALID_STATUSES:
            raise MarkerCloseError(f"ungueltiger status: {next_status}")
        marker.status = next_status
    if naechster_schritt is not None:
        marker.naechster_schritt = str(naechster_schritt).strip()
    if last_session is not None:
        marker.last_session = str(last_session).strip()
    if execution_score is not None:
        score = _validate_execution_score(execution_score)
        marker.execution_score = score
        marker.execution_comment = str(execution_comment).strip() if execution_comment else ""
        marker.last_execution_at = datetime.now(timezone.utc).isoformat()
    effective_updated_at = updated_at or datetime.now(timezone.utc)
    marker.updated_at = effective_updated_at.astimezone(timezone.utc).isoformat() if isinstance(effective_updated_at, datetime) else str(effective_updated_at).strip()
    marker = Marker(**asdict(marker))
    _write_marker(handoff_path, marker)
    # DB synchron halten
    if pid:
        db_fields = {}
        if status is not None:
            db_fields["status"] = marker.status
        if naechster_schritt is not None:
            db_fields["naechster_schritt"] = marker.naechster_schritt
        if last_session is not None:
            db_fields["last_session"] = marker.last_session
        if execution_score is not None:
            db_fields["execution_score"] = marker.execution_score
            db_fields["execution_comment"] = marker.execution_comment
            db_fields["last_execution_at"] = marker.last_execution_at
        if db_fields:
            try:
                core_update_marker_field(pid, marker_id, **db_fields)
            except Exception:
                pass
    if context_path:
        context_name = str(context_path).strip() or "marker-context.md"
        resolved_context_path = context_name if os.path.isabs(context_name) else (_resolve_context_path(project_id, context_name) if project_id else os.path.join(os.path.dirname(handoff_path), context_name))
        if os.path.exists(resolved_context_path):
            os.remove(resolved_context_path)
    return marker


def backfill_marker_last_sessions(project_id):
    project_id = str(project_id or "").strip()
    if not project_id:
        raise ValueError("project_id ist erforderlich")
    handoff_path = _get_handoff_path(project_id)
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("handoff_missing")

    markers = _resolve_markers(project_id, handoff_path)
    if not markers:
        return {"project_id": project_id, "handoff_path": handoff_path, "updated": 0, "markers_total": 0}

    plan_rows = execute(
        """SELECT id, session_uuid
           FROM project_plans
           WHERE project_name = %s
             AND session_uuid IS NOT NULL
             AND TRIM(session_uuid) != ''""",
        (project_id,),
        fetch=True,
    ) or []
    session_by_plan_id = {
        str(row.get("id")): str(row.get("session_uuid") or "").strip()
        for row in plan_rows
        if str(row.get("session_uuid") or "").strip()
    }

    updated = 0
    for marker in markers:
        if str(marker.last_session or "").strip():
            continue
        inferred_session = session_by_plan_id.get(str(marker.plan_id or "").strip())
        if not inferred_session:
            continue
        marker.last_session = inferred_session
        marker.updated_at = datetime.now(timezone.utc).isoformat()
        _write_marker(handoff_path, marker)
        # DB synchron halten
        try:
            core_update_marker_field(project_id, marker.marker_id, last_session=inferred_session)
        except Exception:
            pass
        updated += 1

    return {
        "project_id": project_id,
        "handoff_path": handoff_path,
        "updated": updated,
        "markers_total": len(markers),
    }
