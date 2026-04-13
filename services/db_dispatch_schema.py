"""
ADR-002 Stufe 2a: DB-Schema fuer Dispatch-Schicht.

Drei Strukturen:

- `work_assignments`: Arbeitsauftraege (Marker -> Tool), mit Lifecycle
  (proposed -> approved -> claimed -> completed/failed/rejected/revoked/expired)
- `dispatch_audit_log`: Audit-Trail fuer State-Transitions
- ALTER `tool_profiles`: 4 Dispatch-Spalten (dispatch_manual/pull/push, max_concurrent)

- `dispatch_settings`: Globale/pro-Projekt/pro-Tool Konfiguration (Perplexity-Modus, Expiry)
"""
import threading

_dispatch_schema_ready = False
_dispatch_schema_lock = threading.Lock()


def ensure_dispatch_schema_impl(execute):
    """Erstellt Dispatch-Tabellen + Indizes. Idempotent, thread-safe.

    Voraussetzung: Policy-Schema muss existieren (FK auf roles, tool_profiles).
    """
    global _dispatch_schema_ready
    if _dispatch_schema_ready:
        return
    with _dispatch_schema_lock:
        if _dispatch_schema_ready:
            return

        # --- work_assignments ---
        execute("""
            CREATE TABLE IF NOT EXISTS work_assignments (
                assignment_id     SERIAL PRIMARY KEY,
                project_name      VARCHAR(255) NOT NULL,
                marker_id         VARCHAR(128),
                role_id           VARCHAR(50) REFERENCES roles(role_id),
                executor_tool     VARCHAR(80) REFERENCES tool_profiles(tool_id),
                scope_ref         JSONB NOT NULL DEFAULT '{}'::jsonb,
                input_payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
                risk_level        VARCHAR(10) NOT NULL DEFAULT 'medium',
                automation_level  SMALLINT NOT NULL DEFAULT 1,
                dispatch_mode     VARCHAR(10) NOT NULL DEFAULT 'manual',
                approval_required BOOLEAN NOT NULL DEFAULT TRUE,
                approval_state    VARCHAR(20) NOT NULL DEFAULT 'proposed',
                allowed_write_scope JSONB DEFAULT '[]'::jsonb,
                timeout_at        TIMESTAMPTZ,
                claimed_at        TIMESTAMPTZ,
                claimed_by        VARCHAR(80),
                completed_at      TIMESTAMPTZ,
                result_ref        JSONB,
                perplexity_review JSONB,
                created_by        VARCHAR(50) NOT NULL DEFAULT 'joseph',
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Indizes auf work_assignments
        execute("""
            CREATE INDEX IF NOT EXISTS idx_wa_project
            ON work_assignments (project_name)
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_wa_status
            ON work_assignments (approval_state)
        """)

        # Partial-Index fuer Pull-API: approved + noch nicht geclaimed
        execute("""
            CREATE INDEX IF NOT EXISTS idx_wa_pending_pull
            ON work_assignments (executor_tool, created_at)
            WHERE approval_state = 'approved' AND claimed_at IS NULL
        """)

        # --- dispatch_audit_log ---
        execute("""
            CREATE TABLE IF NOT EXISTS dispatch_audit_log (
                log_id            SERIAL PRIMARY KEY,
                assignment_id     INTEGER NOT NULL REFERENCES work_assignments(assignment_id),
                from_state        VARCHAR(20),
                to_state          VARCHAR(20) NOT NULL,
                changed_by        VARCHAR(80) NOT NULL,
                reason            TEXT,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_dispatch_audit_assignment
            ON dispatch_audit_log (assignment_id)
        """)

        # --- tool_profiles erweitern: Dispatch-Spalten ---
        for col, typ, default in [
            ("dispatch_manual", "BOOLEAN", "TRUE"),
            ("dispatch_pull", "BOOLEAN", "FALSE"),
            ("dispatch_push", "BOOLEAN", "FALSE"),
            ("max_concurrent", "INTEGER", "1"),
        ]:
            execute(f"""
                ALTER TABLE tool_profiles
                ADD COLUMN IF NOT EXISTS {col} {typ} NOT NULL DEFAULT {default}
            """)

        # --- dispatch_settings ---
        execute("""
            CREATE TABLE IF NOT EXISTS dispatch_settings (
                setting_id        SERIAL PRIMARY KEY,
                scope             VARCHAR(20) NOT NULL DEFAULT 'global',
                scope_ref         VARCHAR(255) NOT NULL DEFAULT '',
                perplexity_mode   VARCHAR(20),
                auto_expire_hours INTEGER,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(scope, scope_ref)
            )
        """)

        _dispatch_schema_ready = True


def ensure_dispatch_schema():
    """Lazy Wrapper — importiert execute und Policy-Schema erst bei Aufruf."""
    from services.db_policy_schema import ensure_policy_schema
    from services.db_service import execute
    ensure_policy_schema()
    ensure_dispatch_schema_impl(execute)
