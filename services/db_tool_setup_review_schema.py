"""
ADR-002 Stufe 1a: DB-Schema fuer Tool-Setup-Reviews.

project_reviews: Single-Row pro (project_name, review_type). In Stufe 1a nur
review_type='setup'. In Stufe 3 koennen weitere Typen ergaenzt werden, ohne
Schema-Migration.

Die Spalten sind so geschnitten, dass sie den Datenvertrag aus
`prompts/setup_reviewer.md` direkt spiegeln — die Reviewer-Antwort wird
feldweise uebernommen, Raw-Response wird bei Parse-Fehler gespeichert.
"""
import threading

_tool_setup_review_schema_ready = False
_tool_setup_review_schema_lock = threading.Lock()


def ensure_tool_setup_review_schema_impl(execute):
    """Erstellt project_reviews-Tabelle. Idempotent, thread-safe."""
    global _tool_setup_review_schema_ready
    if _tool_setup_review_schema_ready:
        return
    with _tool_setup_review_schema_lock:
        if _tool_setup_review_schema_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS project_reviews (
                project_name          VARCHAR(255) NOT NULL,
                review_type           VARCHAR(30)  NOT NULL DEFAULT 'setup',
                reviewer_tool         VARCHAR(30)  NOT NULL DEFAULT 'perplexity',
                reviewed_tools        JSONB        NOT NULL DEFAULT '[]'::jsonb,
                setup_ok              BOOLEAN,
                priority              VARCHAR(10),
                summary               TEXT,
                findings              JSONB        NOT NULL DEFAULT '[]'::jsonb,
                suggested_blocks      JSONB        NOT NULL DEFAULT '{}'::jsonb,
                project_json_patch    JSONB,
                implementation_scope  VARCHAR(10),
                notes                 JSONB        NOT NULL DEFAULT '[]'::jsonb,
                context_drift         JSONB,
                context_hash          VARCHAR(64),
                reviewer_model        VARCHAR(100),
                raw_response          TEXT,
                error                 VARCHAR(80),
                created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                PRIMARY KEY (project_name, review_type)
            )
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_project_reviews_context_hash
                ON project_reviews(context_hash)
        """)

        execute("""
            CREATE INDEX IF NOT EXISTS idx_project_reviews_updated
                ON project_reviews(updated_at DESC)
        """)

        _tool_setup_review_schema_ready = True


def ensure_tool_setup_review_schema():
    """Lazy DB-Schema-Sicherstellung ohne Delegate in db_service.

    Wird von services/tool_setup_review/storage.py aufgerufen. Importiert
    execute lazy, damit keine Zyklen mit db_service entstehen und
    db_service.py nicht um einen weiteren Delegate wachsen muss.
    """
    from services.db_service import execute
    ensure_tool_setup_review_schema_impl(execute)


def reset_schema_state_for_tests():
    """Nur fuer Tests: setzt das Ready-Flag zurueck.

    Produktionscode ruft diese Funktion nie auf. Tests nutzen sie, um
    Idempotenz-Checks erneut laufen zu lassen.
    """
    global _tool_setup_review_schema_ready
    with _tool_setup_review_schema_lock:
        _tool_setup_review_schema_ready = False
