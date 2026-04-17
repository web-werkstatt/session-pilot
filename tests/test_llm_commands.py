"""
Sprint D: Abnahmetests fuer LLM Command Hub.
Deckt D1-D8 ab: Command-Parsing, API, Connector-Mock, Persistenz.
"""
import json
import pytest
from unittest.mock import patch

from app import app as flask_app
from services.llm_command_service import (
    load_command,
    list_commands,
    _parse_command,
    run_command,
    get_recent_runs,
    ensure_llm_commands_schema,
)


# --- D1+D2: Command-Parsing ---

class TestCommandParsing:
    def test_load_existing_command(self):
        cmd = load_command("audit-summary")
        assert cmd is not None
        assert cmd["command_id"] == "audit-summary"
        assert cmd["title"] == "Audit-Zusammenfassung"
        assert len(cmd["parameters"]) == 1
        assert cmd["parameters"][0]["name"] == "project"
        assert cmd["parameters"][0]["required"] is True
        assert "{{project}}" in cmd["prompt_body"]

    def test_load_all_three_commands(self):
        cmds = list_commands()
        ids = [c["command_id"] for c in cmds]
        assert "audit-summary" in ids
        assert "risk-files" in ids
        assert "governance-recommendation" in ids

    def test_load_nonexistent_returns_none(self):
        cmd = load_command("nonexistent-command-xyz")
        assert cmd is None

    def test_parse_invalid_frontmatter(self):
        cmd = _parse_command("no frontmatter here")
        assert cmd is None

    def test_parse_missing_command_id(self):
        cmd = _parse_command("---\ntitle: test\n---\nbody")
        assert cmd is None

    def test_parse_valid_command(self):
        content = """---
command_id: test-cmd
title: Test Command
purpose: Testing
parameters:
  - name: foo
    type: string
    required: true
---

Hello {{foo}}!
"""
        cmd = _parse_command(content)
        assert cmd["command_id"] == "test-cmd"
        assert cmd["title"] == "Test Command"
        assert cmd["parameters"][0]["name"] == "foo"
        assert "{{foo}}" in cmd["prompt_body"]


# --- D3: API-Endpoint ---

class TestCommandRunAPI:
    @pytest.fixture
    def client(self):
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as c:
            yield c

    def test_list_commands(self, client):
        r = client.get("/api/llm/commands")
        assert r.status_code == 200
        d = r.get_json()
        assert "commands" in d
        assert len(d["commands"]) >= 3

    def test_run_missing_command_id(self, client):
        r = client.post("/api/llm/commands/run",
                        data=json.dumps({"context": {}}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_run_invalid_command_id(self, client):
        r = client.post("/api/llm/commands/run",
                        data=json.dumps({"command_id": "nonexistent", "context": {}}),
                        content_type="application/json")
        assert r.status_code == 422
        d = r.get_json()
        assert d["status"] == "failure"
        assert "nicht gefunden" in d["error_info"]

    def test_run_missing_required_param(self, client):
        r = client.post("/api/llm/commands/run",
                        data=json.dumps({"command_id": "audit-summary", "context": {}}),
                        content_type="application/json")
        assert r.status_code == 422
        d = r.get_json()
        assert d["status"] == "failure"
        assert "erforderlich" in d["error_info"]

    @patch("services.llm_command_service.query_perplexity")
    def test_run_success_mocked(self, mock_llm, client):
        mock_llm.return_value = {
            "content": "Das Projekt steht auf ROT.",
            "model": "sonar-test",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        r = client.post("/api/llm/commands/run",
                        data=json.dumps({
                            "command_id": "audit-summary",
                            "context": {"project": "project_dashboard"},
                        }),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "success"
        assert d["output_text"] == "Das Projekt steht auf ROT."
        assert d["model"] == "sonar-test"
        assert isinstance(d["run_id"], int)
        assert d["duration_ms"] is not None

    def test_recent_runs(self, client):
        r = client.get("/api/llm/commands/runs")
        assert r.status_code == 200
        d = r.get_json()
        assert "runs" in d
        assert isinstance(d["runs"], list)


# --- D5: Persistenz ---

class TestPersistence:
    @patch("services.llm_command_service.query_perplexity")
    def test_run_is_persisted(self, mock_llm):
        mock_llm.return_value = {
            "content": "Test output",
            "model": "sonar-mock",
            "usage": {},
        }
        result = run_command("audit-summary", {"project": "test_persist"})
        assert result["status"] == "success"
        run_id = result["run_id"]

        # Verify in recent runs
        runs = get_recent_runs(100)
        found = [r for r in runs if r["run_id"] == run_id]
        assert len(found) == 1
        assert found[0]["command_id"] == "audit-summary"
        assert found[0]["output_text"] == "Test output"
        assert found[0]["status"] == "success"

    def test_failure_is_persisted(self):
        result = run_command("nonexistent", {})
        assert result["status"] == "failure"
        run_id = result["run_id"]

        runs = get_recent_runs(100)
        found = [r for r in runs if r["run_id"] == run_id]
        assert len(found) == 1
        assert found[0]["status"] == "failure"


# --- D7: UI ---

class TestUI:
    @pytest.fixture
    def client(self):
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_page_renders(self, client):
        r = client.get("/llm-commands")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "cmdSelect" in html
        assert "btnRunCmd" in html
        assert "llm-commands.js" in html
        assert "marked.min.js" in html
