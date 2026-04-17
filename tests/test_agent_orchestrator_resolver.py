"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
Resolver-Tests ausgelagert aus tests/test_agent_orchestrator.py, damit die
Hauptdatei unter dem 500-Zeilen-Limit bleibt.

Fokus:
  * resolve_context: handoff_path, plan_lookup, marker_lookup, start_scope
  * Lookup-Registry: register_project_lookups / unregister_project_lookups
"""
from __future__ import annotations

import pytest

import services.agent_orchestrator_resolver as resolver


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


# ---------------------------------------------------------------------------
# Handoff-/Marker-Resolver (Tag 3)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sprint Project-Config: Resolver-Lookup-Registry
# ---------------------------------------------------------------------------

def test_registry_override_replaces_default_handoff_path():
    calls = {"handoff": 0, "marker": 0, "plan": 0}

    def custom_handoff(project_id):
        calls["handoff"] += 1
        return f"/custom/{project_id}/HANDOFF.md"

    def custom_marker(project_id, marker_id):
        calls["marker"] += 1
        return _FakeMarker(marker_id=marker_id, plan_id="5", titel="Custom")

    def custom_plan(plan_id):
        calls["plan"] += 1
        return {
            "id": int(plan_id),
            "project_name": "custom_proj",
            "title": "Custom Plan",
            "status": "active",
            "source_path": "custom/plan.md",
            "source_kind": "project_sprints",
            "updated_at": None,
        }

    resolver.register_project_lookups(
        "custom_proj",
        handoff_path_fn=custom_handoff,
        marker_lookup=custom_marker,
        plan_lookup=custom_plan,
    )
    try:
        result = resolver.resolve_context(
            "custom_proj",
            marker_id="m1",
        )
        assert result["handoff_path"] == "/custom/custom_proj/HANDOFF.md"
        assert result["active_marker"]["marker_id"] == "m1"
        assert result["relevant_plan"]["source_path"] == "custom/plan.md"
        assert result["start_scope"] == ["custom/plan.md"]
        assert calls == {"handoff": 1, "marker": 1, "plan": 1}
    finally:
        resolver.unregister_project_lookups("custom_proj")


def test_registry_does_not_affect_other_projects():
    resolver.register_project_lookups(
        "proj_a",
        handoff_path_fn=lambda pid: f"/a/{pid}",
    )
    try:
        # proj_b hat keinen Registry-Eintrag -> kwargs-Override greift,
        # Default wird nicht konsultiert.
        result = resolver.resolve_context(
            "proj_b",
            handoff_path_fn=lambda pid: f"/b/{pid}",
        )
        assert result["handoff_path"] == "/b/proj_b"
    finally:
        resolver.unregister_project_lookups("proj_a")


def test_registry_kwargs_override_beats_registered_function():
    resolver.register_project_lookups(
        "proj_x",
        handoff_path_fn=lambda pid: "/registered/path",
    )
    try:
        result = resolver.resolve_context(
            "proj_x",
            handoff_path_fn=lambda pid: "/explicit/path",
        )
        assert result["handoff_path"] == "/explicit/path"
    finally:
        resolver.unregister_project_lookups("proj_x")


def test_register_project_lookups_rejects_empty_id():
    with pytest.raises(ValueError):
        resolver.register_project_lookups("", handoff_path_fn=lambda pid: "")
