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
