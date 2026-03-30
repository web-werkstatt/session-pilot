"""
Usage Monitor: Real-time per-account usage with burn rates, limits, predictions.
Liest JSONL-Dateien direkt fuer Echtzeit-Daten.
Nutzt OTel-Daten (echte Anthropic-Werte) wenn verfuegbar, P90 als Fallback.
"""
from flask import Blueprint, jsonify, request, render_template
from services.usage_live_service import get_live_usage, calculate_p90_limits, _default_limits
from services.account_discovery import discover_all_accounts
from services.otel_store import get_rate_limits
from routes.api_utils import api_route

usage_monitor_bp = Blueprint('usage_monitor', __name__)


@usage_monitor_bp.route('/usage-monitor')
def usage_monitor_page():
    return render_template('usage_monitor.html', active_page='usage_monitor')


@usage_monitor_bp.route('/api/usage-monitor/live')
@api_route
def api_usage_monitor_live():
    """Live-Daten aus JSONL + OTel-Metriken."""
    window_hours = request.args.get('window', 5, type=int)
    if window_hours not in (1, 2, 5, 12, 24, 48):
        window_hours = 5

    live_data = get_live_usage(window_hours)

    # Try to get real OTel rate-limit data from Anthropic
    otel_data = get_rate_limits()
    otel_available = otel_data is not None and otel_data.get("age_seconds", 999) < 300

    # Calculate P90 limits per account (fallback)
    all_accounts = discover_all_accounts()
    p90_limits = {}
    for acc in all_accounts:
        if acc["tool"] == "claude":
            p90_limits[acc["name"]] = calculate_p90_limits(acc["config_dir"])

    accounts = []
    for name, acct in live_data["accounts"].items():
        limits = p90_limits.get(name)
        if limits is None:
            limits = _default_limits()

        # Use OTel data if available (primary account only for now)
        if otel_available and acct["active"]:
            acct["limits_method"] = "otel"
            # OTel gives us the real used_percentage directly
            session_pct = otel_data.get("session_used_pct")
            if session_pct is not None:
                acct["cost_pct"] = round(session_pct, 1)
                # Back-calculate limit from percentage and actual cost
                if session_pct > 0:
                    acct["cost_limit"] = round(acct["total_cost"] / session_pct * 100, 2)
                else:
                    acct["cost_limit"] = limits["cost_limit"]
            else:
                acct["cost_pct"] = round(acct["total_cost"] / limits["cost_limit"] * 100, 1) if limits["cost_limit"] > 0 else 0
                acct["cost_limit"] = limits["cost_limit"]

            # OTel reset time
            if otel_data.get("session_resets_at"):
                acct["window_reset_time"] = otel_data["session_resets_at"]

            # Week data
            acct["week_used_pct"] = otel_data.get("week_used_pct")
            acct["week_resets_at"] = otel_data.get("week_resets_at")

            # Token/message limits from P90 (OTel doesn't give these separately)
            acct["token_limit"] = limits["token_limit"]
            acct["message_limit"] = limits["message_limit"]
            acct["tokens_pct"] = round(acct["billable_tokens"] / limits["token_limit"] * 100, 1) if limits["token_limit"] > 0 else 0
            acct["messages_pct"] = round(acct["user_messages"] / limits["message_limit"] * 100, 1) if limits["message_limit"] > 0 else 0
            acct["limits_sample_blocks"] = limits["sample_blocks"]
            acct["otel_age_seconds"] = round(otel_data.get("age_seconds", 0))
        else:
            # Pure P90 fallback
            cost_limit = limits["cost_limit"]
            msg_limit = limits["message_limit"]
            tok_limit = limits["token_limit"]
            acct["cost_limit"] = cost_limit
            acct["message_limit"] = msg_limit
            acct["token_limit"] = tok_limit
            acct["cost_pct"] = min(round(acct["total_cost"] / cost_limit * 100, 1) if cost_limit > 0 else 0, 100)
            acct["messages_pct"] = min(round(acct["user_messages"] / msg_limit * 100, 1) if msg_limit > 0 else 0, 100)
            acct["tokens_pct"] = min(round(acct["billable_tokens"] / tok_limit * 100, 1) if tok_limit > 0 else 0, 100)
            acct["limits_method"] = limits["method"]
            acct["limits_sample_blocks"] = limits["sample_blocks"]

        # Week data (always from P90/JSONL analysis)
        acct["week_cost"] = limits.get("week_cost", 0)
        acct["week_tokens"] = limits.get("week_tokens", 0)
        acct["week_messages"] = limits.get("week_messages", 0)
        # Week percentage only from OTel (Anthropic knows the real limit, we don't)
        if otel_available and otel_data.get("week_used_pct") is not None:
            acct["week_used_pct"] = otel_data["week_used_pct"]
        else:
            acct["week_used_pct"] = 0  # unknown without OTel

        # Predictions based on burn rate
        burn = acct["burn_rate"]
        acct["prediction_cost_min"] = None
        if burn["cost_per_min"] > 0 and acct["cost_pct"] < 100:
            remaining_cost = acct["cost_limit"] - acct["total_cost"]
            if remaining_cost > 0:
                acct["prediction_cost_min"] = round(remaining_cost / burn["cost_per_min"])

        acct["prediction_msg_min"] = None
        if acct["user_messages"] > 0 and acct["elapsed_minutes"] > 0:
            msg_rate = acct["user_messages"] / acct["elapsed_minutes"]
            remaining_msg = acct.get("message_limit", 999) - acct["user_messages"]
            if msg_rate > 0 and remaining_msg > 0:
                acct["prediction_msg_min"] = round(remaining_msg / msg_rate)

        acct["prediction_tok_min"] = None
        if burn["tokens_per_min"] > 0 and acct.get("token_limit", 0) > 0:
            remaining_tok = acct["token_limit"] - acct["billable_tokens"]
            if remaining_tok > 0:
                acct["prediction_tok_min"] = round(remaining_tok / burn["tokens_per_min"])

        accounts.append(acct)

    accounts.sort(key=lambda x: (-int(x["active"]), -x["total_cost"]))

    return jsonify({
        "accounts": accounts,
        "window_hours": live_data["window_hours"],
        "timestamp": live_data["timestamp"],
        "otel_available": otel_available,
    })
