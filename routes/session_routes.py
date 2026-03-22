"""
Flask-Routes fuer Claude Code Sessions
"""
from flask import Blueprint, render_template, jsonify, request, Response
from services.db_service import execute, ensure_session_review_schema
from services.session_import import sync_all
from services.session_export import (
    export_json, export_markdown, export_html, export_xlsx, export_txt,
    format_duration, format_tokens
)

sessions_bp = Blueprint("sessions", __name__)


def _serialize_review(row):
    data = dict(row)
    data["created_at"] = data["created_at"].isoformat() if data.get("created_at") else None
    return data


def _get_session_row(uuid):
    return execute("SELECT * FROM sessions WHERE session_uuid = %s", (uuid,), fetchone=True)


def _get_or_create_review_thread(session_row, thread_id=None, thread_title=None):
    if thread_id:
        thread = execute("SELECT * FROM review_threads WHERE id = %s", (thread_id,), fetchone=True)
        if not thread:
            raise ValueError("Review-Thread nicht gefunden")
        return thread

    title = (thread_title or "").strip()
    if not title:
        return None

    existing = execute(
        "SELECT * FROM review_threads WHERE project_name IS NOT DISTINCT FROM %s AND LOWER(title) = LOWER(%s) ORDER BY updated_at DESC LIMIT 1",
        (session_row.get("project_name"), title), fetchone=True
    )
    if existing:
        return existing

    execute(
        "INSERT INTO review_threads (project_name, title) VALUES (%s, %s)",
        (session_row.get("project_name"), title)
    )
    return execute(
        "SELECT * FROM review_threads WHERE project_name IS NOT DISTINCT FROM %s AND LOWER(title) = LOWER(%s) ORDER BY id DESC LIMIT 1",
        (session_row.get("project_name"), title), fetchone=True
    )


def _touch_review_thread(thread_id):
    if not thread_id:
        return
    execute("UPDATE review_threads SET updated_at = NOW() WHERE id = %s", (thread_id,))


def _load_project_review_threads(project_name):
    return execute("""
        SELECT t.id, t.title, t.status, t.project_name, t.created_at, t.updated_at,
               COUNT(DISTINCT sr.session_id) AS session_count,
               COUNT(sr.id) AS note_count,
               MAX(sr.created_at) AS last_activity
        FROM review_threads t
        LEFT JOIN session_reviews sr ON sr.thread_id = t.id
        WHERE t.project_name IS NOT DISTINCT FROM %s
        GROUP BY t.id
        ORDER BY COALESCE(MAX(sr.created_at), t.updated_at) DESC, t.id DESC
    """, (project_name,), fetch=True)


def _load_thread_sessions(thread_ids, current_session_id=None):
    if not thread_ids:
        return []
    return execute("""
        SELECT DISTINCT ON (t.id, s.id)
               t.id AS thread_id,
               t.title AS thread_title,
               s.session_uuid,
               s.project_name,
               s.started_at,
               s.duration_ms,
               s.outcome
        FROM review_threads t
        JOIN session_reviews sr ON sr.thread_id = t.id
        JOIN sessions s ON s.id = sr.session_id
        WHERE t.id = ANY(%s) AND (%s IS NULL OR s.id <> %s)
        ORDER BY t.id, s.id, sr.created_at DESC
    """, (thread_ids, current_session_id, current_session_id), fetch=True)


@sessions_bp.route("/sessions")
def sessions_page():
    return render_template("sessions.html", active_page="sessions")


@sessions_bp.route("/sessions/<uuid>")
def session_detail_page(uuid):
    return render_template("session_detail.html", session_uuid=uuid, active_page="sessions")


@sessions_bp.route("/api/sessions")
def api_sessions():
    """Session-Liste mit Filtern"""
    try:
        return _api_sessions_inner()
    except Exception as e:
        return jsonify({"error": f"Datenbankfehler: {e}", "sessions": [], "total": 0}), 500


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
        "total_input_tokens", "total_output_tokens", "model", "git_branch", "outcome"
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
                   total_input_tokens, total_output_tokens, outcome
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
        return jsonify({"error": f"Datenbankfehler: {e}"}), 500


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
        return jsonify({"error": f"Datenbankfehler: {e}"}), 500


def _api_session_detail_inner(uuid):
    ensure_session_review_schema()
    session = _get_session_row(uuid)
    if not session:
        return jsonify({"error": "Session nicht gefunden"}), 404

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

    project_threads = _load_project_review_threads(session.get("project_name")) or []
    thread_ids = [row["thread_id"] for row in (reviews or []) if row.get("thread_id")]
    related_sessions = _load_thread_sessions(thread_ids, session["id"]) if thread_ids else []

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


@sessions_bp.route("/api/sessions/<uuid>/outcome", methods=["POST"])
def api_session_outcome(uuid):
    """Session-Outcome aktualisieren"""
    try:
        ensure_session_review_schema()
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON Body erforderlich"}), 400

        outcome = data.get("outcome")
        allowed = {"ok", "needs_fix", "reverted", "partial", None}
        if outcome not in allowed:
            return jsonify({"error": f"Ungueltiger Outcome: {outcome}"}), 400

        note = (data.get("note") or "").strip()
        session = _get_session_row(uuid)
        if not session:
            return jsonify({"error": "Session nicht gefunden"}), 404

        thread = _get_or_create_review_thread(session, data.get("thread_id"), data.get("thread_title"))
        execute("""
            UPDATE sessions SET outcome = %s, outcome_note = %s, outcome_at = NOW()
            WHERE session_uuid = %s
        """, (outcome, note or None, uuid))

        if note:
            execute("""
                INSERT INTO session_reviews (session_id, thread_id, outcome_snapshot, note, author)
                VALUES (%s, %s, %s, %s, %s)
            """, (session["id"], thread["id"] if thread else None, outcome, note, data.get("author") or "local"))
            _touch_review_thread(thread["id"] if thread else None)

        return jsonify({"success": True, "thread_id": thread["id"] if thread else None})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@sessions_bp.route("/api/sessions/<uuid>/reviews", methods=["POST"])
