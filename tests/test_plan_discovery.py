"""
Test-Stubs fuer Plan-Discovery (Sprint sprint-plan-discovery, Commit 2+3).

Option A verbindlich: die bestehenden Klassen sind Stubs (pytest.skip). Der
volle pytest-Setup (fs-Fixture, DB-Fake, Metrik-Assertions) wird im
Folge-Sprint `sprint-test-infrastructure.md` nachgezogen.

Ausnahme: `TestRecursiveScannerReal` am Ende dieser Datei enthaelt einen
echten Test fuer den Full-Project-Recursive-Scanner (ohne DB).

Abdeckungsziele, die der Folge-Sprint einloesen muss:
  - Heuristik: Filename-Regex, Plan-Tag, Negativ-Liste, ##-Headline-Gate
  - Pfad-Ableitung: project_name aus /mnt/projects/<name>/... inkl. Symlink
    via realpath
  - Exclusion-Matching: globale vs. projekt-spezifische Patterns, fnmatch
  - Frontmatter-Gate: draft/archived -> excluded aus Ergebnis
  - 4-stufige Upsert-Logik (plans_sync_service):
      1. source_path-Match -> UPDATE (+ Draft-Re-Eval fuer claude_plans)
      2. filename+project_name -> Migration; Kollisions-Guard
      3. content_hash+project_name -> Migration (Filename-Drift)
      4. Kein Match -> INSERT mit korrektem auto_status
  - Schutz-Mechanismen: Modul-Lock (plan_scan_lock_skipped),
    60-s-Cooldown, 15-min-Circuit-Breaker (duration_ms > 5000),
    Bulk-Tx-Rollback, Savepoint-Isolation pro Upsert
  - Notification-Suppression: is_scanning() True waehrend Scan
  - Preview-Cache: 10 s TTL, gleicher Aufruf liefert gecachtes Ergebnis
  - Metric-Log-Zeile: WARNING-Level, Format
    "plan_scan metrics inserted=%d updated=%d ..."
"""
import os

import pytest

_STUB_SKIP = pytest.mark.skip(
    reason="Stubs only — voller Testaufbau in sprint-test-infrastructure.md"
)


# ---------------------------------------------------------------------------
# Discovery-Schicht (services/plan_discovery_service.py)
# ---------------------------------------------------------------------------

class TestHeuristik:
    pytestmark = _STUB_SKIP

    def test_plan_filename_regex_matches_sprint_spec_plan_roadmap_adr(self):
        pass

    def test_negative_filename_overrides_plan_match(self):
        # -retro, -notes, -log, -changelog, -template, README, CHANGELOG, HISTORY
        pass

    def test_plan_tag_without_filename_match_still_counts(self):
        # Datei heisst foo.md, enthaelt #sprint-xyz -> plan
        pass

    def test_heading_gate_rejects_files_without_double_hash(self):
        pass

    def test_blacklist_dirs_never_descended(self):
        # node_modules, .venv, archive, __pycache__, ...
        pass

    def test_max_depth_3_and_max_size_1mb(self):
        pass


class TestProjektAbleitung:
    pytestmark = _STUB_SKIP

    def test_project_name_from_path(self):
        pass

    def test_symlink_realpath_reassigns_project_name(self):
        # Symlink in Projekt A zeigt auf Datei in Projekt B -> project=B
        pass

    def test_seen_set_deduplicates_via_realpath(self):
        pass


class TestFrontmatter:
    pytestmark = _STUB_SKIP

    def test_draft_true_excludes_file(self):
        pass

    def test_archived_true_excludes_file(self):
        pass

    def test_malformed_frontmatter_does_not_crash(self):
        pass


class TestExclusions:
    pytestmark = _STUB_SKIP

    def test_global_exclusion_applies_to_all_projects(self):
        # project_name IS NULL in plan_scan_exclusions
        pass

    def test_project_specific_exclusion_only_applies_to_that_project(self):
        pass

    def test_excluded_entry_still_appears_in_preview_with_excluded_by(self):
        pass

    def test_fnmatch_pattern_semantics(self):
        # docs/archive/*.md, sprints/old-*.md, etc.
        pass


class TestPreviewCache:
    pytestmark = _STUB_SKIP

    def test_use_cache_true_returns_within_ttl(self):
        pass

    def test_cache_expires_after_ttl(self):
        pass


# ---------------------------------------------------------------------------
# Sync-Orchestrator (services/plans_sync_service.py)
# ---------------------------------------------------------------------------

