from services import copilot_marker_service
from services.copilot_marker_service import (
    Marker,
    get_marker_context,
    get_marker_execution_rating,
    list_markers_for_plan,
    parse_markers,
    read_marker_context,
    update_execution_rating,
    update_marker_fields,
    update_marker_status,
    _serialize_marker,
    _write_marker,
)


class TestCopilotMarkerServiceCore:
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
            sprint_tag="#sprint-p1",
            spec_tag="#spec-parser",
        )

        block = _serialize_marker(marker)
        assert "<!-- MARKER:001" in block
        assert "## Beispiel-Marker · todo" in block
        assert '"sprint_tag": "#sprint-p1"' in block
        assert '"spec_tag": "#spec-parser"' in block

        _write_marker(str(handoff_path), marker)
        assert parse_markers(str(handoff_path)) == [marker]

    def test_write_replaces_existing_marker_by_id(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Marker Alt",
            plan_id="sprint-p1",
            status="todo",
            ziel="Alt",
            naechster_schritt="Alt",
            prompt="",
        ))
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
        first = Marker(marker_id="001", titel="Marker Eins", plan_id="sprint-p1", status="todo", ziel="Ziel eins", naechster_schritt="Schritt eins", prompt="")
        second = Marker(marker_id="002", titel="Marker Zwei", plan_id="sprint-p1", status="blocked", ziel="Ziel zwei", naechster_schritt="Schritt zwei", prompt="Prompt zwei")
        _write_marker(str(handoff_path), first)
        _write_marker(str(handoff_path), second)

        parsed = parse_markers(str(handoff_path))
        assert parsed == [first, second]
        assert handoff_path.read_text(encoding="utf-8").count("<!-- MARKER:") == 2

    def test_list_markers_for_plan_computes_gate(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Ohne Prompt", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="", checks=["Check eins"]))
        _write_marker(str(handoff_path), Marker(marker_id="002", titel="Ohne Checks", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt gesetzt", checks=[]))
        _write_marker(str(handoff_path), Marker(marker_id="003", titel="Freigegeben", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt gesetzt", checks=["Check eins"]))

        markers = list_markers_for_plan("demo", "42")
        assert [item["marker_id"] for item in markers] == ["001", "002", "003"]
        assert markers[0]["is_activatable"] is False
        assert markers[0]["gate_reason"] == "prompt ist leer"
        assert markers[1]["is_activatable"] is False
        assert markers[1]["gate_reason"] == "keine checks definiert"
        assert markers[2]["is_activatable"] is True

    def test_update_marker_status_writes_back(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Status Marker", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt gesetzt", checks=["Check eins"]))
        updated = update_marker_status("demo", "001", "in_progress")
        assert updated is not None
        assert updated["status"] == "in_progress"
        assert parse_markers(str(handoff_path))[0].status == "in_progress"

    def test_update_marker_fields_updates_prompt_and_context(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        monkeypatch.setattr(copilot_marker_service, "PROJECTS_DIR", str(tmp_path))

        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Prompt Marker", plan_id="42", status="todo", ziel="Ziel", naechster_schritt="Schritt", prompt="", prompt_suggestion="Nutze den Vorschlag", checks=["Check eins"]))
        updated = update_marker_fields("demo", "001", {"prompt": "Nutze den Vorschlag"})
        assert updated is not None
        assert updated["prompt"] == "Nutze den Vorschlag"
        assert updated["is_activatable"] is True

        context = get_marker_context("demo", "001")
        assert context is not None
        assert context["prompt"] == "Nutze den Vorschlag"

    def test_update_execution_rating_sets_marker_fields_and_iso_timestamp(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Rating Marker", plan_id="42", status="done", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt", checks=["Check eins"]))

        result = update_execution_rating(str(handoff_path), "001", 4, "Solide Ausfuehrung")
        assert result["marker_id"] == "001"
        assert result["execution_score"] == 4
        assert result["execution_comment"] == "Solide Ausfuehrung"
        assert "T" in result["last_execution_at"]

        parsed = parse_markers(str(handoff_path))[0]
        assert parsed.execution_score == 4
        assert parsed.execution_comment == "Solide Ausfuehrung"
        assert parsed.last_execution_at == result["last_execution_at"]

    def test_update_execution_rating_updates_session_when_sessionid_given(self, tmp_path, monkeypatch):
        handoff_path = tmp_path / "handoff.md"
        writes = []
        _write_marker(str(handoff_path), Marker(marker_id="001", titel="Rating Marker", plan_id="42", status="done", ziel="Ziel", naechster_schritt="Schritt", prompt="Prompt", checks=["Check eins"]))
        monkeypatch.setattr(copilot_marker_service, "ensure_session_review_schema", lambda: None)
        monkeypatch.setattr(copilot_marker_service, "execute", lambda sql, params=None, fetch=False, fetchone=False: writes.append((sql, params)))

        result = update_execution_rating(str(handoff_path), "001", 5, "Sehr gut", sessionid="sess-1")
        assert result["execution_score"] == 5
        assert len(writes) == 1
        assert writes[0][1] == (5, "Sehr gut", "sess-1")

    def test_get_marker_execution_rating_returns_current_rating_block(self, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        _write_marker(str(handoff_path), Marker(
            marker_id="001",
            titel="Rating Marker",
            plan_id="42",
            status="done",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
            execution_score=3,
            execution_comment="Passt",
            last_execution_at="2026-04-04T12:30:00+00:00",
        ))

        assert get_marker_execution_rating(str(handoff_path), "001") == {
            "marker_id": "001",
            "execution_score": 3,
            "execution_comment": "Passt",
            "last_execution_at": "2026-04-04T12:30:00+00:00",
        }

    def test_read_marker_context_reads_project_and_plan_ids(self, tmp_path):
        context_path = tmp_path / "marker-context.md"
        context_path.write_text(
            "# Marker-Kontext\n\n- marker_id: 001\n- plan_id: 42\n- project_id: demo\n- titel: Beispiel\n",
            encoding="utf-8",
        )

        context = read_marker_context(context_path=str(context_path))
        assert context["marker_id"] == "001"
        assert context["plan_id"] == "42"
        assert context["project_id"] == "demo"
        assert context["context_path"] == str(context_path)
