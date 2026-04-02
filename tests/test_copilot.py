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
    def test_copilot_without_plan_id_shows_landing(self, client):
        """/copilot ohne plan_id zeigt Landing-Seite (kein Redirect)."""
        r = client.get("/copilot")
        assert r.status_code == 200


# --- C5: Abgrenzung ---

class TestSeparation:
    def test_copilot_routes_separate_from_commands(self, client):
        """Copilot und Command Hub sind getrennte Blueprints."""
        # Copilot-Route existiert (redirect ohne plan_id)
        r1 = client.get("/copilot")
        assert r1.status_code in (200, 302)
        # Command-Endpoints existieren weiterhin unabhaengig
        r2 = client.get("/llm-commands")
        assert r2.status_code == 200
        r3 = client.get("/api/llm/commands")
        assert r3.status_code == 200


# --- Sprint H: Copilot-UI im Plan-Modal ---

class TestPlanCopilotChat:
    """Tests fuer C1-C7: Copilot-Tab, plan_id-Filter, Bild-Upload, Persistenz."""

    @patch("services.copilot_service.query_perplexity")
    def test_chat_with_plan_id(self, mock_llm, client):
        """C3/C5: POST /api/copilot/chat mit plan_id persistiert korrekt."""
        mock_llm.return_value = {"content": "Plan-Antwort", "model": "sonar", "usage": {}}
        r = client.post("/api/copilot/chat",
                        data=json.dumps({
                            "message": "Was ist der naechste Schritt?",
                            "plan_id": 1,
                            "project_id": "test_plan_proj",
                        }),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["plan_id"] == 1
        assert d["status"] == "success"

    @patch("services.copilot_service.query_perplexity")
    def test_runs_filter_by_plan_id(self, mock_llm, client):
        """C2: GET /api/copilot/runs?plan_id= filtert korrekt."""
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        # Erzeuge Runs fuer plan_id=42
        client.post("/api/copilot/chat",
                     data=json.dumps({"message": "Plan-Frage", "plan_id": 42}),
                     content_type="application/json")

        r = client.get("/api/copilot/runs?plan_id=42")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) >= 1
        assert all(run["plan_id"] == 42 for run in d["runs"])

    @patch("services.copilot_service.query_perplexity")
    def test_chat_with_images(self, mock_llm, client):
        """C5: POST /api/copilot/chat mit images persistiert Bild-Referenzen."""
        mock_llm.return_value = {"content": "Bild gesehen", "model": "sonar", "usage": {}}
        images = [{"filename": "screenshot.png", "url": "/static/uploads/copilot/abc.png", "mime_type": "image/png"}]
        r = client.post("/api/copilot/chat",
                        data=json.dumps({
                            "message": "Sieh dir dieses Bild an",
                            "plan_id": 99,
                            "images": images,
                        }),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["images"] is not None
        assert len(d["images"]) == 1
        assert d["images"][0]["filename"] == "screenshot.png"

    @patch("services.copilot_service.query_perplexity")
    def test_chat_without_images_backward_compatible(self, mock_llm, client):
        """C5: Runs ohne Bilder funktionieren weiterhin."""
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        r = client.post("/api/copilot/chat",
                        data=json.dumps({"message": "Einfache Frage"}),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["images"] is None

    @patch("services.copilot_service.query_perplexity")
    def test_runs_with_images_in_listing(self, mock_llm, client):
        """C7: GET /api/copilot/runs zeigt images-Feld ohne Fehler."""
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        images = [{"filename": "test.jpg", "url": "/static/uploads/copilot/x.jpg", "mime_type": "image/jpeg"}]
        client.post("/api/copilot/chat",
                     data=json.dumps({"message": "Bild", "plan_id": 77, "images": images}),
                     content_type="application/json")

        r = client.get("/api/copilot/runs?plan_id=77")
        assert r.status_code == 200
        runs = r.get_json()["runs"]
        img_runs = [run for run in runs if run.get("images")]
        assert len(img_runs) >= 1
        assert img_runs[0]["images"][0]["filename"] == "test.jpg"

    def test_upload_image_no_file(self, client):
        """C4: Upload ohne Datei gibt 400."""
        r = client.post("/api/copilot/upload_image")
        assert r.status_code == 400

    def test_upload_image_success(self, client):
        """C4: Upload mit gueltigem Bild gibt URL zurueck."""
        import io
        data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "test-upload.png", "image/png"),
        }
        r = client.post("/api/copilot/upload_image",
                        data=data,
                        content_type="multipart/form-data")
        assert r.status_code == 200
        d = r.get_json()
        assert d["filename"] == "test-upload.png"
        assert d["url"].startswith("/static/uploads/copilot/")
        assert d["mime_type"] == "image/png"

    def test_upload_image_wrong_type(self, client):
        """C4: Upload mit nicht-erlaubtem Typ gibt 400."""
        import io
        data = {
            "file": (io.BytesIO(b"not a pdf"), "evil.pdf", "application/pdf"),
        }
        r = client.post("/api/copilot/upload_image",
                        data=data,
                        content_type="multipart/form-data")
        assert r.status_code == 400

    def test_plans_page_has_no_copilot_tab(self, client):
        """Plans-Seite hat KEIN Copilot-Tab (Trennung Level 1/2)."""
        r = client.get("/plans")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert 'data-tab="copilot"' not in html
        assert "planChatMessages" not in html

    def test_copilot_board_renders_for_plan_id(self, client):
        """Copilot-Board rendert unter /copilot?plan_id=X."""
        # plan_id=1 muss nicht existieren, Template rendert trotzdem
        r = client.get("/copilot?plan_id=1")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "sectionsBoard" in html
        assert "copilot_board.js" in html
        assert "sectionModal" in html
        assert "sectionChatInput" in html
