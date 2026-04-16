#!/usr/bin/env python3
"""Plan-Tag-Migrator: schreibt fehlende #sprint-* / #spec-* Tags in
discoverte Plan-Dateien.

Modi:
  --preview             Liste und Diff-Statistik, kein Write
  --apply-file PATH     Genau eine Datei, mit Backup
  --apply-all           Alle zulaessigen Dateien, mit Backup pro Datei

Schutz-Liste (werden NIE geschrieben):
  handoff.md, next-session.md, next-session-archiv.md,
  CLAUDE.md, AGENTS.md, GEMINI.md

Backup-Verzeichnis:
  <projekt>/.plan_tag_migration_backups/<timestamp>/
  Original wird vor Write dorthin kopiert, Mapping in manifest.json.

Idempotent: existierende Tags werden nicht dupliziert.
Commits: NICHT automatisch (gitignored sprints/*.md wuerden fehlschlagen).
         User macht git add/commit bewusst fuer tracked files.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.markdown_routine_service import (  # noqa: E402
    apply_tag_update_plan,
    build_tag_update_plan,
    read_markdown_with_fallback,
)
from services.plan_discovery_service import discover_plans  # noqa: E402


PROTECTED_FILENAMES = {
    "handoff.md",
    "next-session.md",
    "next-session-archiv.md",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
}

BACKUP_ROOT = os.path.join(ROOT_DIR, ".plan_tag_migration_backups")


def is_protected(filename: str) -> bool:
    return os.path.basename(filename) in PROTECTED_FILENAMES


def compute_updates(content: str) -> list[dict]:
    """Gibt Liste der geplanten Tag-Inserts zurueck (leer = nichts zu tun)."""
    return build_tag_update_plan(content)


def collect_candidates() -> list[dict]:
    """Liefert alle nicht-exkludierten, nicht-geschuetzten Discovery-Entries
    mit mindestens einem fehlenden Tag."""
    entries = discover_plans()
    candidates = []
    for entry in entries:
        if entry.get("excluded_by"):
            continue
        if is_protected(entry["filename"]):
            continue
        updates = compute_updates(entry["content"])
        if not updates:
            continue
        entry_with_updates = dict(entry)
        entry_with_updates["updates"] = updates
        candidates.append(entry_with_updates)
    return candidates


def count_updates(updates: list[dict]) -> tuple[int, int]:
    sprint_count = sum(1 for u in updates if u["kind"] == "sprint")
    spec_count = sum(1 for u in updates if u["kind"] == "spec")
    return sprint_count, spec_count


def print_preview(candidates: list[dict], protected_hits: list[dict]) -> None:
    by_project: dict[str, list[dict]] = {}
    for entry in candidates:
        key = entry.get("project_name") or "(global)"
        by_project.setdefault(key, []).append(entry)

    total_sprint = 0
    total_spec = 0
    for project in sorted(by_project.keys()):
        entries = sorted(by_project[project], key=lambda e: e["source_path"])
        print(f"\n[{project}]  ({len(entries)} Datei(en))")
        for entry in entries:
            sprint_count, spec_count = count_updates(entry["updates"])
            total_sprint += sprint_count
            total_spec += spec_count
            rel = entry["source_path"]
            if entry.get("project_name"):
                project_root = f"/mnt/projects/{entry['project_name']}"
                if rel.startswith(project_root):
                    rel = rel[len(project_root) + 1:]
            print(f"  {rel}")
            print(f"    +{sprint_count} sprint, +{spec_count} spec")

    print("\n" + "=" * 60)
    print(f"Total zu migrieren: {len(candidates)} Datei(en), "
          f"+{total_sprint} sprint-tags, +{total_spec} spec-tags")
    if protected_hits:
        print(f"Geschuetzt (skipped): {len(protected_hits)} Datei(en) "
              f"-> {sorted({e['filename'] for e in protected_hits})}")


def make_backup_dir() -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = os.path.join(BACKUP_ROOT, timestamp)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def backup_file(entry: dict, backup_dir: str) -> str:
    source_path = entry["source_path"]
    project = entry.get("project_name") or "_global"
    rel_name = f"{project}__{os.path.basename(source_path)}"
    # Bei Namenskollisionen: Index anhaengen
    target_path = os.path.join(backup_dir, rel_name)
    idx = 1
    while os.path.exists(target_path):
        base, ext = os.path.splitext(rel_name)
        target_path = os.path.join(backup_dir, f"{base}.{idx}{ext}")
        idx += 1
    shutil.copy2(source_path, target_path)
    return target_path


def apply_one(entry: dict, backup_dir: str) -> dict:
    source_path = entry["source_path"]
    loaded = read_markdown_with_fallback(source_path)
    updates = build_tag_update_plan(loaded["content"])
    if not updates:
        return {"path": source_path, "status": "noop", "reason": "no_updates"}

    backup_path = backup_file(entry, backup_dir)
    new_content = apply_tag_update_plan(loaded["content"], updates)
    if new_content == loaded["content"]:
        return {"path": source_path, "status": "noop", "reason": "idempotent"}

    with open(source_path, "w", encoding=loaded["encoding"]) as f:
        f.write(new_content)

    sprint_count, spec_count = count_updates(updates)
    return {
        "path": source_path,
        "status": "applied",
        "backup": backup_path,
        "encoding": loaded["encoding"],
        "sprint_added": sprint_count,
        "spec_added": spec_count,
    }


def write_manifest(backup_dir: str, records: list[dict]) -> str:
    manifest_path = os.path.join(backup_dir, "manifest.json")
    payload = {
        "timestamp": datetime.now().isoformat(),
        "backup_dir": backup_dir,
        "records": records,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return manifest_path


def run_preview() -> int:
    candidates = collect_candidates()
    entries = discover_plans()
    protected_hits = [
        e for e in entries
        if is_protected(e["filename"])
        and not e.get("excluded_by")
        and compute_updates(e["content"])
    ]
    if not candidates:
        print("Keine Datei zu migrieren.")
        if protected_hits:
            print(f"\nGeschuetzt (mit pending Tags, skipped): "
                  f"{len(protected_hits)} Datei(en) "
                  f"-> {sorted({e['filename'] for e in protected_hits})}")
        return 0
    print_preview(candidates, protected_hits)
    return 0


def run_apply_file(target_path: str) -> int:
    abs_target = os.path.abspath(target_path)
    if is_protected(abs_target):
        print(f"FEHLER: {os.path.basename(abs_target)} steht auf der "
              f"Schutz-Liste und wird nicht migriert.", file=sys.stderr)
        return 2

    candidates = collect_candidates()
    entry = next(
        (e for e in candidates if os.path.realpath(e["source_path"]) == os.path.realpath(abs_target)),
        None,
    )
    if entry is None:
        print(f"FEHLER: {abs_target} ist keine discovered Plan-Datei oder "
              f"hat keine pending Tag-Updates.", file=sys.stderr)
        return 3

    backup_dir = make_backup_dir()
    record = apply_one(entry, backup_dir)
    write_manifest(backup_dir, [record])
    print(f"Status: {record['status']}")
    if record.get("status") == "applied":
        print(f"  +{record['sprint_added']} sprint, +{record['spec_added']} spec")
        print(f"  Backup: {record['backup']}")
    return 0


def run_apply_all() -> int:
    candidates = collect_candidates()
    if not candidates:
        print("Keine Datei zu migrieren.")
        return 0

    print(f"Migriere {len(candidates)} Datei(en) ...")
    backup_dir = make_backup_dir()
    records = []
    applied = 0
    skipped = 0
    for entry in candidates:
        try:
            record = apply_one(entry, backup_dir)
        except Exception as exc:  # noqa: BLE001
            record = {
                "path": entry["source_path"],
                "status": "error",
                "error": str(exc),
            }
        records.append(record)
        status = record.get("status")
        if status == "applied":
            applied += 1
        else:
            skipped += 1
        print(f"  [{status}] {record['path']}")

    manifest_path = write_manifest(backup_dir, records)
    print("\n" + "=" * 60)
    print(f"Applied: {applied}, Skipped/Error: {skipped}")
    print(f"Backup-Verzeichnis: {backup_dir}")
    print(f"Manifest: {manifest_path}")
    print("\nRollback: originale Datei aus Backup zurueckkopieren, "
          "oder via git checkout (fuer tracked files).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan-Tag-Migrator (Multi-Source, mit Schutz-Liste)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preview", action="store_true",
                       help="Zeigt Kandidaten und Tag-Zahlen, kein Write")
    group.add_argument("--apply-file", metavar="PATH",
                       help="Migriert genau eine Datei")
    group.add_argument("--apply-all", action="store_true",
                       help="Migriert alle zulaessigen Kandidaten")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.preview:
        return run_preview()
    if args.apply_file:
        return run_apply_file(args.apply_file)
    if args.apply_all:
        return run_apply_all()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
