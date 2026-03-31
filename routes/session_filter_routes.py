"""
Flask-Routes fuer Session-Filter und erweiterte Outcome-Felder (Sprint 9).
Eigenes Modul: Filter-Logik, Outcome-Reasons, AI-Scope-Filter.
"""
from flask import Blueprint, jsonify, request
from services.db_service import execute, ensure_ai_scope_schema, ensure_session_review_schema
from routes.api_utils import api_route

session_filter_bp = Blueprint("session_filters", __name__)

# Vordefinierte Outcome-Reasons (erweiterbar)
OUTCOME_REASONS = {
    "needs_fix": [
        "syntax_error", "wrong_file", "incomplete", "wrong_approach",
        "missing_import", "test_failure", "type_error", "logic_error",
    ],
    "reverted": [
        "broke_existing", "wrong_scope", "not_requested", "regression",
        "performance_issue",
    ],
    "partial": [
        "needs_followup", "incomplete_refactor", "manual_fix_needed",
        "missing_tests",
    ],
}

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]


@session_filter_bp.route("/api/sessions/outcome-reasons")
@api_route
def api_outcome_reasons():
    """Gibt vordefinierte Outcome-Reasons und Severity-Levels zurueck"""
    return jsonify({
        "reasons": OUTCOME_REASONS,
        "severities": SEVERITY_LEVELS,
    })


@session_filter_bp.route("/api/sessions/filters")
@api_route
def api_session_filters():
    """Gibt dynamische Filter-Optionen zurueck (aus DB aggregiert)"""
    ensure_ai_scope_schema()
    ensure_session_review_schema()

    accounts = execute(
        "SELECT DISTINCT account FROM sessions WHERE account IS NOT NULL ORDER BY account",
        fetch=True
    )
    projects = execute(
        "SELECT DISTINCT project_name FROM sessions WHERE project_name IS NOT NULL AND project_name != 'home' AND project_name != 'gemini_sessions' ORDER BY project_name",
        fetch=True
    )
    models = execute(
        "SELECT DISTINCT model FROM sessions WHERE model IS NOT NULL AND model != '' AND model NOT LIKE '<%>' ORDER BY model",
        fetch=True
    )
    outcomes = execute(
        "SELECT outcome, COUNT(*) as cnt FROM sessions GROUP BY outcome ORDER BY outcome",
        fetch=True
    )
    # AI-Scope-Statistiken
    scope_stats = execute("""
        SELECT
            COUNT(*) FILTER (WHERE ai_has_tool_calls = TRUE) AS with_tools,
            COUNT(*) FILTER (WHERE ai_has_writes = TRUE) AS with_writes,
            COUNT(*) FILTER (WHERE ai_has_tool_calls = FALSE OR ai_has_tool_calls IS NULL) AS read_only,
            COUNT(*) AS total
        FROM sessions
    """, fetchone=True)

    return jsonify({
        "accounts": [r["account"] for r in accounts],
        "projects": [r["project_name"] for r in projects],
        "models": [r["model"] for r in models],
        "outcomes": {r["outcome"] or "unrated": r["cnt"] for r in outcomes},
        "scope": dict(scope_stats) if scope_stats else {},
    })


@session_filter_bp.route("/api/sessions/<uuid>/outcome-detail", methods=["POST"])
@api_route
def api_session_outcome_detail(uuid):
    """Erweitert Outcome um reason + severity (Sprint 9)"""
    ensure_ai_scope_schema()
    ensure_session_review_schema()
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON Body erforderlich"}), 400

    reason = data.get("reason")
    severity = data.get("severity")

    if severity and severity not in SEVERITY_LEVELS:
        return jsonify({"error": f"Ungueltige Severity: {severity}"}), 400

    session = execute("SELECT id FROM sessions WHERE session_uuid = %s", (uuid,), fetchone=True)
    if not session:
        return jsonify({"error": "Session nicht gefunden"}), 404

    execute("""
        UPDATE sessions SET outcome_reason = %s, outcome_severity = %s
        WHERE session_uuid = %s
    """, (reason, severity, uuid))

    return jsonify({"success": True})


@session_filter_bp.route("/api/sessions/scope-stats")
@api_route
def api_scope_stats():
    """AI-Scope-Statistiken: Tool-Nutzung, Write-Anteil, haeufigste Tools"""
    ensure_ai_scope_schema()

    stats = execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE ai_has_tool_calls = TRUE) AS with_tools,
            COUNT(*) FILTER (WHERE ai_has_writes = TRUE) AS with_writes,
            COUNT(*) FILTER (WHERE outcome = 'needs_fix') AS needs_fix,
            COUNT(*) FILTER (WHERE outcome = 'needs_fix' AND ai_has_writes = TRUE) AS needs_fix_with_writes
        FROM sessions
    """, fetchone=True)

    # Top-Tools aggregieren (aus JSONB-Array)
    top_tools = execute("""
        SELECT tool, COUNT(*) AS cnt
        FROM sessions, jsonb_array_elements_text(ai_tools_used) AS tool
        WHERE ai_tools_used != '[]'::jsonb
        GROUP BY tool
        ORDER BY cnt DESC
        LIMIT 20
    """, fetch=True)

    return jsonify({
        "stats": dict(stats) if stats else {},
        "top_tools": [{"tool": r["tool"], "count": r["cnt"]} for r in top_tools],
    })
