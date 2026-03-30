"""
Live Usage Monitor Service.
Liest JSONL Session-Dateien direkt fuer Echtzeit-Metriken.
Inspiriert von github.com/Maciek-roboblog/Claude-Code-Usage-Monitor
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from services.account_discovery import discover_all_accounts
from services.cost_service import calculate_cost
from services.usage_limits import calculate_p90_limits as _calc_p90, _default_limits

# Cache to avoid re-reading unchanged files
_file_cache = {}  # path -> (mtime, size, entries)


def get_live_usage(window_hours=5):
    """Liest alle JSONL-Dateien und berechnet Live-Metriken pro Account.

    Returns dict with per-account usage data including:
    - Token counts (input, output, cache_read, cache_create)
    - Cost breakdown per model
    - Session blocks (5h windows)
    - Burn rates and predictions
    - Message counts
    """
    accounts = discover_all_accounts()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    result = {}

    for account in accounts:
        if account["tool"] != "claude":
            continue

        name = account["name"]
        config_dir = account["config_dir"]
        projects_dir = os.path.join(config_dir, "projects")

        if not os.path.isdir(projects_dir):
            continue

        entries = _read_all_jsonl_entries(projects_dir, cutoff)
        if not entries:
            result[name] = _empty_account(name, window_hours)
            continue

        result[name] = _analyze_entries(name, entries, now, window_hours)

    return {
        "accounts": result,
        "timestamp": now.isoformat(),
        "window_hours": window_hours,
    }


def _read_all_jsonl_entries(projects_dir, cutoff):
    """Liest alle JSONL-Dateien im projects-Verzeichnis."""
    entries = []
    projects_path = Path(projects_dir)

    for jsonl_file in projects_path.rglob("*.jsonl"):
        # Skip subagent files for main count (but include for tokens)
        file_entries = _read_jsonl_cached(str(jsonl_file), cutoff)
        entries.extend(file_entries)

    entries.sort(key=lambda e: e["timestamp"])
    return entries


def _read_jsonl_cached(filepath, cutoff):
    """Liest JSONL mit Cache basierend auf mtime."""
    global _file_cache
    try:
        stat = os.stat(filepath)
        mtime = stat.st_mtime
        size = stat.st_size
    except OSError:
        return []

    cache_key = filepath
    cached = _file_cache.get(cache_key)
    if cached and cached[0] == mtime and cached[1] == size:
        # Return filtered by cutoff
        return [e for e in cached[2] if e["timestamp"] >= cutoff]

    # Read and parse
    all_entries = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = _parse_entry(data)
                    if entry:
                        all_entries.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        return []

    _file_cache[cache_key] = (mtime, size, all_entries)
    return [e for e in all_entries if e["timestamp"] >= cutoff]


def _parse_entry(data):
    """Parst einen JSONL-Eintrag in ein normalisiertes Format."""
    entry_type = data.get("type")

    if entry_type == "assistant":
        msg = data.get("message", {})
        usage = msg.get("usage", {})
        if not usage:
            return None

        ts_str = data.get("timestamp")
        if not ts_str:
            return None

        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

        return {
            "type": "assistant",
            "timestamp": ts,
            "model": msg.get("model", "unknown"),
            "input_tokens": usage.get("input_tokens", 0) or 0,
            "output_tokens": usage.get("output_tokens", 0) or 0,
            "cache_creation": usage.get("cache_creation_input_tokens", 0) or 0,
            "cache_read": usage.get("cache_read_input_tokens", 0) or 0,
            "session_id": data.get("sessionId"),
            "request_id": data.get("requestId"),
            "is_subagent": "/subagents/" in str(data.get("uuid", "")),
        }

    if entry_type == "user":
        ts_str = data.get("timestamp")
        if not ts_str:
            return None
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        return {
            "type": "user",
            "timestamp": ts,
            "session_id": data.get("sessionId"),
        }

    return None


def _analyze_entries(name, entries, now, window_hours):
    """Analysiert Entries und berechnet alle Metriken."""
    window_min = window_hours * 60

    # Separate user/assistant entries
    user_msgs = [e for e in entries if e["type"] == "user"]
    api_calls = [e for e in entries if e["type"] == "assistant"]

    if not api_calls:
        return _empty_account(name, window_hours)

    # Aggregate tokens per model
    models = {}
    totals = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read": 0, "cache_create": 0,
        "cost": 0.0, "api_calls": 0,
    }

    for e in api_calls:
        model = e["model"]
        if model not in models:
            models[model] = {
                "input_tokens": 0, "output_tokens": 0,
                "cache_read": 0, "cache_create": 0,
                "cost": 0.0, "api_calls": 0,
            }
        m = models[model]

        inp = e["input_tokens"]
        out = e["output_tokens"]
        cr = e["cache_read"]
        cc = e["cache_creation"]

        m["input_tokens"] += inp
        m["output_tokens"] += out
        m["cache_read"] += cr
        m["cache_create"] += cc
        m["api_calls"] += 1

        cost = calculate_cost(model, inp, out, cr, cc)
        m["cost"] += cost

        totals["input_tokens"] += inp
        totals["output_tokens"] += out
        totals["cache_read"] += cr
        totals["cache_create"] += cc
        totals["cost"] += cost
        totals["api_calls"] += 1

    # Billable tokens (input+output) - used for limits
    billable_tokens = totals["input_tokens"] + totals["output_tokens"]
    # Total tokens including cache - for informational display
    total_tokens = billable_tokens + totals["cache_read"] + totals["cache_create"]

    # Time range - use rounded block start for reset calculation (like Anthropic)
    first_ts = api_calls[0]["timestamp"]
    last_ts = api_calls[-1]["timestamp"]
    block_start = first_ts.replace(minute=0, second=0, microsecond=0)
    elapsed_min = max(1, (now - first_ts).total_seconds() / 60)
    block_elapsed = (now - block_start).total_seconds() / 60
    reset_min = max(0, window_min - block_elapsed)

    # Burn rates (based on billable tokens for limit predictions)
    burn_tokens_min = billable_tokens / elapsed_min if elapsed_min > 0 else 0
    burn_cost_min = totals["cost"] / elapsed_min if elapsed_min > 0 else 0
    burn_cost_hour = burn_cost_min * 60

    # Recent burn rate (last 30 min for more accurate short-term prediction)
    recent_cutoff = now - timedelta(minutes=30)
    recent_calls = [e for e in api_calls if e["timestamp"] >= recent_cutoff]
    recent_tokens = sum(
        e["input_tokens"] + e["output_tokens"]
        for e in recent_calls
    )
    recent_cost = sum(
        calculate_cost(e["model"], e["input_tokens"], e["output_tokens"],
                       e["cache_read"], e["cache_creation"])
        for e in recent_calls
    )
    recent_elapsed = max(1, (now - recent_cutoff).total_seconds() / 60)
    recent_burn_tokens = recent_tokens / recent_elapsed
    recent_burn_cost = recent_cost / recent_elapsed

    # Session blocks (5h windows)
    blocks = _build_session_blocks(api_calls, user_msgs, now)

    # Model breakdown for response
    model_list = []
    for model_name, stats in sorted(models.items(), key=lambda x: -x[1]["cost"]):
        model_billable = stats["input_tokens"] + stats["output_tokens"]
        model_tokens = model_billable + stats["cache_read"] + stats["cache_create"]
        pct = round(model_billable / billable_tokens * 100, 1) if billable_tokens > 0 else 0
        model_list.append({
            "model": model_name,
            "input_tokens": stats["input_tokens"],
            "output_tokens": stats["output_tokens"],
            "cache_read": stats["cache_read"],
            "cache_create": stats["cache_create"],
            "total_tokens": model_tokens,
            "cost": round(stats["cost"], 4),
            "api_calls": stats["api_calls"],
            "pct": pct,
        })

    # Unique sessions
    session_ids = set(e.get("session_id") for e in entries if e.get("session_id"))

    return {
        "name": name,
        "active": True,
        "billable_tokens": billable_tokens,
        "total_tokens": total_tokens,
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "cache_read": totals["cache_read"],
        "cache_create": totals["cache_create"],
        "total_cost": round(totals["cost"], 4),
        "api_calls": totals["api_calls"],
        "user_messages": len(user_msgs),
        "session_count": len(session_ids),
        "elapsed_minutes": round(elapsed_min),
        "window_reset_minutes": round(reset_min),
        "window_reset_time": (block_start + timedelta(hours=window_hours)).isoformat(),
        "window_hours": window_hours,
        "first_activity": first_ts.isoformat(),
        "last_activity": last_ts.isoformat(),
        # Burn rates
        "burn_rate": {
            "tokens_per_min": round(burn_tokens_min),
            "cost_per_min": round(burn_cost_min, 4),
            "cost_per_hour": round(burn_cost_hour, 4),
            "recent_tokens_per_min": round(recent_burn_tokens),
            "recent_cost_per_min": round(recent_burn_cost, 4),
        },
        # Model breakdown
        "models": model_list,
        # Session blocks
        "blocks": blocks,
    }


def _build_session_blocks(api_calls, user_msgs, now):
    """Baut 5-Stunden Session-Bloecke aus Entries."""
    if not api_calls:
        return []

    blocks = []
    block_duration = timedelta(hours=5)

    # Group by 5h windows starting from rounded hour
    current_block = None

    for entry in api_calls:
        ts = entry["timestamp"]

        if current_block is None or ts >= current_block["_end_dt"]:
            if current_block:
                _finalize_block(current_block, now)
                blocks.append(current_block)
            # Start new block at rounded hour
            start = ts.replace(minute=0, second=0, microsecond=0)
            current_block = {
                "start_time": start.isoformat(),
                "end_time": (start + block_duration).isoformat(),
                "_end_dt": start + block_duration,
                "input_tokens": 0, "output_tokens": 0,
                "cache_read": 0, "cache_create": 0,
                "cost": 0.0, "api_calls": 0, "messages": 0,
                "models": {},
                "is_active": False,
                "last_activity": None,
            }

        inp = entry["input_tokens"]
        out = entry["output_tokens"]
        cr = entry["cache_read"]
        cc = entry["cache_creation"]
        model = entry["model"]

        current_block["input_tokens"] += inp
        current_block["output_tokens"] += out
        current_block["cache_read"] += cr
        current_block["cache_create"] += cc
        current_block["api_calls"] += 1
        current_block["last_activity"] = ts.isoformat()

        cost = calculate_cost(model, inp, out, cr, cc)
        current_block["cost"] += cost

        if model not in current_block["models"]:
            current_block["models"][model] = {"tokens": 0, "cost": 0.0, "calls": 0}
        current_block["models"][model]["tokens"] += inp + out + cr + cc
        current_block["models"][model]["cost"] += cost
        current_block["models"][model]["calls"] += 1

    if current_block:
        _finalize_block(current_block, now)
        blocks.append(current_block)

    # Count user messages per block
    for block in blocks:
        start = datetime.fromisoformat(block["start_time"])
        end = datetime.fromisoformat(block["end_time"])
        block["messages"] = sum(
            1 for m in user_msgs if start <= m["timestamp"] < end
        )

    return blocks


def _finalize_block(block, now):
    """Finalisiert einen Block."""
    end_dt = block.pop("_end_dt")
    block["is_active"] = now < end_dt
    total = (block["input_tokens"] + block["output_tokens"]
             + block["cache_read"] + block["cache_create"])
    block["total_tokens"] = total
    block["cost"] = round(block["cost"], 4)
    # Convert models dict to list
    block["models"] = [
        {"model": k, "tokens": v["tokens"], "cost": round(v["cost"], 4), "calls": v["calls"]}
        for k, v in sorted(block["models"].items(), key=lambda x: -x[1]["cost"])
    ]


def _empty_account(name, window_hours):
    """Leerer Account ohne Aktivitaet."""
    return {
        "name": name,
        "active": False,
        "billable_tokens": 0,
        "total_tokens": 0,
        "input_tokens": 0, "output_tokens": 0,
        "cache_read": 0, "cache_create": 0,
        "total_cost": 0, "api_calls": 0,
        "user_messages": 0, "session_count": 0,
        "elapsed_minutes": 0,
        "window_reset_minutes": window_hours * 60,
        "window_reset_time": None,
        "window_hours": window_hours,
        "first_activity": None, "last_activity": None,
        "burn_rate": {
            "tokens_per_min": 0, "cost_per_min": 0, "cost_per_hour": 0,
            "recent_tokens_per_min": 0, "recent_cost_per_min": 0,
        },
        "models": [],
        "blocks": [],
    }


def calculate_p90_limits(config_dir):
    """Wrapper fuer P90-Berechnung aus usage_limits.py."""
    return _calc_p90(config_dir, _read_all_jsonl_entries)
