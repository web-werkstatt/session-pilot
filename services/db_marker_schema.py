"""
ADR-001: DB-Schema fuer Marker-Definitionen (DB-first).

Erstellt die `markers`-Tabelle und erweitert `marker_workflow_states`
um das Feld `executor_tool`.
"""
import threading

_marker_schema_ready = False
_marker_schema_lock = threading.Lock()


def ensure_marker_schema_impl(execute):
    """Erstellt markers-Tabelle und ergaenzt executor_tool. Idempotent."""
    global _marker_schema_ready
    if _marker_schema_ready:
        return
    with _marker_schema_lock:
        if _marker_schema_ready:
            return

        # Marker-Definitionen (kanonische Quelle, ersetzt handoff.md)
        execute("""
            CREATE TABLE IF NOT EXISTS markers (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(255) NOT NULL,
                marker_id VARCHAR(128) NOT NULL,
                titel VARCHAR(500) NOT NULL,
                plan_id VARCHAR(64) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'todo',
                ziel TEXT NOT NULL DEFAULT '',
                naechster_schritt TEXT NOT NULL DEFAULT '',
                prompt TEXT NOT NULL DEFAULT '',
                prompt_suggestion TEXT DEFAULT '',
                risiko TEXT DEFAULT '',
                checks JSONB NOT NULL DEFAULT '[]'::jsonb,
                last_session VARCHAR(64) DEFAULT '',
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                execution_score SMALLINT,
                execution_comment TEXT DEFAULT '',
                last_execution_at TIMESTAMPTZ,
                sprint_tag VARCHAR(128) DEFAULT '',
                spec_tag VARCHAR(128) DEFAULT '',
                sprint_plan_id INTEGER,
                spec_id INTEGER,
                imported_from VARCHAR(20) DEFAULT 'handoff',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(project_name, marker_id)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_markers_project ON markers(project_name)")
        execute("CREATE INDEX IF NOT EXISTS idx_markers_status ON markers(status)")
        execute("CREATE INDEX IF NOT EXISTS idx_markers_plan ON markers(plan_id)")

        # executor_tool in marker_workflow_states (Sprint ADR-001 Erweiterung)
        execute("""
            DO $$ BEGIN
                ALTER TABLE marker_workflow_states
                    ADD COLUMN executor_tool VARCHAR(30);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)

        _marker_schema_ready = True
