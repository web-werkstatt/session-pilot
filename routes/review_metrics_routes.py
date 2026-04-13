"""
Review-Metriken: REST-API + UI-Seite.

- GET /metrics              — Rendert die Metrics-Seite
- GET /api/review-metrics   — Aggregierte KPIs + Per-Projekt-Daten
"""
import logging

from flask import Blueprint, jsonify, render_template

from routes.api_utils import api_route

log = logging.getLogger(__name__)

review_metrics_bp = Blueprint("review_metrics", __name__)


@review_metrics_bp.route("/metrics", methods=["GET"])
def metrics_page():
    """Rendert die Review-Metriken-Seite."""
    return render_template("metrics.html", active_page="metrics")


@review_metrics_bp.route("/api/review-metrics", methods=["GET"])
@api_route
def get_review_metrics():
    """Liefert aggregierte Review-Metriken fuer das Dashboard."""
    from services.review_metrics_service import get_review_metrics

    metrics = get_review_metrics()
    return jsonify(metrics), 200
