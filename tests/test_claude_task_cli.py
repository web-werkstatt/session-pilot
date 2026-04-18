"""
Sprint sprint-agent-orchestrator-executor-handoff Commit 2 (2026-04-18):
Tests fuer scripts/claude_task.py.

Alle vier Subcommands (pull, finish, verify, close) werden mit gemocktem
urllib.request.urlopen und — fuer finish — einem temporaeren Git-Repo getestet.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import claude_task  # noqa: E402


# ---------------------------------------------------------------------------
# Test-Helpers
# ---------------------------------------------------------------------------

class _FakeResp:
    """Minimaler urllib-Response-Ersatz mit Context-Manager-Support."""

    def __init__(self, status: int, body, content_type: str = "application/json"):
        self.status = status
        if isinstance(body, str):
            self._body = body.encode("utf-8")
            self._ct = content_type
        else:
            self._body = json.dumps(body).encode("utf-8")
            self._ct = content_type
        self.headers = {"Content-Type": self._ct}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def _http_error(code: int, body_dict) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="http://x/",
        code=code,
        msg="err",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(json.dumps(body_dict).encode()),
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_load_config_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_TASK_URL", "http://env-host:9000")
    monkeypatch.setenv("AGENT_TASK_TOKEN", "env-token")
    monkeypatch.setattr(claude_task, "TOML_PATH", tmp_path / "no.toml")
    monkeypatch.setattr(claude_task, "TOKEN_FILE_PATH", tmp_path / "no-tok")
    url, token = claude_task.load_config()
    assert url == "http://env-host:9000"
    assert token == "env-token"


def test_load_config_toml(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_TASK_URL", raising=False)
    monkeypatch.delenv("AGENT_TASK_TOKEN", raising=False)
    toml = tmp_path / ".agent-task.toml"
    toml.write_text('[agent_task]\nurl = "http://toml:8000"\ntoken = "toml-tok"\n')
    monkeypatch.setattr(claude_task, "TOML_PATH", toml)
    monkeypatch.setattr(claude_task, "TOKEN_FILE_PATH", tmp_path / "no-tok")
    url, token = claude_task.load_config()
    assert url == "http://toml:8000"
    assert token == "toml-tok"


def test_load_config_token_file(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_TASK_URL", raising=False)
    monkeypatch.delenv("AGENT_TASK_TOKEN", raising=False)
    monkeypatch.setattr(claude_task, "TOML_PATH", tmp_path / "no.toml")
    tf = tmp_path / ".agent-task-token"
    tf.write_text("file-token\n")
    monkeypatch.setattr(claude_task, "TOKEN_FILE_PATH", tf)
    _, token = claude_task.load_config()
    assert token == "file-token"


def test_load_config_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_TASK_URL", raising=False)
    monkeypatch.delenv("AGENT_TASK_TOKEN", raising=False)
    monkeypatch.setattr(claude_task, "TOML_PATH", tmp_path / "no.toml")
    monkeypatch.setattr(claude_task, "TOKEN_FILE_PATH", tmp_path / "no-tok")
    url, token = claude_task.load_config()
    assert url == claude_task.DEFAULT_URL
    assert token == ""


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------

def test_pull_writes_prompt_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prompt_resp = _FakeResp(200, "# Agent-Task 42: Test\n", "text/markdown")
    contract = {"task_id": 42, "allowed_files": ["services/foo.py"]}
    contract_resp = _FakeResp(200, contract)

    with patch("urllib.request.urlopen", side_effect=[prompt_resp, contract_resp]):
        claude_task.cmd_pull(42, "http://localhost:5055", "tok")

    assert (tmp_path / ".agent-task-42.md").read_text() == "# Agent-Task 42: Test\n"


def test_pull_shows_allowed_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    prompt_resp = _FakeResp(200, "# ...\n", "text/markdown")
    contract = {"task_id": 3, "allowed_files": ["services/x.py", "routes/y.py"]}
    contract_resp = _FakeResp(200, contract)

    with patch("urllib.request.urlopen", side_effect=[prompt_resp, contract_resp]):
        claude_task.cmd_pull(3, "http://localhost:5055", "tok")

    out = capsys.readouterr().out
    assert "services/x.py" in out
    assert "routes/y.py" in out


def test_pull_401_exits():
    with patch("urllib.request.urlopen", side_effect=_http_error(401, {"error": "bad token"})):
        with pytest.raises(SystemExit):
            claude_task.cmd_pull(1, "http://localhost:5055", "bad")


def test_pull_404_exits():
    with patch("urllib.request.urlopen", side_effect=_http_error(404, {"error": "not found"})):
        with pytest.raises(SystemExit):
            claude_task.cmd_pull(99, "http://localhost:5055", "tok")


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------

def _make_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True)


def test_finish_posts_execution_payload(tmp_path):
    _make_git_repo(tmp_path)
    (tmp_path / "allowed.py").write_text("x=1")
    (tmp_path / "outside.py").write_text("y=2")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add files"], cwd=tmp_path, capture_output=True)
    (tmp_path / "allowed.py").write_text("x=2")
    (tmp_path / "outside.py").write_text("y=3")

    contract = {"task_id": 7, "allowed_files": ["allowed.py"]}
    contract_resp = _FakeResp(200, contract)
    exec_resp = _FakeResp(201, {"execution_id": 1})

    captured: dict = {}

    def fake_urlopen(req, **_):
        if "execution" in req.get_full_url():
            captured.update(json.loads(req.data.decode()))
            return exec_resp
        return contract_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        claude_task.cmd_finish(7, "http://localhost:5055", "tok", repo_path=str(tmp_path))

    assert "allowed.py" in captured["changed_files"]
    assert "outside.py" in captured["changed_files"]
    assert captured["out_of_scope_files"] == ["outside.py"]
    assert captured["agent"] == "claude-cli"
    assert "diff_stat_text" in captured
    assert isinstance(captured["diff_stat_text"], str)
    assert "files_changed_json" not in captured
    assert "out_of_scope_files_json" not in captured
    assert "notes_text" not in captured


def test_finish_with_notes_file(tmp_path):
    _make_git_repo(tmp_path)
    notes = tmp_path / "notes.txt"
    notes.write_text("Meine Notizen\n")

    contract = {"task_id": 5, "allowed_files": []}
    contract_resp = _FakeResp(200, contract)
    exec_resp = _FakeResp(201, {"execution_id": 2})

    captured: dict = {}

    def fake_urlopen(req, **_):
        if "execution" in req.get_full_url():
            captured.update(json.loads(req.data.decode()))
            return exec_resp
        return contract_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        claude_task.cmd_finish(
            5, "http://localhost:5055", "tok",
            notes_file=str(notes), repo_path=str(tmp_path),
        )

    assert captured.get("summary") == "Meine Notizen"
    assert captured.get("agent") == "claude-cli"
    assert "notes_text" not in captured


def test_finish_forwards_started_and_finished(tmp_path):
    _make_git_repo(tmp_path)

    contract = {"task_id": 9, "allowed_files": []}
    contract_resp = _FakeResp(200, contract)
    exec_resp = _FakeResp(201, {"execution_id": 3})

    captured: dict = {}

    def fake_urlopen(req, **_):
        if "execution" in req.get_full_url():
            captured.update(json.loads(req.data.decode()))
            return exec_resp
        return contract_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        claude_task.cmd_finish(
            9, "http://localhost:5055", "tok",
            repo_path=str(tmp_path),
            started_at="2026-04-18T10:00:00Z",
            finished_at="2026-04-18T10:05:00Z",
        )

    assert captured["started_at"] == "2026-04-18T10:00:00Z"
    assert captured["finished_at"] == "2026-04-18T10:05:00Z"


def test_finish_omits_timestamps_by_default(tmp_path):
    _make_git_repo(tmp_path)

    contract = {"task_id": 10, "allowed_files": []}
    contract_resp = _FakeResp(200, contract)
    exec_resp = _FakeResp(201, {"execution_id": 4})

    captured: dict = {}

    def fake_urlopen(req, **_):
        if "execution" in req.get_full_url():
            captured.update(json.loads(req.data.decode()))
            return exec_resp
        return contract_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        claude_task.cmd_finish(10, "http://localhost:5055", "tok", repo_path=str(tmp_path))

    assert "started_at" not in captured
    assert "finished_at" not in captured


def test_finish_404_exits(tmp_path):
    _make_git_repo(tmp_path)
    with patch("urllib.request.urlopen", side_effect=_http_error(404, {"error": "not found"})):
        with pytest.raises(SystemExit):
            claude_task.cmd_finish(99, "http://localhost:5055", "tok", repo_path=str(tmp_path))


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def test_verify_pass(capsys):
    resp = _FakeResp(201, {"decision": {"passed": True, "failed_claims": []}, "verify_id": 1})
    with patch("urllib.request.urlopen", return_value=resp):
        claude_task.cmd_verify(3, "http://localhost:5055", "tok")
    assert "PASS" in capsys.readouterr().out


def test_verify_fail_shows_claims(capsys):
    resp = _FakeResp(201, {"decision": {"passed": False, "failed_claims": ["tests_passed"]}, "verify_id": 2})
    with patch("urllib.request.urlopen", return_value=resp):
        claude_task.cmd_verify(3, "http://localhost:5055", "tok")
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "tests_passed" in out


def test_verify_404_exits():
    with patch("urllib.request.urlopen", side_effect=_http_error(404, {"error": "no execution"})):
        with pytest.raises(SystemExit):
            claude_task.cmd_verify(99, "http://localhost:5055", "tok")


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

def test_close_success(capsys):
    resp = _FakeResp(200, {"decision": {"can_close": True}, "task": {"status": "closed"}})
    with patch("urllib.request.urlopen", return_value=resp):
        claude_task.cmd_close(4, "http://localhost:5055", "tok")
    assert "geschlossen" in capsys.readouterr().out


def test_close_rejected_exits():
    with patch("urllib.request.urlopen", side_effect=_http_error(409, {"decision": {"can_close": False, "reason": "no verify"}})):
        with pytest.raises(SystemExit):
            claude_task.cmd_close(4, "http://localhost:5055", "tok")


def test_close_with_session_id():
    resp = _FakeResp(200, {"decision": {"can_close": True}})
    captured: dict = {}

    def fake_urlopen(req, **_):
        captured["body"] = json.loads(req.data.decode()) if req.data else {}
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        claude_task.cmd_close(4, "http://localhost:5055", "tok", session_id="sess-abc")

    assert captured["body"].get("session_id") == "sess-abc"


# ---------------------------------------------------------------------------
# _compute_out_of_scope (Unit-Tests)
# ---------------------------------------------------------------------------

def test_out_of_scope_empty_allowed():
    assert claude_task._compute_out_of_scope(["a.py", "b.py"], []) == []


def test_out_of_scope_all_allowed():
    assert claude_task._compute_out_of_scope(["a.py"], ["a.py", "b.py"]) == []


def test_out_of_scope_partial():
    assert claude_task._compute_out_of_scope(["a.py", "x.py"], ["a.py"]) == ["x.py"]


# ---------------------------------------------------------------------------
# main() — Token-Fehler ohne Config
# ---------------------------------------------------------------------------

def test_main_exits_without_token(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_TASK_URL", raising=False)
    monkeypatch.delenv("AGENT_TASK_TOKEN", raising=False)
    monkeypatch.setattr(claude_task, "TOML_PATH", tmp_path / "no.toml")
    monkeypatch.setattr(claude_task, "TOKEN_FILE_PATH", tmp_path / "no-tok")
    with pytest.raises(SystemExit):
        claude_task.main(["pull", "1"])
