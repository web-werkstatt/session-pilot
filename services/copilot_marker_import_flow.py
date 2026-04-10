"""
Import- und Mapping-Flow fuer Sprint-/Plan-Marker.
"""
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone

from services.copilot_marker_format import Marker, parse_markers, _write_marker
from services.markdown_routine_service import scan_markdown_structure


def _sync_to_db(handoff_path):
    """Synchronisiert neue/geaenderte Marker aus handoff.md in die DB."""
    try:
        project_name = os.path.basename(os.path.dirname(handoff_path))
        if project_name:
            from services.marker_importer import import_markers_from_handoff
            import_markers_from_handoff(project_name)
    except Exception:
        pass


_PLAN_ID_LINE_RE = re.compile(r"plan-id:\*+\s*(?P<plan_id>[^\s*]+)|plan-id:\s*(?P<plan_id_plain>[^\s*]+)", re.IGNORECASE)
_TASK_BULLET_RE = re.compile(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(?P<task>.+?)\s*$")


def _normalize_marker_title(title):
    return re.sub(r"\s+", " ", str(title or "").strip()).lower()


def _slugify_marker_part(value):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "marker"


def _build_sprint_marker_id(plan_id, title):
    return f"{_slugify_marker_part(plan_id)}-{_slugify_marker_part(title)}"


def _read_sprint_content(sprint_path):
    resolved = str(sprint_path or "").strip()
    if not resolved:
        raise FileNotFoundError("sprint_missing")
    if not os.path.isabs(resolved):
        resolved = os.path.abspath(resolved)
    if os.path.exists(resolved):
        with open(resolved, "r", encoding="utf-8") as f:
            return resolved, f.read()

    plan_token = os.path.splitext(os.path.basename(resolved))[0]
    for base in [os.path.join(os.getcwd(), "upload", "Sprints"), os.path.join(os.getcwd(), "sprints")]:
        if not os.path.isdir(base):
            continue
        for filename in sorted(os.listdir(base)):
            if plan_token in filename or plan_token.replace("_", "-") in filename:
                candidate = os.path.join(base, filename)
                with open(candidate, "r", encoding="utf-8") as f:
                    return candidate, f.read()
    raise FileNotFoundError(resolved)


def _extract_tasks_from_sprint(sprint_path, plan_id):
    resolved_path, content = _read_sprint_content(sprint_path)
    return _extract_tasks_from_content(content, plan_id, resolved_path)


def _extract_tasks_from_content(content, plan_id, source_label):
    lines = content.splitlines()
    plan_id = str(plan_id).strip()
    structure = scan_markdown_structure(content, source_label)
    matched_sprint = None
    for sprint in structure.get("sprints") or []:
        sprint_plan_id = str(sprint.get("plan_id") or "").strip()
        sprint_tag = str(sprint.get("sprint_tag") or "").strip()
        if sprint_plan_id == plan_id or sprint_tag.lstrip("#") == plan_id.lstrip("#"):
            matched_sprint = sprint
            break

    if matched_sprint:
        task_items = [{"title": task, "spec_title": "", "sprint_tag": matched_sprint.get("sprint_tag") or "", "spec_tag": ""} for task in matched_sprint.get("tasks") or []]
        for spec in matched_sprint.get("specs") or []:
            for task in spec.get("tasks") or []:
                task_items.append({
                    "title": task,
                    "spec_title": spec.get("title") or "",
                    "sprint_tag": matched_sprint.get("sprint_tag") or "",
                    "spec_tag": spec.get("spec_tag") or "",
                })
        tasks = [item["title"] for item in task_items if item.get("title")]
        if tasks:
            return {"sprint_path": source_label, "sprint_title": matched_sprint.get("title") or plan_id, "sprint_tag": matched_sprint.get("sprint_tag") or "", "tasks": tasks, "task_items": task_items}

    plan_line_idx = None
    for idx, line in enumerate(lines):
        match = _PLAN_ID_LINE_RE.search(line)
        matched_plan_id = (match.group("plan_id") or match.group("plan_id_plain") or "").strip() if match else ""
        if matched_plan_id == plan_id:
            plan_line_idx = idx
            break
    if plan_line_idx is None:
        raise ValueError("plan_id_not_found")

    section_start = 0
    section_level = 1
    for idx in range(plan_line_idx, -1, -1):
        stripped = lines[idx].strip()
        if stripped.startswith("#"):
            section_start = idx
            section_level = len(stripped) - len(stripped.lstrip("#"))
            break

    section_end = len(lines)
    for idx in range(plan_line_idx + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith("#") and len(stripped) - len(stripped.lstrip("#")) <= section_level:
            section_end = idx
            break

    section_lines = lines[section_start:section_end]
    sprint_title = lines[section_start].strip().lstrip("#").strip() if lines[section_start].strip().startswith("#") else plan_id
    tasks_start = None
    tasks_heading_level = None
    for idx, line in enumerate(section_lines):
        stripped = line.strip()
        if stripped.startswith("#") and "aufgaben" in stripped.lower():
            tasks_start = idx + 1
            tasks_heading_level = len(stripped) - len(stripped.lstrip("#"))
            break
        if stripped.lower().startswith("aufgaben:"):
            tasks_start = idx + 1
            break

    search_lines = section_lines[tasks_start:] if tasks_start is not None else section_lines
    tasks = []
    task_items = []
    current_spec = ""
    for line in search_lines:
        stripped = line.strip()
        if tasks_heading_level is not None and stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= tasks_heading_level:
                break
            current_spec = stripped.lstrip("#").strip()
            continue
        if stripped.startswith("#"):
            current_spec = stripped.lstrip("#").strip()
            continue
        match = _TASK_BULLET_RE.match(line)
        if not match:
            continue
        task = match.group("task").strip()
        if task:
            tasks.append(task)
            task_items.append({"title": task, "spec_title": current_spec, "sprint_tag": "", "spec_tag": ""})
    if not tasks:
        raise ValueError("tasks_not_found")
    return {"sprint_path": source_label, "sprint_title": sprint_title, "sprint_tag": "", "tasks": tasks, "task_items": task_items}


def buildsuggestion(marker, sprint_context):
    sprint_title = str((sprint_context or {}).get("sprint_title") or marker.plan_id).strip()
    sprint_name = os.path.basename(str((sprint_context or {}).get("sprint_path") or "")).strip()
    suggestion = f"Arbeite die Sprint-Aufgabe '{marker.titel}' aus {sprint_title} ab."
    if sprint_name:
        suggestion += f" Orientiere dich am Sprint-Plan in {sprint_name}."
    if marker.ziel and marker.ziel != marker.titel:
        suggestion += f" Ziel: {marker.ziel}."
    return suggestion.strip()


def _resolve_marker_refs(handoff_path, plan_id, task_item):
    try:
        from services.plan_structure_service import resolve_marker_structure_refs
        return resolve_marker_structure_refs(
            os.path.basename(os.path.dirname(handoff_path)) or "",
            plan_id,
            task_item.get("spec_title"),
            task_item.get("spec_tag"),
        )
    except Exception:
        return None, None


def _upsert_task_markers(sprint_context, plan_id, handoff_path):
    existing_markers = parse_markers(handoff_path)
    existing_by_id = {marker.marker_id: marker for marker in existing_markers}
    existing_by_title = {_normalize_marker_title(marker.titel): marker for marker in existing_markers if marker.plan_id == plan_id}
    written = []
    task_items = sprint_context.get("task_items") or [{"title": task, "spec_title": ""} for task in sprint_context["tasks"]]
    for task_item in task_items:
        task = task_item["title"]
        existing = existing_by_id.get(_build_sprint_marker_id(plan_id, task)) or existing_by_title.get(_normalize_marker_title(task))
        sprint_plan_id, spec_id = _resolve_marker_refs(handoff_path, plan_id, task_item)
        if existing:
            marker = Marker(**asdict(existing))
            marker.marker_id = existing.marker_id
            marker.titel = task
            marker.ziel = task
            marker.prompt_suggestion = buildsuggestion(marker, sprint_context)
            marker.updated_at = datetime.now(timezone.utc).isoformat()
            if sprint_plan_id is not None:
                marker.sprint_plan_id = sprint_plan_id
            if spec_id is not None:
                marker.spec_id = spec_id
            if task_item.get("sprint_tag"):
                marker.sprint_tag = str(task_item.get("sprint_tag")).strip()
            if task_item.get("spec_tag"):
                marker.spec_tag = str(task_item.get("spec_tag")).strip()
        else:
            marker = Marker(
                marker_id=_build_sprint_marker_id(plan_id, task),
                titel=task,
                plan_id=plan_id,
                status="todo",
                ziel=task,
                naechster_schritt="Sprint-Aufgabe im Detail ausarbeiten",
                prompt="",
                prompt_suggestion="",
                risiko="",
                checks=[],
                last_session="",
                updated_at=datetime.now(timezone.utc).isoformat(),
                sprint_tag=str(task_item.get("sprint_tag") or "").strip(),
                spec_tag=str(task_item.get("spec_tag") or "").strip(),
                sprint_plan_id=sprint_plan_id,
                spec_id=spec_id,
            )
            marker.prompt_suggestion = buildsuggestion(marker, sprint_context)
        _write_marker(handoff_path, marker)
        written.append(marker)
    return written


def sprinttomarkers(sprint_path, plan_id, handoff_path):
    plan_id = str(plan_id).strip()
    if not plan_id:
        raise ValueError("plan_id ist erforderlich")
    result = _upsert_task_markers(_extract_tasks_from_sprint(sprint_path, plan_id), plan_id, handoff_path)
    _sync_to_db(handoff_path)
    return result


def sprinttomarkers_from_content(content, plan_id, handoff_path, source_label="db_plan"):
    plan_id = str(plan_id).strip()
    if not plan_id:
        raise ValueError("plan_id ist erforderlich")
    result = _upsert_task_markers(_extract_tasks_from_content(str(content or ""), plan_id, source_label), plan_id, handoff_path)
    _sync_to_db(handoff_path)
    return result


def plan_to_marker(plan_id, handoff_path, *, title, context_summary="", next_action="", status="todo", source_label="db_plan"):
    plan_id = str(plan_id).strip()
    if not plan_id:
        raise ValueError("plan_id ist erforderlich")
    existing = next((marker for marker in parse_markers(handoff_path) if marker.marker_id == plan_id), None)
    prompt_suggestion = f"Arbeite an: {str(title or '').strip()}."
    if context_summary:
        prompt_suggestion += f" Kontext: {str(context_summary).strip()}"
    if next_action:
        prompt_suggestion += f" Naechster Schritt: {str(next_action).strip()}."
    if source_label:
        prompt_suggestion += f" Quelle: {source_label}."
    if existing:
        marker = Marker(**asdict(existing))
        marker.titel = str(title or existing.titel).strip() or existing.titel
        marker.ziel = str(context_summary or marker.ziel or marker.titel).strip() or marker.titel
        marker.naechster_schritt = str(next_action or marker.naechster_schritt).strip() or "Plan im Detail ausarbeiten"
        marker.prompt_suggestion = prompt_suggestion.strip()
        marker.updated_at = datetime.now(timezone.utc).isoformat()
    else:
        marker = Marker(
            marker_id=plan_id,
            titel=str(title or plan_id).strip() or plan_id,
            plan_id=plan_id,
            status=status,
            ziel=str(context_summary or title or plan_id).strip() or plan_id,
            naechster_schritt=str(next_action or "Plan im Detail ausarbeiten").strip(),
            prompt="",
            prompt_suggestion=prompt_suggestion.strip(),
            risiko="",
            checks=["Marker vor Ausfuehrung kurz gegen Plan-Kontext pruefen"],
            last_session="",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    _write_marker(handoff_path, marker)
    _sync_to_db(handoff_path)
    return [marker]
