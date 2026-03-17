"""
Session-Analyse Routes: Token-Kosten, Tools, produktivste Zeiten
"""
from flask import Blueprint, jsonify, request, render_template
from services.db_service import execute

session_analysis_bp = Blueprint('session_analysis', __name__)

# Preise pro 1M Tokens (USD) - Stand Maerz 2026
MODEL_PRICING = {
    "claude-sonnet-4-5-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5-20250514": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def _estimate_cost(model, input_tokens, output_tokens):
    pricing = DEFAULT_PRICING
    if model:
        for key, p in MODEL_PRICING.items():
            if key in model:
                pricing = p
                break
    cost_in = (input_tokens or 0) / 1_000_000 * pricing["input"]
    cost_out = (output_tokens or 0) / 1_000_000 * pricing["output"]
    return round(cost_in + cost_out, 4)


@session_analysis_bp.route('/sessions/analysis')
def session_analysis_page():
    return render_template('session_analysis.html', active_page='analysis')


@session_analysis_bp.route('/api/sessions/analysis')
def session_analysis():
    """Umfassende Session-Analyse"""
    days = request.args.get('days', 30, type=int)
    days = min(days, 365)

    # Kosten pro Modell
    model_stats = execute("""
        SELECT model,
               COUNT(*) as session_count,
               SUM(total_input_tokens) as input_tokens,
               SUM(total_output_tokens) as output_tokens,
               SUM(duration_ms) as total_duration
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY model
        ORDER BY SUM(total_input_tokens + total_output_tokens) DESC
    """, (days,), fetch=True)

    models = []
    total_cost = 0
    total_input = 0
    total_output = 0
    for m in (model_stats or []):
        cost = _estimate_cost(m["model"], m["input_tokens"], m["output_tokens"])
        total_cost += cost
        total_input += (m["input_tokens"] or 0)
        total_output += (m["output_tokens"] or 0)
        models.append({
            "model": m["model"] or "unbekannt",
            "sessions": m["session_count"],
            "input_tokens": m["input_tokens"] or 0,
            "output_tokens": m["output_tokens"] or 0,
            "cost_usd": round(cost, 2),
            "duration_ms": m["total_duration"] or 0,
        })

    # Aktivitaet pro Stunde
    hourly = execute("""
        SELECT EXTRACT(HOUR FROM started_at) as hour,
               COUNT(*) as cnt,
               SUM(total_input_tokens + total_output_tokens) as tokens
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY hour ORDER BY hour
    """, (days,), fetch=True)

    hours = {int(h["hour"]): {"sessions": h["cnt"], "tokens": h["tokens"] or 0} for h in (hourly or [])}

    # Aktivitaet pro Wochentag (0=Mo, 6=So)
    daily = execute("""
        SELECT EXTRACT(ISODOW FROM started_at) as dow,
               COUNT(*) as cnt,
               SUM(duration_ms) as total_dur
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY dow ORDER BY dow
    """, (days,), fetch=True)

    weekday_names = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}
    weekdays = [
        {"day": weekday_names.get(int(d["dow"]), "?"), "sessions": d["cnt"], "duration_ms": d["total_dur"] or 0}
        for d in (daily or [])
    ]

    # Aktivitaet pro Tag (letzte N Tage)
    daily_activity = execute("""
        SELECT started_at::date as day,
               COUNT(*) as sessions,
               SUM(total_input_tokens + total_output_tokens) as tokens,
               SUM(duration_ms) as duration_ms
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY day ORDER BY day
    """, (days,), fetch=True)

    activity = [
        {"date": str(d["day"]), "sessions": d["sessions"], "tokens": d["tokens"] or 0, "duration_ms": d["duration_ms"] or 0}
        for d in (daily_activity or [])
    ]

    # Top-Projekte nach Kosten
    project_costs = execute("""
        SELECT project_name, model,
               SUM(total_input_tokens) as input_tokens,
               SUM(total_output_tokens) as output_tokens,
               COUNT(*) as sessions,
               SUM(duration_ms) as duration_ms
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days' AND project_name IS NOT NULL
        GROUP BY project_name, model
    """, (days,), fetch=True)

    project_map = {}
    for p in (project_costs or []):
        name = p["project_name"]
        cost = _estimate_cost(p["model"], p["input_tokens"], p["output_tokens"])
        if name not in project_map:
            project_map[name] = {"project": name, "cost_usd": 0, "sessions": 0, "tokens": 0, "duration_ms": 0}
        project_map[name]["cost_usd"] += cost
        project_map[name]["sessions"] += p["sessions"]
        project_map[name]["tokens"] += (p["input_tokens"] or 0) + (p["output_tokens"] or 0)
        project_map[name]["duration_ms"] += (p["duration_ms"] or 0)

    top_projects = sorted(project_map.values(), key=lambda x: x["cost_usd"], reverse=True)[:15]
    for p in top_projects:
        p["cost_usd"] = round(p["cost_usd"], 2)

    # Haeufigste Tools (aus messages.content_json)
    tool_stats = execute("""
        SELECT content_json->>'tool_name' as tool_name, COUNT(*) as cnt
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.type = 'tool_use'
          AND s.started_at >= NOW() - INTERVAL '%s days'
          AND content_json->>'tool_name' IS NOT NULL
        GROUP BY tool_name
        ORDER BY cnt DESC
        LIMIT 20
    """, (days,), fetch=True)

    tools = [{"name": t["tool_name"], "count": t["cnt"]} for t in (tool_stats or [])]

    return jsonify({
        "days": days,
        "cost": {
            "total_usd": round(total_cost, 2),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "by_model": models,
            "by_project": top_projects,
        },
        "hourly": hours,
        "weekdays": weekdays,
        "activity": activity,
        "tools": tools,
    })
