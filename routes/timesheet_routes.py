"""
AI Timesheets: Nutzungsanalyse pro Projekt, Tool und Zeitraum
"""
from flask import Blueprint, jsonify, request, render_template
from services.db_service import execute
from services.cost_service import calculate_cost, format_cost
from services.session_export import format_duration
from routes.api_utils import api_route

timesheets_bp = Blueprint('timesheets', __name__)


def _build_timesheet_filter():
    """Baut WHERE-Klausel aus Request-Parametern (days, project, account)"""
    days = request.args.get('days', 30, type=int)
    days = min(max(days, 1), 365)
    project = request.args.get('project')
    account = request.args.get('account')

    conditions = ["started_at >= NOW() - INTERVAL '%s days'"]
    params = [days]
    if project:
        conditions.append("project_name = %s")
        params.append(project)
    if account:
        conditions.append("account = %s")
        params.append(account)

    where = "WHERE " + " AND ".join(conditions)
    return where, params, days, project, account


@timesheets_bp.route('/timesheets')
def timesheets_page():
    return render_template('timesheets.html', active_page='timesheets')


@timesheets_bp.route('/api/timesheets/summary')
@api_route
def api_timesheets_summary():
    """Zusammenfassung: Zeit, Tokens, Kosten aggregiert"""
    where, params, days, project, account = _build_timesheet_filter()

    # Gesamt-Aggregation
    totals = execute(f"""
        SELECT
            COUNT(*) as sessions,
            COALESCE(SUM(duration_ms), 0) as total_duration_ms,
            COALESCE(SUM(total_input_tokens), 0) as total_input,
            COALESCE(SUM(total_output_tokens), 0) as total_output,
            COALESCE(SUM(user_message_count), 0) as total_messages,
            COALESCE(SUM(assistant_message_count), 0) as total_responses
        FROM sessions {where}
    """, params, fetchone=True)

    # Kosten pro Modell berechnen
    model_rows = execute(f"""
        SELECT model,
               SUM(total_input_tokens) as input_t,
               SUM(total_output_tokens) as output_t,
               SUM(cache_read_tokens) as cache_r,
               SUM(cache_creation_tokens) as cache_c
        FROM sessions {where}
        GROUP BY model
    """, params, fetch=True)

    total_cost = 0
    for r in (model_rows or []):
        total_cost += calculate_cost(r["model"], r["input_t"], r["output_t"], r["cache_r"], r["cache_c"])

    # Vorperioden-Vergleich
    prev_totals = execute(f"""
        SELECT
            COUNT(*) as sessions,
            COALESCE(SUM(duration_ms), 0) as total_duration_ms,
            COALESCE(SUM(total_input_tokens), 0) as total_input,
            COALESCE(SUM(total_output_tokens), 0) as total_output
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
          AND started_at < NOW() - INTERVAL '%s days'
          {" AND project_name = %s" if project else ""}
          {" AND account = %s" if account else ""}
    """, [days * 2, days] + ([project] if project else []) + ([account] if account else []),
        fetchone=True)

    prev_cost = 0
    if prev_totals and prev_totals["sessions"] > 0:
        prev_model_rows = execute(f"""
            SELECT model,
                   SUM(total_input_tokens) as input_t,
                   SUM(total_output_tokens) as output_t
            FROM sessions
            WHERE started_at >= NOW() - INTERVAL '%s days'
              AND started_at < NOW() - INTERVAL '%s days'
              {" AND project_name = %s" if project else ""}
              {" AND account = %s" if account else ""}
            GROUP BY model
        """, [days * 2, days] + ([project] if project else []) + ([account] if account else []),
            fetch=True)
        for r in (prev_model_rows or []):
            prev_cost += calculate_cost(r["model"], r["input_t"], r["output_t"])

    def trend(current, previous):
        if not previous:
            return None
        if previous == 0:
            return 100 if current > 0 else 0
        return round((current - previous) / previous * 100, 1)

    t = totals
    p = prev_totals or {}
    sessions_count = t["sessions"] if t else 0
    duration_ms = t["total_duration_ms"] if t else 0

    return jsonify({
        "sessions": sessions_count,
        "duration_ms": duration_ms,
        "duration_formatted": format_duration(duration_ms),
        "total_input": t["total_input"] if t else 0,
        "total_output": t["total_output"] if t else 0,
        "total_tokens": (t["total_input"] or 0) + (t["total_output"] or 0) if t else 0,
        "total_cost": round(total_cost, 2),
        "total_cost_formatted": format_cost(total_cost),
        "total_messages": t["total_messages"] if t else 0,
        "avg_duration_ms": round(duration_ms / sessions_count) if sessions_count else 0,
        "avg_duration_formatted": format_duration(round(duration_ms / sessions_count)) if sessions_count else "0s",
        "avg_cost": round(total_cost / sessions_count, 2) if sessions_count else 0,
        "trends": {
            "sessions": trend(t["sessions"] if t else 0, p.get("sessions", 0)),
            "duration": trend(t["total_duration_ms"] if t else 0, p.get("total_duration_ms", 0)),
            "tokens": trend((t["total_input"] or 0) + (t["total_output"] or 0) if t else 0,
                           (p.get("total_input") or 0) + (p.get("total_output") or 0)),
            "cost": trend(total_cost, prev_cost),
        },
        "days": days,
    })


