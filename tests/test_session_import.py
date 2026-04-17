"""
Unit-Tests fuer services/session_import.py

Testet Projektname-Extraktion, Content-Parsing, Tool-Erkennung
und JSONL-Parsing. DB-Zugriffe werden gemockt.
"""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# extract_project_name
# ---------------------------------------------------------------------------

class TestExtractProjectName:

    def test_mnt_projects_prefix(self):
        from services.session_import import extract_project_name
        with patch("services.session_import._resolve_dir_name", return_value="my_project"):
            result = extract_project_name("-mnt-projects-my_project")
        assert result == "my_project"

    def test_gemini_prefix_returns_gemini_sessions(self):
        from services.session_import import extract_project_name
        result = extract_project_name("gemini:/some/path/my-project")
        assert result == "gemini_sessions"

    def test_codex_prefix_strips_prefix(self):
        from services.session_import import extract_project_name
        result = extract_project_name("codex:/some/path/my-project")
        assert "codex:" not in result

    def test_opencode_prefix_strips_prefix(self):
        from services.session_import import extract_project_name
        result = extract_project_name("opencode:project_dashboard")
        assert "opencode:" not in result

    def test_kilo_prefix_strips_prefix(self):
        from services.session_import import extract_project_name
        result = extract_project_name("kilo:project_dashboard")
        assert "kilo:" not in result

    def test_raw_hash_fallback(self):
        from services.session_import import extract_project_name
        result = extract_project_name("random-hash-value")
        assert result == "random-hash-value"


# ---------------------------------------------------------------------------
# extract_text_content
# ---------------------------------------------------------------------------

class TestExtractTextContent:

    def test_string_passthrough(self):
        from services.session_import import extract_text_content
        assert extract_text_content("Hello world") == "Hello world"

    def test_list_with_text_block(self):
        from services.session_import import extract_text_content
        content = [{"type": "text", "text": "Hello"}, {"type": "text", "text": " world"}]
        result = extract_text_content(content)
        assert "Hello" in result
        assert "world" in result

    def test_list_with_tool_result(self):
        from services.session_import import extract_text_content
        content = [
            {"type": "tool_result", "content": [{"type": "text", "text": "result data"}]},
        ]
        result = extract_text_content(content)
        assert "result data" in result

    def test_empty_list(self):
        from services.session_import import extract_text_content
        result = extract_text_content([])
        assert result == ""

    def test_none_content(self):
        from services.session_import import extract_text_content
        result = extract_text_content(None)
        assert result == "None" or result == ""


# ---------------------------------------------------------------------------
# has_tool_use
# ---------------------------------------------------------------------------

class TestHasToolUse:

    def test_with_tool_use(self):
        from services.session_import import has_tool_use
        content = [{"type": "text"}, {"type": "tool_use", "name": "Bash"}]
        assert has_tool_use(content) is True

    def test_without_tool_use(self):
        from services.session_import import has_tool_use
        content = [{"type": "text", "text": "Hello"}]
        assert has_tool_use(content) is False

    def test_string_content(self):
        from services.session_import import has_tool_use
        assert has_tool_use("just text") is False

    def test_empty_list(self):
        from services.session_import import has_tool_use
        assert has_tool_use([]) is False


# ---------------------------------------------------------------------------
# parse_jsonl
# ---------------------------------------------------------------------------

