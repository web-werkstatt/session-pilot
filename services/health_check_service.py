"""
Health Check Service - HTTP-Checks fuer laufende Services
Prueft konfigurierte URLs aus project.json oder leitet sie aus Port ab.
"""
import ssl
import urllib.request
from datetime import datetime

# In-Memory Cache (2 Minuten TTL)
_health_cache = {"data": {}, "updated_at": None}
_HEALTH_CACHE_TTL = 120  # Sekunden


def check_health(url, timeout=5):
    """Prueft ob eine URL erreichbar ist.
    Returns: {"status": "up"|"down"|"error", "code": int|None, "ms": int}
    """
    result = {"status": "down", "code": None, "ms": 0, "url": url}
    start = datetime.now()
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, method="GET", headers={
            "User-Agent": "ProjectDashboard-HealthCheck/1.0"
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            result["code"] = resp.status
            result["status"] = "up" if 200 <= resp.status < 400 else "error"
    except urllib.error.HTTPError as e:
        result["code"] = e.code
        result["status"] = "error" if e.code >= 500 else "up"  # 4xx = erreichbar
    except Exception:
        result["status"] = "down"

    elapsed = (datetime.now() - start).total_seconds() * 1000
    result["ms"] = int(elapsed)
    return result


def get_health_for_project(project_name, port=None, health_url=None):
    """Health-Check fuer ein Projekt. Nutzt health_url aus project.json oder baut URL aus Port.
    Returns: dict oder None (wenn kein Port/URL konfiguriert)
    """
    global _health_cache

    # Cache pruefen
    if _health_cache["updated_at"]:
        age = (datetime.now() - _health_cache["updated_at"]).total_seconds()
        if age < _HEALTH_CACHE_TTL and project_name in _health_cache["data"]:
            return _health_cache["data"][project_name]

    url = health_url
    if not url and port:
        url = f"http://localhost:{port}"

    if not url:
        return None

    result = check_health(url)

    # Cache speichern
    _health_cache["data"][project_name] = result
    _health_cache["updated_at"] = datetime.now()

    return result
