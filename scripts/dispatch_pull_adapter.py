#!/usr/bin/env python3
"""
ADR-002 Stufe 2a, Commit 7: Dispatch Pull-Adapter (Referenz-Implementierung).

Standalone-Script das als Cronjob oder Daemon laeuft und offene
Assignments via Pull-API abholt und an ein CLI-Tool weitergibt.

Konfiguration via Umgebungsvariablen:
    DISPATCH_API_URL    - Dashboard-URL (Default: http://localhost:5055)
    DISPATCH_TOOL_ID    - Tool-ID fuer Pull (z.B. "claude_code", "codex", "gemini_cli")
    DISPATCH_API_KEY    - Bearer-Token fuer Pull-API Auth
    DISPATCH_POLL_SEC   - Poll-Intervall in Sekunden (Default: 60)
    DISPATCH_ONE_SHOT   - Wenn "1": nur einmal pruefen, dann exit (fuer Cron)

Beispiel:
    export DISPATCH_API_URL=http://localhost:5055
    export DISPATCH_TOOL_ID=claude_code
    export DISPATCH_API_KEY=mein-geheimer-key
    python3 scripts/dispatch_pull_adapter.py

Oder als Cron (alle 2 Minuten):
    */2 * * * * DISPATCH_ONE_SHOT=1 DISPATCH_API_KEY=... python3 /pfad/dispatch_pull_adapter.py
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dispatch_pull_adapter")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = os.environ.get("DISPATCH_API_URL", "http://localhost:5055").rstrip("/")
TOOL_ID = os.environ.get("DISPATCH_TOOL_ID", "")
API_KEY = os.environ.get("DISPATCH_API_KEY", "")
POLL_SEC = int(os.environ.get("DISPATCH_POLL_SEC", "60"))
ONE_SHOT = os.environ.get("DISPATCH_ONE_SHOT", "0") == "1"


# ---------------------------------------------------------------------------
# HTTP Helpers
# ---------------------------------------------------------------------------

def _request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
) -> tuple[int, Optional[Dict[str, Any]]]:
    """HTTP-Request an die Dashboard-API. Gibt (status_code, json_body) zurueck."""
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            return status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return e.code, {"error": raw[:500]}
    except urllib.error.URLError as e:
        log.error("Verbindungsfehler: %s", e.reason)
        return 0, None


def pull_next() -> Optional[Dict[str, Any]]:
    """Holt das naechste offene Assignment. Gibt None bei 204 oder Fehler zurueck."""
    status, data = _request("GET", f"/api/dispatch/pull?tool={TOOL_ID}")

    if status == 204:
        return None
    if status == 200 and data:
        return data
    if status == 401:
        log.error("Authentifizierung fehlgeschlagen (401). API_KEY pruefen.")
        return None
    if status == 403:
        log.error("Pull nicht erlaubt fuer Tool '%s' (403).", TOOL_ID)
        return None

    log.warning("Pull-API Status %d: %s", status, data)
    return None


def claim(assignment_id: int) -> Optional[Dict[str, Any]]:
    """Claimed ein Assignment. Gibt Assignment-Daten oder None bei Conflict zurueck."""
    status, data = _request(
        "POST",
        f"/api/dispatch/pull/{assignment_id}/claim",
        body={"claimed_by": TOOL_ID},
    )

    if status == 200 and data:
        return data
    if status == 409:
        log.warning("Assignment %d bereits geclaimed (Race Condition).", assignment_id)
        return None

    log.warning("Claim Status %d: %s", status, data)
    return None


def complete(assignment_id: int, result_ref: Dict[str, Any]) -> bool:
    """Meldet ein Assignment als completed. Gibt True bei Erfolg zurueck."""
    status, data = _request(
        "POST",
        f"/api/dispatch/assignments/{assignment_id}/complete",
        body={"result_ref": result_ref},
    )
    if status == 200:
        return True
    log.warning("Complete Status %d: %s", status, data)
    return False


def fail(assignment_id: int, reason: str) -> bool:
    """Meldet ein Assignment als failed. Gibt True bei Erfolg zurueck."""
    status, data = _request(
        "POST",
        f"/api/dispatch/assignments/{assignment_id}/fail",
        body={"reason": reason},
    )
    if status == 200:
        return True
    log.warning("Fail Status %d: %s", status, data)
    return False


# ---------------------------------------------------------------------------
# Assignment-Verarbeitung
# ---------------------------------------------------------------------------

def build_prompt(assignment: Dict[str, Any]) -> str:
    """Baut einen Prompt-String aus Assignment-Daten."""
    parts = []

    # Marker-Kontext
    marker_id = assignment.get("marker_id", "")
    project = assignment.get("project_name", "")
    if marker_id:
        parts.append(f"Marker: {marker_id} (Projekt: {project})")

    # Scope
    scope = assignment.get("scope_ref")
    if scope and isinstance(scope, dict) and scope:
        parts.append(f"Scope: {json.dumps(scope, ensure_ascii=False)}")

    # Input-Payload (eigentlicher Arbeitsauftrag)
    payload = assignment.get("input_payload")
    if payload and isinstance(payload, dict):
        if payload.get("prompt"):
            parts.append(f"Auftrag: {payload['prompt']}")
        elif payload.get("task"):
            parts.append(f"Aufgabe: {payload['task']}")
        else:
            parts.append(f"Payload: {json.dumps(payload, ensure_ascii=False)}")

    # Risiko-Hinweis
    risk = assignment.get("risk_level", "medium")
    if risk in ("high", "critical"):
        parts.append(f"ACHTUNG: Risiko-Level ist '{risk}'. Besondere Vorsicht.")

    # Write-Scope
    ws = assignment.get("allowed_write_scope")
    if ws and isinstance(ws, list) and ws:
        parts.append(f"Erlaubter Write-Scope: {', '.join(str(s) for s in ws)}")

    return "\n".join(parts)


def execute_tool(assignment: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    """Fuehrt das CLI-Tool mit dem Assignment aus.

    Gibt (success, result_ref) zurueck. Die Default-Implementierung
    loggt nur — spezifische Adapter (Claude, Codex, Gemini) ueberschreiben
    diese Funktion oder nutzen sie als Basis.

    Zum Erweitern: Subclass oder dieses Script als Library importieren
    und execute_tool() ersetzen.
    """
    prompt = build_prompt(assignment)
    aid = assignment["assignment_id"]

    log.info("=== Assignment %d starten ===", aid)
    log.info("Tool: %s | Projekt: %s | Marker: %s",
             assignment.get("executor_tool"),
             assignment.get("project_name"),
             assignment.get("marker_id", "-"))
    log.info("Prompt:\n%s", prompt)

    # Perplexity-Review anzeigen falls vorhanden
    review = assignment.get("perplexity_review")
    if review and isinstance(review, dict):
        rec = review.get("recommendation", "?")
        risk = review.get("risk_assessment", "?")
        fit = review.get("tool_fit_score", "?")
        log.info("Perplexity-Review: recommendation=%s, risk=%s, fit=%s",
                 rec, risk, fit)

    if assignment.get("perplexity_pending"):
        log.warning("Perplexity-Review noch ausstehend. Fortfahren trotzdem.")

    # --- Hier CLI-Aufruf einbauen ---
    # Default: Nur Logging, kein echter CLI-Aufruf.
    # Fuer echte Ausfuehrung: dispatch_pull_adapter_claude.sh oder
    # eigenen Adapter schreiben.
    log.info("(Dry-Run: Kein CLI-Aufruf. Setze DISPATCH_EXECUTE=1 fuer Echtbetrieb.)")

    if os.environ.get("DISPATCH_EXECUTE") == "1":
        return _execute_cli(assignment, prompt)

    return True, {"mode": "dry_run", "prompt_length": len(prompt)}


def _execute_cli(assignment: Dict[str, Any], prompt: str) -> tuple[bool, Dict[str, Any]]:
    """Tatsaechlicher CLI-Aufruf. Adapter-spezifisch.

    Default: claude --print (Claude Code).
    Ueberschreibbar via DISPATCH_CLI_CMD Umgebungsvariable.
    """
    tool = assignment.get("executor_tool", "claude_code")
    project = assignment.get("project_name", "")

    # CLI-Kommando bestimmen
    cli_cmd = os.environ.get("DISPATCH_CLI_CMD", "")
    if not cli_cmd:
        # Defaults pro Tool
        cli_defaults = {
            "claude_code": "claude --print",
            "codex": "codex --quiet",
            "gemini_cli": "gemini",
        }
        cli_cmd = cli_defaults.get(tool, f"echo 'Kein CLI fuer {tool}'")

    # Working Directory bestimmen
    work_dir = f"/mnt/projects/{project}" if project else "."
    if not os.path.isdir(work_dir):
        work_dir = "."

    cmd = f"{cli_cmd} <<'DISPATCH_EOF'\n{prompt}\nDISPATCH_EOF"
    log.info("CLI: %s (cwd=%s)", cli_cmd, work_dir)

    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 Minuten
        )

        output = result.stdout[-5000:] if result.stdout else ""
        stderr = result.stderr[-2000:] if result.stderr else ""

        if result.returncode == 0:
            return True, {
                "exit_code": 0,
                "output_tail": output,
                "output_length": len(result.stdout or ""),
            }
        else:
            return False, {
                "exit_code": result.returncode,
                "stderr_tail": stderr,
                "output_tail": output,
            }

    except subprocess.TimeoutExpired:
        return False, {"error": "timeout", "timeout_sec": 600}
    except Exception as e:
        return False, {"error": str(e)}


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------

def poll_once() -> bool:
    """Ein Poll-Zyklus. Gibt True zurueck wenn ein Assignment verarbeitet wurde."""
    assignment = pull_next()
    if not assignment:
        return False

    aid = assignment["assignment_id"]
    log.info("Neues Assignment gefunden: #%d", aid)

    # Claim
    claimed = claim(aid)
    if not claimed:
        return False

    log.info("Assignment #%d geclaimed.", aid)

    # Ausfuehren
    success, result_ref = execute_tool(claimed)

    # Ergebnis melden
    if success:
        complete(aid, result_ref)
        log.info("Assignment #%d completed.", aid)
    else:
        reason = result_ref.get("error", "CLI execution failed")
        if isinstance(reason, dict):
            reason = json.dumps(reason)
        fail(aid, str(reason)[:500])
        log.warning("Assignment #%d failed: %s", aid, reason)

    return True


def main():
    if not TOOL_ID:
        log.error("DISPATCH_TOOL_ID nicht gesetzt. Abbruch.")
        sys.exit(1)
    if not API_KEY:
        log.error("DISPATCH_API_KEY nicht gesetzt. Abbruch.")
        sys.exit(1)

    log.info("Dispatch Pull-Adapter gestartet.")
    log.info("  API:  %s", API_URL)
    log.info("  Tool: %s", TOOL_ID)
    log.info("  Mode: %s", "one-shot" if ONE_SHOT else f"poll (alle {POLL_SEC}s)")

    if ONE_SHOT:
        poll_once()
        return

    while True:
        try:
            poll_once()
        except KeyboardInterrupt:
            log.info("Beendet durch Ctrl+C.")
            break
        except Exception:
            log.exception("Unerwarteter Fehler im Poll-Zyklus.")

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
