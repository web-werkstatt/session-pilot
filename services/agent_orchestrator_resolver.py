"""
Sprint sprint-agent-orchestrator-hardening Tag 3 (2026-04-17):
Handoff-/Marker-Resolver fuer den Agent-Orchestrator.

Liefert fuer einen Agentenlauf den kompletten Arbeitskontext:
  * handoff_path (Pfad zur projektspezifischen handoff.md)
  * aktiver Marker (DB-first via workflow_core_service)
  * relevanter Plan (project_plans Row)
  * start_scope (abgeleitete allowed_files-Empfehlung)

Bewusst als eigenes Modul ausgelagert, damit der Phase-1-Service
(`agent_orchestrator_service`) klein bleibt und unter der 500-Zeilen-Grenze.
Phase-1-APIs (Task-CRUD, Session-State, Preflight) leben weiterhin in
`agent_orchestrator_service`. Der Bootstrap-Flow dort nutzt diesen Resolver.
"""
import os

from services.db_service import execute


def resolve_context(project_id, plan_id=None, marker_id=None,
                    *, marker_lookup=None, plan_lookup=None,
                    handoff_path_fn=None):
    """Loest den Arbeitskontext fuer einen Agentenlauf auf.

    Parameter:
      * project_id: Pflicht. Eindeutiger Projekt-Slug unter /mnt/projects.
      * plan_id: optional. Numerische ID eines project_plans-Eintrags.
      * marker_id: optional. Marker-Slug; Lookup ueber workflow_core_service.
      * marker_lookup / plan_lookup / handoff_path_fn: Injection fuer Tests.

    Rueckgabe:
      dict mit Feldern:
        - project_id
        - handoff_path (absoluter Pfad)
        - handoff_exists (bool)
        - active_marker (dict oder None)
        - relevant_plan (dict oder None)
        - start_scope (list[str], abgeleitete allowed_files-Empfehlung)
        - notes (list[str], z.B. marker_not_found:<id>)

    Die Funktion ist read-only. Sie schreibt nichts in die DB und ruft keinen
    Write-Guard.
    """
    project_id = str(project_id or "").strip()
    if not project_id:
        raise ValueError("project_id darf nicht leer sein")

    handoff_path = (handoff_path_fn or _default_handoff_path)(project_id)
    handoff_exists = bool(handoff_path) and os.path.exists(handoff_path)

    notes = []
    active_marker = None
    relevant_plan = None

    effective_plan_id = plan_id

    if marker_id is not None and str(marker_id).strip() != "":
        marker = (marker_lookup or _default_marker_lookup)(project_id, str(marker_id).strip())
        if marker is not None:
            active_marker = _marker_to_public_dict(marker)
            if effective_plan_id in (None, "") and active_marker.get("plan_id"):
                effective_plan_id = active_marker["plan_id"]
        else:
            notes.append(f"marker_not_found:{marker_id}")

    if effective_plan_id is not None and str(effective_plan_id).strip() != "":
        plan_row = (plan_lookup or _default_plan_lookup)(effective_plan_id)
        if plan_row is not None:
            relevant_plan = _plan_row_to_dict(plan_row)
        else:
            notes.append(f"plan_not_found:{effective_plan_id}")

    start_scope = _derive_start_scope(relevant_plan)

    return {
        "project_id": project_id,
        "handoff_path": handoff_path,
        "handoff_exists": handoff_exists,
        "active_marker": active_marker,
        "relevant_plan": relevant_plan,
        "start_scope": start_scope,
        "notes": notes,
    }


def _default_handoff_path(project_id):
    # Lazy-Import verhindert Zirkel bei Modulinitialisierung.
    from services.project_handoff_service import get_handoff_path
    return get_handoff_path(project_id)


def _default_marker_lookup(project_id, marker_id):
    from services.workflow_core_service import get_marker
    try:
        return get_marker(project_id, marker_id)
    except Exception:
        return None


def _default_plan_lookup(plan_id):
    try:
        pid = int(str(plan_id).strip())
    except (TypeError, ValueError):
        return None
    try:
        return execute(
            """SELECT id, project_name, title, status,
                      source_path, source_kind, updated_at
               FROM project_plans
               WHERE id = %s""",
            (pid,),
            fetchone=True,
        )
    except Exception:
        return None


def _marker_to_public_dict(marker):
    # marker ist eine Marker-Dataclass-Instanz aus workflow_core_service.
    return {
        "marker_id": getattr(marker, "marker_id", None),
        "plan_id": getattr(marker, "plan_id", None),
        "titel": getattr(marker, "titel", "") or "",
        "status": getattr(marker, "status", "") or "",
        "ziel": getattr(marker, "ziel", "") or "",
        "naechster_schritt": getattr(marker, "naechster_schritt", "") or "",
        "last_session": getattr(marker, "last_session", "") or "",
    }


def _plan_row_to_dict(row):
    if row is None:
        return None
    data = dict(row)
    updated_at = data.get("updated_at")
    if updated_at is not None and hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "project_name": data.get("project_name"),
        "status": data.get("status"),
        "source_path": data.get("source_path"),
        "source_kind": data.get("source_kind"),
        "updated_at": updated_at,
    }


def _derive_start_scope(plan_dict):
    """Leitet den Default-Start-Scope fuer den Task-Contract ab.

    Regeln v1:
      * Wenn ein Plan bekannt ist und `source_path` gesetzt hat -> genau
        dieser Pfad als Scope.
      * handoff.md wird bewusst NICHT in den Scope aufgenommen: die Datei ist
        ein generiertes Artefakt und darf nicht freies Ziel von Executor-Writes
        werden.
      * Ohne Plan oder ohne source_path bleibt der Scope leer; der Caller
        muss dann explizit allowed_files setzen.
    """
    if not plan_dict:
        return []
    source_path = plan_dict.get("source_path")
    if source_path:
        return [source_path]
    return []
