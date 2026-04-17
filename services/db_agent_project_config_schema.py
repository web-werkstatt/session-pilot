"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
DB-Schema fuer projektspezifische Agent-Orchestrator-Konfiguration.

Legt eine Tabelle an:
  * agent_project_configs -> pro Projekt austauschbare Werte fuer
    sensitive_files, Append-only-Block-Marker, handoff_path und docs_paths.

Idempotent und thread-safe nach Muster db_agent_orchestrator_schema.py.
"""
import threading

_agent_project_config_ready = False
_agent_project_config_lock = threading.Lock()


def ensure_agent_project_config_schema_impl(execute):
    """Erstellt agent_project_configs. Idempotent."""
    global _agent_project_config_ready
    if _agent_project_config_ready:
        return
    with _agent_project_config_lock:
        if _agent_project_config_ready:
            return

        execute("""
            CREATE TABLE IF NOT EXISTS agent_project_configs (
                project_id INTEGER PRIMARY KEY,
                sensitive_files_json JSONB,
                append_only_block_start_regex TEXT,
                append_only_block_end_regex TEXT,
                handoff_path_relative TEXT,
                docs_paths_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        _agent_project_config_ready = True
