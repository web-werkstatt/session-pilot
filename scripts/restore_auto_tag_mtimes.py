#!/usr/bin/env python3
"""
Einmaliger Fix nach dem Auto-Tagging-Lauf vom 2026-04-16 19:52:51.

Das Auto-Tagging hat die Datei-mtime aller getaggten Plaene auf den
Tag-Zeitpunkt gesetzt, wodurch beim naechsten Sync `updated_at=NOW()`
gesetzt wurde — alle Sprint-Plaene zeigten in der UI "heute".

Dieses Script:
1. Liest die originalen mtime-Werte aus dem Backup-Verzeichnis
   `backups/plan-auto-tagging/<timestamp>/`.
2. Setzt die aktuelle .md-Datei-mtime via `os.utime()` auf den alten Wert zurueck.
3. Schreibt die DB-Spalten `file_mtime` und `updated_at` auf diesen
   alten Wert zurueck (nur fuer betroffene Plans mit source_kind
   in ('project_sprints', 'project_plans')).

Ist idempotent — zweiter Lauf findet keine Drift mehr und aendert nichts.
"""
import os
import sys
from datetime import datetime, timezone

# Repo-Wurzel zum PYTHONPATH
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.db_service import execute  # noqa: E402
from services.markdown_routine_service import (  # noqa: E402
    compute_content_hash,
    read_markdown_with_fallback,
)


BACKUP_ROOT = os.path.join(ROOT, "backups", "plan-auto-tagging")


def find_latest_backup_dir():
    if not os.path.isdir(BACKUP_ROOT):
        return None
    stamps = sorted(os.listdir(BACKUP_ROOT))
    return os.path.join(BACKUP_ROOT, stamps[-1]) if stamps else None


def backup_name_to_source_path(basename):
    """`mnt__projects__...__sprints__x.md` -> `/mnt/projects/.../sprints/x.md`."""
    parts = basename.split(".")
    name = parts[0]
    # Bei Collisions-Suffix wie `...__x.md.1` -> Index entfernen
    if len(parts) > 2 and parts[-1].isdigit():
        name = ".".join(parts[:-2])
        ext = parts[-2]
    else:
        ext = "md"
    path_parts = name.split("__")
    return "/" + "/".join(path_parts) + "." + ext


def main():
    backup_dir = find_latest_backup_dir()
    if not backup_dir:
        print("Kein Backup-Verzeichnis gefunden — nichts zu tun.")
        return 0

    print(f"Lese Backups aus: {backup_dir}")
    restored = 0
    skipped_missing = 0
    skipped_unknown = 0

    for basename in sorted(os.listdir(backup_dir)):
        if not basename.endswith((".md", ".md.1", ".md.2", ".md.3")):
            continue
        source_path = backup_name_to_source_path(basename)
        backup_file = os.path.join(backup_dir, basename)

        if not os.path.isfile(source_path):
            skipped_missing += 1
            continue

        original_mtime = os.path.getmtime(backup_file)
        current_mtime = os.path.getmtime(source_path)

        # Datei-mtime zurueckstellen, falls abweichend
        if abs(current_mtime - original_mtime) > 1.0:
            os.utime(source_path, (original_mtime, original_mtime))

        # Content + Hash frisch aus der Datei lesen, damit der naechste Sync
        # die Plaene als "unchanged" erkennt (sonst triggert der Hash-Mismatch
        # den changed-Pfad mit updated_at=NOW() und das Datum-Problem kommt zurueck).
        try:
            loaded = read_markdown_with_fallback(source_path)
            fresh_content = loaded["content"]
            fresh_hash = compute_content_hash(fresh_content)
        except Exception:
            fresh_content = None
            fresh_hash = None

        # DB-Felder updated_at + file_mtime zurueckrollen, Content/Hash
        # nur aktualisieren wenn erfolgreich gelesen.
        dt = datetime.fromtimestamp(original_mtime, tz=timezone.utc)
        if fresh_content is not None:
            rows = execute(
                """UPDATE project_plans
                   SET updated_at=%s, file_mtime=%s,
                       content=%s, content_hash=%s
                   WHERE source_path=%s
                   AND source_kind IN ('project_sprints','project_plans')
                   RETURNING id""",
                (dt, original_mtime, fresh_content, fresh_hash, source_path),
                fetch=True,
            )
        else:
            rows = execute(
                """UPDATE project_plans
                   SET updated_at=%s, file_mtime=%s
                   WHERE source_path=%s
                   AND source_kind IN ('project_sprints','project_plans')
                   RETURNING id""",
                (dt, original_mtime, source_path),
                fetch=True,
            )
        if rows:
            restored += len(rows)
        else:
            skipped_unknown += 1

    print(f"Zurueckgerollt: {restored} DB-Eintraege")
    print(f"Backup ohne aktuelle Datei: {skipped_missing}")
    print(f"Backup ohne DB-Match: {skipped_unknown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
