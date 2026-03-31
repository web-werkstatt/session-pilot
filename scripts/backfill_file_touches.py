#!/usr/bin/env python3
"""
Backfill-Script: Extrahiert File-Touches aus bestehenden Sessions.
Parst tool_use Bloecke in gespeicherten Messages und speichert Dateipfade.

Usage:
    python3 scripts/backfill_file_touches.py [--dry-run] [--project NAME]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.db_service import execute, ensure_file_touch_schema
from services.file_touch_service import extract_file_touches, save_file_touches


def backfill(dry_run=False, project_filter=None):
    ensure_file_touch_schema()

    where = "WHERE 1=1"
    params = []
    if project_filter:
        where += " AND project_name = %s"
        params.append(project_filter)

    sessions = execute(
        f"SELECT id, session_uuid, project_name, cwd FROM sessions {where} ORDER BY id",
        params or None, fetch=True
    )
    if not sessions:
        print("Keine Sessions gefunden.")
        return

    print(f"{len(sessions)} Sessions gefunden, extrahiere File-Touches...")
    total_touches = 0
    sessions_with_touches = 0

    for sess in sessions:
        sid = sess["id"]
        messages = execute(
            "SELECT type, content_json, timestamp FROM messages WHERE session_id = %s AND type = 'assistant'",
            (sid,), fetch=True
        )
        if not messages:
            continue

        touches = extract_file_touches(messages, cwd=sess.get("cwd"))
        if not touches:
            continue

        if dry_run:
            print(f"  [{sess['session_uuid'][:12]}] {sess.get('project_name', '?')}: "
                  f"{len(touches)} touches ({len(set(t['file_path'] for t in touches))} unique files)")
        else:
            save_file_touches(sid, touches)

        total_touches += len(touches)
        sessions_with_touches += 1

    mode = "DRY-RUN" if dry_run else "SAVED"
    print(f"\n{mode}: {total_touches} File-Touches aus {sessions_with_touches}/{len(sessions)} Sessions")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    project = None
    for i, arg in enumerate(sys.argv):
        if arg == "--project" and i + 1 < len(sys.argv):
            project = sys.argv[i + 1]
    backfill(dry_run=dry_run, project_filter=project)
