import json

from services import copilot_marker_service
from services.copilot_marker_service import Marker, _write_marker


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

        response = client.get("/api/copilot/markers?project_id=demo&plan_id=42")
        assert response.status_code == 200
        data = response.get_json()
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

        response = client.patch(
            "/api/copilot/markers/001/status",
            data=json.dumps({"project_id": "demo", "status": "done"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
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

        response = client.patch(
            "/api/copilot/markers/001/fields",
            data=json.dumps({"project_id": "demo", "fields": {"prompt": "Nutze diesen Prompt"}}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["prompt"] == "Nutze diesen Prompt"
        assert data["is_activatable"] is True
        assert data["gate_reason"] == ""

    def test_post_execution_rating_updates_marker_and_session(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        writes = []
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        monkeypatch.setattr(copilot_marker_service, "ensure_session_review_schema", lambda: None)
        monkeypatch.setattr(
            copilot_marker_service,
            "execute",
            lambda sql, params=None, fetch=False, fetchone=False: writes.append((sql, params)),
        )

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="42",
            status="done",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        response = client.post(
            "/api/marker/001/execution-rating",
            data=json.dumps({
                "project_id": "demo",
                "execution_score": 4,
                "execution_comment": "Stabil geliefert",
                "sessionid": "sess-123",
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["marker_id"] == "001"
        assert data["execution_score"] == 4
        assert data["execution_comment"] == "Stabil geliefert"
        assert data["last_execution_at"]

        parsed = copilot_marker_service.parse_markers(str(handoff_path))
        assert parsed[0].execution_score == 4
        assert parsed[0].execution_comment == "Stabil geliefert"
        assert len(writes) == 1
        assert writes[0][1] == (4, "Stabil geliefert", "sess-123")

    def test_post_execution_rating_rejects_out_of_range_score(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(project_dir / "handoff.md"), Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="42",
            status="done",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        response = client.post(
            "/api/marker/001/execution-rating",
            data=json.dumps({"project_id": "demo", "execution_score": 7}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "zwischen 0 und 5" in response.get_json()["error"]

    def test_get_execution_rating_returns_current_marker_state(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="42",
            status="done",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
            execution_score=2,
            execution_comment="Noch wacklig",
            last_execution_at="2026-04-04T10:00:00+00:00",
        ))

        response = client.get("/api/marker/001/execution-rating?project_id=demo&plan_id=42")
        assert response.status_code == 200
        data = response.get_json()
        assert data["execution_score"] == 2
        assert data["execution_comment"] == "Noch wacklig"
        assert data["last_execution_at"] == "2026-04-04T10:00:00+00:00"

    def test_close_marker_route_removes_context_file(self, client, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        context_path = project_dir / "marker-context.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Active Marker",
            plan_id="42",
            status="in_progress",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
            updated_at="2026-04-04T08:00:00+00:00",
        ))
        context_path.write_text("# Marker-Kontext\n- marker_id: 001\n- plan_id: 42\n- project_id: demo\n", encoding="utf-8")

        response = client.post("/api/copilot/markers/001/close", json={"project_id": "demo", "status": "done"})
        assert response.status_code == 200
        assert response.get_json()["ok"] is True
        assert not context_path.exists()
