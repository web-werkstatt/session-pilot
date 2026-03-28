"""
Shared Utility-Funktionen fuer Session-Import (Claude, Codex, Gemini).
Vermeidet Circular Imports zwischen session_import.py und session_import_multi.py.
"""
import json
from datetime import datetime


def parse_ts(ts_str):
    """Parst ISO-Timestamp String zu datetime"""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def create_session_meta(include_cache_tokens=False):
    """Erzeugt leere Session-Meta-Struktur fuer Import"""
    meta = {
        "session_uuid": None, "cwd": None, "git_branch": None,
        "model": None, "claude_version": None, "slug": None,
        "started_at": None, "ended_at": None, "duration_ms": 0,
        "user_message_count": 0, "assistant_message_count": 0,
        "total_input_tokens": 0, "total_output_tokens": 0,
    }
    if include_cache_tokens:
        meta["cache_read_tokens"] = 0
        meta["cache_creation_tokens"] = 0
    return meta


def update_time_range(meta, timestamp):
    """Aktualisiert started_at/ended_at Range im Meta-Dict"""
    if not timestamp:
        return
    if not meta["started_at"] or timestamp < meta["started_at"]:
        meta["started_at"] = timestamp
    if not meta["ended_at"] or timestamp > meta["ended_at"]:
        meta["ended_at"] = timestamp


def sanitize_content_json(content_json_str):
    """Bereinigt content_json fuer PostgreSQL jsonb"""
    if not content_json_str:
        return None
    s = content_json_str.replace("\x00", "").replace("\\u0000", "")
    try:
        parsed = json.loads(s)
        result = json.dumps(parsed, ensure_ascii=True)
        return result.replace("\\u0000", "")
    except (json.JSONDecodeError, ValueError):
        return None
