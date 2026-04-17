"""
Sprint sprint-agent-orchestrator-hardening-phase-1-foundation (2026-04-17):
DB-Schema fuer den Agent-Orchestrator Phase 1.

Legt zwei Tabellen an:
  * agent_task_contracts  -> maschinenlesbarer Auftrag pro Task
  * agent_session_states  -> expliziter Phasen-Zustand pro Session

Idempotent und thread-safe nach dem Muster der anderen ensure_*_schema
Implementierungen.
"""
import threading

_agent_orchestrator_ready = False
_agent_orchestrator_lock = threading.Lock()


def ensure_agent_orchestrator_schema_impl(execute):
    """Erstellt agent_task_contracts + agent_session_states. Idempotent."""
    global _agent_orchestrator_ready
    if _agent_orchestrator_ready:
        return
    with _agent_orchestrator_lock:
        if _agent_orchestrator_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS agent_task_contracts (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(128),
                title TEXT NOT NULL,
                goal TEXT NOT NULL DEFAULT '',
                mode VARCHAR(20) NOT NULL DEFAULT 'executor',
                allowed_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                forbidden_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                required_verification_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                required_outputs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                stop_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_agent_task_contracts_session ON agent_task_contracts(session_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_agent_task_contracts_created ON agent_task_contracts(created_at DESC)")

        execute("""
            CREATE TABLE IF NOT EXISTS agent_session_states (
                session_id VARCHAR(128) PRIMARY KEY,
                state VARCHAR(20) NOT NULL DEFAULT 'inspect',
                previous_state VARCHAR(20),
                reason TEXT,
                locked BOOLEAN NOT NULL DEFAULT FALSE,
                blocking_issues_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Phase 3 (2026-04-17): Recovery-Snapshot als JSONB-Feld am Session-State.
        # ADD COLUMN IF NOT EXISTS ist idempotent und laeuft auch auf bestehenden
        # Instanzen, bei denen die Tabelle vor Phase 3 angelegt wurde.
        execute("ALTER TABLE agent_session_states ADD COLUMN IF NOT EXISTS recovery_snapshot_json JSONB")

        _agent_orchestrator_ready = True
