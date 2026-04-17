"""
ADR-002 Stufe 1b Commit 9: Test fuer get_handoff_view-Erweiterung um
active_policies.

Patcht get_markers, get_workflow_state und get_active_policies direkt
im workflow_core_service-Modul, damit keine echte DB gebraucht wird.
"""
from dataclasses import dataclass

import pytest


@dataclass
class FakeMarker:
    marker_id: str
    plan_id: str
    titel: str = ""
    ziel: str = ""
    naechster_schritt: str = ""
    prompt: str = ""
    prompt_suggestion: str = ""
    risiko: str = ""
    checks: list = None  # type: ignore
    status: str = "planned"
    last_session: str = ""
    execution_score: int = 0
    execution_comment: str = ""
    sprint_tag: str = ""
    spec_tag: str = ""

    def __post_init__(self):
        if self.checks is None:
            self.checks = []


@pytest.fixture
def patched_workflow_core(monkeypatch):
    """Patcht Marker-, State- und Policy-Aufrufe im Modul."""
    import services.workflow_core_service as wcs

    state = {
        "markers": [FakeMarker(marker_id="m1", plan_id="p1", titel="Test")],
        "policies": [],
        "state_rows": {},
    }

    def fake_get_markers(project_name, plan_id=None):
        return list(state["markers"])

    def fake_get_workflow_state(project_name, marker_id):
        return state["state_rows"].get(marker_id)

    def fake_get_active_policies(role_id=None):
        return list(state["policies"])

    monkeypatch.setattr(wcs, "get_markers", fake_get_markers)
    monkeypatch.setattr(wcs, "get_workflow_state", fake_get_workflow_state)

    import services.policy_service as ps
    monkeypatch.setattr(ps, "get_active_policies", fake_get_active_policies)

    return state


def test_handoff_view_returns_dict_with_markers_and_policies(patched_workflow_core):
    import services.workflow_core_service as wcs
    result = wcs.get_handoff_view("any-project")
    assert isinstance(result, dict)
    assert "markers" in result
    assert "active_policies" in result
    assert len(result["markers"]) == 1
    assert result["markers"][0]["marker_id"] == "m1"


def test_handoff_view_empty_policies(patched_workflow_core):
    import services.workflow_core_service as wcs
    result = wcs.get_handoff_view("any-project")
    assert result["active_policies"] == {}


def test_handoff_view_single_policy(patched_workflow_core):
    patched_workflow_core["policies"] = [
        {
            "policy_id": 1,
            "role_id": "programming",
            "tool_id": "claude-opus",
            "rank": 1,
            "confidence": 80,
        }
    ]
    import services.workflow_core_service as wcs
    result = wcs.get_handoff_view("any-project")
    assert "programming" in result["active_policies"]
    assert result["active_policies"]["programming"]["tool_id"] == "claude-opus"
    assert result["active_policies"]["programming"]["rank"] == 1


def test_handoff_view_primary_policy_wins_lowest_rank(patched_workflow_core):
    patched_workflow_core["policies"] = [
        {"role_id": "programming", "tool_id": "fallback-tool", "rank": 2, "confidence": 50},
        {"role_id": "programming", "tool_id": "primary-tool", "rank": 1, "confidence": 80},
        {"role_id": "programming", "tool_id": "another", "rank": 3, "confidence": 40},
    ]
    import services.workflow_core_service as wcs
    result = wcs.get_handoff_view("any-project")
    assert result["active_policies"]["programming"]["tool_id"] == "primary-tool"
    assert result["active_policies"]["programming"]["rank"] == 1


def test_handoff_view_multiple_roles(patched_workflow_core):
    patched_workflow_core["policies"] = [
        {"role_id": "programming", "tool_id": "claude-opus", "rank": 1, "confidence": 80},
        {"role_id": "ux_ui", "tool_id": "codex", "rank": 1, "confidence": 70},
    ]
    import services.workflow_core_service as wcs
    result = wcs.get_handoff_view("any-project")
    assert len(result["active_policies"]) == 2
    assert result["active_policies"]["programming"]["tool_id"] == "claude-opus"
    assert result["active_policies"]["ux_ui"]["tool_id"] == "codex"


def test_handoff_view_policies_failure_returns_empty_dict(monkeypatch):
    """Wenn Policy-Schicht nicht verfuegbar, leere active_policies, keine Exception."""
    import services.workflow_core_service as wcs

    # Marker-Teil mocken
    monkeypatch.setattr(wcs, "get_markers", lambda name, plan_id=None: [])
    monkeypatch.setattr(wcs, "get_workflow_state", lambda name, mid: None)

    # Policy-Teil wirft
    import services.policy_service as ps
    def boom(role_id=None):
        raise RuntimeError("policy schema missing")
    monkeypatch.setattr(ps, "get_active_policies", boom)

    result = wcs.get_handoff_view("any-project")
    assert result["markers"] == []
    assert result["active_policies"] == {}
