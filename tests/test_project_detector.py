"""
Unit-Tests fuer services/project_detector.py

Testet Projekt-Typ-Erkennung, Tag-Detection, Subprojekt-Erkennung
und Validierung. Nutzt tmp_path fuer Filesystem-Tests.
"""
import os
import json
import pytest


# ---------------------------------------------------------------------------
# detect_tags
# ---------------------------------------------------------------------------

class TestDetectTags:

    def test_python_project(self, tmp_path):
        from services.project_detector import detect_tags
        (tmp_path / "requirements.txt").write_text("flask\n")
        tags = detect_tags(str(tmp_path))
        assert "python" in tags

    def test_nodejs_project(self, tmp_path):
        from services.project_detector import detect_tags
        (tmp_path / "package.json").write_text('{"name": "test"}')
        tags = detect_tags(str(tmp_path))
        assert "nodejs" in tags

    def test_docker_project(self, tmp_path):
        from services.project_detector import detect_tags
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        tags = detect_tags(str(tmp_path))
        assert "docker" in tags

    def test_react_detected_from_deps(self, tmp_path):
        from services.project_detector import detect_tags
        pkg = {"name": "test", "dependencies": {"react": "^18.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        tags = detect_tags(str(tmp_path))
        assert "nodejs" in tags
        assert "react" in tags

    def test_empty_project_no_tags(self, tmp_path):
        from services.project_detector import detect_tags
        tags = detect_tags(str(tmp_path))
        assert tags == []


# ---------------------------------------------------------------------------
# detect_project_type
# ---------------------------------------------------------------------------

class TestDetectProjectType:

    def test_tool_prefix(self, tmp_path):
        from services.project_detector import detect_project_type
        result = detect_project_type(str(tmp_path), "tool_myutil")
        assert result == "tool"

    def test_documentation_project(self, tmp_path):
        from services.project_detector import detect_project_type
        # >50% markdown files, no source code
        (tmp_path / "README.md").write_text("# Docs\n")
        (tmp_path / "guide.md").write_text("# Guide\n")
        (tmp_path / "reference.md").write_text("# Ref\n")
        result = detect_project_type(str(tmp_path), "my-docs")
        assert result == "documentation"

    def test_monorepo_with_apps_dir(self, tmp_path):
        from services.project_detector import detect_project_type
        apps_dir = tmp_path / "apps"
        apps_dir.mkdir()
        (apps_dir / "frontend").mkdir()
        (apps_dir / "backend").mkdir()
        # Need some marker files for valid subprojects
        (apps_dir / "frontend" / "package.json").write_text("{}")
        (apps_dir / "backend" / "requirements.txt").write_text("")
        result = detect_project_type(str(tmp_path), "my-monorepo")
        assert result == "monorepo"

    def test_default_is_project(self, tmp_path):
        from services.project_detector import detect_project_type
        (tmp_path / "main.py").write_text("print('hello')\n")
        result = detect_project_type(str(tmp_path), "simple-app")
        assert result == "project"


# ---------------------------------------------------------------------------
# is_valid_project
# ---------------------------------------------------------------------------

class TestIsValidProject:

    def test_git_repo_is_valid(self, tmp_path):
        from services.project_detector import is_valid_project
        (tmp_path / ".git").mkdir()
        # Also need at least one visible file for the check
        (tmp_path / "README.md").write_text("# Test\n")
        assert is_valid_project(str(tmp_path), "test") is True

    def test_has_config_file(self, tmp_path):
        from services.project_detector import is_valid_project
        (tmp_path / "package.json").write_text("{}")
        assert is_valid_project(str(tmp_path), "test") is True

    def test_has_readme(self, tmp_path):
        from services.project_detector import is_valid_project
        (tmp_path / "README.md").write_text("# Test\n")
        assert is_valid_project(str(tmp_path), "test") is True

    def test_empty_dir_invalid(self, tmp_path):
        from services.project_detector import is_valid_project
        assert is_valid_project(str(tmp_path), "test") is False


# ---------------------------------------------------------------------------
# is_valid_subproject
# ---------------------------------------------------------------------------

class TestIsValidSubproject:

    def test_with_config_file(self, tmp_path):
        from services.project_detector import is_valid_subproject
        (tmp_path / "package.json").write_text("{}")
        assert is_valid_subproject(str(tmp_path)) is True

    def test_with_entry_point(self, tmp_path):
        from services.project_detector import is_valid_subproject
        (tmp_path / "main.py").write_text("print('hi')\n")
        assert is_valid_subproject(str(tmp_path)) is True

    def test_empty_dir_invalid(self, tmp_path):
        from services.project_detector import is_valid_subproject
        assert is_valid_subproject(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# needs_schema_update
# ---------------------------------------------------------------------------

class TestSchemaUpdate:

    def test_old_version_needs_update(self):
        from services.project_detector import needs_schema_update, SCHEMA_VERSION
        assert needs_schema_update({"schema_version": 1}) is True

    def test_current_version_ok(self):
        from services.project_detector import needs_schema_update, SCHEMA_VERSION
        assert needs_schema_update({"schema_version": SCHEMA_VERSION}) is False

    def test_missing_version_needs_update(self):
        from services.project_detector import needs_schema_update
        assert needs_schema_update({}) is True
