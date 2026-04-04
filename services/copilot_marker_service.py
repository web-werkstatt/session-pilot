"""
Marker-Service fuer das handoff.md Dual-Format.

Wahrheitsquelle beim Einlesen ist der JSON-Block im HTML-Kommentar.
Der lesbare Markdown-Teil wird immer aus dem Marker-Objekt neu generiert.
"""
import json
import os
import re
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from typing import List

from config import PROJECTS_DIR
from services.path_resolver import resolve_project_path


VALID_STATUSES = {"todo", "in_progress", "done", "blocked"}
_PLAN_ID_LINE_RE = re.compile(r"plan-id:\*+\s*(?P<plan_id>[^\s*]+)|plan-id:\s*(?P<plan_id_plain>[^\s*]+)", re.IGNORECASE)
_TASK_BULLET_RE = re.compile(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(?P<task>.+?)\s*$")

_MARKER_BLOCK_RE = re.compile(
    r"""
    <!--\s*MARKER:(?P<marker_id>[^\s>]+)\s*
    (?P<json>\{.*?\})
    \s*-->
    \s*
    (?P<markdown>.*?)
    \n---\s*(?=\n|$)
    """,
    re.VERBOSE | re.DOTALL,
)


@dataclass(eq=True)
class Marker:
    marker_id: str
    titel: str
    plan_id: str
    status: str
    ziel: str
    naechster_schritt: str
    prompt: str
    prompt_suggestion: str = ""
    risiko: str = ""
    checks: List[str] = field(default_factory=list)
    last_session: str = ""
    updated_at: str = ""

    def __post_init__(self):
        self.marker_id = str(self.marker_id).strip()
        self.titel = str(self.titel or "").strip()
        self.plan_id = str(self.plan_id or "").strip()
        self.status = str(self.status or "").strip()
        self.ziel = str(self.ziel or "").strip()
        self.naechster_schritt = str(self.naechster_schritt or "").strip()
        self.prompt = "" if self.prompt is None else str(self.prompt)
        self.prompt_suggestion = "" if self.prompt_suggestion is None else str(self.prompt_suggestion).strip()
        self.risiko = "" if self.risiko is None else str(self.risiko).strip()
        self.last_session = "" if self.last_session is None else str(self.last_session).strip()
        self.updated_at = "" if self.updated_at is None else str(self.updated_at).strip()
        if not isinstance(self.checks, list):
            raise ValueError("checks muss eine Liste sein")
        self.checks = [str(item).strip() for item in self.checks if str(item).strip()]
        if not self.marker_id:
            raise ValueError("marker_id ist erforderlich")
        if not self.titel:
            raise ValueError("titel ist erforderlich")
        if not self.plan_id:
            raise ValueError("plan_id ist erforderlich")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"ungueltiger status: {self.status}")
        if not self.ziel:
            raise ValueError("ziel ist erforderlich")
        if not self.naechster_schritt:
            raise ValueError("naechster_schritt ist erforderlich")
        if self.prompt is None:
            raise ValueError("prompt ist erforderlich")


class MarkerActivationError(ValueError):
    """Fehler fuer blockierte oder ungueltige Marker-Aktivierung."""

    def __init__(self, message, gate_reason=""):
        super().__init__(message)
        self.gate_reason = gate_reason or message


class MarkerCloseError(ValueError):
    """Fehler fuer ungueltige oder nicht auffindbare Marker beim Session-Write-back."""


def _render_marker_markdown(marker):
    """Erzeugt den lesbaren Markdown-Teil fuer einen Marker."""
    prompt_text = marker.prompt.strip() if marker.prompt.strip() else "_(noch nicht gesetzt)_"
    if marker.checks:
        checks_text = "\n".join(f"- {item}" for item in marker.checks)
    else:
        checks_text = "_(noch keine)_"

    lines = [
        f"## {marker.titel} · {marker.status}",
        "",
        f"**Ziel:** {marker.ziel}",
        f"**Naechster Schritt:** {marker.naechster_schritt}",
        f"**Risiko:** {marker.risiko or '-'}",
        "",
        "**Prompt:**",
        prompt_text,
        "",
        "**Checks:**",
        checks_text,
        "",
    ]
    return "\n".join(lines)


