#!/usr/bin/env python3
"""
Sprint sprint-agent-orchestrator-executor-handoff Commit 2 (2026-04-18):
CLI-Helper fuer den Agent-Orchestrator Executor-Handoff (Modell B).

Subcommands:
  pull   <id>  - Task-Contract + Prompt herunterladen
  finish <id>  - Git-Diff sammeln und Execution-Result uebertragen
  verify <id>  - Verify-Gate aufrufen
  close  <id>  - Task schliessen

Konfiguration (Prioritaet: CLI-Argument > env > TOML-Datei > token-file > default):
  AGENT_TASK_URL    - Dashboard-URL (Default: http://localhost:5055)
  AGENT_TASK_TOKEN  - Auth-Token
  ~/.agent-task.toml:
    [agent_task]
    url = "http://localhost:5055"
    token = "EXAMPLE"
  ~/.agent-task-token  - Token als erste nicht-leere Zeile (Plaintext)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Pfade & Konstanten
# ---------------------------------------------------------------------------

TOML_PATH = Path.home() / ".agent-task.toml"
TOKEN_FILE_PATH = Path.home() / ".agent-task-token"
TOKEN_HEADER = "X-Agent-Task-Token"
DEFAULT_URL = "http://localhost:5055"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_toml_simple(path: Path) -> Dict[str, str]:
    """Minimaler Parser fuer die [agent_task]-Sektion in ~/.agent-task.toml."""
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return result
    in_section = False
    for line in text.splitlines():
        line = line.strip()
        if line == "[agent_task]":
            in_section = True
            continue
        if in_section and line.startswith("["):
            break
        if in_section:
            m = re.match(r'^(\w+)\s*=\s*"([^"]*)"', line)
            if m:
                result[m.group(1)] = m.group(2)
    return result


def _load_token_file(path: Optional[Path] = None) -> str:
    """Liest den Token aus einer Plaintext-Datei (erste nicht-leere Zeile)."""
    _path = path if path is not None else TOKEN_FILE_PATH
    try:
        with open(_path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    return stripped
    except (FileNotFoundError, OSError):
        pass
    return ""


def load_config() -> Tuple[str, str]:
    """Gibt (url, token) zurueck. Prioritaet: env > TOML > token-file > default."""
    toml = _load_toml_simple(TOML_PATH)
    url = (
        os.environ.get("AGENT_TASK_URL")
        or toml.get("url")
        or DEFAULT_URL
    ).rstrip("/")
    token = (
        os.environ.get("AGENT_TASK_TOKEN")
        or toml.get("token")
        or _load_token_file()
    )
    return url, token


# ---------------------------------------------------------------------------
# HTTP-Helper
# ---------------------------------------------------------------------------

def _request(
    method: str,
    url: str,
    token: str,
    body: Optional[Dict[str, Any]] = None,
    accept: str = "application/json",
) -> Tuple[int, Any]:
    """HTTP-Request mit X-Agent-Task-Token Auth.

    Rueckgabe: (status_code, body). body ist str bei text/*, sonst dict/None.
    Wirft SystemExit bei Verbindungsfehler.
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
    except urllib.error.URLError as e:
        print(f"Verbindungsfehler: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Git-Helpers
# ---------------------------------------------------------------------------

def _git(*args: str, cwd: Optional[str] = None) -> str:
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


def _get_changed_files(cwd: Optional[str] = None) -> List[str]:
    """git status --porcelain -> Liste geaenderter Dateipfade."""
    out = _git("status", "--porcelain", cwd=cwd)
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def _get_diff_stat(cwd: Optional[str] = None) -> str:
    """git diff --stat HEAD."""
    return _git("diff", "--stat", "HEAD", cwd=cwd).strip()


def _compute_out_of_scope(changed_files: List[str], allowed_files: List[str]) -> List[str]:
    """Dateien aus changed_files, die nicht in allowed_files vorkommen."""
    if not allowed_files:
        return []
    allowed_set = set(allowed_files)
    return [f for f in changed_files if f not in allowed_set]


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_pull(task_id: int, url: str, token: str) -> None:
    """Laedt Task-Prompt und schreibt .agent-task-<id>.md."""
    prompt_url = f"{url}/api/agent-tasks/{task_id}/prompt"
    status, body = _request("GET", prompt_url, token, accept="text/markdown")
    if status == 401:
        print(
            "Fehler: Ungültiger Token (401). "
            "Bitte ~/.agent-task-token oder AGENT_TASK_TOKEN prüfen.",
            file=sys.stderr,
        )
        sys.exit(1)
    if status == 404:
        print(f"Fehler: Task {task_id} nicht gefunden (404).", file=sys.stderr)
        sys.exit(1)
    if status != 200:
        err = body.get("error") if isinstance(body, dict) else str(body)
        print(f"Fehler: Prompt-Endpunkt Status {status}: {err}", file=sys.stderr)
        sys.exit(1)

    out_file = Path(f".agent-task-{task_id}.md")
    out_file.write_text(body if isinstance(body, str) else str(body), encoding="utf-8")
    print(f"Prompt geschrieben: {out_file}")

    contract_url = f"{url}/api/agent-tasks/{task_id}"
    cstatus, contract = _request("GET", contract_url, token)
    allowed: List[str] = []
    if cstatus == 200 and isinstance(contract, dict):
        allowed = contract.get("allowed_files") or []

    print()
    print("Startbefehl:  claude")
    print(f"Dann den Inhalt von {out_file} in die Claude-Session pasten.")
    if allowed:
        print()
        print("Erlaubte Dateien laut Task-Contract:")
        for f in allowed:
            print(f"  - {f}")
    print()
    print("Nach dem Run:")
    print(f"  claude-task finish {task_id}")
    print(f"  claude-task verify {task_id}")
    print(f"  claude-task close  {task_id}")


def cmd_finish(
    task_id: int,
    url: str,
    token: str,
    notes_file: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> None:
    """Sammelt Git-Diff und uebertraegt Execution-Result."""
    cstatus, contract = _request("GET", f"{url}/api/agent-tasks/{task_id}", token)
    if cstatus != 200 or not isinstance(contract, dict):
        print(f"Fehler: Task {task_id} nicht erreichbar (Status {cstatus}).", file=sys.stderr)
        sys.exit(1)
    allowed_files: List[str] = contract.get("allowed_files") or []

    changed = _get_changed_files(cwd=repo_path)
    diff_stat = _get_diff_stat(cwd=repo_path)
    out_of_scope = _compute_out_of_scope(changed, allowed_files)

    notes_text = ""
    if notes_file:
        try:
            notes_text = Path(notes_file).read_text(encoding="utf-8").strip()
        except OSError as e:
            print(f"Warnung: Notiz-Datei nicht lesbar: {e}", file=sys.stderr)

    payload: Dict[str, Any] = {
        "files_changed_json": changed,
        "out_of_scope_files_json": out_of_scope,
        "diff_stat_text": diff_stat,
        "notes_text": notes_text,
    }

    estatus, eresp = _request("POST", f"{url}/api/agent-tasks/{task_id}/execution", token, body=payload)
    if estatus == 201:
        print(f"Execution-Result gespeichert (Task {task_id}).")
        if out_of_scope:
            print(f"Warnung: {len(out_of_scope)} Datei(en) ausserhalb erlaubtem Scope:")
            for f in out_of_scope:
                print(f"  - {f}")
        print(f"Naechster Schritt: claude-task verify {task_id}")
    elif estatus == 404:
        print(f"Fehler: Task {task_id} nicht gefunden.", file=sys.stderr)
        sys.exit(1)
    else:
        err = eresp.get("error") if isinstance(eresp, dict) else str(eresp)
        print(f"Fehler beim Speichern (Status {estatus}): {err}", file=sys.stderr)
        sys.exit(1)


def cmd_verify(task_id: int, url: str, token: str) -> None:
    """Ruft das Verify-Gate auf."""
    vstatus, vresp = _request("POST", f"{url}/api/agent-tasks/{task_id}/verify", token)
    if vstatus in (200, 201):
        decision = vresp.get("decision") if isinstance(vresp, dict) else {}
        passed = decision.get("passed") if isinstance(decision, dict) else None
        label = "PASS" if passed else "FAIL"
        print(f"Verify-Gate: {label} (Task {task_id})")
        if isinstance(decision, dict) and decision.get("failed_claims"):
            print("Fehlgeschlagene Claims:")
            for c in decision["failed_claims"]:
                print(f"  - {c}")
        print(f"Naechster Schritt: claude-task close {task_id}")
    elif vstatus == 404:
        print(f"Fehler: Task {task_id} nicht gefunden (kein Execution-Result?).", file=sys.stderr)
        sys.exit(1)
    else:
        err = vresp.get("error") if isinstance(vresp, dict) else str(vresp)
        print(f"Fehler beim Verify (Status {vstatus}): {err}", file=sys.stderr)
        sys.exit(1)


def cmd_close(task_id: int, url: str, token: str, session_id: Optional[str] = None) -> None:
    """Schliesst den Task."""
    body: Dict[str, Any] = {}
    if session_id:
        body["session_id"] = session_id
    cstatus, cresp = _request(
        "POST", f"{url}/api/agent-tasks/{task_id}/close",
        token, body=body if body else None,
    )
    if cstatus == 200:
        decision = cresp.get("decision") if isinstance(cresp, dict) else {}
        can_close = decision.get("can_close") if isinstance(decision, dict) else None
        if can_close:
            print(f"Task {task_id} erfolgreich geschlossen.")
        else:
            reason = (decision.get("reason") if isinstance(decision, dict) else None) or "unbekannt"
            print(f"Task {task_id} kann nicht geschlossen werden: {reason}")
    elif cstatus == 409:
        decision = cresp.get("decision") if isinstance(cresp, dict) else {}
        reason = (decision.get("reason") if isinstance(decision, dict) else None) or "unbekannt"
        print(f"Task {task_id} kann nicht geschlossen werden (409): {reason}", file=sys.stderr)
        sys.exit(1)
    elif cstatus == 404:
        print(f"Fehler: Task {task_id} nicht gefunden.", file=sys.stderr)
        sys.exit(1)
    else:
        err = cresp.get("error") if isinstance(cresp, dict) else str(cresp)
        print(f"Fehler beim Schliessen (Status {cstatus}): {err}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-task",
        description="CLI-Helper fuer den Agent-Orchestrator Executor-Handoff.",
    )
    parser.add_argument("--url", metavar="URL", help=f"Dashboard-URL (Default: {DEFAULT_URL})")
    parser.add_argument("--token", metavar="TOKEN", help="Auth-Token")

    sub = parser.add_subparsers(dest="command", required=True)

    p_pull = sub.add_parser("pull", help="Task-Prompt herunterladen.")
    p_pull.add_argument("task_id", type=int)

    p_finish = sub.add_parser("finish", help="Git-Diff sammeln und Execution-Result uebertragen.")
    p_finish.add_argument("task_id", type=int)
    p_finish.add_argument("--notes", metavar="FILE", help="Optionale Notiz-Datei")
    p_finish.add_argument("--repo", metavar="PATH", help="Repo-Pfad fuer git (Default: CWD)")

    p_verify = sub.add_parser("verify", help="Verify-Gate aufrufen.")
    p_verify.add_argument("task_id", type=int)

    p_close = sub.add_parser("close", help="Task schliessen.")
    p_close.add_argument("task_id", type=int)
    p_close.add_argument("--session", metavar="SESSION_ID", help="Optionale Session-ID")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg_url, cfg_token = load_config()
    url = (args.url or cfg_url).rstrip("/")
    token = args.token or cfg_token

    if not token:
        print(
            "Fehler: Kein Token konfiguriert. "
            "Bitte AGENT_TASK_TOKEN setzen, ~/.agent-task-token anlegen "
            "oder ~/.agent-task.toml mit [agent_task] token = '...' befuellen.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.command == "pull":
        cmd_pull(args.task_id, url, token)
    elif args.command == "finish":
        cmd_finish(args.task_id, url, token, notes_file=args.notes, repo_path=args.repo)
    elif args.command == "verify":
        cmd_verify(args.task_id, url, token)
    elif args.command == "close":
        cmd_close(args.task_id, url, token, session_id=args.session)


if __name__ == "__main__":
    main()
