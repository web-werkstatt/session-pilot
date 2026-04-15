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
                source_line INTEGER,
                UNIQUE(project_name, marker_id)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_markers_project ON markers(project_name)")
        execute("CREATE INDEX IF NOT EXISTS idx_markers_status ON markers(status)")
        execute("CREATE INDEX IF NOT EXISTS idx_markers_plan ON markers(plan_id)")

        # source_line fuer bestehende Installationen nachziehen (Phase 7, 2026-04-14):
        # Reihenfolge der Marker entspricht der Position in der handoff.md.
        execute("""
            DO $$ BEGIN
                ALTER TABLE markers
                    ADD COLUMN source_line INTEGER;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)

        # rating_skipped (2026-04-15): User kann Rating explizit verwerfen
        # (z.B. Marker ohne relevante Ausfuehrung, Ratlosigkeit). Setzt das
        # "Bewertung nachholen"-Signal stumm, ohne execution_score zu setzen.
        execute("""
            DO $$ BEGIN
                ALTER TABLE markers
                    ADD COLUMN rating_skipped BOOLEAN NOT NULL DEFAULT FALSE;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)

        # executor_tool in marker_workflow_states (Sprint ADR-001 Erweiterung)
        execute("""
            DO $$ BEGIN
                ALTER TABLE marker_workflow_states
                    ADD COLUMN executor_tool VARCHAR(30);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)

        # Implementation-Check Persisting (Sprint sprint-impl-check-persisting, 2026-04-15):
        # Cache fuer Prozent + Signale + Timestamp. NULL = nicht berechnet / invalidiert.
        execute("""
            DO $$ BEGIN
                ALTER TABLE markers
                    ADD COLUMN implementation_percent SMALLINT;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)
        execute("""
            DO $$ BEGIN
                ALTER TABLE markers
                    ADD COLUMN implementation_signals JSONB;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)
        execute("""
            DO $$ BEGIN
                ALTER TABLE markers
                    ADD COLUMN implementation_checked_at TIMESTAMPTZ;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)

        _marker_schema_ready = True
