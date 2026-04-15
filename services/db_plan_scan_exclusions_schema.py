"""
Sprint sprint-plan-discovery (2026-04-15):
Tabelle plan_scan_exclusions — GUI-gestuetzte Exclusion-Patterns fuer den
Plan-Discovery-Scanner.

- project_name NULL = globale Exclusion (alle Projekte)
- path_pattern = fnmatch-Glob relativ zum Projekt-Root (z.B. "docs/plans/archive/**")
- scope = 'folder' | 'file'
- UNIQUE(project_name, path_pattern) verhindert Duplikate

Harte Blacklist (node_modules, .git etc.) bleibt im Scanner-Code und wird durch
Exclusions ergaenzt, nicht ueberschrieben.
"""
import threading

_plan_scan_exclusions_schema_ready = False
_plan_scan_exclusions_schema_lock = threading.Lock()


def ensure_plan_scan_exclusions_schema_impl(execute):
    """Erstellt plan_scan_exclusions + Index. Idempotent."""
    global _plan_scan_exclusions_schema_ready
    if _plan_scan_exclusions_schema_ready:
        return
    with _plan_scan_exclusions_schema_lock:
        if _plan_scan_exclusions_schema_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS plan_scan_exclusions (
                id SERIAL PRIMARY KEY,
                project_name VARCHAR(128),
                path_pattern TEXT NOT NULL,
                scope VARCHAR(16) NOT NULL DEFAULT 'folder',
                excluded_at TIMESTAMPTZ DEFAULT NOW(),
                excluded_by VARCHAR(128),
                reason TEXT,
                UNIQUE(project_name, path_pattern)
            )
        """)
        execute("""
            CREATE INDEX IF NOT EXISTS ix_plan_scan_exclusions_project
            ON plan_scan_exclusions(project_name)
        """)

        _plan_scan_exclusions_schema_ready = True
