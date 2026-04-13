"""
Finding-Decisions: REST-Endpoints fuer Approve/Dismiss/Ignore von Review-Findings.

Drei Endpoints:
- POST /api/project/<name>/findings/decide   — Entscheidung treffen
- GET  /api/project/<name>/findings/decisions — Entscheidungen auflisten
- POST /api/project/<name>/findings/reset     — Entscheidung zuruecksetzen
"""
import logging

from flask import Blueprint, jsonify, request

from routes.api_utils import api_route
from services.path_resolver import resolve_project_path

log = logging.getLogger(__name__)

finding_decisions_bp = Blueprint("finding_decisions", __name__)


@finding_decisions_bp.route(
    "/api/project/<path:name>/findings/decide", methods=["POST"],
)
@api_route
def decide_finding(name):
    """Speichert eine Entscheidung zu einem Finding.

    Body:
    {
        "fingerprint": "abc123...",
        "review_type": "setup" | "cwo",
        "status": "approved" | "dismissed" | "ignored_once",
        "dismiss_reason": "bewusst_so" | "runtime_datei" | "kein_projektziel" | "dupliziert",
        "dismiss_note": "optional freitext",
        "finding_snapshot": {...}
    }
    """
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    body = request.get_json(silent=True) or {}
    fingerprint = body.get("fingerprint")
    review_type = body.get("review_type")
    status = body.get("status")
    finding_snapshot = body.get("finding_snapshot") or {}

    if not fingerprint or not review_type or not status:
        return jsonify({
            "error": "missing_fields",
            "detail": "fingerprint, review_type und status sind Pflichtfelder",
        }), 400

    from services.finding_decision_service import record_decision

    decision_id = record_decision(
        project_name=name,
        review_type=review_type,
        fingerprint=fingerprint,
        status=status,
        finding_snapshot=finding_snapshot,
        dismiss_reason=body.get("dismiss_reason"),
        dismiss_note=body.get("dismiss_note"),
        decided_by=body.get("decided_by", "joseph"),
    )

    return jsonify({
        "decision_id": decision_id,
        "fingerprint": fingerprint,
        "status": status,
    }), 200


@finding_decisions_bp.route(
    "/api/project/<path:name>/findings/decisions", methods=["GET"],
)
@api_route
def get_decisions(name):
    """Listet Entscheidungen fuer ein Projekt auf.

    Query-Parameter:
    - review_type: 'setup' | 'cwo' (optional)
    - status: 'dismissed' | 'approved' | 'pending' | 'ignored_once' (optional)
    """
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    review_type = request.args.get("review_type")
    status_filter = request.args.get("status")

    from services.finding_decision_service import list_decisions

    decisions = list_decisions(
        name, review_type=review_type, status_filter=status_filter,
    )
    return jsonify({"project": name, "decisions": decisions}), 200


@finding_decisions_bp.route(
    "/api/project/<path:name>/findings/reset", methods=["POST"],
)
@api_route
def reset_finding(name):
    """Setzt eine Entscheidung auf 'pending' zurueck.

    Body: {"fingerprint": "abc123...", "review_type": "setup"}
    """
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    body = request.get_json(silent=True) or {}
    fingerprint = body.get("fingerprint")
    review_type = body.get("review_type")

    if not fingerprint or not review_type:
        return jsonify({
            "error": "missing_fields",
            "detail": "fingerprint und review_type sind Pflichtfelder",
        }), 400

    from services.finding_decision_service import reset_decision

    reset_decision(name, review_type, fingerprint)
    return jsonify({
        "fingerprint": fingerprint,
        "status": "pending",
    }), 200
