"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 2, 2026-04-17):
Tests fuer den Verify-Gate MVP.

Fokus auf Akzeptanzkriterien AC1-AC4:
  AC1: tests_passed ohne echten Command-Exit -> blocked
  AC2: tests_passed mit Exit 0 -> pass
  AC3: close ohne verify=pass wird abgelehnt
  AC4: execution_result + verify_gate_result via API lesbar

Datenbank wird komplett durch einen In-Memory-Fake ersetzt, analog zu
tests/test_agent_orchestrator.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Tuple

import pytest

import services.agent_orchestrator_service as orchestrator
import services.agent_verify_service as verify_service


@pytest.fixture
def fake_db(monkeypatch):
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
            # neuester zuerst
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


# ---------------------------------------------------------------------------
# execution_result
# ---------------------------------------------------------------------------

def _make_task(required_verification=None, allowed_files=None):
    payload = {
        "title": "Phase 2 Test",
        "session_id": "ses_t1",
        "allowed_files": allowed_files if allowed_files is not None else ["tests/test_x.py"],
        "required_verification": required_verification or [],
    }
    return orchestrator.create_task(payload)


def test_record_execution_persists_payload(fake_db):
    task = _make_task()
    result = verify_service.record_execution(task["task_id"], {
        "agent": "claude_code",
        "changed_files": ["tests/test_x.py"],
        "claims": [{"type": "tests_passed", "value": True}],
        "summary": "done",
    })
    assert result["task_id"] == task["task_id"]
    assert result["agent"] == "claude_code"
    assert result["changed_files"] == ["tests/test_x.py"]
    assert result["claims"][0]["type"] == "tests_passed"

    latest = verify_service.get_execution(task["task_id"])
    assert latest["id"] == result["id"]
    assert latest["summary"] == "done"


def test_record_execution_rejects_unknown_task(fake_db):
    with pytest.raises(ValueError):
        verify_service.record_execution(9999, {"summary": "nope"})


# ---------------------------------------------------------------------------
# Sprint sprint-agent-orchestrator-execution-payload-fix Commit 1:
# Neue Felder diff_stat_text + out_of_scope_files im Execution-Payload.
# ---------------------------------------------------------------------------

def test_record_execution_persists_diff_stat_and_out_of_scope(fake_db):
    task = _make_task(allowed_files=["tests/test_x.py"])
    result = verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py", "services/secret.py"],
        "diff_stat_text": " tests/test_x.py | 2 +-\n services/secret.py | 5 +++++",
        "out_of_scope_files": ["services/secret.py"],
    })
    assert result["diff_stat_text"].startswith(" tests/test_x.py")
    assert result["out_of_scope_files"] == ["services/secret.py"]

    # Direkt aus dem Fake-Row-Store pruefen, dass beide Spalten persistiert sind.
    stored = fake_db["executions"][-1]
    assert stored["diff_stat_text"].startswith(" tests/test_x.py")
    assert stored["out_of_scope_files_json"] == ["services/secret.py"]


def test_record_execution_empty_payload_defaults_diff_stat_and_out_of_scope(fake_db):
    task = _make_task()
    result = verify_service.record_execution(task["task_id"], {})
    assert result["diff_stat_text"] is None
    assert result["out_of_scope_files"] == []

    stored = fake_db["executions"][-1]
    assert stored["diff_stat_text"] is None
    assert stored["out_of_scope_files_json"] == []


def test_get_execution_roundtrip_includes_diff_stat_and_out_of_scope(fake_db):
    task = _make_task(allowed_files=["tests/test_x.py"])
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py", "services/secret.py"],
        "diff_stat_text": "diff --stat output",
        "out_of_scope_files": ["services/secret.py"],
        "summary": "roundtrip",
    })

    latest = verify_service.get_execution(task["task_id"])
    assert latest is not None
    assert latest["diff_stat_text"] == "diff --stat output"
    assert latest["out_of_scope_files"] == ["services/secret.py"]
    assert latest["summary"] == "roundtrip"


# ---------------------------------------------------------------------------
# AC1 — tests_passed ohne Command-Exit -> blocked
# ---------------------------------------------------------------------------

def test_ac1_tests_passed_without_runner_is_blocked(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest -q", "claim": "tests_passed"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [{"type": "tests_passed", "value": True}],
    })

    # Kein command_runner uebergeben -> blocked, tests_passed unverified
    gate = verify_service.run_verify_gate(task["task_id"])

    assert gate["status"] == "blocked"
    assert "tests_passed" in gate["unverified_claims"]
    rv_checks = [c for c in gate["checks"] if c["type"] == "required_verification"]
    assert any(c["status"] == "blocked" and c["claim"] == "tests_passed" for c in rv_checks)


# ---------------------------------------------------------------------------
# AC2 — tests_passed mit Exit 0 -> pass
# ---------------------------------------------------------------------------

