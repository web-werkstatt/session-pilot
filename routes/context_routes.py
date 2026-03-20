"""
Context Effectiveness: Vorher/Nachher-Analyse von CLAUDE.md Aenderungen
"""
from flask import Blueprint, jsonify, request
from services.db_service import execute
from services.cost_service import calculate_cost

context_bp = Blueprint('context', __name__)


@context_bp.route('/api/timesheets/context-changes')
def api_context_changes():
    """Liste aller Instruktions-Aenderungen"""
    try:
        project = request.args.get('project')
        conditions = []
        params = []
        if project:
            conditions.append("project_name = %s")
            params.append(project)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        rows = execute(f"""
            SELECT id, project_name, file_path, changed_at,
                   lines_added, lines_removed, commit_hash, commit_message
            FROM context_changes {where}
            ORDER BY changed_at DESC LIMIT 200
        """, params, fetch=True)

        return jsonify([{
            "id": r["id"], "project": r["project_name"], "file": r["file_path"],
            "date": r["changed_at"].isoformat() if r["changed_at"] else None,
            "added": r["lines_added"], "removed": r["lines_removed"],
            "commit": r["commit_hash"][:7] if r["commit_hash"] else None,
            "message": r["commit_message"],
        } for r in (rows or [])])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@context_bp.route('/api/timesheets/context-effectiveness')
def api_context_effectiveness():
    """Vorher/Nachher-Vergleich pro CLAUDE.md-Aenderung"""
    try:
        project = request.args.get('project')
        window_days = request.args.get('window', 14, type=int)

        conditions = []
        params = []
        if project:
            conditions.append("project_name = %s")
            params.append(project)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        changes = execute(f"""
            SELECT project_name, file_path, changed_at, commit_hash, commit_message,
                   lines_added, lines_removed
            FROM context_changes {where} ORDER BY changed_at DESC
        """, params, fetch=True)

        results = []
        for ch in (changes or []):
            proj = ch["project_name"]
            ts = ch["changed_at"]
            proj_variants = [proj, proj.replace("_", "-")]

            before = _get_period_metrics(proj_variants, ts, -window_days, 0)
            after = _get_period_metrics(proj_variants, ts, 0, window_days)

            if before["sessions"] < 2 and after["sessions"] < 2:
                continue

            deltas = {}
            for key in ("avg_messages", "avg_tokens", "avg_cost"):
                bv = before.get(key, 0)
                av = after.get(key, 0)
                deltas[key] = round((av - bv) / bv * 100, 1) if bv and bv > 0 else None

            results.append({
                "project": proj, "file": ch["file_path"], "date": ts.isoformat(),
                "commit": ch["commit_hash"][:7] if ch["commit_hash"] else None,
                "message": ch["commit_message"],
                "added": ch["lines_added"], "removed": ch["lines_removed"],
                "before": before, "after": after, "deltas": deltas,
            })

        summary = []
        seen = set()
        for r in results:
            if r["project"] in seen:
                continue
            seen.add(r["project"])
            d = r["deltas"]
            if d.get("avg_cost") is not None:
                summary.append({
                    "project": r["project"], "cost_delta": d["avg_cost"],
                    "tokens_delta": d.get("avg_tokens"), "messages_delta": d.get("avg_messages"),
                })
        summary.sort(key=lambda x: x["cost_delta"] or 0)

        return jsonify({"changes": results, "summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _get_period_metrics(project_names, reference_date, offset_start, offset_end):
    """Berechnet Session-Metriken fuer ein Zeitfenster relativ zu einem Datum"""
    placeholders = ",".join(["%s"] * len(project_names))
    row = execute(f"""
        SELECT COUNT(*) as sessions,
            COALESCE(AVG(user_message_count + assistant_message_count), 0) as avg_messages,
            COALESCE(AVG(total_input_tokens + total_output_tokens), 0) as avg_tokens,
            COALESCE(AVG(duration_ms), 0) as avg_duration,
            COALESCE(SUM(total_input_tokens), 0) as total_input,
            COALESCE(SUM(total_output_tokens), 0) as total_output,
            COALESCE(SUM(cache_read_tokens), 0) as cache_r,
            COALESCE(SUM(cache_creation_tokens), 0) as cache_c
        FROM sessions
        WHERE project_name IN ({placeholders})
          AND started_at >= %s + INTERVAL '{offset_start} days'
          AND started_at < %s + INTERVAL '{offset_end} days'
    """, project_names + [reference_date, reference_date], fetchone=True)

    if not row or row["sessions"] == 0:
        return {"sessions": 0, "avg_messages": 0, "avg_tokens": 0, "avg_cost": 0, "avg_duration": 0}

    total_cost = calculate_cost(None, row["total_input"], row["total_output"], row["cache_r"], row["cache_c"])
    return {
        "sessions": row["sessions"],
        "avg_messages": round(float(row["avg_messages"]), 1),
        "avg_tokens": round(float(row["avg_tokens"])),
        "avg_cost": round(total_cost / row["sessions"], 2),
        "avg_duration": round(float(row["avg_duration"])),
    }
