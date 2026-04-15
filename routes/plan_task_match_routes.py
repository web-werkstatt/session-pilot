"""
Sprint sprint-task-backfill (2026-04-15):
API fuer Task-Match-Suggestions (Fuzzy-Backfill bestehender Marker).

Endpoints:
- POST /api/plans/<id>/task-matches/recompute
- GET  /api/plans/<id>/task-matches?status=pending
- POST /api/task-matches/<id>/approve
- POST /api/task-matches/<id>/reject
- POST /api/plans/<id>/task-matches/auto-apply
"""
from flask import Blueprint, jsonify, request

from routes.api_utils import api_route
from services.plan_task_match_service import (
    AUTO_APPLY_MIN_SCORE,
    approve,
    auto_apply,
    compute_suggestions,
    count_orphans,
    list_suggestions,
    reject,
)


plan_task_match_bp = Blueprint("plan_task_match", __name__)


def _decider():
    return (request.headers.get("X-User") or "dashboard").strip() or "dashboard"


@plan_task_match_bp.route("/api/plans/<int:plan_id>/task-matches/recompute", methods=["POST"])
@api_route
def api_recompute_task_matches(plan_id):
    stats = compute_suggestions(plan_id)
    return jsonify({"ok": True, "plan_id": plan_id, **stats})


@plan_task_match_bp.route("/api/plans/<int:plan_id>/task-matches", methods=["GET"])
@api_route
def api_list_task_matches(plan_id):
    status = (request.args.get("status") or "pending").strip().lower()
    if status not in {"pending", "approved", "rejected"}:
        return jsonify({"ok": False, "error": "invalid_status"}), 400
    suggestions = list_suggestions(plan_id, status=status)
    return jsonify({
        "ok": True,
        "plan_id": plan_id,
        "status": status,
        "count": len(suggestions),
        "suggestions": suggestions,
        "orphans_remaining": count_orphans(plan_id),
    })


@plan_task_match_bp.route("/api/task-matches/<int:suggestion_id>/approve", methods=["POST"])
@api_route
def api_approve_task_match(suggestion_id):
    result = approve(suggestion_id, decided_by=_decider())
    if not result:
        return jsonify({"ok": False, "error": "suggestion_not_found"}), 404
    return jsonify({"ok": True, "result": result})


@plan_task_match_bp.route("/api/task-matches/<int:suggestion_id>/reject", methods=["POST"])
@api_route
def api_reject_task_match(suggestion_id):
    result = reject(suggestion_id, decided_by=_decider())
    if not result:
        return jsonify({"ok": False, "error": "suggestion_not_found_or_not_pending"}), 404
    return jsonify({"ok": True, "result": result})


@plan_task_match_bp.route("/api/plans/<int:plan_id>/task-matches/auto-apply", methods=["POST"])
@api_route
def api_auto_apply_task_matches(plan_id):
    body = request.get_json(silent=True) or {}
    try:
        min_score = float(body.get("min_score") or AUTO_APPLY_MIN_SCORE)
    except (TypeError, ValueError):
        min_score = AUTO_APPLY_MIN_SCORE
    min_score = max(0.0, min(1.0, min_score))
    result = auto_apply(plan_id, min_score=min_score, decided_by=_decider())
    return jsonify({
        "ok": True,
        "plan_id": plan_id,
        "min_score": min_score,
        **result,
        "orphans_remaining": count_orphans(plan_id),
    })
