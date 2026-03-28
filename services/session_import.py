"""
JSONL-Parser und DB-Import fuer Claude Code Sessions.
Codex/Gemini-Parser sind in session_import_multi.py ausgelagert.
"""
import hashlib
import json
import os
from datetime import datetime
from services.db_service import execute, execute_many
from services.account_discovery import discover_all_accounts
from services.session_import_multi import (
    find_sessions_codex, import_codex_session,
    find_sessions_gemini, parse_gemini_json, import_gemini_session,
)

HASH_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".sync_hashes.json")

IMPORT_TYPES = {"user", "assistant", "system"}
IGNORE_TYPES = {"progress", "file-history-snapshot", "queue-operation", "last-prompt"}


def extract_project_name(project_hash):
    """Extrahiert Projektnamen aus Hash"""
    if not project_hash:
        return None
    if project_hash.startswith("gemini:"):
        return "~ Gemini Session"
    if len(project_hash) > 40 and all(c in '0123456789abcdef' for c in project_hash):
        return "~ Gemini Session"
    if project_hash.startswith("codex:"):
        name = project_hash.replace("codex:", "").replace("_", "-")
        return "~ (Home)" if not name or name in ("joshko",) else name
    if project_hash in ("-mnt-projects", "-home-joshko"):
        return "~ (Home)"
    if project_hash.startswith("-mnt-projects-"):
        name = project_hash[len("-mnt-projects-"):]
        return name.rstrip("/") if name else "~ (Home)"
    if project_hash.startswith("-home-joshko-"):
        name = project_hash[len("-home-joshko-"):]
        return name.rstrip("/") if name else "~ (Home)"
    return project_hash


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
        return any(isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result") for b in content)
    return False


def parse_jsonl(filepath):
    """Parsed eine Claude Code JSONL-Datei"""
    meta = {
        "session_uuid": None, "cwd": None, "git_branch": None,
        "model": None, "claude_version": None, "slug": None,
        "started_at": None, "ended_at": None, "duration_ms": 0,
        "user_message_count": 0, "assistant_message_count": 0,
        "total_input_tokens": 0, "total_output_tokens": 0,
        "cache_read_tokens": 0, "cache_creation_tokens": 0,
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
                if entry_type in IGNORE_TYPES or entry_type not in IMPORT_TYPES:
                    continue

                timestamp = _parse_ts(entry.get("timestamp"))

                if not meta["session_uuid"]:
                    meta["session_uuid"] = entry.get("sessionId")
                    meta["cwd"] = entry.get("cwd")
                    meta["git_branch"] = entry.get("gitBranch")
                    meta["claude_version"] = entry.get("version")

                if timestamp:
                    if not meta["started_at"] or timestamp < meta["started_at"]:
                        meta["started_at"] = timestamp
                    if not meta["ended_at"] or timestamp > meta["ended_at"]:
                        meta["ended_at"] = timestamp

                if entry.get("slug"):
                    meta["slug"] = entry["slug"]

                if entry_type == "system" and entry.get("subtype") == "turn_duration":
                    meta["duration_ms"] += entry.get("durationMs", 0)
                    messages.append({
                        "uuid": entry.get("uuid"), "parent_uuid": entry.get("parentUuid"),
                        "type": "system",
                        "content": f"Turn-Dauer: {entry.get('durationMs', 0)}ms",
                        "content_json": json.dumps({"subtype": "turn_duration", "durationMs": entry.get("durationMs", 0)}),
                        "model": None, "input_tokens": 0, "output_tokens": 0,
                        "duration_ms": entry.get("durationMs", 0), "timestamp": timestamp, "is_tool_result": False,
                    })
                    continue

                message = entry.get("message", {})
                role = message.get("role", entry_type)
                content = message.get("content", "")

                if role == "user":
                    meta["user_message_count"] += 1
                elif role == "assistant":
                    meta["assistant_message_count"] += 1
                    model = message.get("model")
                    if model:
                        meta["model"] = model
                    usage = message.get("usage", {})
                    meta["total_input_tokens"] += usage.get("input_tokens", 0)
                    meta["total_output_tokens"] += usage.get("output_tokens", 0)
                    meta["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
                    meta["cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)

                content_json = None
                if isinstance(content, list):
                    try:
                        content_json = json.dumps(content, ensure_ascii=False)
                    except (TypeError, ValueError):
                        pass

                messages.append({
                    "uuid": entry.get("uuid"), "parent_uuid": entry.get("parentUuid"),
                    "type": role, "content": extract_text_content(content),
                    "content_json": content_json, "model": message.get("model"),
                    "input_tokens": message.get("usage", {}).get("input_tokens", 0) if role == "assistant" else 0,
                    "output_tokens": message.get("usage", {}).get("output_tokens", 0) if role == "assistant" else 0,
                    "duration_ms": 0, "timestamp": timestamp, "is_tool_result": has_tool_use(content),
                })

    except Exception as e:
        print(f"Fehler beim Parsen von {filepath}: {e}")
        return None, []

    return meta, messages


def _parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def import_session(filepath, account_name, project_hash):
    """Importiert eine einzelne Claude Session in die Datenbank"""
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

    meta, messages = parse_jsonl(filepath)
    if not meta or not meta["session_uuid"]:
        return "skipped"

    project_name = extract_project_name(project_hash)

    for m in messages:
        if m.get("content"):
            m["content"] = m["content"].replace("\x00", "")
        if m.get("content_json"):
            # PostgreSQL jsonb akzeptiert keine \u0000 Null-Bytes
            s = m["content_json"].replace("\x00", "").replace("\\u0000", "")
            try:
                parsed = json.loads(s)
                result = json.dumps(parsed, ensure_ascii=True)
                result = result.replace("\\u0000", "")
                m["content_json"] = result
            except (json.JSONDecodeError, ValueError):
                m["content_json"] = None

    if session_id:
        execute("""
            UPDATE sessions SET
                account=%s, project_hash=%s, project_name=%s, cwd=%s, git_branch=%s,
                model=%s, claude_version=%s, slug=%s, started_at=%s, ended_at=%s,
                duration_ms=%s, user_message_count=%s, assistant_message_count=%s,
                total_input_tokens=%s, total_output_tokens=%s,
                cache_read_tokens=%s, cache_creation_tokens=%s,
                jsonl_size=%s, jsonl_mtime=%s, updated_at=NOW()
            WHERE id=%s
        """, (account_name, project_hash, project_name, meta["cwd"], meta["git_branch"],
              meta["model"], meta["claude_version"], meta["slug"],
              meta["started_at"], meta["ended_at"], meta["duration_ms"],
              meta["user_message_count"], meta["assistant_message_count"],
              meta["total_input_tokens"], meta["total_output_tokens"],
              meta.get("cache_read_tokens", 0), meta.get("cache_creation_tokens", 0),
              file_size, file_mtime, session_id))
    else:
        row = execute("""
            INSERT INTO sessions (session_uuid, account, project_hash, project_name,
                cwd, git_branch, model, claude_version, slug, started_at, ended_at,
                duration_ms, user_message_count, assistant_message_count,
                total_input_tokens, total_output_tokens, cache_read_tokens, cache_creation_tokens,
                jsonl_path, jsonl_size, jsonl_mtime)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
              filepath, file_size, file_mtime), fetchone=True)
        if not row:
            return "skipped"
        session_id = row["id"]

    if messages:
        # Sicherheitshalber immer alte Messages loeschen bevor neue eingefuegt werden
        execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
        msg_params = [(session_id, m["uuid"], m["parent_uuid"], m["type"],
                       m["content"], m["content_json"], m["model"],
                       m["input_tokens"], m["output_tokens"], m["duration_ms"],
                       m["timestamp"], m["is_tool_result"]) for m in messages]
        execute_many("""
            INSERT INTO messages (session_id, uuid, parent_uuid, type, content, content_json,
                model, input_tokens, output_tokens, duration_ms, timestamp, is_tool_result)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, msg_params)

    return "updated" if existing else "imported"


def find_sessions_claude(config_dir):
    """Findet alle JSONL-Session-Dateien in einem Claude Account-Verzeichnis"""
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
                sessions.append((os.path.join(project_path, filename), project_hash))
    return sessions


def _load_hash_cache():
    """Laedt lokale Hash-Cache-Datei (kein DB-Zugriff)"""
    try:
        with open(HASH_CACHE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_hash_cache(cache):
    """Speichert Hash-Cache atomar"""
    tmp = HASH_CACHE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f)
    os.replace(tmp, HASH_CACHE_PATH)


def _file_hash(filepath):
    """Berechnet schnellen Hash: MD5 ueber Dateigroesse + erste/letzte 8KB"""
    try:
        size = os.path.getsize(filepath)
        h = hashlib.md5(str(size).encode())
        with open(filepath, "rb") as f:
            h.update(f.read(8192))
            if size > 16384:
                f.seek(-8192, 2)
                h.update(f.read(8192))
        return h.hexdigest()
    except OSError:
        return None


def sync_account(account, hash_cache=None):
    """Synchronisiert alle Sessions eines Accounts (alle Tools)"""
    name = account["name"]
    config_dir = account["config_dir"]
    tool = account.get("tool", "claude")
    stats = {"imported": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}

    if hash_cache is None:
        hash_cache = _load_hash_cache()

    def _check_and_import(filepath, import_fn):
        """Prueft Hash und importiert nur bei Aenderung"""
        current_hash = _file_hash(filepath)
        if current_hash and hash_cache.get(filepath) == current_hash:
            stats["unchanged"] += 1
            return
        try:
            result = import_fn()
            stats[result] += 1
            if current_hash:
                hash_cache[filepath] = current_hash
        except Exception as e:
            print(f"Fehler bei {filepath}: {e}")
            stats["errors"] += 1

    if tool == "claude":
        for filepath, project_hash in find_sessions_claude(config_dir):
            _check_and_import(filepath, lambda fp=filepath, ph=project_hash: import_session(fp, name, ph))
    elif tool == "codex":
        for filepath, _ in find_sessions_codex(config_dir):
            _check_and_import(filepath, lambda fp=filepath: import_codex_session(fp, name))
    elif tool == "gemini":
        for filepath, project_hash in find_sessions_gemini(config_dir):
            current_hash = _file_hash(filepath)
            if current_hash and hash_cache.get(filepath) == current_hash:
                stats["unchanged"] += 1
                continue
            try:
                for meta, messages, phash in parse_gemini_json(filepath, project_hash):
                    stats[import_gemini_session(meta, messages, name, phash)] += 1
                if current_hash:
                    hash_cache[filepath] = current_hash
            except Exception as e:
                print(f"Fehler bei {filepath}: {e}")
                stats["errors"] += 1

    return stats


def sync_all():
    """Synchronisiert alle automatisch erkannten Accounts"""
    total_stats = {"imported": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}
    accounts = discover_all_accounts()

    if not accounts:
        print("Keine AI-Assistenten gefunden.")
        return total_stats

    hash_cache = _load_hash_cache()

    print(f"{len(accounts)} Account(s) erkannt, {len(hash_cache)} Hashes im Cache:")
    for acc in accounts:
        print(f"  {acc['name']} [{acc['tool']}] -> {acc['config_dir']}")

    for account in accounts:
        print(f"Sync {account['name']} [{account['tool']}]...")
        stats = sync_account(account, hash_cache=hash_cache)
        for k, v in stats.items():
            total_stats[k] = total_stats.get(k, 0) + v
        print(f"  {stats}")

    _save_hash_cache(hash_cache)
    print(f"Gesamt: {total_stats}")
    return total_stats