class TestUpsertStep1:
    pytestmark = _STUB_SKIP

    def test_source_path_match_updates_content_fields(self):
        pass

    def test_unchanged_hash_does_not_update(self):
        # stats["unchanged"] += 1, keine DB-Writes
        pass

    def test_draft_re_evaluation_only_for_claude_plans(self):
        # Nur source_kind='claude_plans' triggert detect_status_from_sessions
        pass

    def test_legacy_repair_fills_null_project_name(self):
        pass


class TestUpsertStep2:
    pytestmark = _STUB_SKIP

    def test_filename_project_match_migrates_alt_row(self):
        # source_path IS NULL + filename+project_name matcht -> Migration
        pass

    def test_filename_collision_with_mismatched_project_skips(self):
        # Kollisions-Guard: kein Auto-Umhaengen
        pass


class TestUpsertStep3:
    pytestmark = _STUB_SKIP

    def test_content_hash_migration_requires_project_match(self):
        pass

    def test_identical_content_in_different_projects_does_not_migrate(self):
        pass


class TestUpsertStep4:
    pytestmark = _STUB_SKIP

    def test_insert_with_neutral_defaults_for_multi_source(self):
        # source_kind != claude_plans -> status='unknown', session_uuid=NULL
        pass

    def test_insert_with_auto_status_for_claude_plans(self):
        # Legacy-Pfad: detect_status_from_sessions
        pass

    def test_unique_filename_collision_does_not_crash_sync(self):
        # Insert schlaegt fehl -> stats["skipped"] += 1, weiter
        pass


class TestSchutzMechanismen:
    pytestmark = _STUB_SKIP

    def test_module_lock_prevents_parallel_scan(self):
        # zweiter Aufruf -> skipped_reason='lock'
        pass

    def test_cooldown_60s_blocks_second_call(self):
        pass

    def test_force_true_bypasses_cooldown(self):
        pass

    def test_circuit_breaker_opens_on_slow_scan(self):
        # duration_ms > 5000 -> _NEXT_ALLOWED_AT += 900 s
        pass

    def test_savepoint_isolates_single_upsert_failure(self):
        # Eine fehlerhafte Insert-Row kippt nicht die Bulk-Tx
        pass

    def test_is_scanning_flag_set_during_scan(self):
        # Thread-local, fuer Notification-Suppression
        pass


class TestMetrikLog:
    pytestmark = _STUB_SKIP

    def test_metric_line_format_and_warning_level(self):
        # "plan_scan metrics inserted=%d updated=%d migrated=%d "
        # "unchanged=%d skipped=%d total=%d duration_ms=%d"
        pass


# ---------------------------------------------------------------------------
# Echter Test fuer den Full-Project-Recursive-Scanner (kein Stub).
# ---------------------------------------------------------------------------

class TestRecursiveScannerReal:
    """Einzelner echter Test: eine planartige .md-Datei ausserhalb der
    Standardpfade wird vom rekursiven Scanner gefunden UND durch die
    Discovery-Pipeline bis zu einem import-reifen Record verarbeitet
    (Heuristik + Frontmatter + Content-Hash). Der anschliessende SQL-INSERT
    wird hier nicht ausgefuehrt, weil er eine echte PostgreSQL-Verbindung
    braucht."""

    def test_md_ausserhalb_standardpfade_wird_gefunden_und_fuer_import_vorbereitet(
        self, tmp_path, monkeypatch,
    ):
        from services import plan_discovery_service as pds

        project = "test_project_alpha"
        target_dir = tmp_path / project / "some" / "subdir"
        target_dir.mkdir(parents=True)
        plan_file = target_dir / "sprint-feature-roadmap.md"
        plan_file.write_text(
            "# Sprint Feature Roadmap\n\n## Context\n\nPlan body\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(pds, "PROJECTS_DIR", str(tmp_path))

        # exclusions=[] umgeht load_exclusions() und damit jeden DB-Zugriff.
        # use_cache=False erzwingt frischen Walk statt Preview-Cache.
        records = pds.discover_plans(exclusions=[], use_cache=False)

        expected_real = os.path.realpath(str(plan_file))
        matches = [r for r in records if r["source_path"] == expected_real]
        assert matches, (
            "Plan-Datei wurde nicht als import-reifer Record erzeugt. "
            f"Discovered: {[r.get('source_path') for r in records]}"
        )
        rec = matches[0]
        assert rec["source_kind"] == "project_recursive"
        assert rec["project_name"] == project
        assert rec["filename"] == "sprint-feature-roadmap.md"
        assert rec["content_hash"], "content_hash fehlt — Upsert-Dedup greift nicht"
        assert not rec.get("excluded_by")
        assert "Sprint Feature Roadmap" in (rec.get("content") or "")
