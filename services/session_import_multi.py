"""
Parser und Import-Funktionen fuer Nicht-Claude AI-Assistenten:
- OpenAI Codex CLI (JSONL)
- Google Gemini CLI (JSON)
"""
import json
import os
from datetime import datetime
from services.db_service import execute, execute_many


def find_sessions_codex(config_dir):
    """Findet alle Codex CLI JSONL-Session-Dateien (sessions/YYYY/MM/DD/*.jsonl)"""
    sessions_dir = os.path.join(config_dir, "sessions")
    if not os.path.isdir(sessions_dir):
        return []

    sessions = []
    for year in os.listdir(sessions_dir):
        year_path = os.path.join(sessions_dir, year)
        if not os.path.isdir(year_path):
            continue
        for month in os.listdir(year_path):
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue
            for day_or_file in os.listdir(month_path):
                full_path = os.path.join(month_path, day_or_file)
                if os.path.isdir(full_path):
                    for f in os.listdir(full_path):
                        if f.endswith(".jsonl"):
                            sessions.append((os.path.join(full_path, f), None))
                elif day_or_file.endswith(".jsonl"):
                    sessions.append((full_path, None))
    return sessions


def parse_codex_jsonl(filepath):
    """Parsed eine Codex CLI JSONL-Session"""
    session_meta = {
        "session_uuid": None, "cwd": None, "git_branch": None,
        "model": None, "claude_version": None, "slug": None,
        "started_at": None, "ended_at": None, "duration_ms": 0,
        "user_message_count": 0, "assistant_message_count": 0,
        "total_input_tokens": 0, "total_output_tokens": 0,
    }
    messages = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type")
                timestamp_str = entry.get("timestamp")
                timestamp = None
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                if timestamp:
                    if not session_meta["started_at"] or timestamp < session_meta["started_at"]:
                        session_meta["started_at"] = timestamp
                    if not session_meta["ended_at"] or timestamp > session_meta["ended_at"]:
                        session_meta["ended_at"] = timestamp

                if entry_type == "session_meta":
                    payload = entry.get("payload", {})
                    session_meta["session_uuid"] = payload.get("id")
                    session_meta["cwd"] = payload.get("cwd")
                    session_meta["claude_version"] = payload.get("cli_version")
                    git_info = payload.get("git", {})
                    session_meta["git_branch"] = git_info.get("branch")
                    continue

                if entry_type == "response_item":
                    payload = entry.get("payload", {})
                    role = payload.get("role")

                    if role not in ("user", "assistant"):
                        model = payload.get("model")
                        if model:
                            session_meta["model"] = model
                        continue

                    content_blocks = payload.get("content") or []
                    text_parts = []
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") in ("input_text", "output_text"):
                            text_parts.append(block.get("text", ""))
                    text = "\n".join(text_parts)

                    if role == "user":
                        session_meta["user_message_count"] += 1
                    elif role == "assistant":
                        session_meta["assistant_message_count"] += 1

                    model = payload.get("model")
                    if model:
                        session_meta["model"] = model

                    usage = payload.get("usage", {})
                    if usage:
                        session_meta["total_input_tokens"] += usage.get("input_tokens", 0)
                        session_meta["total_output_tokens"] += usage.get("output_tokens", 0)

                    if not text or not text.strip():
                        continue

                    messages.append({
                        "uuid": payload.get("id"), "parent_uuid": None,
                        "type": role, "content": text[:10000], "content_json": None,
                        "model": model,
                        "input_tokens": usage.get("input_tokens", 0) if role == "assistant" else 0,
                        "output_tokens": usage.get("output_tokens", 0) if role == "assistant" else 0,
                        "duration_ms": 0, "timestamp": timestamp, "is_tool_result": False,
                    })

    except Exception as e:
        print(f"Fehler beim Parsen von Codex-Session {filepath}: {e}")
        return None, []

    if session_meta["started_at"] and session_meta["ended_at"]:
        delta = session_meta["ended_at"] - session_meta["started_at"]
        session_meta["duration_ms"] = int(delta.total_seconds() * 1000)

    return session_meta, messages


