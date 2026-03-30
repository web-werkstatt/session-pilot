"""
P90-basierte Limit-Berechnung fuer den Usage Monitor.
Analysiert historische 5h-Bloecke und berechnet dynamische Limits.
"""
import os
import time
from datetime import datetime, timedelta, timezone
from services.cost_service import calculate_cost

# P90 limits cache (recalculated every 30min)
_p90_cache = {}
_P90_TTL = 1800


def calculate_p90_limits(config_dir, read_entries_fn):
    """Berechnet P90-basierte Limits aus historischen 5h-Bloecken (letzte 8 Tage).

    Args:
        config_dir: Pfad zum Claude Config-Verzeichnis
        read_entries_fn: Funktion zum Lesen der JSONL-Entries (projects_dir, cutoff) -> list
    """
    global _p90_cache

    cache_key = config_dir
    cached = _p90_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _P90_TTL:
        return cached["limits"]

    projects_dir = os.path.join(config_dir, "projects")
    if not os.path.isdir(projects_dir):
        return _default_limits()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=192)  # 8 days

    entries = read_entries_fn(projects_dir, cutoff)
    api_calls = [e for e in entries if e["type"] == "assistant"]

    if len(api_calls) < 10:
        return _default_limits()

    # Group into 5h blocks
    block_duration = timedelta(hours=5)
    blocks_data = []
    current_start = None
    current_end = None
    current = {"cost": 0.0, "tokens": 0, "messages": 0}

    user_msgs = [e for e in entries if e["type"] == "user"]

    for e in api_calls:
        ts = e["timestamp"]
        block_start = ts.replace(minute=0, second=0, microsecond=0)

        if current_start is None or ts >= current_end:
            if current_start is not None and current["tokens"] > 0:
                current["messages"] = sum(
                    1 for m in user_msgs if current_start <= m["timestamp"] < current_end
                )
                blocks_data.append(current)
            current_start = block_start
            current_end = block_start + block_duration
            current = {"cost": 0.0, "tokens": 0, "messages": 0}

        current["tokens"] += e["input_tokens"] + e["output_tokens"]
        current["cost"] += calculate_cost(
            e["model"], e["input_tokens"], e["output_tokens"],
            e["cache_read"], e["cache_creation"]
        )

    if current_start is not None and current["tokens"] > 0:
        current["messages"] = sum(
            1 for m in user_msgs if current_start <= m["timestamp"] < current_end
        )
        blocks_data.append(current)

    if len(blocks_data) < 2:
        return _default_limits()

    def p90(values):
        s = sorted(values)
        idx = int(len(s) * 0.9)
        return s[min(idx, len(s) - 1)]

    # 7-day totals from the same data
    week_cutoff = now - timedelta(days=7)
    week_api = [e for e in api_calls if e["timestamp"] >= week_cutoff]
    week_cost = sum(
        calculate_cost(e["model"], e["input_tokens"], e["output_tokens"],
                       e["cache_read"], e["cache_creation"])
        for e in week_api
    )
    week_tokens = sum(e["input_tokens"] + e["output_tokens"] for e in week_api)
    week_msgs = sum(1 for e in entries if e["type"] == "user" and e["timestamp"] >= week_cutoff)

    limits = {
        "cost_limit": round(p90([b["cost"] for b in blocks_data]) * 1.1, 2),
        "token_limit": int(p90([b["tokens"] for b in blocks_data]) * 1.1),
        "message_limit": max(250, int(p90([b["messages"] for b in blocks_data]) * 1.1)),
        "method": "p90",
        "sample_blocks": len(blocks_data),
        "week_cost": round(week_cost, 2),
        "week_tokens": week_tokens,
        "week_messages": week_msgs,
    }

    _p90_cache[cache_key] = {"limits": limits, "ts": time.time()}
    return limits


def _default_limits():
    """Fallback-Limits wenn nicht genug Daten fuer P90."""
    return {
        "cost_limit": 140,
        "token_limit": 220000,
        "message_limit": 2000,
        "method": "default",
        "sample_blocks": 0,
        "week_cost": 0,
        "week_tokens": 0,
        "week_messages": 0,
    }
