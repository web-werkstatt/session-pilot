"""
JSONL-Parser und DB-Import fuer Claude Code Sessions
"""
import json
import os
import re
from datetime import datetime, timezone
from config import CLAUDE_ACCOUNTS
from services.db_service import execute, execute_many

# Typen die importiert werden
IMPORT_TYPES = {"user", "assistant", "system"}
# Typen die ignoriert werden
IGNORE_TYPES = {"progress", "file-history-snapshot", "queue-operation", "last-prompt"}


def extract_project_name(project_hash):
    """Extrahiert Projektnamen aus Hash (z.B. -mnt-projects-proj-irtours -> proj-irtours)"""
    if not project_hash:
        return None
    # Entferne fuehrendes -mnt-projects-
    name = re.sub(r'^-mnt-projects-', '', project_hash)
    # Entferne -home-joshko- Prefix
    name = re.sub(r'^-home-joshko-?', 'home', name)
    # Wenn nur "-mnt-projects" ohne Suffix, zeige als "(root)"
    if not name or name == project_hash:
        return project_hash
    return name


def extract_text_content(content):
    """Extrahiert lesbaren Text aus Message-Content"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    # Tool-Ergebnisse zusammenfassen
                    tool_content = block.get("content", "")
                    if isinstance(tool_content, list):
                        for tc in tool_content:
                            if isinstance(tc, dict) and tc.get("type") == "text":
                                texts.append(tc.get("text", ""))
                    elif isinstance(tool_content, str):
                        texts.append(tool_content)
        return "\n".join(texts) if texts else ""
    return str(content) if content else ""


def has_tool_use(content):
    """Prueft ob Content Tool-Calls enthaelt"""
    if isinstance(content, list):
        return any(
            isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result")
            for b in content
        )
    return False


def parse_jsonl(filepath):
    """Parsed eine JSONL-Datei und gibt Session-Metadaten + Messages zurueck"""
    session_meta = {
        "session_uuid": None,
        "cwd": None,
        "git_branch": None,
        "model": None,
        "claude_version": None,
        "slug": None,
        "started_at": None,
        "ended_at": None,
        "duration_ms": 0,
        "user_message_count": 0,
        "assistant_message_count": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
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
                if entry_type in IGNORE_TYPES:
                    continue
                if entry_type not in IMPORT_TYPES:
                    continue

                timestamp_str = entry.get("timestamp")
                timestamp = None
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                # Session-Metadaten aus erstem Eintrag
                if not session_meta["session_uuid"]:
                    session_meta["session_uuid"] = entry.get("sessionId")
                    session_meta["cwd"] = entry.get("cwd")
                    session_meta["git_branch"] = entry.get("gitBranch")
                    session_meta["claude_version"] = entry.get("version")

                if timestamp:
                    if not session_meta["started_at"] or timestamp < session_meta["started_at"]:
                        session_meta["started_at"] = timestamp
                    if not session_meta["ended_at"] or timestamp > session_meta["ended_at"]:
                        session_meta["ended_at"] = timestamp

                # Slug aus system-Eintraegen
                if entry.get("slug"):
                    session_meta["slug"] = entry["slug"]

                # System turn_duration
                if entry_type == "system" and entry.get("subtype") == "turn_duration":
                    session_meta["duration_ms"] += entry.get("durationMs", 0)
                    msg_data = {
                        "uuid": entry.get("uuid"),
                        "parent_uuid": entry.get("parentUuid"),
                        "type": "system",
                        "content": f"Turn-Dauer: {entry.get('durationMs', 0)}ms",
                        "content_json": json.dumps({"subtype": "turn_duration", "durationMs": entry.get("durationMs", 0)}),
                        "model": None,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "duration_ms": entry.get("durationMs", 0),
                        "timestamp": timestamp,
                        "is_tool_result": False,
                    }
                    messages.append(msg_data)
                    continue

                # User/Assistant Messages
                message = entry.get("message", {})
                role = message.get("role", entry_type)
                content = message.get("content", "")

                if role == "user":
                    session_meta["user_message_count"] += 1
                elif role == "assistant":
                    session_meta["assistant_message_count"] += 1
                    # Model + Tokens
                    model = message.get("model")
                    if model:
                        session_meta["model"] = model
                    usage = message.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    session_meta["total_input_tokens"] += input_tokens
                    session_meta["total_output_tokens"] += output_tokens

                text_content = extract_text_content(content)
                is_tool = has_tool_use(content)

                # Content-JSON nur bei Tool-Use oder komplexem Content
                content_json = None
                if isinstance(content, list):
                    try:
                        content_json = json.dumps(content, ensure_ascii=False)
                    except (TypeError, ValueError):
                        content_json = None

                msg_data = {
                    "uuid": entry.get("uuid"),
                    "parent_uuid": entry.get("parentUuid"),
                    "type": role,
                    "content": text_content,
                    "content_json": content_json,
                    "model": message.get("model"),
                    "input_tokens": message.get("usage", {}).get("input_tokens", 0) if role == "assistant" else 0,
                    "output_tokens": message.get("usage", {}).get("output_tokens", 0) if role == "assistant" else 0,
                    "duration_ms": 0,
                    "timestamp": timestamp,
                    "is_tool_result": is_tool,
                }
                messages.append(msg_data)

    except Exception as e:
        print(f"Fehler beim Parsen von {filepath}: {e}")
        return None, []

    return session_meta, messages


def import_session(filepath, account_name, project_hash):
    """Importiert eine einzelne Session in die Datenbank"""
    stat = os.stat(filepath)
    file_size = stat.st_size
    file_mtime = stat.st_mtime

    # Change-Detection: Pruefen ob bereits importiert und unveraendert
    existing = execute(
        "SELECT id, jsonl_size, jsonl_mtime FROM sessions WHERE jsonl_path = %s",
        (filepath,), fetchone=True
    )

    if existing:
        if existing["jsonl_size"] == file_size and abs(existing["jsonl_mtime"] - file_mtime) < 0.001:
            return "unchanged"
        # Geaendert -> Re-Import: Messages loeschen
        execute("DELETE FROM messages WHERE session_id = %s", (existing["id"],))
        session_id = existing["id"]
    else:
        session_id = None

    # JSONL parsen
    meta, messages = parse_jsonl(filepath)
    if not meta or not meta["session_uuid"]:
        return "skipped"

    project_name = extract_project_name(project_hash)

    # NUL-Zeichen aus Content entfernen (kommt in manchen JSONL vor)
    for m in messages:
        if m.get("content"):
            m["content"] = m["content"].replace("\x00", "").replace("\\u0000", "")
        if m.get("content_json"):
            m["content_json"] = m["content_json"].replace("\x00", "").replace("\\u0000", "")

    if session_id:
        # Update bestehende Session
        execute("""
            UPDATE sessions SET
                account = %s, project_hash = %s, project_name = %s,
                cwd = %s, git_branch = %s, model = %s, claude_version = %s,
                slug = %s, started_at = %s, ended_at = %s, duration_ms = %s,
                user_message_count = %s, assistant_message_count = %s,
                total_input_tokens = %s, total_output_tokens = %s,
                jsonl_size = %s, jsonl_mtime = %s, updated_at = NOW()
            WHERE id = %s
        """, (
            account_name, project_hash, project_name,
            meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
            meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
            meta["user_message_count"], meta["assistant_message_count"],
            meta["total_input_tokens"], meta["total_output_tokens"],
            file_size, file_mtime, session_id
        ))
    else:
        # Neue Session einfuegen
        row = execute("""
            INSERT INTO sessions (
                session_uuid, account, project_hash, project_name,
                cwd, git_branch, model, claude_version, slug,
                started_at, ended_at, duration_ms,
                user_message_count, assistant_message_count,
                total_input_tokens, total_output_tokens,
                jsonl_path, jsonl_size, jsonl_mtime
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_uuid) DO UPDATE SET
                jsonl_size = EXCLUDED.jsonl_size, jsonl_mtime = EXCLUDED.jsonl_mtime,
                updated_at = NOW()
            RETURNING id
        """, (
            meta["session_uuid"], account_name, project_hash, project_name,
            meta["cwd"], meta["git_branch"], meta["model"], meta["claude_version"],
            meta["slug"], meta["started_at"], meta["ended_at"], meta["duration_ms"],
            meta["user_message_count"], meta["assistant_message_count"],
            meta["total_input_tokens"], meta["total_output_tokens"],
            filepath, file_size, file_mtime
        ), fetchone=True)
        session_id = row["id"]

    # Messages einfuegen
    if messages:
        msg_params = [
            (
                session_id, m["uuid"], m["parent_uuid"], m["type"],
                m["content"], m["content_json"], m["model"],
                m["input_tokens"], m["output_tokens"], m["duration_ms"],
                m["timestamp"], m["is_tool_result"]
            )
            for m in messages
        ]
        execute_many("""
            INSERT INTO messages (
                session_id, uuid, parent_uuid, type, content, content_json,
                model, input_tokens, output_tokens, duration_ms, timestamp, is_tool_result
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, msg_params)

    return "updated" if existing else "imported"


