"""
Sprint sprint-plan-discovery (2026-04-15):
Schema-Delta fuer mehrquelligen Plan-Scanner.

- project_plans.source_path TEXT          -> Kanonischer Dateipfad (realpath)
- project_plans.source_kind VARCHAR(32)   -> Quelle (claude_plans, project_sprints, ...)
- project_plans.content_hash VARCHAR(32)  -> MD5 fuer Aenderungs-/Duplikat-Erkennung

Indizes:
- ux_project_plans_source_path  UNIQUE (partial, WHERE source_path IS NOT NULL)
- ix_project_plans_content_hash nicht-eindeutig, fuer Content-Duplikat-Scans

Idempotent: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
"""
import threading

_plan_source_schema_ready = False
_plan_source_schema_lock = threading.Lock()


def ensure_plan_source_schema_impl(execute, ensure_plans_schema):
    """Erweitert project_plans um source_path, source_kind, content_hash + Indizes."""
    global _plan_source_schema_ready
    if _plan_source_schema_ready:
        return
    with _plan_source_schema_lock:
        if _plan_source_schema_ready:
            return

        ensure_plans_schema()

        execute("ALTER TABLE project_plans ADD COLUMN IF NOT EXISTS source_path TEXT")
        execute("ALTER TABLE project_plans ADD COLUMN IF NOT EXISTS source_kind VARCHAR(32)")
        execute("ALTER TABLE project_plans ADD COLUMN IF NOT EXISTS content_hash VARCHAR(32)")

        execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_project_plans_source_path
            ON project_plans(source_path)
            WHERE source_path IS NOT NULL
        """)
        execute("""
            CREATE INDEX IF NOT EXISTS ix_project_plans_content_hash
            ON project_plans(content_hash)
        """)

        _plan_source_schema_ready = True
