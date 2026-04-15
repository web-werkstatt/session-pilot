"""
Sprint sprint-task-backfill (2026-04-15):
DB-Schema fuer Task-Match-Suggestions — Fuzzy-Match zwischen Bestands-Markern
(task_id=NULL) und plan_tasks mit Review-Workflow (pending/approved/rejected).

Voraussetzung: plan_tasks + markers.task_id aus sprint-task-entity-und-drilldown.
"""
import threading

_plan_task_match_schema_ready = False
_plan_task_match_schema_lock = threading.Lock()


def ensure_plan_task_match_schema_impl(execute):
    """Erstellt plan_task_match_suggestions. Idempotent."""
    global _plan_task_match_schema_ready
    if _plan_task_match_schema_ready:
        return
    with _plan_task_match_schema_lock:
        if _plan_task_match_schema_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS plan_task_match_suggestions (
                id SERIAL PRIMARY KEY,
                marker_id INTEGER NOT NULL REFERENCES markers(id) ON DELETE CASCADE,
                task_id INTEGER NOT NULL REFERENCES plan_tasks(id) ON DELETE CASCADE,
                score NUMERIC(4,3) NOT NULL,
                method VARCHAR(30) NOT NULL DEFAULT 'normalized_jaccard',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                decided_at TIMESTAMPTZ,
                decided_by VARCHAR(255),
                UNIQUE(marker_id, task_id)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_task_match_marker ON plan_task_match_suggestions(marker_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_task_match_task ON plan_task_match_suggestions(task_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_task_match_status ON plan_task_match_suggestions(status)")

        _plan_task_match_schema_ready = True
