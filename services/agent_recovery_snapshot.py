"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 3, 2026-04-17):
Recovery-Snapshot-Builder fuer den Agent-Orchestrator.

Baut einen einmaligen Snapshot des aktuellen Arbeitsstands:
  * git status --short
  * git diff --stat HEAD (Diff-Summary)
  * untracked / modified Files
  * Risk-Flags (dirty_worktree, sensitive_file_touched)

Persistiert den Snapshot als JSONB-Feld am Session-State und setzt den
Session-Zustand auf `recovery`. Bewusst OHNE Restore-Logik — wir sichern
Stand, wir setzen nicht zurueck.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from services.db_service import execute, ensure_agent_orchestrator_schema
from services.agent_orchestrator_service import (
    SENSITIVE_FILES,
    _git_status,
    get_session_state,
)


def build_recovery_snapshot(repo_path: Optional[str] = None,
                            git_runner: Optional[Callable] = None) -> dict:
    """Baut den Recovery-Snapshot.

    Parameter:
      repo_path: optional, Default = Projekt-Root.
      git_runner: optional Callable(list[str]) -> (rc, stdout).
        Tests uebergeben einen Fake-Runner.

    Rueckgabe: Snapshot-dict (serialisierbar, wird als JSONB persistiert).
    """
    if repo_path is None:
        repo_path = str(Path(__file__).resolve().parent.parent)

    runner = git_runner or _default_git_runner(repo_path)

    status_rc, status_out = runner(["status", "--short"])
    diff_rc, diff_out = runner(["diff", "--stat", "HEAD"])

    untracked, modified = _git_status(runner)
    touched = untracked + modified
    sensitive = [p for p in touched if p in SENSITIVE_FILES]

    risk_flags = []
    if untracked or modified:
        risk_flags.append("dirty_worktree")
    if sensitive:
        risk_flags.append("sensitive_file_touched")

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_status_short": status_out if status_rc == 0 else "",
        "diff_stat": diff_out if diff_rc == 0 else "",
        "untracked_files": untracked,
        "modified_files": modified,
        "sensitive_files_touched": sensitive,
        "risk_flags": risk_flags,
    }


def persist_recovery_snapshot(session_id: str,
                              snapshot: dict,
                              *,
                              reason: Optional[str] = None) -> dict:
    """Persistiert den Snapshot und setzt den Session-State auf `recovery`.

    Gibt den aktualisierten Session-State zurueck (inkl. `recovery_snapshot`).
    """
    if not session_id or not str(session_id).strip():
        raise ValueError("session_id darf nicht leer sein")

    ensure_agent_orchestrator_schema()

    current = get_session_state(session_id)
    previous_state = current["state"] if current else None
    snapshot_json = json.dumps(snapshot or {})
    blocking_issues = list((current or {}).get("blocking_issues") or [])
    blocking_json = json.dumps(blocking_issues)
    locked = bool((current or {}).get("locked") or False)
    effective_reason = reason or "recovery snapshot captured"

    execute(
        """
        INSERT INTO agent_session_states (
            session_id, state, previous_state, reason, locked,
            blocking_issues_json, recovery_snapshot_json, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW())
        ON CONFLICT (session_id) DO UPDATE SET
            previous_state = EXCLUDED.previous_state,
            state = EXCLUDED.state,
            reason = EXCLUDED.reason,
            locked = EXCLUDED.locked,
            blocking_issues_json = EXCLUDED.blocking_issues_json,
            recovery_snapshot_json = EXCLUDED.recovery_snapshot_json,
            updated_at = NOW()
        """,
        (
            session_id,
            "recovery",
            previous_state,
            effective_reason,
            locked,
            blocking_json,
            snapshot_json,
        ),
    )
    result = get_session_state(session_id)
    if result is None:
        # Darf praktisch nicht passieren, weil wir gerade geschrieben haben.
        raise RuntimeError(
            f"agent_session_states write fuer session_id={session_id} "
            f"ergab keinen lesbaren State"
        )
    return result


def _default_git_runner(repo_path: str) -> Callable:
    def _run(args):
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, *args],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode, result.stdout
        except Exception:
            return 1, ""
    return _run
