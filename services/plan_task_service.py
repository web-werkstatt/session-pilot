"""
Sprint sprint-task-entity-und-drilldown (2026-04-15):
Service-Schicht fuer plan_tasks als eigenstaendige DB-Entitaet.

Patterns:
- Surrogate-ID (plan_tasks.id SERIAL) als stabile Identitaet.
- parse_key = section_key:spec_key:normalized_title fuer deterministisches
  Matching beim Markdown-Re-Parse. UPSERT via ON CONFLICT.
- Rename im UI aendert nur `title`, `parse_key` bleibt stabil => Marker
  bleiben verknuepft.
- Task-Status abgeleitet aus Marker-Status, nicht persistiert.
- Verwaiste Tasks (nicht mehr im Parse) bleiben in DB; `last_parsed_at`
  bleibt alt und kann Cleanup spaeter identifizieren.
"""
import re

from services.db_service import ensure_plan_task_schema, execute


def _normalize_title(title):
    lowered = str(title or "").strip().lower()
    return re.sub(r"\s+", " ", lowered)


def _task_title(task):
    """Akzeptiert sowohl Strings (rohes Markdown) als auch dicts
    (build_task_items-Output {title, sessions, marker_id, status})."""
    if isinstance(task, dict):
        return str(task.get("title") or "").strip()
    return str(task or "").strip()


def _build_parse_key(section_key, spec_key, normalized_title):
    return f"{section_key or ''}:{spec_key or ''}:{normalized_title or ''}"


def derive_task_status(markers_for_task):
    """Leitet Task-Status aus Marker-Status ab (open/in_progress/done)."""
    if not markers_for_task:
        return "open"
    statuses = {
        str(getattr(m, "status", None) or (m.get("status") if isinstance(m, dict) else "") or "").strip().lower()
        for m in markers_for_task
    }
    statuses.discard("")
    if statuses and statuses <= {"done"}:
        return "done"
    if "in_progress" in statuses or "active" in statuses:
        return "in_progress"
    return "open"


def upsert_tasks_for_plan(plan_id, sections):
    """
    Persistiert alle Tasks eines Plans.

    `sections` ist eine Liste aus `derive_tagged_plan_sections()`-Format:
    [{sprint_tag, tasks: [str, ...], specs: [{spec_tag, tasks: [str, ...]}]}]

    UPSERT via parse_key. Idempotent — zweiter Call ohne Aenderung erzeugt
    keine neuen Zeilen, aktualisiert nur `last_parsed_at`.
    Verwaiste Tasks bleiben erhalten (ON DELETE SET NULL schuetzt Marker).

    Returns: dict {parse_key: task_id} fuer den aktuellen Parse.
    """
    ensure_plan_task_schema()
    if plan_id is None:
        return {}

    result = {}
    order_counter = 0

    for section in sections or []:
        section_key = str(section.get("sprint_tag") or section.get("id") or "").strip().lstrip("#")
        if not section_key:
            continue

        for task_entry in section.get("tasks") or []:
            title = _task_title(task_entry)
            if not title:
                continue
            normalized = _normalize_title(title)
            parse_key = _build_parse_key(section_key, "", normalized)
            task_id = _upsert_single_task(
                plan_id=plan_id,
                section_key=section_key,
                spec_key="",
                title=title,
                normalized_title=normalized,
                parse_key=parse_key,
                order_index=order_counter,
                body=title,
            )
            if task_id is not None:
                result[parse_key] = task_id
            order_counter += 1

        for spec in section.get("specs") or []:
            spec_key = str(spec.get("spec_tag") or spec.get("id") or "").strip().lstrip("#")
            for task_entry in spec.get("tasks") or []:
                title = _task_title(task_entry)
                if not title:
                    continue
                normalized = _normalize_title(title)
                parse_key = _build_parse_key(section_key, spec_key, normalized)
                task_id = _upsert_single_task(
                    plan_id=plan_id,
                    section_key=section_key,
                    spec_key=spec_key,
                    title=title,
                    normalized_title=normalized,
                    parse_key=parse_key,
                    order_index=order_counter,
                    body=title,
                )
                if task_id is not None:
                    result[parse_key] = task_id
                order_counter += 1

    return result


def _upsert_single_task(plan_id, section_key, spec_key, title, normalized_title, parse_key, order_index, body):
    row = execute(
        """
        INSERT INTO plan_tasks
            (plan_id, section_key, spec_key, title, normalized_title, parse_key, order_index, body, last_parsed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (plan_id, parse_key) DO UPDATE SET
            title = EXCLUDED.title,
            order_index = EXCLUDED.order_index,
            body = EXCLUDED.body,
            last_parsed_at = NOW(),
            updated_at = NOW()
        RETURNING id
        """,
        (plan_id, section_key, spec_key, title, normalized_title, parse_key, order_index, body),
        fetchone=True,
    )
    return row["id"] if row else None


