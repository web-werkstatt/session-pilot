"""
Per-File AI-Touch-Extraktion und Analyse (Sprint 10).
Extrahiert Datei-Pfade aus Write/Edit/MultiEdit Tool-Calls in Session-Messages.
Fallback: Git-Diff-Analyse fuer Sessions ohne explizite Tool-Calls.
"""
import json
import logging
import os
import subprocess
from services.db_service import execute, execute_many, ensure_file_touch_schema

log = logging.getLogger(__name__)

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

# Tools die als ai_written=True zaehlen (aktive Datei-Aenderungen)
WRITE_TOOLS = frozenset(
    name for name, ttype in TOOL_TOUCH_MAP.items() if ttype in ("write", "edit")
)

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
                    "ai_written": tool_name in WRITE_TOOLS,
                    "ai_touched": True,
                    "timestamp": timestamp,
                })

    return touches


def extract_file_touches_git(cwd, started_at, ended_at):
    """Fallback: Extrahiert geaenderte Dateien via git log im Session-Zeitraum.

    Fuer Sessions ohne explizite Tool-Call-Daten.
    Heuristik: Commits waehrend Session-Zeitraum = AI-Aenderungen.
    """
    if not cwd or not os.path.isdir(os.path.join(cwd, ".git")):
        return []
    if not started_at or not ended_at:
        return []

    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", "--diff-filter=ACMR",
             f"--after={started_at}", f"--before={ended_at}"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []

        touches = []
        seen = set()
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line or line in seen:
                continue
            seen.add(line)
            touches.append({
                "file_path": line,
                "touch_type": "modified",
                "tool_name": "git-diff",
                "ai_written": True,
                "ai_touched": True,
                "timestamp": ended_at,
            })
        return touches
    except (subprocess.TimeoutExpired, OSError) as e:
        log.warning("Git-Diff-Fallback fehlgeschlagen fuer %s: %s", cwd, e)
        return []


def save_file_touches(session_id, touches, project="", model=None):
    """Speichert File-Touches in die DB (loescht vorherige fuer die Session).

    Args:
        session_id: DB-ID der Session
        touches: Liste von extract_file_touches()
        project: Projektname (fuer direkte Aggregation ohne Join)
        model: Modellname der Session
    """
    ensure_file_touch_schema()
    if not touches:
        execute("DELETE FROM ai_file_touches WHERE session_id = %s", (session_id,))
        return 0
    params = [
        (session_id, t["file_path"], project, t["touch_type"],
         t.get("ai_written", False), t.get("ai_touched", True),
         t["tool_name"], model, t.get("timestamp"))
        for t in touches
    ]
    execute_many(
        "INSERT INTO ai_file_touches "
        "(session_id, file_path, project, touch_type, ai_written, ai_touched, "
        "tool_name, model, timestamp) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (session_id, file_path, touch_type) DO UPDATE SET "
        "ai_written = EXCLUDED.ai_written, ai_touched = EXCLUDED.ai_touched, "
        "tool_name = EXCLUDED.tool_name, model = EXCLUDED.model, "
        "project = EXCLUDED.project, timestamp = EXCLUDED.timestamp",
        params,
    )
    return len(params)


def _build_heatmap_where(project_name, period, only_written, model, category):
    """Baut WHERE-Klausel fuer Heatmap-Queries."""
    conditions = ["ft.project = %s"]
    params = [project_name]
    period_map = {"30d": "30 days", "90d": "90 days", "365d": "365 days"}
    if period in period_map:
        conditions.append(f"ft.timestamp > NOW() - INTERVAL '{period_map[period]}'")
    if only_written:
        conditions.append("ft.ai_written = TRUE")
    if model:
        conditions.append("ft.model = %s")
        params.append(model)
    if category:
        conditions.append("ft.issue_category = %s")
        params.append(category)
    return " AND ".join(conditions), params


def get_file_heatmap(project_name, period="30d", depth=2, model=None,
                     category=None, only_written=True, limit=100):
    """Holt aggregierte File-Touch-Daten fuer ein Projekt (Spec 10.3).

    Aggregiert in SQL via split_part nach Verzeichnistiefe.
    Liefert dict mit 'dirs' (Verzeichnis-Aggregation) und 'files' (Einzeldateien).
    """
    ensure_file_touch_schema()
    where, params = _build_heatmap_where(project_name, period, only_written, model, category)

    # Verzeichnis-Aggregation in SQL (split_part)
    if depth and depth > 0:
        # depth=1 -> split_part(file_path,'/',1), depth=2 -> erste 2 Segmente
        # Fuer depth>1 brauchen wir array_to_string + string_to_array
        depth_expr = (
            f"array_to_string((string_to_array(ft.file_path, '/'))[1:{depth}], '/')"
        )
    else:
        depth_expr = "ft.file_path"

    dir_params = params + [limit]
    dirs = execute(f"""
        SELECT
            {depth_expr} AS dir,
            COUNT(*) AS touches,
            COUNT(DISTINCT ft.session_id) AS sessions,
            COUNT(*) FILTER (WHERE s.outcome = 'ok') AS ok_count,
            COUNT(*) FILTER (WHERE s.outcome = 'needs_fix') AS needs_fix_count,
            COUNT(*) FILTER (WHERE s.outcome = 'reverted') AS reverted_count
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE {where}
        GROUP BY dir
        ORDER BY touches DESC
        LIMIT %s
    """, dir_params, fetch=True)

    # Einzeldateien mit Modell-Verteilung (Children der Verzeichnisse)
    file_params = params + [limit * 5]
    files = execute(f"""
        SELECT
            ft.file_path,
            {depth_expr} AS dir,
            COUNT(*) AS touches,
            COUNT(DISTINCT ft.session_id) AS sessions,
            MAX(ft.timestamp) AS last_touched,
            COUNT(*) FILTER (WHERE s.outcome = 'ok') AS ok_count,
            COUNT(*) FILTER (WHERE s.outcome = 'needs_fix') AS needs_fix_count,
            COUNT(*) FILTER (WHERE s.outcome = 'reverted') AS reverted_count,
            (SELECT jsonb_object_agg(sub.m, sub.c) FROM (
                SELECT ft2.model AS m, COUNT(*) AS c
                FROM ai_file_touches ft2
                WHERE ft2.file_path = ft.file_path AND ft2.project = %s
                    AND ft2.model IS NOT NULL
                GROUP BY ft2.model
            ) sub) AS models,
            MODE() WITHIN GROUP (ORDER BY s.outcome_reason)
                FILTER (WHERE s.outcome_reason IS NOT NULL) AS top_reason
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE {where}
        GROUP BY ft.file_path, dir
        ORDER BY touches DESC
        LIMIT %s
    """, [project_name] + file_params, fetch=True)

    return {"dirs": dirs or [], "files": files or []}


