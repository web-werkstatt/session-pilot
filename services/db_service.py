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
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS execution_score SMALLINT")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS execution_comment TEXT")
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
        # filename NICHT mehr global UNIQUE — Cross-Project-Importe duerfen
        # identische Dateinamen fuehren (z.B. `sprint-1.md` in mehreren Projekten).
        # Composite UNIQUE(filename, project_name) wird in
        # ensure_plan_source_schema() nachgezogen (Followup 2026-04-16).
        execute("""
            CREATE TABLE IF NOT EXISTS project_plans (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
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


def ensure_plan_workflow_schema():
    from services.db_plan_workflow_schema import ensure_plan_workflow_schema_impl
    ensure_plan_workflow_schema_impl(execute, ensure_plans_schema)


def ensure_plan_source_schema():
    """Sprint Plan-Discovery: source_path, source_kind, content_hash auf project_plans."""
    from services.db_plan_source_schema import ensure_plan_source_schema_impl
    ensure_plan_source_schema_impl(execute, ensure_plans_schema)


def ensure_plan_scan_exclusions_schema():
    """Sprint Plan-Discovery: plan_scan_exclusions (GUI-Exclusion-Patterns)."""
    from services.db_plan_scan_exclusions_schema import ensure_plan_scan_exclusions_schema_impl
    ensure_plan_scan_exclusions_schema_impl(execute)


def ensure_plan_structure_schema():
    from services.db_plan_structure_schema import ensure_plan_structure_schema_impl
    ensure_plan_structure_schema_impl(execute, ensure_plan_workflow_schema)


def ensure_session_marker_schema():
    """Sprint SB: Session-Marker-Binding (delegiert an db_session_marker_schema)."""
    from services.db_session_marker_schema import ensure_session_marker_schema_impl
    ensure_session_marker_schema_impl(execute)


def ensure_workflow_state_schema():
    """Sprint Workflow-v2: Persistente Marker-Workflow-States."""
    from services.db_workflow_state_schema import ensure_workflow_state_schema_impl
    ensure_workflow_state_schema_impl(execute)


def ensure_marker_schema():
    """ADR-001: Marker-Definitionen DB-first."""
    from services.db_marker_schema import ensure_marker_schema_impl
    ensure_marker_schema_impl(execute)


def ensure_plan_task_schema():
    """Sprint Task-Entity: plan_tasks + markers.task_id (FK)."""
    # markers muss existieren bevor task_id FK angelegt wird
    ensure_marker_schema()
    from services.db_plan_task_schema import ensure_plan_task_schema_impl
    ensure_plan_task_schema_impl(execute)


def ensure_plan_task_match_schema():
    """Sprint Task-Backfill: Fuzzy-Match-Suggestions fuer Bestands-Marker."""
    ensure_plan_task_schema()
    from services.db_plan_task_match_schema import ensure_plan_task_match_schema_impl
    ensure_plan_task_match_schema_impl(execute)


def ensure_cwo_schema():
    """CWO Sprint: Context Window Optimizer Tabellen."""
    from services.db_cwo_schema import ensure_cwo_schema_impl
    ensure_cwo_schema_impl(execute)


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


_model_quality_ready = False
_model_quality_lock = threading.Lock()


def ensure_model_quality_view():
    """Sprint 11: Materialized View fuer Modell-Qualitaetsvergleich"""
    global _model_quality_ready
    if _model_quality_ready:
        return
    with _model_quality_lock:
        if _model_quality_ready:
            return
        # Spalten sicherstellen bevor View erstellt wird
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cost_estimate NUMERIC(10,4)")
        execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS duration_minutes NUMERIC(8,2)")
        execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_model_quality AS
            SELECT
                model,
                COUNT(*) AS total_sessions,
                COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS rated_sessions,
                COUNT(*) FILTER (WHERE outcome = 'ok') AS ok_count,
                COUNT(*) FILTER (WHERE outcome = 'needs_fix') AS needs_fix_count,
                COUNT(*) FILTER (WHERE outcome = 'reverted') AS reverted_count,
                ROUND(
                    COUNT(*) FILTER (WHERE outcome IN ('needs_fix', 'reverted'))::numeric /
                    NULLIF(COUNT(*) FILTER (WHERE outcome IS NOT NULL), 0) * 100, 1
                ) AS rework_rate,
                SUM(COALESCE(total_input_tokens, 0) + COALESCE(total_output_tokens, 0)) AS total_tokens,
                SUM(COALESCE(cost_estimate, 0)) AS total_cost,
                AVG(duration_ms / 60000.0) FILTER (WHERE duration_ms > 0) AS avg_duration_min,
                AVG(CASE outcome_severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 END) FILTER (WHERE outcome_severity IS NOT NULL) AS avg_severity
            FROM sessions
            WHERE model IS NOT NULL AND model != '' AND model NOT LIKE '<%>'
            GROUP BY model
        """)
        execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_model_quality_model ON mv_model_quality(model)")
        _model_quality_ready = True

