"""
Usage Reports Service.
Aggregiert JSONL-Daten nach Tag/Woche/Monat fuer Auswertungen.
"""
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from services.account_discovery import discover_all_accounts
from services.cost_service import calculate_cost
from services.usage_live_service import read_all_jsonl_entries

# Result cache (60s TTL)
_report_cache = {}
_CACHE_TTL = 60


def get_usage_report(period_type, start_date, end_date):
    """Aggregiert Usage-Daten fuer einen Zeitraum.

    Args:
        period_type: 'daily' | 'weekly' | 'monthly'
        start_date: datetime (UTC)
        end_date: datetime (UTC)

    Returns:
        dict with rows, summary, model_distribution, hourly
    """
    cache_key = (period_type, start_date.isoformat(), end_date.isoformat())
    cached = _report_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    entries = _collect_entries(start_date, end_date)
    api_calls = [e for e in entries if e["type"] == "assistant"]
    user_msgs = [e for e in entries if e["type"] == "user"]

    if not api_calls:
        result = _empty_report(period_type, start_date, end_date)
        _report_cache[cache_key] = {"data": result, "ts": time.time()}
        return result

    rows = _group_entries(period_type, api_calls, user_msgs, start_date, end_date)
    summary = _build_summary(rows, start_date, end_date)
    model_dist = _build_model_distribution(api_calls)
    hourly = _build_hourly(api_calls) if period_type == "daily" else []

    result = {
        "period_type": period_type,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows,
        "summary": summary,
        "model_distribution": model_dist,
        "hourly": hourly,
    }

    _report_cache[cache_key] = {"data": result, "ts": time.time()}
    return result


def _collect_entries(start_date, end_date):
    """Sammelt alle JSONL-Entries aller Claude-Accounts im Zeitraum."""
    accounts = discover_all_accounts()
    all_entries = []

    for account in accounts:
        if account["tool"] != "claude":
            continue
        projects_dir = os.path.join(account["config_dir"], "projects")
        if not os.path.isdir(projects_dir):
            continue
        entries = read_all_jsonl_entries(projects_dir, start_date)
        filtered = [e for e in entries if e["timestamp"] <= end_date]
        all_entries.extend(filtered)

    all_entries.sort(key=lambda e: e["timestamp"])
    return all_entries


def _group_entries(period_type, api_calls, user_msgs, start_date, end_date):
    """Gruppiert Entries nach Periode und berechnet Metriken pro Gruppe."""
    groups = defaultdict(lambda: {
        "cost": 0.0, "input_tokens": 0, "output_tokens": 0,
        "cache_read": 0, "cache_create": 0, "messages": 0,
        "sessions": set(), "api_calls": 0, "models": defaultdict(lambda: {"cost": 0.0, "tokens": 0}),
    })

    for e in api_calls:
        key = _period_key(period_type, e["timestamp"])
        g = groups[key]
        inp, out = e["input_tokens"], e["output_tokens"]
        cr, cc = e["cache_read"], e["cache_creation"]
        cost = calculate_cost(e["model"], inp, out, cr, cc)

        g["cost"] += cost
        g["input_tokens"] += inp
        g["output_tokens"] += out
        g["cache_read"] += cr
        g["cache_create"] += cc
        g["api_calls"] += 1
        if e.get("session_id"):
            g["sessions"].add(e["session_id"])

        model_short = _shorten_model(e["model"])
        g["models"][model_short]["cost"] += cost
        g["models"][model_short]["tokens"] += inp + out

    for m in user_msgs:
        key = _period_key(period_type, m["timestamp"])
        groups[key]["messages"] += 1

    rows = []
    for key in sorted(groups.keys()):
        g = groups[key]
        models = {k: {"cost": round(v["cost"], 4), "tokens": v["tokens"]}
                  for k, v in g["models"].items()}
        rows.append({
            "date": key,
            "cost": round(g["cost"], 2),
            "input_tokens": g["input_tokens"],
            "output_tokens": g["output_tokens"],
            "cache_read": g["cache_read"],
            "cache_create": g["cache_create"],
            "messages": g["messages"],
            "sessions": len(g["sessions"]),
            "api_calls": g["api_calls"],
            "models": models,
        })

    return rows