def api_session_review_add(uuid):
    """Review-Notiz zu einer Session hinzufuegen"""
    try:
        ensure_session_review_schema()
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON Body erforderlich"}), 400

        note = (data.get("note") or "").strip()
        if not note:
            return jsonify({"error": "Notiz erforderlich"}), 400

        outcome = data.get("outcome")
        allowed = {"ok", "needs_fix", "reverted", "partial", None}
        if outcome not in allowed:
            return jsonify({"error": f"Ungueltiger Outcome: {outcome}"}), 400

        session = _get_session_row(uuid)
        if not session:
            return jsonify({"error": "Session nicht gefunden"}), 404

        thread = _get_or_create_review_thread(session, data.get("thread_id"), data.get("thread_title"))

        execute("""
            INSERT INTO session_reviews (session_id, thread_id, outcome_snapshot, note, author)
            VALUES (%s, %s, %s, %s, %s)
        """, (session["id"], thread["id"] if thread else None, outcome, note, data.get("author") or "local"))
        _touch_review_thread(thread["id"] if thread else None)

        if outcome is not None:
            execute("""
                UPDATE sessions SET outcome = %s, outcome_note = %s, outcome_at = NOW()
                WHERE session_uuid = %s
            """, (outcome, note, uuid))

        review = execute("""
            SELECT sr.id, sr.thread_id, rt.title AS thread_title, sr.outcome_snapshot, sr.note, sr.author, sr.created_at
            FROM session_reviews sr
            LEFT JOIN review_threads rt ON rt.id = sr.thread_id
            WHERE sr.session_id = %s
            ORDER BY sr.created_at DESC
            LIMIT 1
        """, (session["id"],), fetchone=True)
        return jsonify({"success": True, "review": _serialize_review(review), "thread_id": thread["id"] if thread else None})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/api/review-threads", methods=["POST"])
def api_review_thread_create():
    """Projektbezogenen Review-Thread anlegen oder wiederverwenden"""
    try:
        ensure_session_review_schema()
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON Body erforderlich"}), 400
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Titel erforderlich"}), 400

        project_name = data.get("project_name")
        existing = execute(
            "SELECT * FROM review_threads WHERE project_name IS NOT DISTINCT FROM %s AND LOWER(title) = LOWER(%s) ORDER BY updated_at DESC LIMIT 1",
            (project_name, title), fetchone=True
        )
        if existing:
            row = dict(existing)
            row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
            row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
            return jsonify({"success": True, "thread": row})

        execute("INSERT INTO review_threads (project_name, title) VALUES (%s, %s)", (project_name, title))
        thread = execute(
            "SELECT * FROM review_threads WHERE project_name IS NOT DISTINCT FROM %s AND LOWER(title) = LOWER(%s) ORDER BY id DESC LIMIT 1",
            (project_name, title), fetchone=True
        )
        row = dict(thread)
        row["created_at"] = row["created_at"].isoformat() if row.get("created_at") else None
        row["updated_at"] = row["updated_at"].isoformat() if row.get("updated_at") else None
        return jsonify({"success": True, "thread": row})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@sessions_bp.route("/api/sessions/bulk-outcome", methods=["POST"])
def api_sessions_bulk_outcome():
    """Mehrere Sessions gleichzeitig bewerten"""
    try:
        data = request.get_json()
        uuids = data.get("uuids", [])
        outcome = data.get("outcome")

        if not uuids:
            return jsonify({"error": "uuids erforderlich"}), 400
        allowed = {"ok", "needs_fix", "reverted", "partial", None}
        if outcome not in allowed:
            return jsonify({"error": f"Ungueltiger Outcome: {outcome}"}), 400

        for uuid in uuids:
            execute("""
                UPDATE sessions SET outcome = %s, outcome_at = NOW()
                WHERE session_uuid = %s
            """, (outcome, uuid))

        return jsonify({"success": True, "count": len(uuids)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/api/sessions/search")
def api_sessions_search():
    """Volltextsuche ueber Session-Message-Inhalte"""
    try:
        return _api_sessions_search_inner()
    except Exception as e:
        return jsonify({"error": f"Datenbankfehler: {e}", "results": [], "total": 0}), 500


def _api_sessions_search_inner():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"error": "Suchbegriff muss mindestens 2 Zeichen haben", "results": [], "total": 0}), 400

    account = request.args.get("account")
    project = request.args.get("project")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    limit = min(int(request.args.get("limit", 30)), 100)
    offset = int(request.args.get("offset", 0))

    words = query.split()
    conditions = []
    params = []

    # Alle Woerter muessen in derselben Message vorkommen, ODER
    # bei einem einzelnen Wort: einfach ILIKE
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

    # Anzahl betroffener Sessions
    total = execute(f"""
        SELECT COUNT(DISTINCT s.id) as cnt
        FROM messages m JOIN sessions s ON m.session_id = s.id
        {where}
    """, params, fetchone=True)
    total_count = total["cnt"] if total else 0

    # Sessions mit Treffer-Snippets laden
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

    # Nach Datum sortieren (neueste zuerst)
    result_list.sort(key=lambda x: x.get("started_at") or "", reverse=True)

    return jsonify({"results": result_list, "total": total_count, "query": query, "limit": limit, "offset": offset})


@sessions_bp.route("/api/sessions/sync", methods=["POST"])
def api_sessions_sync():
    """Manuellen Sync ausloesen"""
    try:
        stats = sync_all()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
