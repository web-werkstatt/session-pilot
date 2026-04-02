"""
SPEC-PROJECT-MEMORY-001: Project Memory Service.
Aggregiert Projekt-Kontext aus bestehenden Datenquellen (read-only).
"""
import os
import json
from datetime import datetime, timezone

from config import PROJECTS_DIR
from services.db_service import (
    execute,
    ensure_project_identity_schema,
    ensure_plans_schema,
    ensure_file_touch_schema,
    ensure_ai_scope_schema,
)
from services.project_scanner import load_project_json
from services.governance_service import get_project_policy


def _bootstrap_project(project_name):
    """Legt oder aktualisiert projects-Eintrag aus project.json / Filesystem."""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.isdir(project_path):
        return None

    data = load_project_json(project_path) or {}
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    policy = get_project_policy(project_name)
    policy_level = policy.get("level_name") if policy else None

    now = datetime.now(timezone.utc)
    row = execute("""
        INSERT INTO projects (name, path, category, topic, tags, status,
                              priority, project_type, ai_policy_level,
                              source_updated_at, updated_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET
            path = EXCLUDED.path,
            category = EXCLUDED.category,
            topic = EXCLUDED.topic,
            tags = EXCLUDED.tags,
            status = EXCLUDED.status,
            priority = EXCLUDED.priority,
            project_type = EXCLUDED.project_type,
            ai_policy_level = EXCLUDED.ai_policy_level,
            source_updated_at = EXCLUDED.source_updated_at,
            updated_at = EXCLUDED.updated_at
        RETURNING *
    """, (
        project_name,
        project_path,
        data.get("category") or None,
        data.get("topic") or None,
        json.dumps(tags),
        data.get("status") or None,
        data.get("priority") or None,
        data.get("project_type") or None,
        policy_level,
        now,
        now,
    ), fetchone=True)
    return row


def _get_session_summary(project_name):
    """Aggregiert Session-Statistiken fuer ein Projekt."""
    ensure_ai_scope_schema()
    row = execute("""
        SELECT
            COUNT(*) AS total_sessions,
            MAX(started_at) AS last_session_at,
            COALESCE(SUM(total_input_tokens), 0) AS total_input_tokens,
            COALESCE(SUM(total_output_tokens), 0) AS total_output_tokens
        FROM sessions
        WHERE project_name = %s
    """, (project_name,), fetchone=True)

    total = row["total_sessions"] if row and row["total_sessions"] else 0
    if total == 0:
        return {
            "total_sessions": 0,
            "last_session_at": None,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "top_models": [],
            "outcome_counts": {},
        }

    last_at = row["last_session_at"] if row else None
    if last_at:
        last_at = last_at.isoformat()

    top_models = execute("""
        SELECT model, COUNT(*) AS sessions
        FROM sessions
        WHERE project_name = %s AND model IS NOT NULL AND model != ''
        GROUP BY model
        ORDER BY sessions DESC
        LIMIT 5
    """, (project_name,), fetch=True) or []

    outcomes = execute("""
        SELECT outcome, COUNT(*) AS cnt
        FROM sessions
        WHERE project_name = %s AND outcome IS NOT NULL
        GROUP BY outcome
    """, (project_name,), fetch=True) or []

    return {
        "total_sessions": total,
        "last_session_at": last_at,
        "total_input_tokens": row["total_input_tokens"] if row else 0,
        "total_output_tokens": row["total_output_tokens"] if row else 0,
        "top_models": [{"model": m["model"], "sessions": m["sessions"]} for m in top_models],
        "outcome_counts": {o["outcome"]: o["cnt"] for o in outcomes},
    }


def _get_recent_plans(project_name, limit=10):
    """Liefert die neuesten Plans fuer ein Projekt."""
    ensure_plans_schema()
    rows = execute("""
        SELECT title, session_uuid, category, status, created_at
        FROM project_plans
        WHERE project_name = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (project_name, limit), fetch=True) or []

    return [
        {
            "title": r["title"],
            "session_uuid": r["session_uuid"],
            "category": r["category"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


def _get_file_activity(project_name, limit=10):
    """Aggregiert File-Touch-Statistiken."""
    ensure_file_touch_schema()
    total_row = execute("""
        SELECT COUNT(*) AS total_touches
        FROM ai_file_touches
        WHERE project = %s
    """, (project_name,), fetchone=True)

    total = total_row["total_touches"] if total_row else 0

    top_files = execute("""
        SELECT file_path, COUNT(*) AS touches
        FROM ai_file_touches
        WHERE project = %s
        GROUP BY file_path
        ORDER BY touches DESC
        LIMIT %s
    """, (project_name, limit), fetch=True) or []

    return {
        "total_touches": total,
        "top_touched_files": [
            {"file_path": f["file_path"], "touches": f["touches"]}
            for f in top_files
        ],
    }


def _get_handoffs(project_name):
    """Generiert/aktualisiert die eine handoff.md fuer dieses Projekt."""
    try:
        from services.project_handoff_service import write_handoff
        filepath, _ = write_handoff(project_name)
        if filepath is None:
            return []
        return [{"filepath": filepath, "exists": True, "generated": True}]
    except Exception:
        return []


def get_project_memory(project_name):
    """Aggregiert Project Memory aus allen verfuegbaren Quellen.

    Returns:
        dict mit project, metadata, governance, session_summary,
        recent_plans, file_activity -- oder None wenn Projekt unbekannt.
    """
    ensure_project_identity_schema()

    # Bootstrap: Eintrag anlegen/aktualisieren aus Filesystem
    project_path = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.isdir(project_path):
        return None

    proj = _bootstrap_project(project_name)
    if not proj:
        return None

    tags = proj["tags"]
    if isinstance(tags, str):
        tags = json.loads(tags)

    policy = get_project_policy(project_name)

    return {
        "project": {
            "name": proj["name"],
            "path": proj["path"],
        },
        "metadata": {
            "category": proj["category"],
            "topic": proj["topic"],
            "tags": tags,
            "project_type": proj["project_type"],
            "status": proj["status"],
            "priority": proj["priority"],
        },
        "governance": {
            "policy_level": policy.get("level_name") if policy else None,
        },
        "session_summary": _get_session_summary(project_name),
        "recent_plans": _get_recent_plans(project_name),
        "file_activity": _get_file_activity(project_name),
        "handoffs": _get_handoffs(project_name),
    }
