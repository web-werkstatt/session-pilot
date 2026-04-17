"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 3, 2026-04-17):
Tests fuer Recovery-Snapshot + API-Endpoint.

Fokus auf AC4 aus §spec-phase3-akzeptanz:
  AC4: Recovery-API speichert Snapshot und setzt State auf `recovery`

Zusaetzlich abgedeckt:
  * build_recovery_snapshot liest git status + risk_flags korrekt zusammen
  * persist_recovery_snapshot setzt previous_state aus dem letzten State

Datenbank wird komplett durch einen In-Memory-Fake ersetzt, analog
tests/test_agent_verify.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import services.agent_orchestrator_service as orchestrator
import services.agent_recovery_snapshot as recovery


@pytest.fixture
def fake_db(monkeypatch):
    states: dict[str, dict] = {}

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
        p = tuple(params or ())

        if q.startswith("insert into agent_session_states"):
            sid = p[0]
            existing = states.get(sid, {})
            row = {
                "session_id": sid,
                "state": p[1],
                "previous_state": p[2],
                "reason": p[3],
                "locked": bool(p[4]),
                "blocking_issues_json": _as_json(p[5]),
                "recovery_snapshot_json": _as_json(p[6]) if len(p) > 6 else existing.get("recovery_snapshot_json"),
                "updated_at": _now(),
            }
            states[sid] = row
            return None

        if q.startswith("select session_id, state, previous_state") and "from agent_session_states" in q:
            s = states.get(p[0])
            return dict(s) if s else None

        return None

    monkeypatch.setattr(orchestrator, "execute", fake_execute)
    monkeypatch.setattr(orchestrator, "ensure_agent_orchestrator_schema", lambda: None)
    monkeypatch.setattr(recovery, "execute", fake_execute)
    monkeypatch.setattr(recovery, "ensure_agent_orchestrator_schema", lambda: None)
    return {"states": states}


def _make_git_runner(status_out="", diff_out=""):
    def runner(args):
        if args[:2] == ["status", "--short"]:
            return 0, status_out
        if args[:1] == ["diff"]:
            return 0, diff_out
        if args[:1] == ["branch"]:
            return 0, "main\n"
        return 0, ""
    return runner


def test_build_snapshot_collects_git_state():
    status = (
        " M next-session.md\n"
        "?? sprints/new.md\n"
    )
    diff = " next-session.md | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)\n"
    snap = recovery.build_recovery_snapshot(
        repo_path="/tmp/fake",
        git_runner=_make_git_runner(status, diff),
    )
    assert snap["git_status_short"] == status
    assert snap["diff_stat"] == diff
    assert "next-session.md" in snap["modified_files"]
    assert "sprints/new.md" in snap["untracked_files"]
    assert "dirty_worktree" in snap["risk_flags"]
    assert "sensitive_file_touched" in snap["risk_flags"]
    assert snap["sensitive_files_touched"] == ["next-session.md"]
    # ISO 8601 mit TZ
    assert snap["created_at"].endswith("+00:00")


def test_persist_snapshot_sets_state_to_recovery(fake_db):
    # Vorheriger State existiert als 'implement' — wird zu previous_state.
    orchestrator.set_session_state("ses_r1", "implement", reason="vorher")

    snap = {
        "git_status_short": " M handoff.md\n",
        "risk_flags": ["sensitive_file_touched"],
    }
    state = recovery.persist_recovery_snapshot(
        "ses_r1", snap, reason="scope violation detected",
    )
    assert state["state"] == "recovery"
    assert state["previous_state"] == "implement"
    assert state["reason"] == "scope violation detected"
    assert state["recovery_snapshot"]["risk_flags"] == ["sensitive_file_touched"]


def test_persist_snapshot_rejects_empty_session_id(fake_db):
    with pytest.raises(ValueError):
        recovery.persist_recovery_snapshot("", {"risk_flags": []})


def test_ac4_recovery_api_persists_snapshot_and_sets_state(fake_db, monkeypatch):
    """AC4 via Flask test client — kompletter Roundtrip."""
    # Default-Git-Runner darf nicht als Subprocess auf dem Host laufen.
    monkeypatch.setattr(
        recovery,
        "_default_git_runner",
        lambda repo_path: _make_git_runner(
            " M next-session.md\n", " next-session.md | 1 +\n",
        ),
    )
    # Session-State wird durch die API neu angelegt (kein vorheriger State).
    from app import app

    client = app.test_client()
    resp = client.post(
        "/api/agent-sessions/ses_r2/recover",
        json={"reason": "preflight scope_violation"},
    )
    assert resp.status_code == 201, resp.data
    body = resp.get_json()
    assert body["session_state"]["state"] == "recovery"
    assert body["session_state"]["reason"] == "preflight scope_violation"
    snapshot = body["snapshot"]
    assert "sensitive_file_touched" in snapshot["risk_flags"]
    assert snapshot["modified_files"] == ["next-session.md"]

    # Snapshot ist am Session-State abgelegt.
    state_resp = client.get("/api/agent-sessions/ses_r2/state")
    assert state_resp.status_code == 200
    state = state_resp.get_json()
    assert state["state"] == "recovery"
    assert state["recovery_snapshot"]["modified_files"] == ["next-session.md"]


def test_ac4_recovery_api_accepts_explicit_snapshot(fake_db):
    """Payload kann einen explizit gebauten Snapshot uebergeben."""
    from app import app

    client = app.test_client()
    explicit = {
        "git_status_short": "",
        "risk_flags": [],
        "modified_files": [],
        "untracked_files": [],
        "sensitive_files_touched": [],
        "diff_stat": "",
        "created_at": "2026-04-17T00:00:00+00:00",
    }
    resp = client.post(
        "/api/agent-sessions/ses_r3/recover",
        json={"snapshot": explicit, "reason": "manual recovery"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["snapshot"] == explicit
    assert body["session_state"]["state"] == "recovery"
