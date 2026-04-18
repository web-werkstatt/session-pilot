"""
Sprint sprint-agent-orchestrator-hardening-phase-1-foundation (2026-04-17):
Service-Schicht fuer den Agent-Orchestrator Phase 1.

Kapselt:
  * Task-Contract erstellen + lesen (agent_task_contracts)
  * Session-State lesen + schreiben (agent_session_states)
  * Preflight-Gate: Branch, dirty worktree, untracked / modified files,
    Scope-Verletzung gegen allowed_files, sensitive File-Flags.

Tag 3 (2026-04-17) ergaenzt den Handoff-/Marker-Resolver:
  * `resolve_context(project_id, plan_id, marker_id)` liefert `handoff_path`,
    aktiven Marker, relevanten Plan und einen abgeleiteten `start_scope`.
  * `bootstrap_task(...)` kombiniert Resolver + `create_task` und bildet so
    den End-to-End-Einstieg fuer einen Agentenlauf.

Die Persistenz ist schlank gehalten (zwei Tabellen, kein Verify/Recovery).
Spaetere Phasen ergaenzen Verify-Gate, Claim-Modell, Close-Gate, Recovery.
"""
import json
from pathlib import Path

from services.agent_git_utils import default_git_runner as _default_git_runner
from services.agent_git_utils import git_branch as _git_branch
from services.agent_git_utils import git_status as _git_status

from services.db_service import execute, ensure_agent_orchestrator_schema, ensure_agent_verify_schema


ALLOWED_STATES = {"inspect", "implement", "verify", "document", "done", "recovery"}
DEFAULT_MODE = "executor"
ALLOWED_MODES = {"executor", "reviewer", "recovery"}

# Sprint Project-Config (2026-04-17): Die historischen Dashboard-Defaults
# werden nicht mehr direkt im Preflight geprueft, sondern kommen pro Task ueber
# `agent_project_config_service.get_config(task.project_id)`. Die Konstante
# bleibt erhalten, damit Altaufrufe (externe Tools, alte Migrations-Snippets)
# den gleichen Blick auf den Default behalten. Sie ist nicht mehr autoritativ.
SENSITIVE_FILES = (
    "next-session.md",
    "handoff.md",
    "sprints/master-plan-2026-04-01.md",
)


# ---------------------------------------------------------------------------
# Task-Contract CRUD
# ---------------------------------------------------------------------------

def create_task(payload):
    """Persistiert einen neuen agent_task_contract.

    Pflichtfelder: title. Alle Listen sind defensiv, JSONB nimmt sie roh.
    Rueckgabe: dict mit Task-Contract inkl. id + created_at.
    """
    ensure_agent_orchestrator_schema()

    title = (payload or {}).get("title")
    if not title or not str(title).strip():
        raise ValueError("title darf nicht leer sein")

    mode = payload.get("mode") or DEFAULT_MODE
    if mode not in ALLOWED_MODES:
        raise ValueError(f"ungueltiger mode: {mode}")

    project_id = payload.get("project_id")
    if project_id is not None and str(project_id).strip() != "":
        try:
            project_id = int(project_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"project_id muss numerisch sein: {project_id}") from exc
    else:
        project_id = None

    source_plan_id = payload.get("source_plan_id")
    if source_plan_id is not None and str(source_plan_id).strip() != "":
        try:
            source_plan_id = int(source_plan_id)
        except (TypeError, ValueError):
            source_plan_id = None
    else:
        source_plan_id = None

    row = execute(
        """
        INSERT INTO agent_task_contracts (
            session_id, title, goal, mode,
            allowed_files_json, forbidden_actions_json,
            required_verification_json, required_outputs_json,
            stop_conditions_json, project_id,
            marker_id, source_plan_id
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
        RETURNING id, created_at
        """,
        (
            payload.get("session_id"),
            str(title).strip(),
            payload.get("goal") or "",
            mode,
            json.dumps(payload.get("allowed_files") or []),
            json.dumps(payload.get("forbidden_actions") or []),
            json.dumps(payload.get("required_verification") or []),
            json.dumps(payload.get("required_outputs") or []),
            json.dumps(payload.get("stop_conditions") or []),
            project_id,
            payload.get("marker_id") or None,
            source_plan_id,
        ),
        fetchone=True,
    )
    if not row:
        raise RuntimeError("agent_task_contracts insert lieferte keine Zeile zurueck")

    return get_task(row["id"])


def get_task(task_id):
    """Liest einen Task-Contract oder gibt None zurueck."""
    ensure_agent_orchestrator_schema()
    row = execute(
        """
        SELECT id, session_id, title, goal, mode,
               allowed_files_json, forbidden_actions_json,
               required_verification_json, required_outputs_json,
               stop_conditions_json, project_id,
               marker_id, source_plan_id, created_at
        FROM agent_task_contracts
        WHERE id = %s
        """,
        (task_id,),
        fetchone=True,
    )
    if not row:
        return None
    return _task_row_to_contract(row)


