#!/usr/bin/env python3
"""
Projektweite Check/Apply-Routine fuer Sprint-/Spec-Tags in Markdown-Dateien.

Modul 2/3 von Sprint PX:
- scannt relevante Markdown-Dateien
- meldet fehlende #sprint-* / #spec-* Tags
- kann die fehlenden Tags idempotent direkt in Heading-Zeilen schreiben
- meldet optional Marker in handoff.md ohne sprint_tag/spec_tag
- kann bestehende Marker konservativ mit sprint_tag/spec_tag nachziehen
"""
import argparse
import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.copilot_marker_service import _write_marker, parse_markers
from services.markdown_routine_service import (
    apply_tag_update_plan,
    build_tag_update_plan,
    classify_markdown_content,
    read_markdown_with_fallback,
    scan_markdown_structure,
)
from services.path_resolver import resolve_project_path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "static",
    "BACKUP_FRAGENKATALOGE",
}


def resolve_scan_root(project_arg):
    if not project_arg:
        return os.getcwd()
    if os.path.isabs(project_arg) and os.path.isdir(project_arg):
        return project_arg
    resolved = resolve_project_path(project_arg)
    if resolved:
        return resolved
    local = os.path.abspath(project_arg)
    if os.path.isdir(local):
        return local
    raise FileNotFoundError(f"Projektpfad nicht gefunden: {project_arg}")


def iter_markdown_files(root_path):
    for current_root, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS and not name.startswith(".")]
        for filename in sorted(filenames):
            if filename.lower().endswith(".md"):
                yield os.path.join(current_root, filename)


def scan_markdown_file(path):
    loaded = read_markdown_with_fallback(path)
    classification = classify_markdown_content(path, loaded["content"])
    updates = build_tag_update_plan(loaded["content"])
    structure = scan_markdown_structure(loaded["content"], path)
    return {
        "path": path,
        "encoding": loaded["encoding"],
        "classification": classification,
        "updates": updates,
        "content": loaded["content"],
        "structure": structure,
    }


def _normalize_text(value):
    return " ".join(str(value or "").strip().lower().split())


def build_marker_mapping_index(markdown_results):
    plan_to_sprints = {}
    for item in markdown_results:
        structure = item.get("structure") or {}
        for sprint in structure.get("sprints") or []:
            sprint_tag = str(sprint.get("sprint_tag") or "").strip()
            plan_id = str(sprint.get("plan_id") or "").strip()
            if not sprint_tag or not plan_id:
                continue
            entry = {
                "path": item["path"],
                "plan_id": plan_id,
                "sprint_title": sprint.get("title") or "",
                "sprint_tag": sprint_tag,
                "specs": [],
                "tasks": {_normalize_text(task): {"spec_tag": "", "spec_title": ""} for task in sprint.get("tasks") or []},
            }
            for spec in sprint.get("specs") or []:
                spec_tag = str(spec.get("spec_tag") or "").strip()
                spec_title = str(spec.get("title") or "").strip()
                if spec_tag and spec_title:
                    entry["specs"].append({
                        "spec_tag": spec_tag,
                        "spec_title": spec_title,
                        "normalized_title": _normalize_text(spec_title),
                    })
                for task in spec.get("tasks") or []:
                    entry["tasks"][_normalize_text(task)] = {
                        "spec_tag": spec_tag,
                        "spec_title": spec_title,
                    }
            plan_to_sprints.setdefault(plan_id, []).append(entry)
    return plan_to_sprints


def _select_marker_mapping(marker, plan_to_sprints):
    candidates = list(plan_to_sprints.get(str(marker.plan_id or "").strip(), []))
    if len(candidates) != 1:
        return None

    sprint = candidates[0]
    result = {
        "marker_id": marker.marker_id,
        "titel": marker.titel,
        "plan_id": marker.plan_id,
        "current_sprint_tag": marker.sprint_tag,
        "current_spec_tag": marker.spec_tag,
        "new_sprint_tag": marker.sprint_tag or sprint["sprint_tag"],
        "new_spec_tag": marker.spec_tag or "",
        "path": sprint["path"],
        "reason": "plan_id_unique_match",
    }

    title_key = _normalize_text(marker.titel)
    task_hit = sprint["tasks"].get(title_key)
    if task_hit and task_hit.get("spec_tag"):
        result["new_spec_tag"] = marker.spec_tag or task_hit["spec_tag"]
        result["reason"] = "plan_id_plus_task_match"
        return result

    matching_specs = [spec for spec in sprint["specs"] if spec["normalized_title"] == title_key]
    if len(matching_specs) == 1:
        result["new_spec_tag"] = marker.spec_tag or matching_specs[0]["spec_tag"]
        result["reason"] = "plan_id_plus_spec_title_match"
        return result

    return result


def check_handoff_markers(handoff_path, markdown_results=None):
    if not handoff_path or not os.path.exists(handoff_path):
        return []
    plan_to_sprints = build_marker_mapping_index(markdown_results or [])
    missing = []
    for marker in parse_markers(handoff_path):
        if marker.sprint_tag:
            continue
        mapped = _select_marker_mapping(marker, plan_to_sprints)
        issue = {
            "marker_id": marker.marker_id,
            "titel": marker.titel,
            "plan_id": marker.plan_id,
            "sprint_tag": marker.sprint_tag,
            "spec_tag": marker.spec_tag,
        }
        if mapped:
            issue["suggested_sprint_tag"] = mapped["new_sprint_tag"]
            issue["suggested_spec_tag"] = mapped["new_spec_tag"]
            issue["reason"] = mapped["reason"]
            issue["path"] = mapped["path"]
        missing.append(issue)
    return missing