def _period_key(period_type, ts):
    """Erzeugt den Gruppierungs-Key fuer eine Periode."""
    if period_type == "daily":
        return ts.strftime("%Y-%m-%d")
    elif period_type == "weekly":
        # ISO week: Monday as start
        monday = ts - timedelta(days=ts.weekday())
        return monday.strftime("%Y-%m-%d")
    elif period_type == "monthly":
        return ts.strftime("%Y-%m")
    return ts.strftime("%Y-%m-%d")


def _build_summary(rows, start_date, end_date):
    """Berechnet Zusammenfassung ueber alle Rows."""
    if not rows:
        return _empty_summary()

    total_cost = sum(r["cost"] for r in rows)
    total_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in rows)
    total_cache = sum(r["cache_read"] + r["cache_create"] for r in rows)
    total_messages = sum(r["messages"] for r in rows)
    total_sessions = sum(r["sessions"] for r in rows)
    total_api_calls = sum(r["api_calls"] for r in rows)
    days = max(1, (end_date - start_date).days)

    return {
        "total_cost": round(total_cost, 2),
        "total_tokens": total_tokens,
        "total_cache": total_cache,
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "total_api_calls": total_api_calls,
        "avg_daily_cost": round(total_cost / days, 2),
        "avg_daily_tokens": round(total_tokens / days),
        "days": days,
        "periods": len(rows),
    }


def _build_model_distribution(api_calls):
    """Berechnet Modell-Verteilung."""
    models = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})

    for e in api_calls:
        model = _shorten_model(e["model"])
        cost = calculate_cost(e["model"], e["input_tokens"], e["output_tokens"],
                              e["cache_read"], e["cache_creation"])
        models[model]["cost"] += cost
        models[model]["tokens"] += e["input_tokens"] + e["output_tokens"]
        models[model]["calls"] += 1

    total_cost = sum(m["cost"] for m in models.values())
    result = []
    for name, m in sorted(models.items(), key=lambda x: -x[1]["cost"]):
        pct = round(m["cost"] / total_cost * 100, 1) if total_cost > 0 else 0
        result.append({
            "model": name,
            "cost": round(m["cost"], 2),
            "tokens": m["tokens"],
            "calls": m["calls"],
            "pct": pct,
        })
    return result


def _build_hourly(api_calls):
    """Berechnet stuendliche Verteilung (nur fuer daily)."""
    hours = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "messages": 0, "calls": 0})

    for e in api_calls:
        h = e["timestamp"].hour
        cost = calculate_cost(e["model"], e["input_tokens"], e["output_tokens"],
                              e["cache_read"], e["cache_creation"])
        hours[h]["cost"] += cost
        hours[h]["tokens"] += e["input_tokens"] + e["output_tokens"]
        hours[h]["calls"] += 1

    return [{"hour": h, "cost": round(hours[h]["cost"], 2),
             "tokens": hours[h]["tokens"], "calls": hours[h]["calls"]}
            for h in range(24)]


def _shorten_model(model):
    """Kuerzt Modellname fuer Anzeige."""
    import re
    name = model.replace("claude-", "")
    name = re.sub(r"-20\d{6,}", "", name)
    name = re.sub(r"\[.*\]", "", name)
    return name


def _empty_report(period_type, start_date, end_date):
    return {
        "period_type": period_type,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": [],
        "summary": _empty_summary(),
        "model_distribution": [],
        "hourly": [],
    }


def _empty_summary():
    return {
        "total_cost": 0, "total_tokens": 0, "total_cache": 0,
        "total_messages": 0, "total_sessions": 0, "total_api_calls": 0,
        "avg_daily_cost": 0, "avg_daily_tokens": 0, "days": 0, "periods": 0,
    }
