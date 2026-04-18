"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
Loader/Writer fuer projektspezifische Agent-Orchestrator-Konfiguration.

Kapselt:
  * get_config(project_id)    -> vollstaendige Config mit Default-Fallback je Feld
  * set_config(project_id, **fields) -> Upsert nur der uebergebenen Felder
  * delete_config(project_id) -> entfernt DB-Eintrag, Defaults gelten wieder

Die Defaults spiegeln den heutigen Dashboard-Stand (SENSITIVE_FILES,
DASHBOARD-GENERATED-Regex, next-session.md). Dashboard selbst braucht damit
keinen Eintrag in agent_project_configs, um wie bisher zu laufen
(#spec-agent-project-config, AC5).
"""
import json

from services.db_service import execute, ensure_agent_project_config_schema


DEFAULT_SENSITIVE_FILES = [
    "next-session.md",
    "handoff.md",
    "sprints/master-plan-2026-04-01.md",
]
DEFAULT_BLOCK_START_REGEX = r"<!--\s*DASHBOARD-GENERATED:START"
DEFAULT_BLOCK_END_REGEX = r"<!--\s*DASHBOARD-GENERATED:END"
DEFAULT_HANDOFF_PATH_RELATIVE = "next-session.md"
DEFAULT_DOCS_PATHS: list[str] = []


ALLOWED_FIELDS = (
    "sensitive_files",
    "append_only_block_start_regex",
    "append_only_block_end_regex",
    "handoff_path_relative",
    "docs_paths",
    "allowed_verify_commands",
)


def get_config(project_id):
    """Liefert die effektive Config fuer ein Projekt.

    project_id = None -> alle Defaults (keine DB-Abfrage).
    Fehlende Felder im DB-Eintrag fallen feldweise auf Default zurueck
    (#spec-config-resolution).
    """
    if project_id is None:
        return _default_config(None)

    try:
        normalized_id = int(project_id)
    except (TypeError, ValueError):
        return _default_config(project_id)

    ensure_agent_project_config_schema()
    row = execute(
        """
        SELECT project_id,
               sensitive_files_json,
               append_only_block_start_regex,
               append_only_block_end_regex,
               handoff_path_relative,
               docs_paths_json,
               allowed_verify_commands_json,
               created_at,
               updated_at
        FROM agent_project_configs
        WHERE project_id = %s
        """,
        (normalized_id,),
        fetchone=True,
    )
    if not row:
        return _default_config(normalized_id)

    return {
        "project_id": normalized_id,
        "sensitive_files": _coerce_list(
            row.get("sensitive_files_json"), DEFAULT_SENSITIVE_FILES
        ),
        "append_only_block_start_regex": row.get("append_only_block_start_regex")
            or DEFAULT_BLOCK_START_REGEX,
        "append_only_block_end_regex": row.get("append_only_block_end_regex")
            or DEFAULT_BLOCK_END_REGEX,
        "handoff_path_relative": row.get("handoff_path_relative")
            or DEFAULT_HANDOFF_PATH_RELATIVE,
        "docs_paths": _coerce_list(
            row.get("docs_paths_json"), DEFAULT_DOCS_PATHS
        ),
        # Sprint Soll-Workflow-Luecken Session L3: None = nicht konfiguriert
        # (= kein Whitelist-Check); [] = leer konfiguriert (= alles blocked);
        # Liste = exakte String-Matches erlaubt.
        "allowed_verify_commands": _coerce_list_or_none(
            row.get("allowed_verify_commands_json")
        ),
    }


def set_config(project_id, **fields):
    """Upserts die uebergebenen Felder. Unbekannte Keys werden ignoriert.

    Felder, die NICHT uebergeben werden, bleiben auf dem bisherigen DB-Wert
    (bzw. NULL -> Default-Fallback beim Lesen).
    """
    if project_id is None:
        raise ValueError("project_id darf nicht None sein")
    try:
        normalized_id = int(project_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"project_id muss numerisch sein: {project_id}") from exc

    unknown = [k for k in fields if k not in ALLOWED_FIELDS]
    if unknown:
        raise ValueError(f"unbekannte Config-Felder: {unknown}")

    ensure_agent_project_config_schema()

    current = execute(
        "SELECT project_id FROM agent_project_configs WHERE project_id = %s",
        (normalized_id,),
        fetchone=True,
    )
    if not current:
        execute(
            """
            INSERT INTO agent_project_configs (
                project_id, sensitive_files_json,
                append_only_block_start_regex, append_only_block_end_regex,
                handoff_path_relative, docs_paths_json,
                allowed_verify_commands_json
            )
            VALUES (%s, %s::jsonb, %s, %s, %s, %s::jsonb, %s::jsonb)
            """,
            (
                normalized_id,
                _to_json_or_null(fields.get("sensitive_files")),
                fields.get("append_only_block_start_regex"),
                fields.get("append_only_block_end_regex"),
                fields.get("handoff_path_relative"),
                _to_json_or_null(fields.get("docs_paths")),
                _to_json_or_null(fields.get("allowed_verify_commands")),
            ),
        )
        return get_config(normalized_id)

    assignments = []
    params = []
    if "sensitive_files" in fields:
        assignments.append("sensitive_files_json = %s::jsonb")
        params.append(_to_json_or_null(fields.get("sensitive_files")))
    if "append_only_block_start_regex" in fields:
        assignments.append("append_only_block_start_regex = %s")
        params.append(fields.get("append_only_block_start_regex"))
    if "append_only_block_end_regex" in fields:
        assignments.append("append_only_block_end_regex = %s")
        params.append(fields.get("append_only_block_end_regex"))
    if "handoff_path_relative" in fields:
        assignments.append("handoff_path_relative = %s")
        params.append(fields.get("handoff_path_relative"))
    if "docs_paths" in fields:
        assignments.append("docs_paths_json = %s::jsonb")
        params.append(_to_json_or_null(fields.get("docs_paths")))
    if "allowed_verify_commands" in fields:
        assignments.append("allowed_verify_commands_json = %s::jsonb")
        params.append(_to_json_or_null(fields.get("allowed_verify_commands")))

    if assignments:
        assignments.append("updated_at = NOW()")
        sql = (
            "UPDATE agent_project_configs SET "
            + ", ".join(assignments)
            + " WHERE project_id = %s"
        )
        params.append(normalized_id)
        execute(sql, tuple(params))

    return get_config(normalized_id)


def delete_config(project_id):
    """Entfernt den DB-Eintrag. Danach gelten wieder Defaults."""
    try:
        normalized_id = int(project_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"project_id muss numerisch sein: {project_id}") from exc
    ensure_agent_project_config_schema()
    execute(
        "DELETE FROM agent_project_configs WHERE project_id = %s",
        (normalized_id,),
    )


def _default_config(project_id):
    return {
        "project_id": project_id,
        "sensitive_files": list(DEFAULT_SENSITIVE_FILES),
        "append_only_block_start_regex": DEFAULT_BLOCK_START_REGEX,
        "append_only_block_end_regex": DEFAULT_BLOCK_END_REGEX,
        "handoff_path_relative": DEFAULT_HANDOFF_PATH_RELATIVE,
        "docs_paths": list(DEFAULT_DOCS_PATHS),
        # None = nicht konfiguriert -> im Gate kein Whitelist-Check.
        "allowed_verify_commands": None,
    }


def _coerce_list_or_none(value):
    """Wie `_coerce_list`, unterscheidet aber NULL vom leer-Array:
    * None / ungueltiger Wert -> None (= nicht konfiguriert)
    * [] -> [] (= explizit leere Whitelist)
    * [..] -> Liste
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return None
    return None


def _coerce_list(value, default):
    if value is None:
        return list(default)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return list(default)
    return list(default)


def _to_json_or_null(value):
    if value is None:
        return None
    return json.dumps(value)
