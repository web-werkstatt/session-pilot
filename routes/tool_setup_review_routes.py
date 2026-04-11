"""
ADR-002 Stufe 1a: REST-Endpoints fuer Setup-Reviewer.

Zwei Endpoints:
- POST /api/project/<name>/tool-setup/review — fuehrt Review durch, persistiert
- GET  /api/project/<name>/tool-setup/review — liefert letztes gespeichertes Ergebnis

Der Reviewer ist Read-Only fuer Runtime-Artefakte. Tool-Files werden nicht
geschrieben — der Schreibweg geht weiterhin ueber den bestehenden
tool_profile_adapter-Endpoint (nach Joseph-Freigabe).
"""
import logging

from flask import Blueprint, jsonify, request

from services.path_resolver import resolve_project_path
from services.tool_setup_review import load_review, review_tool_setup

log = logging.getLogger(__name__)

tool_setup_review_bp = Blueprint("tool_setup_review", __name__)


@tool_setup_review_bp.route(
    "/api/project/<path:name>/tool-setup/review", methods=["POST"]
)
def trigger_review(name):
    """Fuehrt einen Setup-Review aus und persistiert das Ergebnis.

    Body (optional): {"force": true} erzwingt einen neuen Perplexity-Call,
    auch wenn der context_hash identisch zum letzten Review ist.
    """
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))

    try:
        result = review_tool_setup(name, force=force)
    except Exception as exc:
        log.exception("Setup-Review fehlgeschlagen fuer %s", name)
        return (
            jsonify(
                {
                    "project": name,
                    "error": "internal_error",
                    "detail": str(exc),
                }
            ),
            500,
        )

    if result.get("error") == "project_not_found":
        return jsonify({"error": "Project not found"}), 404

    # query_failed und parse_failed sind **kein** HTTP-Fehler:
    # der Reviewer-Flow hat funktioniert, nur die Antwort war unbrauchbar.
    # Die UI muss den Fehler als eigenen State anzeigen koennen.
    return jsonify({"project": name, "result": result}), 200


@tool_setup_review_bp.route(
    "/api/project/<path:name>/tool-setup/review", methods=["GET"]
)
def get_review(name):
    """Liefert letztes gespeichertes Setup-Review ohne neuen Perplexity-Call."""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    try:
        result = load_review(name)
    except Exception as exc:
        log.exception("Setup-Review Load fehlgeschlagen fuer %s", name)
        return (
            jsonify(
                {
                    "project": name,
                    "error": "internal_error",
                    "detail": str(exc),
                }
            ),
            500,
        )

    return jsonify({"project": name, "result": result}), 200
