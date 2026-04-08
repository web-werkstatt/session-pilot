"""
Zentrale API-Utilities fuer Route-Handler.
Vermeidet dupliziertes try/except in jedem Endpoint.
"""
from functools import wraps
from flask import jsonify, request


READ_ONLY_FALLBACKS = {
    "/api/settings/accounts": [],
    "/api/settings/pricing": [],
    "/api/settings/system": {
        "projects_dir": "",
        "gitea_url": "",
        "gitea_user": "",
        "host": "",
        "port": 0,
        "db_host": "",
        "db_port": 0,
        "db_name": "",
        "db_size": "?",
        "total_sessions": 0,
        "total_messages": 0,
        "pricing_models": 0,
    },
    "/api/sessions/filters": {
        "accounts": [],
        "projects": [],
        "models": [],
        "outcomes": {},
        "scope": {},
        "project_defaults": {},
    },
    "/api/sessions/scope-stats": {"stats": {}, "top_tools": []},
    "/api/timesheets/summary": {},
    "/api/timesheets/daily": [],
    "/api/timesheets/projects": [],
    "/api/timesheets/models": [],
    "/api/timesheets/tools": [],
    "/api/timesheets/rework": {},
    "/api/timesheets/context-changes": [],
    "/api/timesheets/context-effectiveness": {"changes": [], "summary": []},
    "/api/analytics/model-comparison": {},
    "/api/analytics/model-by-stack": {},
    "/api/analytics/model-recommendation": {},
    "/api/analytics/model-trend": {},
    "/api/llm/commands": {"commands": []},
    "/api/llm/commands/runs": {"runs": []},
}


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
            if request.method == "GET":
                fallback = READ_ONLY_FALLBACKS.get(request.path)
                if fallback is not None:
                    return jsonify(fallback), 200
            return jsonify({"error": str(e)}), 500
    return wrapper
