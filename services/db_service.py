"""
PostgreSQL-Verbindung und Schema-Management fuer Claude Sessions
"""
import threading
import psycopg2
from psycopg2 import pool, extras
from config import DB_CONFIG

_pool = None
_pool_lock = threading.Lock()


def get_pool():
    """Gibt den Connection-Pool zurueck, erstellt ihn bei Bedarf (thread-safe)"""
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool
    with _pool_lock:
        if _pool is None or _pool.closed:
            _pool = pool.ThreadedConnectionPool(3, 10, **DB_CONFIG)
    return _pool


def get_conn():
    """Holt eine Verbindung aus dem Pool"""
    return get_pool().getconn()


def put_conn(conn):
    """Gibt eine Verbindung zurueck in den Pool"""
    try:
        get_pool().putconn(conn)
    except Exception:
        pass


def execute(sql, params=None, fetch=False, fetchone=False):
    """Fuehrt SQL aus und gibt optional Ergebnisse zurueck"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetchone:
                result = cur.fetchone()
            elif fetch:
                result = cur.fetchall()
            else:
                result = None
            conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def execute_many(sql, params_list):
    """Fuehrt SQL mit mehreren Parameter-Sets aus"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            extras.execute_batch(cur, sql, params_list, page_size=100)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def ensure_database():
    """Erstellt die Datenbank und Tabellen falls noetig"""
    import re
    # Erst pruefen ob DB existiert
    cfg = DB_CONFIG.copy()
    cfg["dbname"] = "postgres"
    dbname = DB_CONFIG["dbname"]
    # DB-Name validieren: nur alphanumerisch und Unterstriche
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', dbname):
        raise ValueError(f"Ungültiger Datenbankname: {dbname}")
    try:
        conn = psycopg2.connect(**cfg)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if not cur.fetchone():
                # psycopg2.sql für sichere Identifier
                from psycopg2 import sql
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
        conn.close()
    except Exception as e:
        print(f"DB-Erstellung fehlgeschlagen: {e}")
        raise

    # Tabellen erstellen
    execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            session_uuid VARCHAR(64) UNIQUE NOT NULL,
            account VARCHAR(20) NOT NULL,
            project_hash VARCHAR(255),
            project_name VARCHAR(255),
            cwd VARCHAR(500),
            git_branch VARCHAR(100),
            model VARCHAR(100),
            claude_version VARCHAR(20),
            slug VARCHAR(100),
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            duration_ms INTEGER DEFAULT 0,
            user_message_count INTEGER DEFAULT 0,
            assistant_message_count INTEGER DEFAULT 0,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            jsonl_path VARCHAR(1000),
            jsonl_size BIGINT,
            jsonl_mtime DOUBLE PRECISION,
            imported_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
            uuid VARCHAR(64),
            parent_uuid VARCHAR(64),
            type VARCHAR(20),
            content TEXT,
            content_json JSONB,
            model VARCHAR(100),
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            timestamp TIMESTAMPTZ,
            is_tool_result BOOLEAN DEFAULT FALSE
        )
    """)
    # Indizes
    execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account)")
    execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name)")
    execute("CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC)")


_schema_ready = False
_schema_lock = threading.Lock()
_plans_schema_ready = False
_plans_schema_lock = threading.Lock()


def ensure_session_review_schema():
    """Stellt Review-Spalten und Review-Notiz-Tabelle fuer Sessions bereit"""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS outcome VARCHAR(20)")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS outcome_note TEXT")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS outcome_at TIMESTAMPTZ")
        execute("""
            CREATE TABLE IF NOT EXISTS review_threads (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(255),
                title VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'open',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("""
            CREATE TABLE IF NOT EXISTS session_reviews (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                thread_id INTEGER REFERENCES review_threads(id) ON DELETE SET NULL,
                outcome_snapshot VARCHAR(20),
                note TEXT NOT NULL,
                author VARCHAR(80) DEFAULT 'local',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("ALTER TABLE session_reviews ADD COLUMN IF NOT EXISTS thread_id INTEGER REFERENCES review_threads(id) ON DELETE SET NULL")
        execute("CREATE INDEX IF NOT EXISTS idx_session_reviews_session_id ON session_reviews(session_id, created_at DESC)")
        execute("CREATE INDEX IF NOT EXISTS idx_session_reviews_thread_id ON session_reviews(thread_id, created_at DESC)")
        execute("CREATE INDEX IF NOT EXISTS idx_review_threads_project_name ON review_threads(project_name, updated_at DESC)")
        _schema_ready = True


def ensure_plans_schema():
    """Erstellt die project_plans Tabelle falls noetig"""
    global _plans_schema_ready
    if _plans_schema_ready:
        return
    with _plans_schema_lock:
        if _plans_schema_ready:
            return
        execute("""
            CREATE TABLE IF NOT EXISTS project_plans (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                title VARCHAR(500),
                project_name VARCHAR(255),
                content TEXT,
                context_summary TEXT,
                category VARCHAR(50) DEFAULT 'plan',
                status VARCHAR(20) DEFAULT 'draft',
                session_uuid VARCHAR(64),
                file_hash VARCHAR(64),
                file_mtime DOUBLE PRECISION,
                created_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ,
                imported_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_plans_project ON project_plans(project_name)")
        execute("CREATE INDEX IF NOT EXISTS idx_plans_status ON project_plans(status)")
        execute("CREATE INDEX IF NOT EXISTS idx_plans_created ON project_plans(created_at DESC)")
        _plans_schema_ready = True


_ai_scope_ready = False
_ai_scope_lock = threading.Lock()


def ensure_ai_scope_schema():
    """Sprint 9: Fehler-Kategorien + AI-Scope-Spalten"""
    global _ai_scope_ready
    if _ai_scope_ready:
        return
    with _ai_scope_lock:
        if _ai_scope_ready:
            return
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS outcome_reason VARCHAR(50)")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS outcome_severity VARCHAR(20)")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ai_has_writes BOOLEAN DEFAULT FALSE")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ai_has_tool_calls BOOLEAN DEFAULT FALSE")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ai_tools_used JSONB DEFAULT '[]'::jsonb")
        _ai_scope_ready = True


_file_touch_ready = False
_file_touch_lock = threading.Lock()


def ensure_file_touch_schema():
    """Sprint 10: Per-File AI-Heatmap Tabelle"""
    global _file_touch_ready
    if _file_touch_ready:
        return
    with _file_touch_lock:
        if _file_touch_ready:
            return
        execute("""
            CREATE TABLE IF NOT EXISTS ai_file_touches (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                file_path VARCHAR(1000) NOT NULL,
                touch_type VARCHAR(20) NOT NULL,
                tool_name VARCHAR(50),
                timestamp TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_session ON ai_file_touches(session_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_path ON ai_file_touches(file_path)")
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_type ON ai_file_touches(touch_type)")
        _file_touch_ready = True
