"""
Verify-Gate-Logik des Agent-Orchestrators (ausgelagert aus
`agent_verify_service.py`, 2026-04-18).

Kapselt die reine Gate-Mechanik:
  * run_verify_gate(task_id, command_runner)
  * get_verify_gate(task_id)
  * _check_required_verification(...)

Die Execution-CRUD (record_execution / get_execution) sowie der
Close-Gate verbleiben in `agent_verify_service.py`, weil Tests dort
Modul-Attribute monkeypatchen (z.B. `verify_service.get_execution`).
"""
import json
from typing import Callable, Optional

from services.db_service import execute, ensure_agent_verify_schema
from services.agent_orchestrator_service import get_task, _as_list, _iso
from services.agent_append_only_diff import (
    check_append_only_required_verification,
    CLAIM_APPEND_ONLY_RESPECTED,
)
from services.agent_verify_claim_checks import (
    check_docs_updated as _check_docs_updated,
    load_project_config as _load_project_config,
)


CLAIM_TYPES_COMMAND = ("tests_passed", "syntax_check_passed")
CLAIM_TYPE_SMOKE = "smoke_test_done"
CLAIM_TYPE_FEATURE = "feature_complete"
CLAIM_TYPE_APPEND_ONLY = CLAIM_APPEND_ONLY_RESPECTED

VERIFY_STATUS_PASS = "pass"
VERIFY_STATUS_BLOCKED = "blocked"
VERIFY_STATUS_FAIL = "fail"


def run_verify_gate(task_id, *, command_runner: Optional[Callable] = None,
                    get_execution_fn: Optional[Callable] = None):
    """Fuehrt den Verify-Gate aus und persistiert das Ergebnis.

    `get_execution_fn` wird injiziert, damit Tests, die
    `verify_service.get_execution` monkeypatchen, weiterhin greifen.
    Default: `services.agent_verify_service.get_execution`.
    """
    ensure_agent_verify_schema()

    contract = get_task(task_id)
    if not contract:
        raise ValueError(f"task {task_id} nicht gefunden")

    if get_execution_fn is None:
        from services import agent_verify_service
        get_execution_fn = agent_verify_service.get_execution

    execution = get_execution_fn(task_id)
    execution_claims = list((execution or {}).get("claims") or [])
    changed_files = list((execution or {}).get("changed_files") or [])

    checks = []
    unverified = []

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

    runner = command_runner
    project_config = _load_project_config(contract.get("project_id"))
    for req in contract.get("required_verification") or []:
        check, failing_claim = _check_required_verification(
            req, execution_claims, runner,
            changed_files=changed_files,
            project_config=project_config,
        )
        checks.append(check)
        if failing_claim and check["status"] != VERIFY_STATUS_PASS:
            if failing_claim not in unverified:
                unverified.append(failing_claim)

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


def _check_required_verification(req, execution_claims, runner,
                                 *, changed_files=None, project_config=None):
    """Fuehrt einen einzelnen required_verification-Eintrag aus.

    Unterstuetzte Typen:
      * command_exit_zero  -> runner(command) muss Exit 0 liefern
      * smoke_test_evidence -> expliziter Beleg in execution.claims
      * append_only_diff   -> Append-only-Regel mit projekt-spezifischem Block-Regex
      * docs_updated       -> Doku-Diff gegen docs_paths der Project-Config

    Rueckgabe: (check_dict, claim_name_or_None)
    """
    claim = req.get("claim") or req.get("type")
    rtype = req.get("type")
    project_config = project_config or {}

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
        return check_append_only_required_verification(
            req,
            block_start_regex=project_config.get("append_only_block_start_regex"),
            block_end_regex=project_config.get("append_only_block_end_regex"),
        )

    if rtype == "docs_updated":
        return _check_docs_updated(req, runner, changed_files or [], project_config)

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