@timesheets_bp.route('/api/timesheets/daily')
@api_route
def api_timesheets_daily():
    """Tagesweise Aggregation fuer Charts"""
    where, params, days, project, account = _build_timesheet_filter()

    rows = execute(f"""
        SELECT
            DATE(started_at) as day,
            COUNT(*) as sessions,
            COALESCE(SUM(duration_ms), 0) as duration_ms,
            COALESCE(SUM(total_input_tokens), 0) as tokens_in,
            COALESCE(SUM(total_output_tokens), 0) as tokens_out,
            COALESCE(SUM(user_message_count), 0) as messages
        FROM sessions {where}
        GROUP BY DATE(started_at)
        ORDER BY day
    """, params, fetch=True)

    result = []
    for r in (rows or []):
        cost = calculate_cost(None, r["tokens_in"], r["tokens_out"])
        result.append({
            "date": r["day"].isoformat(),
            "sessions": r["sessions"],
            "duration_ms": r["duration_ms"],
            "duration_h": round(r["duration_ms"] / 3600000, 1),
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "cost": round(cost, 2),
            "messages": r["messages"],
        })

    return jsonify(result)


@timesheets_bp.route('/api/timesheets/projects')
@api_route
def api_timesheets_projects():
    """Top-Projekte nach Zeit/Tokens/Kosten"""
    sort = request.args.get('sort', 'cost')
    where, params, days, project, account = _build_timesheet_filter()

    rows = execute(f"""
        SELECT
            project_name,
            COUNT(*) as sessions,
            COALESCE(SUM(duration_ms), 0) as duration_ms,
            COALESCE(SUM(total_input_tokens), 0) as tokens_in,
            COALESCE(SUM(total_output_tokens), 0) as tokens_out,
            COALESCE(SUM(user_message_count), 0) as messages,
            COALESCE(SUM(assistant_message_count), 0) as responses,
            array_agg(DISTINCT model) FILTER (WHERE model IS NOT NULL AND model != '' AND model NOT LIKE '<%>') as models,
            array_agg(DISTINCT account) as accounts
        FROM sessions {where}
        GROUP BY project_name
        ORDER BY SUM(total_input_tokens + total_output_tokens) DESC
    """, params, fetch=True)

    result = []
    for r in (rows or []):
        cost = calculate_cost(None, r["tokens_in"], r["tokens_out"])
        result.append({
            "project": r["project_name"],
            "sessions": r["sessions"],
            "duration_ms": r["duration_ms"],
            "duration_formatted": format_duration(r["duration_ms"]),
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "cost": round(cost, 2),
            "cost_formatted": format_cost(cost),
            "messages": r["messages"],
            "models": r["models"] or [],
            "accounts": r["accounts"] or [],
        })

    sort_keys = {
        "cost": lambda x: x["cost"],
        "duration": lambda x: x["duration_ms"],
        "sessions": lambda x: x["sessions"],
        "tokens": lambda x: x["tokens_in"] + x["tokens_out"],
    }
    result.sort(key=sort_keys.get(sort, sort_keys["cost"]), reverse=True)

    return jsonify(result)


