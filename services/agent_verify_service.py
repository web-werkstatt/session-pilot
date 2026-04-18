"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 2, 2026-04-17):
Verify-Gate MVP fuer den Agent-Orchestrator.

Dieses Modul haelt:
  * ExecutionAlreadyRecordedError
  * record_execution(task_id, payload)   -> speichert execution_result
  * get_execution(task_id)               -> letzter execution_result
  * evaluate_close / close_task          -> Close-Gate

Die Verify-Gate-Logik (run_verify_gate / get_verify_gate / Claim-Typen /
Status-Konstanten) wurde 2026-04-18 nach `agent_verify_gate.py` ausgelagert
und wird hier re-exportiert, damit Aufrufer (Routes, Tests) unveraendert
`verify_service.run_verify_gate` nutzen koennen.
"""
import json

from services.db_service import execute, ensure_agent_verify_schema
from services.agent_orchestrator_service import (
    get_task,
    set_session_state,
    _as_list,
    _iso,
)
from services.agent_verify_claim_checks import default_command_runner
from services.agent_verify_gate import (
    run_verify_gate,
    get_verify_gate,
    CLAIM_TYPES_COMMAND,
    CLAIM_TYPE_SMOKE,
    CLAIM_TYPE_FEATURE,
    CLAIM_TYPE_APPEND_ONLY,
    VERIFY_STATUS_PASS,
    VERIFY_STATUS_BLOCKED,
    VERIFY_STATUS_FAIL,
)


__all__ = [
    "ExecutionAlreadyRecordedError",
    "record_execution",
    "get_execution",
    "evaluate_close",
    "close_task",
    "run_verify_gate",
    "get_verify_gate",
    "default_command_runner",
    "CLAIM_TYPES_COMMAND",
    "CLAIM_TYPE_SMOKE",
    "CLAIM_TYPE_FEATURE",
    "CLAIM_TYPE_APPEND_ONLY",
    "VERIFY_STATUS_PASS",
    "VERIFY_STATUS_BLOCKED",
    "VERIFY_STATUS_FAIL",
    "CLOSE_GATE_REASON_OK",
    "CLOSE_GATE_REASON_NO_VERIFY",
    "CLOSE_GATE_REASON_NOT_PASS",
]


class ExecutionAlreadyRecordedError(Exception):
    """Sprint Workflow-Finalization Session 2 (AC2-2).

    Wird geworfen, wenn `record_execution` fuer einen Task einen zweiten
    INSERT versuchen wuerde. Route uebersetzt den Fehler in HTTP 409.
    """

    code = "execution_already_recorded"

    def __init__(self, task_id, existing_execution_id=None):
        super().__init__(
            f"execution_result for task {task_id} already recorded"
            + (f" (execution_id={existing_execution_id})" if existing_execution_id else "")
        )
        self.task_id = task_id
        self.existing_execution_id = existing_execution_id


CLOSE_GATE_REASON_OK = "verify_pass"
CLOSE_GATE_REASON_NO_VERIFY = "verification_missing"
CLOSE_GATE_REASON_NOT_PASS = "verify_not_pass"


# ---------------------------------------------------------------------------
# execution_result
# ---------------------------------------------------------------------------

def record_execution(task_id, payload, *, _post_insert_hook=None):
    """Speichert ein execution_result gemaess Technical Spec §2.4.

    Sprint Workflow-Finalization Session 2 (2026-04-18) — Haertungen:
      * AC2-2: Pro Task darf es nur ein Execution-Result geben. Zweiter
        Aufruf (seriell oder nebenlaeufig) wirft `ExecutionAlreadyRecordedError`.
        Nebenlaeufigkeit wird durch DB-UNIQUE(task_id)-Constraint gesichert;
        UniqueViolation aus psycopg2 wird hier in denselben Fehlertyp
        uebersetzt. Der App-Level-Check vor dem INSERT macht den Normalfall
        billig.
      * AC2-3: Der Post-Processing-Pfad nach dem INSERT ist mit einem
        DELETE-Rollback abgesichert. Exceptions nach dem INSERT (z.B. vom
        optionalen `_post_insert_hook`, der nur in Tests genutzt wird)
        hinterlassen die DB im Pre-Insert-Zustand.
    """
    ensure_agent_verify_schema()

    if not get_task(task_id):
        raise ValueError(f"task {task_id} nicht gefunden")

    existing = get_execution(task_id)
    if existing is not None:
        raise ExecutionAlreadyRecordedError(task_id, existing.get("id"))

    payload = payload or {}
    try:
        row = execute(
            """
            INSERT INTO agent_execution_results (
                task_id, agent, started_at, finished_at,
                changed_files_json, created_files_json, deleted_files_json,
                claims_json, summary, diff_stat_text, out_of_scope_files_json
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb)
            RETURNING id, created_at
            """,
            (
                task_id,
                payload.get("agent"),
                payload.get("started_at"),
                payload.get("finished_at"),
                json.dumps(payload.get("changed_files") or []),
                json.dumps(payload.get("created_files") or []),
                json.dumps(payload.get("deleted_files") or []),
                json.dumps(payload.get("claims") or []),
                payload.get("summary"),
                payload.get("diff_stat_text"),
                json.dumps(payload.get("out_of_scope_files") or []),
            ),
            fetchone=True,
        )
    except Exception as exc:
        if _is_unique_violation(exc):
            existing = get_execution(task_id)
            raise ExecutionAlreadyRecordedError(
                task_id, existing.get("id") if existing else None
            ) from exc
        raise

    if not row:
        raise RuntimeError("agent_execution_results insert lieferte keine Zeile zurueck")

    execution_id = row["id"]
    try:
        if _post_insert_hook is not None:
            _post_insert_hook(execution_id)
        return _execution_row_to_dict({
            "id": execution_id,
            "task_id": task_id,
            "agent": payload.get("agent"),
            "started_at": payload.get("started_at"),
            "finished_at": payload.get("finished_at"),
            "changed_files_json": payload.get("changed_files") or [],
            "created_files_json": payload.get("created_files") or [],
            "deleted_files_json": payload.get("deleted_files") or [],
            "claims_json": payload.get("claims") or [],
            "summary": payload.get("summary"),
            "diff_stat_text": payload.get("diff_stat_text"),
            "out_of_scope_files_json": payload.get("out_of_scope_files") or [],
            "created_at": row["created_at"],
        })
    except Exception:
        # AC2-3: Rollback per DELETE, damit die DB im Pre-Insert-Zustand bleibt.
        try:
            execute(
                "DELETE FROM agent_execution_results WHERE id = %s",
                (execution_id,),
            )
        except Exception:
            pass
        raise


def _is_unique_violation(exc):
    """Best-effort-Erkennung einer psycopg2 UniqueViolation.

    Wir importieren psycopg2.errors nicht hart, damit der Service in Tests
    ohne laufendes PostgreSQL importierbar bleibt.
    """
    try:
        from psycopg2 import errors as pg_errors  # type: ignore
        if isinstance(exc, pg_errors.UniqueViolation):
            return True
    except Exception:
        pass
    pgcode = getattr(exc, "pgcode", None)
    if pgcode == "23505":
        return True
    msg = str(exc).lower()
    return "unique constraint" in msg or "uq_agent_execution_task" in msg


def get_execution(task_id):
    """Liefert das juengste execution_result fuer einen Task oder None."""
    ensure_agent_verify_schema()
    row = execute(
        """
        SELECT id, task_id, agent, started_at, finished_at,
               changed_files_json, created_files_json, deleted_files_json,
               claims_json, summary, diff_stat_text, out_of_scope_files_json,
               created_at
        FROM agent_execution_results
        WHERE task_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (task_id,),
        fetchone=True,
    )
    if not row:
        return None
    return _execution_row_to_dict(row)