def find_sessions(config_dir):
    """Findet alle JSONL-Session-Dateien in einem Account-Verzeichnis"""
    projects_dir = os.path.join(config_dir, "projects")
    if not os.path.isdir(projects_dir):
        return []

    sessions = []
    for project_hash in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_hash)
        if not os.path.isdir(project_path):
            continue
        for filename in os.listdir(project_path):
            if filename.endswith(".jsonl") and not filename.startswith("agent-"):
                filepath = os.path.join(project_path, filename)
                sessions.append((filepath, project_hash))
        # Subagents-Verzeichnis ueberspringen
    return sessions


def sync_account(account):
    """Synchronisiert alle Sessions eines Accounts"""
    name = account["name"]
    config_dir = account["config_dir"]

    sessions = find_sessions(config_dir)
    stats = {"imported": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}

    for filepath, project_hash in sessions:
        try:
            result = import_session(filepath, name, project_hash)
            stats[result] = stats.get(result, 0) + 1
        except Exception as e:
            print(f"Fehler bei {filepath}: {e}")
            stats["errors"] += 1

    return stats


def sync_all():
    """Synchronisiert alle konfigurierten Accounts"""
    total_stats = {"imported": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}

    for account in CLAUDE_ACCOUNTS:
        print(f"Sync {account['name']}...")
        stats = sync_account(account)
        for k, v in stats.items():
            total_stats[k] = total_stats.get(k, 0) + v
        print(f"  {stats}")

    print(f"Gesamt: {total_stats}")
    return total_stats
