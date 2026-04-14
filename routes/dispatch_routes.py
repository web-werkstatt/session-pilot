"""
ADR-002 Stufe 2a: Dispatch REST-Endpoints.

Blueprint 'dispatch' mit CRUD, Pull-API (Variante B) und
Perplexity-Review/Suggest-Triggern.

Pull-API ist mit Bearer-Token geschuetzt (DISPATCH_PULL_API_KEY aus .env).
"""
import os
from functools import wraps

from flask import Blueprint, jsonify, request

from routes.api_utils import api_route

dispatch_bp = Blueprint("dispatch", __name__)


# ---------------------------------------------------------------------------
# Pull-API Auth
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    return os.environ.get("DISPATCH_PULL_API_KEY", "")


def require_pull_auth(f):
    """Bearer-Token-Check fuer Pull-API Endpoints."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = _get_api_key()
        if not api_key:
            return jsonify({"error": "Pull-API nicht konfiguriert"}), 503

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != api_key:
            return jsonify({"error": "Unauthorized"}), 401

        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/assignments", methods=["GET"])
@api_route
def list_assignments_api():
    """Gefilterte Assignment-Liste."""
    from services.dispatch_service import list_assignments

    project = request.args.get("project")
    status = request.args.get("status")
    tool = request.args.get("tool")
    limit = int(request.args.get("limit", 100))

    rows = list_assignments(
        project_name=project, status=status,
        executor_tool=tool, limit=limit,
    )
    return jsonify({"assignments": rows, "count": len(rows)})


@dispatch_bp.route("/api/dispatch/assignments/<int:aid>", methods=["GET"])
@api_route
def get_assignment_api(aid):
    """Einzelnes Assignment."""
    from services.dispatch_service import get_assignment

    row = get_assignment(aid)
    if not row:
        return jsonify({"error": "Nicht gefunden"}), 404
    return jsonify(row)


@dispatch_bp.route("/api/dispatch/assignments", methods=["POST"])
@api_route
def create_assignment_api():
    """Neues Assignment erstellen."""
    from services.dispatch_service import create_assignment

    body = request.get_json(silent=True) or {}

    required = ["project_name", "executor_tool"]
    for field in required:
        if not body.get(field):
            return jsonify({"error": f"Feld '{field}' fehlt"}), 400

    row = create_assignment(
        project_name=body["project_name"],
        executor_tool=body["executor_tool"],
        marker_id=body.get("marker_id"),
        role_id=body.get("role_id"),
        scope_ref=body.get("scope_ref"),
        input_payload=body.get("input_payload"),
        risk_level=body.get("risk_level", "medium"),
        automation_level=body.get("automation_level", 1),
        dispatch_mode=body.get("dispatch_mode", "manual"),
        approval_required=body.get("approval_required", True),
        allowed_write_scope=body.get("allowed_write_scope"),
        timeout_hours=body.get("timeout_hours"),
        created_by=body.get("created_by", "joseph"),
    )
    return jsonify(row), 201


# ---------------------------------------------------------------------------
# Lifecycle-Transitions
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/approve", methods=["POST"])
@api_route
def approve_api(aid):
    from services.dispatch_service import approve_assignment
    body = request.get_json(silent=True) or {}
    row = approve_assignment(aid, approved_by=body.get("approved_by", "joseph"))
    return jsonify(row)


@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/reject", methods=["POST"])
@api_route
def reject_api(aid):
    from services.dispatch_service import reject_assignment
    body = request.get_json(silent=True) or {}
    row = reject_assignment(
        aid,
        rejected_by=body.get("rejected_by", "joseph"),
        reason=body.get("reason"),
    )
    return jsonify(row)


@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/revoke", methods=["POST"])
@api_route
def revoke_api(aid):
    from services.dispatch_service import revoke_assignment
    body = request.get_json(silent=True) or {}
    row = revoke_assignment(
        aid,
        revoked_by=body.get("revoked_by", "joseph"),
        reason=body.get("reason"),
    )
    return jsonify(row)


@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/complete", methods=["POST"])
@api_route
def complete_api(aid):
    from services.dispatch_service import complete_assignment
    body = request.get_json(silent=True) or {}
    row = complete_assignment(aid, result_ref=body.get("result_ref"))
    return jsonify(row)


@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/fail", methods=["POST"])
@api_route
def fail_api(aid):
    from services.dispatch_service import fail_assignment
    body = request.get_json(silent=True) or {}
    row = fail_assignment(aid, reason=body.get("reason"))
    return jsonify(row)


# ---------------------------------------------------------------------------
# Pull-API (Variante B) — Bearer-Token-geschuetzt
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/pull", methods=["GET"])
@require_pull_auth
@api_route
def pull_next():
    """Aeltestes approved+unclaimed Assignment fuer ein Tool.

    Query-Param: tool=<tool_id>
    Response: Assignment-Daten oder 204 No Content.
    """
    tool_id = request.args.get("tool")
    if not tool_id:
        return jsonify({"error": "Query-Param 'tool' fehlt"}), 400

    # Pruefe dispatch_pull Erlaubnis
    from services.policy_service import list_tool_profiles
    profiles = {p["tool_id"]: p for p in list_tool_profiles(include_inactive=True)}
    profile = profiles.get(tool_id)
    if not profile:
        return jsonify({"error": f"Tool '{tool_id}' nicht gefunden"}), 404
    if not profile.get("dispatch_pull"):
        return jsonify({"error": f"Pull nicht erlaubt fuer '{tool_id}'"}), 403

    # Aeltestes approved + unclaimed
    from services.db_dispatch_schema import ensure_dispatch_schema
    ensure_dispatch_schema()
    from services.db_service import execute

    row = execute(
        """
        SELECT * FROM work_assignments
        WHERE executor_tool = %s
          AND approval_state = 'approved'
          AND claimed_at IS NULL
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (tool_id,),
        fetchone=True,
    )

    if not row:
        return "", 204

    result = dict(row)

    # Perplexity-Gate: Review triggern falls noch nicht vorhanden
    if not result.get("perplexity_review"):
        from services.dispatch_service import get_perplexity_mode
        pmode = get_perplexity_mode(project_name=result.get("project_name"))

        if pmode != "off":
            # Review asynchron anstoßen (fire-and-forget, blockiert nicht)
            try:
                from services.dispatch_review_service import review_assignment
                review_result = review_assignment(result["assignment_id"])
                if review_result.get("error") is None:
                    result["perplexity_review"] = review_result.get("review")
                    result["perplexity_pending"] = False
                else:
                    result["perplexity_pending"] = True
            except Exception:
                result["perplexity_pending"] = True
        else:
            result["perplexity_pending"] = False

    return jsonify(result)


