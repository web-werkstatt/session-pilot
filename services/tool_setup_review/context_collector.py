"""
ADR-002 Stufe 1a: Observe-Schicht - Context-Collector fuer Setup-Reviewer.

Sammelt Projektkontext aus bestehenden Services (project.json, Tool-Files,
workflow_core_service, Quality-Scanner, marker-context.md) zu einem rein
beschreibenden Snapshot. Der Collector urteilt nicht - der Reviewer
(Perplexity) urteilt.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from services.tool_setup_review.constants import (
    EXCERPT_HEAD_LINES,
    EXCERPT_TAIL_LINES,
    SCHEMA_VERSION,
    TOOL_FILES,
)
from services.tool_setup_review.drift_check import detect_context_drift

log = logging.getLogger(__name__)


def build_tool_setup_context(project_name: str) -> Optional[Dict[str, Any]]:
    """Sammelt Projektkontext fuer den Reviewer.

    Returns:
        Context-Dict oder None wenn Projekt nicht existiert.
    """
    from services.path_resolver import resolve_project_path
    from services.project_scanner import load_project_json

    project_path = resolve_project_path(project_name)
    if not project_path:
        return None

    pjson = load_project_json(project_path) or {}

    tool_files: Dict[str, Dict[str, Any]] = {}
    for filename in TOOL_FILES.values():
        filepath = os.path.join(project_path, filename)
        tool_files[filename] = _collect_tool_file_info(filepath)

    drift = detect_context_drift(tool_files)
    workflow_snapshot = _collect_workflow_snapshot(project_name, project_path)
    quality_snapshot = _collect_quality_snapshot(project_path)

    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "name": project_name,
            "path": project_path,
            "type": pjson.get("project_type") or pjson.get("type"),
            "description": pjson.get("description"),
            "tags": pjson.get("tags") or [],
            "meta_commands": (pjson.get("meta") or {}).get("commands"),
        },
        "tool_files": tool_files,
        "context_drift": drift,
        "workflow_snapshot": workflow_snapshot,
        "quality_snapshot": quality_snapshot,
        "policy_hints": {
            "faustregel": [
                "Muss das AI-Tool das in fast jeder Session wissen?",
                "Waere es teuer oder fehleranfaellig, wenn das Tool es erst selbst herausfinden muesste?",
                "Ist es eine Regel oder ein Stolperstein, die/den das Tool nicht sicher aus dem Code ableiten kann?",
            ],
            "forbidden_block_content": [
                "Heuristisch geratene Befehle",
                "Metadaten die in project.json oder README bereits stehen",
                "Staendig wechselnder Status der nicht session-start-relevant ist",
            ],
        },
    }


def _collect_tool_file_info(filepath: str) -> Dict[str, Any]:
    """Liest eine Tool-Datei und extrahiert Struktur + Generated-Block."""
    if not os.path.exists(filepath):
        return {
            "exists": False,
            "size_lines": 0,
            "has_generated_block": False,
            "manual_excerpt_head": None,
            "manual_excerpt_tail": None,
            "generated_block_content": None,
            "generated_block_source": None,
            "generated_block_updated": None,
        }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        log.warning("Konnte Tool-Datei nicht lesen: %s (%s)", filepath, e)
        return {
            "exists": True,
            "size_lines": 0,
            "has_generated_block": False,
            "manual_excerpt_head": None,
            "manual_excerpt_tail": None,
            "generated_block_content": None,
            "generated_block_source": None,
            "generated_block_updated": None,
            "read_error": str(e),
        }

    generated_content: Optional[str] = None
    generated_source: Optional[str] = None
    generated_updated: Optional[str] = None

    try:
        from services.block_marker_parser import BlockType, parse_blocks

        blocks = parse_blocks(filepath)
        generated_blocks = [
            b for b in blocks if b.block_type == BlockType.DASHBOARD_GENERATED
        ]
        if generated_blocks:
            first = generated_blocks[0]
            block_lines = lines[first.start_line - 1 : first.end_line - 1]
            generated_content = "".join(block_lines)
            generated_source = first.source
            generated_updated = first.updated
    except Exception as e:
        log.warning("block_marker_parser fehlgeschlagen fuer %s: %s", filepath, e)

    head = "".join(lines[:EXCERPT_HEAD_LINES])
    tail = ""
    if len(lines) > EXCERPT_HEAD_LINES + EXCERPT_TAIL_LINES:
        tail = "".join(lines[-EXCERPT_TAIL_LINES:])

    return {
        "exists": True,
        "size_lines": len(lines),
        "has_generated_block": generated_content is not None,
        "manual_excerpt_head": head,
        "manual_excerpt_tail": tail,
        "generated_block_content": generated_content,
        "generated_block_source": generated_source,
        "generated_block_updated": generated_updated,
    }


def _collect_workflow_snapshot(project_name: str, project_path: str) -> Dict[str, Any]:
    """Liest aktiven Marker + marker-context.md als Fokuszustand."""
    try:
        from services.workflow_core_service import get_markers

        markers = get_markers(project_name)
    except Exception as e:
        log.info("workflow_core_service.get_markers fehlgeschlagen: %s", e)
        markers = []

    def _s(m, attr):
        return getattr(m, attr, None)

    active = [m for m in markers if _s(m, "status") == "active"]
    ready = [m for m in markers if _s(m, "status") == "ready"]
    blocked = [m for m in markers if _s(m, "status") == "blocked"]
    done = [m for m in markers if _s(m, "status") == "done"]

    primary = active[0] if active else None

    marker_context_path = os.path.join(project_path, "marker-context.md")
    marker_context_info = _inspect_marker_context(marker_context_path)

    return {
        "active_marker_id": _s(primary, "marker_id"),
        "active_marker_title": _s(primary, "titel"),
        "active_marker_next_step": _s(primary, "naechster_schritt"),
        "marker_context_exists": marker_context_info["exists"],
        "marker_context_status": marker_context_info["status"],
        "marker_context_warning": marker_context_info["warning"],
        "counts": {
            "active": len(active),
            "ready": len(ready),
            "blocked": len(blocked),
            "done": len(done),
            "total": len(markers),
        },
    }


def _inspect_marker_context(path: str) -> Dict[str, Any]:
    """Analysiert marker-context.md nur oberflaechlich.

    Erkennt insbesondere bekannte Test-Marker-Muster, damit der Reviewer
    warnen kann, wenn marker-context.md noch einen veralteten Test-Marker
    enthaelt.
    """
    if not os.path.exists(path):
        return {"exists": False, "status": "absent", "warning": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return {"exists": True, "status": "unreadable", "warning": "read_error"}

    lowered = text.lower()
    if "test-cockpit" in lowered or "testmarker" in lowered:
        return {
            "exists": True,
            "status": "testmarker_detected",
            "warning": "marker-context.md enthaelt einen Testmarker, moeglicherweise veraltet",
        }
    if not text.strip():
        return {"exists": True, "status": "empty", "warning": None}
    return {"exists": True, "status": "present", "warning": None}


def _collect_quality_snapshot(project_path: str) -> Dict[str, Any]:
    """Liest minimalen Quality-Snapshot, falls Report existiert.

    Stufe 1a ist bewusst minimal: ein optionaler quality_report.json wird
    gelesen, wenn vorhanden. Volle Quality-Integration kommt spaeter.
    """
    report_path = os.path.join(project_path, "quality_report.json")
    if not os.path.exists(report_path):
        return {"available": False}
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"available": False, "error": "parse_failed"}

    return {
        "available": True,
        "score": data.get("score"),
        "issues_count": len(data.get("issues") or []),
        "raw_summary": data.get("summary"),
    }
