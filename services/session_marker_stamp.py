"""
Sprint SB - Post-Sync-Hook fuer Session-Marker-Bindung.

Wird am Ende von session_import.sync_all() aufgerufen. Iteriert ueber
alle Projektordner mit marker-context.md und stempelt fuer alle Sessions
mit started_at >= mtime(marker-context.md) und marker_id IS NULL die
aktive marker_id ein. Single point of change fuer alle 5 Importer.
"""
import os
from datetime import datetime, timezone

from config import PROJECTS_DIR
from services.db_service import execute, ensure_session_marker_schema


def _read_marker_id_from_context(ctx_path):
    with open(ctx_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith("- marker_id:"):
                return line.split(":", 1)[1].strip() or None
    return None


def stamp_marker_context_after_sync():
    """Stempelt sessions.marker_id fuer Sessions seit aktueller marker-context.md.

    Fehler je Projekt brechen den Sync nicht ab - nur Warning-Print.
    """
    if not os.path.isdir(PROJECTS_DIR):
        return
    try:
        ensure_session_marker_schema()
    except Exception as e:
        print(f"stamp_marker_context_after_sync: schema-init fehlgeschlagen: {e}")
        return

    for entry in os.listdir(PROJECTS_DIR):
        project_root = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(project_root):
            continue
        ctx_path = os.path.join(project_root, "marker-context.md")
        if not os.path.isfile(ctx_path):
            continue
        try:
            marker_id = _read_marker_id_from_context(ctx_path)
            if not marker_id:
                continue
            ctx_mtime = datetime.fromtimestamp(os.path.getmtime(ctx_path), tz=timezone.utc)
            handoff_path = os.path.join(project_root, "handoff.md")
            handoff_path_value = handoff_path if os.path.isfile(handoff_path) else None
            execute(
                """UPDATE sessions
                      SET marker_id = %s,
                          marker_handoff_path = %s,
                          updated_at = NOW()
                    WHERE project_name = %s
                      AND marker_id IS NULL
                      AND started_at IS NOT NULL
                      AND started_at >= %s""",
                (marker_id, handoff_path_value, entry, ctx_mtime),
            )
        except Exception as e:
            print(f"stamp_marker_context_after_sync: {entry} uebersprungen: {e}")
