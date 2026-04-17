"""
Sprint sprint-agent-orchestrator-hardening-phase-1-foundation (2026-04-17):
Tests fuer Agent-Orchestrator Phase 1.

Fokus: Preflight-Logik mit gemocktem Git-Runner. Task-CRUD und Session-State
werden gegen einen In-Memory-Fake der `execute`-Funktion geprueft, damit kein
laufendes PostgreSQL erforderlich ist.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Tuple

import pytest

import services.agent_orchestrator_service as orchestrator
import services.agent_orchestrator_resolver as resolver


@pytest.fixture
def fake_db(monkeypatch):
    """Kleiner In-Memory-Store statt PostgreSQL fuer Task + State."""
    contracts: dict[int, dict] = {}
    states: dict[str, dict] = {}
    next_id = {"value": 1}

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
        params = params_tuple

        if q.startswith("insert into agent_task_contracts"):
            task_id = next_id["value"]
            next_id["value"] += 1
            contracts[task_id] = {
                "id": task_id,
                "session_id": params[0],
                "title": params[1],
                "goal": params[2],
                "mode": params[3],
                "allowed_files_json": _as_json(params[4]),
                "forbidden_actions_json": _as_json(params[5]),
                "required_verification_json": _as_json(params[6]),
                "required_outputs_json": _as_json(params[7]),
                "stop_conditions_json": _as_json(params[8]),
                "created_at": _now(),
            }
            return {"id": task_id, "created_at": contracts[task_id]["created_at"]}

        if q.startswith("select id, session_id, title, goal, mode") and "from agent_task_contracts" in q:
            contract = contracts.get(params[0])
            if not contract:
                return None
            return dict(contract)

        if q.startswith("select session_id, state, previous_state") and "from agent_session_states" in q:
            state = states.get(params[0])
            if not state:
                return None
            return dict(state)

        if q.startswith("insert into agent_session_states"):
            session_id = params[0]
            states[session_id] = {
                "session_id": session_id,
                "state": params[1],
                "previous_state": params[2],
                "reason": params[3],
                "locked": bool(params[4]),
                "blocking_issues_json": _as_json(params[5]),
                "updated_at": _now(),
            }
            return None

        return None

    monkeypatch.setattr(orchestrator, "execute", fake_execute)
    monkeypatch.setattr(orchestrator, "ensure_agent_orchestrator_schema", lambda: None)
    return {"contracts": contracts, "states": states}


# ---------------------------------------------------------------------------
# Task-Contract CRUD
# ---------------------------------------------------------------------------

def test_create_and_read_task_contract(fake_db):
    payload = {
        "title": "Phase 1 Foundation",
        "goal": "agent_task_contract + preflight",
        "allowed_files": ["tests/test_plan_discovery.py"],
        "forbidden_actions": ["git"],
        "required_verification": [{"type": "command_exit_zero", "command": "pytest"}],
    }
    contract = orchestrator.create_task(payload)

    assert contract["task_id"] == 1
    assert contract["title"] == "Phase 1 Foundation"
    assert contract["allowed_files"] == ["tests/test_plan_discovery.py"]
    assert contract["forbidden_actions"] == ["git"]
    assert contract["mode"] == "executor"

    again = orchestrator.get_task(1)
    assert again is not None
    assert again["title"] == contract["title"]
    assert again["required_verification"][0]["command"] == "pytest"


def test_create_task_rejects_empty_title(fake_db):
    with pytest.raises(ValueError):
        orchestrator.create_task({"title": "   "})


# ---------------------------------------------------------------------------
# Session-State
# ---------------------------------------------------------------------------

def test_session_state_tracks_previous_state(fake_db):
    first = orchestrator.set_session_state("ses_1", "inspect", reason="start")
    assert first["state"] == "inspect"
    assert first["previous_state"] is None

    second = orchestrator.set_session_state("ses_1", "implement", reason="go")
    assert second["state"] == "implement"
    assert second["previous_state"] == "inspect"
    assert second["reason"] == "go"


def test_session_state_rejects_invalid_state(fake_db):
    with pytest.raises(ValueError):
        orchestrator.set_session_state("ses_x", "wat")


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def _git_runner(branch="main", status_lines=None):
    status_lines = status_lines or []

    def _run(args):
        if args[:2] == ["branch", "--show-current"]:
            return 0, f"{branch}\n"
        if args[:2] == ["status", "--short"]:
            return 0, "\n".join(status_lines) + "\n"
        return 0, ""

    return _run


def test_preflight_ok_when_all_changes_in_scope(fake_db):
    contract = orchestrator.create_task({
        "title": "Scope Hit",
        "allowed_files": ["tests/test_plan_discovery.py"],
    })
    runner = _git_runner(status_lines=[" M tests/test_plan_discovery.py"])

    result = orchestrator.run_preflight(contract["task_id"], git_runner=runner)

    assert result["ok"] is True
    assert result["blocking_reason"] is None
    assert result["branch"] == "main"
    assert result["out_of_scope_files"] == []
    assert result["sensitive_files_touched"] == []
    assert "scope_violation" not in result["risk_flags"]


def test_preflight_blocks_on_out_of_scope_file(fake_db):
    contract = orchestrator.create_task({
        "title": "Scope Miss",
        "allowed_files": ["tests/test_plan_discovery.py"],
    })
    runner = _git_runner(status_lines=[
        " M tests/test_plan_discovery.py",
        " M services/path_resolver.py",
    ])

    result = orchestrator.run_preflight(contract["task_id"], git_runner=runner)

    assert result["ok"] is False
    assert result["blocking_reason"] == "out_of_scope_files_present"
    assert "services/path_resolver.py" in result["out_of_scope_files"]
    assert "scope_violation" in result["risk_flags"]
    assert result["dirty_worktree"] is True


def test_preflight_flags_sensitive_file(fake_db):
    contract = orchestrator.create_task({
        "title": "Sensitive Touch",
        "allowed_files": ["next-session.md"],
    })
    runner = _git_runner(status_lines=[" M next-session.md"])

    result = orchestrator.run_preflight(contract["task_id"], git_runner=runner)

    assert "next-session.md" in result["sensitive_files_touched"]
    assert "sensitive_file_touched" in result["risk_flags"]
    # Scope ist explizit erlaubt, daher kein scope_violation,
    # aber die Sensitive-File-Beruehrung muss weiterhin blocken.
    assert result["ok"] is False
    assert result["blocking_reason"] == "sensitive_file_touched"


def test_preflight_detects_untracked_files(fake_db):
    contract = orchestrator.create_task({
        "title": "Untracked",
        "allowed_files": ["tests/new_test.py"],
    })
    runner = _git_runner(status_lines=["?? tests/new_test.py"])

    result = orchestrator.run_preflight(contract["task_id"], git_runner=runner)

    assert result["untracked_files"] == ["tests/new_test.py"]
    assert result["modified_files"] == []
    assert result["dirty_worktree"] is True
    # Datei ist im Scope, daher ok=true trotz dirty_worktree (Scope deckt sie ab).
    assert result["ok"] is True


def test_preflight_raises_for_unknown_task(fake_db):
    with pytest.raises(ValueError):
        orchestrator.run_preflight(9999, git_runner=_git_runner())


# ---------------------------------------------------------------------------
# Handoff-/Marker-Resolver (Tag 3)
# ---------------------------------------------------------------------------

class _FakeMarker:
    """Minimale Marker-Stand-in-Dataclass fuer Resolver-Tests."""

    def __init__(self, marker_id, plan_id=None, titel="", status="todo",
                 ziel="", naechster_schritt="", last_session=""):
        self.marker_id = marker_id
        self.plan_id = plan_id
        self.titel = titel
        self.status = status
        self.ziel = ziel
        self.naechster_schritt = naechster_schritt
        self.last_session = last_session


def _fixed_handoff_path(_project_id):
    return "/tmp/does-not-exist/handoff.md"


def test_resolver_requires_project_id():
    with pytest.raises(ValueError):
        resolver.resolve_context("")


def test_resolver_returns_handoff_path_without_plan_or_marker():
    result = resolver.resolve_context(
        "demo_project",
        handoff_path_fn=_fixed_handoff_path,
    )
    assert result["project_id"] == "demo_project"
    assert result["handoff_path"] == "/tmp/does-not-exist/handoff.md"
    assert result["handoff_exists"] is False
    assert result["active_marker"] is None
    assert result["relevant_plan"] is None
    assert result["start_scope"] == []
    assert result["notes"] == []


def test_resolver_with_plan_id_sets_start_scope_from_source_path():
    plan_row = {
        "id": 42,
        "project_name": "demo_project",
        "title": "Sprint X",
        "status": "active",
        "source_path": "sprints/sprint-x.md",
        "source_kind": "project_sprints",
        "updated_at": None,
    }

    result = resolver.resolve_context(
        "demo_project",
        plan_id=42,
        plan_lookup=lambda pid: plan_row if int(pid) == 42 else None,
        handoff_path_fn=_fixed_handoff_path,
    )
    assert result["relevant_plan"]["id"] == 42
    assert result["relevant_plan"]["source_path"] == "sprints/sprint-x.md"
    assert result["start_scope"] == ["sprints/sprint-x.md"]
    assert result["notes"] == []


def test_resolver_with_unknown_plan_id_notes_not_found():
    result = resolver.resolve_context(
        "demo_project",
        plan_id=999,
        plan_lookup=lambda pid: None,
        handoff_path_fn=_fixed_handoff_path,
    )
    assert result["relevant_plan"] is None
    assert result["start_scope"] == []
    assert "plan_not_found:999" in result["notes"]


def test_resolver_with_marker_id_derives_plan_id_from_marker():
    marker = _FakeMarker(
        marker_id="mkr-1",
        plan_id="7",
        titel="Scope A",
        status="in_progress",
        naechster_schritt="Weiter machen",
    )
    plan_row = {
        "id": 7,
        "project_name": "demo_project",
        "title": "Plan 7",
        "status": "active",
        "source_path": "sprints/plan-7.md",
        "source_kind": "project_sprints",
        "updated_at": None,
    }

    lookups = {"marker_called_with": None, "plan_called_with": None}

    def marker_lookup(project_id, marker_id):
        lookups["marker_called_with"] = (project_id, marker_id)
        return marker

    def plan_lookup(plan_id):
        lookups["plan_called_with"] = plan_id
        return plan_row

    result = resolver.resolve_context(
        "demo_project",
        marker_id="mkr-1",
        marker_lookup=marker_lookup,
        plan_lookup=plan_lookup,
        handoff_path_fn=_fixed_handoff_path,
    )
    assert lookups["marker_called_with"] == ("demo_project", "mkr-1")
    assert lookups["plan_called_with"] == "7"
    assert result["active_marker"]["marker_id"] == "mkr-1"
    assert result["active_marker"]["status"] == "in_progress"
    assert result["relevant_plan"]["id"] == 7
    assert result["start_scope"] == ["sprints/plan-7.md"]


def test_resolver_with_unknown_marker_notes_not_found():
    result = resolver.resolve_context(
        "demo_project",
        marker_id="missing",
        marker_lookup=lambda pid, mid: None,
        plan_lookup=lambda pid: None,
        handoff_path_fn=_fixed_handoff_path,
    )
    assert result["active_marker"] is None
    assert "marker_not_found:missing" in result["notes"]


def test_resolver_explicit_plan_id_overrides_marker_plan():
    # marker zeigt auf plan "7", aber der Caller uebergibt plan_id=99 explizit.
    marker = _FakeMarker(marker_id="mkr-1", plan_id="7")
    calls = {"plan_ids": []}

    def plan_lookup(plan_id):
        calls["plan_ids"].append(plan_id)
        if int(plan_id) == 99:
            return {
                "id": 99,
                "project_name": "demo_project",
                "title": "Explicit Plan",
                "status": "draft",
                "source_path": "sprints/explicit.md",
                "source_kind": "project_sprints",
                "updated_at": None,
            }
        return None

    result = resolver.resolve_context(
        "demo_project",
        plan_id=99,
        marker_id="mkr-1",
        marker_lookup=lambda pid, mid: marker,
        plan_lookup=plan_lookup,
        handoff_path_fn=_fixed_handoff_path,
    )
    assert calls["plan_ids"] == [99]
    assert result["relevant_plan"]["id"] == 99
    assert result["start_scope"] == ["sprints/explicit.md"]


def test_bootstrap_task_uses_start_scope_as_allowed_files(fake_db):
    plan_row = {
        "id": 5,
        "project_name": "demo_project",
        "title": "Plan 5",
        "status": "active",
        "source_path": "sprints/plan-5.md",
        "source_kind": "project_sprints",
        "updated_at": None,
    }

    result = orchestrator.bootstrap_task(
        project_id="demo_project",
        title="Agent Run 1",
        goal="Refactor plan-5",
        plan_id=5,
        session_id="ses_b1",
        plan_lookup=lambda pid: plan_row,
        handoff_path_fn=_fixed_handoff_path,
    )
    contract = result["contract"]
    context = result["context"]

    assert contract["title"] == "Agent Run 1"
    assert contract["session_id"] == "ses_b1"
    assert contract["allowed_files"] == ["sprints/plan-5.md"]
    assert context["relevant_plan"]["id"] == 5
    assert context["start_scope"] == ["sprints/plan-5.md"]


def test_bootstrap_task_allows_allowed_files_override(fake_db):
    plan_row = {
        "id": 6,
        "project_name": "demo_project",
        "title": "Plan 6",
        "status": "active",
        "source_path": "sprints/plan-6.md",
        "source_kind": "project_sprints",
        "updated_at": None,
    }

    result = orchestrator.bootstrap_task(
        project_id="demo_project",
        title="Agent Run 2",
        plan_id=6,
        overrides={"allowed_files": ["tests/test_foo.py"], "forbidden_actions": ["git"]},
        plan_lookup=lambda pid: plan_row,
        handoff_path_fn=_fixed_handoff_path,
    )
    contract = result["contract"]

    assert contract["allowed_files"] == ["tests/test_foo.py"]
    assert contract["forbidden_actions"] == ["git"]
    # start_scope bleibt im Kontext sichtbar, auch wenn der Contract ihn nicht uebernimmt.
    assert result["context"]["start_scope"] == ["sprints/plan-6.md"]


def test_bootstrap_task_without_plan_or_marker_produces_empty_scope(fake_db):
    result = orchestrator.bootstrap_task(
        project_id="demo_project",
        title="Freier Lauf",
        handoff_path_fn=_fixed_handoff_path,
    )
    assert result["contract"]["allowed_files"] == []
    assert result["context"]["start_scope"] == []
