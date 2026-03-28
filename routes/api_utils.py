"""
Zentrale API-Utilities fuer Route-Handler.
Vermeidet dupliziertes try/except in jedem Endpoint.
"""
from functools import wraps
from flask import jsonify


def api_route(f):
    """Decorator fuer API-Endpoints: Faengt Exceptions und gibt JSON-Error zurueck.

    Usage:
        @bp.route('/api/example')
        @api_route
        def api_example():
            return jsonify({"data": "..."})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return wrapper
