"""
Format-, Parse- und Validierungshelfer fuer Copilot-Marker.
"""
import json
import re
from dataclasses import asdict, dataclass, field
from typing import List


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
    execution_score: int | None = None
    execution_comment: str = ""
    last_execution_at: str = ""
    sprint_tag: str = ""
    spec_tag: str = ""
    sprint_plan_id: int | None = None
    spec_id: int | None = None

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
        self.execution_comment = "" if self.execution_comment is None else str(self.execution_comment).strip()
        self.last_execution_at = "" if self.last_execution_at is None else str(self.last_execution_at).strip()
        self.sprint_tag = "" if self.sprint_tag is None else str(self.sprint_tag).strip()
        self.spec_tag = "" if self.spec_tag is None else str(self.spec_tag).strip()
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
        if self.execution_score is not None:
            self.execution_score = _validate_execution_score(self.execution_score)
        if self.sprint_plan_id is not None:
            self.sprint_plan_id = int(self.sprint_plan_id)
        if self.spec_id is not None:
            self.spec_id = int(self.spec_id)


class MarkerActivationError(ValueError):
    def __init__(self, message, gate_reason=""):
        super().__init__(message)
        self.gate_reason = gate_reason or message


class MarkerCloseError(ValueError):
    """Fehler fuer ungueltige oder nicht auffindbare Marker beim Session-Write-back."""


def _render_marker_markdown(marker):
    prompt_text = marker.prompt.strip() if marker.prompt.strip() else "_(noch nicht gesetzt)_"
    checks_text = "\n".join(f"- {item}" for item in marker.checks) if marker.checks else "_(noch keine)_"
    return "\n".join([
        f"## {marker.titel} · {marker.status}",
        "",
        f"**Ziel:** {marker.ziel}",
        f"**Naechster Schritt:** {marker.naechster_schritt}",
        f"**Risiko:** {marker.risiko or '-'}",
        f"**Execution Score:** {marker.execution_score if marker.execution_score is not None else '-'}",
        f"**Execution Comment:** {marker.execution_comment or '-'}",
        f"**Last Execution:** {marker.last_execution_at or '-'}",
        f"**Sprint Tag:** {marker.sprint_tag or '-'}",
        f"**Spec Tag:** {marker.spec_tag or '-'}",
        "",
        "**Prompt:**",
        prompt_text,
        "",
        "**Checks:**",
        checks_text,
        "",
    ])


def _serialize_marker(marker):
    if not isinstance(marker, Marker):
        marker = Marker(**marker)
    payload = json.dumps(asdict(marker), ensure_ascii=False, indent=2)
    return f"<!-- MARKER:{marker.marker_id}\n{payload}\n-->\n\n{_render_marker_markdown(marker)}\n---\n"


def parse_markers(handoff_path):
    """Tolerante Variante: liefert nur die gueltigen Marker, fehlerhafte Bloecke werden uebersprungen.

    Fuer aufrufende Stellen, die zusaetzlich die Fehler brauchen (z.B. UI-Anzeige),
    siehe parse_markers_with_errors.
    """
    markers, _errors = parse_markers_with_errors(handoff_path)
    return markers


def parse_markers_with_errors(handoff_path):
    """Parst eine handoff.md und liefert (markers, errors).

    errors ist eine Liste von Dicts mit den Feldern:
        - marker_id: aus dem MARKER:<id>-Tag oder "<unknown>"
        - error: lesbare Fehlermeldung
        - error_type: "json_decode" oder "validation" oder "unexpected"
        - handoff_path: absoluter Pfad der Datei
    """
    try:
        with open(handoff_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return [], []

    markers = []
    errors = []
    for match in _MARKER_BLOCK_RE.finditer(content):
        marker_id_hint = (match.group("marker_id") or "").strip() or "<unknown>"
        try:
            payload = json.loads(match.group("json"))
        except json.JSONDecodeError as exc:
            errors.append({
                "marker_id": marker_id_hint,
                "error": f"JSON kaputt: {exc.msg} (Zeile {exc.lineno}, Spalte {exc.colno})",
                "error_type": "json_decode",
                "handoff_path": handoff_path,
            })
            continue
        try:
            payload["marker_id"] = str(payload.get("marker_id") or marker_id_hint).strip()
            markers.append(Marker(**payload))
        except (ValueError, TypeError) as exc:
            errors.append({
                "marker_id": str(payload.get("marker_id") or marker_id_hint),
                "error": str(exc),
                "error_type": "validation",
                "handoff_path": handoff_path,
            })
        except Exception as exc:  # pragma: no cover - defensive
            errors.append({
                "marker_id": marker_id_hint,
                "error": f"unerwarteter Fehler: {exc}",
                "error_type": "unexpected",
                "handoff_path": handoff_path,
            })
    return markers, errors


def _write_marker(handoff_path, marker):
    if not isinstance(marker, Marker):
        marker = Marker(**marker)
    new_block = _serialize_marker(marker)
    try:
        with open(handoff_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

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


def _compute_gate(marker):
    if not (marker.prompt or "").strip():
        return False, "prompt ist leer"
    if len(marker.checks or []) < 1:
        return False, "keine checks definiert"
    return True, ""


def _marker_to_dict(marker, include_gate=False):
    data = asdict(marker)
    if include_gate:
        is_activatable, gate_reason = _compute_gate(marker)
        data["is_activatable"] = is_activatable
        data["gate_reason"] = gate_reason
    return data


def _validate_execution_score(execution_score):
    try:
        score = int(execution_score)
    except (TypeError, ValueError):
        raise ValueError("execution_score muss zwischen 0 und 5 liegen")
    if score < 0 or score > 5:
        raise ValueError("execution_score muss zwischen 0 und 5 liegen")
    return score
