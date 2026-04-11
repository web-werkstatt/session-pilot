"""
ADR-002 Stufe 1b: REST-Endpoints + UI fuer die Policy-Schicht.

Acht Endpoints:
- GET  /api/policies/roles
- GET  /api/policies/tool-profiles
- GET  /api/policies/assignments[?role_id=...]
- GET  /api/policies/suggestions[?status=pending]
- POST /api/policies/review
- POST /api/policies/suggestions/<id>/approve
- POST /api/policies/suggestions/<id>/reject
- POST /api/policies/seed-defaults

Approval- und Reject-Pfade setzen decided_by aus dem Request-Body
(Default 'joseph'). Bei unbekanntem Status oder fehlendem Body wird
klar abgelehnt - kein implizites Zurueckfallen auf Defaults, die zu
Verwirrung fuehren koennten.
"""
import logging

from flask import Blueprint, jsonify, render_template, request

from services.policy_service import (
    apply_suggestion,
    get_active_policies,
    list_pending_suggestions,
    list_roles,
    list_tool_profiles,
    reject_suggestion,
)
from services.policy_review_service import review_policies

log = logging.getLogger(__name__)

policy_bp = Blueprint("policy", __name__)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@policy_bp.route("/policies", methods=["GET"])
def policies_page():
    """Rendert die Policy-Uebersicht-Seite."""
    return render_template("policies.html", active_page="policies")


# ---------------------------------------------------------------------------
# Read-Endpoints
# ---------------------------------------------------------------------------

@policy_bp.route("/api/policies/roles", methods=["GET"])
def get_roles():
    """Liefert Rollen. Default nur aktive, ?include_inactive=true liefert alle."""
    include_inactive = request.args.get("include_inactive") == "true"
    roles = list_roles(include_inactive=include_inactive)
    return jsonify({"roles": roles})


@policy_bp.route("/api/policies/tool-profiles", methods=["GET"])
def get_tool_profiles():
    """Liefert Tool-Profile. Default nur aktive."""
    include_inactive = request.args.get("include_inactive") == "true"
    profiles = list_tool_profiles(include_inactive=include_inactive)
    return jsonify({"tool_profiles": profiles})


@policy_bp.route("/api/policies/assignments", methods=["GET"])
def get_assignments():
    """Liefert aktive Policies (valid_until IS NULL AND approved_by IS NOT NULL).

    Optionaler Filter ?role_id=programming.
    """
    role_id = request.args.get("role_id") or None
    policies = get_active_policies(role_id=role_id)
    return jsonify({"policies": policies})


@policy_bp.route("/api/policies/suggestions", methods=["GET"])
def get_suggestions():
    """Liefert pending Suggestions. Andere Stati sind in Stufe 1b nicht abrufbar."""
    status = request.args.get("status", "pending")
    if status != "pending":
        return (
            jsonify(
                {
                    "error": "status_unsupported",
                    "detail": "Nur status=pending in Stufe 1b",
                }
            ),
            400,
        )
    suggestions = list_pending_suggestions()
    return jsonify({"suggestions": suggestions})


# ---------------------------------------------------------------------------
# Write-Endpoints
# ---------------------------------------------------------------------------

@policy_bp.route("/api/policies/review", methods=["POST"])
def trigger_policy_review():
    """Triggert einen Policy-Review via Perplexity.

    Persistiert neue Suggestions in policy_review_suggestions.
    query_failed und parse_failed werden als 200-Result mit error-Feld
    zurueckgegeben (analog zum Setup-Reviewer).
    """
    try:
        result = review_policies()
    except Exception as exc:
        log.exception("Policy-Review fehlgeschlagen")
        return (
            jsonify({"error": "internal_error", "detail": str(exc)}),
            500,
        )
    return jsonify(result), 200


@policy_bp.route(
    "/api/policies/suggestions/<int:suggestion_id>/approve",
    methods=["POST"],
)
def approve_policy_suggestion(suggestion_id):
    """Genehmigt eine pending Suggestion und erzeugt eine neue Policy-Zeile.

    Body (optional): {"decided_by": "joseph"}
    """
    body = request.get_json(silent=True) or {}
    decided_by = body.get("decided_by", "joseph")

    try:
        policy_id = apply_suggestion(suggestion_id, decided_by=decided_by)
    except Exception as exc:
        log.exception("apply_suggestion fehlgeschlagen")
        return (
            jsonify({"error": "internal_error", "detail": str(exc)}),
            500,
        )

    if policy_id is None:
        return (
            jsonify(
                {
                    "suggestion_id": suggestion_id,
                    "applied_policy_id": None,
                    "note": "Suggestion nicht pending oder Typ ohne Policy-Insert",
                }
            ),
            200,
        )

    return jsonify(
        {
            "suggestion_id": suggestion_id,
            "applied_policy_id": policy_id,
            "decided_by": decided_by,
        }
    ), 200


@policy_bp.route(
    "/api/policies/suggestions/<int:suggestion_id>/reject",
    methods=["POST"],
)
def reject_policy_suggestion(suggestion_id):
    """Lehnt eine pending Suggestion ab.

    Body (optional): {"decided_by": "joseph", "reason": "..."}
    """
    body = request.get_json(silent=True) or {}
    decided_by = body.get("decided_by", "joseph")
    reason = body.get("reason")

    try:
        reject_suggestion(
            suggestion_id, decided_by=decided_by, reason=reason,
        )
    except Exception as exc:
        log.exception("reject_suggestion fehlgeschlagen")
        return (
            jsonify({"error": "internal_error", "detail": str(exc)}),
            500,
        )

    return jsonify(
        {
            "suggestion_id": suggestion_id,
            "status": "rejected",
            "decided_by": decided_by,
        }
    ), 200


@policy_bp.route("/api/policies/seed-defaults", methods=["POST"])
def trigger_seed_defaults():
    """Legt Default-Rollen und Tool-Profile an (idempotent).

    Bestehende Eintraege werden nicht ueberschrieben - Josephs manuelle
    Anpassungen bleiben erhalten. Re-Run zieht nur neue Defaults nach.
    """
    from services.policy_seed import seed_defaults
    try:
        result = seed_defaults()
    except Exception as exc:
        log.exception("seed_defaults fehlgeschlagen")
        return (
            jsonify({"error": "internal_error", "detail": str(exc)}),
            500,
        )
    return jsonify(result), 200
