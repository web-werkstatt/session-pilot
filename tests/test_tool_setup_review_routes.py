"""
ADR-002 Stufe 1a: Tests fuer die Setup-Reviewer REST-Endpoints.

Patcht `review_tool_setup` und `load_review` direkt im Route-Modul, damit
kein echter Reviewer-Service und keine DB gebraucht werden.
"""
import json

import pytest


@pytest.fixture
def patched_routes(monkeypatch):
    """Patcht resolve_project_path + review_tool_setup + load_review im Route-Modul."""
    import routes.tool_setup_review_routes as routes_mod

    state = {"stored": None}

    def fake_resolve(name):
        if name in ("fake-project", "other-project"):
            return "/tmp/" + name
        return None

    def fake_review_tool_setup(name, force=False):
        result = {
            "project_name": name,
            "review_type": "setup",
            "schema_version": 1,
            "setup_ok": False,
            "priority": "medium",
            "summary": "Testprojekt braucht Setup",
            "findings": [
                {
                    "area": "claude_md",
                    "severity": "warn",
                    "title": "Keine CLAUDE.md",
                    "problem": "fehlt",
                    "why_it_matters": "keine Session-Orientierung",
                    "recommended_change": "anlegen",
                    "can_autofix": False,
                }
            ],
            "suggested_blocks": {"CLAUDE.md": "Beispiel-Snapshot"},
            "project_json_patch": None,
            "implementation_scope": "small",
            "notes": [],
            "context_drift": {"has_drift": False},
            "context_hash": "abc123",
            "reviewer_tool": "perplexity",
            "reviewer_model": "sonar-test",
            "reviewed_tools": ["claude", "codex", "gemini"],
            "raw_response": json.dumps({"setup_ok": False}),
            "error": None,
        }
        state["stored"] = result
        return result

    def fake_load_review(name, review_type="setup"):
        return state["stored"]

    monkeypatch.setattr(routes_mod, "resolve_project_path", fake_resolve)
    monkeypatch.setattr(routes_mod, "review_tool_setup", fake_review_tool_setup)
    monkeypatch.setattr(routes_mod, "load_review", fake_load_review)

    return state


# ---------------------------------------------------------------------------
# POST /api/project/<name>/tool-setup/review
# ---------------------------------------------------------------------------

def test_post_review_success(client, patched_routes):
    response = client.post("/api/project/fake-project/tool-setup/review")
    assert response.status_code == 200

    data = response.get_json()
    assert data["project"] == "fake-project"
    assert data["result"]["setup_ok"] is False
    assert data["result"]["priority"] == "medium"
    assert len(data["result"]["findings"]) == 1
    assert data["result"]["reviewer_tool"] == "perplexity"


def test_post_review_404_unknown_project(client, patched_routes):
    response = client.post("/api/project/ghost-project/tool-setup/review")
    assert response.status_code == 404

    data = response.get_json()
    assert "error" in data


def test_post_review_accepts_force_flag(client, patched_routes):
    response = client.post(
        "/api/project/fake-project/tool-setup/review",
        json={"force": True},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"]["setup_ok"] is False


def test_post_review_500_on_internal_error(client, monkeypatch):
    import routes.tool_setup_review_routes as routes_mod

    monkeypatch.setattr(routes_mod, "resolve_project_path", lambda n: "/tmp/x")

    def boom(name, force=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(routes_mod, "review_tool_setup", boom)

    response = client.post("/api/project/fake-project/tool-setup/review")
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "internal_error"


# ---------------------------------------------------------------------------
# GET /api/project/<name>/tool-setup/review
# ---------------------------------------------------------------------------

def test_get_review_without_prior(client, patched_routes):
    # state["stored"] ist None am Start
    response = client.get("/api/project/fake-project/tool-setup/review")
    assert response.status_code == 200

    data = response.get_json()
    assert data["project"] == "fake-project"
    assert data["result"] is None


def test_get_review_after_post(client, patched_routes):
    # Erst Review ausloesen, dann lesen
    client.post("/api/project/fake-project/tool-setup/review")
    response = client.get("/api/project/fake-project/tool-setup/review")
    assert response.status_code == 200

    data = response.get_json()
    assert data["result"] is not None
    assert data["result"]["setup_ok"] is False
    assert data["result"]["summary"] == "Testprojekt braucht Setup"


def test_get_review_404_unknown_project(client, patched_routes):
    response = client.get("/api/project/ghost-project/tool-setup/review")
    assert response.status_code == 404
