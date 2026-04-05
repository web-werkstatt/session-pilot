"""
Session Validation Service - Validiert Session-UUIDs gegen Format und Datenbank
"""
import re
import time
import logging
import threading
from functools import wraps
from flask import jsonify, request, redirect, url_for

logger = logging.getLogger(__name__)

# Session-ID-Format: Buchstaben/Ziffern plus `_` und `-`, max 64 Zeichen.
# Das deckt klassische UUIDs, `sess-123` sowie Formate wie `ses_...` von Kilo/OpenCode ab.
_UUID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{8,64}$')

# Rate-Limiting: max 100 Validierungen pro IP pro Minute
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 100
_rate_limit_store = {}
_rate_limit_lock = threading.Lock()


def validate_uuid_format(uuid_str):
    """
    Prueft ob eine Session-UUID dem erwarteten Format entspricht.
    Verhindert Injection durch strikte Whitelist-Validierung.
    """
    if not uuid_str or not isinstance(uuid_str, str):
        return False, "missing_or_invalid_uuid"
    if len(uuid_str) > 64:
        return False, "uuid_too_long"
    if not _UUID_PATTERN.match(uuid_str):
        return False, "uuid_format_invalid"
    return True, None


def _check_rate_limit(ip_address):
    """
    Prueft Rate-Limit fuer eine IP-Adresse.
    Gibt True zurueck wenn Anfrage erlaubt ist, False wenn Limit erreicht.
    """
    now = time.time()
    with _rate_limit_lock:
        if ip_address not in _rate_limit_store:
            _rate_limit_store[ip_address] = []
        timestamps = _rate_limit_store[ip_address]
        timestamps[:] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(timestamps) >= _RATE_LIMIT_MAX:
            return False
        timestamps.append(now)
        return True


def validate_session_exists(session_uuid):
    """
    Prueft ob eine Session mit der gegebenen UUID in der Datenbank existiert.
    Gibt (True, session_data) oder (False, error_reason) zurueck.
    """
    from services.db_service import execute

    try:
        session = execute(
            "SELECT session_uuid, project_name, account, started_at, ended_at, outcome "
            "FROM sessions WHERE session_uuid = %s",
            (session_uuid,),
            fetchone=True
        )
        if not session:
            return False, "session_not_found"
        return True, dict(session)
    except Exception as e:
        logger.error(f"Session validation DB error for {session_uuid}: {e}")
        return False, "database_error"


def validate_session_path(session_uuid, ip_address=None):
    """
    Vollstaendige Validierung eines Session-Pfades:
    1. Format-Check (UUID-Struktur)
    2. Rate-Limit-Check (optional, wenn IP gegeben)
    3. Datenbank-Existenz-Check

    Gibt Dict zurueck mit:
    - valid: bool
    - status: "valid" | "invalid_format" | "rate_limited" | "not_found" | "db_error"
    - session: dict (nur wenn valid=True)
    - error: str (nur wenn valid=False)
    """
    result = {"valid": False}

    format_ok, format_error = validate_uuid_format(session_uuid)
    if not format_ok:
        logger.warning(f"Invalid session UUID format: {session_uuid} ({format_error})")
        result.update({"status": "invalid_format", "error": format_error})
        return result

    if ip_address and not _check_rate_limit(ip_address):
        logger.warning(f"Rate limit exceeded for session validation: {ip_address}")
        result.update({"status": "rate_limited", "error": "rate_limit_exceeded"})
        return result

    exists, session_or_error = validate_session_exists(session_uuid)
    if not exists:
        if session_or_error == "database_error":
            result.update({"status": "db_error", "error": "database_error"})
        else:
            logger.warning(f"Session not found in DB: {session_uuid}")
            result.update({"status": "not_found", "error": "session_not_found"})
        return result

    result.update({"valid": True, "status": "valid", "session": session_or_error})
    return result


def validate_session(f):
    """
    Decorator fuer Flask-Routes, die eine gueltige Session-UUID erwarten.
    Bei ungueltiger UUID: 400/404/429 JSON-Response.
    Bei gueltiger UUID: ruft die dekorierte Funktion mit session_uuid auf.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        session_uuid = kwargs.get('uuid') or kwargs.get('session_uuid')
        if not session_uuid:
            return jsonify({"error": "Missing session UUID"}), 400

        ip_address = request.remote_addr
        validation = validate_session_path(session_uuid, ip_address)

        if validation["status"] == "invalid_format":
            return jsonify({"error": f"Invalid session UUID format: {validation['error']}"}), 400

        if validation["status"] == "rate_limited":
            return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

        if validation["status"] == "not_found":
            return jsonify({"error": "Session not found"}), 404

        if validation["status"] == "db_error":
            return jsonify({"error": "Internal server error during session lookup"}), 500

        return f(*args, **kwargs)
    return wrapper


def validate_session_page(f):
    """
    Decorator fuer Flask-Page-Routes (HTML).
    Bei ungueltiger UUID: Redirect zur Session-Liste mit Flash-Message.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        session_uuid = kwargs.get('uuid') or kwargs.get('session_uuid')
        if not session_uuid:
            return redirect(url_for('sessions.sessions_page'))

        ip_address = request.remote_addr
        validation = validate_session_path(session_uuid, ip_address)

        if not validation["valid"]:
            if validation["status"] in ("invalid_format", "not_found"):
                return redirect(url_for('sessions.sessions_page'))
            return jsonify({"error": "Internal server error"}), 500

        return f(*args, **kwargs)
    return wrapper
