"""
Sprint sprint-plan-discovery (2026-04-15) + Followup (2026-04-16):
Schema-Delta fuer mehrquelligen Plan-Scanner.

- project_plans.source_path TEXT          -> Kanonischer Dateipfad (realpath)
- project_plans.source_kind VARCHAR(32)   -> Quelle (claude_plans, project_sprints, ...)
- project_plans.content_hash VARCHAR(32)  -> MD5 fuer Aenderungs-/Duplikat-Erkennung

Indizes:
- ux_project_plans_source_path  UNIQUE (partial, WHERE source_path IS NOT NULL)
- ix_project_plans_content_hash nicht-eindeutig, fuer Content-Duplikat-Scans

Constraint-Aufloesung (Followup-Sprint 2026-04-16):
- Globaler UNIQUE(filename) wird durch UNIQUE(filename, project_name)
  ersetzt — dadurch scheitern Cross-Project-Importe nicht mehr, wenn
  mehrere Projekte identische Dateinamen wie `sprint-1.md` fuehren.

Idempotent: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS +
kontrolliertes DROP CONSTRAINT mit Existenz-Check.
"""
import threading

_plan_source_schema_ready = False
_plan_source_schema_lock = threading.Lock()


def ensure_plan_source_schema_impl(execute, ensure_plans_schema):
    """Erweitert project_plans um source_path, source_kind, content_hash + Indizes
    und bricht den globalen UNIQUE(filename)-Constraint auf (Followup 2026-04-16)."""
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

        # Globaler UNIQUE(filename) -> UNIQUE(filename, project_name).
        # Cross-Project-Importe duerfen nicht mehr an globalem filename-Konflikt scheitern.
        # Umsetzung in PostgreSQL-kompatibler idempotenter Form.
        rows = execute("""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'project_plans'::regclass AND contype = 'u'
        """, fetch=True) or []
        existing_uniques = {row['conname'] for row in rows}

        # Standard-Name von CREATE TABLE: project_plans_filename_key
        if 'project_plans_filename_key' in existing_uniques:
            execute("ALTER TABLE project_plans DROP CONSTRAINT project_plans_filename_key")

        if 'project_plans_filename_project_key' not in existing_uniques:
            # Composite-UNIQUE mit NULL-vertraeglichkeit: NULL-project wird mehrfach erlaubt
            # (was fuer Legacy-claude_plans ohne project_name gewollt ist).
            execute("""
                ALTER TABLE project_plans
                ADD CONSTRAINT project_plans_filename_project_key
                UNIQUE (filename, project_name)
            """)

        _plan_source_schema_ready = True
