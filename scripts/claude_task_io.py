"""
I/O-Helfer fuer `claude_task.py` (ausgelagert 2026-04-18, Session 2 Split):
HTTP-Client, Auth-Fehlerbehandlung und Git-Helfer.

Konstanten (TOML_PATH, TOKEN_FILE_PATH) und `load_config` bleiben im
Haupt-Modul, damit die bestehenden Tests (`monkeypatch.setattr(claude_task,
"TOML_PATH", ...)`) unveraendert greifen.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


TOKEN_HEADER = "X-Agent-Task-Token"


# ---------------------------------------------------------------------------
# Required-Verification (Session L1 sprint-agent-orchestrator-soll-workflow-luecken)
# ---------------------------------------------------------------------------

ALLOWED_VERIFY_CLAIMS = (
    "tests_passed",
    "append_only_respected",
    "docs_updated",
    "feature_complete",
)
CLAIM_TO_VERIFY_TYPE = {
    "tests_passed": "command_exit_zero",
    "append_only_respected": "append_only_diff",
    "docs_updated": "docs_updated",
    "feature_complete": "feature_complete",
}


class VerifyEntryAction(argparse.Action):
    """Sammelt --required-verify und --required-verify-command in CLI-Reihenfolge."""

    def __call__(self, parser, namespace, values, option_string=None):
        entries = getattr(namespace, "_verify_entries", None)
        if entries is None:
            entries = []
            setattr(namespace, "_verify_entries", entries)
        kind = "claim" if option_string == "--required-verify" else "command"
        entries.append((kind, values))


def build_required_verification(
    entries: List[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    """Baut die `required_verification`-Liste aus CLI-Eintraegen.

    Regeln (siehe Sprint §spec-session-l1-cli):
      * Jeder Claim erzeugt einen neuen Eintrag mit `type` gemaess
        `CLAIM_TO_VERIFY_TYPE`.
      * `--required-verify-command` wird an den zuletzt genannten
        command_exit_zero-Eintrag gehaengt (paarweise).
      * Unbekannter Claim -> ValueError.
      * Command ohne vorheriges tests_passed -> ValueError.
    """
    result: List[Dict[str, Any]] = []
    last_cmd_idx: Optional[int] = None
    for kind, value in entries:
        if kind == "claim":
            if value not in ALLOWED_VERIFY_CLAIMS:
                raise ValueError(
                    f"Unbekannter Typ '{value}'. "
                    f"Erlaubt: {', '.join(ALLOWED_VERIFY_CLAIMS)}"
                )
            vtype = CLAIM_TO_VERIFY_TYPE[value]
            result.append({"type": vtype, "claim": value})
            last_cmd_idx = (
                len(result) - 1 if vtype == "command_exit_zero" else None
            )
        else:  # "command"
            if last_cmd_idx is None:
                raise ValueError(
                    "--required-verify-command ohne vorheriges "
                    "--required-verify tests_passed"
                )
            result[last_cmd_idx]["command"] = value
            last_cmd_idx = None
    return result


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def http_request(
    method: str,
    url: str,
    token: str,
    body: Optional[Dict[str, Any]] = None,
    accept: str = "application/json",
) -> Tuple[int, Any]:
    """HTTP-Request mit X-Agent-Task-Token Auth.

    Rueckgabe: (status_code, body). body ist str bei text/*, sonst dict/None.

    Sprint Workflow-Finalization Session 2 (2026-04-18), AC2-4:
    Connection-Refused, Timeout und generelle URLError werden als jeweils
    eigene, menschenlesbare Meldung ausgegeben und fuehren zu Exit != 0.
    """
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
            if "markdown" in ct or ct.startswith("text/"):
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
    except socket.timeout:
        print(
            f"Fehler: Timeout beim Aufruf von {url}. "
            "Laeuft das Dashboard? Ist es erreichbar?",
            file=sys.stderr,
        )
        sys.exit(2)
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, ConnectionRefusedError) or "refused" in str(reason).lower():
            print(
                f"Fehler: Verbindung abgelehnt ({url}). "
                "Dashboard laeuft nicht oder falsche URL. "
                "Pruefe: sudo systemctl status project-dashboard",
                file=sys.stderr,
            )
            sys.exit(2)
        if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
            print(
                f"Fehler: Timeout beim Aufruf von {url}. "
                "Laeuft das Dashboard? Ist es erreichbar?",
                file=sys.stderr,
            )
            sys.exit(2)
        print(
            f"Fehler: Verbindungsproblem zu {url}: {reason}",
            file=sys.stderr,
        )
        sys.exit(2)


def maybe_exit_on_auth_error(status: int, resp: Any) -> None:
    """Beendet den Prozess mit klarer Meldung bei 401/403.

    Sprint Workflow-Finalization Session 2 AC2-4: Auth-Fehler muessen
    eindeutig sein, damit der Nutzer weiss, wo er nachsehen soll.
    """
    if status == 401:
        print(
            "Fehler: Token abgelehnt (HTTP 401). "
            "Pruefe ~/.agent-task-token oder die Env-Variable "
            "AGENT_TASK_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(3)
    if status == 403:
        err = ""
        if isinstance(resp, dict):
            err = resp.get("error") or ""
        print(
            f"Fehler: Zugriff verweigert (HTTP 403). {err}".rstrip(),
            file=sys.stderr,
        )
        sys.exit(3)


# ---------------------------------------------------------------------------
# Git-Helpers
# ---------------------------------------------------------------------------

def git(*args: str, cwd: Optional[str] = None) -> str:
    """Fuehrt git aus und gibt stdout zurueck."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr:
        print(f"git Warnung: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout


def get_changed_files(cwd: Optional[str] = None) -> List[str]:
    """git status --porcelain -> Liste geaenderter Dateipfade."""
    out = git("status", "--porcelain", cwd=cwd)
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def get_diff_stat(cwd: Optional[str] = None) -> str:
    """git diff --stat HEAD."""
    return git("diff", "--stat", "HEAD", cwd=cwd).strip()


def compute_out_of_scope(changed_files: List[str], allowed_files: List[str]) -> List[str]:
    """Dateien aus changed_files, die nicht in allowed_files vorkommen."""
    if not allowed_files:
        return []
    allowed_set = set(allowed_files)
    return [f for f in changed_files if f not in allowed_set]
