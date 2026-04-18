"""
Git-Hilfsfunktionen fuer den Agent-Orchestrator.

Ausgelagert aus agent_orchestrator_service.py (2026-04-18) wegen
Dateigroessen-Limit (500 Zeilen). Enthaelt reine Git-Utilities ohne
Datenbank-Abhaengigkeiten.
"""
import subprocess


def default_git_runner(repo_path):
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


def git_branch(runner):
    rc, out = runner(["branch", "--show-current"])
    if rc != 0:
        return None
    branch = out.strip()
    return branch or None


def git_status(runner):
    """Liefert (untracked, modified) Listen ohne Duplikate.

    Interpretation von `git status --short`:
      * '??' am Zeilenanfang -> untracked
      * alles andere -> modified (inkl. staged 'M ' / 'A ' / ' M' / 'MM' etc.)
    """
    rc, out = runner(["status", "--short"])
    if rc != 0:
        return [], []
    untracked = []
    modified = []
    for raw_line in out.splitlines():
        if not raw_line.strip():
            continue
        status = raw_line[:2]
        path = raw_line[3:].strip()
        if not path:
            continue
        if "->" in path:
            path = path.split("->", 1)[1].strip()
        if status == "??":
            if path not in untracked:
                untracked.append(path)
        else:
            if path not in modified:
                modified.append(path)
    return untracked, modified
