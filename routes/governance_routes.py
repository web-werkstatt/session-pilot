"""
Sprint 12: Governance Routes - Policy-Verwaltung und Regel-Generierung.
"""
from flask import Blueprint, jsonify, request, render_template
from routes.api_utils import api_route
from services.governance_service import (
    get_project_policy,
    update_project_policy,
    get_governance_overview,
    get_unreviewed_critical_count,
    apply_rule_to_project,
    get_rule_effectiveness,
    generate_policy_snippets,
)
from services.rule_generator import generate_rules, get_feedback_loop_analysis

governance_bp = Blueprint("governance", __name__)


@governance_bp.route("/governance")
def governance_page():
    return render_template("governance.html", active_page="governance")


@governance_bp.route("/api/governance/overview")
@api_route
def api_governance_overview():
    """Uebersicht aller Projekte mit Policy-Level und Rework-Rate."""
    data = get_governance_overview()
    data["unreviewed_critical"] = get_unreviewed_critical_count()
    return jsonify(data)


@governance_bp.route("/api/projects/<name>/policy")
@api_route
def api_get_policy(name):
    """Policy fuer ein Projekt abfragen."""
    policy = get_project_policy(name)
    return jsonify(policy)


@governance_bp.route("/api/projects/<name>/policy", methods=["PUT"])
@api_route
def api_update_policy(name):
    """Policy fuer ein Projekt aktualisieren."""
    body = request.get_json(force=True)
    level = body.get("level", 1)
    notes = body.get("notes")
    allowed_models = body.get("allowed_models")
    max_ai_write_scope = body.get("max_ai_write_scope")
    preferred_workflow = body.get("preferred_workflow")

    policy = update_project_policy(
        name, level,
        notes=notes,
        allowed_models=allowed_models,
        max_ai_write_scope=max_ai_write_scope,
        preferred_workflow=preferred_workflow,
    )
    return jsonify(policy)


@governance_bp.route("/api/governance/rules/<project>")
@api_route
def api_rules(project):
    """Regel-Vorschlaege fuer ein Projekt."""
    period = request.args.get("period", "90d")
    limit = int(request.args.get("limit", "5"))
    rules = generate_rules(project=project, period=period, limit=limit)
    return jsonify({"project": project, "rules": rules})


@governance_bp.route("/api/governance/rules/<project>/apply", methods=["POST"])
@api_route
def api_apply_rule(project):
    """Regel in project.json uebernehmen."""
    body = request.get_json(force=True)
    reason = body.get("reason")
    rule_text = body.get("rule_text")
    if not reason or not rule_text:
        return jsonify({"error": "reason und rule_text erforderlich"}), 400
    policy = apply_rule_to_project(project, reason, rule_text)
    return jsonify(policy)


@governance_bp.route("/api/governance/effectiveness/<project>")
@api_route
def api_effectiveness(project):
    """Wirkungs-Tracking fuer angewandte Regeln."""
    results = get_rule_effectiveness(project)
    return jsonify({"project": project, "effectiveness": results})


@governance_bp.route("/api/governance/feedback-loop")
@api_route
def api_feedback_loop():
    """Feedback-Loop: Fehlerkategorien pro Policy-Level."""
    period = request.args.get("period", "90d")
    data = get_feedback_loop_analysis(period=period)
    return jsonify(data)


@governance_bp.route("/api/governance/snippets/<project>")
@api_route
def api_snippets(project):
    """Exportierbare Policy-Snippets fuer CLAUDE.md, AGENTS.md, pre-commit."""
    snippets = generate_policy_snippets(project)
    return jsonify(snippets)