@timesheets_bp.route('/api/timesheets/tools')
@api_route
def api_timesheets_tools():
    """Vergleich nach Account/Tool"""
    days = request.args.get('days', 30, type=int)

    rows = execute("""
        SELECT
            account,
            COUNT(*) as sessions,
            COALESCE(SUM(duration_ms), 0) as duration_ms,
            COALESCE(SUM(total_input_tokens), 0) as tokens_in,
            COALESCE(SUM(total_output_tokens), 0) as tokens_out,
            COALESCE(SUM(user_message_count), 0) as messages,
            COUNT(DISTINCT project_name) as projects
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY account
        ORDER BY SUM(total_input_tokens + total_output_tokens) DESC
    """, (days,), fetch=True)

    result = []
    for r in (rows or []):
        cost = calculate_cost(None, r["tokens_in"], r["tokens_out"])
        result.append({
            "account": r["account"],
            "sessions": r["sessions"],
            "duration_ms": r["duration_ms"],
            "duration_formatted": format_duration(r["duration_ms"]),
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "cost": round(cost, 2),
            "cost_formatted": format_cost(cost),
            "messages": r["messages"],
            "projects": r["projects"],
        })

    return jsonify(result)


@timesheets_bp.route('/api/timesheets/models')
@api_route
def api_timesheets_models():
    """Kosten-Aufschluesselung nach Modell"""
    days = request.args.get('days', 30, type=int)

    rows = execute("""
        SELECT
            model,
            COUNT(*) as sessions,
            COALESCE(SUM(total_input_tokens), 0) as tokens_in,
            COALESCE(SUM(total_output_tokens), 0) as tokens_out,
            COALESCE(SUM(duration_ms), 0) as duration_ms
        FROM sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY model
        ORDER BY SUM(total_input_tokens + total_output_tokens) DESC
    """, (days,), fetch=True)

    result = []
    for r in (rows or []):
        cost = calculate_cost(r["model"], r["tokens_in"], r["tokens_out"])
        result.append({
            "model": r["model"] or "unknown",
            "sessions": r["sessions"],
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "cost": round(cost, 2),
            "cost_formatted": format_cost(cost),
            "duration_formatted": format_duration(r["duration_ms"]),
        })

    return jsonify(result)


# === Rework-Tracking ===

