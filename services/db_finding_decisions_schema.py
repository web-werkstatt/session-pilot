"""
Finding-Decisions: DB-Schema fuer Entscheidungen zu Review-Findings.

Eine Tabelle `finding_decisions` speichert Approve/Dismiss/Ignore-Entscheidungen
pro Finding (identifiziert ueber SHA256-Fingerprint). Gilt fuer Setup-Reviewer-
und CWO-Findings gleichermassen.

Reaktivierungs-Logik: Wenn sich `context_signature` aendert (Severity, Problem
oder Empfehlung haben sich geaendert), wird ein dismissed Finding automatisch
auf 'pending' zurueckgesetzt.
"""
import threading

_finding_decisions_schema_ready = False
_finding_decisions_schema_lock = threading.Lock()


def ensure_finding_decisions_schema_impl(execute):
    """Erstellt finding_decisions Tabelle + Indizes. Idempotent, thread-safe."""
    global _finding_decisions_schema_ready
    if _finding_decisions_schema_ready:
        return
    with _finding_decisions_schema_lock:
        if _finding_decisions_schema_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS finding_decisions (
                id                SERIAL PRIMARY KEY,
                project_name      VARCHAR(255) NOT NULL,
                review_type       VARCHAR(30) NOT NULL,
                fingerprint       VARCHAR(64) NOT NULL,
                status            VARCHAR(20) NOT NULL DEFAULT 'pending',
                dismiss_reason    VARCHAR(40),
                dismiss_note      TEXT,
                decided_by        VARCHAR(50),
                decided_at        TIMESTAMPTZ,
                context_signature VARCHAR(64),
                finding_snapshot  JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (project_name, review_type, fingerprint)
            )
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_finding_decisions_active
            ON finding_decisions (project_name, review_type)
            WHERE status IN ('dismissed', 'approved')
        """)

        _finding_decisions_schema_ready = True


def ensure_finding_decisions_schema():
    """Lazy Wrapper — importiert execute erst bei Aufruf."""
    from services.db_service import execute
    ensure_finding_decisions_schema_impl(execute)
