"""
Gemeinsame Helfer fuer tool-spezifische Session-Importer.
"""
import os
from datetime import datetime, timezone
from config import PROJECTS_DIR
from services.db_service import execute_many


def insert_messages(session_id, messages):
    """Fuegt Messages in die DB ein."""
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


def millis_to_dt(value):
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def resolve_project_name_from_cwd(cwd):
    if not cwd:
        return None
    if PROJECTS_DIR in cwd:
        project_name = cwd.split(PROJECTS_DIR + "/")[-1].split("/")[0]
    else:
        project_name = os.path.basename(cwd.rstrip("/"))
    if not project_name:
        return None
    real_path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.isdir(real_path):
        alt = project_name.replace("-", "_")
        if os.path.isdir(os.path.join(PROJECTS_DIR, alt)):
            project_name = alt
    return project_name
