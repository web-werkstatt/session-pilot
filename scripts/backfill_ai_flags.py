#!/usr/bin/env python3
"""
Backfill-Script: Setzt AI-Scope-Flags fuer bestehende Sessions.

Usage:
    python3 scripts/backfill_ai_flags.py              # Strategie B: aus DB-Messages
    python3 scripts/backfill_ai_flags.py --full        # Strategie A: Re-Import aller JSONL
    python3 scripts/backfill_ai_flags.py --project X   # Nur ein Projekt
    python3 scripts/backfill_ai_flags.py --dry-run     # Nur anzeigen, nichts aendern
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.db_service import execute, ensure_ai_scope_schema
from services.ai_scope_service import analyze_from_db_messages


def backfill(dry_run=False, project=None):
    """Strategie B: Berechnet AI-Flags aus gespeicherten DB-Messages."""
    ensure_ai_scope_schema()

    where = "WHERE (ai_tools_used = '[]'::jsonb OR ai_tools_used IS NULL)"
    params = []
    if project:
        where += " AND project_name = %s"
        params.append(project)

    sessions = execute(
        f"SELECT id, session_uuid, project_name FROM sessions {where} ORDER BY id",
        params or None, fetch=True
    )
    if not sessions:
        print("Keine Sessions gefunden.")
        return

    print(f"{len(sessions)} Sessions gefunden, analysiere...")
    updated = 0

    for sess in sessions:
        sid = sess["id"]
        messages = execute(
            "SELECT type, content_json FROM messages WHERE session_id = %s AND type = 'assistant'",
            (sid,), fetch=True
        )
        if not messages:
            continue

        flags = analyze_from_db_messages(messages)
        tools_json = json.dumps(flags["ai_tools_used"])

        if dry_run:
            if flags["ai_has_tool_calls"]:
                print(f"  [{sess['session_uuid'][:12]}] writes={flags['ai_has_writes']} "
                      f"tools={len(flags['ai_tools_used'])} ({', '.join(flags['ai_tools_used'][:5])})")
        else:
            execute("""
                UPDATE sessions SET
                    ai_has_writes = %s,
                    ai_has_tool_calls = %s,
                    ai_tools_used = %s
                WHERE id = %s
            """, (flags["ai_has_writes"], flags["ai_has_tool_calls"], tools_json, sid))

        if flags["ai_has_tool_calls"]:
            updated += 1

    mode = "DRY-RUN" if dry_run else "UPDATED"
    print(f"\n{mode}: {updated}/{len(sessions)} Sessions mit Tool-Calls")


def force_reimport():
    """Strategie A: Loescht Sync-Hashes und importiert alle Sessions neu."""
    from config import PROJECTS_DIR
    hash_cache = os.path.join(PROJECTS_DIR, ".sync_hashes.json")
    if os.path.exists(hash_cache):
        os.remove(hash_cache)
        print(f"Sync-Cache geloescht: {hash_cache}")
    else:
        print("Kein Sync-Cache vorhanden.")

    from services.session_import import sync_all
    print("Starte Re-Import aller Sessions...")
    result = sync_all()
    print(f"Re-Import abgeschlossen: {result}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    full = "--full" in sys.argv
    project = None
    for i, arg in enumerate(sys.argv):
        if arg == "--project" and i + 1 < len(sys.argv):
            project = sys.argv[i + 1]

    if full:
        force_reimport()
    else:
        backfill(dry_run=dry_run, project=project)
