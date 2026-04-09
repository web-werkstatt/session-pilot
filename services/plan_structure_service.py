"""Explizite Struktur fuer Plan -> Sprint-Plan -> Spec -> Marker."""
import json
import os
import re

from services.copilot_marker_service import parse_markers
from services.db_service import ensure_plan_structure_schema, ensure_session_review_schema, execute
from services.markdown_routine_service import scan_markdown_structure
from services.path_resolver import resolve_project_path
from services.plan_structure_helpers import (
    build_task_items,
    collect_session_summaries,
    marker_summary,
    serialize_session_row,
)
def _slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "item"

def _normalize_sprint_plan_id(title):
    title = str(title or "").strip()
    match = re.match(r"^Sprint\s+([A-Za-z0-9.\-]+)", title, re.IGNORECASE)
    token = match.group(1) if match else title
    return f"sprint-{_slugify(token)}"

def _extract_heading_title(raw_title):
    parts = [part.strip() for part in re.split(r"\s+[—-]\s+", str(raw_title or "").strip()) if part.strip()]
    if not parts:
        return "", "", "planned"
    sprint_label = parts[0]
    status = "planned"
    if parts[-1].lower() in ("done", "active", "planned"):
        status = parts[-1].lower()
        parts = parts[:-1]
    title = " - ".join(parts[1:]).strip() if len(parts) > 1 else sprint_label
    return sprint_label, title or sprint_label, status

def _find_master_plan_path(project_id, master_plan_path=None):
    if master_plan_path:
        return master_plan_path
    project_root = resolve_project_path(project_id) or os.getcwd()
    sprint_dir = os.path.join(project_root, "sprints")
    if not os.path.isdir(sprint_dir):
        raise FileNotFoundError("master_plan_missing")
    candidates = sorted(
        os.path.join(sprint_dir, name)
        for name in os.listdir(sprint_dir)
        if name.startswith("master-plan-") and name.endswith(".md")
    )
    if not candidates:
        raise FileNotFoundError("master_plan_missing")
    return candidates[-1]

def _first_description_line(lines):
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return re.sub(r"^(?:[-*]|\d+\.)\s+", "", stripped)
    return ""


