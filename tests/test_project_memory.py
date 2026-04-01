"""
SPEC-PROJECT-MEMORY-001: Tests fuer Project Memory Service und API.
Laufen ohne DB: Service-Funktionen werden per monkeypatch ersetzt.
"""
import pytest

# ---------------------------------------------------------------------------
# Flask Test-Client
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Erzeugt Flask-App fuer Tests."""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Fake-Daten fuer monkeypatch
# ---------------------------------------------------------------------------

FAKE_MEMORY = {
    "project": {"name": "test-project", "path": "/mnt/projects/test-project"},
    "metadata": {
        "category": "tool",
        "topic": "testing",
        "tags": ["python", "flask"],
        "project_type": "project",
        "status": "active",
        "priority": "high",
    },
    "governance": {"policy_level": "sandbox"},
    "session_summary": {
        "total_sessions": 5,
        "last_session_at": "2026-04-01T10:00:00+00:00",
        "total_input_tokens": 1000,
        "total_output_tokens": 500,
        "top_models": [{"model": "claude-opus-4.6", "sessions": 3}],
        "outcome_counts": {"ok": 4, "needs_fix": 1},
    },
    "recent_plans": [
        {
            "title": "Test-Plan",
            "session_uuid": "abc-123",
            "category": "feature",
            "status": "active",
            "created_at": "2026-03-31T18:00:00+00:00",
        }
    ],
    "file_activity": {
        "total_touches": 20,
        "top_touched_files": [
            {"file_path": "services/test.py", "touches": 5}
        ],
    },
}


# ---------------------------------------------------------------------------
# Service Happy Path
# ---------------------------------------------------------------------------

class TestGetProjectMemory:
    """Tests fuer get_project_memory()."""

    def test_happy_path(self, monkeypatch):
        """Liefert vollstaendiges Memory-Objekt fuer existierendes Projekt."""
        import services.project_memory_service as svc

        monkeypatch.setattr(svc, "get_project_memory", lambda name: FAKE_MEMORY if name == "test-project" else None)

        result = svc.get_project_memory("test-project")
        assert result is not None
        assert result["project"]["name"] == "test-project"
        assert "metadata" in result
        assert "governance" in result
        assert "session_summary" in result
        assert "recent_plans" in result
        assert "file_activity" in result

    def test_unknown_project_returns_none(self, monkeypatch):
        """Unbekanntes Projekt gibt None zurueck."""
        import services.project_memory_service as svc

        monkeypatch.setattr(svc, "get_project_memory", lambda name: None)

        result = svc.get_project_memory("does-not-exist")
        assert result is None

    def test_response_contract_fields(self, monkeypatch):
        """Prueft dass alle Pflichtfelder im Response vorhanden sind."""
        import services.project_memory_service as svc

        monkeypatch.setattr(svc, "get_project_memory", lambda name: FAKE_MEMORY)

        result = svc.get_project_memory("test-project")
        # Top-Level required fields
        for key in ("project", "metadata", "governance", "session_summary", "recent_plans", "file_activity"):
            assert key in result, f"Fehlendes Feld: {key}"

        # project required
        assert "name" in result["project"]
        assert "path" in result["project"]

        # metadata required
        for key in ("category", "topic", "tags", "project_type", "status", "priority"):
            assert key in result["metadata"], f"metadata.{key} fehlt"

        # session_summary required
        for key in ("total_sessions", "last_session_at", "total_input_tokens", "total_output_tokens", "top_models", "outcome_counts"):
            assert key in result["session_summary"], f"session_summary.{key} fehlt"

        # file_activity required
        assert "total_touches" in result["file_activity"]
        assert "top_touched_files" in result["file_activity"]


# ---------------------------------------------------------------------------
# Service: Fehlende Teilquellen ergeben Defaults
# ---------------------------------------------------------------------------

class TestPartialDataDefaults:
    """Fehlende Teilquellen duerfen nicht den gesamten Response brechen."""

    def test_empty_sessions(self, monkeypatch):
        """Keine Sessions -> leere Defaults."""
        import services.project_memory_service as svc

        empty = dict(FAKE_MEMORY)
        empty["session_summary"] = {
            "total_sessions": 0,
            "last_session_at": None,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "top_models": [],
            "outcome_counts": {},
        }
        monkeypatch.setattr(svc, "get_project_memory", lambda name: empty)

        result = svc.get_project_memory("test-project")
        assert result["session_summary"]["total_sessions"] == 0
        assert result["session_summary"]["top_models"] == []
        assert result["session_summary"]["outcome_counts"] == {}

    def test_empty_plans(self, monkeypatch):
        """Keine Plans -> leere Liste."""
        import services.project_memory_service as svc

        empty = dict(FAKE_MEMORY)
        empty["recent_plans"] = []
        monkeypatch.setattr(svc, "get_project_memory", lambda name: empty)

        result = svc.get_project_memory("test-project")
        assert result["recent_plans"] == []

    def test_empty_file_activity(self, monkeypatch):
        """Keine File-Touches -> leere Defaults."""
        import services.project_memory_service as svc

        empty = dict(FAKE_MEMORY)
        empty["file_activity"] = {"total_touches": 0, "top_touched_files": []}
        monkeypatch.setattr(svc, "get_project_memory", lambda name: empty)

        result = svc.get_project_memory("test-project")
        assert result["file_activity"]["total_touches"] == 0
        assert result["file_activity"]["top_touched_files"] == []


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

class TestProjectMemoryAPI:
    """Tests fuer GET /api/projects/<name>/memory."""

    def test_200_existing_project(self, client, monkeypatch):
        """200 mit vollem Payload fuer bekanntes Projekt."""
        import routes.project_memory_routes as routes_mod

        monkeypatch.setattr(routes_mod, "get_project_memory", lambda name: FAKE_MEMORY)

        resp = client.get("/api/projects/test-project/memory")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["project"]["name"] == "test-project"
        assert "metadata" in data
        assert "governance" in data

    def test_404_unknown_project(self, client, monkeypatch):
        """404 mit stabilem Fehlerpayload fuer unbekanntes Projekt."""
        import routes.project_memory_routes as routes_mod

        monkeypatch.setattr(routes_mod, "get_project_memory", lambda name: None)

        resp = client.get("/api/projects/nonexistent/memory")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "project_not_found"
        assert data["project"] == "nonexistent"

    def test_response_is_json(self, client, monkeypatch):
        """Response ist application/json."""
        import routes.project_memory_routes as routes_mod

        monkeypatch.setattr(routes_mod, "get_project_memory", lambda name: FAKE_MEMORY)

        resp = client.get("/api/projects/test-project/memory")
        assert resp.content_type.startswith("application/json")
