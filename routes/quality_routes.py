"""Quality-Dashboard: Score, Issues, Baseline-Vergleich"""

import json
import os
import subprocess
import sys
from flask import Blueprint, jsonify, render_template

from config import PROJECTS_DIR

quality_bp = Blueprint('quality', __name__)

AUTO_CODER_PATH = "/mnt/projects/auto_coder"
QUALITY_DIR = ".quality"


def _read_report(project_path):
    """Liest report.json fuer ein Projekt"""
    path = os.path.join(project_path, QUALITY_DIR, "report.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _read_baseline(project_path):
    """Liest baseline.json fuer ein Projekt"""
    path = os.path.join(project_path, QUALITY_DIR, "baseline.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


@quality_bp.route('/quality')
def quality_page():
    return render_template('quality.html', active_page='quality')


@quality_bp.route('/api/quality/projects')
def quality_projects():
    """Alle Projekte mit Quality-Reports"""
    results = []
    if not os.path.isdir(PROJECTS_DIR):
        return jsonify(results)

    for entry in sorted(os.listdir(PROJECTS_DIR)):
        path = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(path) or entry.startswith('.'):
            continue
        report = _read_report(path)
        if report:
            results.append({
                "name": entry,
                "score": report.get("score", "?"),
                "score_numeric": report.get("score_numeric", 0),
                "errors": report.get("summary", {}).get("errors", 0),
                "warnings": report.get("summary", {}).get("warnings", 0),
                "info": report.get("summary", {}).get("info", 0),
                "total_issues": report.get("summary", {}).get("total_issues", 0),
                "scanned_at": report.get("scanned_at", ""),
            })

    results.sort(key=lambda x: x["score_numeric"])
    return jsonify(results)


@quality_bp.route('/api/quality/report/<path:project>')
def quality_report(project):
    """Detaillierter Report fuer ein Projekt"""
    project_path = os.path.join(PROJECTS_DIR, project)
    if not os.path.isdir(project_path):
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    report = _read_report(project_path)
    baseline = _read_baseline(project_path)

    if not report:
        return jsonify({"error": "Kein Report vorhanden"}), 404

    result = {
        "report": report,
        "baseline": None,
        "diff": None,
    }

    if baseline:
        baseline_ids = {i["id"] for i in baseline.get("issues", []) if i.get("status") != "ignored"}
        current_ids = {i["id"] for i in report.get("issues", []) if i.get("status") != "ignored"}

        new_issues = [i for i in report["issues"] if i["id"] not in baseline_ids and i.get("status") != "ignored"]
        fixed_issues = [i for i in baseline["issues"] if i["id"] not in current_ids and i.get("status") != "ignored"]

        result["baseline"] = {
            "score": baseline.get("score"),
            "score_numeric": baseline.get("score_numeric"),
            "scanned_at": baseline.get("scanned_at"),
        }
        result["diff"] = {
            "score_delta": report.get("score_numeric", 0) - baseline.get("score_numeric", 0),
            "new_issues": len(new_issues),
            "fixed_issues": len(fixed_issues),
        }

    return jsonify(result)


@quality_bp.route('/api/quality/scan/<path:project>', methods=['POST'])
def quality_scan(project):
    """Startet einen Scan fuer ein Projekt"""
    project_path = os.path.join(PROJECTS_DIR, project)
    if not os.path.isdir(project_path):
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = AUTO_CODER_PATH
        result = subprocess.run(
            [sys.executable, "-m", "auto_coder", "scan", project_path],
            capture_output=True, text=True, timeout=120, env=env,
        )
        report = _read_report(project_path)
        if report:
            return jsonify({"success": True, "report": report})
        return jsonify({"error": result.stderr or "Scan fehlgeschlagen"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Scan-Timeout (120s)"}), 500


@quality_bp.route('/api/quality/baseline/<path:project>', methods=['POST'])
def quality_set_baseline(project):
    """Setzt aktuelle Report als Baseline"""
    project_path = os.path.join(PROJECTS_DIR, project)
    report = _read_report(project_path)
    if not report:
        return jsonify({"error": "Kein Report vorhanden"}), 404

    baseline_path = os.path.join(project_path, QUALITY_DIR, "baseline.json")
    with open(baseline_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return jsonify({"success": True, "score": report.get("score"), "score_numeric": report.get("score_numeric")})
