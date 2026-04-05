import json

from services import copilot_marker_service
from services.copilot_marker_service import Marker, _write_marker


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

        response = client.post(
            "/api/copilot/markers/001/activate",
            data=json.dumps({"project_id": "demo", "context_path": "marker-context.md"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
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

        response = client.post(
            "/api/copilot/markers/001/activate",
            data=json.dumps({"project_id": "demo", "context_path": "marker-context.md"}),
            content_type="application/json",
        )
        assert response.status_code == 409
        data = response.get_json()
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

        response = client.post(
            "/api/copilot/markers/001/close",
            data=json.dumps({
                "project_id": "demo",
                "status": "done",
                "naechster_schritt": "Parser noch einmal gegen echten Repo-Stand laufen lassen",
                "last_session": "sess_abc123",
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
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

        response = client.post(
            "/api/copilot/markers/404/close",
            data=json.dumps({"project_id": "demo", "status": "done"}),
            content_type="application/json",
        )
        assert response.status_code == 404
        assert response.get_json() == {"ok": False, "error": "marker_not_found"}

    def test_close_marker_returns_handoff_missing(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        response = client.post(
            "/api/copilot/markers/001/close",
            data=json.dumps({"project_id": "demo", "status": "done"}),
            content_type="application/json",
        )
        assert response.status_code == 404
        assert response.get_json() == {"ok": False, "error": "handoff_missing"}

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

        response = client.post(
            "/api/copilot/markers/001/close",
            data=json.dumps({"context_path": str(context_path), "status": "done", "last_session": "sess_ctx_1"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is True

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

        response = client.post(
            "/api/sprint/sprint-p5/to-markers",
            data=json.dumps({"project_id": "demo", "sprint_path": str(sprint_path)}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["plan_id"] == "sprint-p5"
        assert data["count"] == 2

        parsed = copilot_marker_service.parse_markers(str(project_dir / "handoff.md"))
        assert len(parsed) == 2
        assert all(marker.plan_id == "sprint-p5" for marker in parsed)
        assert all(marker.prompt_suggestion for marker in parsed)

    def test_sprint_to_markers_endpoint_falls_back_to_db_plan_content(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        import routes.copilot_marker_routes as copilot_marker_routes

        original_execute = copilot_marker_routes.execute

        def fake_execute(query, params=None, fetch=False, fetchone=False):
            compact = " ".join(str(query).lower().split())
            if "from project_plans where id = %s" in compact:
                return {
                    "content": "# Sprint P-E3\n\n**Plan-ID:** sprint-p-e3\n\n## Aufgaben\n\n- [ ] Execution-Rating speichern\n- [ ] Marker-Panel anzeigen\n",
                    "filename": "plan-144.md",
                    "title": "Sprint P-E3",
                }
            return original_execute(query, params, fetch=fetch, fetchone=fetchone)

        monkeypatch.setattr(copilot_marker_routes, "execute", fake_execute)

        response = client.post(
            "/api/sprint/sprint-p-e3/to-markers",
            data=json.dumps({"project_id": "demo", "db_plan_id": 144, "sprint_path": "nicht-vorhanden.md"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["count"] == 2

    def test_sprint_to_markers_endpoint_falls_back_to_single_marker_for_classic_plan(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        import routes.copilot_marker_routes as copilot_marker_routes

        original_execute = copilot_marker_routes.execute

        def fake_execute(query, params=None, fetch=False, fetchone=False):
            compact = " ".join(str(query).lower().split())
            if "from project_plans where id = %s" in compact:
                return {
                    "content": "# Plan: Week-Daten fixen + Usage Reports Seite\n\n## Context\nKlassischer Plan ohne Sprint-Sektion.\n",
                    "filename": "curried-doodling-bubble.md",
                    "title": "Week-Daten fixen + Usage Reports Seite",
                }
            return original_execute(query, params, fetch=fetch, fetchone=fetchone)

        monkeypatch.setattr(copilot_marker_routes, "execute", fake_execute)

        response = client.post(
            "/api/sprint/144/to-markers",
            data=json.dumps({"project_id": "demo", "db_plan_id": 144, "sprint_path": "nicht-vorhanden.md"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["count"] == 1

        parsed = copilot_marker_service.parse_markers(str(project_dir / "handoff.md"))
        assert len(parsed) == 1
        assert parsed[0].marker_id == "144"
        assert parsed[0].titel == "Week-Daten fixen + Usage Reports Seite"
