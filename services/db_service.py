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
