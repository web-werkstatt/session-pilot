"""
ADR-001: Importiert Marker-Definitionen aus handoff.md in die DB.

Idempotent: Re-Run aktualisiert bestehende Marker, legt neue an, loescht nichts.
Legacy-Marker (done ohne Rating) werden als review_needed markiert.
"""
import json
import logging
import os

from config import PROJECTS_DIR
from services.copilot_marker_format import parse_markers_with_errors
from services.db_service import ensure_marker_schema, execute
from services.path_resolver import resolve_project_path

log = logging.getLogger(__name__)


def _get_handoff_path(project_name):
    """Ermittelt den handoff.md-Pfad fuer ein Projekt."""
    direct_root = os.path.join(PROJECTS_DIR, project_name)
    if os.path.isdir(direct_root):
        return os.path.join(direct_root, "handoff.md")
    project_root = resolve_project_path(project_name)
    if project_root:
        return os.path.join(project_root, "handoff.md")
    return os.path.join(PROJECTS_DIR, project_name, "handoff.md")


def import_markers_from_handoff(project_name):
    """Importiert alle Marker aus der handoff.md eines Projekts in die DB.

    Returns:
        dict mit created, updated, skipped, errors counts
    """
    ensure_marker_schema()
    project_name = str(project_name or "").strip()
    if not project_name:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    handoff_path = _get_handoff_path(project_name)
    if not os.path.exists(handoff_path):
        return {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    markers, parse_errors = parse_markers_with_errors(handoff_path)

    created = 0
    updated = 0
    skipped = 0

    for marker in markers:
        try:
            result = _upsert_marker(project_name, marker)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1
        except Exception as exc:
            log.warning("Marker-Import fehlgeschlagen: %s/%s: %s",
                        project_name, marker.marker_id, exc)
            parse_errors.append({
                "marker_id": marker.marker_id,
                "error": str(exc),
                "error_type": "db_write",
                "handoff_path": handoff_path,
            })

    log.info("Marker-Import %s: %d created, %d updated, %d skipped, %d errors",
             project_name, created, updated, skipped, len(parse_errors))

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": parse_errors,
    }


def _upsert_marker(project_name, marker):
    """Fuegt einen Marker ein oder aktualisiert ihn. Gibt 'created'/'updated'/'skipped' zurueck."""
    existing = execute(
        "SELECT id, status, updated_at FROM markers WHERE project_name = %s AND marker_id = %s",
        (project_name, marker.marker_id),
        fetchone=True,
    )

    checks_json = json.dumps(marker.checks or [], ensure_ascii=True)
    last_exec = str(marker.last_execution_at or "").strip() or None

    if existing:
        # Update: nur wenn sich etwas geaendert hat
        execute(
            """UPDATE markers SET
                titel = %s,
                plan_id = %s,
                status = %s,
                ziel = %s,
                naechster_schritt = %s,
                prompt = %s,
                prompt_suggestion = %s,
                risiko = %s,
                checks = %s::jsonb,
                last_session = %s,
                execution_score = %s,
                execution_comment = %s,
                last_execution_at = %s,
                sprint_tag = %s,
                spec_tag = %s,
                sprint_plan_id = %s,
                spec_id = %s,
                updated_at = NOW()
            WHERE project_name = %s AND marker_id = %s""",
            (
                marker.titel,
                str(marker.plan_id),
                marker.status,
                marker.ziel,
                marker.naechster_schritt,
                marker.prompt or "",
                marker.prompt_suggestion or "",
                marker.risiko or "",
                checks_json,
                marker.last_session or "",
                marker.execution_score,
                marker.execution_comment or "",
                last_exec,
                marker.sprint_tag or "",
                marker.spec_tag or "",
                marker.sprint_plan_id,
                marker.spec_id,
                project_name,
                marker.marker_id,
            ),
        )
        return "updated"

    # Insert
    execute(
        """INSERT INTO markers (
            project_name, marker_id, titel, plan_id, status, ziel,
            naechster_schritt, prompt, prompt_suggestion, risiko, checks,
            last_session, execution_score, execution_comment,
            last_execution_at, sprint_tag, spec_tag,
            sprint_plan_id, spec_id, imported_from
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s::jsonb,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, 'handoff'
        )""",
        (
            project_name,
            marker.marker_id,
            marker.titel,
            str(marker.plan_id),
            marker.status,
            marker.ziel,
            marker.naechster_schritt,
            marker.prompt or "",
            marker.prompt_suggestion or "",
            marker.risiko or "",
            checks_json,
            marker.last_session or "",
            marker.execution_score,
            marker.execution_comment or "",
            last_exec,
            marker.sprint_tag or "",
            marker.spec_tag or "",
            marker.sprint_plan_id,
            marker.spec_id,
        ),
    )
    return "created"


def import_all_projects():
    """Importiert Marker aus allen Projekten unter PROJECTS_DIR.

    Returns:
        dict {project_name: import_result}
    """
    results = {}
    if not os.path.isdir(PROJECTS_DIR):
        return results

    for entry in sorted(os.listdir(PROJECTS_DIR)):
        project_dir = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(project_dir):
            continue
        handoff_path = os.path.join(project_dir, "handoff.md")
        if not os.path.exists(handoff_path):
            continue
        result = import_markers_from_handoff(entry)
        if result["created"] or result["updated"] or result["errors"]:
            results[entry] = result

    return results
