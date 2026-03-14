"""
Flask-Routes fuer Claude Code Sessions
"""
from flask import Blueprint, render_template, jsonify, request, Response
from services.db_service import execute
from services.session_import import sync_all
from services.session_export import (
    export_json, export_markdown, export_html, export_xlsx, export_txt,
    format_duration, format_tokens
)

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions")
def sessions_page():
    return render_template("sessions.html", active_page="sessions")


@sessions_bp.route("/sessions/<uuid>")
def session_detail_page(uuid):
    return render_template("session_detail.html", session_uuid=uuid, active_page="sessions")


@sessions_bp.route("/api/sessions")
def api_sessions():
    """Session-Liste mit Filtern"""
    account = request.args.get("account")
    project = request.args.get("project")
    search = request.args.get("search")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    sort = request.args.get("sort", "started_at")
    order = request.args.get("order", "desc")
    limit = min(int(request.args.get("limit", 50)), 500)
    offset = int(request.args.get("offset", 0))

    # Whitelist fuer Sort-Spalten
    allowed_sorts = {
        "started_at", "ended_at", "duration_ms", "project_name",
        "account", "user_message_count", "assistant_message_count",
        "total_input_tokens", "total_output_tokens", "model", "git_branch"
    }
    if sort not in allowed_sorts:
        sort = "started_at"
    if order not in ("asc", "desc"):
        order = "desc"

    conditions = []
    params = []

    if account:
        conditions.append("account = %s")
        params.append(account)
    if project:
        conditions.append("project_name = %s")
        params.append(project)
    if search:
        conditions.append("(project_name ILIKE %s OR slug ILIKE %s OR cwd ILIKE %s)")
        params.extend([f"%{search}%"] * 3)
    if date_from:
        conditions.append("started_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("started_at < %s::date + 1")
        params.append(date_to)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Total count
    total = execute(f"SELECT COUNT(*) as cnt FROM sessions {where}", params, fetchone=True)
    total_count = total["cnt"] if total else 0

    # Sessions laden
    sessions = execute(
        f"""SELECT session_uuid, account, project_name, project_hash, cwd, git_branch,
                   model, claude_version, slug, started_at, ended_at, duration_ms,
                   user_message_count, assistant_message_count,
                   total_input_tokens, total_output_tokens
            FROM sessions {where}
            ORDER BY {sort} {order}
            LIMIT %s OFFSET %s""",
        params + [limit, offset], fetch=True
    )

    result = []
    for s in (sessions or []):
        row = dict(s)
        row["started_at"] = row["started_at"].isoformat() if row.get("started_at") else None
        row["ended_at"] = row["ended_at"].isoformat() if row.get("ended_at") else None
        row["duration_formatted"] = format_duration(row.get("duration_ms"))
        row["tokens_formatted"] = f"{format_tokens(row.get('total_input_tokens'))} / {format_tokens(row.get('total_output_tokens'))}"
        result.append(row)

    return jsonify({"sessions": result, "total": total_count, "limit": limit, "offset": offset})


@sessions_bp.route("/api/sessions/stats")
def api_sessions_stats():
    """Aggregierte Statistiken"""
    stats = execute("""
        SELECT
            COUNT(*) as total_sessions,
            COUNT(DISTINCT account) as accounts,
            COUNT(DISTINCT project_name) as projects,
            SUM(duration_ms) as total_duration_ms,
            SUM(user_message_count) as total_user_messages,
            SUM(assistant_message_count) as total_assistant_messages,
            SUM(total_input_tokens) as total_input_tokens,
            SUM(total_output_tokens) as total_output_tokens
        FROM sessions
    """, fetchone=True)

    if not stats:
        stats = {}

    result = dict(stats)
    result["total_duration_formatted"] = format_duration(result.get("total_duration_ms"))
    result["total_input_formatted"] = format_tokens(result.get("total_input_tokens"))
    result["total_output_formatted"] = format_tokens(result.get("total_output_tokens"))

    # Top-Projekte
    top_projects = execute("""
        SELECT project_name, COUNT(*) as cnt, SUM(duration_ms) as total_dur
        FROM sessions
        WHERE project_name IS NOT NULL
        GROUP BY project_name
        ORDER BY cnt DESC
        LIMIT 10
    """, fetch=True)

    result["top_projects"] = [
        {"name": p["project_name"], "count": p["cnt"], "duration": format_duration(p["total_dur"])}
        for p in (top_projects or [])
    ]

    # Sessions pro Account
    account_stats = execute("""
        SELECT account, COUNT(*) as cnt
        FROM sessions GROUP BY account ORDER BY cnt DESC
    """, fetch=True)
    result["accounts"] = [dict(a) for a in (account_stats or [])]

    return jsonify(result)


@sessions_bp.route("/api/sessions/<uuid>")
def api_session_detail(uuid):
    """Einzelne Session mit Messages"""
    session = execute(
        "SELECT * FROM sessions WHERE session_uuid = %s", (uuid,), fetchone=True
    )
    if not session:
        return jsonify({"error": "Session nicht gefunden"}), 404

    messages = execute(
        "SELECT * FROM messages WHERE session_id = %s ORDER BY timestamp ASC",
        (session["id"],), fetch=True
    )

    s = dict(session)
    s["started_at"] = s["started_at"].isoformat() if s.get("started_at") else None
    s["ended_at"] = s["ended_at"].isoformat() if s.get("ended_at") else None
    s["imported_at"] = s["imported_at"].isoformat() if s.get("imported_at") else None
    s["updated_at"] = s["updated_at"].isoformat() if s.get("updated_at") else None
    s["duration_formatted"] = format_duration(s.get("duration_ms"))

    msgs = []
    for m in (messages or []):
        md = dict(m)
        md["timestamp"] = md["timestamp"].isoformat() if md.get("timestamp") else None
        msgs.append(md)

    return jsonify({"session": s, "messages": msgs})


@sessions_bp.route("/api/sessions/<uuid>/export")
def api_session_export(uuid):
    """Export einer Session"""
    fmt = request.args.get("format", "json")

    exporters = {
        "json": (export_json, "application/json"),
        "md": (export_markdown, "text/markdown"),
        "html": (export_html, "text/html"),
        "xlsx": (export_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "txt": (export_txt, "text/plain"),
    }

    if fmt not in exporters:
        return jsonify({"error": f"Unbekanntes Format: {fmt}"}), 400

    export_fn, content_type = exporters[fmt]
    content, filename = export_fn(uuid)

    if content is None:
        return jsonify({"error": "Session nicht gefunden"}), 404

    return Response(
        content,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@sessions_bp.route("/api/sessions/sync", methods=["POST"])
def api_sessions_sync():
    """Manuellen Sync ausloesen"""
    try:
        stats = sync_all()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
