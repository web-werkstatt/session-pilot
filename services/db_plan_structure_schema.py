"""
Ausgelagerte Schema-Sicherung fuer Plan -> Sprint-Plan -> Spec.
"""
import threading


_plan_structure_ready = False
_plan_structure_lock = threading.Lock()


def ensure_plan_structure_schema_impl(execute, ensure_plan_workflow_schema):
    global _plan_structure_ready
    if _plan_structure_ready:
        return
    with _plan_structure_lock:
        if _plan_structure_ready:
            return
        ensure_plan_workflow_schema()
        execute("""
            CREATE TABLE IF NOT EXISTS sprint_plans (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR(255) NOT NULL,
                plan_id VARCHAR(120) NOT NULL,
                title VARCHAR(500) NOT NULL,
                status VARCHAR(30) DEFAULT 'planned',
                parent_plan_id INTEGER REFERENCES project_plans(id) ON DELETE SET NULL,
                sprint_file VARCHAR(1000),
                anchor VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(project_id, plan_id)
            )
        """)
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS project_id VARCHAR(255)")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS plan_id VARCHAR(120)")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS title VARCHAR(500)")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'planned'")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS parent_plan_id INTEGER")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS sprint_file VARCHAR(1000)")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS anchor VARCHAR(255)")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
        execute("ALTER TABLE sprint_plans ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")
        execute("""
            CREATE TABLE IF NOT EXISTS specs (
                id SERIAL PRIMARY KEY,
                sprint_plan_id INTEGER NOT NULL REFERENCES sprint_plans(id) ON DELETE CASCADE,
                anchor VARCHAR(255),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                status VARCHAR(30) DEFAULT 'planned',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(sprint_plan_id, anchor)
            )
        """)
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS sprint_plan_id INTEGER")
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS anchor VARCHAR(255)")
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS title VARCHAR(500)")
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS description TEXT")
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'planned'")
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
        execute("ALTER TABLE specs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()")
        execute("CREATE INDEX IF NOT EXISTS idx_sprint_plans_project ON sprint_plans(project_id, updated_at DESC)")
        execute("CREATE INDEX IF NOT EXISTS idx_sprint_plans_parent ON sprint_plans(parent_plan_id)")
        execute("CREATE INDEX IF NOT EXISTS idx_specs_sprint_plan ON specs(sprint_plan_id, updated_at DESC)")
        _plan_structure_ready = True
