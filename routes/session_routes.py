"""
Flask-Routes fuer Claude Code Sessions
Review-Routes sind in session_review_routes.py ausgelagert.
"""
import time
import threading
from flask import Blueprint, render_template, jsonify, request, Response
from services.db_service import execute, ensure_session_review_schema
from services.session_import import sync_all
from services.session_export import (
    export_json, export_markdown, export_html, export_xlsx, export_txt,
    format_duration, format_tokens
)
from routes.session_review_routes import (
    load_project_review_threads, load_thread_sessions, _serialize_review
)

sessions_bp = Blueprint("sessions", __name__)

# Sync-Cooldown: max 1x pro Stunde automatisch
_last_sync_time = 0
_sync_lock = threading.Lock()
_sync_running = False
SYNC_COOLDOWN = 3600  # 1 Stunde


@sessions_bp.route("/sessions")
def sessions_page():
    return render_template("sessions.html", active_page="sessions")


@sessions_bp.route("/sessions/<uuid>")
def session_detail_page(uuid):
    return render_template("session_detail.html", session_uuid=uuid, active_page="sessions")


@sessions_bp.route("/api/sessions")
def api_sessions():
    """Session-Liste mit Filtern, triggert Auto-Sync im Hintergrund"""
    _try_background_sync()
    try:
        return _api_sessions_inner()
    except Exception as e:
        return jsonify({"error": f"Database error: {e}", "sessions": [], "total": 0}), 500