def refresh_model_quality_view():
    """Refresh der Materialized View (concurrent wenn moeglich)"""
    try:
        execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_model_quality")
    except Exception:
        execute("REFRESH MATERIALIZED VIEW mv_model_quality")


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
                file_path TEXT NOT NULL,
                project VARCHAR(200) NOT NULL DEFAULT '',
                touch_type VARCHAR(20) NOT NULL,
                ai_written BOOLEAN DEFAULT FALSE,
                ai_touched BOOLEAN DEFAULT TRUE,
                tool_name VARCHAR(50),
                model VARCHAR(100),
                issue_category VARCHAR(30),
                timestamp TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Spec-Spalten nachrüsten falls Tabelle schon existiert (VOR Index-Erstellung!)
        for col, definition in [
            ("project", "VARCHAR(200) NOT NULL DEFAULT ''"),
            ("ai_written", "BOOLEAN DEFAULT FALSE"),
            ("ai_touched", "BOOLEAN DEFAULT TRUE"),
            ("model", "VARCHAR(100)"),
            ("issue_category", "VARCHAR(30)"),
        ]:
            execute(f"""
                DO $$ BEGIN
                    ALTER TABLE ai_file_touches ADD COLUMN {col} {definition};
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$
            """)
        # Indexes (nach ALTER TABLE, damit alle Spalten existieren)
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_session ON ai_file_touches(session_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_path ON ai_file_touches(file_path)")
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_type ON ai_file_touches(touch_type)")
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_project ON ai_file_touches(project)")
        execute("CREATE INDEX IF NOT EXISTS idx_file_touches_date ON ai_file_touches(timestamp)")
        # Partial index for written files
        execute("""
            CREATE INDEX IF NOT EXISTS idx_file_touches_written
            ON ai_file_touches(ai_written) WHERE ai_written = TRUE
        """)
        # Unique constraint (session_id statt session_uuid, da FK auf id)
        # Erst Duplikate bereinigen, dann Constraint anlegen
        execute("""
            DELETE FROM ai_file_touches a USING ai_file_touches b
            WHERE a.id < b.id
              AND a.session_id = b.session_id
              AND a.file_path = b.file_path
              AND a.touch_type = b.touch_type
        """)
        execute("""
            DO $$ BEGIN
                ALTER TABLE ai_file_touches
                    ADD CONSTRAINT uq_file_touch_session_path_type
                    UNIQUE(session_id, file_path, touch_type);
            EXCEPTION WHEN duplicate_table THEN NULL;
                      WHEN unique_violation THEN NULL;
            END $$
        """)
        _file_touch_ready = True

_project_identity_ready = False
_project_identity_lock = threading.Lock()

def ensure_project_identity_schema():
    """SPEC-PROJECT-MEMORY-001: Projekt-Identity-Tabelle"""
    global _project_identity_ready
    if _project_identity_ready:
        return
    with _project_identity_lock:
        if _project_identity_ready:
            return
        execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                path TEXT NOT NULL,
                category VARCHAR(100),
                topic VARCHAR(100),
                tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                status VARCHAR(50),
                priority VARCHAR(50),
                project_type VARCHAR(100),
                ai_policy_level VARCHAR(50),
                source_updated_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        execute("CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path)")
        _project_identity_ready = True

def ensure_audit_schema():
    """SPEC-AUDIT-001: Tabellen fuer Spec-Audit-System."""
    from services.db_audit_schema import ensure_audit_schema_impl
    ensure_audit_schema_impl(execute)


def ensure_agent_orchestrator_schema():
    """Sprint Agent-Orchestrator Phase 1: agent_task_contracts + agent_session_states."""
    from services.db_agent_orchestrator_schema import ensure_agent_orchestrator_schema_impl
    ensure_agent_orchestrator_schema_impl(execute)


def ensure_agent_verify_schema():
    """Sprint Agent-Orchestrator Phase 2: agent_execution_results + agent_verify_results."""
    from services.db_agent_verify_schema import ensure_agent_verify_schema_impl
    ensure_agent_verify_schema_impl(execute)
