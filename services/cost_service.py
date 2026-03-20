"""
Kostenberechnung fuer AI-Coding-Sessions.
Modell-Preise aus DB (model_pricing), Cache mit 30s TTL.
"""
import time

_pricing_cache = None
_pricing_cache_ts = 0
_CACHE_TTL = 30

DEFAULT_PRICING = {
    "input": 3.0, "output": 15.0,
    "cache_read_factor": 0.1, "cache_create_factor": 1.25,
}


def _load_pricing():
    """Laedt Preise aus DB mit Cache"""
    global _pricing_cache, _pricing_cache_ts
    now = time.time()
    if _pricing_cache is not None and (now - _pricing_cache_ts) < _CACHE_TTL:
        return _pricing_cache

    try:
        from services.db_service import execute
        rows = execute(
            "SELECT model_pattern, input_price, output_price, cache_read_factor, cache_create_factor FROM model_pricing",
            fetch=True
        )
        pricing = {}
        for r in (rows or []):
            pricing[r["model_pattern"].lower()] = {
                "input": float(r["input_price"]),
                "output": float(r["output_price"]),
                "cache_read_factor": float(r["cache_read_factor"] or 0.1),
                "cache_create_factor": float(r["cache_create_factor"] or 1.25),
            }
        _pricing_cache = pricing
        _pricing_cache_ts = now
        return pricing
    except Exception:
        return _pricing_cache or {}


def get_model_price(model_name):
    """Gibt Preise fuer ein Modell zurueck (Fuzzy-Match aus DB)"""
    if not model_name:
        return DEFAULT_PRICING

    pricing = _load_pricing()
    model_lower = model_name.lower()

    # Exakter Match
    if model_lower in pricing:
        return pricing[model_lower]

    # Substring-Match (z.B. "claude-opus-4-6-20250301" matched "claude-opus-4-6")
    for key, price in pricing.items():
        if key in model_lower:
            return price

    # Prefix-Match (z.B. "gpt-4o-2024" matched "gpt-4o")
    for key, price in pricing.items():
        if model_lower.startswith(key):
            return price

    return DEFAULT_PRICING


def calculate_cost(model, input_tokens, output_tokens, cache_read=0, cache_create=0):
    """Berechnet Kosten in USD. Cache-Tokens werden separat bepreist."""
    pricing = get_model_price(model)
    cr_factor = pricing.get("cache_read_factor", 0.1)
    cc_factor = pricing.get("cache_create_factor", 1.25)

    cost_in = float(input_tokens or 0) / 1_000_000 * pricing["input"]
    cost_cache_read = float(cache_read or 0) / 1_000_000 * pricing["input"] * cr_factor
    cost_cache_create = float(cache_create or 0) / 1_000_000 * pricing["input"] * cc_factor
    cost_out = float(output_tokens or 0) / 1_000_000 * pricing["output"]
    return round(cost_in + cost_cache_read + cost_cache_create + cost_out, 4)


def format_cost(cost_usd):
    """Formatiert Kosten als String"""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    if cost_usd < 1:
        return f"${cost_usd:.2f}"
    return f"${cost_usd:,.2f}"


def get_tool_for_model(model_name):
    """Leitet das AI-Tool aus dem Modellnamen ab"""
    if not model_name:
        return "unknown"
    m = model_name.lower()
    if "claude" in m:
        return "claude"
    if "gpt" in m or "o3" in m or "o4" in m or "codex" in m:
        return "codex"
    if "gemini" in m:
        return "gemini"
    if "amazon" in m or "nova" in m:
        return "amazonq"
    return "other"
