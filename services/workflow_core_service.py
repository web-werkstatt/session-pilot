"""
ADR-001: Zentrale Domaenenschicht fuer Marker-Zugriff (DB-first).

Alle Marker-Lese- und Schreiboperationen laufen ueber diesen Service.
workflow_loop_service und copilot_marker_service delegieren hierher.

Prio 5 (Write-Back): Schreibende Core-Operationen triggern anschliessend
einen Mirror-Write in handoff.md ueber den Write-Guard. Die DB bleibt
kanonische Quelle, handoff.md ist abgeleiteter Mirror.
"""
import json
import logging
import os
from dataclasses import asdict

from config import PROJECTS_DIR
from services.copilot_marker_format import Marker, _serialize_marker
from services.db_service import ensure_marker_schema, execute
from services.marker_importer import import_markers_from_handoff
from services.path_resolver import resolve_project_path
from services.workflow_state_service import (
    get_workflow_state,
    sync_marker_to_workflow,
)

log = logging.getLogger(__name__)

MIRROR_WRITER_SOURCE = "workflow_core_service"


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


def get_marker_detail(project_name, marker_id):
    """Liest einen Marker mit zugehoerigen Dispatch-Assignments.

    Returns:
        Dict mit Marker-Daten + assignments-Liste, oder None.
    """
    marker = get_marker(project_name, marker_id)
    if not marker:
        return None

    data = asdict(marker)

    try:
        from services.dispatch_service import list_assignments
        assignments = []
        for a in list_assignments(project_name=project_name):
            if str(a.get("marker_id") or "") == str(marker_id):
                assignments.append({
                    "assignment_id": a.get("assignment_id"),
                    "executor_tool": a.get("executor_tool", ""),
                    "approval_state": a.get("approval_state", ""),
                    "risk_level": a.get("risk_level", "medium"),
                    "dispatch_mode": a.get("dispatch_mode", "manual"),
                })
        data["assignments"] = assignments
    except Exception:
        data["assignments"] = []

    return data


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
    marker = get_marker(project_name, marker_id)
    _trigger_mirror_write(project_name)
    return marker


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
    """Read-Model fuer handoff.md-Regenerierung + Policy-Kontext.

    Liefert ein Dict:
    - `markers`: Liste aller Marker eines Projekts als Dicts (sortiert nach
      plan_id, marker_id), angereichert mit Workflow-State.
    - `active_policies`: Map `role_id -> {tool_id, rank, confidence}` aus
      der Policy-Schicht. Pro Rolle wird die primary Policy (niedrigster
      rank) gewaehlt. Leer wenn Policy-Schicht nicht verfuegbar oder keine
      Policies approved sind.

    Hinweis: Format wurde in ADR-002 Stufe 1b (Commit 9) von einer Liste
    auf ein Dict geaendert. Bis zu diesem Commit hatte die Funktion keinen
    produktiven Aufrufer.
    """
    markers = get_markers(project_name)
    marker_list = []
    for m in markers:
        if m is None:
            continue
        data = asdict(m)
        state = get_workflow_state(project_name, m.marker_id)
        if state:
            data["workflow_status"] = state.get("workflow_status", "planned")
            data["owner"] = state.get("owner", "")
            data["blocked_reason"] = state.get("blocked_reason", "")
            data["executor_tool"] = state.get("executor_tool", "")
        marker_list.append(data)

    active_policies = {}
    try:
        from services.policy_service import get_active_policies
        for p in get_active_policies() or []:
            rid = p.get("role_id")
            if not rid:
                continue
            current = active_policies.get(rid)
            new_rank = p.get("rank") or 99
            if current is None or new_rank < (current.get("rank") or 99):
                active_policies[rid] = {
                    "tool_id": p.get("tool_id"),
                    "rank": p.get("rank"),
                    "confidence": p.get("confidence"),
                }
    except Exception as exc:
        log.info("Policy-Schicht fuer handoff_view nicht verfuegbar: %s", exc)

    # Aktive Assignments pro Marker
    active_assignments = {}
    try:
        from services.dispatch_service import list_assignments
        for state in ("proposed", "approved", "claimed"):
            for a in list_assignments(project_name=project_name, status=state):
                mid = str(a.get("marker_id") or "")
                if mid and mid not in active_assignments:
                    active_assignments[mid] = {
                        "assignment_id": a.get("assignment_id"),
                        "executor_tool": a.get("executor_tool", ""),
                        "approval_state": a.get("approval_state", ""),
                        "risk_level": a.get("risk_level", "medium"),
                    }
    except Exception as exc:
        log.info("Dispatch-Assignments fuer handoff_view nicht ladbar: %s", exc)

    return {
        "markers": marker_list,
        "active_policies": active_policies,
        "active_assignments": active_assignments,
    }


