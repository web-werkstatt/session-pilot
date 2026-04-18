#!/usr/bin/env python3
"""
Sprint sprint-agent-orchestrator-workflow-finalization Session 3
(§spec-session-3-e2e-doku, 2026-04-18):
End-to-End-Smoke fuer den Agent-Orchestrator-Workflow.

Laeuft gegen ein lokal oder remote verfuegbares Dashboard und testet die
fuenf Workflow-Schritte
    create -> pull -> finish -> verify -> close
gegen die echte Flask-App. Zusaetzlich wird die HTML-Listenseite
`/agent-tasks` geprueft, damit AC3-1 (DOM-/UI-Sichtbarkeit) abgedeckt ist.

Exit-Codes:
  0   alle Schritte PASS
  1   API-/HTTP-Fehler
  2   Token fehlt oder Dashboard nicht erreichbar
  3   Auth-Fehler (401/403)

Konfiguration:
  AGENT_TASK_URL     Dashboard-URL (Default: http://localhost:5055)
  AGENT_TASK_TOKEN   Auth-Token (alternativ ~/.agent-task-token)

Aufruf:
  python3 scripts/e2e_smoke.py [--url URL] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


TOKEN_HEADER = "X-Agent-Task-Token"
DEFAULT_URL = "http://localhost:5055"
TOKEN_FILE = Path.home() / ".agent-task-token"


def _load_token() -> str:
    env = os.environ.get("AGENT_TASK_TOKEN")
    if env:
        return env.strip()
    try:
        for line in TOKEN_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                return line.strip()
    except (FileNotFoundError, OSError):
        pass
    return ""


def _request(method: str, url: str, token: str,
             body: Optional[Dict[str, Any]] = None,
             accept: str = "application/json") -> Tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        TOKEN_HEADER: token,
        "Content-Type": "application/json",
        "Accept": accept,
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            ct = resp.headers.get("Content-Type", "")
            if ct.startswith("text/html") or "markdown" in ct:
                return resp.status, raw
            try:
                return resp.status, json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return e.code, {"error": raw[:500]}
    except (urllib.error.URLError, socket.timeout) as e:
        print(f"FEHLER: Dashboard nicht erreichbar ({url}): {e}", file=sys.stderr)
        sys.exit(2)


def _step(name: str, ok: bool, detail: str = "") -> None:
    marker = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{marker}] {name}{suffix}")
    if not ok:
        sys.exit(1)


def run_smoke(url: str, token: str, verbose: bool = False) -> int:
    print(f"E2E-Smoke gegen {url}")
    print(f"Token-Quelle: {'env AGENT_TASK_TOKEN' if os.environ.get('AGENT_TASK_TOKEN') else str(TOKEN_FILE)}")
    print()

    # Pruef: Health
    hstatus, _ = _request("GET", f"{url}/agent-tasks", token, accept="text/html")
    _step("Dashboard erreichbar (GET /agent-tasks)", hstatus == 200, f"HTTP {hstatus}")

    ts = int(time.time())
    title = f"E2E Smoke {ts}"
    dummy_file = f"/tmp/e2e_smoke_{ts}.txt"

    # 1. create
    payload_create = {
        "title": title,
        "goal": "End-to-End-Smoke durch scripts/e2e_smoke.py",
        "mode": "executor",
        "allowed_files": [dummy_file],
    }
    cstatus, cresp = _request("POST", f"{url}/api/agent-tasks", token, body=payload_create)
    if cstatus in (401, 403):
        print(f"FEHLER: Auth-Fehler beim create (HTTP {cstatus}): {cresp}", file=sys.stderr)
        sys.exit(3)
    _step("create (POST /api/agent-tasks)", cstatus in (200, 201), f"HTTP {cstatus}")
    task_id = cresp.get("task_id") if isinstance(cresp, dict) else None
    _step("Task-ID in Response", isinstance(task_id, int) and task_id > 0, f"task_id={task_id}")
    if verbose:
        print(f"    created task: {json.dumps(cresp, indent=2)}")

    # 2. pull (prompt)
    pstatus, pbody = _request("GET", f"{url}/api/agent-tasks/{task_id}/prompt", token, accept="text/markdown")
    _step("pull (GET .../prompt)", pstatus == 200, f"HTTP {pstatus}, {len(pbody) if isinstance(pbody, str) else 0} bytes")
    _step("Prompt enthaelt Ziel", isinstance(pbody, str) and "End-to-End-Smoke" in pbody, "Ziel-Text gefunden")

    # 3. finish (simulierte Execution)
    payload_finish = {
        "agent": "e2e-smoke",
        "changed_files": [dummy_file],
        "summary": "Smoke-Run abgeschlossen (simuliertes Execution-Result).",
        "diff_stat_text": f" {dummy_file} | 1 +\n 1 file changed, 1 insertion(+)",
        "claims": [],
    }
    fstatus, _ = _request(
        "POST", f"{url}/api/agent-tasks/{task_id}/execution",
        token, body=payload_finish,
    )
    _step("finish (POST .../execution)", fstatus == 201, f"HTTP {fstatus}")

    # 3b. zweites finish -> muss 409 liefern
    fstatus2, fresp2 = _request(
        "POST", f"{url}/api/agent-tasks/{task_id}/execution",
        token, body=payload_finish,
    )
    is_conflict = (fstatus2 == 409 and isinstance(fresp2, dict)
                   and fresp2.get("code") == "execution_already_recorded")
    _step("Zweites finish -> 409 execution_already_recorded", is_conflict,
          f"HTTP {fstatus2}, code={fresp2.get('code') if isinstance(fresp2, dict) else None}")

    # 4. verify
    vstatus, vresp = _request("POST", f"{url}/api/agent-tasks/{task_id}/verify", token)
    _step("verify (POST .../verify)", vstatus in (200, 201), f"HTTP {vstatus}")
    status_val = None
    if isinstance(vresp, dict):
        status_val = vresp.get("status") or (vresp.get("decision") or {}).get("status")
    _step("verify liefert status=pass", status_val == "pass", f"status={status_val}")

    # 5. close
    cstatus2, cresp2 = _request("POST", f"{url}/api/agent-tasks/{task_id}/close", token, body={})
    _step("close (POST .../close)", cstatus2 == 200, f"HTTP {cstatus2}")
    decision = cresp2.get("decision") if isinstance(cresp2, dict) else {}
    can_close = decision.get("can_close") if isinstance(decision, dict) else None
    _step("close_decision.can_close = True", can_close is True, f"decision={decision}")

    # 6. Listenseite: HTML-Skelett rendert + JSON-API hat den Task
    # (Die Task-Liste wird clientseitig per AJAX befuellt, daher keine
    # Titel-Assertion im HTML selbst.)
    lstatus, lbody = _request("GET", f"{url}/agent-tasks", token, accept="text/html")
    _step("GET /agent-tasks (HTML)", lstatus == 200, f"HTTP {lstatus}")
    _step("HTML enthaelt Listen-Container",
          isinstance(lbody, str) and 'id="agentTasksBody"' in lbody,
          "Tabellen-Body gefunden")
    jstatus, jresp = _request(
        "GET", f"{url}/api/agent-tasks/list?status=closed&limit=50", token,
    )
    _step("GET /api/agent-tasks/list?status=closed", jstatus == 200, f"HTTP {jstatus}")
    tasks = jresp.get("tasks") if isinstance(jresp, dict) else []
    hit = any(t.get("task_id") == task_id for t in tasks or [])
    _step("Geschlossener Task erscheint in /list?status=closed", hit,
          f"count={len(tasks or [])}, task_id={task_id}")

    # 7. Konsistenz-Check via API
    dstatus, _ = _request("GET", f"{url}/api/agent-tasks/{task_id}", token)
    _step("GET /api/agent-tasks/<id> (finale Sicht)", dstatus == 200, f"HTTP {dstatus}")

    print()
    print(f"OK — Smoke gruen. task_id={task_id}, title={title!r}")
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="E2E-Smoke fuer den Agent-Orchestrator-Workflow.")
    parser.add_argument("--url", default=os.environ.get("AGENT_TASK_URL", DEFAULT_URL),
                        help=f"Dashboard-URL (Default: {DEFAULT_URL})")
    parser.add_argument("--verbose", action="store_true", help="Ausfuehrliche Ausgabe.")
    args = parser.parse_args(argv)

    token = _load_token()
    if not token:
        print(
            "FEHLER: Kein Token konfiguriert. "
            "Entweder AGENT_TASK_TOKEN setzen oder ~/.agent-task-token anlegen.",
            file=sys.stderr,
        )
        return 2

    return run_smoke(args.url.rstrip("/"), token, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
