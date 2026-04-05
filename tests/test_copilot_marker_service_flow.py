from services import copilot_marker_service
from services.copilot_marker_service import (
    Marker,
    MarkerActivationError,
    activate_marker,
    backfill_marker_last_sessions,
    buildsuggestion,
    close_marker,
    is_activatable,
    list_markers_for_plan,
    parse_markers,
    plan_to_marker,
    sprinttomarkers,
    sprinttomarkers_from_content,
    _write_marker,
)


class TestCopilotMarkerServiceFlow:
    def test_sprinttomarkers_from_content_uses_plan_content_without_external_file(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        content = "### Sprint P-E3 #sprint-p-e3\nPlan-ID: sprint-p-e3\n\n- [ ] Execution-Rating speichern\n#### Session Detail #spec-session-detail\n- [ ] Marker-Panel anzeigen\n"
        markers = sprinttomarkers_from_content(content, "sprint-p-e3", str(handoff_path), source_label="plan-144.md")
        assert len(markers) == 2
        assert markers[0].plan_id == "sprint-p-e3"
        assert "plan-144.md" in markers[0].prompt_suggestion
        assert markers[0].sprint_tag == "#sprint-p-e3"
        assert markers[0].spec_tag == ""
        assert markers[1].spec_tag == "#spec-session-detail"

    def test_plan_to_marker_creates_single_marker_for_classic_plan(self, tmp_path):
        markers = plan_to_marker(
            "144",
            str(tmp_path / "handoff.md"),
            title="Week-Daten fixen + Usage Reports Seite",
            context_summary="Usage Reports bauen",
            next_action="Plan im Detail ausarbeiten",
            source_label="curried-doodling-bubble.md",
        )
        assert len(markers) == 1
        assert markers[0].marker_id == "144"
        assert markers[0].titel == "Week-Daten fixen + Usage Reports Seite"
        assert "curried-doodling-bubble.md" in markers[0].prompt_suggestion

    def test_list_markers_regenerates_legacy_handoff_once(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        handoff_path.write_text("# Legacy Handoff\n", encoding="utf-8")
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        def fake_write_handoff(project_id):
            _write_marker(str(handoff_path), Marker(marker_id="145", titel="Regenerierter Marker", plan_id="145", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt", checks=["Check eins"]))
            return str(handoff_path), handoff_path.read_text(encoding="utf-8")

        monkeypatch.setattr("services.project_handoff_service.write_handoff", fake_write_handoff)
        markers = list_markers_for_plan("demo", "145")
        assert len(markers) == 1
        assert markers[0]["marker_id"] == "145"
        assert markers[0]["is_activatable"] is True

    def test_is_activatable_matches_gate_logic(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Nicht freigegeben", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="", checks=["Check eins"]))
        _write_marker(str(handoff_path), Marker(marker_id="002", titel="Freigegeben", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt gesetzt", checks=["Check eins"]))
        assert is_activatable(str(handoff_path), "001") == (False, "prompt ist leer")
        assert is_activatable(str(handoff_path), "002") == (True, "")

    def test_activate_marker_writes_context_and_status(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Aktivierbarer Marker",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Naechster Schritt",
            prompt="Bitte fuehre den Marker aus",
            risiko="mittel",
            checks=["Check eins", "Check zwei"],
            sprint_tag="#sprint-demo",
            spec_tag="#spec-kontext",
        ))

        result = activate_marker("demo", "001", "marker-context.md")
        context_path = project_dir / "marker-context.md"
        assert result["marker"]["status"] == "in_progress"
        assert result["context_path"] == str(context_path)
        assert context_path.exists()
        content = context_path.read_text(encoding="utf-8")
        assert "- sprint_tag: #sprint-demo" in content
        assert "- spec_tag: #spec-kontext" in content
        assert "Bitte fuehre den Marker aus" in content
        assert parse_markers(str(handoff_path))[0].status == "in_progress"

    def test_activate_marker_blocks_when_gate_fails(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Blockierter Marker", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Naechster Schritt", prompt="", checks=["Check eins"]))

        try:
            activate_marker("demo", "001", "marker-context.md")
            assert False, "MarkerActivationError erwartet"
        except MarkerActivationError as exc:
            assert str(exc) == "gate_blocked"
            assert exc.gate_reason == "prompt ist leer"

        assert not (project_dir / "marker-context.md").exists()
        assert parse_markers(str(handoff_path))[0].status == "todo"

    def test_close_marker_roundtrip_writes_back_session_fields(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Writeback Marker", plan_id="42", status="in_progress", ziel="Ziel", naechster_schritt="Aktuell", prompt="Prompt", checks=["Check eins"], updated_at="2026-04-04T08:00:00+00:00"))
        marker = close_marker(str(handoff_path), "001", status="done", naechster_schritt="Parser noch einmal gegen echten Repo-Stand laufen lassen", last_session="sess_123")
        assert marker.status == "done"
        assert marker.last_session == "sess_123"
        assert parse_markers(str(handoff_path))[0].status == "done"

    def test_sprinttomarkers_creates_markers_and_is_idempotent(self, tmp_path):
        sprint_path = tmp_path / "sprint-p5.md"
        handoff_path = tmp_path / "handoff.md"
        sprint_path.write_text("# Sprint P5\n\n**Plan-ID:** sprint-p5\n\n## Aufgaben\n\n- [ ] Marker-Service implementieren\n- [ ] Route bauen\n", encoding="utf-8")
        markers = sprinttomarkers(str(sprint_path), "sprint-p5", str(handoff_path))
        assert len(markers) == 2
        second_run = sprinttomarkers(str(sprint_path), "sprint-p5", str(handoff_path))
        assert len(second_run) == 2
        parsed = parse_markers(str(handoff_path))
        assert len(parsed) == 2
        assert parsed[0].prompt_suggestion
        assert parsed[1].prompt_suggestion

    def test_buildsuggestion_uses_sprint_context(self):
        marker = Marker(marker_id="sprint-p5-route-bauen", titel="Route bauen", plan_id="sprint-p5", status="todo", ziel="Route bauen", naechster_schritt="Sprint-Aufgabe im Detail ausarbeiten", prompt="")
        suggestion = buildsuggestion(marker, {"sprint_title": "Sprint P5", "sprint_path": "/tmp/sprint-p5.md"})
        assert "Route bauen" in suggestion
        assert "Sprint P5" in suggestion
        assert "sprint-p5.md" in suggestion

    def test_close_marker_removes_context_file_if_provided(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        context_path = project_dir / "marker-context.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Cleanup Test Marker", plan_id="42", status="in_progress", ziel="Test Ziel", naechster_schritt="Test Schritt", prompt="Test Prompt", checks=["Check eins"], updated_at="2026-04-04T08:00:00+00:00"))
        context_path.write_text("# Marker-Kontext\n- marker_id: 001\n- plan_id: 42\n- titel: Cleanup Test Marker\n")
        marker = close_marker(str(handoff_path), "001", project_id="demo", status="done", context_path="marker-context.md")
        assert marker.status == "done"
        assert not context_path.exists()

    def test_close_marker_does_not_remove_context_file_if_not_provided(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        context_path = project_dir / "marker-context.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        _write_marker(str(handoff_path), Marker(marker_id="002", titel="Keep Context Test Marker", plan_id="43", status="in_progress", ziel="Test Ziel", naechster_schritt="Test Schritt", prompt="Test Prompt", checks=["Check eins"], updated_at="2026-04-04T08:00:00+00:00"))
        context_path.write_text("# Marker-Kontext\n- marker_id: 002\n- plan_id: 43\n- titel: Keep Context Test Marker\n")
        marker = close_marker(str(handoff_path), "002", project_id="demo", status="done")
        assert marker.status == "done"
        assert context_path.exists()

    def test_backfill_marker_last_sessions_uses_project_plan_session_uuid(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))
        _write_marker(str(handoff_path), Marker(
            marker_id="145",
            titel="Plan Marker",
            plan_id="145",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        def fake_execute(sql, params=None, fetch=False, fetchone=False):
            if "FROM project_plans" in sql:
                return [{"id": 145, "session_uuid": "sess_plan_145"}]
            return []

        monkeypatch.setattr("services.copilot_marker_service.execute", fake_execute)

        result = backfill_marker_last_sessions("demo")

        assert result["updated"] == 1
        assert parse_markers(str(handoff_path))[0].last_session == "sess_plan_145"