@dispatch_bp.route("/api/dispatch/pull/<int:aid>/claim", methods=["POST"])
@require_pull_auth
@api_route
def pull_claim(aid):
    """Tool uebernimmt ein Assignment (atomar)."""
    from services.dispatch_service import claim_assignment

    body = request.get_json(silent=True) or {}
    claimed_by = body.get("claimed_by", request.headers.get("X-Tool-ID", "unknown"))

    try:
        row = claim_assignment(aid, claimed_by=claimed_by)
        return jsonify(row)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------------------------------------------------------
# Perplexity-Endpoints
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/review", methods=["POST"])
@api_route
def review_api(aid):
    """Triggert Perplexity-Review fuer ein Assignment."""
    from services.dispatch_review_service import review_assignment
    result = review_assignment(aid)
    return jsonify(result)


@dispatch_bp.route("/api/dispatch/suggest", methods=["POST"])
@api_route
def suggest_api():
    """Triggert Perplexity-Suggest fuer offene Marker."""
    from services.dispatch_review_service import suggest_assignments

    project = request.args.get("project")
    if not project:
        body = request.get_json(silent=True) or {}
        project = body.get("project_name")
    if not project:
        return jsonify({"error": "project_name fehlt"}), 400

    result = suggest_assignments(project)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Audit-Log
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/audit", methods=["GET"])
@api_route
def audit_log_api(aid):
    """Audit-Trail fuer ein Assignment."""
    from services.dispatch_service import get_audit_log
    rows = get_audit_log(aid)
    return jsonify({"audit_log": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/settings", methods=["GET"])
@api_route
def get_settings_api():
    """Effektive Dispatch-Settings (optional pro Projekt/Tool)."""
    from services.dispatch_service import get_effective_settings

    project = request.args.get("project")
    tool = request.args.get("tool")
    settings = get_effective_settings(project_name=project, tool_id=tool)
    return jsonify(settings)


@dispatch_bp.route("/api/dispatch/settings", methods=["POST"])
@api_route
def update_settings_api():
    """Settings upsert (scope + scope_ref + Felder)."""
    from services.dispatch_service import update_settings

    body = request.get_json(silent=True) or {}
    scope = body.get("scope", "global")
    scope_ref = body.get("scope_ref")

    kwargs = {}
    if "perplexity_mode" in body:
        kwargs["perplexity_mode"] = body["perplexity_mode"]
    if "auto_expire_hours" in body:
        kwargs["auto_expire_hours"] = body["auto_expire_hours"]

    if not kwargs:
        return jsonify({"error": "Keine Felder zum Aktualisieren"}), 400

    row = update_settings(scope, scope_ref, **kwargs)
    return jsonify(row)


# ---------------------------------------------------------------------------
# Marker-Liste fuer Dispatch-UI (Commit 6)
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/markers", methods=["GET"])
@api_route
def list_markers_for_dispatch():
    """Marker eines Projekts fuer die Dispatch-UI.

    Liefert alle Marker (als Dicts) aus workflow_core_service.
    """
    from dataclasses import asdict

    from services.workflow_core_service import get_markers

    project = request.args.get("project")
    if not project:
        return jsonify({"error": "Query-Param 'project' fehlt"}), 400

    markers = get_markers(project)
    result = [asdict(m) for m in markers if m]
    return jsonify({
        "markers": result,
        "count": len(result),
    })


# ---------------------------------------------------------------------------
# Manual Claim (Commit 6 — kein Bearer-Auth, interne UI)
# ---------------------------------------------------------------------------

@dispatch_bp.route("/api/dispatch/assignments/<int:aid>/claim", methods=["POST"])
@api_route
def manual_claim_api(aid):
    """Manuelles Claim eines Assignments aus der UI (Variante A)."""
    from services.dispatch_service import claim_assignment

    body = request.get_json(silent=True) or {}
    claimed_by = body.get("claimed_by", "joseph")

    try:
        row = claim_assignment(aid, claimed_by=claimed_by)
        return jsonify(row)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
