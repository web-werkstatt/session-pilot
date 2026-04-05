"""
Ausgelagerte Schema-Sicherung fuer Plan-Workflow-Spalten.
"""
import threading


_plan_workflow_ready = False
_plan_workflow_lock = threading.Lock()


def ensure_plan_workflow_schema_impl(execute, ensure_plans_schema):
    global _plan_workflow_ready
    if _plan_workflow_ready:
        return
    with _plan_workflow_lock:
        if _plan_workflow_ready:
            return
        ensure_plans_schema()
        columns = [
            ("plan_type", "VARCHAR(50) DEFAULT 'plan'"),
            ("workflow_stage", "VARCHAR(30) DEFAULT 'idea'"),
            ("current_state", "TEXT"),
            ("target_state", "TEXT"),
            ("next_action", "TEXT"),
            ("latest_executor_status", "VARCHAR(30)"),
            ("latest_review_status", "VARCHAR(30)"),
            ("open_items_count", "INTEGER DEFAULT 0"),
            ("latest_audit_status", "VARCHAR(30)"),
            ("latest_quality_score", "INTEGER"),
            ("governance_status", "VARCHAR(20)"),
            ("spec_ref", "VARCHAR(500)"),
            ("prompt_ref", "VARCHAR(500)"),
            ("last_run_at", "TIMESTAMPTZ"),
        ]
        for col_name, col_def in columns:
            try:
                execute(f"ALTER TABLE project_plans ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

        try:
            execute("ALTER TABLE copilot_runs ADD COLUMN plan_id INTEGER")
        except Exception:
            pass
        try:
            execute("CREATE INDEX IF NOT EXISTS idx_copilot_runs_plan ON copilot_runs(plan_id)")
        except Exception:
            pass
        _plan_workflow_ready = True
