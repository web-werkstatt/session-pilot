"""
Flask-Routes fuer Session-Reviews und Review-Threads
Extrahiert aus session_routes.py (Dateigroessen-Limit)
"""
from flask import Blueprint, jsonify, request
from services.db_service import execute, ensure_session_review_schema
from services.session_export import format_duration
from routes.api_utils import api_route

session_review_bp = Blueprint("session_reviews", __name__)


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


def load_project_review_threads(project_name):
    """Oeffentlich fuer session_routes.py Detail-API"""
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


def load_thread_sessions(thread_ids, current_session_id=None):
    """Oeffentlich fuer session_routes.py Detail-API"""
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


@session_review_bp.route("/api/sessions/<uuid>/outcome", methods=["POST"])
@api_route
def api_session_outcome(uuid):
    """Session-Outcome aktualisieren"""
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

    try:
        thread = _get_or_create_review_thread(session, data.get("thread_id"), data.get("thread_title"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

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


@session_review_bp.route("/api/sessions/<uuid>/reviews", methods=["POST"])
@api_route
def api_session_review_add(uuid):
    """Review-Notiz zu einer Session hinzufuegen"""
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

    try:
        thread = _get_or_create_review_thread(session, data.get("thread_id"), data.get("thread_title"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

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


@session_review_bp.route("/api/review-threads", methods=["POST"])
@api_route
def api_review_thread_create():
    """Projektbezogenen Review-Thread anlegen oder wiederverwenden"""
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


@session_review_bp.route("/api/sessions/bulk-outcome", methods=["POST"])
@api_route
def api_sessions_bulk_outcome():
    """Mehrere Sessions gleichzeitig bewerten"""
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