def import_codex_session(filepath, account_name):
    """Importiert eine Codex CLI Session"""
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

    meta, messages = parse_codex_jsonl(filepath)
    if not meta or not meta["session_uuid"]:
        return "skipped"

    project_name = None
    if meta.get("cwd"):
        cwd = meta["cwd"]
        if "/mnt/projects/" in cwd:
            project_name = cwd.split("/mnt/projects/")[-1].split("/")[0]
        else:
            project_name = os.path.basename(cwd)
    project_hash = f"codex:{project_name or 'unknown'}"

    for m in messages:
        if m.get("content"):
            m["content"] = m["content"].replace("\x00", "")

    if session_id:
        execute("""
            UPDATE sessions SET
                account=%s, project_hash=%s, project_name=%s, cwd=%s, git_branch=%s,
                model=%s, claude_version=%s, slug=%s, started_at=%s, ended_at=%s,
                duration_ms=%s, user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s,
                jsonl_size=%s, jsonl_mtime=%s, updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"], meta["started_at"],
              meta["ended_at"], meta["duration_ms"], meta["user_message_count"],
              meta["assistant_message_count"], meta["total_input_tokens"],
              meta["total_output_tokens"], file_size, file_mtime, session_id))
    else:
        row = execute("""
            INSERT INTO sessions (session_uuid, account, project_hash, project_name,
                cwd, git_branch, model, claude_version, slug, started_at, ended_at,
                duration_ms, user_message_count, assistant_message_count,
                total_input_tokens, total_output_tokens, jsonl_path, jsonl_size, jsonl_mtime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_uuid) DO UPDATE SET
                jsonl_size=EXCLUDED.jsonl_size, jsonl_mtime=EXCLUDED.jsonl_mtime, updated_at=NOW()
            RETURNING id
        """, (meta["session_uuid"], account_name, project_hash, project_name,
              meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
              meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
              meta["user_message_count"], meta["assistant_message_count"],
              meta["total_input_tokens"], meta["total_output_tokens"],
              filepath, file_size, file_mtime), fetchone=True)
        session_id = row["id"]

    _insert_messages(session_id, messages)
    return "updated" if existing else "imported"


# === Gemini ===

def find_sessions_gemini(config_dir):
    """Findet alle Gemini CLI Session-Dateien (tmp/<hash>/logs.json)"""
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
    """Parsed eine Gemini CLI logs.json - kann mehrere Sessions enthalten"""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return []

        by_session = {}
        for entry in data:
            sid = entry.get("sessionId", "unknown")
            by_session.setdefault(sid, []).append(entry)

        for sid, entries in by_session.items():
            meta = {
                "session_uuid": sid, "cwd": None, "git_branch": None,
                "model": None, "claude_version": None, "slug": None,
                "started_at": None, "ended_at": None, "duration_ms": 0,
                "user_message_count": 0, "assistant_message_count": 0,
                "total_input_tokens": 0, "total_output_tokens": 0,
            }
            messages = []

            for entry in entries:
                ts_str = entry.get("timestamp")
                timestamp = None
                if ts_str:
                    try:
                        timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass
                if timestamp:
                    if not meta["started_at"] or timestamp < meta["started_at"]:
                        meta["started_at"] = timestamp
                    if not meta["ended_at"] or timestamp > meta["ended_at"]:
                        meta["ended_at"] = timestamp

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

                msg_uuid = f"{sid}-{entry.get('messageId', 0)}"
                messages.append({
                    "uuid": msg_uuid[:36], "parent_uuid": None,
                    "type": role if role in ("user", "assistant") else "system",
                    "content": text[:10000] if text else "", "content_json": None,
                    "model": entry.get("model"),
                    "input_tokens": usage.get("promptTokenCount", 0),
                    "output_tokens": usage.get("candidatesTokenCount", 0),
                    "duration_ms": 0, "timestamp": timestamp, "is_tool_result": False,
                })

            if meta["started_at"] and meta["ended_at"]:
                delta = meta["ended_at"] - meta["started_at"]
                meta["duration_ms"] = int(delta.total_seconds() * 1000)
            results.append((meta, messages, project_hash))

    except Exception as e:
        print(f"Fehler beim Parsen von Gemini-Session {filepath}: {e}")
    return results


def import_gemini_session(meta, messages, account_name, project_hash):
    """Importiert eine einzelne Gemini-Session"""
    if not meta or not meta["session_uuid"]:
        return "skipped"

    project_name = f"gemini:{project_hash[:12]}"
    existing = execute(
        "SELECT id, updated_at FROM sessions WHERE session_uuid = %s",
        (meta["session_uuid"],), fetchone=True
    )

    for m in messages:
        if m.get("content"):
            m["content"] = m["content"].replace("\x00", "")

    if existing:
        execute("""
            UPDATE sessions SET account=%s, project_hash=%s, project_name=%s,
                cwd=%s, git_branch=%s, model=%s, claude_version=%s, slug=%s,
                started_at=%s, ended_at=%s, duration_ms=%s,
                user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s, updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"], meta["started_at"],
              meta["ended_at"], meta["duration_ms"], meta["user_message_count"],
              meta["assistant_message_count"], meta["total_input_tokens"],
              meta["total_output_tokens"], existing["id"]))
        execute("DELETE FROM messages WHERE session_id = %s", (existing["id"],))
        session_id = existing["id"]
        status = "updated"
    else:
        row = execute("""
            INSERT INTO sessions (session_uuid, account, project_hash, project_name,
                cwd, git_branch, model, claude_version, slug, started_at, ended_at,
                duration_ms, user_message_count, assistant_message_count,
                total_input_tokens, total_output_tokens, jsonl_path, jsonl_size, jsonl_mtime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_uuid) DO UPDATE SET updated_at=NOW()
            RETURNING id
        """, (meta["session_uuid"], account_name, project_hash, project_name,
              meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
              meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
              meta["user_message_count"], meta["assistant_message_count"],
              meta["total_input_tokens"], meta["total_output_tokens"], None, 0, 0),
            fetchone=True)
        session_id = row["id"]
        status = "imported"

    _insert_messages(session_id, messages)
    return status


def _insert_messages(session_id, messages):
    """Fuegt Messages in die DB ein"""
    if not messages:
        return
    msg_params = [
        (session_id, m["uuid"], m["parent_uuid"], m["type"], m["content"],
         m["content_json"], m["model"], m["input_tokens"], m["output_tokens"],
         m["duration_ms"], m["timestamp"], m["is_tool_result"])
        for m in messages
    ]
    execute_many("""
        INSERT INTO messages (session_id, uuid, parent_uuid, type, content, content_json,
            model, input_tokens, output_tokens, duration_ms, timestamp, is_tool_result)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, msg_params)