def list_tasks_for_plan(plan_id, include_status=True):
    """Liefert alle Tasks eines Plans mit Marker-Count + abgeleitetem Status."""
    ensure_plan_task_schema()
    if plan_id is None:
        return []
    rows = execute(
        """
        SELECT t.id, t.plan_id, t.section_key, t.spec_key, t.title,
               t.normalized_title, t.parse_key, t.order_index, t.body,
               t.created_at, t.updated_at, t.last_parsed_at,
               COUNT(m.id) AS marker_count
        FROM plan_tasks t
        LEFT JOIN markers m ON m.task_id = t.id
        WHERE t.plan_id = %s
        GROUP BY t.id
        ORDER BY t.section_key, t.spec_key, t.order_index, t.id
        """,
        (plan_id,),
        fetch=True,
    ) or []
    return [_serialize_task_row(row, include_status=include_status) for row in rows]


def list_tasks_for_section(plan_id, section_key, include_status=True):
    """Liefert Tasks einer einzelnen Section."""
    ensure_plan_task_schema()
    if plan_id is None or not section_key:
        return []
    normalized_section = str(section_key or "").strip().lstrip("#")
    rows = execute(
        """
        SELECT t.id, t.plan_id, t.section_key, t.spec_key, t.title,
               t.normalized_title, t.parse_key, t.order_index, t.body,
               t.created_at, t.updated_at, t.last_parsed_at,
               COUNT(m.id) AS marker_count
        FROM plan_tasks t
        LEFT JOIN markers m ON m.task_id = t.id
        WHERE t.plan_id = %s AND t.section_key = %s
        GROUP BY t.id
        ORDER BY t.spec_key, t.order_index, t.id
        """,
        (plan_id, normalized_section),
        fetch=True,
    ) or []
    return [_serialize_task_row(row, include_status=include_status) for row in rows]


def get_task(task_id):
    """Einzelner Task als dict + Marker-Count + abgeleiteter Status."""
    ensure_plan_task_schema()
    if task_id is None:
        return None
    row = execute(
        """
        SELECT t.id, t.plan_id, t.section_key, t.spec_key, t.title,
               t.normalized_title, t.parse_key, t.order_index, t.body,
               t.created_at, t.updated_at, t.last_parsed_at,
               COUNT(m.id) AS marker_count
        FROM plan_tasks t
        LEFT JOIN markers m ON m.task_id = t.id
        WHERE t.id = %s
        GROUP BY t.id
        """,
        (task_id,),
        fetchone=True,
    )
    return _serialize_task_row(row, include_status=True) if row else None


def get_markers_for_task(task_id):
    """Liefert alle Marker, die `task_id` referenzieren."""
    ensure_plan_task_schema()
    if task_id is None:
        return []
    rows = execute(
        """
        SELECT id, project_name, marker_id, titel, status, plan_id,
               execution_score, implementation_percent, sprint_tag, spec_tag,
               updated_at
        FROM markers
        WHERE task_id = %s
        ORDER BY id
        """,
        (task_id,),
        fetch=True,
    ) or []
    return [dict(row) for row in rows]


def rename_task(task_id, new_title):
    """UI-Rename: nur `title` + `normalized_title` aendern, `parse_key` bleibt.

    So bleibt die Marker-Verknuepfung stabil auch nach Umbenennung im UI.
    Ein spaeteres Markdown-Re-Parse mit dem alten Titel wird den Task
    weiterhin matchen (parse_key unveraendert), obwohl der UI-Titel abweicht
    — bewusster Trade-off (UI-Wahrheit vs. Markdown-Wahrheit).
    """
    ensure_plan_task_schema()
    if task_id is None:
        return None
    clean_title = str(new_title or "").strip()
    if not clean_title:
        return None
    row = execute(
        """
        UPDATE plan_tasks
        SET title = %s, normalized_title = %s, updated_at = NOW()
        WHERE id = %s
        RETURNING id, title, normalized_title, parse_key
        """,
        (clean_title, _normalize_title(clean_title), task_id),
        fetchone=True,
    )
    return dict(row) if row else None


def find_task_by_parse_key(plan_id, section_key, spec_key, title):
    """Lookup fuer Marker-Import: gib task_id zurueck, wenn Match existiert."""
    ensure_plan_task_schema()
    if plan_id is None:
        return None
    normalized = _normalize_title(title)
    parse_key = _build_parse_key(
        str(section_key or "").strip().lstrip("#"),
        str(spec_key or "").strip().lstrip("#"),
        normalized,
    )
    row = execute(
        "SELECT id FROM plan_tasks WHERE plan_id = %s AND parse_key = %s",
        (plan_id, parse_key),
        fetchone=True,
    )
    return row["id"] if row else None


def _serialize_task_row(row, include_status=True):
    if not row:
        return None
    data = {
        "id": row["id"],
        "plan_id": row["plan_id"],
        "section_key": row.get("section_key") or "",
        "spec_key": row.get("spec_key") or "",
        "title": row.get("title") or "",
        "normalized_title": row.get("normalized_title") or "",
        "parse_key": row.get("parse_key") or "",
        "order_index": row.get("order_index") or 0,
        "body": row.get("body") or "",
        "marker_count": int(row.get("marker_count") or 0),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "last_parsed_at": row["last_parsed_at"].isoformat() if row.get("last_parsed_at") else None,
    }
    if include_status:
        markers = get_markers_for_task(row["id"]) if data["marker_count"] else []
        data["status"] = derive_task_status(markers)
    return data
