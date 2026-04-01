"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Abnahmetests fuer Copilot-Chat.
Deckt C1-C7 ab: Persistenz, API, Verlauf, UI, Abgrenzung.
"""
import json
import pytest
from unittest.mock import patch

from app import app as flask_app
from services.copilot_service import call_copilot, list_copilot_runs


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# --- C1: Persistenz ---

class TestPersistence:
    @patch("services.copilot_service.query_perplexity")
    def test_successful_run_persisted(self, mock_llm):
        mock_llm.return_value = {
            "content": "Alles klar, das Projekt sieht gut aus.",
            "model": "sonar-test",
            "usage": {},
        }
        result = call_copilot("Wie steht das Projekt?", project_id="test_proj")
        assert result["status"] == "success"
        assert result["copilot_run_id"] is not None
        assert result["reply"] == "Alles klar, das Projekt sieht gut aus."
        assert result["thread_id"] is not None

        # In DB pruefen
        runs = list_copilot_runs(thread_id=result["thread_id"])
        assert len(runs) >= 1
        found = [r for r in runs if r["id"] == result["copilot_run_id"]]
        assert len(found) == 1
        assert found[0]["status"] == "success"

    @patch("services.copilot_service.query_perplexity")
    def test_failure_persisted(self, mock_llm):
        from services.perplexity_service import PerplexityConfigError
        mock_llm.side_effect = PerplexityConfigError("Key fehlt")
        result = call_copilot("Test", project_id="test_fail")
        assert result["status"] == "failure"
        assert "Config-Fehler" in result["error_info"]
        assert result["copilot_run_id"] is not None


# --- C2: POST /api/copilot/chat ---

class TestChatEndpoint:
    @patch("services.copilot_service.query_perplexity")
    def test_success(self, mock_llm, client):
        mock_llm.return_value = {
            "content": "Das sieht gut aus.",
            "model": "sonar",
            "usage": {},
        }
        r = client.post("/api/copilot/chat",
                        data=json.dumps({"message": "Hallo Copilot"}),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "success"
        assert d["reply"] == "Das sieht gut aus."
        assert "copilot_run_id" in d
        assert "thread_id" in d
        assert "created_at" in d

    def test_missing_message(self, client):
        r = client.post("/api/copilot/chat",
                        data=json.dumps({"project_id": "test"}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_empty_message(self, client):
        r = client.post("/api/copilot/chat",
                        data=json.dumps({"message": "  "}),
                        content_type="application/json")
        assert r.status_code == 400

    @patch("services.copilot_service.query_perplexity")
    def test_with_project_and_thread(self, mock_llm, client):
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        r = client.post("/api/copilot/chat",
                        data=json.dumps({
                            "message": "Test",
                            "project_id": "my_project",
                            "thread_id": "thread-123",
                        }),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["project_id"] == "my_project"
        assert d["thread_id"] == "thread-123"

    @patch("services.copilot_service.query_perplexity")
    def test_connector_error_returns_422(self, mock_llm, client):
        from services.perplexity_service import PerplexityConfigError
        mock_llm.side_effect = PerplexityConfigError("No key")
        r = client.post("/api/copilot/chat",
                        data=json.dumps({"message": "Test"}),
                        content_type="application/json")
        assert r.status_code == 422
        d = r.get_json()
        assert d["status"] == "failure"
        assert d["error_info"] is not None


# --- C3: GET /api/copilot/runs ---

class TestRunsEndpoint:
    @patch("services.copilot_service.query_perplexity")
    def test_filter_by_project(self, mock_llm, client):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        # Erzeuge einen Run fuer spezifisches Projekt
        client.post("/api/copilot/chat",
                     data=json.dumps({"message": "Frage", "project_id": "filter_test_proj"}),
                     content_type="application/json")

        r = client.get("/api/copilot/runs?project_id=filter_test_proj")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) >= 1
        assert all(run["project_id"] == "filter_test_proj" for run in d["runs"])

    @patch("services.copilot_service.query_perplexity")
    def test_filter_by_thread(self, mock_llm, client):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        client.post("/api/copilot/chat",
                     data=json.dumps({"message": "Frage", "thread_id": "th-filter-test"}),
                     content_type="application/json")

        r = client.get("/api/copilot/runs?thread_id=th-filter-test")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) >= 1
        assert all(run["thread_id"] == "th-filter-test" for run in d["runs"])

    def test_limit(self, client):
        r = client.get("/api/copilot/runs?limit=2")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) <= 2


# --- C4: UI ---

class TestUI:
    def test_page_renders(self, client):
        r = client.get("/copilot")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "chatMessages" in html
        assert "chatInput" in html
        assert "btnSend" in html
        assert "copilot.js" in html
        assert "copilot.css" in html
        assert "marked.min.js" in html


# --- C5: Abgrenzung ---

class TestSeparation:
    def test_copilot_routes_separate_from_commands(self, client):
        """Copilot und Command Hub sind getrennte Blueprints."""
        # Copilot-Endpoints existieren
        r1 = client.get("/copilot")
        assert r1.status_code == 200
        # Command-Endpoints existieren weiterhin unabhaengig
        r2 = client.get("/llm-commands")
        assert r2.status_code == 200
        r3 = client.get("/api/llm/commands")
        assert r3.status_code == 200
