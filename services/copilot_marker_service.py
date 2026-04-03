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


def _compute_gate(marker):
    prompt = (marker.prompt or "").strip()
    checks = marker.checks or []
    if not prompt:
        return False, "prompt ist leer"
    if len(checks) < 1:
        return False, "keine checks definiert"
    return True, ""


def _render_marker_context(marker):
    checks = marker.checks or []
    checks_text = "\n".join(f"- {item}" for item in checks) if checks else "- _(keine checks definiert)_"
    last_session = marker.last_session or ""
    prompt = marker.prompt or ""
    return (
        "# Marker-Kontext\n\n"
        f"- marker_id: {marker.marker_id}\n"
        f"- plan_id: {marker.plan_id}\n"
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
            f.write(_render_marker_context(marker))

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
    markers = parse_markers(_get_handoff_path(project_id))
    plan_id = str(plan_id).strip()
    return [
        _marker_to_dict(marker, include_gate=True)
        for marker in markers
        if marker.plan_id == plan_id
    ]


def get_marker_context(project_id, marker_id):
    """Liefert den vollstaendigen Marker-Kontext fuer das Detail-Panel."""
    marker_id = str(marker_id).strip()
    for marker in parse_markers(_get_handoff_path(project_id)):
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
    for marker in parse_markers(handoff_path):
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

    for marker in parse_markers(handoff_path):
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
