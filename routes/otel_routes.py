"""
OTLP Receiver Endpoints.
Empfaengt OpenTelemetry Metriken und Logs von Claude Code.
"""
from flask import Blueprint, request, jsonify
from services.otel_store import store_metrics_from_otlp, store_metrics_from_json, get_metrics, get_rate_limits

otel_bp = Blueprint('otel', __name__)


@otel_bp.route('/v1/metrics', methods=['POST'])
def otlp_metrics():
    """OTLP HTTP Metrics Receiver."""
    content_type = request.content_type or ''

    if 'protobuf' in content_type:
        store_metrics_from_otlp(request.data)
    elif 'json' in content_type:
        store_metrics_from_json(request.get_json(silent=True) or {})
    else:
        # Try protobuf first, fall back to JSON
        try:
            store_metrics_from_otlp(request.data)
        except Exception:
            try:
                store_metrics_from_json(request.get_json(silent=True) or {})
            except Exception:
                return '', 400

    return '', 200


@otel_bp.route('/v1/logs', methods=['POST'])
def otlp_logs():
    """OTLP HTTP Logs Receiver (accept and ignore for now)."""
    return '', 200


@otel_bp.route('/api/otel/metrics')
def api_otel_metrics():
    """Debug-Endpoint: zeigt alle empfangenen OTel-Metriken."""
    return jsonify({
        "metrics": get_metrics(),
        "rate_limits": get_rate_limits(),
    })
