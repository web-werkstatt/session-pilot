"""
Session-Importer fuer OpenAI Codex CLI.
"""
import json
import os
from config import PROJECTS_DIR
from services.ai_scope_service import extract_ai_flags
from services.db_service import execute
from services.importers.common import insert_messages
from services.session_import_utils import parse_ts as _parse_ts, create_session_meta, update_time_range


def find_sessions_codex(config_dir):
    """Findet alle Codex CLI JSONL-Session-Dateien."""
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
                    for filename in os.listdir(full_path):
                        if filename.endswith(".jsonl"):
                            sessions.append((os.path.join(full_path, filename), None))
                elif day_or_file.endswith(".jsonl"):
                    sessions.append((full_path, None))
    return sessions


def parse_codex_jsonl(filepath):
    """Parsed eine Codex CLI JSONL-Session."""
    session_meta = create_session_meta()
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
                timestamp = _parse_ts(entry.get("timestamp"))
                update_time_range(session_meta, timestamp)

                if entry_type == "session_meta":
                    payload = entry.get("payload", {})
                    session_meta["session_uuid"] = payload.get("id")
                    session_meta["cwd"] = payload.get("cwd")
                    session_meta["claude_version"] = payload.get("cli_version")
                    git_info = payload.get("git", {})
                    session_meta["git_branch"] = git_info.get("branch")
                    continue

                if entry_type != "response_item":
                    continue

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
                else:
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
                    "uuid": payload.get("id"),
                    "parent_uuid": None,
                    "type": role,
                    "content": text[:10000],
                    "content_json": None,
                    "model": model,
                    "input_tokens": usage.get("input_tokens", 0) if role == "assistant" else 0,
                    "output_tokens": usage.get("output_tokens", 0) if role == "assistant" else 0,
                    "duration_ms": 0,
                    "timestamp": timestamp,
                    "is_tool_result": False,
                })

    except Exception as e:
        print(f"Fehler beim Parsen von Codex-Session {filepath}: {e}")
        return None, []

    if session_meta["started_at"] and session_meta["ended_at"]:
        delta = session_meta["ended_at"] - session_meta["started_at"]
        session_meta["duration_ms"] = int(delta.total_seconds() * 1000)

    return session_meta, messages


def import_codex_session(filepath, account_name):
    """Importiert eine Codex CLI Session."""
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
        if PROJECTS_DIR in cwd:
            project_name = cwd.split(PROJECTS_DIR + "/")[-1].split("/")[0]
        else:
            project_name = os.path.basename(cwd)
    if project_name:
        real_path = os.path.join(PROJECTS_DIR, project_name)
        if not os.path.isdir(real_path):
            alt = project_name.replace("-", "_")
            if os.path.isdir(os.path.join(PROJECTS_DIR, alt)):
                project_name = alt
    project_hash = f"codex:{project_name or 'unknown'}"

    for message in messages:
        if message.get("content"):
            message["content"] = message["content"].replace("\x00", "")

    ai_flags = extract_ai_flags(messages)

    if session_id:
        execute("""
            UPDATE sessions SET
                account=%s, project_hash=%s, project_name=%s, cwd=%s, git_branch=%s,
                model=%s, claude_version=%s, slug=%s, started_at=%s, ended_at=%s,
                duration_ms=%s, user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s,
                ai_has_writes=%s, ai_has_tool_calls=%s, ai_tools_used=%s,
                jsonl_size=%s, jsonl_mtime=%s, updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"], meta["started_at"],
              meta["ended_at"], meta["duration_ms"], meta["user_message_count"],
              meta["assistant_message_count"], meta["total_input_tokens"],
              meta["total_output_tokens"], ai_flags["ai_has_writes"],
              ai_flags["ai_has_tool_calls"], json.dumps(ai_flags["ai_tools_used"]),
              file_size, file_mtime, session_id))
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
                jsonl_size=EXCLUDED.jsonl_size, jsonl_mtime=EXCLUDED.jsonl_mtime, updated_at=NOW()
            RETURNING id
        """, (meta["session_uuid"], account_name, project_hash, project_name,
              meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
              meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
              meta["user_message_count"], meta["assistant_message_count"],
              meta["total_input_tokens"], meta["total_output_tokens"],
              ai_flags["ai_has_writes"], ai_flags["ai_has_tool_calls"],
              json.dumps(ai_flags["ai_tools_used"]), filepath, file_size, file_mtime),
            fetchone=True)
        session_id = row["id"]

    insert_messages(session_id, messages)
    return "updated" if existing else "imported"
