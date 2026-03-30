"""
OpenTelemetry Metrics Store.
Empfaengt OTLP-Metriken von Claude Code und speichert sie in Memory + JSON.
Stellt die echten Rate-Limit-Daten (used_percentage, resets_at) bereit.
"""
import json
import os
import time
import threading

_STORE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.otel_metrics.json')
_lock = threading.Lock()

# In-memory store: { metric_name: { "value": ..., "ts": ..., "attributes": {...} } }
_metrics = {}
_last_update = 0


def get_metrics():
    """Gibt alle gespeicherten Metriken zurueck."""
    global _metrics, _last_update
    # Load from file if memory is empty
    if not _metrics and os.path.exists(_STORE_FILE):
        try:
            with open(_STORE_FILE, 'r') as f:
                data = json.load(f)
                _metrics = data.get("metrics", {})
                _last_update = data.get("last_update", 0)
        except Exception:
            pass
    return _metrics.copy()


def get_rate_limits():
    """Gibt die echten Rate-Limit-Daten zurueck, falls verfuegbar.

    Returns dict with:
        session_used_pct: float (0-100)
        session_resets_at: str (ISO timestamp)
        week_used_pct: float (0-100)
        week_resets_at: str (ISO timestamp)
        cost_usd: float
        last_update: float (unix timestamp)
    Or None if no OTel data available.
    """
    metrics = get_metrics()
    if not metrics:
        return None

    result = {
        "last_update": _last_update,
        "age_seconds": time.time() - _last_update if _last_update else None,
    }

    # Map known metric names to our fields
    # Claude Code exports these (exact names may vary):
    for name, data in metrics.items():
        val = data.get("value")
        attrs = data.get("attributes", {})

        if "cost" in name and "usd" in name:
            result["cost_usd"] = val
        elif "used_percentage" in name or "used_pct" in name:
            # Distinguish 5h vs 7-day window by attributes or name
            window = attrs.get("window", "")
            if "week" in name or "7" in window or "weekly" in window:
                result["week_used_pct"] = val
                if "resets_at" in attrs:
                    result["week_resets_at"] = attrs["resets_at"]
            else:
                result["session_used_pct"] = val
                if "resets_at" in attrs:
                    result["session_resets_at"] = attrs["resets_at"]
        elif "resets_at" in name:
            if "week" in name:
                result["week_resets_at"] = val
            else:
                result["session_resets_at"] = val
        elif "input_tokens" in name and "cache" not in name:
            result["input_tokens"] = val
        elif "output_tokens" in name:
            result["output_tokens"] = val
        elif "cache_read" in name:
            result["cache_read_tokens"] = val
        elif "cache_creation" in name:
            result["cache_creation_tokens"] = val
        elif "duration_ms" in name and "api" not in name:
            result["duration_ms"] = val
        elif "context" in name and "used" in name:
            result["context_used_pct"] = val

    return result if len(result) > 2 else None


def store_metrics_from_otlp(data_bytes):
    """Parst OTLP protobuf und speichert Metriken."""
    global _metrics, _last_update

    try:
        from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
            ExportMetricsServiceRequest,
        )

        request = ExportMetricsServiceRequest()
        request.ParseFromString(data_bytes)

        with _lock:
            for resource_metrics in request.resource_metrics:
                for scope_metrics in resource_metrics.scope_metrics:
                    for metric in scope_metrics.metrics:
                        _process_metric(metric)

            _last_update = time.time()
            _persist()

    except ImportError:
        print("OTel proto not installed, cannot parse metrics")
    except Exception as e:
        print(f"OTel parse error: {e}")


def store_metrics_from_json(data_dict):
    """Parst OTLP JSON und speichert Metriken (Fallback wenn kein protobuf)."""
    global _metrics, _last_update

    try:
        with _lock:
            for rm in data_dict.get("resourceMetrics", []):
                for sm in rm.get("scopeMetrics", []):
                    for m in sm.get("metrics", []):
                        name = m.get("name", "")
                        # Handle gauge, sum, histogram
                        for dtype in ("gauge", "sum"):
                            dps = m.get(dtype, {}).get("dataPoints", [])
                            for dp in dps:
                                val = dp.get("asDouble") or dp.get("asInt", 0)
                                attrs = {}
                                for attr in dp.get("attributes", []):
                                    k = attr.get("key", "")
                                    v = attr.get("value", {})
                                    attrs[k] = v.get("stringValue") or v.get("intValue") or v.get("doubleValue")
                                _metrics[name] = {
                                    "value": val,
                                    "ts": time.time(),
                                    "attributes": attrs,
                                }
            _last_update = time.time()
            _persist()
    except Exception as e:
        print(f"OTel JSON parse error: {e}")


def _process_metric(metric):
    """Verarbeitet eine einzelne protobuf Metric."""
    name = metric.name

    # Handle Gauge
    if metric.gauge.data_points:
        for dp in metric.gauge.data_points:
            val = dp.as_double if dp.as_double else dp.as_int
            attrs = {a.key: _attr_value(a.value) for a in dp.attributes}
            _metrics[name] = {"value": val, "ts": time.time(), "attributes": attrs}

    # Handle Sum
    if metric.sum.data_points:
        for dp in metric.sum.data_points:
            val = dp.as_double if dp.as_double else dp.as_int
            attrs = {a.key: _attr_value(a.value) for a in dp.attributes}
            _metrics[name] = {"value": val, "ts": time.time(), "attributes": attrs}


def _attr_value(v):
    """Extrahiert den Wert aus einem protobuf AnyValue."""
    if v.string_value:
        return v.string_value
    if v.int_value:
        return v.int_value
    if v.double_value:
        return v.double_value
    if v.bool_value:
        return v.bool_value
    return str(v)


def _persist():
    """Speichert Metriken in JSON-Datei."""
    try:
        with open(_STORE_FILE, 'w') as f:
            json.dump({"metrics": _metrics, "last_update": _last_update}, f, indent=2, default=str)
    except Exception:
        pass
