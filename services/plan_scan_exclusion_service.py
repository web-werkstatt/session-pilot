"""
Plan-Scan-Exclusion-CRUD (Sprint sprint-plan-discovery, Commit 4).

Reine DB-Schicht fuer `plan_scan_exclusions`. Die pfad-bezogene Matching-
Funktion `is_excluded()` liegt bewusst in `plan_discovery_service`, weil
der Scanner sie waehrend der Iteration braucht und keinen Zirkel-Import
erzwingen soll.

Details: sprints/sprint-plan-discovery.md (Nachtrag 3).
"""
import logging
from typing import Optional

from services.db_service import ensure_plan_scan_exclusions_schema, execute

logger = logging.getLogger(__name__)

ALLOWED_SCOPES = frozenset({"folder", "file"})


def _normalize_project_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value or value.lower() in ("null", "none", "*"):
        return None
    return value


def list_exclusions(project_name: Optional[str] = None,
                    include_global: bool = True) -> list[dict]:
    """Gibt Exclusions zurueck.

    - project_name=None: alle Exclusions (global + projekt-spezifisch)
    - project_name='<name>', include_global=True: globale + Projekt-spezifische
    - project_name='<name>', include_global=False: nur Projekt-spezifische
    """
    ensure_plan_scan_exclusions_schema()
    project_name = _normalize_project_name(project_name)

    if project_name is None:
        rows = execute(
            """SELECT id, project_name, path_pattern, scope, excluded_at,
                      excluded_by, reason
               FROM plan_scan_exclusions
               ORDER BY project_name NULLS FIRST, path_pattern""",
            fetch=True,
        )
    elif include_global:
        rows = execute(
            """SELECT id, project_name, path_pattern, scope, excluded_at,
                      excluded_by, reason
               FROM plan_scan_exclusions
               WHERE project_name IS NULL OR project_name = %s
               ORDER BY project_name NULLS FIRST, path_pattern""",
            (project_name,),
            fetch=True,
        )
    else:
        rows = execute(
            """SELECT id, project_name, path_pattern, scope, excluded_at,
                      excluded_by, reason
               FROM plan_scan_exclusions
               WHERE project_name = %s
               ORDER BY path_pattern""",
            (project_name,),
            fetch=True,
        )
    return [_serialize(r) for r in (rows or [])]


def add_exclusion(project_name: Optional[str], path_pattern: str,
                  scope: str = "folder", reason: Optional[str] = None,
                  excluded_by: Optional[str] = None) -> dict:
    """Legt eine neue Exclusion an. Idempotent via UNIQUE(project_name, path_pattern).

    Raises ValueError bei invalidem Input.
    """
    ensure_plan_scan_exclusions_schema()
    project_name = _normalize_project_name(project_name)
    path_pattern = (path_pattern or "").strip()
    scope = (scope or "folder").strip().lower()

    if not path_pattern:
        raise ValueError("path_pattern ist erforderlich")
    if scope not in ALLOWED_SCOPES:
        raise ValueError(f"scope muss in {sorted(ALLOWED_SCOPES)} sein")
    if len(path_pattern) > 512:
        raise ValueError("path_pattern zu lang (max 512)")

    # ON CONFLICT: bestehende Exclusion wird aktualisiert (scope/reason/by)
    row = execute(
        """INSERT INTO plan_scan_exclusions
               (project_name, path_pattern, scope, reason, excluded_by)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (project_name, path_pattern)
           DO UPDATE SET scope = EXCLUDED.scope,
                         reason = EXCLUDED.reason,
                         excluded_by = EXCLUDED.excluded_by,
                         excluded_at = NOW()
           RETURNING id, project_name, path_pattern, scope, excluded_at,
                     excluded_by, reason""",
        (project_name, path_pattern, scope, reason, excluded_by),
        fetchone=True,
    )
    logger.info(
        "plan_scan_exclusion_added project=%s pattern=%s scope=%s",
        project_name, path_pattern, scope,
    )
    return _serialize(row)


def remove_exclusion(exclusion_id: int) -> bool:
    """Loescht eine Exclusion. True wenn entfernt, False wenn nicht gefunden."""
    ensure_plan_scan_exclusions_schema()
    row = execute(
        "DELETE FROM plan_scan_exclusions WHERE id = %s RETURNING id",
        (exclusion_id,),
        fetchone=True,
    )
    if row:
        logger.info("plan_scan_exclusion_removed id=%s", exclusion_id)
        return True
    return False


def _serialize(row) -> dict:
    if row is None:
        return {}
    excluded_at = row.get("excluded_at")
    return {
        "id": row.get("id"),
        "project_name": row.get("project_name"),
        "path_pattern": row.get("path_pattern"),
        "scope": row.get("scope"),
        "excluded_at": excluded_at.isoformat() if excluded_at else None,
        "excluded_by": row.get("excluded_by"),
        "reason": row.get("reason"),
    }