def apply_handoff_marker_backfill(handoff_path, markdown_results):
    if not handoff_path or not os.path.exists(handoff_path):
        return []

    plan_to_sprints = build_marker_mapping_index(markdown_results or [])
    changes = []
    for marker in parse_markers(handoff_path):
        mapped = _select_marker_mapping(marker, plan_to_sprints)
        if not mapped:
            continue

        changed = False
        if not marker.sprint_tag and mapped["new_sprint_tag"]:
            marker.sprint_tag = mapped["new_sprint_tag"]
            changed = True
        if not marker.spec_tag and mapped["new_spec_tag"]:
            marker.spec_tag = mapped["new_spec_tag"]
            changed = True
        if not changed:
            continue

        _write_marker(handoff_path, marker)
        changes.append({
            "marker_id": marker.marker_id,
            "titel": marker.titel,
            "plan_id": marker.plan_id,
            "sprint_tag": marker.sprint_tag,
            "spec_tag": marker.spec_tag,
            "reason": mapped["reason"],
            "path": mapped["path"],
        })

    return changes


def run_check(scan_root, handoff_path=None):
    results = []
    for path in iter_markdown_files(scan_root):
        scanned = scan_markdown_file(path)
        classification = scanned["classification"]["classification"]
        if classification == "technical_documentation":
            continue
        results.append(scanned)

    markdown_results = [item for item in results if item["updates"]]
    marker_issues = check_handoff_markers(handoff_path, results)
    return markdown_results, marker_issues


def run_apply(scan_root, handoff_path=None):
    changed = []
    scanned_results = []
    for path in iter_markdown_files(scan_root):
        scanned = scan_markdown_file(path)
        classification = scanned["classification"]["classification"]
        if classification == "technical_documentation":
            continue
        scanned_results.append(scanned)

    pending = [item for item in scanned_results if item["updates"]]
    for item in pending:
        original_updates = list(item["updates"])
        updated_content = apply_tag_update_plan(item["content"], item["updates"])
        if updated_content == item["content"]:
            continue
        with open(item["path"], "w", encoding=item["encoding"]) as f:
            f.write(updated_content)
        item["content"] = updated_content
        item["structure"] = scan_markdown_structure(updated_content, item["path"])
        item["updates"] = []
        changed.append({
            "path": item["path"],
            "updates": original_updates,
        })

    marker_changes = apply_handoff_marker_backfill(handoff_path, scanned_results)
    marker_issues = check_handoff_markers(handoff_path, scanned_results)
    return changed, marker_changes, marker_issues


def print_report(mode, scan_root, markdown_results, marker_issues, marker_changes=None):
    sprint_tags_added = sum(1 for item in markdown_results for update in item["updates"] if update["kind"] == "sprint")
    spec_tags_added = sum(1 for item in markdown_results for update in item["updates"] if update["kind"] == "spec")
    marker_changes = marker_changes or []

    print(f"Mode: {mode}")
    print(f"Scan root: {scan_root}")
    print(f"Markdown files with pending/applied updates: {len(markdown_results)}")
    print(f"Missing sprint tags: {sprint_tags_added}")
    print(f"Missing spec tags: {spec_tags_added}")
    print(f"Markers updated: {len(marker_changes)}")
    print(f"Markers without complete tag mapping: {len(marker_issues)}")

    if markdown_results:
        print("\nMarkdown updates:")
        for item in markdown_results:
            print(f"- {item['path']}")
            for update in item["updates"]:
                print(f"  line {update['line_number']}: add {update['tag']} to {update['kind']} '{update['title']}'")

    if marker_issues:
        print("\nMarker issues:")
        for item in marker_issues:
            print(
                f"- {item['marker_id']} | plan_id={item['plan_id']} | "
                f"sprint_tag={item['sprint_tag'] or '-'} | spec_tag={item['spec_tag'] or '-'} | "
                f"{item['titel']}"
            )
            if item.get("suggested_sprint_tag") or item.get("suggested_spec_tag"):
                print(
                    f"  suggested sprint_tag={item.get('suggested_sprint_tag') or '-'} | "
                    f"suggested spec_tag={item.get('suggested_spec_tag') or '-'} | "
                    f"reason={item.get('reason') or '-'}"
                )

    if marker_changes:
        print("\nMarker updates:")
        for item in marker_changes:
            print(
                f"- {item['marker_id']} | sprint_tag={item['sprint_tag'] or '-'} | "
                f"spec_tag={item['spec_tag'] or '-'} | reason={item['reason']}"
            )


def build_parser():
    parser = argparse.ArgumentParser(description="Markdown Tag Migration fuer Sprint PX")
    parser.add_argument("--check", action="store_true", help="Nur pruefen, nichts schreiben")
    parser.add_argument("--apply", action="store_true", help="Fehlende Tags direkt schreiben")
    parser.add_argument("--project", help="Projektname oder Pfad")
    parser.add_argument("--handoff", help="Explizite handoff.md fuer Marker-Check")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.check == args.apply:
        parser.error("Genau einer von --check oder --apply ist erforderlich")

    scan_root = resolve_scan_root(args.project)
    handoff_path = os.path.abspath(args.handoff) if args.handoff else None

    if args.check:
        markdown_results, marker_issues = run_check(scan_root, handoff_path=handoff_path)
        print_report("check", scan_root, markdown_results, marker_issues)
        return 0

    markdown_results, marker_changes, marker_issues = run_apply(scan_root, handoff_path=handoff_path)
    print_report("apply", scan_root, markdown_results, marker_issues, marker_changes=marker_changes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
