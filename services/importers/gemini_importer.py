"""
Session-Importer fuer Google Gemini CLI.
"""
import json
import os
from services.ai_scope_service import extract_ai_flags
from services.db_service import execute
from services.importers.common import insert_messages
from services.session_import_utils import parse_ts as _parse_ts, create_session_meta, update_time_range


def find_sessions_gemini(config_dir):
    """Findet alle Gemini CLI Session-Dateien."""
    tmp_dir = os.path.join(config_dir, "tmp")
    if not os.path.isdir(tmp_dir):
        return []
    sessions = []
    for project_hash in os.listdir(tmp_dir):
        log_path = os.path.join(tmp_dir, project_hash, "logs.json")
        if os.path.isfile(log_path):
            sessions.append((log_path, project_hash))
    return sessions


def parse_gemini_json(filepath, project_hash):
    """Parsed eine Gemini CLI logs.json; Datei kann mehrere Sessions enthalten."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return []

        by_session = {}
        for entry in data:
            session_id = entry.get("sessionId", "unknown")
            by_session.setdefault(session_id, []).append(entry)

        for session_id, entries in by_session.items():
            meta = create_session_meta()
            meta["session_uuid"] = session_id
            messages = []

            for entry in entries:
                timestamp = _parse_ts(entry.get("timestamp"))
                update_time_range(meta, timestamp)

                role = entry.get("type", "")
                text = entry.get("message", "")
                if role == "user":
                    meta["user_message_count"] += 1
                elif role == "model":
                    meta["assistant_message_count"] += 1
                    role = "assistant"

                usage = entry.get("usage", {})
                if usage:
                    meta["total_input_tokens"] += usage.get("promptTokenCount", 0)
                    meta["total_output_tokens"] += usage.get("candidatesTokenCount", 0)

                msg_uuid = f"{session_id}-{entry.get('messageId', 0)}"
                messages.append({
                    "uuid": msg_uuid[:36],
                    "parent_uuid": None,
                    "type": role if role in ("user", "assistant") else "system",
                    "content": text[:10000] if text else "",
                    "content_json": None,
                    "model": entry.get("model"),
                    "input_tokens": usage.get("promptTokenCount", 0),
                    "output_tokens": usage.get("candidatesTokenCount", 0),
                    "duration_ms": 0,
                    "timestamp": timestamp,
                    "is_tool_result": False,
                })

            if meta["started_at"] and meta["ended_at"]:
                delta = meta["ended_at"] - meta["started_at"]
                meta["duration_ms"] = int(delta.total_seconds() * 1000)
            results.append((meta, messages, project_hash))

    except Exception as e:
        print(f"Fehler beim Parsen von Gemini-Session {filepath}: {e}")
    return results


def import_gemini_session(meta, messages, account_name, project_hash):
    """Importiert eine einzelne Gemini-Session."""
    if not meta or not meta["session_uuid"]:
        return "skipped"

    project_name = "gemini_sessions"
    existing = execute(
        "SELECT id, updated_at FROM sessions WHERE session_uuid = %s",
        (meta["session_uuid"],), fetchone=True
    )

    for message in messages:
        if message.get("content"):
            message["content"] = message["content"].replace("\x00", "")

    ai_flags = extract_ai_flags(messages)

    if existing:
        execute("""
            UPDATE sessions SET account=%s, project_hash=%s, project_name=%s,
                cwd=%s, git_branch=%s, model=%s, claude_version=%s, slug=%s,
                started_at=%s, ended_at=%s, duration_ms=%s,
                user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s,
                ai_has_writes=%s, ai_has_tool_calls=%s, ai_tools_used=%s,
                updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"], meta["started_at"],
              meta["ended_at"], meta["duration_ms"], meta["user_message_count"],
              meta["assistant_message_count"], meta["total_input_tokens"],
              meta["total_output_tokens"], ai_flags["ai_has_writes"],
              ai_flags["ai_has_tool_calls"], json.dumps(ai_flags["ai_tools_used"]),
              existing["id"]))
        execute("DELETE FROM messages WHERE session_id = %s", (existing["id"],))
        session_id = existing["id"]
        status = "updated"
    else:
        row = execute("""
            INSERT INTO sessions (session_uuid, account, project_hash, project_name,
                cwd, git_branch, model, claude_version, slug, started_at, ended_at,
                duration_ms, user_message_count, assistant_message_count,
                total_input_tokens, total_output_tokens,
                ai_has_writes, ai_has_tool_calls, ai_tools_used,
                jsonl_path, jsonl_size, jsonl_mtime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_uuid) DO UPDATE SET
                account=EXCLUDED.account,
                project_hash=EXCLUDED.project_hash,
                project_name=EXCLUDED.project_name,
                cwd=EXCLUDED.cwd,
                git_branch=EXCLUDED.git_branch,
                model=EXCLUDED.model,
                claude_version=EXCLUDED.claude_version,
                slug=EXCLUDED.slug,
                started_at=EXCLUDED.started_at,
                ended_at=EXCLUDED.ended_at,
                duration_ms=EXCLUDED.duration_ms,
                user_message_count=EXCLUDED.user_message_count,
                assistant_message_count=EXCLUDED.assistant_message_count,
                total_input_tokens=EXCLUDED.total_input_tokens,
                total_output_tokens=EXCLUDED.total_output_tokens,
                ai_has_writes=EXCLUDED.ai_has_writes,
                ai_has_tool_calls=EXCLUDED.ai_has_tool_calls,
                ai_tools_used=EXCLUDED.ai_tools_used,
                jsonl_path=EXCLUDED.jsonl_path,
                jsonl_size=EXCLUDED.jsonl_size,
                jsonl_mtime=EXCLUDED.jsonl_mtime,
                updated_at=NOW()
            RETURNING id
        """, (meta["session_uuid"], account_name, project_hash, project_name,
              meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
              meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
              meta["user_message_count"], meta["assistant_message_count"],
              meta["total_input_tokens"], meta["total_output_tokens"],
              ai_flags["ai_has_writes"], ai_flags["ai_has_tool_calls"],
              json.dumps(ai_flags["ai_tools_used"]), None, 0, 0),
            fetchone=True)
        session_id = row["id"]
        status = "imported"

    insert_messages(session_id, messages)
    return status
