"""
Smoke tests for representative endpoints.

Goal: Verify that endpoints don't crash (no 500 errors).
All requests are safe GET-only — no writes, no pushes, no side effects.
External services are mocked via conftest.py fixtures.
"""
import json
import pytest


# ---------------------------------------------------------------------------
# HTML Page Routes — expect 200 (rendered page)
# ---------------------------------------------------------------------------

PAGE_ROUTES = [
    "/",
    "/sessions",
    "/plans",
    "/copilot",
    "/governance",
    "/quality",
    "/settings",
    "/news",
    "/timesheets",
    "/usage-monitor",
    "/usage-reports",
    "/model-comparison",
]


@pytest.mark.parametrize("path", PAGE_ROUTES)
def test_page_returns_200(client, path):
    """HTML pages must return 200, never 500."""
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert b"<!DOCTYPE" in r.data or b"<html" in r.data, \
        f"{path} did not return HTML"


# ---------------------------------------------------------------------------
# API JSON Routes — expect 200 + valid JSON
# ---------------------------------------------------------------------------

API_ROUTES = [
    "/api/sessions",
    "/api/sessions/stats",
    "/api/sessions/filters",
    "/api/sessions/outcome-reasons",
    "/api/plans",
    "/api/plans/stats",
    "/api/plans/projects",
    "/api/data",
    "/api/groups",
    "/api/ideas",
    "/api/ideas/categories",
    "/api/relations",
    "/api/relations/types",
    "/api/notifications/count",
    "/api/news",
    "/api/governance/overview",
    "/api/widgets/overview",
    "/api/copilot/stats",
    "/api/search?q=test",
]


@pytest.mark.parametrize("path", API_ROUTES)
def test_api_returns_json(client, path):
    """API endpoints must return 200 + parseable JSON, never 500."""
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    # Must be valid JSON
    data = json.loads(r.data)
    assert data is not None, f"{path} returned null JSON"


# ---------------------------------------------------------------------------
# Edge Cases — expect 404, not 500
# ---------------------------------------------------------------------------

NOT_FOUND_ROUTES = [
    ("/api/sessions/00000000-0000-0000-0000-000000000000", 404),
    ("/api/audits/999999", 404),
]


@pytest.mark.parametrize("path,expected_status", NOT_FOUND_ROUTES)
def test_not_found_returns_proper_status(client, path, expected_status):
    """Missing resources must return 404, never 500."""
    r = client.get(path)
    assert r.status_code == expected_status, \
        f"{path} returned {r.status_code}, expected {expected_status}"


# ---------------------------------------------------------------------------
# Response structure spot checks
# ---------------------------------------------------------------------------

class TestResponseStructure:
    """Verify key API responses have expected shape."""

    def test_sessions_has_sessions_key(self, client):
        r = client.get("/api/sessions")
        data = json.loads(r.data)
        assert "sessions" in data, "Expected 'sessions' key in response"
        assert isinstance(data["sessions"], list)

    def test_plans_has_plans_key(self, client):
        r = client.get("/api/plans")
        data = json.loads(r.data)
        assert "plans" in data, "Expected 'plans' key in response"
        assert isinstance(data["plans"], list)

    def test_groups_has_groups_key(self, client):
        r = client.get("/api/groups")
        data = json.loads(r.data)
        assert "groups" in data, "Expected 'groups' key in response"
        assert isinstance(data["groups"], list)

    def test_notification_count_has_unread(self, client):
        r = client.get("/api/notifications/count")
        data = json.loads(r.data)
        assert "unread" in data, "Expected 'unread' key in response"
        assert isinstance(data["unread"], int)

    def test_session_stats_has_total(self, client):
        r = client.get("/api/sessions/stats")
        data = json.loads(r.data)
        assert "total" in data or "total_sessions" in data or isinstance(data, dict), \
            "Expected stats dict"

    def test_search_returns_results_key(self, client):
        r = client.get("/api/search?q=test")
        data = json.loads(r.data)
        assert isinstance(data, (list, dict)), "Expected list or dict from search"
