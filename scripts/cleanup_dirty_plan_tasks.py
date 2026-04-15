#!/usr/bin/env python3
"""Einmaliger Cleanup: plan_tasks-Zeilen mit dict-Repr im title loeschen.

Ursprung: kurzzeitiger Bug in upsert_tasks_for_plan (Sprint
sprint-task-entity-und-drilldown), der dict-Items aus build_task_items
als String stringifizierte. Nach dem Bugfix muessen die kaputten
Zeilen entfernt werden, sonst bleiben sie als Karteileichen in der DB.
Idempotent — DELETE betrifft nur Zeilen mit "{'title':" im title.
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.db_service import execute, ensure_plan_task_schema  # noqa: E402


def main():
    ensure_plan_task_schema()
    rows = execute(
        "SELECT id, plan_id, title FROM plan_tasks WHERE title LIKE %s",
        ("%'title':%",),
        fetch=True,
    ) or []
    if not rows:
        print("OK — keine kaputten Zeilen gefunden")
        return 0
    print(f"Loesche {len(rows)} kaputte plan_tasks-Zeilen:")
    for row in rows[:5]:
        print(f"  - id={row['id']} plan={row['plan_id']} title={row['title'][:80]}")
    if len(rows) > 5:
        print(f"  ... und {len(rows) - 5} weitere")
    execute("DELETE FROM plan_tasks WHERE title LIKE %s", ("%'title':%",))
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
