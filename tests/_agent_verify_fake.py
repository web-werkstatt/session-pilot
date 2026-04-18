"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
Gemeinsame In-Memory-Fake-DB fuer Verify-Gate-Tests.

Ausgelagert, damit tests/test_agent_verify.py und
tests/test_agent_verify_project_config.py dieselbe Fixture-Quelle nutzen,
ohne Code zu duplizieren.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Tuple

import services.agent_orchestrator_service as orchestrator
import services.agent_verify_service as verify_service


def install_fake_db(monkeypatch):
    """Installiert einen In-Memory-Fake fuer orchestrator + verify_service.

    Rueckgabe: dict mit `contracts`, `states`, `executions`, `verifies`,
    damit Tests die persistierten Zustaende pruefen koennen.
    """
    contracts: dict[int, dict] = {}
    states: dict[str, dict] = {}
    executions: list[dict] = []
    verifies: list[dict] = []
    next_ids = {"task": 1, "exec": 1, "verify": 1}

    def _now():
        return datetime.now(timezone.utc)

    def _as_json(value):
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

    def fake_execute(query, params=None, fetch=False, fetchone=False):
        q = " ".join(str(query).lower().split())
        params_tuple: Tuple[Any, ...] = tuple(params or ())
        p = params_tuple

        if q.startswith("insert into agent_task_contracts"):
            tid = next_ids["task"]
            next_ids["task"] += 1
            contracts[tid] = {
                "id": tid,
                "session_id": p[0],
                "title": p[1],
                "goal": p[2],
                "mode": p[3],
                "allowed_files_json": _as_json(p[4]),
                "forbidden_actions_json": _as_json(p[5]),
                "required_verification_json": _as_json(p[6]),
                "required_outputs_json": _as_json(p[7]),
                "stop_conditions_json": _as_json(p[8]),
                "project_id": p[9] if len(p) > 9 else None,
                "created_at": _now(),
            }
            return {"id": tid, "created_at": contracts[tid]["created_at"]}

        if q.startswith("select id, session_id, title, goal, mode") and "from agent_task_contracts" in q:
            c = contracts.get(p[0])
            return dict(c) if c else None

        if q.startswith("insert into agent_session_states"):
            sid = p[0]
            states[sid] = {
                "session_id": sid,
                "state": p[1],
                "previous_state": p[2],
                "reason": p[3],
                "locked": bool(p[4]),
                "blocking_issues_json": _as_json(p[5]),
                "updated_at": _now(),
            }
            return None

        if q.startswith("select session_id, state, previous_state") and "from agent_session_states" in q:
            s = states.get(p[0])
            return dict(s) if s else None

        if q.startswith("insert into agent_execution_results"):
            eid = next_ids["exec"]
            next_ids["exec"] += 1
            row = {
                "id": eid,
                "task_id": p[0],
                "agent": p[1],
                "started_at": p[2],
                "finished_at": p[3],
                "changed_files_json": _as_json(p[4]),
                "created_files_json": _as_json(p[5]),
                "deleted_files_json": _as_json(p[6]),
                "claims_json": _as_json(p[7]),
                "summary": p[8],
                "diff_stat_text": p[9] if len(p) > 9 else None,
                "out_of_scope_files_json": _as_json(p[10]) if len(p) > 10 else [],
                "created_at": _now(),
            }
            executions.append(row)
            return {"id": eid, "created_at": row["created_at"]}

        if q.startswith("select id, task_id, agent, started_at") and "from agent_execution_results" in q:
            matches = [e for e in executions if e["task_id"] == p[0]]
            if not matches:
                return None
            return dict(matches[-1])

        if q.startswith("insert into agent_verify_results"):
            vid = next_ids["verify"]
            next_ids["verify"] += 1
            row = {
                "id": vid,
                "task_id": p[0],
                "status": p[1],
                "checks_json": _as_json(p[2]),
                "unverified_claims_json": _as_json(p[3]),
                "next_state": p[4],
                "execution_result_id": p[5],
                "created_at": _now(),
            }
            verifies.append(row)
            return {"id": vid, "created_at": row["created_at"]}

        if q.startswith("select id, task_id, status, checks_json") and "from agent_verify_results" in q:
            matches = [v for v in verifies if v["task_id"] == p[0]]
            if not matches:
                return None
            return dict(matches[-1])

        return None

    monkeypatch.setattr(orchestrator, "execute", fake_execute)
    monkeypatch.setattr(orchestrator, "ensure_agent_orchestrator_schema", lambda: None)
    monkeypatch.setattr(verify_service, "execute", fake_execute)
    monkeypatch.setattr(verify_service, "ensure_agent_verify_schema", lambda: None)
    return {
        "contracts": contracts,
        "states": states,
        "executions": executions,
        "verifies": verifies,
    }
