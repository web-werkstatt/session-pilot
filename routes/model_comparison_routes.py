"""
Sprint 11: Model Quality Comparison - Routes.
API-Endpoints fuer Modell-Vergleich, Stack-Metriken und Trends.
"""
from flask import Blueprint, jsonify, request, render_template
from routes.api_utils import api_route
from services.model_recommendation import (
    get_model_comparison,
    get_model_by_stack,
    get_model_trend,
    recommend_model,
)

model_comparison_bp = Blueprint("model_comparison", __name__)


@model_comparison_bp.route("/model-comparison")
def model_comparison_page():
    return render_template("model_comparison.html", active_page="model_comparison")


@model_comparison_bp.route("/api/analytics/model-comparison")
@api_route
def api_model_comparison():
    """Modell-Vergleichsdaten mit Quality-Score."""
    period = request.args.get("period", "90d")
    project = request.args.get("project")
    stack = request.args.get("stack")
    data = get_model_comparison(period=period, project=project, stack=stack)
    return jsonify(data)


@model_comparison_bp.route("/api/analytics/model-by-stack")
@api_route
def api_model_by_stack():
    """Stack-spezifische Metriken pro Modell."""
    period = request.args.get("period", "90d")
    project = request.args.get("project")
    data = get_model_by_stack(period=period, project=project)
    return jsonify(data)


@model_comparison_bp.route("/api/analytics/model-trend")
@api_route
def api_model_trend():
    """Woechentliche/taegliche Rework-Rate-Trends pro Modell."""
    model = request.args.get("model")
    project = request.args.get("project")
    granularity = request.args.get("granularity", "weekly")
    data = get_model_trend(model=model, project=project, granularity=granularity)
    return jsonify(data)


@model_comparison_bp.route("/api/analytics/model-recommendation")
@api_route
def api_model_recommendation():
    """Modell-Empfehlung fuer Projekt/Stack."""
    project = request.args.get("project")
    stack = request.args.get("stack")
    data = recommend_model(project=project, stack=stack)
    return jsonify(data)
