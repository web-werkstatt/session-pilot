from services.db_service import ensure_session_review_schema, execute


def marker_summary(marker):
    return {
        "marker_id": marker.marker_id,
        "titel": marker.titel,
        "status": marker.status,
        "ziel": getattr(marker, "ziel", "") or "",
        "naechster_schritt": getattr(marker, "naechster_schritt", "") or "",
        "prompt": getattr(marker, "prompt", "") or "",
        "prompt_suggestion": getattr(marker, "prompt_suggestion", "") or "",
        "risiko": getattr(marker, "risiko", "") or "",
        "checks": list(getattr(marker, "checks", []) or []),
        "last_session": getattr(marker, "last_session", "") or "",
        "execution_score": marker.execution_score,
        "sprint_tag": getattr(marker, "sprint_tag", "") or "",
        "spec_tag": getattr(marker, "spec_tag", "") or "",
        "sessions": list(getattr(marker, "_planning_sessions", []) or []),
    }


def format_duration_ms(duration_ms):
    try:
        total_ms = int(duration_ms or 0)
    except (TypeError, ValueError):
        total_ms = 0
    total_seconds = max(total_ms // 1000, 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"


def serialize_session_row(row):
    if not row:
        return None
    return {
        "session_uuid": row.get("session_uuid"),
        "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
        "duration_ms": row.get("duration_ms") or 0,
        "duration_label": format_duration_ms(row.get("duration_ms")),
        "model": row.get("model") or "",
        "outcome": row.get("outcome") or "",
        "slug": row.get("slug") or "",
    }


def load_sessions_for_markers(project_id, markers):
    session_ids = sorted({
        str(getattr(marker, "last_session", "") or "").strip()
        for marker in (markers or [])
        if str(getattr(marker, "last_session", "") or "").strip()
    })
    if not session_ids:
        return {}
    ensure_session_review_schema()
    rows = execute(
        """SELECT session_uuid, started_at, duration_ms, model, outcome, slug
           FROM sessions
           WHERE session_uuid = ANY(%s)
             AND (
                 project_name = %s
                 OR project_name = REPLACE(%s, '_', '-')
                 OR cwd LIKE %s
             )
           ORDER BY started_at DESC NULLS LAST""",
        (session_ids, project_id, project_id, f"%/{project_id}"),
        fetch=True,
    ) or []
    return {
        str(row.get("session_uuid") or "").strip(): serialize_session_row(row)
        for row in rows
        if str(row.get("session_uuid") or "").strip()
    }


def attach_session_refs_to_markers(project_id, markers):
    session_map = load_sessions_for_markers(project_id, markers)
    for marker in markers or []:
        session_id = str(getattr(marker, "last_session", "") or "").strip()
        session_summary = session_map.get(session_id)
        marker._planning_sessions = [session_summary] if session_summary else []
    return markers


def load_recent_project_sessions(project_id, limit=5):
    if not project_id:
        return []
    ensure_session_review_schema()
    rows = execute(
        """SELECT session_uuid, started_at, duration_ms, model, outcome, slug
           FROM sessions
           WHERE (
               project_name = %s
               OR project_name = REPLACE(%s, '_', '-')
               OR cwd LIKE %s
           )
           ORDER BY started_at DESC NULLS LAST
           LIMIT %s""",
        (project_id, project_id, f"%/{project_id}", int(limit)),
        fetch=True,
    ) or []
    return [serialize_session_row(row) for row in rows if row]


def build_task_items(tasks, markers):
    marker_lookup = {}
    for marker in markers or []:
        title = str(getattr(marker, "titel", "") or "").strip().lower()
        if title and title not in marker_lookup:
            marker_lookup[title] = marker
    items = []
    for task in list(tasks or []):
        task_title = str(task or "").strip()
        matched_marker = marker_lookup.get(task_title.lower())
        items.append({
            "title": task_title,
            "sessions": list(getattr(matched_marker, "_planning_sessions", []) or []) if matched_marker else [],
            "marker_id": getattr(matched_marker, "marker_id", "") if matched_marker else "",
            "status": getattr(matched_marker, "status", "") if matched_marker else "",
        })
    return items


def collect_session_summaries(*collections):
    seen = set()
    result = []
    for collection in collections:
        for item in list(collection or []):
            session_id = str((item or {}).get("session_uuid") or "").strip()
            if not session_id or session_id in seen:
                continue
            seen.add(session_id)
            result.append(item)
    result.sort(key=lambda item: item.get("started_at") or "", reverse=True)
    return result
