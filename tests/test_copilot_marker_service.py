from services import copilot_marker_service
from services.copilot_marker_service import (
    Marker,
    MarkerActivationError,
    buildsuggestion,
    close_marker,
    read_marker_context,
    sprinttomarkers,
    _serialize_marker,
    _write_marker,
    activate_marker,
    get_marker_context,
    is_activatable,
    list_markers_for_plan,
    parse_markers,
    update_marker_fields,
    update_marker_status,
)


class TestCopilotMarkerService:
    def test_serialize_write_parse_roundtrip(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        marker = Marker(
            marker_id="001",
            titel="Beispiel-Marker",
            plan_id="sprint-p1",
            status="todo",
            ziel="Ein Marker soll korrekt serialisiert werden",
            naechster_schritt="Roundtrip testen",
            prompt="Nutze diesen Marker als Test",
            prompt_suggestion="Prompt vorschlagen",
            risiko="niedrig",
            checks=["Parser", "Writer"],
            last_session="",
            updated_at="2026-04-03T11:00:00+00:00",
        )

        block = _serialize_marker(marker)
        assert "<!-- MARKER:001" in block
        assert "## Beispiel-Marker · todo" in block

        _write_marker(str(handoff_path), marker)
        parsed = parse_markers(str(handoff_path))
        assert parsed == [marker]

    def test_write_replaces_existing_marker_by_id(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        marker = Marker(
            marker_id="001",
            titel="Marker Alt",
            plan_id="sprint-p1",
            status="todo",
            ziel="Alt",
            naechster_schritt="Alt",
            prompt="",
        )
        _write_marker(str(handoff_path), marker)

        updated = Marker(
            marker_id="001",
            titel="Marker Neu",
            plan_id="sprint-p1",
            status="in_progress",
            ziel="Neu",
            naechster_schritt="Weiter",
            prompt="Prompt",
            checks=["eins"],
        )
        _write_marker(str(handoff_path), updated)

        parsed = parse_markers(str(handoff_path))
        assert parsed == [updated]
        content = handoff_path.read_text(encoding="utf-8")
        assert "Marker Neu" in content
        assert "Marker Alt" not in content

    def test_write_appends_new_marker_when_missing(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        first = Marker(
            marker_id="001",
            titel="Marker Eins",
            plan_id="sprint-p1",
            status="todo",
            ziel="Ziel eins",
            naechster_schritt="Schritt eins",
            prompt="",
        )
        second = Marker(
            marker_id="002",
            titel="Marker Zwei",
            plan_id="sprint-p1",
            status="blocked",
            ziel="Ziel zwei",
            naechster_schritt="Schritt zwei",
            prompt="Prompt zwei",
        )
        _write_marker(str(handoff_path), first)
        _write_marker(str(handoff_path), second)

        parsed = parse_markers(str(handoff_path))
        assert parsed == [first, second]
        content = handoff_path.read_text(encoding="utf-8")
        assert content.count("<!-- MARKER:") == 2

    def test_list_markers_for_plan_computes_gate(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Ohne Prompt",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="",
            checks=["Check eins"],
        ))
        _write_marker(str(handoff_path), Marker(
            marker_id="002",
            titel="Ohne Checks",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt gesetzt",
            checks=[],
        ))
        _write_marker(str(handoff_path), Marker(
            marker_id="003",
            titel="Freigegeben",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt gesetzt",
            checks=["Check eins"],
        ))

        markers = list_markers_for_plan("demo", "42")
        assert [m["marker_id"] for m in markers] == ["001", "002", "003"]
        assert markers[0]["is_activatable"] is False
        assert markers[0]["gate_reason"] == "prompt ist leer"
        assert markers[1]["is_activatable"] is False
        assert markers[1]["gate_reason"] == "keine checks definiert"
        assert markers[2]["is_activatable"] is True
        assert markers[2]["gate_reason"] == ""

    def test_update_marker_status_writes_back(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Status Marker",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt gesetzt",
            checks=["Check eins"],
        ))

        updated = update_marker_status("demo", "001", "in_progress")
        assert updated["status"] == "in_progress"
        assert updated["updated_at"]

        parsed = parse_markers(str(handoff_path))
        assert parsed[0].status == "in_progress"
        assert parsed[0].updated_at

    def test_update_marker_fields_updates_prompt_and_context(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Prompt Marker",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="",
            prompt_suggestion="Nutze den Vorschlag",
            checks=["Check eins"],
        ))

        updated = update_marker_fields("demo", "001", {"prompt": "Nutze den Vorschlag"})
        assert updated["prompt"] == "Nutze den Vorschlag"
        assert updated["is_activatable"] is True
        assert updated["gate_reason"] == ""

        context = get_marker_context("demo", "001")
        assert context["prompt"] == "Nutze den Vorschlag"
        assert context["updated_at"]

    def test_list_markers_regenerates_legacy_handoff_once(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        handoff_path.write_text("# Legacy Handoff\n", encoding="utf-8")
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        def fake_write_handoff(project_id):
            _write_marker(str(handoff_path), Marker(
                marker_id="145",
                titel="Regenerierter Marker",
                plan_id="145",
                status="todo",
                ziel="Ziel",
                naechster_schritt="Schritt",
                prompt="Prompt",
                checks=["Check eins"],
            ))
            return str(handoff_path), handoff_path.read_text(encoding="utf-8")

        monkeypatch.setattr("services.project_handoff_service.write_handoff", fake_write_handoff)

        markers = list_markers_for_plan("demo", "145")
        assert len(markers) == 1
        assert markers[0]["marker_id"] == "145"
        assert markers[0]["is_activatable"] is True

    def test_is_activatable_matches_gate_logic(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Nicht freigegeben",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="",
            checks=["Check eins"],
        ))
        _write_marker(str(handoff_path), Marker(
            marker_id="002",
            titel="Freigegeben",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt gesetzt",
            checks=["Check eins"],
        ))

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
            last_session="",
        ))

        result = activate_marker("demo", "001", "marker-context.md")
        context_path = project_dir / "marker-context.md"

        assert result["marker"]["status"] == "in_progress"
        assert result["context_path"] == str(context_path)
        assert context_path.exists()

        content = context_path.read_text(encoding="utf-8")
        assert "# Marker-Kontext" in content
        assert "- marker_id: 001" in content
        assert "- project_id: demo" in content
        assert "## Prompt" in content
        assert "Bitte fuehre den Marker aus" in content
        assert "- Check eins" in content

        parsed = parse_markers(str(handoff_path))
        assert parsed[0].status == "in_progress"
        assert parsed[0].updated_at

    def test_activate_marker_blocks_when_gate_fails(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Blockierter Marker",
            plan_id="42",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Naechster Schritt",
            prompt="",
            checks=["Check eins"],
        ))

        try:
            activate_marker("demo", "001", "marker-context.md")
            assert False, "MarkerActivationError erwartet"
        except MarkerActivationError as exc:
            assert str(exc) == "gate_blocked"
            assert exc.gate_reason == "prompt ist leer"

        assert not (project_dir / "marker-context.md").exists()
        parsed = parse_markers(str(handoff_path))
        assert parsed[0].status == "todo"

    def test_close_marker_roundtrip_writes_back_session_fields(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Writeback Marker",
            plan_id="42",
            status="in_progress",
            ziel="Ziel",
            naechster_schritt="Aktuell",
            prompt="Prompt",
            checks=["Check eins"],
            updated_at="2026-04-04T08:00:00+00:00",
        ))

        marker = close_marker(
            str(handoff_path),
            "001",
            status="done",
            naechster_schritt="Parser noch einmal gegen echten Repo-Stand laufen lassen",
            last_session="sess_123",
        )

        assert marker.status == "done"
        assert marker.naechster_schritt == "Parser noch einmal gegen echten Repo-Stand laufen lassen"
        assert marker.last_session == "sess_123"
        assert marker.updated_at

        parsed = parse_markers(str(handoff_path))
        assert len(parsed) == 1
        assert parsed[0].status == "done"
        assert parsed[0].naechster_schritt == "Parser noch einmal gegen echten Repo-Stand laufen lassen"
        assert parsed[0].last_session == "sess_123"
        assert parsed[0].updated_at == marker.updated_at

    def test_read_marker_context_reads_project_and_plan_ids(self, tmp_path):
        context_path = tmp_path / "marker-context.md"
        context_path.write_text(
            "# Marker-Kontext\n\n"
            "- marker_id: 001\n"
            "- plan_id: 42\n"
            "- project_id: demo\n"
            "- titel: Beispiel\n",
            encoding="utf-8",
        )

        context = read_marker_context(context_path=str(context_path))
        assert context["marker_id"] == "001"
        assert context["plan_id"] == "42"
        assert context["project_id"] == "demo"
        assert context["context_path"] == str(context_path)

    def test_sprinttomarkers_creates_markers_and_is_idempotent(self, tmp_path):
        sprint_path = tmp_path / "sprint-p5.md"
        handoff_path = tmp_path / "handoff.md"
        sprint_path.write_text(
            "# Sprint P5\n\n"
            "**Plan-ID:** sprint-p5\n\n"
            "## Aufgaben\n\n"
            "- [ ] Marker-Service implementieren\n"
            "- [ ] Route bauen\n",
            encoding="utf-8",
        )

        markers = sprinttomarkers(str(sprint_path), "sprint-p5", str(handoff_path))
        assert len(markers) == 2
        assert markers[0].plan_id == "sprint-p5"
        assert markers[0].status == "todo"
        assert markers[0].prompt == ""
        assert markers[0].prompt_suggestion

        second_run = sprinttomarkers(str(sprint_path), "sprint-p5", str(handoff_path))
        assert len(second_run) == 2

        parsed = parse_markers(str(handoff_path))
        assert len(parsed) == 2
        assert parsed[0].prompt_suggestion
        assert parsed[1].prompt_suggestion

    def test_buildsuggestion_uses_sprint_context(self):
        marker = Marker(
            marker_id="sprint-p5-route-bauen",
            titel="Route bauen",
            plan_id="sprint-p5",
            status="todo",
            ziel="Route bauen",
            naechster_schritt="Sprint-Aufgabe im Detail ausarbeiten",
            prompt="",
        )
        suggestion = buildsuggestion(marker, {
            "sprint_title": "Sprint P5",
            "sprint_path": "/tmp/sprint-p5.md",
        })
        assert "Route bauen" in suggestion
        assert "Sprint P5" in suggestion
        assert "sprint-p5.md" in suggestion
