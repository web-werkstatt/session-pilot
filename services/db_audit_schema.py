"""
SPEC-AUDIT-001: DB-Schema fuer Spec-Audit-System.

Erstellt die Tabellen `specs`, `spec_requirements`, `audit_runs`
und `audit_results`. Idempotent, Thread-safe via Double-Check-Locking.

Extrahiert aus db_service.py (Dateigroessen-Limit).
"""
import threading

_audit_schema_ready = False
_audit_schema_lock = threading.Lock()


def ensure_audit_schema_impl(execute):
    """SPEC-AUDIT-001: Tabellen fuer Spec-Audit-System. Idempotent."""
    global _audit_schema_ready
    if _audit_schema_ready:
        return
    with _audit_schema_lock:
        if _audit_schema_ready:
            return

        # Specs: Hauptdatensatz einer Spezifikation
        execute("""
            CREATE TABLE IF NOT EXISTS specs (
                id SERIAL PRIMARY KEY,
                spec_id VARCHAR(64) UNIQUE NOT NULL,
                title VARCHAR(500) NOT NULL,
                summary TEXT,
                project_mode VARCHAR(50),
                lifecycle_stage VARCHAR(50),
                risk_level VARCHAR(20),
                status VARCHAR(20) DEFAULT 'draft',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_specs_spec_id ON specs(spec_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_specs_status ON specs(status)")

        # Spec-Requirements: atomare Anforderungen pro Spec
        execute("""
            CREATE TABLE IF NOT EXISTS spec_requirements (
                id SERIAL PRIMARY KEY,
                spec_pk INTEGER NOT NULL REFERENCES specs(id) ON DELETE CASCADE,
                key VARCHAR(20) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                priority VARCHAR(10) NOT NULL DEFAULT 'must',
                source VARCHAR(100),
                acceptance_criteria JSONB DEFAULT '[]'::jsonb,
                affected_areas JSONB DEFAULT '[]'::jsonb,
                sort_order INTEGER DEFAULT 0,
                UNIQUE(spec_pk, key)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_spec_req_spec_pk ON spec_requirements(spec_pk)")

        # Audit-Runs: vorbereitet fuer v0.2, in v0.1 nicht persistent beschrieben
        execute("""
            CREATE TABLE IF NOT EXISTS audit_runs (
                id SERIAL PRIMARY KEY,
                spec_id VARCHAR(64) NOT NULL,
                started_at TIMESTAMPTZ DEFAULT NOW(),
                finished_at TIMESTAMPTZ,
                overall_status VARCHAR(20),
                input_facts JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_audit_runs_spec_id ON audit_runs(spec_id)")

        # Audit-Results: Einzelergebnisse pro Requirement pro Run
        execute("""
            CREATE TABLE IF NOT EXISTS audit_results (
                id SERIAL PRIMARY KEY,
                run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
                requirement_key VARCHAR(20) NOT NULL,
                status VARCHAR(30) NOT NULL,
                notes TEXT,
                evidence JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_audit_results_run_id ON audit_results(run_id)")

        _audit_schema_ready = True
