"""
Sprint sprint-task-entity-und-drilldown (2026-04-15):
DB-Schema fuer plan_tasks als eigenstaendige Entitaet mit Surrogate-ID +
parse_key fuer deterministisches Markdown-Re-Parse-Matching.

Ergaenzt markers.task_id (FK, ON DELETE SET NULL) damit Marker stabil auf
Tasks referenzieren koennen. Task-Loeschung macht Marker nicht kaputt, nur
unzugeordnet.
"""
import threading

_plan_task_schema_ready = False
_plan_task_schema_lock = threading.Lock()


def ensure_plan_task_schema_impl(execute):
    """Erstellt plan_tasks + markers.task_id. Idempotent."""
    global _plan_task_schema_ready
    if _plan_task_schema_ready:
        return
    with _plan_task_schema_lock:
        if _plan_task_schema_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS plan_tasks (
                id SERIAL PRIMARY KEY,
                plan_id INTEGER NOT NULL,
                section_key VARCHAR(500) NOT NULL,
                spec_key VARCHAR(500) NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                normalized_title VARCHAR(500) NOT NULL,
                parse_key VARCHAR(1000) NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0,
                body TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                last_parsed_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(plan_id, parse_key)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_plan_tasks_plan ON plan_tasks(plan_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_plan_tasks_section ON plan_tasks(plan_id, section_key)")

        # markers.task_id nachziehen (idempotent via duplicate_column-Pattern)
        execute("""
            DO $$ BEGIN
                ALTER TABLE markers
                    ADD COLUMN task_id INTEGER REFERENCES plan_tasks(id) ON DELETE SET NULL;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_markers_task ON markers(task_id)")

        _plan_task_schema_ready = True
