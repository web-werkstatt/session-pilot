#!/usr/bin/env python3
"""
Sprint sprint-agent-orchestrator-executor-handoff Commit 2 (2026-04-18):
CLI-Helper fuer den Agent-Orchestrator Executor-Handoff (Modell B).

Subcommands:
  create        - Neuen Agent-Task anlegen (Titel, Ziel, erlaubte Dateien)
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
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_task_io import (  # noqa: E402
    http_request as _request,
    maybe_exit_on_auth_error as _maybe_exit_on_auth_error,
    get_changed_files as _get_changed_files,
    get_diff_stat as _get_diff_stat,
    compute_out_of_scope as _compute_out_of_scope,
)

# ---------------------------------------------------------------------------
# Pfade & Konstanten
# ---------------------------------------------------------------------------

TOML_PATH = Path.home() / ".agent-task.toml"
TOKEN_FILE_PATH = Path.home() / ".agent-task-token"
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
# Subcommands
# ---------------------------------------------------------------------------

def cmd_create(
    url: str,
    token: str,
    title: str,
    goal: Optional[str] = None,
    allowed_files: Optional[List[str]] = None,
    mode: str = "executor",
    project_id: Optional[int] = None,
    marker_id: Optional[str] = None,
) -> None:
    """Legt einen neuen Agent-Task an (ohne vorherigen Marker noetig)."""
    payload: Dict[str, Any] = {
        "title": title,
        "mode": mode,
    }
    if goal:
        payload["goal"] = goal
    if allowed_files:
        payload["allowed_files"] = list(allowed_files)
    if project_id is not None:
        payload["project_id"] = project_id
    if marker_id:
        payload["marker_id"] = marker_id

    status, resp = _request("POST", f"{url}/api/agent-tasks", token, body=payload)
    _maybe_exit_on_auth_error(status, resp)
    if status in (200, 201):
        task_id = resp.get("task_id") if isinstance(resp, dict) else None
        if not task_id:
            print(f"Fehler: Keine task_id in der Antwort: {resp}", file=sys.stderr)
            sys.exit(1)
        print(f"Task {task_id} angelegt: {title}")
        if allowed_files:
            print("Erlaubte Dateien:")
            for f in allowed_files:
                print(f"  - {f}")
        else:
            print("Erlaubte Dateien: keine (reiner Read-Task)")
        print()
        print(f"Naechster Schritt: claude-task pull {task_id}")
    elif status == 400:
        err = resp.get("error") if isinstance(resp, dict) else str(resp)
        print(f"Fehler: Ungueltige Eingabe: {err}", file=sys.stderr)
        sys.exit(1)
    else:
        err = resp.get("error") if isinstance(resp, dict) else str(resp)
        print(f"Fehler beim Anlegen (Status {status}): {err}", file=sys.stderr)
        sys.exit(1)


def cmd_pull(task_id: int, url: str, token: str) -> None:
    """Laedt Task-Prompt und schreibt .agent-task-<id>.md."""
    prompt_url = f"{url}/api/agent-tasks/{task_id}/prompt"
    status, body = _request("GET", prompt_url, token, accept="text/markdown")
    _maybe_exit_on_auth_error(status, body)
    if status == 404:
        print(f"Fehler: Task {task_id} nicht gefunden (HTTP 404).", file=sys.stderr)
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
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> None:
    """Sammelt Git-Diff und uebertraegt Execution-Result."""
    cstatus, contract = _request("GET", f"{url}/api/agent-tasks/{task_id}", token)
    _maybe_exit_on_auth_error(cstatus, contract)
    if cstatus == 404:
        print(f"Fehler: Task {task_id} nicht gefunden (HTTP 404).", file=sys.stderr)
        sys.exit(1)
    if cstatus != 200 or not isinstance(contract, dict):
        print(f"Fehler: Task {task_id} nicht erreichbar (Status {cstatus}).", file=sys.stderr)
        sys.exit(1)
    allowed_files: List[str] = contract.get("allowed_files") or []

    changed = _get_changed_files(cwd=repo_path)
    diff_stat = _get_diff_stat(cwd=repo_path)
    out_of_scope = _compute_out_of_scope(changed, allowed_files)

    summary = ""
    if notes_file:
        try:
            summary = Path(notes_file).read_text(encoding="utf-8").strip()
        except OSError as e:
            print(f"Warnung: Notiz-Datei nicht lesbar: {e}", file=sys.stderr)

    payload: Dict[str, Any] = {
        "agent": "claude-cli",
        "changed_files": changed,
        "out_of_scope_files": out_of_scope,
        "diff_stat_text": diff_stat,
        "summary": summary,
    }
    if started_at:
        payload["started_at"] = started_at
    if finished_at:
        payload["finished_at"] = finished_at

    estatus, eresp = _request("POST", f"{url}/api/agent-tasks/{task_id}/execution", token, body=payload)
    _maybe_exit_on_auth_error(estatus, eresp)
    if estatus == 201:
        print(f"Execution-Result gespeichert (Task {task_id}).")
        if out_of_scope:
            print(f"Warnung: {len(out_of_scope)} Datei(en) ausserhalb erlaubtem Scope:")
            for f in out_of_scope:
                print(f"  - {f}")
        print(f"Naechster Schritt: claude-task verify {task_id}")
    elif estatus == 409:
        # Sprint Workflow-Finalization Session 2 AC2-2: zweites finish.
        code = eresp.get("code") if isinstance(eresp, dict) else None
        err = eresp.get("error") if isinstance(eresp, dict) else str(eresp)
        existing_id = None
        if isinstance(eresp, dict):
            details = eresp.get("details") or {}
            existing_id = details.get("existing_execution_id")
        hint = (
            f" (execution_id={existing_id})" if existing_id else ""
        )
        print(
            f"Fehler: Execution-Result bereits vorhanden{hint}. "
            f"Zweites finish ist nicht erlaubt ({code or 'conflict'}): {err}",
            file=sys.stderr,
        )
        sys.exit(1)
    elif estatus == 404:
        print(f"Fehler: Task {task_id} nicht gefunden (HTTP 404).", file=sys.stderr)
        sys.exit(1)
    else:
        err = eresp.get("error") if isinstance(eresp, dict) else str(eresp)
        print(f"Fehler beim Speichern (Status {estatus}): {err}", file=sys.stderr)
        sys.exit(1)


def cmd_verify(task_id: int, url: str, token: str) -> None:
    """Ruft das Verify-Gate auf."""
    vstatus, vresp = _request("POST", f"{url}/api/agent-tasks/{task_id}/verify", token)
    _maybe_exit_on_auth_error(vstatus, vresp)
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
    _maybe_exit_on_auth_error(cstatus, cresp)
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

    p_create = sub.add_parser(
        "create",
        help="Neuen Agent-Task anlegen (ohne Marker-Bindung).",
    )
    p_create.add_argument("--title", required=True, help="Task-Titel (Pflicht)")
    p_create.add_argument("--goal", help="Ziel-Beschreibung (was soll Claude tun?)")
    p_create.add_argument(
        "--allowed", action="append", default=[], metavar="FILE",
        help="Erlaubte Datei (mehrfach verwendbar: --allowed a.py --allowed b.py)",
    )
    p_create.add_argument(
        "--mode", default="executor",
        help="Task-Modus (Default: executor — Server validiert den Wert)",
    )
    p_create.add_argument("--project", type=int, metavar="ID", help="Optional: project_id")
    p_create.add_argument("--marker", metavar="MARKER_ID", help="Optional: marker_id")

    p_pull = sub.add_parser("pull", help="Task-Prompt herunterladen.")
    p_pull.add_argument("task_id", type=int)

    p_finish = sub.add_parser("finish", help="Git-Diff sammeln und Execution-Result uebertragen.")
    p_finish.add_argument("task_id", type=int)
    p_finish.add_argument("--notes", metavar="FILE", help="Optionale Notiz-Datei")
    p_finish.add_argument("--repo", metavar="PATH", help="Repo-Pfad fuer git (Default: CWD)")
    p_finish.add_argument("--started", metavar="ISO8601", help="Optionaler started_at-Timestamp (ISO-8601)")
    p_finish.add_argument("--finished", metavar="ISO8601", help="Optionaler finished_at-Timestamp (ISO-8601)")

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

    if args.command == "create":
        cmd_create(
            url, token,
            title=args.title,
            goal=args.goal,
            allowed_files=args.allowed or [],
            mode=args.mode,
            project_id=args.project,
            marker_id=args.marker,
        )
    elif args.command == "pull":
        cmd_pull(args.task_id, url, token)
    elif args.command == "finish":
        cmd_finish(
            args.task_id, url, token,
            notes_file=args.notes,
            repo_path=args.repo,
            started_at=args.started,
            finished_at=args.finished,
        )
    elif args.command == "verify":
        cmd_verify(args.task_id, url, token)
    elif args.command == "close":
        cmd_close(args.task_id, url, token, session_id=args.session)


if __name__ == "__main__":
    main()
