#!/usr/bin/env python3
"""
Backfill-Script: Setzt AI-Scope-Flags fuer bestehende Sessions.
Analysiert gespeicherte Messages und aktualisiert ai_has_writes, ai_has_tool_calls, ai_tools_used.

Usage:
    python3 scripts/backfill_ai_flags.py [--dry-run]
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.db_service import execute, ensure_ai_scope_schema
from services.ai_scope_service import analyze_from_db_messages


def backfill(dry_run=False):
    ensure_ai_scope_schema()

    sessions = execute(
        "SELECT id, session_uuid FROM sessions ORDER BY id",
        fetch=True
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


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    backfill(dry_run=dry_run)