def _api_sessions_inner():
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
        "total_input_tokens", "total_output_tokens", "model", "git_branch", "outcome",
        "outcome_severity", "ai_has_writes", "ai_has_tool_calls"
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
        conditions.append("(project_name = %s OR project_name = %s OR cwd LIKE %s)")
        params.extend([project, project.replace('_', '-'), f"%/{project}"])
    if search:
        conditions.append("(project_name ILIKE %s OR slug ILIKE %s OR cwd ILIKE %s)")
        params.extend([f"%{search}%"] * 3)
    if date_from:
        conditions.append("started_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("started_at < %s::date + 1")
        params.append(date_to)

    # Sprint 9: Outcome + Scope Filter
    outcome_filter = request.args.get("outcome")
    if outcome_filter == "unrated":
        conditions.append("outcome IS NULL")
    elif outcome_filter:
        conditions.append("outcome = %s")
        params.append(outcome_filter)

    scope_filter = request.args.get("scope")
    if scope_filter == "writes":
        conditions.append("ai_has_writes = TRUE")
    elif scope_filter == "tools":
        conditions.append("ai_has_tool_calls = TRUE")
    elif scope_filter == "readonly":
        conditions.append("(ai_has_tool_calls = FALSE OR ai_has_tool_calls IS NULL)")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Total count
    total = execute(f"SELECT COUNT(*) as cnt FROM sessions {where}", params, fetchone=True)
    total_count = total["cnt"] if total else 0

    # Sessions laden
    sessions = execute(
        f"""SELECT session_uuid, account, project_name, project_hash, cwd, git_branch,
                   model, claude_version, slug, started_at, ended_at, duration_ms,
                   user_message_count, assistant_message_count,
                   total_input_tokens, total_output_tokens, outcome,
                   outcome_reason, outcome_severity,
                   ai_has_writes, ai_has_tool_calls, ai_tools_used
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
    try:
        return _api_sessions_stats_inner()
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


def _api_sessions_stats_inner():
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
    try:
        return _api_session_detail_inner(uuid)
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


def _api_session_detail_inner(uuid):
    ensure_session_review_schema()
    session = execute("SELECT * FROM sessions WHERE session_uuid = %s", (uuid,), fetchone=True)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    messages = execute(
        "SELECT * FROM messages WHERE session_id = %s ORDER BY timestamp ASC",
        (session["id"],), fetch=True
    )

    reviews = execute("""
        SELECT sr.id, sr.thread_id, rt.title AS thread_title, sr.outcome_snapshot, sr.note, sr.author, sr.created_at
        FROM session_reviews sr
        LEFT JOIN review_threads rt ON rt.id = sr.thread_id
        WHERE sr.session_id = %s
        ORDER BY sr.created_at DESC
    """, (session["id"],), fetch=True)

    project_threads = load_project_review_threads(session.get("project_name")) or []
    thread_ids = [row["thread_id"] for row in (reviews or []) if row.get("thread_id")]
    related_sessions = load_thread_sessions(thread_ids, session["id"]) if thread_ids else []

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

    review_rows = [_serialize_review(review) for review in (reviews or [])]

    threads = []
    for thread in (project_threads or []):
        row = dict(thread)
        row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
        row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
        row["last_activity"] = row["last_activity"].isoformat() if row.get("last_activity") else None
        threads.append(row)

    related = []
    for rel in (related_sessions or []):
        row = dict(rel)
        row["started_at"] = row["started_at"].isoformat() if row.get("started_at") else None
        row["duration_formatted"] = format_duration(row.get("duration_ms"))
        related.append(row)

    return jsonify({
        "session": s,
        "messages": msgs,
        "reviews": review_rows,
        "threads": threads,
        "related_sessions": related,
    })


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
        return jsonify({"error": f"Unknown format: {fmt}"}), 400

    export_fn, content_type = exporters[fmt]
    content, filename = export_fn(uuid)

    if content is None:
        return jsonify({"error": "Session not found"}), 404

    return Response(
        content,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@sessions_bp.route("/api/sessions/search")
def api_sessions_search():
    """Volltextsuche ueber Session-Message-Inhalte"""
    try:
        return _api_sessions_search_inner()
    except Exception as e:
        return jsonify({"error": f"Database error: {e}", "results": [], "total": 0}), 500


def _api_sessions_search_inner():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"error": "Search term must be at least 2 characters", "results": [], "total": 0}), 400

    account = request.args.get("account")
    project = request.args.get("project")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    limit = min(int(request.args.get("limit", 30)), 100)
    offset = int(request.args.get("offset", 0))

    words = query.split()
    conditions = []
    params = []

    for word in words:
        conditions.append("m.content ILIKE %s")
        params.append(f"%{word}%")

    if account:
        conditions.append("s.account = %s")
        params.append(account)
    if project:
        conditions.append("s.project_name = %s")
        params.append(project)
    if date_from:
        conditions.append("s.started_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("s.started_at < %s::date + 1")
        params.append(date_to)

    where = "WHERE " + " AND ".join(conditions)

    total = execute(f"""
        SELECT COUNT(DISTINCT s.id) as cnt
        FROM messages m JOIN sessions s ON m.session_id = s.id
        {where}
    """, params, fetchone=True)
    total_count = total["cnt"] if total else 0

    results = execute(f"""
        SELECT DISTINCT ON (s.id)
            s.session_uuid, s.account, s.project_name, s.started_at,
            s.duration_ms, s.model, s.git_branch, s.slug, s.outcome,
            s.user_message_count, s.assistant_message_count,
            s.total_input_tokens, s.total_output_tokens,
            m.type as match_type,
            SUBSTRING(m.content FROM GREATEST(1, POSITION(LOWER(%s) IN LOWER(m.content)) - 80) FOR 200) as snippet
        FROM messages m JOIN sessions s ON m.session_id = s.id
        {where}
        ORDER BY s.id, m.timestamp ASC
        LIMIT %s OFFSET %s
    """, [words[0]] + params + [limit, offset], fetch=True)

    result_list = []
    for r in (results or []):
        row = dict(r)
        row["started_at"] = row["started_at"].isoformat() if row.get("started_at") else None
        row["duration_formatted"] = format_duration(row.get("duration_ms"))
        row["tokens_formatted"] = f"{format_tokens(row.get('total_input_tokens'))} / {format_tokens(row.get('total_output_tokens'))}"
        result_list.append(row)

    result_list.sort(key=lambda x: x.get("started_at") or "", reverse=True)

    return jsonify({"results": result_list, "total": total_count, "query": query, "limit": limit, "offset": offset})


def _try_background_sync():
    """Startet Sync im Hintergrund wenn Cooldown abgelaufen"""
    global _last_sync_time, _sync_running
    now = time.time()
    if now - _last_sync_time < SYNC_COOLDOWN or _sync_running:
        return False

    with _sync_lock:
        if _sync_running:
            return False
        _sync_running = True

    def _do_sync():
        global _last_sync_time, _sync_running
        try:
            sync_all()
            _last_sync_time = time.time()
        except Exception as e:
            print(f"Background sync error: {e}")
        finally:
            _sync_running = False

    threading.Thread(target=_do_sync, daemon=True).start()
    return True


@sessions_bp.route("/api/sessions/sync", methods=["POST"])
def api_sessions_sync():
    """Manuellen Sync ausloesen"""
    global _last_sync_time, _sync_running
    force = request.args.get("force") == "1"

    if _sync_running:
        return jsonify({"success": False, "message": "Sync already running"})

    if not force and time.time() - _last_sync_time < SYNC_COOLDOWN:
        remaining = int(SYNC_COOLDOWN - (time.time() - _last_sync_time))
        return jsonify({"success": False, "message": f"Cooldown active, next sync in {remaining}s"})

    try:
        _sync_running = True
        stats = sync_all()
        _last_sync_time = time.time()
        _sync_running = False
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        _sync_running = False
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/api/sessions/sync/status")
def api_sessions_sync_status():
    """Status des Sync-Prozesses"""
    now = time.time()
    next_sync = max(0, int(SYNC_COOLDOWN - (now - _last_sync_time)))
    return jsonify({
        "running": _sync_running,
        "last_sync": int(_last_sync_time) if _last_sync_time else None,
        "next_sync_in": next_sync,
        "cooldown": SYNC_COOLDOWN,
    })
