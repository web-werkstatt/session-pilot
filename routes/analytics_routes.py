"""
Analytics-API: File-Heatmap und Risk-Radar (Sprint 10).
Eigenes Modul fuer alle Analytics-Endpoints.
"""
from flask import Blueprint, jsonify, request
from services.file_touch_service import get_file_heatmap, get_risk_radar
from routes.api_utils import api_route

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics/file-heatmap/<project>")
@api_route
def api_file_heatmap(project):
    """File-Touch-Heatmap fuer ein Projekt."""
    limit = request.args.get("limit", 100, type=int)
    touch_type = request.args.get("type")

    rows = get_file_heatmap(project, limit=limit)
    if not rows:
        return jsonify({"files": [], "total": 0})

    files = []
    for r in rows:
        entry = {
            "file_path": r["file_path"],
            "total": r["total"],
            "writes": r["writes"],
            "edits": r["edits"],
            "reads": r["reads"],
            "sessions": r["sessions"],
            "last_touched": r["last_touched"].isoformat() if r["last_touched"] else None,
        }
        # Rework-Rate: Anteil writes+edits am Total
        changes = r["writes"] + r["edits"]
        entry["change_ratio"] = round(changes / r["total"], 2) if r["total"] > 0 else 0
        files.append(entry)

    # Optional: nur bestimmten Touch-Type filtern
    if touch_type and touch_type in ("write", "edit", "read"):
        files = [f for f in files if f.get(touch_type + "s", 0) > 0]

    return jsonify({
        "files": files,
        "total": len(files),
        "project": project,
    })


@analytics_bp.route("/api/analytics/risk-radar/<project>")
@api_route
def api_risk_radar(project):
    """Risk-Radar: Hotspots, Fehlerkategorien, Trend."""
    data = get_risk_radar(project)
    return jsonify(data)
