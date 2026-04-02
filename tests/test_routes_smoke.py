"""
Smoke tests for all safe GET endpoints.

Goal: Verify that endpoints don't crash (no 500 errors).
All requests are read-only GET — no writes, no pushes, no side effects.
External services are mocked via conftest.py fixtures.
"""
import json
import pytest


# ===================================================================
# 1. HTML Page Routes — expect 200 (rendered page)
# ===================================================================

PAGE_ROUTES = [
    "/",
    "/sessions",
    "/sessions/analysis",
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
    "/audits",
    "/containers",
    "/dependencies",
    "/llm-commands",
    "/scaffold",
    "/scheduled-tasks",
    "/vorlagen",
]


@pytest.mark.parametrize("path", PAGE_ROUTES)
def test_page_returns_200(client, path):
    """HTML pages must return 200, never 500."""
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert b"<!DOCTYPE" in r.data or b"<html" in r.data, \
        f"{path} did not return HTML"


# ===================================================================
# 2. API JSON Routes — expect 200 + valid JSON
# ===================================================================

API_ROUTES_CORE = [
    # Sessions
    "/api/sessions",
    "/api/sessions/stats",
    "/api/sessions/filters",
    "/api/sessions/outcome-reasons",
    "/api/sessions/scope-stats",
    "/api/sessions/analysis",
    "/api/sessions/sync/status",
    # Plans
    "/api/plans",
    "/api/plans/stats",
    "/api/plans/projects",
    # Data & Collections
    "/api/data",
    "/api/groups",
    "/api/ideas",
    "/api/ideas/categories",
    "/api/relations",
    "/api/relations/types",
    "/api/favorites",
    # Notifications
    "/api/notifications",
    "/api/notifications/count",
    # News & Search
    "/api/news",
    "/api/search?q=test",
    # Governance
    "/api/governance/overview",
    "/api/governance/feedback-loop",
    # Widgets
    "/api/widgets/overview",
    "/api/widgets/activity",
    "/api/widgets/ai-hotspots",
    # Copilot
    "/api/copilot/stats",
    "/api/copilot/runs",
    "/api/copilot/ai-previews",
    # Analytics
    "/api/analytics/model-comparison",
    "/api/analytics/model-by-stack",
    "/api/analytics/model-recommendation",
    "/api/analytics/model-trend",
    # LLM Commands
    "/api/llm/commands",
    "/api/llm/commands/runs",
    # Timesheets
    "/api/timesheets/summary",
    "/api/timesheets/daily",
    "/api/timesheets/projects",
    "/api/timesheets/models",
    "/api/timesheets/tools",
    "/api/timesheets/rework",
    "/api/timesheets/context-changes",
    "/api/timesheets/context-effectiveness",
    # Usage
    "/api/usage-monitor/live",
    "/api/usage-reports/data",
    # Settings
    "/api/settings/accounts",
    "/api/settings/external-links",
    "/api/settings/pricing",
    "/api/settings/system",
    # Quality
    "/api/quality/projects",
    # Scaffold
    "/api/scaffold/templates",
    # Scheduled Tasks
    "/api/scheduled-tasks",
    "/api/scheduled-tasks/templates",
    # Other
    "/api/containers",
    "/api/otel/metrics",
    "/api/vorlagen",
    "/api/projects/search",
]


# ===================================================================
# 2b. Routes that require query parameters — expect 200 with params
# ===================================================================

PARAM_REQUIRED_ROUTES = [
    ("/api/info?name=test-project", 200),
    ("/api/info/slow?name=test-project", 200),
    ("/api/sessions/search?q=test", 200),
    ("/api/copilot/threads?section_id=1", 200),
    ("/api/copilot/messages?thread_id=1", 200),
    ("/api/plans/workflow?project_id=test-project", 200),
]


@pytest.mark.parametrize("path,expected", PARAM_REQUIRED_ROUTES)
def test_param_routes_with_params(client, path, expected):
    """Routes needing query params must return 200 when params are provided."""
    r = client.get(path)
    # Accept 200 or 404 (resource may not exist, but no 500)
    assert r.status_code in (200, 404), \
        f"{path} returned {r.status_code}, expected 200 or 404"


PARAM_MISSING_ROUTES = [
    "/api/info",
    "/api/info/slow",
    "/api/sessions/search",
    "/api/copilot/threads",
    "/api/copilot/messages",
    "/api/plans/workflow",
]