def get_risk_radar(project_name):
    """Berechnet Risk-Radar-Daten: Hotspots, Fehlerkategorien, Trends (Spec 10.5).

    Returns:
        Dict mit hotspot_files, top_categories, trend
    """
    ensure_file_touch_schema()

    # Top-Hotspot-Dateien (hohe AI-Aktivitaet + Rework)
    hotspots = execute("""
        SELECT
            ft.file_path,
            COUNT(*) AS touches_30d,
            COUNT(DISTINCT ft.session_id) AS sessions,
            COUNT(*) FILTER (WHERE s.outcome IN ('needs_fix', 'reverted')) AS rework_count,
            AVG(CASE s.outcome_severity
                WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                WHEN 'medium' THEN 2 WHEN 'low' THEN 3
            END) FILTER (WHERE s.outcome_severity IS NOT NULL) AS avg_severity,
            MODE() WITHIN GROUP (ORDER BY s.outcome_reason)
                FILTER (WHERE s.outcome_reason IS NOT NULL) AS top_reason
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE ft.project = %s
            AND ft.ai_written = TRUE
            AND ft.timestamp > NOW() - INTERVAL '30 days'
            AND s.outcome IN ('needs_fix', 'reverted')
        GROUP BY ft.file_path
        ORDER BY touches_30d DESC, avg_severity ASC NULLS LAST
        LIMIT 3
    """, (project_name,), fetch=True)

    # Top-Fehlerkategorien (letzte 30 Tage)
    categories = execute("""
        SELECT
            s.outcome_reason AS reason,
            COUNT(*) AS count
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE ft.project = %s
            AND ft.ai_written = TRUE
            AND s.outcome_reason IS NOT NULL
            AND ft.timestamp > NOW() - INTERVAL '30 days'
        GROUP BY s.outcome_reason
        ORDER BY count DESC
        LIMIT 5
    """, (project_name,), fetch=True)

    cat_total = sum(r["count"] for r in (categories or []))
    top_categories = [
        {"reason": r["reason"], "count": r["count"],
         "pct": round(r["count"] / cat_total * 100, 1) if cat_total else 0}
        for r in (categories or [])
    ]

    # Trend: Rework-Rate 7d vs 30d
    trend_data = execute("""
        SELECT
            COUNT(*) FILTER (WHERE ft.timestamp > NOW() - INTERVAL '7 days') AS total_7d,
            COUNT(*) FILTER (
                WHERE ft.timestamp > NOW() - INTERVAL '7 days'
                AND s.outcome IN ('needs_fix', 'reverted')
            ) AS rework_7d,
            COUNT(*) FILTER (WHERE ft.timestamp > NOW() - INTERVAL '30 days') AS total_30d,
            COUNT(*) FILTER (
                WHERE ft.timestamp > NOW() - INTERVAL '30 days'
                AND s.outcome IN ('needs_fix', 'reverted')
            ) AS rework_30d
        FROM ai_file_touches ft
        JOIN sessions s ON s.id = ft.session_id
        WHERE ft.project = %s AND ft.ai_written = TRUE
    """, (project_name,), fetch=True)

    trend = {"rework_rate_7d": 0, "rework_rate_30d": 0, "delta_pp": 0, "direction": "stable"}
    if trend_data and trend_data[0]:
        t = trend_data[0]
        rate_7d = round(t["rework_7d"] / t["total_7d"] * 100, 1) if t["total_7d"] else 0
        rate_30d = round(t["rework_30d"] / t["total_30d"] * 100, 1) if t["total_30d"] else 0
        delta = round(rate_7d - rate_30d, 1)
        trend = {
            "rework_rate_7d": rate_7d,
            "rework_rate_30d": rate_30d,
            "delta_pp": delta,
            "direction": "improving" if delta < -1 else ("worsening" if delta > 1 else "stable"),
        }

    return {
        "project": project_name,
        "hotspot_files": [
            {
                "path": r["file_path"],
                "touches_30d": r["touches_30d"],
                "avg_severity": round(r["avg_severity"], 1) if r["avg_severity"] is not None else None,
                "top_reason": r["top_reason"],
                "rework_rate": round(r["rework_count"] / r["touches_30d"] * 100, 1) if r["touches_30d"] else 0,
                "drill_down": f"/sessions?project={project_name}&file={r['file_path']}",
            }
            for r in (hotspots or [])
        ],
        "top_categories": top_categories,
        "trend": trend,
    }