def test_ac2_tests_passed_with_exit_zero_is_pass(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest -q", "claim": "tests_passed"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [{"type": "tests_passed", "value": True}],
    })

    calls = []

    def runner(cmd):
        calls.append(cmd)
        return 0, "5 passed"

    gate = verify_service.run_verify_gate(task["task_id"], command_runner=runner)

    assert gate["status"] == "pass"
    assert gate["unverified_claims"] == []
    assert calls == ["pytest -q"]
    rv_checks = [c for c in gate["checks"] if c["type"] == "required_verification"]
    assert any(c["status"] == "pass" and c["claim"] == "tests_passed" for c in rv_checks)


def test_verify_gate_exit_nonzero_is_fail(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest -q", "claim": "tests_passed"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [],
    })

    gate = verify_service.run_verify_gate(
        task["task_id"],
        command_runner=lambda cmd: (1, "FAILED tests/test_x.py::test_a"),
    )
    assert gate["status"] == "fail"
    assert "tests_passed" in gate["unverified_claims"]


def test_verify_gate_scope_violation_is_fail(fake_db):
    task = _make_task(allowed_files=["tests/test_x.py"])
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py", "services/secret.py"],
        "claims": [],
    })

    gate = verify_service.run_verify_gate(task["task_id"])
    scope_check = next(c for c in gate["checks"] if c["type"] == "scope_enforcement")
    assert scope_check["status"] == "fail"
    assert gate["status"] == "fail"


def test_verify_gate_smoke_test_evidence_required(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "smoke_test_evidence", "claim": "smoke_test_done"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [{"type": "smoke_test_done", "value": True}],  # ohne evidence
    })
    gate1 = verify_service.run_verify_gate(task["task_id"])
    assert gate1["status"] == "blocked"
    assert "smoke_test_done" in gate1["unverified_claims"]

    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [{
            "type": "smoke_test_done",
            "value": True,
            "evidence": "curl http://localhost:5055/health -> 200 OK",
        }],
    })
    gate2 = verify_service.run_verify_gate(task["task_id"])
    assert gate2["status"] == "pass"


def test_feature_complete_requires_all_checks_pass(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest -q", "claim": "tests_passed"},
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [
            {"type": "tests_passed", "value": True},
            {"type": "feature_complete", "value": True},
        ],
    })
    # tests_passed wird nicht geprueft (kein runner) -> feature_complete nicht belegbar
    gate = verify_service.run_verify_gate(task["task_id"])
    assert gate["status"] == "blocked"
    assert "feature_complete" in gate["unverified_claims"]


# ---------------------------------------------------------------------------
# AC3 — Close-Gate blockt ohne verify=pass
# ---------------------------------------------------------------------------

def test_ac3_close_rejected_without_verify(fake_db):
    task = _make_task()
    result = verify_service.close_task(task["task_id"])
    assert result["decision"]["can_close"] is False
    assert result["decision"]["reason"] == "verification_missing"


def test_ac3_close_rejected_when_verify_not_pass(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest", "claim": "tests_passed"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [],
    })
    verify_service.run_verify_gate(task["task_id"])  # blocked

    result = verify_service.close_task(task["task_id"])
    assert result["decision"]["can_close"] is False
    assert result["decision"]["reason"] == "verify_not_pass"


def test_ac3_close_ok_when_verify_pass_sets_session_done(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest", "claim": "tests_passed"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["tests/test_x.py"],
        "claims": [{"type": "tests_passed", "value": True}],
    })
    verify_service.run_verify_gate(
        task["task_id"],
        command_runner=lambda cmd: (0, "ok"),
    )

    result = verify_service.close_task(task["task_id"], session_id="ses_t1")
    assert result["decision"]["can_close"] is True
    assert result["decision"]["reason"] == "verify_pass"
    assert result["session_state"]["state"] == "done"


# ---------------------------------------------------------------------------
# AC4 — Lesbarkeit der letzten Ergebnisse
# ---------------------------------------------------------------------------

def test_ac4_execution_and_verify_readable_after_write(fake_db):
    task = _make_task(
        required_verification=[
            {"type": "command_exit_zero", "command": "pytest", "claim": "tests_passed"}
        ],
    )
    verify_service.record_execution(task["task_id"], {
        "agent": "claude_code",
        "changed_files": ["tests/test_x.py"],
        "claims": [{"type": "tests_passed", "value": True}],
        "summary": "added test",
    })
    verify_service.run_verify_gate(
        task["task_id"],
        command_runner=lambda cmd: (0, "ok"),
    )

    exec_read = verify_service.get_execution(task["task_id"])
    verify_read = verify_service.get_verify_gate(task["task_id"])

    assert exec_read is not None
    assert exec_read["summary"] == "added test"
    assert verify_read is not None
    assert verify_read["status"] == "pass"
    assert verify_read["execution_result_id"] == exec_read["id"]


def test_default_command_runner_executes_true():
    # Muss echt ein Exit-0-Kommando laufen lassen, aber ohne Datenbank-Zugriff.
    rc, out = verify_service.default_command_runner("true")
    assert rc == 0