@timesheets_bp.route('/api/timesheets/rework')
@api_route
def api_timesheets_rework():
    """Rework-Statistiken"""
    where, params, days, project, account = _build_timesheet_filter()

    # Outcome-Verteilung
    dist = execute(f"""
        SELECT
            COALESCE(outcome, 'unrated') as outcome,
            COUNT(*) as cnt
        FROM sessions {where}
        GROUP BY COALESCE(outcome, 'unrated')
    """, params, fetch=True)

    distribution = {r["outcome"]: r["cnt"] for r in (dist or [])}
    total = sum(distribution.values())
    rated = total - distribution.get("unrated", 0)
    rework = distribution.get("needs_fix", 0) + distribution.get("reverted", 0)
    rework_rate = round(rework / rated * 100, 1) if rated > 0 else 0

    # Rework-Rate pro Projekt
    by_project = execute(f"""
        SELECT project_name,
               COUNT(*) FILTER (WHERE outcome IS NOT NULL) as rated,
               COUNT(*) FILTER (WHERE outcome IN ('needs_fix','reverted')) as rework,
               COUNT(*) as total
        FROM sessions {where}
        GROUP BY project_name
        HAVING COUNT(*) FILTER (WHERE outcome IS NOT NULL) > 0
        ORDER BY COUNT(*) FILTER (WHERE outcome IN ('needs_fix','reverted')) DESC
    """, params, fetch=True)

    projects = []
    for r in (by_project or []):
        r_rated = r["rated"]
        r_rework = r["rework"]
        projects.append({
            "project": r["project_name"],
            "total": r["total"],
            "rated": r_rated,
            "rework": r_rework,
            "rate": round(r_rework / r_rated * 100, 1) if r_rated > 0 else 0,
        })

    # Wochen-Trend
    trend = execute(f"""
        SELECT
            DATE_TRUNC('week', started_at)::date as week,
            COUNT(*) FILTER (WHERE outcome IS NOT NULL) as rated,
            COUNT(*) FILTER (WHERE outcome IN ('needs_fix','reverted')) as rework
        FROM sessions {where}
        GROUP BY DATE_TRUNC('week', started_at)
        ORDER BY week
    """, params, fetch=True)

    weeks = []
    for r in (trend or []):
        w_rated = r["rated"]
        w_rework = r["rework"]
        weeks.append({
            "week": r["week"].isoformat(),
            "rated": w_rated,
            "rework": w_rework,
            "rate": round(w_rework / w_rated * 100, 1) if w_rated > 0 else 0,
        })

    # Kosten nach Outcome
    cost_rows = execute(f"""
        SELECT
            COALESCE(outcome, 'unrated') as outcome,
            SUM(total_input_tokens) as inp,
            SUM(total_output_tokens) as out,
            SUM(cache_read_tokens) as cr,
            SUM(cache_creation_tokens) as cc
        FROM sessions {where}
        GROUP BY COALESCE(outcome, 'unrated')
    """, params, fetch=True)

    costs = {}
    for r in (cost_rows or []):
        c = calculate_cost(None, r["inp"], r["out"], r["cr"], r["cc"])
        costs[r["outcome"]] = round(c, 2)

    wasted = costs.get("reverted", 0)
    fixcost = costs.get("needs_fix", 0)
    effective = costs.get("ok", 0) + costs.get("partial", 0)

    # Reason-Distribution (Sprint 9)
    reason_rows = execute(f"""
        SELECT outcome_reason, COUNT(*) as cnt
        FROM sessions {where} AND outcome_reason IS NOT NULL
        GROUP BY outcome_reason
        ORDER BY cnt DESC
    """, params, fetch=True)

    reason_total = sum(r["cnt"] for r in (reason_rows or []))
    reason_distribution = [
        {"reason": r["outcome_reason"], "count": r["cnt"],
         "pct": round(r["cnt"] / reason_total * 100, 1) if reason_total else 0}
        for r in (reason_rows or [])
    ]

    # Reason by Model (Sprint 9)
    rbm_rows = execute(f"""
        SELECT model, outcome_reason, COUNT(*) as cnt
        FROM sessions {where} AND outcome_reason IS NOT NULL
            AND model IS NOT NULL AND model NOT LIKE '<%%>'
        GROUP BY model, outcome_reason
        ORDER BY model, cnt DESC
    """, params, fetch=True)

    reason_by_model = {}
    for r in (rbm_rows or []):
        m = r["model"]
        if m not in reason_by_model:
            reason_by_model[m] = {}
        reason_by_model[m][r["outcome_reason"]] = r["cnt"]

    # Reason by Project (Sprint 9.3)
    rbp_rows = execute(f"""
        SELECT project_name, outcome_reason, COUNT(*) as cnt
        FROM sessions {where} AND outcome_reason IS NOT NULL AND project_name IS NOT NULL
        GROUP BY project_name, outcome_reason
        ORDER BY project_name, cnt DESC
    """, params, fetch=True)

    reason_by_project = {}
    for r in (rbp_rows or []):
        p = r["project_name"]
        if p not in reason_by_project:
            reason_by_project[p] = {}
        reason_by_project[p][r["outcome_reason"]] = r["cnt"]

    # Reason Trend (Sprint 9.3) - woechentlich pro Reason
    rt_rows = execute(f"""
        SELECT DATE_TRUNC('week', started_at)::date as week, outcome_reason, COUNT(*) as cnt
        FROM sessions {where} AND outcome_reason IS NOT NULL
        GROUP BY week, outcome_reason
        ORDER BY week
    """, params, fetch=True)

    reason_trend = {}
    for r in (rt_rows or []):
        w = r["week"].isoformat()
        if w not in reason_trend:
            reason_trend[w] = {}
        reason_trend[w][r["outcome_reason"]] = r["cnt"]

    return jsonify({
        "total_sessions": total,
        "rated_sessions": rated,
        "distribution": distribution,
        "rework_rate": rework_rate,
        "reason_distribution": reason_distribution,
        "reason_by_model": reason_by_model,
        "reason_by_project": reason_by_project,
        "reason_trend": reason_trend,
        "top_3_reasons": [r["reason"] for r in reason_distribution[:3]],
        "costs": {
            "wasted": wasted,
            "wasted_formatted": format_cost(wasted),
            "fix_cost": fixcost,
            "fix_cost_formatted": format_cost(fixcost),
            "effective": effective,
            "effective_formatted": format_cost(effective),
            "by_outcome": costs,
        },
        "by_project": projects,
        "trend": weeks,
    })


# Context Effectiveness: siehe context_routes.py
