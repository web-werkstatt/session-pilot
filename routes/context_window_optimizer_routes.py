"""
CWO Sprint: REST-Endpoints fuer Context Window Optimizer.

Phase 1a (Read-Only Analyse):
- POST /api/project/<name>/cwo/analyze — Analyse durchfuehren (context_hash-Dedup)
- GET  /api/project/<name>/cwo/analyze — Letzte Analyse laden
- POST /api/cwo/analyze-all            — Alle Projekte analysieren
- GET  /api/cwo/overview               — Uebersicht: Projekte nach Token-Budget

Phase 1b (Perplexity-Review):
- POST /api/project/<name>/cwo/review  — Perplexity-Review ausloesen
- GET  /api/project/<name>/cwo/review  — Letztes Review laden
"""
import logging

from flask import Blueprint, jsonify, request

from routes.api_utils import api_route
from services.path_resolver import resolve_project_path

log = logging.getLogger(__name__)

cwo_bp = Blueprint("context_window_optimizer", __name__)


@cwo_bp.route("/api/project/<path:name>/cwo/analyze", methods=["POST"])
@api_route
def trigger_analysis(name):
    """Fuehrt CWO-Analyse fuer ein Projekt durch und persistiert das Ergebnis.

    Body (optional): {"force": true} erzwingt Neuanalyse trotz
    identischem context_hash.
    """
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))

    from services.context_window_optimizer import analyze_project

    result = analyze_project(name, force=force)

    if result.get("error") == "project_not_found":
        return jsonify({"error": "Project not found"}), 404

    return jsonify({"project": name, "result": result}), 200


@cwo_bp.route("/api/project/<path:name>/cwo/analyze", methods=["GET"])
@api_route
def get_analysis(name):
    """Liefert letzte gespeicherte CWO-Analyse ohne Neuberechnung."""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    from services.context_window_optimizer import load_analysis

    result = load_analysis(name)
    return jsonify({"project": name, "result": result}), 200


@cwo_bp.route("/api/cwo/analyze-all", methods=["POST"])
@api_route
def trigger_analysis_all():
    """Analysiert alle Projekte unter /mnt/projects/.

    Body (optional): {"force": true} erzwingt Neuanalyse fuer alle.
    """
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))

    from services.context_window_optimizer import analyze_all_projects

    result = analyze_all_projects(force=force)

    return jsonify(result), 200


@cwo_bp.route("/api/cwo/overview", methods=["GET"])
@api_route
def get_overview():
    """Uebersicht aller CWO-Analysen, sortiert nach Token-Verbrauch.

    Optional: ?rating=warning filtert auf ein bestimmtes Rating.
    """
    from services.context_window_optimizer import load_all_analyses

    analyses = load_all_analyses()

    rating_filter = request.args.get("rating")
    if rating_filter:
        analyses = [
            a for a in analyses
            if a.get("token_budget_rating") == rating_filter
        ]

    summary = {
        "total": len(analyses),
        "by_rating": _count_by_rating(analyses),
    }

    return jsonify({
        "summary": summary,
        "projects": analyses,
    }), 200


@cwo_bp.route("/api/project/<path:name>/cwo/review", methods=["POST"])
@api_route
def trigger_review(name):
    """Loest ein Perplexity-Review fuer die bestehende CWO-Analyse aus.

    Voraussetzung: Es muss bereits eine Analyse existieren
    (via POST /api/project/<name>/cwo/analyze).

    Body (optional): {"force": true} erzwingt Review trotz
    identischem review_context_hash.
    """
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))

    from services.context_window_optimizer import review_project

    result = review_project(name, force=force)

    if result.get("error") == "no_analysis":
        return jsonify({
            "error": "No CWO analysis found. Run POST /api/project/<name>/cwo/analyze first."
        }), 404

    return jsonify({"project": name, "result": result}), 200


@cwo_bp.route("/api/project/<path:name>/cwo/review", methods=["GET"])
@api_route
def get_review(name):
    """Liefert das letzte gespeicherte Perplexity-Review ohne neuen Aufruf."""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    from services.context_window_optimizer import load_review

    result = load_review(name)
    return jsonify({"project": name, "result": result}), 200


def _count_by_rating(analyses):
    """Zaehlt Projekte pro Rating-Stufe."""
    counts = {"ok": 0, "info": 0, "warning": 0, "error": 0}
    for a in analyses:
        rating = a.get("token_budget_rating", "ok")
        counts[rating] = counts.get(rating, 0) + 1
    return counts