def _load_project_meta(project_id):
    project_root = resolve_project_path(project_id)
    if not project_root:
        return {}
    project_json = os.path.join(project_root, "project.json")
    if not os.path.exists(project_json):
        return {}
    try:
        with open(project_json, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_planning_project_id(project_id):
    meta = _load_project_meta(project_id)
    if meta.get("project_type") == "subproject" and meta.get("parent_project"):
        return str(meta.get("parent_project")).strip() or project_id
    return project_id


def load_recent_project_sessions(project_id, limit=5):
    if not project_id:
        return []
    ensure_session_review_schema()
    rows = execute(
        """SELECT session_uuid, started_at, duration_ms, model, outcome, slug,
                  account, total_input_tokens, total_output_tokens
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
        """SELECT session_uuid, started_at, duration_ms, model, outcome, slug,
                  account, total_input_tokens, total_output_tokens
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


def derive_tagged_plan_sections(content, markers=None, source_path="", project_id=""):
    """Leitet Plan -> Sprint -> Spec -> Marker direkt aus Markdown + Marker-Tags ab."""
    structure = scan_markdown_structure(content or "", source_path)
    markers = attach_session_refs_to_markers(project_id, markers or [])
    sections = []

    for sprint in structure.get("sprints") or []:
        sprint_tag = str(sprint.get("sprint_tag") or "").strip()
        sprint_plan_id = str(sprint.get("plan_id") or "").strip()
        sprint_markers = [
            marker for marker in markers
            if (
                sprint_tag and str(getattr(marker, "sprint_tag", "") or "").strip() == sprint_tag
            ) or (
                not getattr(marker, "sprint_tag", "") and sprint_plan_id and str(marker.plan_id or "").strip() == sprint_plan_id
            )
        ]

        specs = []
        direct_markers = []
        for marker in sprint_markers:
            marker_spec_tag = str(getattr(marker, "spec_tag", "") or "").strip()
            if not marker_spec_tag:
                direct_markers.append(marker_summary(marker))

        for spec in sprint.get("specs") or []:
            spec_tag = str(spec.get("spec_tag") or "").strip()
            matched_spec_markers = [
                marker
                for marker in sprint_markers
                if spec_tag and str(getattr(marker, "spec_tag", "") or "").strip() == spec_tag
            ]
            spec_markers = [
                marker_summary(marker)
                for marker in matched_spec_markers
            ]
            task_items = build_task_items(spec.get("tasks") or [], matched_spec_markers)
            specs.append({
                "id": spec_tag or ("spec:" + re.sub(r"[^a-z0-9]+", "-", str(spec.get("title") or "").lower()).strip("-")),
                "title": spec.get("title") or "",
                "summary": spec.get("description") or "",
                "spec_tag": spec_tag,
                "tasks": task_items,
                "markers": spec_markers,
                "sessions": collect_session_summaries(
                    [session for marker in spec_markers for session in list(marker.get("sessions") or [])],
                    [session for task in task_items for session in list(task.get("sessions") or [])],
                ),
            })
        direct_task_items = build_task_items(sprint.get("tasks") or [], [
            marker
            for marker in sprint_markers
            if not str(getattr(marker, "spec_tag", "") or "").strip()
        ])

        sections.append({
            "id": sprint_tag or ("sprint:" + sprint_plan_id) or ("sprint-line-" + str(sprint.get("line") or len(sections) + 1)),
            "title": sprint.get("title") or "",
            "summary": sprint.get("description") or "",
            "body": "\n".join(sprint.get("lines") or []).strip(),
            "plan_id": sprint_plan_id,
            "sprint_tag": sprint_tag,
            "tasks": direct_task_items,
            "markers": [marker_summary(marker) for marker in sprint_markers],
            "direct_markers": direct_markers,
            "specs": specs,
            "sessions": collect_session_summaries(
                [session for marker in direct_markers for session in list(marker.get("sessions") or [])],
                [session for task in direct_task_items for session in list(task.get("sessions") or [])],
                [session for spec in specs for session in list(spec.get("sessions") or [])],
            ),
        })

    return sections


def _upsert_sprint_plan(project_id, plan_id, title, status, sprint_file, anchor, parent_plan_id=None):
    existing = execute(
        "SELECT * FROM sprint_plans WHERE project_id = %s AND plan_id = %s",
        (project_id, plan_id),
        fetchone=True,
    )
    if existing:
        execute(
            """UPDATE sprint_plans
               SET title = %s, status = %s, parent_plan_id = %s, sprint_file = %s, anchor = %s, updated_at = NOW()
               WHERE id = %s""",
            (title, status, parent_plan_id, sprint_file, anchor, existing["id"]),
        )
        existing["title"] = title
        existing["status"] = status
        existing["parent_plan_id"] = parent_plan_id
        existing["sprint_file"] = sprint_file
        existing["anchor"] = anchor
        return existing["id"]

    row = execute(
        """INSERT INTO sprint_plans (project_id, plan_id, title, status, parent_plan_id, sprint_file, anchor)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (project_id, plan_id, title, status, parent_plan_id, sprint_file, anchor),
        fetchone=True,
    )
    return row["id"]


def _upsert_spec(sprint_plan_id, anchor, title, description, status):
    existing = execute(
        "SELECT * FROM specs WHERE sprint_plan_id = %s AND anchor = %s",
        (sprint_plan_id, anchor),
        fetchone=True,
    )
    if existing:
        execute(
            """UPDATE specs
               SET title = %s, description = %s, status = %s, updated_at = NOW()
               WHERE id = %s""",
            (title, description, status, existing["id"]),
        )
        existing["title"] = title
        existing["description"] = description
        existing["status"] = status
        return existing["id"]

    row = execute(
        """INSERT INTO specs (sprint_plan_id, anchor, title, description, status)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING id""",
        (sprint_plan_id, anchor, title, description, status),
        fetchone=True,
    )
    return row["id"]


def sync_sprint_plans_from_master(project_id, master_plan_path=None):
    ensure_plan_structure_schema()
    resolved_path = _find_master_plan_path(project_id, master_plan_path)
    with open(resolved_path, "r", encoding="utf-8") as f:
        content = f.read()

    parsed = scan_markdown_structure(content, resolved_path)
    sections = parsed.get("sprints") or []
    synced = []
    for section in sections:
        raw_title = section.get("raw_title") or section.get("title") or ""
        sprint_label, title, status = _extract_heading_title(raw_title)
        plan_id = str(section.get("sprint_tag") or "").strip().lstrip("#") or str(section.get("plan_id") or "").strip() or _normalize_sprint_plan_id(sprint_label)
        sprint_plan_id = _upsert_sprint_plan(
            project_id,
            plan_id,
            title,
            status,
            resolved_path,
            anchor=_slugify(raw_title),
            parent_plan_id=None,
        )
        synced.append({
            "id": sprint_plan_id,
            "plan_id": plan_id,
            "title": title,
            "status": status,
            "sprint_file": resolved_path,
        })
    return synced


def sync_specs_from_sprint_plan(sprint_plan_id):
    ensure_plan_structure_schema()
    sprint_plan = execute(
        "SELECT * FROM sprint_plans WHERE id = %s",
        (sprint_plan_id,),
        fetchone=True,
    )
    if not sprint_plan:
        return []

    if not sprint_plan.get("sprint_file") or not os.path.exists(sprint_plan["sprint_file"]):
        raise FileNotFoundError("sprint_file_missing")

    with open(sprint_plan["sprint_file"], "r", encoding="utf-8") as f:
        content = f.read()

    parsed = scan_markdown_structure(content, sprint_plan["sprint_file"])
    matching = next(
        (
            section for section in (parsed.get("sprints") or [])
            if str(section.get("sprint_tag") or "").strip().lstrip("#") == str(sprint_plan["plan_id"]).strip()
            or str(section.get("plan_id") or "").strip() == str(sprint_plan["plan_id"]).strip()
        ),
        None,
    )
    if not matching:
        return []

    synced = []
    subsection_matches = matching.get("specs") or []
    if not subsection_matches:
        spec_id = _upsert_spec(
            sprint_plan_id,
            "overview",
            sprint_plan["title"],
            _first_description_line(matching["lines"]) or sprint_plan["title"],
            sprint_plan.get("status") or "planned",
        )
        synced.append({
            "id": spec_id,
            "anchor": "overview",
            "title": sprint_plan["title"],
        })
        return synced

    for section in subsection_matches:
        anchor = str(section.get("spec_tag") or "").strip().lstrip("#") or _slugify(section["title"])
        description = section.get("description") or _first_description_line(section.get("lines") or []) or section["title"]
        spec_id = _upsert_spec(
            sprint_plan_id,
            anchor,
            section["title"],
            description,
            sprint_plan.get("status") or "planned",
        )
        synced.append({
            "id": spec_id,
            "anchor": anchor,
            "title": section["title"],
            "description": description,
        })
    return synced


def resolve_marker_structure_refs(project_id, sprint_plan_token, spec_title=None, spec_tag=None):
    ensure_plan_structure_schema()
    if not project_id or not sprint_plan_token:
        return None, None
    sprint_plan = execute(
        "SELECT * FROM sprint_plans WHERE project_id = %s AND plan_id = %s",
        (project_id, str(sprint_plan_token).strip()),
        fetchone=True,
    )
    if not sprint_plan:
        return None, None
    spec_id = None
    normalized_spec_tag = str(spec_tag or "").strip().lstrip("#")
    if normalized_spec_tag:
        spec = execute(
            """SELECT * FROM specs
               WHERE sprint_plan_id = %s AND LOWER(anchor) = LOWER(%s)
               ORDER BY id ASC LIMIT 1""",
            (sprint_plan["id"], normalized_spec_tag),
            fetchone=True,
        )
        if spec:
            spec_id = spec["id"]
    if spec_id is None and spec_title:
        spec = execute(
            """SELECT * FROM specs
               WHERE sprint_plan_id = %s AND LOWER(title) = LOWER(%s)
               ORDER BY id ASC LIMIT 1""",
            (sprint_plan["id"], str(spec_title).strip()),
            fetchone=True,
        )
        if spec:
            spec_id = spec["id"]
    return sprint_plan["id"], spec_id


def get_plan_structure(project_id, handoff_path=None):
    ensure_plan_structure_schema()
    try:
        sync_sprint_plans_from_master(project_id)
    except FileNotFoundError:
        pass
    sprint_rows = execute(
        "SELECT * FROM sprint_plans WHERE project_id = %s ORDER BY updated_at DESC, id DESC",
        (project_id,),
        fetch=True,
    ) or []
    markers = parse_markers(handoff_path) if handoff_path and os.path.exists(handoff_path) else []

    items = []
    for sprint in sprint_rows:
        spec_rows = execute(
            "SELECT * FROM specs WHERE sprint_plan_id = %s ORDER BY id ASC",
            (sprint["id"],),
            fetch=True,
        ) or []
        sprint_markers = [
            m for m in markers
            if str(getattr(m, "sprint_tag", "") or "").strip().lstrip("#") == str(sprint["plan_id"]).strip()
            or (
                not getattr(m, "sprint_tag", "")
                and str(m.plan_id or "").strip() == str(sprint["plan_id"]).strip()
            )
        ]
        items.append({
            "id": sprint["id"],
            "plan_id": sprint["plan_id"],
            "title": sprint["title"],
            "status": sprint["status"],
            "sprint_file": sprint.get("sprint_file"),
            "spec_count": len(spec_rows),
            "marker_count": len(sprint_markers),
            "open_marker_count": len([m for m in sprint_markers if m.status != "done"]),
        })
    return items


def get_tagged_plan_structure(content, handoff_path=None, source_path=""):
    markers = parse_markers(handoff_path) if handoff_path and os.path.exists(handoff_path) else []
    project_id = ""
    if handoff_path and os.path.exists(handoff_path):
        project_id = os.path.basename(os.path.dirname(handoff_path))
    return derive_tagged_plan_sections(content, markers, source_path=source_path, project_id=project_id)


def get_sprint_plan_detail(sprint_plan_id, handoff_path=None):
    ensure_plan_structure_schema()
    sprint = execute(
        "SELECT * FROM sprint_plans WHERE id = %s",
        (sprint_plan_id,),
        fetchone=True,
    )
    if not sprint:
        return None

    sync_specs_from_sprint_plan(sprint_plan_id)
    spec_rows = execute(
        "SELECT * FROM specs WHERE sprint_plan_id = %s ORDER BY id ASC",
        (sprint_plan_id,),
        fetch=True,
    ) or []
    markers = parse_markers(handoff_path) if handoff_path and os.path.exists(handoff_path) else []
    sprint_markers = [
        m for m in markers
        if str(getattr(m, "sprint_tag", "") or "").strip().lstrip("#") == str(sprint["plan_id"]).strip()
        or (
            not getattr(m, "sprint_tag", "")
            and str(m.plan_id or "").strip() == str(sprint["plan_id"]).strip()
        )
    ]

    spec_items = []
    for spec in spec_rows:
        matched = [
            marker for marker in sprint_markers
            if getattr(marker, "spec_id", None) == spec["id"]
            or str(getattr(marker, "spec_tag", "") or "").strip().lstrip("#") == str(spec.get("anchor") or "").strip()
        ]
        spec_items.append({
            "id": spec["id"],
            "anchor": spec.get("anchor"),
            "title": spec["title"],
            "description": spec.get("description") or "",
            "status": spec.get("status") or "planned",
            "markers": [
                {
                    "marker_id": marker.marker_id,
                    "titel": marker.titel,
                    "status": marker.status,
                    "execution_score": marker.execution_score,
                }
                for marker in matched
            ],
        })

    direct_markers = [
        {
            "marker_id": marker.marker_id,
            "titel": marker.titel,
            "status": marker.status,
            "execution_score": marker.execution_score,
        }
        for marker in sprint_markers
        if getattr(marker, "spec_id", None) is None and not str(getattr(marker, "spec_tag", "") or "").strip()
    ]

    return {
        "sprint_plan": {
            "id": sprint["id"],
            "plan_id": sprint["plan_id"],
            "title": sprint["title"],
            "status": sprint["status"],
            "sprint_file": sprint.get("sprint_file"),
        },
        "specs": spec_items,
        "direct_markers": direct_markers,
    }


def get_project_planning_hierarchy(project_id, handoff_path=None):
    """Liest die Projekt-Hierarchie fuer den Planning-Workspace read-only aus."""
    ensure_plan_structure_schema()
    planning_project_id = resolve_planning_project_id(project_id)
    rows = execute(
        """SELECT id, title, project_name, context_summary, content, category, status,
                  workflow_stage, current_state, target_state, next_action,
                  created_at, updated_at
           FROM project_plans
           WHERE project_name = %s
           ORDER BY created_at DESC, id DESC""",
        (planning_project_id,),
        fetch=True,
    ) or []

    recent_project_sessions = load_recent_project_sessions(planning_project_id, limit=10)
    hierarchy = []
    for row in rows:
        sections = get_tagged_plan_structure(
            row.get("content") or "",
            handoff_path=handoff_path,
            source_path=row.get("title") or f"plan:{row['id']}",
        )
        hierarchy.append({
            "plan": {
                "id": row["id"],
                "title": row.get("title") or f"Plan {row['id']}",
                "project_name": row.get("project_name"),
                "summary": row.get("context_summary") or "",
                "category": row.get("category") or "plan",
                "status": row.get("status") or "draft",
                "workflow_stage": row.get("workflow_stage") or "idea",
                "current_state": row.get("current_state") or "",
                "target_state": row.get("target_state") or "",
                "next_action": row.get("next_action") or "",
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
            },
            "sprints": sections,
            "recent_sessions": recent_project_sessions,
            "stats": {
                "sprint_count": len(sections),
                "spec_count": sum(len(section.get("specs") or []) for section in sections),
                "direct_task_count": sum(len(section.get("tasks") or []) for section in sections),
                "direct_marker_count": sum(len(section.get("direct_markers") or []) for section in sections),
            },
        })
    return hierarchy
