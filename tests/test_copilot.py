"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Abnahmetests fuer Copilot-Chat.
Deckt C1-C7 ab: Persistenz, API, Verlauf, UI, Abgrenzung.
"""
import json
import pytest
from unittest.mock import patch

from services import copilot_marker_service
from services.copilot_marker_service import Marker, _write_marker
from services.copilot_service import build_marker_chat_context, call_copilot, list_copilot_runs


# --- C1: Persistenz ---

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

        # In DB pruefen
        runs = list_copilot_runs(thread_id=result["thread_id"])
        assert len(runs) >= 1
        found = [r for r in runs if r["id"] == result["copilot_run_id"]]
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

        _write_marker(str(handoff_path), Marker(
            marker_id="144",
            titel="Week-Daten fixen + Usage Reports Seite",
            plan_id="144",
            status="in_progress",
            ziel="Week-Daten stabilisieren",
            naechster_schritt="Reports validieren",
            prompt="Bitte fixen",
            prompt_suggestion="Nutze echte Week-Daten",
            risiko="Abweichende Summen",
            checks=["Report stimmt", "Week-Ansicht passt"],
            last_session="sess_123",
            updated_at="2026-04-04T12:00:00+00:00",
        ))
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

        _write_marker(str(project_dir / "handoff.md"), Marker(
            marker_id="144",
            titel="Week-Daten fixen + Usage Reports Seite",
            plan_id="144",
            status="todo",
            ziel="Week-Daten stabilisieren",
            naechster_schritt="Reports validieren",
            prompt="Bitte fixen",
            prompt_suggestion="Nutze echte Week-Daten",
            risiko="Abweichende Summen",
            checks=["Report stimmt"],
        ))
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
            m["content"] for m in captured["messages"]
            if "Aktiver Marker-Kontext" in m.get("content", "")
        ]
        assert len(context_messages) == 1
        assert '"marker_id": "144"' in context_messages[0]
        assert '"plan_title": "Master Plan April"' in context_messages[0]
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


# --- C2: POST /api/copilot/chat ---

class TestChatEndpoint:
    @patch("services.copilot_service.query_perplexity")
    def test_success(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {
            "content": "Das sieht gut aus.",
            "model": "sonar",
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
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
        assert d["total_tokens"] == 20
        assert d["cost_usd"] is not None

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
    def test_with_project_and_thread(self, mock_llm, client, mock_copilot_db):
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
    def test_connector_error_returns_422(self, mock_llm, client, mock_copilot_db):
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
    def test_filter_by_project(self, mock_llm, client, mock_copilot_db):
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
    def test_filter_by_thread(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        client.post("/api/copilot/chat",
                     data=json.dumps({"message": "Frage", "thread_id": "th-filter-test"}),
                     content_type="application/json")

        r = client.get("/api/copilot/runs?thread_id=th-filter-test")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) >= 1
        assert all(run["thread_id"] == "th-filter-test" for run in d["runs"])

    def test_limit(self, client, mock_copilot_db):
        r = client.get("/api/copilot/runs?limit=2")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["runs"]) <= 2

    @patch("services.copilot_service.query_perplexity")
    def test_runs_include_usage_and_cost(self, mock_llm, client, mock_copilot_db):
        mock_llm.return_value = {
            "content": "Reply",
            "model": "sonar-pro",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        client.post("/api/copilot/chat",
                    data=json.dumps({"message": "Kosten zeigen", "thread_id": "usage-test"}),
                    content_type="application/json")

        r = client.get("/api/copilot/runs?thread_id=usage-test")
        assert r.status_code == 200
        runs = r.get_json()["runs"]
        assert len(runs) == 1
        assert runs[0]["input_tokens"] == 100
        assert runs[0]["output_tokens"] == 50
        assert runs[0]["total_tokens"] == 150
        assert runs[0]["cost_usd"] is not None


# --- C4: UI ---

class TestUI:
    def test_copilot_without_plan_id_redirects(self, client):
        """/copilot ohne plan_id redirectet zum letzten Plan oder nach /plans."""
        r = client.get("/copilot", follow_redirects=False)
        assert r.status_code in (302, 303)
        location = r.headers.get("Location", "")
        assert location.startswith("/copilot?plan_id=") or location == "/plans"


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
    def test_chat_with_plan_id(self, mock_llm, client, mock_copilot_db):
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
    def test_runs_filter_by_plan_id(self, mock_llm, client, mock_copilot_db):
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
    def test_chat_with_images(self, mock_llm, client, mock_copilot_db):
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
    def test_chat_without_images_backward_compatible(self, mock_llm, client, mock_copilot_db):
        """C5: Runs ohne Bilder funktionieren weiterhin."""
        mock_llm.return_value = {"content": "OK", "model": "sonar", "usage": {}}
        r = client.post("/api/copilot/chat",
                        data=json.dumps({"message": "Einfache Frage"}),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["images"] is None

    @patch("services.copilot_service.query_perplexity")
    def test_runs_with_images_in_listing(self, mock_llm, client, mock_copilot_db):
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


class TestMarkerActivationEndpoint:
    def test_activate_marker_success(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(project_dir / "handoff.md"), Marker(
            marker_id="001",
            titel="Startbereit",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Arbeite diesen Marker ab",
            checks=["Check eins"],
        ))

        r = client.post(
            "/api/copilot/markers/001/activate",
            data=json.dumps({"project_id": "demo", "context_path": "marker-context.md"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["marker_id"] == "001"
        assert data["status"] == "in_progress"
        assert (project_dir / "marker-context.md").exists()

    def test_activate_marker_gate_blocked(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(project_dir / "handoff.md"), Marker(
            marker_id="001",
            titel="Nicht startbereit",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="",
            checks=["Check eins"],
        ))

        r = client.post(
            "/api/copilot/markers/001/activate",
            data=json.dumps({"project_id": "demo", "context_path": "marker-context.md"}),
            content_type="application/json",
        )
        assert r.status_code == 409
        data = r.get_json()
        assert data["ok"] is False
        assert data["error"] == "gate_blocked"
        assert data["reason"] == "prompt ist leer"

    def test_close_marker_success(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Writeback Marker",
            plan_id="42",
            status="in_progress",
            ziel="Ziel",
            naechster_schritt="Aktuell",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        r = client.post(
            "/api/copilot/markers/001/close",
            data=json.dumps({
                "project_id": "demo",
                "status": "done",
                "naechster_schritt": "Parser noch einmal gegen echten Repo-Stand laufen lassen",
                "last_session": "sess_abc123",
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["marker_id"] == "001"
        assert data["status"] == "done"
        assert data["updated_at"]

        parsed = copilot_marker_service.parse_markers(str(handoff_path))
        assert parsed[0].status == "done"
        assert parsed[0].naechster_schritt == "Parser noch einmal gegen echten Repo-Stand laufen lassen"
        assert parsed[0].last_session == "sess_abc123"

    def test_close_marker_returns_marker_not_found(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        (project_dir / "handoff.md").write_text("", encoding="utf-8")
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        r = client.post(
            "/api/copilot/markers/404/close",
            data=json.dumps({"project_id": "demo", "status": "done"}),
            content_type="application/json",
        )
        assert r.status_code == 404
        data = r.get_json()
        assert data == {"ok": False, "error": "marker_not_found"}

    def test_close_marker_returns_handoff_missing(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        r = client.post(
            "/api/copilot/markers/001/close",
            data=json.dumps({"project_id": "demo", "status": "done"}),
            content_type="application/json",
        )
        assert r.status_code == 404
        data = r.get_json()
        assert data == {"ok": False, "error": "handoff_missing"}

    def test_close_marker_uses_project_from_marker_context(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        context_path = tmp_path / "marker-context.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Writeback Marker",
            plan_id="42",
            status="in_progress",
            ziel="Ziel",
            naechster_schritt="Aktuell",
            prompt="Prompt",
            checks=["Check eins"],
        ))
        context_path.write_text(
            "# Marker-Kontext\n\n"
            "- marker_id: 001\n"
            "- plan_id: 42\n"
            "- project_id: demo\n",
            encoding="utf-8",
        )

        r = client.post(
            "/api/copilot/markers/001/close",
            data=json.dumps({
                "context_path": str(context_path),
                "status": "done",
                "last_session": "sess_ctx_1",
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["status"] == "done"

        parsed = copilot_marker_service.parse_markers(str(handoff_path))
        assert parsed[0].status == "done"
        assert parsed[0].last_session == "sess_ctx_1"

    def test_sprint_to_markers_endpoint(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        sprint_path = tmp_path / "sprint-p5.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        sprint_path.write_text(
            "# Sprint P5\n\n"
            "**Plan-ID:** sprint-p5\n\n"
            "## Aufgaben\n\n"
            "- [ ] Marker-Service implementieren\n"
            "- [ ] Route bauen\n",
            encoding="utf-8",
        )

        r = client.post(
            "/api/sprint/sprint-p5/to-markers",
            data=json.dumps({
                "project_id": "demo",
                "sprint_path": str(sprint_path),
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["plan_id"] == "sprint-p5"
        assert data["count"] == 2

        parsed = copilot_marker_service.parse_markers(str(project_dir / "handoff.md"))
        assert len(parsed) == 2
        assert all(marker.plan_id == "sprint-p5" for marker in parsed)
        assert all(marker.prompt_suggestion for marker in parsed)

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
        assert "addSectionModal" in html
        assert "panel-chat-input" in html


class TestMarkerAPI:
    def test_get_markers_for_plan(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="",
            checks=["Check eins"],
        ))

        r = client.get("/api/copilot/markers?project_id=demo&plan_id=42")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["markers"]) == 1
        assert data["markers"][0]["marker_id"] == "001"
        assert data["markers"][0]["gate_reason"] == "prompt ist leer"

    def test_patch_marker_status(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        r = client.patch(
            "/api/copilot/markers/001/status",
            data=json.dumps({"project_id": "demo", "status": "done"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["status"] == "done"

    def test_patch_marker_fields_adopts_prompt(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="",
            prompt_suggestion="Nutze diesen Prompt",
            checks=["Check eins"],
        ))

        r = client.patch(
            "/api/copilot/markers/001/fields",
            data=json.dumps({"project_id": "demo", "fields": {"prompt": "Nutze diesen Prompt"}}),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["prompt"] == "Nutze diesen Prompt"
        assert data["is_activatable"] is True
        assert data["gate_reason"] == ""
