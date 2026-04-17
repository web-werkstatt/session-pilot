"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
Claim-spezifische Verify-Gate-Checks.

Ausgelagert aus `agent_verify_service.py`, damit dort Kern-Workflow (CRUD,
Orchestrierung, Close-Gate) vom claim-spezifischen Verhalten getrennt ist.
Enthaelt:
  * load_project_config(project_id) -> dict (Lazy-Loader mit Exception-Guard)
  * check_docs_updated(req, runner, changed_files, project_config)
  * path_matches_any(file_path, patterns) -> bool
  * default_command_runner(command, ...) -> (rc, stdout+stderr)
"""
import subprocess


# Status-Konstanten doppelt pflegen waere Zirkularimport — Aufrufer in
# agent_verify_service reicht sie sowieso nicht in die dict zurueck; die
# Strings sind unveraenderlich Teil des Verify-Contracts.
VERIFY_STATUS_PASS = "pass"
VERIFY_STATUS_BLOCKED = "blocked"
VERIFY_STATUS_FAIL = "fail"


def load_project_config(project_id):
    """Laedt die Project-Config oder liefert leeres Dict bei Ausfall.

    Fehler im Loader duerfen den Verify-Gate nicht crashen — sensitive_files
    und Block-Regexe fallen dann auf Defaults zurueck.
    """
    try:
        from services.agent_project_config_service import get_config
        return get_config(project_id) or {}
    except Exception:
        return {}


def check_docs_updated(req, runner, changed_files, project_config):
    """Claim `docs_updated`: mindestens ein Doku-Pfad wurde veraendert.

    Quelle der geaenderten Dateien ist primaer `execution.changed_files`
    (schneller Pfad, kein Subprocess). Wenn der Caller explizit
    `use_git_diff=True` setzt, laeuft zusaetzlich
    `git diff --name-only <base>..HEAD` ueber den command_runner.
    docs_paths kommen aus der Project-Config (#spec-commit-5-docs-updated).
    """
    claim = req.get("claim") or "docs_updated"
    docs_paths = project_config.get("docs_paths") or []
    if not docs_paths:
        return ({
            "type": "required_verification",
            "status": VERIFY_STATUS_BLOCKED,
            "claim": claim,
            "details": "docs_paths empty in project config",
        }, claim)

    candidate_files = list(changed_files or [])

    if req.get("use_git_diff"):
        base = req.get("base") or "main"
        if runner is None:
            return ({
                "type": "required_verification",
                "status": VERIFY_STATUS_BLOCKED,
                "claim": claim,
                "details": f"git diff --name-only {base}..HEAD not executed (no runner)",
            }, claim)
        rc, out = runner(f"git diff --name-only {base}..HEAD")
        if rc != 0:
            return ({
                "type": "required_verification",
                "status": VERIFY_STATUS_FAIL,
                "claim": claim,
                "details": f"git diff exit={rc} output={_truncate(out)}",
            }, claim)
        candidate_files = [line.strip() for line in (out or "").splitlines() if line.strip()]

    matched = [f for f in candidate_files if path_matches_any(f, docs_paths)]
    if matched:
        return ({
            "type": "required_verification",
            "status": VERIFY_STATUS_PASS,
            "claim": claim,
            "details": f"docs changed: {matched}",
        }, claim)
    return ({
        "type": "required_verification",
        "status": VERIFY_STATUS_FAIL,
        "claim": claim,
        "details": f"no changes in docs_paths={docs_paths}",
    }, claim)


def path_matches_any(file_path, patterns):
    """True wenn file_path einen der Patterns matcht.

    Patterns sind einfache Prefixes (Verzeichnisse) oder exakte Dateipfade.
    Beispiel: `docs/` matcht `docs/README.md`, `README.md` matcht nur exakt.
    """
    for pattern in patterns:
        if not pattern:
            continue
        if pattern.endswith("/"):
            if file_path.startswith(pattern):
                return True
        elif file_path == pattern:
            return True
        elif file_path.startswith(pattern + "/"):
            return True
    return False


def default_command_runner(command, *, timeout=30, cwd=None):
    """Default-Runner fuer Command-Exit-Checks.

    Bewusst nicht automatisch aktiv: run_verify_gate nutzt ihn nur, wenn der
    Aufrufer ihn explizit uebergibt. Das haelt Tests und API-Aufrufe ohne
    Subprocess-Seiteneffekte stabil.
    """
    try:
        result = subprocess.run(
            command if isinstance(command, list) else command,
            shell=not isinstance(command, list),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except Exception as exc:
        return 1, f"command_runner_error: {exc}"


def _truncate(text, limit=200):
    if text is None:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