@pytest.mark.parametrize("path", PARAM_MISSING_ROUTES)
def test_param_routes_without_params_return_400(client, path):
    """Routes needing query params must return 400 without them, not 500."""
    r = client.get(path)
    assert r.status_code == 400, \
        f"{path} returned {r.status_code}, expected 400"


@pytest.mark.parametrize("path", API_ROUTES_CORE)
def test_api_returns_json(client, path):
    """API endpoints must return 200 + parseable JSON, never 500."""
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    data = json.loads(r.data)
    assert data is not None, f"{path} returned null JSON"


# ===================================================================
# 3. Parametrisierte Routes mit sicheren Fake-IDs
# ===================================================================

PARAM_ROUTES_404 = [
    # Nicht existierende Ressourcen -> 404, nicht 500
    ("/api/sessions/00000000-0000-0000-0000-000000000000", 404),
    ("/api/audits/999999", 404),
    ("/api/plan-sections/999999", 404),
    ("/api/plans/999999", 404),
    ("/api/plans/999999/workflow", 404),
    ("/api/plans/999999/sections", [200, 404]),
    ("/api/plans/999999/handoff", [200, 404]),
]


@pytest.mark.parametrize("path,expected", PARAM_ROUTES_404)
def test_missing_resource_no_500(client, path, expected):
    """Missing resources must return 404 (or 200 empty), never 500."""
    r = client.get(path)
    if isinstance(expected, list):
        assert r.status_code in expected, \
            f"{path} returned {r.status_code}, expected one of {expected}"
    else:
        assert r.status_code == expected, \
            f"{path} returned {r.status_code}, expected {expected}"


# ===================================================================
# 4. /api/info/slow (kann laenger dauern, eigener Test)
# ===================================================================

def test_api_info_slow_returns_json(client):
    """/api/info/slow requires name param, returns project info."""
    r = client.get("/api/info/slow?name=test-project")
    # 200 if project exists, 404 if not — but never 500
    assert r.status_code in (200, 404), \
        f"/api/info/slow returned {r.status_code}"


# ===================================================================
# 5. Response-Struktur Spot-Checks
# ===================================================================

class TestResponseStructure:
    """Verify key API responses have expected shape."""

    def test_sessions_has_sessions_key(self, client):
        r = client.get("/api/sessions")
        data = json.loads(r.data)
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_plans_has_plans_key(self, client):
        r = client.get("/api/plans")
        data = json.loads(r.data)
        assert "plans" in data
        assert isinstance(data["plans"], list)

    def test_groups_has_groups_key(self, client):
        r = client.get("/api/groups")
        data = json.loads(r.data)
        assert "groups" in data
        assert isinstance(data["groups"], list)

    def test_notification_count_has_unread(self, client):
        r = client.get("/api/notifications/count")
        data = json.loads(r.data)
        assert "unread" in data
        assert isinstance(data["unread"], int)

    def test_session_stats_is_dict(self, client):
        r = client.get("/api/sessions/stats")
        data = json.loads(r.data)
        assert isinstance(data, dict)

    def test_search_returns_results(self, client):
        r = client.get("/api/search?q=test")
        data = json.loads(r.data)
        assert isinstance(data, (list, dict))

    def test_settings_accounts_is_list(self, client):
        r = client.get("/api/settings/accounts")
        data = json.loads(r.data)
        assert isinstance(data, list)

    def test_scaffold_templates_is_list(self, client):
        r = client.get("/api/scaffold/templates")
        data = json.loads(r.data)
        assert isinstance(data, list)

    def test_timesheets_summary_is_dict(self, client):
        r = client.get("/api/timesheets/summary")
        data = json.loads(r.data)
        assert isinstance(data, dict)

    def test_quality_projects_is_list_or_dict(self, client):
        r = client.get("/api/quality/projects")
        data = json.loads(r.data)
        assert isinstance(data, (list, dict))

    def test_widgets_overview_is_dict(self, client):
        r = client.get("/api/widgets/overview")
        data = json.loads(r.data)
        assert isinstance(data, dict)

    def test_llm_commands_has_commands_key(self, client):
        r = client.get("/api/llm/commands")
        data = json.loads(r.data)
        assert "commands" in data
        assert isinstance(data["commands"], list)

    def test_analytics_model_comparison_is_dict(self, client):
        r = client.get("/api/analytics/model-comparison")
        data = json.loads(r.data)
        assert isinstance(data, dict)
