"""
Tests fuer project_handoff_service: Projekt-weite handoff.md.
"""
import os
import pytest
from unittest.mock import patch

from app import app as flask_app
from services.copilot_marker_service import parse_markers
from services.project_handoff_service import (
    get_handoff_path,
    build_handoff_markdown,
    build_empty_handoff_markdown,
    write_handoff,
)


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def mock_plan_rows():
    return [
        {
            "id": 145,
            "title": "[TEST] Handoff Plan",
            "status": "active",
            "category": "feature",
            "plan_type": "plan",
            "workflow_stage": "idea",
            "current_state": "Ist-Zustand vorhanden",
            "target_state": "Soll-Zustand definiert",
            "next_action": "Naechsten Schritt umsetzen",
            "latest_executor_status": "pending",
            "latest_review_status": "pending",
            "latest_quality_score": None,
            "latest_audit_status": None,
            "governance_status": None,
            "updated_at": None,
        }
    ]


class TestGetHandoffPath:
    def test_returns_project_level_path(self):
        path = get_handoff_path("project_dashboard")
        assert path.endswith("/project_dashboard/handoff.md")

    def test_different_project(self):
        path = get_handoff_path("some_other_project")
        assert path.endswith("/some_other_project/handoff.md")


class TestBuildHandoffMarkdown:
    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    def test_builds_markdown_for_project_with_plans(self, mock_execute, _mock_schema, mock_plan_rows):
        mock_execute.return_value = mock_plan_rows
        md = build_handoff_markdown("project_dashboard")
        assert md is not None
        assert "project_dashboard" in md
        assert "[TEST] Handoff Plan" in md
        assert "handoff:" in md
        assert "## Copilot Markers" in md
        assert "<!-- MARKER:" in md

    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    @patch("services.project_handoff_service.get_handoff_path")
    def test_generated_markers_are_parseable(self, mock_path, mock_execute, _mock_schema, mock_plan_rows, tmp_path):
        mock_path.return_value = str(tmp_path / "source-handoff.md")
        mock_execute.return_value = mock_plan_rows
        md = build_handoff_markdown("project_dashboard")
        handoff_path = tmp_path / "handoff.md"
        handoff_path.write_text(md, encoding="utf-8")
        markers = parse_markers(str(handoff_path))
        assert len(markers) >= 1
        marker = next(m for m in markers if m.titel == "[TEST] Handoff Plan")
        assert marker.plan_id == "145"
        assert marker.status == "in_progress"
        assert marker.prompt == ""

    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    def test_returns_none_for_project_without_plans(self, mock_execute, _mock_schema):
        mock_execute.return_value = []
        md = build_handoff_markdown("nonexistent_project_xyz_999")
        assert md is None

    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    @patch("services.project_handoff_service.get_handoff_path")
    def test_preserves_last_session_from_existing_handoff(self, mock_path, mock_execute, _mock_schema, mock_plan_rows, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        handoff_path.write_text(
            "<!-- MARKER:145\n"
            "{\n"
            '  "marker_id": "145",\n'
            '  "titel": "[TEST] Handoff Plan",\n'
            '  "plan_id": "145",\n'
            '  "status": "done",\n'
            '  "ziel": "Soll-Zustand definiert",\n'
            '  "naechster_schritt": "Naechsten Schritt umsetzen",\n'
            '  "prompt": "",\n'
            '  "prompt_suggestion": "",\n'
            '  "risiko": "",\n'
            '  "checks": ["Check"],\n'
            '  "last_session": "sess_keep",\n'
            '  "updated_at": "2026-04-05T10:00:00+00:00",\n'
            '  "execution_score": null,\n'
            '  "execution_comment": "",\n'
            '  "last_execution_at": "",\n'
            '  "sprint_tag": "",\n'
            '  "spec_tag": "",\n'
            '  "sprint_plan_id": null,\n'
            '  "spec_id": null\n'
            "}\n"
            "-->\n\n"
            "## [TEST] Handoff Plan · done\n\n"
            "**Ziel:** Soll-Zustand definiert\n"
            "**Naechster Schritt:** Naechsten Schritt umsetzen\n"
            "**Risiko:** -\n"
            "**Execution Score:** -\n"
            "**Execution Comment:** -\n"
            "**Last Execution:** -\n"
            "**Sprint Tag:** -\n"
            "**Spec Tag:** -\n\n"
            "**Prompt:**\n_(noch nicht gesetzt)_\n\n"
            "**Checks:**\n- Check\n\n---\n",
            encoding="utf-8",
        )
        mock_path.return_value = str(handoff_path)
        mock_execute.return_value = mock_plan_rows

        md = build_handoff_markdown("project_dashboard")

        assert '"last_session": "sess_keep"' in md

    def test_builds_empty_marker_handoff(self):
        md = build_empty_handoff_markdown("empty_project")
        assert 'project_id: "empty_project"' in md
        assert 'state_format: "copilot_markers_v1"' in md
        assert "## Copilot Markers" in md
        assert "noch keine Marker vorhanden" in md


class TestWriteHandoff:
    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    @patch("services.project_handoff_service.get_handoff_path")
    def test_writes_single_file(self, mock_path, mock_execute, _mock_schema, mock_plan_rows, tmp_path):
        mock_path.return_value = str(tmp_path / "handoff.md")
        mock_execute.return_value = mock_plan_rows
        filepath, md = write_handoff("project_dashboard")
        assert filepath is not None
        assert filepath.endswith("handoff.md")
        assert os.path.isfile(filepath)
        assert "project_dashboard" in md
        markers = parse_markers(filepath)
        assert any(m.plan_id == "145" for m in markers)

    def test_nonexistent_project_dir(self):
        filepath, md = write_handoff("nonexistent_project_xyz_999")
        assert filepath is None
        assert md is None

    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    @patch("services.project_handoff_service.get_handoff_path")
    @patch("services.project_handoff_service.resolve_project_path")
    def test_writes_empty_handoff_for_existing_project_without_plans(
        self,
        mock_resolve_project_path,
        mock_path,
        mock_execute,
        _mock_schema,
        tmp_path,
    ):
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        mock_resolve_project_path.return_value = str(project_dir)
        mock_path.return_value = str(handoff_path)
        mock_execute.return_value = []

        filepath, md = write_handoff("empty_project")

        assert filepath == str(handoff_path)
        assert os.path.isfile(filepath)
        assert 'state_format: "copilot_markers_v1"' in md
        assert "noch keine Marker vorhanden" in md
        assert parse_markers(filepath) == []

    @patch("services.project_handoff_service.ensure_plans_schema")
    @patch("services.project_handoff_service.execute")
    @patch("services.project_handoff_service.get_handoff_path")
    def test_overwrites_on_second_call(self, mock_path, mock_execute, _mock_schema, mock_plan_rows, tmp_path):
        mock_path.return_value = str(tmp_path / "handoff.md")
        mock_execute.return_value = mock_plan_rows
        filepath1, md1 = write_handoff("project_dashboard")
        filepath2, md2 = write_handoff("project_dashboard")
        assert filepath1 == filepath2
        # Inhalt sollte gleich sein (gleiche DB-Daten)
        assert md1 == md2


class TestAPIUsesHandoffService:
    @patch("routes.plans_routes.write_handoff")
    @patch("routes.plans_routes.execute")
    def test_handoff_api_endpoint(self, mock_execute, mock_write_handoff, client):
        """API-Endpoint /api/plans/<id>/handoff nutzt write_handoff."""
        mock_execute.return_value = {"project_name": "project_dashboard"}
        mock_write_handoff.return_value = ("/mnt/projects/project_dashboard/handoff.md", "---\n# Handoff fuer Projekt project_dashboard\n")
        r = client.get("/api/plans/145/handoff")
        assert r.status_code == 200
        assert r.content_type.startswith("text/markdown")
        data = r.data.decode("utf-8")
        assert "project_dashboard" in data

    @patch("routes.plans_routes.execute")
    def test_handoff_api_nonexistent_plan(self, mock_execute, client):
        mock_execute.return_value = None
        r = client.get("/api/plans/999999/handoff")
        assert r.status_code == 404