def _serialize_marker(marker):
    """Serialisiert einen Marker als Dual-Format Block."""
    if not isinstance(marker, Marker):
        marker = Marker(**marker)

    payload = asdict(marker)
    json_block = json.dumps(payload, ensure_ascii=False, indent=2)
    markdown_block = _render_marker_markdown(marker)
    return f"<!-- MARKER:{marker.marker_id}\n{json_block}\n-->\n\n{markdown_block}\n---\n"


def parse_markers(handoff_path):
    """Parst alle Marker aus einer handoff.md."""
    if not os.path.exists(handoff_path):
        return []

    with open(handoff_path, "r", encoding="utf-8") as f:
        content = f.read()

    markers = []
    for match in _MARKER_BLOCK_RE.finditer(content):
        payload = json.loads(match.group("json"))
        payload["marker_id"] = str(payload.get("marker_id") or match.group("marker_id")).strip()
        markers.append(Marker(**payload))
    return markers


def _write_marker(handoff_path, marker):
    """Schreibt oder ersetzt einen Marker in der Datei per marker_id."""
    if not isinstance(marker, Marker):
        marker = Marker(**marker)

    new_block = _serialize_marker(marker)
    content = ""
    if os.path.exists(handoff_path):
        with open(handoff_path, "r", encoding="utf-8") as f:
            content = f.read()

    replaced = False

    def _replace(match):
        nonlocal replaced
        payload = json.loads(match.group("json"))
        existing_marker_id = str(payload.get("marker_id") or match.group("marker_id")).strip()
        if existing_marker_id == marker.marker_id:
            replaced = True
            return new_block
        return match.group(0)

    updated = _MARKER_BLOCK_RE.sub(_replace, content)

    if not replaced:
        updated = updated.rstrip()
        if updated:
            updated += "\n\n"
        updated += new_block

    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(updated.rstrip() + "\n")

    return marker


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
    if os.path.isdir(direct_root):
        project_root = direct_root
    else:
        project_root = resolve_project_path(project_id)
    if not project_root:
        raise FileNotFoundError(f"Projektpfad konnte nicht aufgeloest werden: {project_id}")

    context_name = str(context_path or "marker-context.md").strip()
    if not context_name:
        context_name = "marker-context.md"

    if os.path.isabs(context_name):
        return context_name
    return os.path.join(project_root, context_name)


