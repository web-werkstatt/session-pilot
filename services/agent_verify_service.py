"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 2, 2026-04-17):
Verify-Gate MVP fuer den Agent-Orchestrator.

Kapselt:
  * record_execution(task_id, payload)         -> speichert execution_result
  * get_execution(task_id)                     -> letzter execution_result
  * run_verify_gate(task_id, command_runner)   -> berechnet + speichert verify_gate_result
  * get_verify_gate(task_id)                   -> letzter verify_gate_result
  * close_task(task_id)                        -> close_decision + Session-State

Claim-Typen v1 in diesem Service (ohne append_only_respected / docs_updated,
die in Phase 3 folgen):
  * tests_passed         -> Exit-Code-0-Check via command_runner
  * syntax_check_passed  -> Exit-Code-0-Check via command_runner
  * smoke_test_done      -> expliziter Beleg in execution.claims
  * feature_complete     -> alle anderen Pflicht-Checks pass

Command-Runner wird per Dependency-Injection uebergeben. Default ist ein
subprocess-basierter Runner mit Timeout, damit der Service in Tests ohne
echten Prozess laeuft.
"""
import json
import subprocess
from typing import Callable, Optional

from services.db_service import execute, ensure_agent_verify_schema
from services.agent_orchestrator_service import (
    get_task,
    set_session_state,
    _as_list,
    _iso,
)
from services.agent_append_only_diff import (
    check_append_only_required_verification,
    CLAIM_APPEND_ONLY_RESPECTED,
)


CLOSE_GATE_REASON_OK = "verify_pass"
CLOSE_GATE_REASON_NO_VERIFY = "verification_missing"
CLOSE_GATE_REASON_NOT_PASS = "verify_not_pass"

CLAIM_TYPES_COMMAND = ("tests_passed", "syntax_check_passed")
CLAIM_TYPE_SMOKE = "smoke_test_done"
CLAIM_TYPE_FEATURE = "feature_complete"
CLAIM_TYPE_APPEND_ONLY = CLAIM_APPEND_ONLY_RESPECTED

VERIFY_STATUS_PASS = "pass"
VERIFY_STATUS_BLOCKED = "blocked"
VERIFY_STATUS_FAIL = "fail"


# ---------------------------------------------------------------------------
# execution_result
# ---------------------------------------------------------------------------

def record_execution(task_id, payload):
    """Speichert ein execution_result gemaess Technical Spec §2.4.

    Pflichtfelder: task_id. Alle Listen/Claims sind defensiv.
    Rueckgabe: persistiertes execution_result als dict.
    """
    ensure_agent_verify_schema()

    if not get_task(task_id):
        raise ValueError(f"task {task_id} nicht gefunden")

    payload = payload or {}
    row = execute(
        """
        INSERT INTO agent_execution_results (
            task_id, agent, started_at, finished_at,
            changed_files_json, created_files_json, deleted_files_json,
            claims_json, summary
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
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
        ),
        fetchone=True,
    )
    if not row:
        raise RuntimeError("agent_execution_results insert lieferte keine Zeile zurueck")
    return _execution_row_to_dict({
        "id": row["id"],
        "task_id": task_id,
        "agent": payload.get("agent"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "changed_files_json": payload.get("changed_files") or [],
        "created_files_json": payload.get("created_files") or [],
        "deleted_files_json": payload.get("deleted_files") or [],
        "claims_json": payload.get("claims") or [],
        "summary": payload.get("summary"),
        "created_at": row["created_at"],
    })


def get_execution(task_id):
    """Liefert das juengste execution_result fuer einen Task oder None."""
    ensure_agent_verify_schema()
    row = execute(
        """
        SELECT id, task_id, agent, started_at, finished_at,
               changed_files_json, created_files_json, deleted_files_json,
               claims_json, summary, created_at
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
        "created_at": _iso(row.get("created_at")),
    }


# ---------------------------------------------------------------------------
# verify_gate_result
# ---------------------------------------------------------------------------

def run_verify_gate(task_id, *, command_runner: Optional[Callable] = None):
    """Fuehrt den Verify-Gate aus und persistiert das Ergebnis.

    Ablauf:
      1. Task-Contract laden (sonst ValueError)
      2. Letztes execution_result lesen (None -> Gate laeuft gegen leere Fakten)
      3. Checks ausfuehren:
         - scope_enforcement gegen allowed_files
         - pro required_verification-Eintrag (command_exit_zero / smoke_test_evidence)
         - feature_complete, wenn vom Agenten behauptet
      4. status aggregieren (fail > blocked > pass)
      5. persistieren
    """
    ensure_agent_verify_schema()

    contract = get_task(task_id)
    if not contract:
        raise ValueError(f"task {task_id} nicht gefunden")

    execution = get_execution(task_id)
    execution_claims = list((execution or {}).get("claims") or [])
    changed_files = list((execution or {}).get("changed_files") or [])

    checks = []
    unverified = []

    # scope_enforcement
    allowed = list(contract.get("allowed_files") or [])
    if allowed:
        out_of_scope = [p for p in changed_files if p not in allowed]
        if out_of_scope:
            checks.append({
                "type": "scope_enforcement",
                "status": VERIFY_STATUS_FAIL,
                "details": f"out_of_scope_files: {out_of_scope}",
            })
        else:
            checks.append({
                "type": "scope_enforcement",
                "status": VERIFY_STATUS_PASS,
                "details": "all changed files within allowed_files",
            })
    elif changed_files:
        checks.append({
            "type": "scope_enforcement",
            "status": VERIFY_STATUS_FAIL,
            "details": "allowed_files empty but execution has changed_files",
        })
    else:
        checks.append({
            "type": "scope_enforcement",
            "status": VERIFY_STATUS_PASS,
            "details": "no changed files, no allowed_files scope to enforce",
        })

    # required_verification pro Eintrag
    runner = command_runner  # keine Default-Ausfuehrung bis explizit injiziert
    for req in contract.get("required_verification") or []:
        check, failing_claim = _check_required_verification(req, execution_claims, runner)
        checks.append(check)
        if failing_claim and check["status"] != VERIFY_STATUS_PASS:
            if failing_claim not in unverified:
                unverified.append(failing_claim)

    # feature_complete: nur falls der Agent das behauptet
    if _claim_asserted(execution_claims, CLAIM_TYPE_FEATURE):
        other_fail = any(
            c.get("status") != VERIFY_STATUS_PASS and c.get("type") != CLAIM_TYPE_FEATURE
            for c in checks
        )
        if other_fail:
            checks.append({
                "type": CLAIM_TYPE_FEATURE,
                "status": VERIFY_STATUS_BLOCKED,
                "details": "feature_complete claimed but other checks not all pass",
            })
            if CLAIM_TYPE_FEATURE not in unverified:
                unverified.append(CLAIM_TYPE_FEATURE)
        else:
            checks.append({
                "type": CLAIM_TYPE_FEATURE,
                "status": VERIFY_STATUS_PASS,
                "details": "all required checks pass",
            })

    # Aggregation: fail > blocked > pass
    statuses = [c.get("status") for c in checks]
    if VERIFY_STATUS_FAIL in statuses:
        overall = VERIFY_STATUS_FAIL
    elif VERIFY_STATUS_BLOCKED in statuses:
        overall = VERIFY_STATUS_BLOCKED
    else:
        overall = VERIFY_STATUS_PASS

    next_state = "done" if overall == VERIFY_STATUS_PASS else "implement"

    exec_id = (execution or {}).get("id")
    row = execute(
        """
        INSERT INTO agent_verify_results (
            task_id, status, checks_json, unverified_claims_json,
            next_state, execution_result_id
        )
        VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s)
        RETURNING id, created_at
        """,
        (
            task_id,
            overall,
            json.dumps(checks),
            json.dumps(unverified),
            next_state,
            exec_id,
        ),
        fetchone=True,
    )
    if not row:
        raise RuntimeError("agent_verify_results insert lieferte keine Zeile zurueck")

    return {
        "id": row["id"],
        "task_id": task_id,
        "status": overall,
        "checks": checks,
        "unverified_claims": unverified,
        "next_state": next_state,
        "execution_result_id": exec_id,
        "created_at": _iso(row["created_at"]),
    }


def get_verify_gate(task_id):
    """Liefert das juengste verify_gate_result fuer einen Task oder None."""
    ensure_agent_verify_schema()
    row = execute(
        """
        SELECT id, task_id, status, checks_json, unverified_claims_json,
               next_state, execution_result_id, created_at
        FROM agent_verify_results
        WHERE task_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (task_id,),
        fetchone=True,
    )
    if not row:
        return None
    return {
        "id": row.get("id"),
        "task_id": row.get("task_id"),
        "status": row.get("status"),
        "checks": _as_list(row.get("checks_json")),
        "unverified_claims": _as_list(row.get("unverified_claims_json")),
        "next_state": row.get("next_state"),
        "execution_result_id": row.get("execution_result_id"),
        "created_at": _iso(row.get("created_at")),
    }


