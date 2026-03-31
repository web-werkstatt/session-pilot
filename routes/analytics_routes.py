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
    """File-Touch-Heatmap fuer ein Projekt (Spec 10.3)."""
    period = request.args.get("period", "30d")
    depth = request.args.get("depth", 2, type=int)
    model = request.args.get("model")
    category = request.args.get("category")
    only_written = request.args.get("only_written", "true").lower() != "false"
    limit = request.args.get("limit", 100, type=int)

    data = get_file_heatmap(
        project, period=period, depth=depth, model=model,
        category=category, only_written=only_written, limit=limit,
    )
    dirs = data["dirs"]
    files = data["files"]

    if not dirs:
        return jsonify({"tree": [], "total_touches": 0, "project": project, "period": period})

    total_all = sum(d["touches"] for d in dirs)

    # Dateien nach Verzeichnis gruppieren
    files_by_dir = {}
    for f in files:
        d = f["dir"]
        if d not in files_by_dir:
            files_by_dir[d] = []
        nf = f["needs_fix_count"] or 0
        rv = f["reverted_count"] or 0
        total = f["touches"]
        rework = nf + rv
        files_by_dir[d].append({
            "path": f["file_path"],
            "touches": total,
            "pct": round(total / total_all * 100, 1) if total_all else 0,
            "outcome_stats": {"ok": f["ok_count"] or 0, "needs_fix": nf, "reverted": rv},
            "rework_rate": round(rework / total * 100, 1) if total else 0,
            "models": f["models"] or {},
            "sessions": f["sessions"],
            "last_touched": f["last_touched"].isoformat() if f["last_touched"] else None,
            "top_reason": f.get("top_reason"),
        })

    # Verzeichnisbaum aus SQL-aggregierten Dirs bauen
    result_tree = []
    all_file_entries = []
    for d in dirs:
        nf = d["needs_fix_count"] or 0
        rv = d["reverted_count"] or 0
        total = d["touches"]
        total_outcomes = (d["ok_count"] or 0) + nf + rv
        children = sorted(files_by_dir.get(d["dir"], []),
                          key=lambda x: x["touches"], reverse=True)
        all_file_entries.extend(children)
        node = {
            "path": d["dir"] + "/" if not d["dir"].endswith("/") and depth and depth > 0 else d["dir"],
            "touches": total,
            "pct": round(total / total_all * 100, 1) if total_all else 0,
            "outcome_stats": {"ok": d["ok_count"] or 0, "needs_fix": nf, "reverted": rv},
            "rework_rate": round((nf + rv) / total_outcomes * 100, 1) if total_outcomes else 0,
            "children": children,
        }
        result_tree.append(node)

    # Hotspots: Top 5 Dateien nach Touches
    hotspots = sorted(all_file_entries, key=lambda x: x["touches"], reverse=True)[:5]

    return jsonify({
        "tree": result_tree,
        "hotspots": [{"path": h["path"], "touches": h["touches"],
                       "rework_rate": h["rework_rate"]} for h in hotspots],
        "total_touches": total_all,
        "project": project,
        "period": period,
    })


@analytics_bp.route("/api/analytics/risk-radar/<project>")
@api_route
def api_risk_radar(project):
    """Risk-Radar: Hotspots, Fehlerkategorien, Trend."""
    data = get_risk_radar(project)
    return jsonify(data)
