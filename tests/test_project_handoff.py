"""
Tests fuer project_handoff_service: Projekt-weite handoff.md.
"""
import os
import uuid
import pytest

from app import app as flask_app
from services.db_service import execute, ensure_plans_schema
from services.project_handoff_service import (
    get_handoff_path,
    build_handoff_markdown,
    write_handoff,
)


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def test_plan():
    """Plan fuer project_dashboard (existierendes Projektverzeichnis)."""
    ensure_plans_schema()
    unique = str(uuid.uuid4())[:8]
    row = execute(
        """INSERT INTO project_plans (filename, title, project_name, status, category)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (f"test-ho-{unique}.md", "Handoff Test Plan", "project_dashboard", "active", "feature"),
        fetchone=True,
    )
    plan_id = row["id"]
    yield plan_id
    # Cleanup: Test-Plan entfernen
    execute("DELETE FROM project_plans WHERE id = %s", (plan_id,))


class TestGetHandoffPath:
    def test_returns_project_level_path(self):
        path = get_handoff_path("project_dashboard")
        assert path.endswith("/project_dashboard/handoff.md")

    def test_different_project(self):
        path = get_handoff_path("some_other_project")
        assert path.endswith("/some_other_project/handoff.md")


class TestBuildHandoffMarkdown:
    def test_builds_markdown_for_project_with_plans(self, test_plan):
        md = build_handoff_markdown("project_dashboard")
        assert md is not None
        assert "project_dashboard" in md
        assert "Handoff Test Plan" in md
        assert "handoff:" in md
        assert "## Aktueller Stand (IST)" in md

    def test_returns_none_for_project_without_plans(self):
        md = build_handoff_markdown("nonexistent_project_xyz_999")
        assert md is None


class TestWriteHandoff:
    def test_writes_single_file(self, test_plan):
        filepath, md = write_handoff("project_dashboard")
        assert filepath is not None
        assert filepath.endswith("/project_dashboard/handoff.md")
        assert os.path.isfile(filepath)
        assert "project_dashboard" in md

    def test_nonexistent_project_dir(self):
        filepath, md = write_handoff("nonexistent_project_xyz_999")
        assert filepath is None
        assert md is None

    def test_overwrites_on_second_call(self, test_plan):
        filepath1, md1 = write_handoff("project_dashboard")
        filepath2, md2 = write_handoff("project_dashboard")
        assert filepath1 == filepath2
        # Inhalt sollte gleich sein (gleiche DB-Daten)
        assert md1 == md2


class TestAPIUsesHandoffService:
    def test_handoff_api_endpoint(self, client, test_plan):
        """API-Endpoint /api/plans/<id>/handoff nutzt write_handoff."""
        r = client.get(f"/api/plans/{test_plan}/handoff")
        assert r.status_code == 200
        assert r.content_type.startswith("text/markdown")
        data = r.data.decode("utf-8")
        assert "project_dashboard" in data

    def test_handoff_api_nonexistent_plan(self, client):
        r = client.get("/api/plans/999999/handoff")
        assert r.status_code == 404
