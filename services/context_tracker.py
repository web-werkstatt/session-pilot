"""
Context-Change-Tracker: Erkennt Aenderungen an AI-Instruktionsdateien
(CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules, copilot-instructions.md)
und speichert sie in der DB fuer Vorher/Nachher-Analysen.
"""
import os
import subprocess
from datetime import datetime, timezone
from config import PROJECTS_DIR
from services.db_service import execute

# Instruktionsdateien die getrackt werden
INSTRUCTION_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".cursorrules",
    ".github/copilot-instructions.md",
]


def _run_git(cwd, args, timeout=10):
    """Fuehrt git-Befehl aus und gibt stdout zurueck"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def scan_project_context(project_path, project_name):
    """Scannt ein Projekt auf Aenderungen an Instruktionsdateien.
    Gibt Anzahl neuer Eintraege zurueck.
    """
    if not os.path.isdir(os.path.join(project_path, ".git")):
        return 0

    new_entries = 0

    for filename in INSTRUCTION_FILES:
        filepath = os.path.join(project_path, filename)
        if not os.path.isfile(filepath):
            continue

        # Git-Log fuer diese Datei
        log = _run_git(project_path, [
            "log", "--format=%H|%aI|%s", "--follow", "--diff-filter=AM",
            "--", filename
        ])
        if not log:
            continue

        for line in log.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue

            commit_hash = parts[0]
            date_str = parts[1]
            message = parts[2]

            # Bereits vorhanden?
            existing = execute(
                "SELECT id FROM context_changes WHERE project_name = %s AND file_path = %s AND commit_hash = %s",
                (project_name, filename, commit_hash), fetchone=True
            )
            if existing:
                continue

            # Diff-Statistik
            stat = _run_git(project_path, [
                "diff", "--numstat", f"{commit_hash}~1", commit_hash, "--", filename
            ])
            added, removed = 0, 0
            if stat:
                stat_parts = stat.split("\t")
                if len(stat_parts) >= 2:
                    try:
                        added = int(stat_parts[0]) if stat_parts[0] != '-' else 0
                        removed = int(stat_parts[1]) if stat_parts[1] != '-' else 0
                    except ValueError:
                        pass

            # Content-Snapshot (Zustand nach dem Commit)
            snapshot = _run_git(project_path, ["show", f"{commit_hash}:{filename}"])

            # Timestamp parsen
            try:
                changed_at = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                changed_at = datetime.now(timezone.utc)

            execute("""
                INSERT INTO context_changes
                    (project_name, file_path, changed_at, lines_added, lines_removed,
                     commit_hash, commit_message, content_snapshot)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_name, file_path, commit_hash) DO NOTHING
            """, (
                project_name, filename, changed_at, added, removed,
                commit_hash, message, snapshot[:50000] if snapshot else None
            ))
            new_entries += 1

    return new_entries


def scan_all_projects():
    """Scannt alle Projekte auf Instruktions-Aenderungen"""
    total = 0
    scanned = 0

    for entry in sorted(os.listdir(PROJECTS_DIR)):
        project_path = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(project_path):
            continue
        if entry.startswith(".") or entry in ("backups", "vorlagen", "node_modules"):
            continue

        count = scan_project_context(project_path, entry)
        if count > 0:
            print(f"  {entry}: {count} neue Aenderungen")
        total += count
        scanned += 1

    print(f"Context-Scan: {scanned} Projekte, {total} neue Aenderungen")
    return total


if __name__ == "__main__":
    scan_all_projects()