def read_marker_context(project_id=None, context_path="marker-context.md"):
    """Liest einfache Metadaten aus marker-context.md."""
    if project_id:
        resolved_path = _resolve_context_path(project_id, context_path)
    else:
        context_name = str(context_path or "marker-context.md").strip() or "marker-context.md"
        resolved_path = context_name if os.path.isabs(context_name) else os.path.abspath(context_name)

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(resolved_path)

    metadata = {"context_path": resolved_path}
    with open(resolved_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("- ") or ":" not in line:
                continue
            key, value = line[2:].split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def _compute_gate(marker):
    prompt = (marker.prompt or "").strip()
    checks = marker.checks or []
    if not prompt:
        return False, "prompt ist leer"
    if len(checks) < 1:
        return False, "keine checks definiert"
    return True, ""


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
    candidates = [
        os.path.join(os.getcwd(), "upload", "Sprints"),
        os.path.join(os.getcwd(), "sprints"),
    ]
    for base in candidates:
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
    lines = content.splitlines()
    plan_id = str(plan_id).strip()

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
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= section_level:
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
            tasks_heading_level = None
            break

    search_lines = section_lines[tasks_start:] if tasks_start is not None else section_lines
    tasks = []
    for line in search_lines:
        stripped = line.strip()
        if tasks_heading_level is not None and stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= tasks_heading_level:
                break
        match = _TASK_BULLET_RE.match(line)
        if not match:
            continue
        task = match.group("task").strip()
        if task:
            tasks.append(task)

    if not tasks:
        raise ValueError("tasks_not_found")

    return {
        "sprint_path": resolved_path,
        "sprint_title": sprint_title,
        "tasks": tasks,
    }


def buildsuggestion(marker, sprint_context):
    sprint_title = str((sprint_context or {}).get("sprint_title") or marker.plan_id).strip()
    sprint_name = os.path.basename(str((sprint_context or {}).get("sprint_path") or "")).strip()
    suggestion = f"Arbeite die Sprint-Aufgabe '{marker.titel}' aus {sprint_title} ab."
    if sprint_name:
        suggestion += f" Orientiere dich am Sprint-Plan in {sprint_name}."
    if marker.ziel and marker.ziel != marker.titel:
        suggestion += f" Ziel: {marker.ziel}."
    return suggestion.strip()


def sprinttomarkers(sprint_path, plan_id, handoff_path):
    """Erzeugt oder aktualisiert Marker aus einer Sprint-Aufgabenliste."""
    plan_id = str(plan_id).strip()
    if not plan_id:
        raise ValueError("plan_id ist erforderlich")

    sprint_context = _extract_tasks_from_sprint(sprint_path, plan_id)
    existing_markers = parse_markers(handoff_path)
    existing_by_id = {marker.marker_id: marker for marker in existing_markers}
    existing_by_title = {
        _normalize_marker_title(marker.titel): marker
        for marker in existing_markers
        if marker.plan_id == plan_id
    }

    written = []
    for task in sprint_context["tasks"]:
        normalized_title = _normalize_marker_title(task)
        marker_id = _build_sprint_marker_id(plan_id, task)
        existing = existing_by_id.get(marker_id) or existing_by_title.get(normalized_title)

        if existing:
            marker = Marker(**asdict(existing))
            marker.marker_id = existing.marker_id
            marker.titel = task
            marker.ziel = task
            marker.prompt_suggestion = buildsuggestion(marker, sprint_context)
            marker.updated_at = datetime.now(timezone.utc).isoformat()
        else:
            marker = Marker(
                marker_id=marker_id,
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
            )
            marker.prompt_suggestion = buildsuggestion(marker, sprint_context)

        _write_marker(handoff_path, marker)
        written.append(marker)

    return written


def _load_markers_with_regeneration(project_id):
    """Laedt Marker und regeneriert ein Legacy-Handoff bei Bedarf einmalig."""
    handoff_path = _get_handoff_path(project_id)
    markers = parse_markers(handoff_path)
    if markers:
        return markers
    if not os.path.exists(handoff_path):
        return []

    try:
        from services.project_handoff_service import write_handoff
        filepath, _ = write_handoff(project_id)
        if not filepath:
            return []
        return parse_markers(filepath)
    except Exception:
        return []


def _render_marker_context(marker, project_id=""):
    checks = marker.checks or []
    checks_text = "\n".join(f"- {item}" for item in checks) if checks else "- _(keine checks definiert)_"
    last_session = marker.last_session or ""
    prompt = marker.prompt or ""
    project_line = f"- project_id: {project_id}\n" if project_id else ""
    return (
        "# Marker-Kontext\n\n"
        f"- marker_id: {marker.marker_id}\n"
        f"- plan_id: {marker.plan_id}\n"
        f"{project_line}"
        f"- titel: {marker.titel}\n"
        f"- ziel: {marker.ziel}\n"
        f"- naechster_schritt: {marker.naechster_schritt}\n"
        f"- risiko: {marker.risiko}\n"
        f"- status: {marker.status}\n"
        f"- last_session: {last_session}\n\n"
        "## Prompt\n\n"
        f"{prompt}\n\n"
        "## Checks (Definition of Done)\n\n"
        f"{checks_text}\n"
    )


def is_activatable(handoff_path, marker_id):
    """Prueft, ob ein Marker auf Basis der Gate-Logik aktivierbar ist."""
    marker_id = str(marker_id).strip()
    for marker in parse_markers(handoff_path):
        if marker.marker_id == marker_id:
            return _compute_gate(marker)
    raise MarkerActivationError("Marker nicht gefunden")


def activate_marker(project_id, marker_id, context_path):
    """Bereitet genau einen Marker zur Ausfuehrung vor: Kontextdatei + Statuswechsel."""
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
        return {
            "marker": _marker_to_dict(marker, include_gate=True),
            "context_path": resolved_context_path,
        }

    raise MarkerActivationError("Marker nicht gefunden")


def _marker_to_dict(marker, include_gate=False):
    data = asdict(marker)
    if include_gate:
        is_activatable, gate_reason = _compute_gate(marker)
        data["is_activatable"] = is_activatable
        data["gate_reason"] = gate_reason
    return data


def list_markers_for_plan(project_id, plan_id):
    """Laedt Marker fuer einen Plan aus der handoff.md des Projekts."""
    markers = _load_markers_with_regeneration(project_id)
    plan_id = str(plan_id).strip()
    return [
        _marker_to_dict(marker, include_gate=True)
        for marker in markers
        if marker.plan_id == plan_id
    ]


def get_marker_context(project_id, marker_id):
    """Liefert den vollstaendigen Marker-Kontext fuer das Detail-Panel."""
    marker_id = str(marker_id).strip()
    for marker in _load_markers_with_regeneration(project_id):
        if marker.marker_id == marker_id:
            return _marker_to_dict(marker, include_gate=True)
    return None


def update_marker_status(project_id, marker_id, status):
    """Aktualisiert den Status eines Markers und schreibt ihn zurueck."""
    status = str(status or "").strip()
    if status not in VALID_STATUSES:
        raise ValueError(f"ungueltiger status: {status}")

    handoff_path = _get_handoff_path(project_id)
    marker_id = str(marker_id).strip()
    for marker in _load_markers_with_regeneration(project_id):
        if marker.marker_id != marker_id:
            continue
        marker.status = status
        marker.updated_at = datetime.now(timezone.utc).isoformat()
        _write_marker(handoff_path, marker)
        # TODO: Falls spaeter noetig, plan_sections status optional mit Marker-Status synchronisieren.
        return _marker_to_dict(marker, include_gate=True)
    return None


def update_marker_fields(project_id, marker_id, fields):
    """Aktualisiert einzelne Marker-Felder und schreibt den Marker zurueck."""
    if not isinstance(fields, dict) or not fields:
        raise ValueError("fields muss ein nicht-leeres Objekt sein")

    handoff_path = _get_handoff_path(project_id)
    marker_id = str(marker_id).strip()
    allowed_fields = {
        "titel",
        "plan_id",
        "status",
        "ziel",
        "naechster_schritt",
        "prompt",
        "prompt_suggestion",
        "risiko",
        "checks",
        "last_session",
        "updated_at",
    }

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


def close_marker(
    handoff_path,
    marker_id,
    *,
    status=None,
    naechster_schritt=None,
    last_session=None,
    updated_at=None
):
    """Schreibt den Session-Fortschritt fuer genau einen Marker in handoff.md zurueck."""
    if not os.path.exists(handoff_path):
        raise FileNotFoundError("handoff_missing")

    marker_id = str(marker_id).strip()
    if not marker_id:
        raise MarkerCloseError("marker_not_found")

    markers = parse_markers(handoff_path)
    for marker in markers:
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
        if isinstance(effective_updated_at, datetime):
            marker.updated_at = effective_updated_at.astimezone(timezone.utc).isoformat()
        else:
            marker.updated_at = str(effective_updated_at).strip()

        marker = Marker(**asdict(marker))
        _write_marker(handoff_path, marker)
        return marker

    raise MarkerCloseError("marker_not_found")
