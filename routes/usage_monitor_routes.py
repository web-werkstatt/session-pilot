"""
Usage Monitor: Real-time per-account usage with burn rates, limits, predictions.
Rolling 5-hour billing window per account.
"""
import json
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, render_template
from services.db_service import execute
from services.cost_service import calculate_cost
from services.account_discovery import discover_all_accounts
from routes.api_utils import api_route

usage_monitor_bp = Blueprint('usage_monitor', __name__)

PLANS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'account_plans.json')

PLAN_PRESETS = {
    "pro": {"cost_limit": 18, "message_limit": 250},
    "max5": {"cost_limit": 35, "message_limit": 1000},
    "max20": {"cost_limit": 140, "message_limit": 2000},
}


def _load_plans():
    if os.path.exists(PLANS_FILE):
        with open(PLANS_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_plans(plans):
    with open(PLANS_FILE, 'w') as f:
        json.dump(plans, f, indent=2)


@usage_monitor_bp.route('/usage-monitor')
def usage_monitor_page():
    return render_template('usage_monitor.html', active_page='usage_monitor')


@usage_monitor_bp.route('/api/usage-monitor')
@api_route
def api_usage_monitor():
    plans = _load_plans()
    accounts_info = discover_all_accounts()
    account_names = [a["name"] for a in accounts_info]

    # Sessions from last 5 hours grouped by account + model
    rows = execute("""
        SELECT
            s.account,
            s.model,
            COUNT(DISTINCT s.id) as session_count,
            COALESCE(SUM(s.user_message_count), 0) as user_messages,
            COALESCE(SUM(s.total_input_tokens), 0) as input_tokens,
            COALESCE(SUM(s.total_output_tokens), 0) as output_tokens,
            COALESCE(SUM(s.cache_read_tokens), 0) as cache_read,
            COALESCE(SUM(s.cache_creation_tokens), 0) as cache_create,
            MIN(s.started_at) as first_session,
            MAX(s.started_at) as last_session
        FROM sessions s
        WHERE s.started_at >= NOW() - INTERVAL '5 hours'
        GROUP BY s.account, s.model
    """, fetch=True)

    # Build per-account data
    acct_data = {}
    for r in (rows or []):
        name = r["account"] or "unknown"
        if name not in acct_data:
            acct_data[name] = {
                "models": [],
                "total_cost": 0, "total_tokens": 0,
                "input_tokens": 0, "output_tokens": 0,
                "cache_read": 0, "cache_create": 0,
                "messages": 0, "sessions": 0,
                "first_session": None, "last_session": None,
            }
        a = acct_data[name]

        cost = calculate_cost(
            r["model"], r["input_tokens"], r["output_tokens"],
            r["cache_read"], r["cache_create"]
        )
        tokens = (r["input_tokens"] or 0) + (r["output_tokens"] or 0)

        a["models"].append({
            "model": r["model"] or "unknown",
            "cost": round(cost, 2),
            "tokens": tokens,
            "messages": r["user_messages"],
            "sessions": r["session_count"],
        })
        a["total_cost"] += cost
        a["total_tokens"] += tokens
        a["input_tokens"] += r["input_tokens"] or 0
        a["output_tokens"] += r["output_tokens"] or 0
        a["cache_read"] += r["cache_read"] or 0
        a["cache_create"] += r["cache_create"] or 0
        a["messages"] += r["user_messages"]
        a["sessions"] += r["session_count"]

        fs = r["first_session"]
        ls = r["last_session"]
        if fs and (a["first_session"] is None or fs < a["first_session"]):
            a["first_session"] = fs
        if ls and (a["last_session"] is None or ls > a["last_session"]):
            a["last_session"] = ls

    now = datetime.now(timezone.utc)
    result = []

    # Include all known accounts (even idle ones)
    all_names = sorted(set(account_names) | set(acct_data.keys()))

    for name in all_names:
        plan_cfg = plans.get(name, {"plan": "pro", "cost_limit": 18, "message_limit": 250})
        plan_name = plan_cfg.get("plan", "pro")
        cost_limit = plan_cfg.get("cost_limit", PLAN_PRESETS.get(plan_name, {}).get("cost_limit", 18))
        msg_limit = plan_cfg.get("message_limit", PLAN_PRESETS.get(plan_name, {}).get("message_limit", 250))

        a = acct_data.get(name)
        if not a:
            result.append({
                "name": name, "plan": plan_name,
                "cost_limit": cost_limit, "message_limit": msg_limit,
                "cost_used": 0, "cost_pct": 0,
                "tokens_used": 0, "input_tokens": 0, "output_tokens": 0,
                "messages_used": 0, "messages_pct": 0,
                "session_count": 0, "elapsed_minutes": 0,
                "window_reset_minutes": 300,
                "burn_rate_cost": 0, "burn_rate_tokens": 0,
                "prediction_cost_min": None, "prediction_msg_min": None,
                "models": [], "active": False,
            })
            continue

        # Elapsed time in current window
        elapsed_min = 0
        reset_min = 300
        if a["first_session"]:
            fs_utc = a["first_session"]
            if fs_utc.tzinfo is None:
                fs_utc = fs_utc.replace(tzinfo=timezone.utc)
            elapsed_min = max(1, (now - fs_utc).total_seconds() / 60)
            reset_min = max(0, 300 - elapsed_min)

        total_cost = round(a["total_cost"], 2)
        cost_pct = round(total_cost / cost_limit * 100, 1) if cost_limit > 0 else 0
        msg_pct = round(a["messages"] / msg_limit * 100, 1) if msg_limit > 0 else 0

        # Burn rates
        burn_cost = round(total_cost / elapsed_min, 4) if elapsed_min > 0 else 0
        burn_tokens = round(a["total_tokens"] / elapsed_min, 0) if elapsed_min > 0 else 0

        # Predictions: minutes until limit hit
        pred_cost = None
        if burn_cost > 0 and total_cost < cost_limit:
            pred_cost = round((cost_limit - total_cost) / burn_cost)
        pred_msg = None
        burn_msg = a["messages"] / elapsed_min if elapsed_min > 0 else 0
        if burn_msg > 0 and a["messages"] < msg_limit:
            pred_msg = round((msg_limit - a["messages"]) / burn_msg)

        result.append({
            "name": name, "plan": plan_name,
            "cost_limit": cost_limit, "message_limit": msg_limit,
            "cost_used": total_cost, "cost_pct": min(cost_pct, 100),
            "tokens_used": a["total_tokens"],
            "input_tokens": a["input_tokens"], "output_tokens": a["output_tokens"],
            "cache_read": a["cache_read"], "cache_create": a["cache_create"],
            "messages_used": a["messages"], "messages_pct": min(msg_pct, 100),
            "session_count": a["sessions"],
            "elapsed_minutes": round(elapsed_min),
            "window_reset_minutes": round(reset_min),
            "burn_rate_cost": burn_cost, "burn_rate_tokens": int(burn_tokens),
            "prediction_cost_min": pred_cost, "prediction_msg_min": pred_msg,
            "models": sorted(a["models"], key=lambda m: m["cost"], reverse=True),
            "active": True,
        })

    # Sort: active accounts first, then by cost desc
    result.sort(key=lambda x: (-int(x["active"]), -x["cost_used"]))

    return jsonify({
        "accounts": result,
        "plan_presets": PLAN_PRESETS,
        "timestamp": now.isoformat(),
    })


@usage_monitor_bp.route('/api/usage-monitor/plans', methods=['POST'])
@api_route
def api_usage_monitor_save_plan():
    data = request.get_json()
    if not data or not data.get('account'):
        return jsonify({"error": "Account name required"}), 400

    plans = _load_plans()
    account = data['account']
    plan_name = data.get('plan', 'pro')
    preset = PLAN_PRESETS.get(plan_name, PLAN_PRESETS['pro'])

    plans[account] = {
        "plan": plan_name,
        "cost_limit": data.get('cost_limit', preset['cost_limit']),
        "message_limit": data.get('message_limit', preset['message_limit']),
    }
    _save_plans(plans)
    return jsonify({"success": True})
