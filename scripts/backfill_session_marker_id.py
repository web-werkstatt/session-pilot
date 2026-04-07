#!/usr/bin/env python3
"""
Sprint SB - Backfill fuer sessions.marker_id

Iteriert ueber alle Projektordner unter PROJECTS_DIR. Wo eine handoff.md
existiert, werden alle Marker mit nicht-leerem last_session genutzt, um
sessions.marker_id und sessions.marker_handoff_path zu setzen - aber nur,
wenn sessions.marker_id noch NULL ist (idempotent, nicht-destruktiv).

Aufruf:
    python3 scripts/backfill_session_marker_id.py
    python3 scripts/backfill_session_marker_id.py --project project_dashboard
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import PROJECTS_DIR
from services.copilot_marker_format import parse_markers
from services.db_service import ensure_session_marker_schema, execute


def _iter_handoff_files(project_filter=None):
    """Yield (project_name, handoff_path) fuer alle Projekte mit handoff.md."""
    if not os.path.isdir(PROJECTS_DIR):
        return
    for entry in sorted(os.listdir(PROJECTS_DIR)):
        if project_filter and entry != project_filter:
            continue
        project_root = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(project_root):
            continue
        handoff_path = os.path.join(project_root, "handoff.md")
        if os.path.isfile(handoff_path):
            yield entry, handoff_path


def backfill_project(project_name, handoff_path):
    """Stempelt sessions.marker_id fuer alle Marker in einer handoff.md."""
    markers = parse_markers(handoff_path)
    stats = {
        "project": project_name,
        "handoff_path": handoff_path,
        "markers_total": len(markers),
        "markers_with_session": 0,
        "sessions_updated": 0,
        "sessions_already_set": 0,
        "sessions_missing": 0,
    }
    for marker in markers:
        session_uuid = str(marker.last_session or "").strip()
        if not session_uuid:
            continue
        stats["markers_with_session"] += 1

        existing = execute(
            "SELECT id, marker_id FROM sessions WHERE session_uuid = %s",
            (session_uuid,),
            fetchone=True,
        )
        if not existing:
            stats["sessions_missing"] += 1
            continue
        if existing.get("marker_id"):
            stats["sessions_already_set"] += 1
            continue

        execute(
            """UPDATE sessions
                  SET marker_id = %s,
                      marker_handoff_path = %s,
                      updated_at = NOW()
                WHERE session_uuid = %s
                  AND marker_id IS NULL""",
            (marker.marker_id, handoff_path, session_uuid),
        )
        stats["sessions_updated"] += 1
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill sessions.marker_id aus marker.last_session in allen handoff.md."
    )
    parser.add_argument("--project", help="Nur dieses eine Projekt verarbeiten")
    args = parser.parse_args()

    ensure_session_marker_schema()

    results = []
    totals = {
        "projects_scanned": 0,
        "markers_total": 0,
        "markers_with_session": 0,
        "sessions_updated": 0,
        "sessions_already_set": 0,
        "sessions_missing": 0,
    }
    for project_name, handoff_path in _iter_handoff_files(args.project):
        stats = backfill_project(project_name, handoff_path)
        results.append(stats)
        totals["projects_scanned"] += 1
        for key in (
            "markers_total",
            "markers_with_session",
            "sessions_updated",
            "sessions_already_set",
            "sessions_missing",
        ):
            totals[key] += stats[key]

    print(json.dumps({"totals": totals, "per_project": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
