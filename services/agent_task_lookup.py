"""
Sprint sprint-agent-orchestrator-workflow-finalization §spec-session-1-ui
(2026-04-18): Lese-/Lookup-Pfade fuer Tasks.

Aus `services/agent_orchestrator_service.py` ausgelagert, damit der
Haupt-Service unter dem 500-Zeilen-Limit bleibt. Externe Importpfade
aendern sich nicht — `agent_orchestrator_service` re-exportiert
`list_tasks` und `get_task_for_marker` unveraendert.

Zugriffsstrategie auf DB:
Die Funktionen dereferenzieren `execute` + `ensure_*_schema` IMMER ueber
`_orchestrator.<attr>`, damit Tests die Attribute per monkeypatch auf
dem Haupt-Service austauschen koennen (`monkeypatch.setattr(orchestrator,
"execute", fake_execute)` — wirkt ohne Zusatzpatch auch hier).
"""
from services import agent_orchestrator_service as _orchestrator


def list_tasks(status: "str | None" = None, limit: "int | str | None" = 50):
    """Listet Tasks in der Reihenfolge created_at DESC.

    Parameter:
      * status: None | "open" | "closed"
        - "open"   = noch kein verify_gate_result mit next_state='done'
        - "closed" = bereits mindestens ein verify_gate_result mit next_state='done'
      * limit: max. Anzahl Zeilen (geclamped auf [1, 500], Default 50)

    Rueckgabe: list[dict], jeder Eintrag ist ein Task-Contract erweitert um
    `verify_status`, `is_closed`, `has_execution`.
    """
    _orchestrator.ensure_agent_orchestrator_schema()
    _orchestrator.ensure_agent_verify_schema()

    try:
        limit_int = int(limit) if limit is not None else 50
    except (TypeError, ValueError):
        limit_int = 50
    limit_int = max(1, min(500, limit_int))

    rows = _orchestrator.execute(
        """
        SELECT id, session_id, title, goal, mode,
               allowed_files_json, forbidden_actions_json,
               required_verification_json, required_outputs_json,
               stop_conditions_json, project_id,
               marker_id, source_plan_id, created_at
        FROM agent_task_contracts
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit_int,),
        fetch=True,
    ) or []

    result = []
    for row in rows:
        contract = _orchestrator._task_row_to_contract(row)
        verify = _latest_verify_summary(contract["task_id"])
        contract["verify_status"] = verify.get("status") if verify else None
        contract["is_closed"] = bool(verify and verify.get("next_state") == "done")
        contract["has_execution"] = _has_execution(contract["task_id"])
        if status == "open" and contract["is_closed"]:
            continue
        if status == "closed" and not contract["is_closed"]:
            continue
        result.append(contract)
    return result


def _latest_verify_summary(task_id):
    return _orchestrator.execute(
        """
        SELECT status, next_state
        FROM agent_verify_results
        WHERE task_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (task_id,),
        fetchone=True,
    )


def _has_execution(task_id):
    row = _orchestrator.execute(
        "SELECT 1 AS present FROM agent_execution_results WHERE task_id = %s LIMIT 1",
        (task_id,),
        fetchone=True,
    )
    return row is not None


def get_task_for_marker(marker_id, *, open_only=True):
    """Aktuellster Task fuer einen Marker, oder None.

    open_only=True (Default): nur Tasks ohne Verify-Pass (next_state='done').
    """
    if not marker_id:
        return None
    _orchestrator.ensure_agent_orchestrator_schema()
    _orchestrator.ensure_agent_verify_schema()
    done_filter = (
        "AND NOT EXISTS (SELECT 1 FROM agent_verify_results v "
        "WHERE v.task_id = atc.id AND v.next_state = 'done')"
        if open_only else ""
    )
    sql = f"""
        SELECT atc.id, atc.session_id, atc.title, atc.goal, atc.mode,
               atc.allowed_files_json, atc.forbidden_actions_json,
               atc.required_verification_json, atc.required_outputs_json,
               atc.stop_conditions_json, atc.project_id,
               atc.marker_id, atc.source_plan_id, atc.created_at
        FROM agent_task_contracts atc
        WHERE atc.marker_id = %s {done_filter}
        ORDER BY atc.created_at DESC LIMIT 1
    """
    row = _orchestrator.execute(sql, (str(marker_id).strip(),), fetchone=True)
    return _orchestrator._task_row_to_contract(row) if row else None