MARKERS_SECTION_HEADING = "## Copilot Markers"


def write_handoff_mirror(project_name):
    """Regeneriert handoff.md aus DB-Markern (Core -> Mirror).

    ADR-001 Prio 5: Die DB ist kanonische Quelle. Dieser Write-Back laedt
    alle Marker des Projekts aus der DB, serialisiert sie deterministisch
    und schreibt das Ergebnis ueber den Write-Guard nach
    <project>/handoff.md.

    Manueller Text oberhalb von "## Copilot Markers" (YAML-Frontmatter,
    Projekt-Titel, Einleitung) bleibt erhalten. Nur die Marker-Sektion
    wird neu generiert.

    Idempotent: Bei gleichem DB-Zustand erzeugen Folgeaufrufe keinen Diff.

    Args:
        project_name: Projekt-Slug (z.B. "project_dashboard").

    Returns:
        Tuple (filepath, markdown) bei Erfolg, sonst (None, None).
    """
    from services.write_guard import safe_write

    project_name = str(project_name or "").strip()
    if not project_name:
        return None, None

    project_root = resolve_project_path(project_name) or os.path.join(PROJECTS_DIR, project_name)
    if not os.path.isdir(project_root):
        return None, None

    handoff_path = os.path.join(project_root, "handoff.md")

    # Uebergangsphase: Falls handoff.md Marker enthaelt, die noch nicht in der
    # DB stehen (z.B. manuell angelegte), werden sie per idempotentem Import
    # in den Core gehoben, bevor wir von DB zurueckspielen. So werden sie
    # nicht durch die Regenerierung gedroppt. import_markers_from_handoff
    # ist ein Upsert und loescht nie.
    if os.path.exists(handoff_path):
        try:
            import_markers_from_handoff(project_name)
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Pre-Mirror-Import fehlgeschlagen fuer %s: %s", project_name, exc)

    markers = get_markers(project_name)
    preamble = _read_preamble(handoff_path, project_name)
    marker_section = _build_marker_section(markers)
    markdown = preamble + marker_section

    result = safe_write(handoff_path, markdown, MIRROR_WRITER_SOURCE)
    if not result.allowed:
        log.warning(
            "Mirror-Write-Back blockiert fuer %s: %s",
            project_name,
            [v.description for v in result.violations],
        )
        return None, None

    return handoff_path, markdown


def _read_preamble(handoff_path, project_name):
    """Liest den Text bis inklusive "## Copilot Markers" aus einer vorhandenen
    handoff.md. Falls die Datei nicht existiert oder die Section fehlt, wird
    ein frischer Standard-Header erzeugt.
    """
    try:
        with open(handoff_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        return _build_default_preamble(project_name)

    idx = content.find(MARKERS_SECTION_HEADING)
    if idx < 0:
        return _build_default_preamble(project_name)

    # Alles bis inklusive "## Copilot Markers\n" einschliesslich trailing newline
    end = idx + len(MARKERS_SECTION_HEADING)
    # Trailing newline sicherstellen
    tail = content[end:end + 1]
    if tail == "\n":
        end += 1
    return content[:end] + "\n"


def _build_default_preamble(project_name):
    """Erzeugt den Standard-Preamble wenn keine handoff.md existiert."""
    return (
        "---\n"
        "handoff:\n"
        f'  project_id: "{project_name}"\n'
        '  state_format: "copilot_markers_v1"\n'
        "---\n"
        "\n"
        f"# Handoff fuer Projekt {project_name}\n"
        "\n"
        f"{MARKERS_SECTION_HEADING}\n"
        "\n"
    )


def _build_marker_section(markers):
    """Baut den Marker-Bereich: alle Marker serialisiert + trailing newline."""
    valid = [m for m in (markers or []) if m is not None]
    if not valid:
        return "\n_(noch keine Marker vorhanden)_\n"

    sorted_markers = sorted(valid, key=lambda m: (str(m.plan_id or ""), str(m.marker_id or "")))
    blocks = [_serialize_marker(m).rstrip() for m in sorted_markers]
    return "\n" + "\n\n".join(blocks) + "\n"


def _trigger_mirror_write(project_name):
    """Best-effort Mirror-Write nach Core-Schreiboperation.

    Fehler werden geloggt, aber nicht propagiert — die DB bleibt
    die kanonische Quelle auch wenn der Mirror temporaer fehlschlaegt.
    """
    try:
        write_handoff_mirror(project_name)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Mirror-Write-Back fehlgeschlagen fuer %s: %s", project_name, exc)


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
