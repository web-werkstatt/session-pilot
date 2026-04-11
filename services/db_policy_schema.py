"""
ADR-002 Stufe 1b: DB-Schema fuer Policy-Schicht.

Vier Tabellen bilden die kanonische Datenbasis fuer Rollen, Tool-Profile
und deren Zuweisungen:

- `roles`: Arbeits-Rollen als Datensatz (programming, saas_webdesign, ...)
- `tool_profiles`: CLI/Modell/Provider-Kombinationen
- `role_tool_policies`: Zuweisungen mit Versionierung
  (valid_from / valid_until), approval-pflichtig fuer Aktivitaet
- `policy_review_suggestions`: Perplexity-Vorschlaege, strict getrennt
  vom aktiven Policy-Store - Perplexity schreibt nie direkt in
  role_tool_policies

Policies sind Daten, keine Konstanten. Das Schema ist so gebaut, dass
Joseph manuell Zeilen setzen kann, Perplexity Vorschlaege einliefert,
und jede Aenderung einen Audit-Trail hinterlaesst.
"""
import threading

_policy_schema_ready = False
_policy_schema_lock = threading.Lock()


def ensure_policy_schema_impl(execute):
    """Erstellt alle 4 Policy-Tabellen + Indizes. Idempotent, thread-safe."""
    global _policy_schema_ready
    if _policy_schema_ready:
        return
    with _policy_schema_lock:
        if _policy_schema_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id     VARCHAR(50) PRIMARY KEY,
                name        VARCHAR(120) NOT NULL,
                description TEXT,
                active      BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        execute("""
            CREATE TABLE IF NOT EXISTS tool_profiles (
                tool_id     VARCHAR(80) PRIMARY KEY,
                cli         VARCHAR(50) NOT NULL,
                model       VARCHAR(120),
                provider    VARCHAR(50),
                strengths   JSONB NOT NULL DEFAULT '[]'::jsonb,
                weaknesses  JSONB NOT NULL DEFAULT '[]'::jsonb,
                notes       TEXT,
                active      BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        execute("""
            CREATE TABLE IF NOT EXISTS role_tool_policies (
                policy_id     SERIAL PRIMARY KEY,
                role_id       VARCHAR(50) NOT NULL REFERENCES roles(role_id),
                tool_id       VARCHAR(80) NOT NULL REFERENCES tool_profiles(tool_id),
                rank          INTEGER NOT NULL DEFAULT 1,
                confidence    INTEGER NOT NULL DEFAULT 50,
                rationale     TEXT,
                source        VARCHAR(30) NOT NULL,
                valid_from    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                valid_until   TIMESTAMPTZ,
                approved_by   VARCHAR(50),
                approved_at   TIMESTAMPTZ,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_role_tool_policies_active
            ON role_tool_policies (role_id, tool_id)
            WHERE valid_until IS NULL
        """)

        execute("""
            CREATE TABLE IF NOT EXISTS policy_review_suggestions (
                suggestion_id     SERIAL PRIMARY KEY,
                reviewer_tool     VARCHAR(30) NOT NULL DEFAULT 'perplexity',
                suggestion_type   VARCHAR(40) NOT NULL,
                payload           JSONB NOT NULL,
                rationale         TEXT,
                evidence          JSONB,
                context_hash      VARCHAR(64),
                status            VARCHAR(20) NOT NULL DEFAULT 'pending',
                decided_by        VARCHAR(50),
                decided_at        TIMESTAMPTZ,
                applied_policy_id INTEGER REFERENCES role_tool_policies(policy_id),
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_policy_suggestions_pending
            ON policy_review_suggestions (status, created_at)
            WHERE status = 'pending'
        """)

        _policy_schema_ready = True


def ensure_policy_schema():
    """Lazy Wrapper ohne Delegate in db_service.

    Wird von services/policy_service.py aufgerufen. Importiert execute
    lazy, damit keine Zyklen entstehen und db_service.py (bereits am
    Limit) nicht um einen weiteren Delegate wachsen muss.
    """
    from services.db_service import execute
    ensure_policy_schema_impl(execute)
