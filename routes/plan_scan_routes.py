"""
Plan-Scan API (Sprint sprint-plan-discovery, Commit 4).

Endpoints:
  GET    /api/plans/scan-preview?project=<name>    — Preview-Baum, kein Schreibzugriff
  GET    /api/plans/scan-exclusions?project=<name> — Liste aktiver Exclusions
  POST   /api/plans/scan-exclusions                — Exclusion anlegen
  DELETE /api/plans/scan-exclusions/<id>           — Exclusion entfernen
  POST   /api/plans/sync-now                       — sync_all_plans(force=True)

Details: sprints/sprint-plan-discovery.md (Nachtrag 3).
"""
import logging
import os

from flask import Blueprint, jsonify, render_template, request

from routes.api_utils import api_route
from services.db_service import execute, ensure_plan_source_schema
from services.plan_discovery_service import discover_plans
from services.plan_scan_exclusion_service import (
    add_exclusion,
    list_exclusions,
    remove_exclusion,
)
from services.plans_sync_service import sync_all_plans

logger = logging.getLogger(__name__)

plan_scan_bp = Blueprint("plan_scan", __name__)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

@plan_scan_bp.route("/plans/scan")
def plan_scan_page():
    return render_template("plan_scan.html", active_page="plans")


def _requester() -> str:
    return (request.headers.get("X-User") or "dashboard").strip() or "dashboard"


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def _existing_source_paths() -> dict[str, int]:
    """Liefert source_path -> id fuer bereits importierte Plaene."""
    try:
        ensure_plan_source_schema()
        rows = execute(
            """SELECT id, source_path FROM project_plans
               WHERE source_path IS NOT NULL""",
            fetch=True,
        )
        return {r["source_path"]: r["id"] for r in (rows or []) if r.get("source_path")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("plan_scan_preview_db_lookup_error error=%s", exc)
        return {}


def _build_preview_entry(record: dict, existing: dict[str, int],
                         hash_counts: dict[str, int]) -> dict:
    """Baut schlankes Preview-Entry (ohne content)."""
    source_path = record.get("source_path")
    content_hash = record.get("content_hash")
    excluded_by = record.get("excluded_by")

    plan_id = existing.get(source_path) if source_path else None

    if excluded_by:
        status = "excluded"
    elif plan_id is not None:
        status = "existing"
    else:
        status = "new"

    if content_hash and hash_counts.get(str(content_hash), 0) > 1:
        is_duplicate = True
    else:
        is_duplicate = False

    directory = os.path.dirname(source_path) if source_path else ""
    return {
        "source_path": source_path,
        "source_kind": record.get("source_kind"),
        "filename": record.get("filename"),
        "directory": directory,
        "project_name": record.get("project_name"),
        "content_hash": content_hash,
        "mtime": record.get("mtime"),
        "excluded_by": excluded_by,
        "status": status,
        "is_duplicate": is_duplicate,
        "plan_id": plan_id,
    }


@plan_scan_bp.route("/api/plans/scan-preview", methods=["GET"])
@api_route
def api_scan_preview():
    """Liefert alles, was discover_plans() finden wuerde, gruppiert.

    Parameter:
      - project (optional): nur dieses Projekt zeigen (Claude-Plans bleiben sichtbar)
      - no_cache=1:         Preview-Cache umgehen (voller Re-Scan)

    Rueckgabe:
      {
        "groups": [
          {
            "project_name": "...",
            "total": N, "new": N, "existing": N, "excluded": N, "duplicates": N,
            "kinds": [ { "source_kind": "...", "directories": [ { "directory": "...", "files": [...] } ] } ]
          }
        ],
        "totals": {...}
      }
    """
    project_filter = (request.args.get("project") or "").strip() or None
    use_cache = request.args.get("no_cache", "").strip() not in ("1", "true", "yes")

    records = discover_plans(use_cache=use_cache)

    # Projekt-Filter: leere Liste bleibt leer, aber claude_plans werden gezeigt
    if project_filter:
        records = [
            r for r in records
            if r.get("project_name") == project_filter
            or r.get("source_kind") == "claude_plans"
        ]

    existing = _existing_source_paths()
    hash_counts: dict[str, int] = {}
    for r in records:
        h = r.get("content_hash")
        if h:
            hash_counts[h] = hash_counts.get(h, 0) + 1

    entries = [_build_preview_entry(r, existing, hash_counts) for r in records]

    # Gruppierung: project_name -> source_kind -> directory
    by_project: dict[str, dict] = {}
    for entry in entries:
        project_key = entry["project_name"] or "__global__"
        bucket = by_project.setdefault(project_key, {
            "project_name": entry["project_name"],
            "total": 0, "new": 0, "existing": 0,
            "excluded": 0, "duplicates": 0,
            "kinds": {},
        })
        bucket["total"] += 1
        bucket[entry["status"]] = bucket.get(entry["status"], 0) + 1
        if entry["is_duplicate"]:
            bucket["duplicates"] += 1

        kind_bucket = bucket["kinds"].setdefault(entry["source_kind"], {
            "source_kind": entry["source_kind"],
            "directories": {},
        })
        dir_key = entry["directory"] or "(root)"
        dir_bucket = kind_bucket["directories"].setdefault(dir_key, {
            "directory": dir_key,
            "files": [],
        })
        dir_bucket["files"].append(entry)

    # Flatten dicts zu Listen, stabile Sortierung
    groups = []
    for key in sorted(by_project.keys(), key=lambda k: (k == "__global__", k)):
        bucket = by_project[key]
        kinds = []
        for kind_name in sorted(bucket["kinds"].keys()):
            kind = bucket["kinds"][kind_name]
            dirs = sorted(kind["directories"].values(),
                          key=lambda d: d["directory"])
            for d in dirs:
                d["files"].sort(key=lambda f: f["filename"] or "")
            kinds.append({"source_kind": kind_name, "directories": dirs})
        bucket["kinds"] = kinds
        groups.append(bucket)

    totals = {
        "total": sum(g["total"] for g in groups),
        "new": sum(g.get("new", 0) for g in groups),
        "existing": sum(g.get("existing", 0) for g in groups),
        "excluded": sum(g.get("excluded", 0) for g in groups),
        "duplicates": sum(g["duplicates"] for g in groups),
    }

    return jsonify({
        "ok": True,
        "project_filter": project_filter,
        "totals": totals,
        "groups": groups,
    })


# ---------------------------------------------------------------------------
# Exclusions CRUD
# ---------------------------------------------------------------------------

@plan_scan_bp.route("/api/plans/scan-exclusions", methods=["GET"])
@api_route
def api_list_exclusions():
    project = (request.args.get("project") or "").strip() or None
    include_global = request.args.get("include_global", "1").strip() not in ("0", "false", "no")
    exclusions = list_exclusions(project_name=project, include_global=include_global)
    return jsonify({"ok": True, "exclusions": exclusions})


@plan_scan_bp.route("/api/plans/scan-exclusions", methods=["POST"])
@api_route
def api_add_exclusion():
    body = request.get_json(silent=True) or {}
    try:
        exclusion = add_exclusion(
            project_name=body.get("project_name"),
            path_pattern=body.get("path_pattern", ""),
            scope=body.get("scope", "folder"),
            reason=body.get("reason"),
            excluded_by=_requester(),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "exclusion": exclusion}), 201


@plan_scan_bp.route("/api/plans/scan-exclusions/<int:exclusion_id>", methods=["DELETE"])
@api_route
def api_remove_exclusion(exclusion_id):
    removed = remove_exclusion(exclusion_id)
    if not removed:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "id": exclusion_id})


# ---------------------------------------------------------------------------
# Sync-Now (umgeht Cooldown)
# ---------------------------------------------------------------------------

@plan_scan_bp.route("/api/plans/sync-now", methods=["POST"])
@api_route
def api_sync_now():
    """Triggert sync_all_plans sofort, umgeht 60-s-Cooldown.

    Circuit-Breaker-Cooldown (15 min bei duration_ms > 5000) bleibt wirksam —
    ein offenes Circuit kann nicht per sync-now umgangen werden, weil der
    Schutz sonst sinnlos waere. Der Modul-Lock wird ebenfalls respektiert.
    """
    stats = sync_all_plans(force=True)
    requester = _requester()
    logger.info("plan_scan_sync_now_audit requester=%s stats=%s", requester, stats)
    return jsonify({"ok": True, "requester": requester, "stats": stats})
