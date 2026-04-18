"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 2, 2026-04-17):
DB-Schema fuer den Verify-Gate MVP.

Legt zwei Tabellen an:
  * agent_execution_results -> rohes Ergebnis einer Agenten-Ausfuehrung
  * agent_verify_results    -> Verify-Gate-Ergebnis pro Task

Schema bewusst schlank gemaess Technical Spec §2.4/§2.5:
`append_only_respected` und `docs_updated` sind NICHT Teil dieser Phase
und wandern nach Phase 3.

Idempotent und thread-safe nach Muster db_agent_orchestrator_schema.py.
"""
import threading

_agent_verify_ready = False
_agent_verify_lock = threading.Lock()


def ensure_agent_verify_schema_impl(execute):
    """Erstellt agent_execution_results + agent_verify_results. Idempotent."""
    global _agent_verify_ready
    if _agent_verify_ready:
        return
    with _agent_verify_lock:
        if _agent_verify_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS agent_execution_results (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                agent VARCHAR(64),
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                changed_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                deleted_files_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                claims_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                summary TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_agent_execution_results_task ON agent_execution_results(task_id, created_at DESC)")

        # Sprint sprint-agent-orchestrator-execution-payload-fix (2026-04-18):
        # Zwei zusaetzliche Signale aus dem CLI-/UI-Handoff-Payload. ADD COLUMN
        # IF NOT EXISTS haelt ensure_agent_verify_schema() idempotent fuer
        # Bestands- und neue Instanzen.
        execute("ALTER TABLE agent_execution_results ADD COLUMN IF NOT EXISTS diff_stat_text TEXT")
        execute("ALTER TABLE agent_execution_results ADD COLUMN IF NOT EXISTS out_of_scope_files_json JSONB NOT NULL DEFAULT '[]'::jsonb")

        # Sprint sprint-agent-orchestrator-workflow-finalization Session 2
        # (2026-04-18): ein Task darf nur genau EIN Execution-Result haben.
        # Zwei parallele `finish`-Calls ergeben so deterministisch einen
        # Gewinner + eine UniqueViolation, die der Service in 409 uebersetzt
        # (AC2-2). Idempotent via EXCEPTION-Catch.
        execute("""
            DO $$ BEGIN
                ALTER TABLE agent_execution_results
                    ADD CONSTRAINT uq_agent_execution_task UNIQUE (task_id);
            EXCEPTION WHEN duplicate_table THEN NULL;
                      WHEN duplicate_object THEN NULL;
                      WHEN unique_violation THEN NULL;
            END $$
        """)

        execute("""
            CREATE TABLE IF NOT EXISTS agent_verify_results (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL,
                checks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                unverified_claims_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                next_state VARCHAR(20),
                execution_result_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_agent_verify_results_task ON agent_verify_results(task_id, created_at DESC)")

        _agent_verify_ready = True