def _task_row_to_contract(row):
    return {
        "task_id": row["id"],
        "session_id": row.get("session_id"),
        "project_id": row.get("project_id"),
        "marker_id": row.get("marker_id"),
        "source_plan_id": row.get("source_plan_id"),
        "title": row.get("title"),
        "goal": row.get("goal") or "",
        "mode": row.get("mode") or DEFAULT_MODE,
        "allowed_files": _as_list(row.get("allowed_files_json")),
        "forbidden_actions": _as_list(row.get("forbidden_actions_json")),
        "required_verification": _as_list(row.get("required_verification_json")),
        "required_outputs": _as_list(row.get("required_outputs_json")),
        "stop_conditions": _as_list(row.get("stop_conditions_json")),
        "created_at": _iso(row.get("created_at")),
    }


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


def _iso(ts):
    if ts is None:
        return None
    try:
        return ts.isoformat()
    except AttributeError:
        return str(ts)


# ---------------------------------------------------------------------------
# Session-State
# ---------------------------------------------------------------------------

def get_session_state(session_id):
    """Liest den persistierten Session-State. None, wenn noch keiner existiert."""
    ensure_agent_orchestrator_schema()
    row = execute(
        """
        SELECT session_id, state, previous_state, reason, locked,
               blocking_issues_json, recovery_snapshot_json, updated_at
        FROM agent_session_states
        WHERE session_id = %s
        """,
        (session_id,),
        fetchone=True,
    )
    if not row:
        return None
    return _state_row_to_dict(row)


def set_session_state(session_id, state, reason=None, locked=False, blocking_issues=None):
    """Upsertet den Session-State und aktualisiert previous_state automatisch.

    State-Uebergaenge werden in Phase 1 nur persistiert, nicht gegen die
    Transition-Matrix gehaertet. Das ist bewusst Phase-2-Arbeit.
    """
    if state not in ALLOWED_STATES:
        raise ValueError(f"ungueltiger state: {state}")
    if not session_id or not str(session_id).strip():
        raise ValueError("session_id darf nicht leer sein")

    ensure_agent_orchestrator_schema()

    current = get_session_state(session_id)
    previous_state = current["state"] if current else None
    blocking_json = json.dumps(blocking_issues or [])

    execute(
        """
        INSERT INTO agent_session_states (
            session_id, state, previous_state, reason, locked,
            blocking_issues_json, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
        ON CONFLICT (session_id) DO UPDATE SET
            previous_state = EXCLUDED.previous_state,
            state = EXCLUDED.state,
            reason = EXCLUDED.reason,
            locked = EXCLUDED.locked,
            blocking_issues_json = EXCLUDED.blocking_issues_json,
            updated_at = NOW()
        """,
        (
            session_id,
            state,
            previous_state,
            reason,
            bool(locked),
            blocking_json,
        ),
    )
    return get_session_state(session_id)


