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
    _serialize_marker,
    _validate_execution_score,
    _write_marker,
    parse_markers,
)
from services.copilot_marker_import_flow import buildsuggestion, plan_to_marker, sprinttomarkers, sprinttomarkers_from_content
from services.db_service import ensure_session_review_schema, execute
from services.path_resolver import resolve_project_path


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


def _load_markers_with_regeneration(project_id):
    handoff_path = _get_handoff_path(project_id)
    markers = parse_markers(handoff_path)
    if markers or not os.path.exists(handoff_path):
        return markers
    try:
        from services.project_handoff_service import write_handoff
        filepath, _ = write_handoff(project_id)
        return parse_markers(filepath) if filepath else []
    except Exception:
        return []


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
    for marker in parse_markers(handoff_path):
        if marker.marker_id == marker_id:
            return _compute_gate(marker)
    raise MarkerActivationError("Marker nicht gefunden")


def activate_marker(project_id, marker_id, context_path):
    handoff_path = _get_handoff_path(project_id)
    resolved_context_path = _resolve_context_path(project_id, context_path)
    marker_id = str(marker_id).strip()
    for marker in parse_markers(handoff_path):
        if marker.marker_id != marker_id:
            continue
        activatable, gate_reason = _compute_gate(marker)
        if not activatable:
            raise MarkerActivationError("gate_blocked", gate_reason=gate_reason)
        marker.status = "in_progress"
        marker.updated_at = datetime.now(timezone.utc).isoformat()
        marker = Marker(**asdict(marker))
        with open(resolved_context_path, "w", encoding="utf-8") as f:
            f.write(_render_marker_context(marker, project_id=project_id))
        _write_marker(handoff_path, marker)
        return {"marker": _marker_to_dict(marker, include_gate=True), "context_path": resolved_context_path}
    raise MarkerActivationError("Marker nicht gefunden")


def list_markers_for_plan(project_id, plan_id):
    return [_marker_to_dict(marker, include_gate=True) for marker in _load_markers_with_regeneration(project_id) if marker.plan_id == str(plan_id).strip()]


def get_marker_context(project_id, marker_id):
    marker_id = str(marker_id).strip()
    for marker in _load_markers_with_regeneration(project_id):
        if marker.marker_id == marker_id:
            return _marker_to_dict(marker, include_gate=True)
    return None


def get_marker_by_last_session(project_id, session_uuid):
    session_uuid = str(session_uuid or "").strip()
    if not session_uuid:
        return None
    for marker in _load_markers_with_regeneration(project_id):
        if marker.last_session == session_uuid:
            return _marker_to_dict(marker, include_gate=True)
    return None


def get_marker_execution_rating(handoff_path, marker_id):
    marker_id = str(marker_id or "").strip()
    for marker in parse_markers(handoff_path):
        if marker.marker_id == marker_id:
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
    for marker in parse_markers(handoff_path):
        if marker.marker_id != marker_id:
            continue
        marker.execution_score = score
        marker.execution_comment = comment
        marker.last_execution_at = now_iso
        marker.updated_at = now_iso
        _write_marker(handoff_path, marker)
        if sessionid:
            ensure_session_review_schema()
            execute("UPDATE sessions SET execution_score = %s, execution_comment = %s, updated_at = NOW() WHERE session_uuid = %s", (score, comment or None, str(sessionid).strip()))
        return {"marker_id": marker.marker_id, "execution_score": marker.execution_score, "execution_comment": marker.execution_comment, "last_execution_at": marker.last_execution_at}
    raise ValueError("marker_not_found")


def update_marker_status(project_id, marker_id, status):
    status = str(status or "").strip()
    if status not in VALID_STATUSES:
        raise ValueError(f"ungueltiger status: {status}")
    handoff_path = _get_handoff_path(project_id)
    marker_id = str(marker_id).strip()
    for marker in _load_markers_with_regeneration(project_id):
        if marker.marker_id == marker_id:
            marker.status = status
            marker.updated_at = datetime.now(timezone.utc).isoformat()
            _write_marker(handoff_path, marker)
            return _marker_to_dict(marker, include_gate=True)
    return None


def update_marker_fields(project_id, marker_id, fields):
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields muss ein nicht-leeres Objekt sein")
    allowed_fields = {"titel", "plan_id", "status", "ziel", "naechster_schritt", "prompt", "prompt_suggestion", "risiko", "checks", "last_session", "updated_at", "execution_score", "execution_comment", "last_execution_at", "sprint_tag", "spec_tag", "sprint_plan_id", "spec_id"}
    handoff_path = _get_handoff_path(project_id)
    marker_id = str(marker_id).strip()
    for marker in _load_markers_with_regeneration(project_id):
        if marker.marker_id != marker_id:
            continue
        for key, value in fields.items():
            if key not in allowed_fields:
                raise ValueError(f"ungueltiges feld: {key}")
            setattr(marker, key, value)
        marker.updated_at = datetime.now(timezone.utc).isoformat()
        marker = Marker(**asdict(marker))
        _write_marker(handoff_path, marker)
        return _marker_to_dict(marker, include_gate=True)
    return None


def close_marker(handoff_path, marker_id, *, project_id=None, status=None, naechster_schritt=None, last_session=None, updated_at=None, context_path=None):
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("handoff_missing")
    marker_id = str(marker_id).strip()
    if not marker_id:
        raise MarkerCloseError("marker_not_found")
    for marker in parse_markers(handoff_path):
        if marker.marker_id != marker_id:
            continue
        if status is not None:
            next_status = str(status).strip()
            if next_status not in VALID_STATUSES:
                raise MarkerCloseError(f"ungueltiger status: {next_status}")
            marker.status = next_status
        if naechster_schritt is not None:
            marker.naechster_schritt = str(naechster_schritt).strip()
        if last_session is not None:
            marker.last_session = str(last_session).strip()
        effective_updated_at = updated_at or datetime.now(timezone.utc)
        marker.updated_at = effective_updated_at.astimezone(timezone.utc).isoformat() if isinstance(effective_updated_at, datetime) else str(effective_updated_at).strip()
        marker = Marker(**asdict(marker))
        _write_marker(handoff_path, marker)
        if context_path:
            context_name = str(context_path).strip() or "marker-context.md"
            resolved_context_path = context_name if os.path.isabs(context_name) else (_resolve_context_path(project_id, context_name) if project_id else os.path.join(os.path.dirname(handoff_path), context_name))
            if os.path.exists(resolved_context_path):
                os.remove(resolved_context_path)
        return marker
    raise MarkerCloseError("marker_not_found")
