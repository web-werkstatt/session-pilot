"""
SPEC-COPILOT-CHAT-PERPLEXITY-001: Copilot-Chat Routes.
POST /api/copilot/chat, GET /api/copilot/runs, POST /api/copilot/upload_image.
"""
import os
import uuid
from flask import Blueprint, jsonify, request, render_template
from services.copilot_service import call_copilot, list_copilot_runs

copilot_bp = Blueprint("copilot", __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "copilot")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}


@copilot_bp.route("/copilot")
def copilot_page():
    plan_id = request.args.get("plan_id", type=int)
    if plan_id:
        return render_template("copilot_board.html", active_page="copilot", plan_id=plan_id)
    # Ohne plan_id: Copilot-Startseite mit letzten Projekten
    return render_template("copilot_landing.html", active_page="copilot")


@copilot_bp.route("/api/copilot/stats")
def api_copilot_stats():
    """Statistiken fuer Copilot-Startseite: letzte Projekte, Plan/Section-Counts."""
    from services.db_service import execute, ensure_plans_schema
    try:
        ensure_plans_schema()
    except Exception:
        return jsonify({"recent_projects": [], "plans_total": 0, "plans_active": 0,
                        "sections_total": 0, "sections_done": 0})

    # Plan-Statistiken
    plan_stats = execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as active,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'draft') as draft
        FROM project_plans
    """, fetchone=True) or {}

    # Section-Statistiken
    sec_stats = {"total": 0, "done": 0, "in_progress": 0}
    try:
        sec_row = execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'done') as done,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress
            FROM plan_sections
        """, fetchone=True)
        if sec_row:
            sec_stats = dict(sec_row)
    except Exception:
        pass

    # Letzte Projekte: Projekte mit den neuesten Plans/Sessions
    recent = execute("""
        SELECT
            p.project_name,
            COUNT(*) as plan_count,
            COUNT(*) FILTER (WHERE p.status = 'active') as active_plans,
            COUNT(*) FILTER (WHERE p.status = 'completed') as done_plans,
            MAX(p.updated_at) as last_activity
        FROM project_plans p
        WHERE p.project_name IS NOT NULL
        GROUP BY p.project_name
        ORDER BY MAX(p.updated_at) DESC NULLS LAST
        LIMIT 10
    """, fetch=True) or []

    recent_projects = []
    for r in recent:
        recent_projects.append({
            "project_name": r["project_name"],
            "plan_count": r["plan_count"],
            "active_plans": r["active_plans"],
            "done_plans": r["done_plans"],
            "last_activity": r["last_activity"].isoformat() if r["last_activity"] else None,
        })

    # Aktive Plans mit Copilot-Link
    active_plans = execute("""
        SELECT id, title, project_name, status, updated_at
        FROM project_plans
        WHERE status IN ('active', 'draft')
        ORDER BY
            CASE WHEN status = 'active' THEN 0 ELSE 1 END,
            updated_at DESC NULLS LAST
        LIMIT 20
    """, fetch=True) or []

    plans_list = []
    for p in active_plans:
        plans_list.append({
            "id": p["id"],
            "title": p["title"],
            "project_name": p["project_name"],
            "status": p["status"],
            "updated_at": p["updated_at"].isoformat() if p["updated_at"] else None,
        })

    return jsonify({
        "plans_total": plan_stats.get("total", 0),
        "plans_active": plan_stats.get("active", 0),
        "plans_completed": plan_stats.get("completed", 0),
        "plans_draft": plan_stats.get("draft", 0),
        "sections_total": sec_stats.get("total", 0),
        "sections_done": sec_stats.get("done", 0),
        "sections_in_progress": sec_stats.get("in_progress", 0),
        "recent_projects": recent_projects,
        "active_plans": plans_list,
    })


@copilot_bp.route("/api/copilot/chat", methods=["POST"])
def api_copilot_chat():
    """Sendet eine Nachricht an den Copilot und speichert die Antwort."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request-Body muss JSON sein"}), 400

    message = data.get("message")
    if not message or not isinstance(message, str) or not message.strip():
        return jsonify({"error": "message ist erforderlich (nicht-leerer String)"}), 400

    project_id = data.get("project_id")
    thread_id = data.get("thread_id")
    context = data.get("context")
    plan_id = data.get("plan_id")
    images = data.get("images")

    if context is not None and not isinstance(context, dict):
        return jsonify({"error": "context muss ein Objekt sein oder null"}), 400
    if images is not None and not isinstance(images, list):
        return jsonify({"error": "images muss eine Liste sein oder null"}), 400

    try:
        result = call_copilot(
            message=message.strip(),
            project_id=project_id,
            thread_id=thread_id,
            context=context,
            plan_id=plan_id,
            images=images,
        )
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {str(e)}"}), 500

    status_code = 200 if result.get("status") == "success" else 422
    return jsonify(result), status_code


@copilot_bp.route("/api/copilot/runs")
def api_copilot_runs():
    """Laedt Copilot-Chat-Verlauf."""
    project_id = request.args.get("project_id")
    thread_id = request.args.get("thread_id")
    plan_id = request.args.get("plan_id", type=int)
    limit = request.args.get("limit", 50, type=int)

    try:
        runs = list_copilot_runs(
            project_id=project_id,
            thread_id=thread_id,
            plan_id=plan_id,
            limit=limit,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"runs": runs})


@copilot_bp.route("/api/copilot/upload_image", methods=["POST"])
def api_copilot_upload_image():
    """Laedt ein Bild hoch fuer Copilot-Chat (Sprint H, C4/C5)."""
    if "file" not in request.files:
        return jsonify({"error": "Kein file-Feld im Request"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Leerer Dateiname"}), 400

    mime = f.content_type or ""
    if mime not in ALLOWED_IMAGE_TYPES:
        return jsonify({"error": f"Nicht erlaubter Dateityp: {mime}. Erlaubt: PNG, JPG, GIF, WebP"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(f.filename)[1].lower() or ".png"
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    f.save(filepath)

    url = f"/static/uploads/copilot/{safe_name}"
    return jsonify({
        "filename": f.filename,
        "url": url,
        "mime_type": mime,
    })
