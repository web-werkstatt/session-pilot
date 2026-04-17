"""
Sprint sprint-agent-orchestrator-executor-handoff Commit 1 (2026-04-17):
Einfacher Shared-Secret-Check fuer den Prompt-Export-Endpunkt.

v1-Policy:
  * Token liegt als Plaintext in ~/.agent-task-token (erste nicht-leere Zeile,
    getrimmt).
  * Fehlt die Datei oder fehlt der Header, Antwort 401.
  * Header-Name: X-Agent-Task-Token.

Bewusst KEIN globales before_request-Hook. Die Auth-Pruefung wird einzeln auf
dem neuen /prompt-Endpunkt aufgerufen, damit AC5 aus dem Sprint
(`44 bestehende Agent-Orchestrator-Tests bleiben gruen`) ohne Anpassung an
den bisherigen Routen einhaltbar bleibt. Spaetere Sprints (Commit 2 CLI-Helper)
koennen den Schutz auf weitere Endpunkte ausweiten.
"""
from pathlib import Path

from flask import jsonify, request


TOKEN_HEADER = "X-Agent-Task-Token"
DEFAULT_TOKEN_PATH = Path.home() / ".agent-task-token"


def _read_configured_token(token_path=None):
    """Liest den konfigurierten Token oder None, wenn nicht vorhanden/lesbar."""
    path = Path(token_path) if token_path else DEFAULT_TOKEN_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    return stripped
    except (FileNotFoundError, OSError):
        return None
    return None


def check_agent_task_token(token_path=None):
    """Prueft den X-Agent-Task-Token Header.

    Rueckgabe:
      * None, wenn der Token gueltig ist (Route darf weitermachen).
      * Tuple `(flask_response, 401)`, wenn der Check fehlschlaegt. Der Caller
        gibt das Tuple direkt aus seiner Route zurueck:

            err = check_agent_task_token()
            if err is not None:
                return err

    Fehlerfaelle (alle -> 401):
      * keine Token-Datei / nicht lesbar
      * fehlender Header
      * falscher Token
    """
    configured = _read_configured_token(token_path=token_path)
    if not configured:
        return jsonify({"error": "agent task token not configured"}), 401
    supplied = (request.headers.get(TOKEN_HEADER) or "").strip()
    if not supplied:
        return jsonify({"error": "missing X-Agent-Task-Token"}), 401
    if supplied != configured:
        return jsonify({"error": "invalid agent task token"}), 401
    return None
