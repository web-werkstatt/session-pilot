"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Abnahmetests fuer Copilot-Chat.
Deckt C1-C7 ab: Persistenz, API, Verlauf, UI, Abgrenzung.
"""
import json
from unittest.mock import patch

from services import copilot_marker_service
from services.copilot_marker_service import Marker, _write_marker
from services.copilot_service import build_marker_chat_context, call_copilot, list_copilot_runs


class TestPersistence:
    @patch("services.copilot_service.query_perplexity")
    def test_successful_run_persisted(self, mock_llm, mock_copilot_db):
        mock_llm.return_value = {
            "content": "Alles klar, das Projekt sieht gut aus.",
            "model": "sonar-test",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        result = call_copilot("Wie steht das Projekt?", project_id="test_proj")
        assert result["status"] == "success"
        assert result["copilot_run_id"] is not None
        assert result["reply"] == "Alles klar, das Projekt sieht gut aus."
        assert result["thread_id"] is not None
        assert result["total_tokens"] == 15
        assert result["cost_usd"] is not None

        runs = list_copilot_runs(thread_id=result["thread_id"])
        assert len(runs) >= 1
        found = [run for run in runs if run["id"] == result["copilot_run_id"]]
        assert len(found) == 1
        assert found[0]["status"] == "success"
        assert found[0]["total_tokens"] == 15
        assert found[0]["cost_usd"] is not None

    def test_build_marker_chat_context_prefers_handoff_truth(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        context_path = project_dir / "marker-context.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        monkeypatch.setattr("services.copilot_service._resolve_plan_title", lambda plan_id: "Master Plan April")

        test_marker = Marker(
            marker_id="144",
            titel="Week-Daten fixen + Usage Reports Seite",
            plan_id="144",
            sprint_tag="#sprint-p3",
            spec_tag="#spec-usage-reports",
            status="in_progress",
            ziel="Week-Daten stabilisieren",
            naechster_schritt="Reports validieren",
            prompt="Bitte fixen",
            prompt_suggestion="Nutze echte Week-Daten",
            risiko="Abweichende Summen",
            checks=["Report stimmt", "Week-Ansicht passt"],
            last_session="sess_123",
            updated_at="2026-04-04T12:00:00+00:00",
        )
        _write_marker(str(handoff_path), test_marker)
        # DB-first: core_get_marker patchen, damit er den Marker aus handoff.md liefert
        monkeypatch.setattr(
            "services.workflow_core_service.get_marker",
            lambda project, mid: test_marker if mid == "144" else None,
        )
        context_path.write_text(
            "# Marker-Kontext\n\n"
            "- marker_id: 144\n"
            "- plan_id: 144\n"
            "- project_id: demo\n"
            "- titel: Alter Titel\n"
            "- naechster_schritt: Veralteter Schritt\n",
            encoding="utf-8",
        )

        result = build_marker_chat_context(project_id="demo", frontend_context={
            "marker_id": "144",
            "titel": "Frontend Titel",
            "naechster_schritt": "Frontend Schritt",
        })

        assert result["marker_id"] == "144"
        assert result["plan_id"] == "144"
        assert result["plan_title"] == "Master Plan April"
        assert result["sprint_tag"] == "#sprint-p3"
        assert result["spec_tag"] == "#spec-usage-reports"
        assert result["titel"] == "Week-Daten fixen + Usage Reports Seite"
        assert result["naechster_schritt"] == "Reports validieren"
        assert result["status"] == "in_progress"
        assert result["checks"] == ["Report stimmt", "Week-Ansicht passt"]

    @patch("services.copilot_service.query_perplexity")
    def test_call_copilot_injects_server_side_marker_context(self, mock_llm, tmp_path, monkeypatch, mock_copilot_db):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        monkeypatch.setattr("services.copilot_service._resolve_plan_title", lambda plan_id: "Master Plan April")

        inject_marker = Marker(
            marker_id="144",
            titel="Week-Daten fixen + Usage Reports Seite",
            plan_id="144",
            sprint_tag="#sprint-p3",
            spec_tag="#spec-usage-reports",
            status="todo",
            ziel="Week-Daten stabilisieren",
            naechster_schritt="Reports validieren",
            prompt="Bitte fixen",
            prompt_suggestion="Nutze echte Week-Daten",
            risiko="Abweichende Summen",
            checks=["Report stimmt"],
        )
        _write_marker(str(project_dir / "handoff.md"), inject_marker)
        monkeypatch.setattr(
            "services.workflow_core_service.get_marker",
            lambda project, mid: inject_marker if mid == "144" else None,
        )
        (project_dir / "marker-context.md").write_text(
            "# Marker-Kontext\n\n"
            "- marker_id: 144\n"
            "- plan_id: 144\n"
            "- project_id: demo\n",
            encoding="utf-8",
        )

        captured = {}

        def fake_llm(**kwargs):
            captured["messages"] = kwargs["messages"]
            return {"content": "OK", "model": "sonar", "usage": {}}

        mock_llm.side_effect = fake_llm

        result = call_copilot(
            "Was ist der naechste Schritt?",
            project_id="demo",
            context={"marker_id": "144", "titel": "Frontend Titel"},
        )

        assert result["status"] == "success"
        context_messages = [
            message["content"] for message in captured["messages"]
            if "Aktiver Marker-Kontext" in message.get("content", "")
        ]
        assert len(context_messages) == 1
        assert '"marker_id": "144"' in context_messages[0]
        assert '"plan_title": "Master Plan April"' in context_messages[0]
        assert '"sprint_tag": "#sprint-p3"' in context_messages[0]
        assert '"spec_tag": "#spec-usage-reports"' in context_messages[0]
        assert '"titel": "Week-Daten fixen + Usage Reports Seite"' in context_messages[0]
        assert '"naechster_schritt": "Reports validieren"' in context_messages[0]
        assert '"titel": "Frontend Titel"' not in context_messages[0]

    @patch("services.copilot_service.query_perplexity")
    def test_failure_persisted(self, mock_llm, mock_copilot_db):
        from services.perplexity_service import PerplexityConfigError

        mock_llm.side_effect = PerplexityConfigError("Key fehlt")
        result = call_copilot("Test", project_id="test_fail")
        assert result["status"] == "failure"
        assert "Config-Fehler" in result["error_info"]
        assert result["copilot_run_id"] is not None


class TestChatEndpoint:
    @patch("services.copilot_service.query_perplexity")
    def test_success(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {
            "content": "Das sieht gut aus.",
            "model": "sonar",
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }
        response = client.post("/api/copilot/chat", data=json.dumps({"message": "Hallo Copilot"}), content_type="application/json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["reply"] == "Das sieht gut aus."
        assert "copilot_run_id" in data
        assert "thread_id" in data
        assert "created_at" in data
        assert data["total_tokens"] == 20
        assert data["cost_usd"] is not None

    def test_missing_message(self, client):
        response = client.post("/api/copilot/chat", data=json.dumps({"project_id": "test"}), content_type="application/json")
        assert response.status_code == 400

    def test_empty_message(self, client):
        response = client.post("/api/copilot/chat", data=json.dumps({"message": "  "}), content_type="application/json")
        assert response.status_code == 400

    @patch("services.copilot_service.query_perplexity")
    def test_with_project_and_thread(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        response = client.post(
            "/api/copilot/chat",
            data=json.dumps({"message": "Test", "project_id": "my_project", "thread_id": "thread-123"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["project_id"] == "my_project"
        assert data["thread_id"] == "thread-123"

    @patch("services.copilot_service.query_perplexity")
    def test_connector_error_returns_422(self, mock_llm, client, mock_copilot_db):
        from services.perplexity_service import PerplexityConfigError

        mock_llm.side_effect = PerplexityConfigError("No key")
        response = client.post("/api/copilot/chat", data=json.dumps({"message": "Test"}), content_type="application/json")
        assert response.status_code == 422
        data = response.get_json()
        assert data["status"] == "failure"
        assert data["error_info"] is not None


class TestRunsEndpoint:
    @patch("services.copilot_service.query_perplexity")
    def test_filter_by_project(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        client.post("/api/copilot/chat", data=json.dumps({"message": "Frage", "project_id": "filter_test_proj"}), content_type="application/json")

        response = client.get("/api/copilot/runs?project_id=filter_test_proj")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["runs"]) >= 1
        assert all(run["project_id"] == "filter_test_proj" for run in data["runs"])

    @patch("services.copilot_service.query_perplexity")
    def test_filter_by_thread(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        client.post("/api/copilot/chat", data=json.dumps({"message": "Frage", "thread_id": "th-filter-test"}), content_type="application/json")

        response = client.get("/api/copilot/runs?thread_id=th-filter-test")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["runs"]) >= 1
        assert all(run["thread_id"] == "th-filter-test" for run in data["runs"])

    def test_limit(self, client, mock_copilot_db):
        response = client.get("/api/copilot/runs?limit=2")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["runs"]) <= 2

    @patch("services.copilot_service.query_perplexity")
    def test_runs_include_usage_and_cost(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {
            "content": "Reply",
            "model": "sonar-pro",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        client.post("/api/copilot/chat", data=json.dumps({"message": "Kosten zeigen", "thread_id": "usage-test"}), content_type="application/json")

        response = client.get("/api/copilot/runs?thread_id=usage-test")
        assert response.status_code == 200
        runs = response.get_json()["runs"]
        assert len(runs) == 1
        assert runs[0]["input_tokens"] == 100
        assert runs[0]["output_tokens"] == 50
        assert runs[0]["total_tokens"] == 150
        assert runs[0]["cost_usd"] is not None


class TestUI:
    def test_copilot_without_plan_id_redirects(self, client):
        response = client.get("/copilot", follow_redirects=False)
        assert response.status_code in (302, 303)
        location = response.headers.get("Location", "")
        assert location.startswith("/copilot?plan_id=") or location == "/plans"


class TestSeparation:
    def test_copilot_routes_separate_from_commands(self, client):
        response = client.get("/copilot")
        assert response.status_code in (200, 302)
        assert client.get("/llm-commands").status_code == 200
        assert client.get("/api/llm/commands").status_code == 200


class TestPlanCopilotChat:
    @patch("services.copilot_service.query_perplexity")
    def test_chat_with_plan_id(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "Plan-Antwort", "model": "sonar", "usage": {}}
        response = client.post(
            "/api/copilot/chat",
            data=json.dumps({"message": "Was ist der naechste Schritt?", "plan_id": 1, "project_id": "test_plan_proj"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["plan_id"] == 1
        assert data["status"] == "success"

    @patch("services.copilot_service.query_perplexity")
    def test_runs_filter_by_plan_id(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        client.post("/api/copilot/chat", data=json.dumps({"message": "Plan-Frage", "plan_id": 42}), content_type="application/json")

        response = client.get("/api/copilot/runs?plan_id=42")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["runs"]) >= 1
        assert all(run["plan_id"] == 42 for run in data["runs"])

    @patch("services.copilot_service.query_perplexity")
    def test_chat_with_images(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "Bild gesehen", "model": "sonar", "usage": {}}
        images = [{"filename": "screenshot.png", "url": "/static/uploads/copilot/abc.png", "mime_type": "image/png"}]
        response = client.post(
            "/api/copilot/chat",
            data=json.dumps({"message": "Sieh dir dieses Bild an", "plan_id": 99, "images": images}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["images"] is not None
        assert len(data["images"]) == 1
        assert data["images"][0]["filename"] == "screenshot.png"

    @patch("services.copilot_service.query_perplexity")
    def test_chat_without_images_backward_compatible(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        response = client.post("/api/copilot/chat", data=json.dumps({"message": "Einfache Frage"}), content_type="application/json")
        assert response.status_code == 200
        assert response.get_json()["images"] is None

    @patch("services.copilot_service.query_perplexity")
    def test_runs_with_images_in_listing(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        images = [{"filename": "test.jpg", "url": "/static/uploads/copilot/x.jpg", "mime_type": "image/jpeg"}]
        client.post("/api/copilot/chat", data=json.dumps({"message": "Bild", "plan_id": 77, "images": images}), content_type="application/json")

        response = client.get("/api/copilot/runs?plan_id=77")
        assert response.status_code == 200
        runs = response.get_json()["runs"]
        img_runs = [run for run in runs if run.get("images")]
        assert len(img_runs) >= 1
        assert img_runs[0]["images"][0]["filename"] == "test.jpg"

    def test_upload_image_no_file(self, client):
        assert client.post("/api/copilot/upload_image").status_code == 400

    def test_upload_image_success(self, client):
        import io

        data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "test-upload.png", "image/png"),
        }
        response = client.post("/api/copilot/upload_image", data=data, content_type="multipart/form-data")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["filename"] == "test-upload.png"
        assert payload["url"].startswith("/static/uploads/copilot/")
        assert payload["mime_type"] == "image/png"

    def test_upload_image_wrong_type(self, client):
        import io

        data = {"file": (io.BytesIO(b"not a pdf"), "evil.pdf", "application/pdf")}
        assert client.post("/api/copilot/upload_image", data=data, content_type="multipart/form-data").status_code == 400

    def test_plans_page_has_no_copilot_tab(self, client):
        response = client.get("/plans")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'data-tab="copilot"' not in html
        assert "planChatMessages" not in html

    def test_copilot_board_renders_for_plan_id(self, client):
        response = client.get("/copilot?plan_id=1")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "sectionsBoard" in html
        assert "copilot_board.js" in html
        assert "addSectionModal" in html
        assert "panel-chat-input" in html