def _state_row_to_dict(row):
    return {
        "session_id": row.get("session_id"),
        "state": row.get("state"),
        "previous_state": row.get("previous_state"),
        "reason": row.get("reason"),
        "locked": bool(row.get("locked")),
        "blocking_issues": _as_list(row.get("blocking_issues_json")),
        "recovery_snapshot": _as_dict(row.get("recovery_snapshot_json")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _as_dict(value):
    """Parst JSONB-Werte defensiv zu dict, sonst None."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Preflight-Gate
# ---------------------------------------------------------------------------

def run_preflight(task_id, repo_path=None, git_runner=None):
    """Fuehrt den Preflight fuer einen Task-Contract aus.

    Parameter:
      * task_id: ID in agent_task_contracts
      * repo_path: optional, Default = Projekt-Root (cwd der App)
      * git_runner: optional Callable(list[str]) -> (rc, stdout). Erlaubt
        Tests ohne echten Git-Prozess.

    Rueckgabe: preflight_result dict gemaess Technical Spec.
    """
    task = get_task(task_id)
    if not task:
        raise ValueError(f"task {task_id} nicht gefunden")

    if repo_path is None:
        repo_path = str(Path(__file__).resolve().parent.parent)

    runner = git_runner or _default_git_runner(repo_path)

    branch = _git_branch(runner)
    untracked, modified = _git_status(runner)

    allowed = set(task.get("allowed_files") or [])
    touched = untracked + modified
    out_of_scope = [path for path in touched if allowed and path not in allowed]
    # Wenn allowed_files leer ist, ist alles out-of-scope (Policy: kein Scope = kein Write erlaubt).
    if not allowed:
        out_of_scope = list(touched)

    sensitive = _resolve_sensitive_files(task.get("project_id"))
    sensitive_touched = [path for path in touched if path in sensitive]

    risk_flags = []
    if untracked or modified:
        risk_flags.append("dirty_worktree")
    if out_of_scope:
        risk_flags.append("scope_violation")
    if sensitive_touched:
        risk_flags.append("sensitive_file_touched")

    # Blocking-Logik Phase 1:
    #   out-of-scope > sensitive > clean.
    # Ein dirty worktree allein ist nur ein Risk-Flag, kein Blocker — solange
    # alle beruehrten Dateien im Scope liegen und nicht sensitiv sind, darf
    # Preflight ok=true liefern.
    if out_of_scope:
        blocking_reason = "out_of_scope_files_present"
    elif sensitive_touched:
        blocking_reason = "sensitive_file_touched"
    else:
        blocking_reason = None

    return {
        "task_id": task_id,
        "ok": blocking_reason is None,
        "branch": branch,
        "dirty_worktree": bool(untracked or modified),
        "untracked_files": untracked,
        "modified_files": modified,
        "out_of_scope_files": out_of_scope,
        "sensitive_files_touched": sensitive_touched,
        "risk_flags": risk_flags,
        "blocking_reason": blocking_reason,
    }


def _resolve_sensitive_files(project_id):
    """Liest sensitive_files aus der Project-Config.

    Fallback: Dashboard-Defaults (SENSITIVE_FILES). Lazy-Import vermeidet einen
    Zirkel beim Modulstart, falls agent_project_config_service spaeter einmal
    selbst Teile aus dem Orchestrator braucht.
    """
    try:
        from services.agent_project_config_service import get_config
        cfg = get_config(project_id)
        files = cfg.get("sensitive_files")
        if isinstance(files, list):
            return set(files)
    except Exception:
        pass
    return set(SENSITIVE_FILES)


# ---------------------------------------------------------------------------
# Handoff-/Marker-Resolver (Tag 3) — Thin Wrappers
# ---------------------------------------------------------------------------
# Die eigentliche Resolver-Logik lebt in services/agent_orchestrator_resolver.py,
# damit dieser Service unter der 500-Zeilen-Grenze bleibt. Hier nur:
#   * bootstrap_task: kombiniert Resolver + create_task in einem Call.
#   * resolve_context: Re-Export, damit bestehende Importpfade nicht brechen.

from services.agent_orchestrator_resolver import resolve_context  # noqa: E402,F401


def bootstrap_task(project_id, title, goal="", plan_id=None, marker_id=None,
                   session_id=None, overrides=None,
                   *, marker_lookup=None, plan_lookup=None,
                   handoff_path_fn=None, project_id_for_contract=None):
    """Loest den Kontext auf und legt direkt einen agent_task_contract an.

    `overrides` erlaubt punktuelles Ueberschreiben der Resolver-Defaults
    (z.B. explizite `allowed_files`, `forbidden_actions`). Wird keine
    `allowed_files`-Ueberschreibung uebergeben, gilt `context.start_scope` als
    Defaultscope.

    Rueckgabe: dict mit `contract` (aus create_task) und `context` (aus
    resolve_context), damit der Caller beides sieht, ohne zwei Calls zu machen.
    """
    overrides = overrides or {}
    context = resolve_context(
        project_id,
        plan_id=plan_id,
        marker_id=marker_id,
        marker_lookup=marker_lookup,
        plan_lookup=plan_lookup,
        handoff_path_fn=handoff_path_fn,
    )

    if "allowed_files" in overrides and overrides["allowed_files"] is not None:
        allowed_files = list(overrides["allowed_files"])
    else:
        allowed_files = list(context["start_scope"])

    # `project_id` auf dem Task-Contract ist numerisch (FK-Kandidat zu projects),
    # der Resolver arbeitet aber mit Slug/String. Wenn der Aufrufer einen
    # expliziten numerischen Bezug setzen will, laeuft das ueber
    # `project_id_for_contract` oder `overrides["project_id"]`.
    contract_project_id = (
        project_id_for_contract
        if project_id_for_contract is not None
        else overrides.get("project_id")
    )

    payload = {
        "session_id": session_id,
        "project_id": contract_project_id,
        "marker_id": marker_id or None,
        "source_plan_id": plan_id or None,
        "title": title,
        "goal": goal or "",
        "mode": overrides.get("mode") or DEFAULT_MODE,
        "allowed_files": allowed_files,
        "forbidden_actions": overrides.get("forbidden_actions") or [],
        "required_verification": overrides.get("required_verification") or [],
        "required_outputs": overrides.get("required_outputs") or [],
        "stop_conditions": overrides.get("stop_conditions") or [],
    }
    contract = create_task(payload)
    return {"contract": contract, "context": context}


# ---------------------------------------------------------------------------
# Task-Lookup / Marker-Lookup — ausgelagert nach services/agent_task_lookup.py
# ---------------------------------------------------------------------------
# Re-Exporte halten die oeffentlichen Importpfade stabil. Lookup-Funktionen
# dereferenzieren `execute` / `ensure_*` ueber dieses Modul, damit Test-
# Monkeypatches auf `orchestrator.execute` weiterhin wirken.

from services.agent_task_lookup import (  # noqa: E402,F401
    list_tasks,
    get_task_for_marker,
)


