"""
Per-File AI-Touch-Extraktion und Analyse (Sprint 10).
Extrahiert Datei-Pfade aus Write/Edit/MultiEdit Tool-Calls in Session-Messages.
"""
import json
import os
from services.db_service import execute, execute_many, ensure_file_touch_schema

# Tool-Name -> Touch-Type Mapping
TOOL_TOUCH_MAP = {
    "Write": "write",
    "Edit": "edit",
    "MultiEdit": "edit",
    "NotebookEdit": "edit",
    "write": "write",
    "edit": "edit",
    "multi_edit": "edit",
    "notebook_edit": "edit",
    "Read": "read",
    "read": "read",
    "Glob": "read",
    "Grep": "read",
    "mcp__serena__create_text_file": "write",
    "mcp__serena__replace_content": "edit",
    "mcp__serena__replace_symbol_body": "edit",
    "mcp__serena__insert_after_symbol": "edit",
    "mcp__serena__insert_before_symbol": "edit",
}

# Felder die Dateipfade enthalten, je nach Tool
PATH_FIELDS = ("file_path", "path", "filePath", "filename")


def extract_file_path(tool_input):
    """Extrahiert Dateipfad aus Tool-Input-Dict."""
    if not isinstance(tool_input, dict):
        return None
    for field in PATH_FIELDS:
        val = tool_input.get(field)
        if val and isinstance(val, str) and ("/" in val or "\\" in val):
            return val
    return None


def normalize_path(file_path, cwd=None):
    """Normalisiert Dateipfad relativ zum Projekt-Root."""
    if not file_path:
        return None
    # Absolute Pfade unter /mnt/projects/ -> relative Pfade
    if file_path.startswith("/mnt/projects/"):
        parts = file_path[len("/mnt/projects/"):].split("/", 1)
        return parts[1] if len(parts) > 1 else parts[0]
    # Andere absolute Pfade mit cwd normalisieren
    if file_path.startswith("/") and cwd:
        try:
            return os.path.relpath(file_path, cwd)
        except ValueError:
            return file_path
    return file_path


def extract_file_touches(messages, cwd=None):
    """Extrahiert File-Touches aus einer Liste von Message-Dicts.

    Args:
        messages: Liste von Message-Dicts (mit type, content_json)
        cwd: Working Directory der Session (fuer Pfad-Normalisierung)

    Returns:
        Liste von Dicts: {file_path, touch_type, tool_name, timestamp}
    """
    touches = []

    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        content_json = msg.get("content_json")
        if not content_json:
            continue
        try:
            content = json.loads(content_json) if isinstance(content_json, str) else content_json
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(content, list):
            continue

        timestamp = msg.get("timestamp")

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool_name = block.get("name", "")
            touch_type = TOOL_TOUCH_MAP.get(tool_name)
            if not touch_type:
                continue
            tool_input = block.get("input", {})
            raw_path = extract_file_path(tool_input)
            if not raw_path:
                continue
            norm_path = normalize_path(raw_path, cwd)
            if norm_path:
                touches.append({
                    "file_path": norm_path,
                    "touch_type": touch_type,
                    "tool_name": tool_name,
                    "timestamp": timestamp,
                })

    return touches


def save_file_touches(session_id, touches):
    """Speichert File-Touches in die DB (loescht vorherige fuer die Session)."""
    ensure_file_touch_schema()
    execute("DELETE FROM ai_file_touches WHERE session_id = %s", (session_id,))
    if not touches:
        return 0
    params = [
        (session_id, t["file_path"], t["touch_type"], t["tool_name"], t.get("timestamp"))
        for t in touches
    ]
    execute_many(
        "INSERT INTO ai_file_touches (session_id, file_path, touch_type, tool_name, timestamp) "
        "VALUES (%s, %s, %s, %s, %s)",
        params,
    )
    return len(params)


def get_file_heatmap(project_name, limit=100):
    """Holt aggregierte File-Touch-Daten fuer ein Projekt.

    Returns:
        Liste von Dicts: {file_path, total, writes, edits, reads, sessions, last_touched}
    """
    ensure_file_touch_schema()
    return execute("""
        SELECT
            ft.file_path,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE ft.touch_type = 'write') AS writes,
            COUNT(*) FILTER (WHERE ft.touch_type = 'edit') AS edits,
            COUNT(*) FILTER (WHERE ft.touch_type = 'read') AS reads,
            COUNT(DISTINCT ft.session_id) AS sessions,
            MAX(ft.timestamp) AS last_touched
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE s.project_name = %s
        GROUP BY ft.file_path
        ORDER BY total DESC
        LIMIT %s
    """, (project_name, limit), fetch=True)


def get_risk_radar(project_name):
    """Berechnet Risk-Radar-Daten: Hotspots, Fehlerkategorien, Trends.

    Returns:
        Dict mit hotspots, error_categories, weekly_trend
    """
    ensure_file_touch_schema()

    # Top-Hotspots: Dateien mit den meisten Writes/Edits
    hotspots = execute("""
        SELECT
            ft.file_path,
            COUNT(*) FILTER (WHERE ft.touch_type IN ('write', 'edit')) AS changes,
            COUNT(DISTINCT ft.session_id) AS sessions,
            COUNT(*) FILTER (WHERE s.outcome = 'needs_fix') AS fix_sessions
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE s.project_name = %s AND ft.touch_type IN ('write', 'edit')
        GROUP BY ft.file_path
        ORDER BY changes DESC
        LIMIT 5
    """, (project_name,), fetch=True)

    # Fehler-Sessions pro Datei (Rework-Indikator)
    error_files = execute("""
        SELECT
            ft.file_path,
            COUNT(DISTINCT ft.session_id) AS error_sessions,
            COUNT(DISTINCT ft.session_id) FILTER (WHERE s.outcome = 'needs_fix') AS needs_fix,
            COUNT(DISTINCT ft.session_id) FILTER (WHERE s.outcome = 'reverted') AS reverted
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE s.project_name = %s
            AND s.outcome IN ('needs_fix', 'reverted')
            AND ft.touch_type IN ('write', 'edit')
        GROUP BY ft.file_path
        ORDER BY error_sessions DESC
        LIMIT 5
    """, (project_name,), fetch=True)

    # Woechentlicher Trend (letzte 8 Wochen)
    weekly_trend = execute("""
        SELECT
            date_trunc('week', ft.timestamp) AS week,
            COUNT(*) AS total_touches,
            COUNT(*) FILTER (WHERE ft.touch_type IN ('write', 'edit')) AS changes,
            COUNT(DISTINCT ft.session_id) AS sessions
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE s.project_name = %s
            AND ft.timestamp >= NOW() - INTERVAL '8 weeks'
        GROUP BY week
        ORDER BY week
    """, (project_name,), fetch=True)

    return {
        "hotspots": [dict(r) for r in hotspots] if hotspots else [],
        "error_files": [dict(r) for r in error_files] if error_files else [],
        "weekly_trend": [
            {
                "week": r["week"].isoformat() if r["week"] else None,
                "total_touches": r["total_touches"],
                "changes": r["changes"],
                "sessions": r["sessions"],
            }
            for r in (weekly_trend or [])
        ],
    }
