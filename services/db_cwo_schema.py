"""
CWO Sprint: DB-Schema fuer Context Window Optimizer.

Erstellt die Tabellen `cwo_analyses` (eine Zeile pro Projekt) und
`cwo_action_log` (Aktions-Protokoll mit Approval-Workflow).
Idempotent, Thread-safe via Double-Check-Locking.
"""
import threading

_cwo_schema_ready = False
_cwo_schema_lock = threading.Lock()


def ensure_cwo_schema_impl(execute):
    """Erstellt CWO-Tabellen. Idempotent."""
    global _cwo_schema_ready
    if _cwo_schema_ready:
        return
    with _cwo_schema_lock:
        if _cwo_schema_ready:
            return

        # Analyse-Ergebnis pro Projekt (Upsert auf project_name)
        execute("""
            CREATE TABLE IF NOT EXISTS cwo_analyses (
                project_name VARCHAR(255) PRIMARY KEY,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                token_budget_rating VARCHAR(10) NOT NULL DEFAULT 'ok',
                findings JSONB NOT NULL DEFAULT '[]'::jsonb,
                migration_map JSONB NOT NULL DEFAULT '[]'::jsonb,
                file_inventory JSONB NOT NULL DEFAULT '[]'::jsonb,
                context_hash VARCHAR(64),
                perplexity_review JSONB,
                perplexity_confidence SMALLINT,
                review_context_hash VARCHAR(64),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Aktions-Protokoll mit Approval-Workflow
        execute("""
            CREATE TABLE IF NOT EXISTS cwo_action_log (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(255) NOT NULL,
                action_id VARCHAR(30) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'proposed',
                parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
                result JSONB,
                proposed_at TIMESTAMPTZ DEFAULT NOW(),
                executed_at TIMESTAMPTZ,
                CONSTRAINT fk_cwo_action_project
                    FOREIGN KEY (project_name)
                    REFERENCES cwo_analyses(project_name)
                    ON DELETE CASCADE
            )
        """)
        execute(
            "CREATE INDEX IF NOT EXISTS idx_cwo_action_project "
            "ON cwo_action_log(project_name)"
        )
        execute(
            "CREATE INDEX IF NOT EXISTS idx_cwo_action_status "
            "ON cwo_action_log(status)"
        )

        # Migration: error-Spalte nachtraeglich hinzufuegen (Ticket 1.6)
        execute("""
            ALTER TABLE cwo_analyses
            ADD COLUMN IF NOT EXISTS error VARCHAR(100)
        """)

        _cwo_schema_ready = True
