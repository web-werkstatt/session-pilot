"""
Security Scanner - npm audit / pip-audit Ergebnisse
Cached pro Projekt (10 Minuten TTL, da Scan langsam ist).
"""
import json
import os
import subprocess
from datetime import datetime

# In-Memory Cache (10 Minuten TTL - Scans sind teuer)
_security_cache = {"data": {}, "updated_at": {}}
_SECURITY_CACHE_TTL = 600  # Sekunden


def scan_npm_audit(project_path):
    """Fuehrt npm audit aus und gibt Zusammenfassung zurueck.
    Returns: {"total": int, "critical": int, "high": int, "moderate": int, "low": int}
    """
    result = {"total": 0, "critical": 0, "high": 0, "moderate": 0, "low": 0}

    if not os.path.exists(os.path.join(project_path, "package-lock.json")):
        # Ohne lock-file kein npm audit moeglich
        if os.path.exists(os.path.join(project_path, "package.json")):
            return {"total": -1, "note": "no_lockfile"}
        return None

    try:
        r = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=project_path,
            capture_output=True, text=True, timeout=10
        )
        # npm audit gibt returncode != 0 bei Vulnerabilities
        data = json.loads(r.stdout) if r.stdout else {}

        # npm audit v2+ Format
        vulns = data.get("metadata", {}).get("vulnerabilities", {})
        if vulns:
            result["critical"] = vulns.get("critical", 0)
            result["high"] = vulns.get("high", 0)
            result["moderate"] = vulns.get("moderate", 0)
            result["low"] = vulns.get("low", 0)
            result["total"] = vulns.get("total", sum(result.values()))
            return result

        # Fallback: aelteres Format
        advisories = data.get("advisories", {})
        for adv in advisories.values():
            sev = adv.get("severity", "low")
            if sev in result:
                result[sev] += 1
            result["total"] += 1

    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    return result


def scan_pip_audit(project_path):
    """Fuehrt pip-audit aus (falls installiert) oder zaehlt bekannte Patterns.
    Returns: {"total": int, "critical": int, "high": int, "moderate": int, "low": int}
    """
    result = {"total": 0, "critical": 0, "high": 0, "moderate": 0, "low": 0}

    has_requirements = os.path.exists(os.path.join(project_path, "requirements.txt"))
    has_pyproject = os.path.exists(os.path.join(project_path, "pyproject.toml"))
    if not has_requirements and not has_pyproject:
        return None

    # Versuche pip-audit (wenn installiert)
    try:
        args = ["pip-audit", "--format=json"]
        if has_requirements:
            args.extend(["-r", os.path.join(project_path, "requirements.txt")])

        r = subprocess.run(
            args,
            cwd=project_path,
            capture_output=True, text=True, timeout=10
        )
        if r.stdout:
            data = json.loads(r.stdout)
            # pip-audit gibt Liste von Vulnerabilities
            if isinstance(data, list):
                result["total"] = len(data)
                # pip-audit hat kein Severity-Feld, alles als "moderate"
                result["moderate"] = len(data)
            elif isinstance(data, dict) and "dependencies" in data:
                for dep in data["dependencies"]:
                    vulns = dep.get("vulns", [])
                    result["total"] += len(vulns)
                    result["moderate"] += len(vulns)
            return result
    except FileNotFoundError:
        # pip-audit nicht installiert - kein Fehler
        return {"total": 0, "critical": 0, "high": 0, "moderate": 0, "low": 0, "note": "pip_audit_not_installed"}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    return result


def get_security_for_project(project_name, project_path):
    """Security-Scan fuer ein Projekt (cached).
    Returns: {"type": "npm"|"pip"|None, "vulnerabilities": {...}} oder None
    """
    global _security_cache

    # Cache pruefen
    if project_name in _security_cache["updated_at"]:
        age = (datetime.now() - _security_cache["updated_at"][project_name]).total_seconds()
        if age < _SECURITY_CACHE_TTL and project_name in _security_cache["data"]:
            return _security_cache["data"][project_name]

    result = None

    # npm-Projekt?
    if os.path.exists(os.path.join(project_path, "package.json")):
        vulns = scan_npm_audit(project_path)
        if vulns is not None:
            result = {"type": "npm", "vulnerabilities": vulns}

    # Python-Projekt?
    if not result:
        if os.path.exists(os.path.join(project_path, "requirements.txt")) or \
           os.path.exists(os.path.join(project_path, "pyproject.toml")):
            vulns = scan_pip_audit(project_path)
            if vulns is not None:
                result = {"type": "pip", "vulnerabilities": vulns}

    if result:
        _security_cache["data"][project_name] = result
        _security_cache["updated_at"][project_name] = datetime.now()

    return result