class TestParseJsonl:

    def _write_jsonl(self, tmp_path, lines):
        fpath = tmp_path / "test.jsonl"
        with open(fpath, "w") as f:
            for line in lines:
                f.write(json.dumps(line) + "\n")
        return str(fpath)

    def test_basic_session_parsing(self, tmp_path):
        from services.session_import import parse_jsonl
        lines = [
            {
                "type": "user",
                "sessionId": "sess-123",
                "timestamp": "2026-04-01T10:00:00Z",
                "cwd": "/mnt/projects/test",
                "message": {"content": "Hello"},
            },
            {
                "type": "assistant",
                "sessionId": "sess-123",
                "timestamp": "2026-04-01T10:01:00Z",
                "message": {
                    "content": "Hi there",
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
        ]
        fpath = self._write_jsonl(tmp_path, lines)
        meta, messages = parse_jsonl(fpath)
        assert meta is not None
        assert meta["session_uuid"] == "sess-123"
        assert meta["user_message_count"] >= 1
        assert len(messages) >= 1

    def test_empty_file_returns_none(self, tmp_path):
        from services.session_import import parse_jsonl
        fpath = self._write_jsonl(tmp_path, [])
        meta, messages = parse_jsonl(fpath)
        # Empty file should return meta with no uuid
        assert meta is None or meta.get("session_uuid") is None

    def test_skips_invalid_json_lines(self, tmp_path):
        from services.session_import import parse_jsonl
        fpath = tmp_path / "test.jsonl"
        with open(fpath, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({
                "type": "user",
                "sessionId": "sess-456",
                "timestamp": "2026-04-01T10:00:00Z",
                "message": {"content": "Hello"},
            }) + "\n")
        meta, messages = parse_jsonl(str(fpath))
        assert meta is not None
        assert meta["session_uuid"] == "sess-456"


# ---------------------------------------------------------------------------
# _file_hash
# ---------------------------------------------------------------------------

class TestFileHash:

    def test_same_content_same_hash(self, tmp_path):
        from services.session_import import _file_hash
        f1 = tmp_path / "a.jsonl"
        f2 = tmp_path / "b.jsonl"
        content = "line1\nline2\n" * 100
        f1.write_text(content)
        f2.write_text(content)
        assert _file_hash(str(f1)) == _file_hash(str(f2))

    def test_different_content_different_hash(self, tmp_path):
        from services.session_import import _file_hash
        f1 = tmp_path / "a.jsonl"
        f2 = tmp_path / "b.jsonl"
        f1.write_text("content A\n" * 100)
        f2.write_text("content B\n" * 100)
        assert _file_hash(str(f1)) != _file_hash(str(f2))

    def test_nonexistent_file_returns_none(self):
        from services.session_import import _file_hash
        assert _file_hash("/nonexistent/path.jsonl") is None

    def test_large_file_uses_head_tail(self, tmp_path):
        from services.session_import import _file_hash
        f = tmp_path / "large.jsonl"
        # Create file >16KB to trigger head+tail hashing
        f.write_text("x" * 20000)
        result = _file_hash(str(f))
        assert result is not None


# ---------------------------------------------------------------------------
# sync_account cache guard
# ---------------------------------------------------------------------------

class TestSyncAccountCacheGuard:

    def test_cached_file_is_reimported_when_db_row_is_missing(self, tmp_path, monkeypatch):
        from services import session_import as mod

        fpath = tmp_path / "codex-session.jsonl"
        fpath.write_text('{"type":"session_meta","payload":{"id":"sess-1"}}\n')

        monkeypatch.setattr(mod, "_file_hash", lambda path: "hash-1")
        monkeypatch.setattr(mod, "_db_has_session_for_path", lambda path: False)
        monkeypatch.setattr(mod, "find_sessions_codex", lambda config_dir: [(str(fpath), None)])

        calls = []

        def fake_import(path, account_name):
            calls.append((path, account_name))
            return "imported"

        monkeypatch.setattr(mod, "import_codex_session", fake_import)

        account = {"name": "codex", "tool": "codex", "config_dir": "/tmp/codex"}
        stats = mod.sync_account(account, hash_cache={f"codex:v1:{fpath}": "hash-1"})

        assert stats["imported"] == 1
        assert stats["unchanged"] == 0
        assert calls == [(str(fpath), "codex")]

    def test_cached_file_stays_unchanged_when_db_row_exists(self, tmp_path, monkeypatch):
        from services import session_import as mod

        fpath = tmp_path / "codex-session.jsonl"
        fpath.write_text('{"type":"session_meta","payload":{"id":"sess-1"}}\n')

        monkeypatch.setattr(mod, "_file_hash", lambda path: "hash-1")
        monkeypatch.setattr(mod, "_db_has_session_for_path", lambda path: True)
        monkeypatch.setattr(mod, "find_sessions_codex", lambda config_dir: [(str(fpath), None)])

        def fail_import(path, account_name):
            raise AssertionError("import should not run for cached DB-backed session")

        monkeypatch.setattr(mod, "import_codex_session", fail_import)

        account = {"name": "codex", "tool": "codex", "config_dir": "/tmp/codex"}
        stats = mod.sync_account(account, hash_cache={f"codex:v1:{fpath}": "hash-1"})

        assert stats["imported"] == 0
        assert stats["unchanged"] == 1


# ---------------------------------------------------------------------------
# codex importer
# ---------------------------------------------------------------------------

class TestCodexImporter:

    def test_parse_codex_jsonl_reads_current_message_format(self, tmp_path):
        from services.importers.codex_importer import parse_codex_jsonl

        fpath = tmp_path / "codex.jsonl"
        lines = [
            {
                "timestamp": "2026-04-17T05:48:36.779Z",
                "type": "session_meta",
                "payload": {
                    "id": "019d99fa-e6f3-70a1-8035-f9c947483a8e",
                    "cwd": "/mnt/projects/project_dashboard",
                    "cli_version": "0.121.0",
                    "git": {"branch": "main"},
                },
            },
            {
                "timestamp": "2026-04-17T05:48:40.000Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Bitte fortsetzen"}],
                },
            },
            {
                "timestamp": "2026-04-17T05:48:42.000Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "model": "gpt-5.4",
                    "usage": {"input_tokens": 123, "output_tokens": 45},
                    "content": [{"type": "output_text", "text": "Weiter geht es."}],
                },
            },
        ]

        with open(fpath, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(json.dumps(line) + "\n")

        meta, messages = parse_codex_jsonl(str(fpath))

        assert meta["session_uuid"] == "019d99fa-e6f3-70a1-8035-f9c947483a8e"
        assert meta["cwd"] == "/mnt/projects/project_dashboard"
        assert meta["git_branch"] == "main"
        assert meta["model"] == "gpt-5.4"
        assert meta["user_message_count"] == 1
        assert meta["assistant_message_count"] == 1
        assert meta["total_input_tokens"] == 123
        assert meta["total_output_tokens"] == 45
        assert len(messages) == 2
        assert messages[0]["type"] == "user"
        assert messages[1]["type"] == "assistant"
        assert messages[1]["content"] == "Weiter geht es."
