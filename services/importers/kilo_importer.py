"""
Session-Importer fuer Kilo.
"""
import json
import os
import sqlite3
from services.ai_scope_service import extract_ai_flags
from services.db_service import execute
from services.importers.common import insert_messages, millis_to_dt, resolve_project_name_from_cwd
from services.session_import_utils import create_session_meta


def import_kilo_sessions(config_dir, account_name):
    """Importiert alle Kilo Sessions aus kilo.db."""
    db_path = os.path.join(config_dir, "kilo.db")
    if not os.path.isfile(db_path):
        return {"imported": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}

    stats = {"imported": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sessions = conn.execute("""
            SELECT id, slug, directory, title, version, time_created, time_updated
            FROM session
            ORDER BY time_updated DESC
        """).fetchall()
        for row in sessions:
            try:
                result = import_kilo_session(conn, row, account_name, db_path)
                stats[result] += 1
            except Exception as e:
                print(f"Fehler bei Kilo-Session {row['id']}: {e}")
                stats["errors"] += 1
    finally:
        conn.close()
    return stats


def import_kilo_session(conn, session_row, account_name, db_path):
    """Importiert eine einzelne Kilo Session aus der SQLite-DB."""
    session_uuid = session_row["id"]
    existing = execute("SELECT id, ended_at FROM sessions WHERE session_uuid = %s", (session_uuid,), fetchone=True)
    updated_at = millis_to_dt(session_row["time_updated"])
    if existing and updated_at and existing.get("ended_at") == updated_at:
        return "unchanged"

    meta = create_session_meta(include_cache_tokens=True)
    meta["session_uuid"] = session_uuid
    meta["cwd"] = session_row["directory"]
    meta["claude_version"] = session_row["version"]
    meta["slug"] = session_row["slug"] or session_row["title"]
    meta["started_at"] = millis_to_dt(session_row["time_created"])
    meta["ended_at"] = updated_at
    if meta["started_at"] and meta["ended_at"]:
        meta["duration_ms"] = int((meta["ended_at"] - meta["started_at"]).total_seconds() * 1000)

    rows = conn.execute("""
        SELECT id, session_id, time_created, time_updated, data
        FROM message
        WHERE session_id = ?
        ORDER BY time_created ASC
    """, (session_uuid,)).fetchall()
    messages = []
    for row in rows:
        payload = json.loads(row["data"])
        message = _build_kilo_message(row, payload)
        messages.append(message)
        if message["type"] == "user":
            meta["user_message_count"] += 1
        elif message["type"] == "assistant":
            meta["assistant_message_count"] += 1
            if message.get("model"):
                meta["model"] = message["model"]
            meta["total_input_tokens"] += message.get("input_tokens", 0)
            meta["total_output_tokens"] += message.get("output_tokens", 0)
            meta["cache_read_tokens"] += message.get("cache_read_tokens", 0)
            meta["cache_creation_tokens"] += message.get("cache_creation_tokens", 0)

    project_name = resolve_project_name_from_cwd(meta.get("cwd"))
    project_hash = f"kilo:{project_name or 'unknown'}"
    ai_flags = extract_ai_flags(messages)
    ai_tools_json = json.dumps(ai_flags["ai_tools_used"])

    if existing:
        execute("DELETE FROM messages WHERE session_id = %s", (existing["id"],))
        session_id = existing["id"]
        execute("""
            UPDATE sessions SET
                account=%s, project_hash=%s, project_name=%s, cwd=%s, git_branch=%s,
                model=%s, claude_version=%s, slug=%s, started_at=%s, ended_at=%s,
                duration_ms=%s, user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s,
                cache_read_tokens=%s, cache_creation_tokens=%s,
                ai_has_writes=%s, ai_has_tool_calls=%s, ai_tools_used=%s,
                jsonl_path=%s, jsonl_size=%s, jsonl_mtime=%s, updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"], meta["started_at"],
              meta["ended_at"], meta["duration_ms"], meta["user_message_count"],
              meta["assistant_message_count"], meta["total_input_tokens"],
              meta["total_output_tokens"], meta.get("cache_read_tokens", 0),
              meta.get("cache_creation_tokens", 0), ai_flags["ai_has_writes"],
              ai_flags["ai_has_tool_calls"], ai_tools_json, db_path, 0, 0, session_id))
        status = "updated"
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
        """, (session_uuid, account_name, project_hash, project_name,
              meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
              meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
              meta["user_message_count"], meta["assistant_message_count"],
              meta["total_input_tokens"], meta["total_output_tokens"],
              meta.get("cache_read_tokens", 0), meta.get("cache_creation_tokens", 0),
              ai_flags["ai_has_writes"], ai_flags["ai_has_tool_calls"], ai_tools_json,
              db_path, 0, 0), fetchone=True)
        session_id = row["id"]
        status = "imported"

    insert_messages(session_id, messages)
    return status


def _build_kilo_message(row, payload):
    role = payload.get("role")
    created_dt = millis_to_dt(row["time_created"])
    updated_dt = millis_to_dt(row["time_updated"])
    usage = payload.get("tokens") or {}
    cache = usage.get("cache") or {}
    content = _extract_kilo_text(payload)
    return {
        "uuid": row["id"],
        "parent_uuid": payload.get("parentID"),
        "type": role if role in ("user", "assistant") else "system",
        "content": content[:10000] if content else "",
        "content_json": json.dumps(payload, ensure_ascii=False),
        "model": payload.get("modelID"),
        "input_tokens": usage.get("input", 0) if role == "assistant" else 0,
        "output_tokens": usage.get("output", 0) if role == "assistant" else 0,
        "cache_read_tokens": cache.get("read", 0) if role == "assistant" else 0,
        "cache_creation_tokens": cache.get("write", 0) if role == "assistant" else 0,
        "duration_ms": int(max(0, row["time_updated"] - row["time_created"])) if row["time_updated"] and row["time_created"] else 0,
        "timestamp": created_dt or updated_dt,
        "is_tool_result": payload.get("finish") == "tool-calls",
    }


def _extract_kilo_text(payload):
    summary = payload.get("summary") or {}
    texts = []
    if summary.get("title"):
        texts.append(summary["title"])
    if summary.get("body"):
        texts.append(summary["body"])
    diffs = summary.get("diffs") or []
    if diffs:
        file_names = []
        for item in diffs[:8]:
            if isinstance(item, dict) and item.get("file"):
                file_names.append(item["file"])
        if file_names:
            texts.append("Changed files: " + ", ".join(file_names))
    if texts:
        return "\n\n".join(texts)
    if payload.get("role") == "assistant":
        bits = []
        if payload.get("modelID"):
            bits.append("Model: " + payload["modelID"])
        if payload.get("finish"):
            bits.append("Finish: " + str(payload["finish"]))
        tokens = payload.get("tokens") or {}
        if tokens:
            bits.append(
                "Tokens: in {0}, out {1}, reasoning {2}".format(
                    tokens.get("input", 0), tokens.get("output", 0), tokens.get("reasoning", 0)
                )
            )
        return "\n".join(bits)
    return ""