def _execution_row_to_dict(row):
    return {
        "id": row.get("id"),
        "task_id": row.get("task_id"),
        "agent": row.get("agent"),
        "started_at": _iso(row.get("started_at")),
        "finished_at": _iso(row.get("finished_at")),
        "changed_files": _as_list(row.get("changed_files_json")),
        "created_files": _as_list(row.get("created_files_json")),
        "deleted_files": _as_list(row.get("deleted_files_json")),
        "claims": _as_list(row.get("claims_json")),
        "summary": row.get("summary"),
        "diff_stat_text": row.get("diff_stat_text"),
        "out_of_scope_files": _as_list(row.get("out_of_scope_files_json")),
        "created_at": _iso(row.get("created_at")),
    }


# ---------------------------------------------------------------------------
# Close-Gate
# ---------------------------------------------------------------------------

def evaluate_close(task_id):
    """Berechnet close_decision ohne Seiteneffekt.

    Rueckgabe gemaess Technical Spec §2.6:
      { task_id, can_close, reason, required_actions }
    """
    verify = get_verify_gate(task_id)
    if not verify:
        return {
            "task_id": task_id,
            "can_close": False,
            "reason": CLOSE_GATE_REASON_NO_VERIFY,
            "required_actions": ["run verify gate", "attach execution_result"],
            "verify": None,
        }
    if verify.get("status") != VERIFY_STATUS_PASS:
        return {
            "task_id": task_id,
            "can_close": False,
            "reason": CLOSE_GATE_REASON_NOT_PASS,
            "required_actions": [
                "resolve unverified claims: " + ", ".join(verify.get("unverified_claims") or []) or "re-run verify gate",
            ],
            "verify": verify,
        }
    return {
        "task_id": task_id,
        "can_close": True,
        "reason": CLOSE_GATE_REASON_OK,
        "required_actions": [],
        "verify": verify,
    }


def close_task(task_id, *, session_id=None):
    """Schliesst einen Task nur bei verify=pass.

    Wenn ein session_id uebergeben ist, wird der Session-State auf `done`
    gesetzt. Rueckgabe enthaelt `decision` und ggf. `session_state`.
    """
    if not get_task(task_id):
        raise ValueError(f"task {task_id} nicht gefunden")

    decision = evaluate_close(task_id)
    result: dict = {"decision": decision}
    if decision["can_close"] and session_id:
        new_state = set_session_state(
            session_id,
            "done",
            reason=f"task {task_id} closed",
        )
        if new_state is not None:
            result["session_state"] = new_state
    return result
