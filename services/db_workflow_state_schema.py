"""
Sprint Workflow-v2: DB-Schema fuer persistente Marker-Workflow-States.
"""
import threading

_workflow_state_ready = False
_workflow_state_lock = threading.Lock()


def ensure_workflow_state_schema_impl(execute):
    """Erstellt marker_workflow_states + workflow_transitions Tabellen."""
    global _workflow_state_ready
    if _workflow_state_ready:
        return
    with _workflow_state_lock:
        if _workflow_state_ready:
            return

        # Persistenter Workflow-State pro Marker
        execute("""
            CREATE TABLE IF NOT EXISTS marker_workflow_states (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(255) NOT NULL,
                marker_id VARCHAR(128) NOT NULL,
                workflow_status VARCHAR(30) NOT NULL DEFAULT 'planned',
                owner VARCHAR(128),
                blocked_reason TEXT,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                last_session VARCHAR(64),
                last_transition_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(project_name, marker_id)
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_mws_project ON marker_workflow_states(project_name)")
        execute("CREATE INDEX IF NOT EXISTS idx_mws_status ON marker_workflow_states(workflow_status)")

        # Audit-Trail: jeder Statuswechsel wird protokolliert
        execute("""
            CREATE TABLE IF NOT EXISTS workflow_transitions (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(255) NOT NULL,
                marker_id VARCHAR(128) NOT NULL,
                from_status VARCHAR(30),
                to_status VARCHAR(30) NOT NULL,
                triggered_by VARCHAR(128) DEFAULT 'user',
                reason TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_wt_marker ON workflow_transitions(project_name, marker_id, created_at DESC)")

        _workflow_state_ready = True
