"""
Sprint E1/E2: Model Eval Routes — API + Seite fuer Eval-Scorecard.
E2: Judge-Scores, SWE-Metriken, Human-Override Layer.
"""
from flask import Blueprint, jsonify, request, render_template
from routes.api_utils import api_route
from services.model_eval_service import (
    create_eval_run,
    list_eval_runs,
    get_eval_run,
    get_criteria,
)
from services.model_eval_layers import (
    set_judge_scores,
    set_swe_metrics,
    set_human_scores,
    compute_final_scores,
)

model_eval_bp = Blueprint("model_eval", __name__)


@model_eval_bp.route("/model-eval")
def model_eval_page():
    return render_template("model_eval.html", active_page="model_eval")


@model_eval_bp.route("/api/eval/criteria")
@api_route
def api_eval_criteria():
    """Liefert die V1-Kriterien mit Gewichten."""
    return jsonify({"criteria": get_criteria()})


@model_eval_bp.route("/api/eval/runs", methods=["POST"])
def api_create_eval_run():
    """Erstellt einen neuen Eval-Run mit Scores."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    task_title = data.get("task_title")
    model_a = data.get("model_a")
    scores_a = data.get("scores_a")

    if not task_title or not isinstance(task_title, str) or not task_title.strip():
        return jsonify({"error": "task_title ist erforderlich"}), 400
    if not model_a or not isinstance(model_a, str) or not model_a.strip():
        return jsonify({"error": "model_a ist erforderlich"}), 400
    if not scores_a or not isinstance(scores_a, list):
        return jsonify({"error": "scores_a ist erforderlich (Liste)"}), 400

    model_b = data.get("model_b")
    scores_b = data.get("scores_b")
    if model_b and not scores_b:
        return jsonify({"error": "scores_b ist erforderlich wenn model_b gesetzt"}), 400

    try:
        result = create_eval_run(
            task_title=task_title.strip(),
            model_a=model_a.strip(),
            scores_a=scores_a,
            model_b=model_b.strip() if model_b else None,
            scores_b=scores_b,
            task_description=data.get("task_description"),
            project_id=data.get("project_id"),
            notes=data.get("notes"),
            created_by=data.get("created_by"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {e}"}), 500

    return jsonify(result), 201


@model_eval_bp.route("/api/eval/runs")
@api_route
def api_list_eval_runs():
    """Listet Eval-Runs, optional gefiltert nach Projekt."""
    project_id = request.args.get("project_id")
    limit = request.args.get("limit", 50, type=int)
    runs = list_eval_runs(project_id=project_id, limit=limit)
    return jsonify({"runs": runs})


@model_eval_bp.route("/api/eval/runs/<int:run_id>")
@api_route
def api_get_eval_run(run_id):
    """Liefert einen einzelnen Eval-Run mit allen Scores und E2-Layern."""
    run = get_eval_run(run_id)
    if not run:
        return jsonify({"error": "Eval-Run nicht gefunden"}), 404
    return jsonify(run)


# --- E2: Layer-Endpoints ---

@model_eval_bp.route("/api/eval/runs/<int:run_id>/judge-scores", methods=["PUT"])
def api_set_judge_scores(run_id):
    """Setzt LLM-Judge-Scores fuer eine Modell-Seite."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    model_side = data.get("model_side", "a")
    scores = data.get("scores")
    if not scores or not isinstance(scores, list):
        return jsonify({"error": "scores ist erforderlich (Liste)"}), 400

    try:
        result = set_judge_scores(run_id, model_side, scores)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {e}"}), 500

    return jsonify(result)


@model_eval_bp.route("/api/eval/runs/<int:run_id>/swe-metrics", methods=["PUT"])
def api_set_swe_metrics(run_id):
    """Setzt SWE-Metriken fuer eine Modell-Seite."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    model_side = data.get("model_side", "a")
    metrics = data.get("metrics")
    if not metrics or not isinstance(metrics, dict):
        return jsonify({"error": "metrics ist erforderlich (Objekt)"}), 400

    try:
        result = set_swe_metrics(run_id, model_side, metrics)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {e}"}), 500

    return jsonify(result)


@model_eval_bp.route("/api/eval/runs/<int:run_id>/human-scores", methods=["PUT"])
def api_set_human_scores(run_id):
    """Setzt Human-Override-Scores fuer eine Modell-Seite."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON-Body erforderlich"}), 400

    model_side = data.get("model_side", "a")
    scores = data.get("scores")
    if not scores or not isinstance(scores, list):
        return jsonify({"error": "scores ist erforderlich (Liste)"}), 400

    try:
        result = set_human_scores(run_id, model_side, scores)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {e}"}), 500

    return jsonify(result)


@model_eval_bp.route("/api/eval/runs/<int:run_id>/final-scores")
@api_route
def api_final_scores(run_id):
    """Berechnet und liefert die finalen Scores mit Layer-Herkunft."""
    model_side = request.args.get("model_side", "a")
    result = compute_final_scores(run_id, model_side)
    return jsonify(result)