def _check_required_verification(req, execution_claims, runner):
    """Fuehrt einen einzelnen required_verification-Eintrag aus.

    Unterstuetzte Typen in Phase 2:
      * command_exit_zero  -> runner(command) muss Exit 0 liefern
      * smoke_test_evidence -> expliziter Beleg in execution.claims mit
        type=smoke_test_done, value=true, evidence/details nicht leer

    Rueckgabe: (check_dict, claim_name_or_None)
    """
    claim = req.get("claim") or req.get("type")
    rtype = req.get("type")

    if rtype == "command_exit_zero":
        command = req.get("command") or ""
        if runner is None:
            return ({
                "type": "required_verification",
                "status": VERIFY_STATUS_BLOCKED,
                "claim": claim,
                "details": f"command '{command}' not executed (no runner)",
            }, claim)
        rc, out = runner(command)
        if rc == 0:
            return ({
                "type": "required_verification",
                "status": VERIFY_STATUS_PASS,
                "claim": claim,
                "details": f"exit=0 command='{command}'",
            }, claim)
        return ({
            "type": "required_verification",
            "status": VERIFY_STATUS_FAIL,
            "claim": claim,
            "details": f"exit={rc} command='{command}' output={_truncate(out)}",
        }, claim)

    if rtype == "append_only_diff":
        # Phase 3: Diff-Regelpruefung, delegiert komplett an
        # services/agent_append_only_diff.py, damit die Verify-Service-Datei
        # keine Append-only-spezifische Logik traegt.
        return check_append_only_required_verification(req)

    if rtype == "smoke_test_evidence":
        evidence_ok = any(
            (
                c.get("type") == CLAIM_TYPE_SMOKE
                and c.get("value") is True
                and (c.get("evidence") or c.get("details"))
            )
            for c in execution_claims
        )
        if evidence_ok:
            return ({
                "type": "required_verification",
                "status": VERIFY_STATUS_PASS,
                "claim": claim,
                "details": "smoke_test_done claim with evidence present",
            }, claim)
        return ({
            "type": "required_verification",
            "status": VERIFY_STATUS_BLOCKED,
            "claim": claim,
            "details": "no smoke_test_done claim with evidence in execution_result",
        }, claim)

    # Unbekannter Typ -> blocked, damit unbekannte Checks nicht heimlich pass erzeugen
    return ({
        "type": "required_verification",
        "status": VERIFY_STATUS_BLOCKED,
        "claim": claim,
        "details": f"unknown required_verification type: {rtype}",
    }, claim)


def _claim_asserted(execution_claims, claim_type):
    for c in execution_claims:
        if c.get("type") == claim_type and c.get("value") is True:
            return True
    return False


def _truncate(text, limit=200):
    if text is None:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def default_command_runner(command, *, timeout=30, cwd=None):
    """Default-Runner fuer Command-Exit-Checks.

    Bewusst nicht automatisch aktiv: run_verify_gate nutzt ihn nur, wenn der
    Aufrufer ihn explizit uebergibt. Das haelt Tests und API-Aufrufe ohne
    Subprocess-Seiteneffekte stabil.
    """
    try:
        result = subprocess.run(
            command if isinstance(command, list) else command,
            shell=not isinstance(command, list),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except Exception as exc:
        return 1, f"command_runner_error: {exc}"


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
