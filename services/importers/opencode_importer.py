"""
Session-Importer fuer OpenCode.
"""
import json
import os
from services.ai_scope_service import extract_ai_flags
from services.db_service import execute
from services.importers.common import insert_messages, millis_to_dt, resolve_project_name_from_cwd
from services.session_import_utils import create_session_meta, update_time_range


def find_sessions_opencode(config_dir):
    """Findet OpenCode Session-Dateien in storage/session/<project>/*.json."""
    session_root = os.path.join(config_dir, "storage", "session")
    if not os.path.isdir(session_root):
        return []

    sessions = []
    for project_id in os.listdir(session_root):
        project_dir = os.path.join(session_root, project_id)
        if not os.path.isdir(project_dir):
            continue
        for filename in os.listdir(project_dir):
            if filename.startswith("ses_") and filename.endswith(".json"):
                sessions.append(os.path.join(project_dir, filename))
    return sessions


def parse_opencode_session(filepath):
    """Parsed eine OpenCode Session aus storage/session + storage/message/part."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            session_data = json.load(f)
    except Exception as e:
        print(f"Fehler beim Parsen von OpenCode-Session {filepath}: {e}")
        return None, []

    session_meta = create_session_meta(include_cache_tokens=True)
    session_id = session_data.get("id")
    session_meta["session_uuid"] = session_id
    session_meta["cwd"] = session_data.get("directory")
    session_meta["claude_version"] = session_data.get("version")
    session_meta["slug"] = session_data.get("title")
    update_time_range(session_meta, millis_to_dt((session_data.get("time") or {}).get("created")))
    update_time_range(session_meta, millis_to_dt((session_data.get("time") or {}).get("updated")))

    messages = []
    storage_root = os.path.dirname(os.path.dirname(os.path.dirname(filepath)))
    message_dir = os.path.join(storage_root, "message", session_id or "")
    if os.path.isdir(message_dir):
        for filename in sorted(os.listdir(message_dir)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(message_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                continue
            message = _build_opencode_message(payload, storage_root)
            if not message:
                continue
            messages.append(message)
            update_time_range(session_meta, message["timestamp"])
            if message["type"] == "user":
                session_meta["user_message_count"] += 1
            elif message["type"] == "assistant":
                session_meta["assistant_message_count"] += 1
                if message.get("model"):
                    session_meta["model"] = message["model"]
                session_meta["total_input_tokens"] += message.get("input_tokens", 0)
                session_meta["total_output_tokens"] += message.get("output_tokens", 0)
                session_meta["cache_read_tokens"] += message.get("cache_read_tokens", 0)
                session_meta["cache_creation_tokens"] += message.get("cache_creation_tokens", 0)

    if session_meta["started_at"] and session_meta["ended_at"]:
        delta = session_meta["ended_at"] - session_meta["started_at"]
        session_meta["duration_ms"] = int(delta.total_seconds() * 1000)

    return session_meta, messages


def import_opencode_session(filepath, account_name):
    """Importiert eine OpenCode Session."""
    stat = os.stat(filepath)
    file_size = stat.st_size
    file_mtime = stat.st_mtime
    existing = execute(
        "SELECT id, jsonl_size, jsonl_mtime FROM sessions WHERE jsonl_path = %s",
        (filepath,), fetchone=True
    )
    if existing:
        if existing["jsonl_size"] == file_size and abs(existing["jsonl_mtime"] - file_mtime) < 0.001:
            return "unchanged"
        execute("DELETE FROM messages WHERE session_id = %s", (existing["id"],))
        session_id = existing["id"]
    else:
        session_id = None

    meta, messages = parse_opencode_session(filepath)
    if not meta or not meta["session_uuid"]:
        return "skipped"

    project_name = resolve_project_name_from_cwd(meta.get("cwd"))
    project_hash = f"opencode:{project_name or 'unknown'}"
    ai_flags = extract_ai_flags(messages)
    ai_tools_json = json.dumps(ai_flags["ai_tools_used"])

    if session_id:
        execute("""
            UPDATE sessions SET
                account=%s, project_hash=%s, project_name=%s, cwd=%s, git_branch=%s,
                model=%s, claude_version=%s, slug=%s, started_at=%s, ended_at=%s,
                duration_ms=%s, user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s,
                cache_read_tokens=%s, cache_creation_tokens=%s,
                ai_has_writes=%s, ai_has_tool_calls=%s, ai_tools_used=%s,
                jsonl_size=%s, jsonl_mtime=%s, updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"], meta["started_at"],
              meta["ended_at"], meta["duration_ms"], meta["user_message_count"],
              meta["assistant_message_count"], meta["total_input_tokens"],
              meta["total_output_tokens"], meta.get("cache_read_tokens", 0),
              meta.get("cache_creation_tokens", 0), ai_flags["ai_has_writes"],
              ai_flags["ai_has_tool_calls"], ai_tools_json, file_size, file_mtime, session_id))
    else:
        row = execute("""
            INSERT INTO sessions (session_uuid, account, project_hash, project_name,
                cwd, git_branch, model, claude_version, slug, started_at, ended_at,
                duration_ms, user_message_count, assistant_message_count,
                total_input_tokens, total_output_tokens, cache_read_tokens, cache_creation_tokens,
                ai_has_writes, ai_has_tool_calls, ai_tools_used,
                jsonl_path, jsonl_size, jsonl_mtime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                cache_read_tokens=EXCLUDED.cache_read_tokens,
                cache_creation_tokens=EXCLUDED.cache_creation_tokens,
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
              meta.get("cache_read_tokens", 0), meta.get("cache_creation_tokens", 0),
              ai_flags["ai_has_writes"], ai_flags["ai_has_tool_calls"], ai_tools_json,
              filepath, file_size, file_mtime), fetchone=True)
        session_id = row["id"]

    insert_messages(session_id, messages)
    return "updated" if existing else "imported"


def _load_opencode_parts(storage_root, message_id):
    part_dir = os.path.join(storage_root, "part", message_id or "")
    if not os.path.isdir(part_dir):
        return []
    parts = []
    for filename in sorted(os.listdir(part_dir)):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(part_dir, filename), "r", encoding="utf-8") as f:
                parts.append(json.load(f))
        except Exception:
            continue
    return parts


def _build_opencode_message(payload, storage_root):
    role = payload.get("role")
    if role not in ("user", "assistant", "system"):
        return None
    parts = _load_opencode_parts(storage_root, payload.get("id"))
    content = _extract_opencode_text(payload, parts)
    model = payload.get("modelID")
    if not model and isinstance(payload.get("model"), dict):
        model = payload["model"].get("modelID")
    usage = payload.get("tokens") or {}
    cache = usage.get("cache") or {}
    created_ms = (payload.get("time") or {}).get("created")
    completed_ms = (payload.get("time") or {}).get("completed")
    created_dt = millis_to_dt(created_ms)
    completed_dt = millis_to_dt(completed_ms)
    duration_ms = 0
    if created_ms and completed_ms:
        duration_ms = max(0, int(completed_ms - created_ms))
    content_json = json.dumps({"payload": payload, "parts": parts}, ensure_ascii=False)
    return {
        "uuid": payload.get("id"),
        "parent_uuid": payload.get("parentID"),
        "type": role,
        "content": (content or "")[:10000],
        "content_json": content_json,
        "model": model,
        "input_tokens": usage.get("input", 0) if role == "assistant" else 0,
        "output_tokens": usage.get("output", 0) if role == "assistant" else 0,
        "cache_read_tokens": cache.get("read", 0) if role == "assistant" else 0,
        "cache_creation_tokens": cache.get("write", 0) if role == "assistant" else 0,
        "duration_ms": duration_ms,
        "timestamp": created_dt or completed_dt,
        "is_tool_result": any(part.get("type") not in ("text", "reasoning", "step-start", "step-finish") for part in parts),
    }


def _extract_opencode_text(payload, parts):
    texts = []
    for part in parts:
        if part.get("type") in ("text", "reasoning") and part.get("text"):
            texts.append(part.get("text"))
    if texts:
        return "\n\n".join(texts)
    summary = payload.get("summary") or {}
    if summary.get("body"):
        return summary["body"]
    if summary.get("title"):
        return summary["title"]
    return ""
