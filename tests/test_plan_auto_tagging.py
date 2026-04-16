"""
Tests fuer Auto-Tagging in plans_sync_service (Issue #28, Option A).

Verifiziert Byte-Integritaet: Auto-Tagger darf ausschliesslich Tag-Appends
an Heading-Zeilen produzieren, keine Content-Manipulation.
"""
import os
import re
import tempfile
import unittest
from unittest import mock


class TestPlanAutoTagging(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="plan_auto_tag_test_")
        self.backup_dir = os.path.join(self.tmpdir, "backups")

    def _write(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _plan_record(self, source_path, source_kind="project_sprints"):
        """Minimaler Plan-Record wie scan_all_plans() ihn liefert."""
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "source_path": source_path,
            "source_kind": source_kind,
            "filename": os.path.basename(source_path),
            "content": content,
            "mtime": os.path.getmtime(source_path),
        }

    def test_auto_tags_sprint_and_spec_only_on_heading_lines(self):
        from services.plans_sync_service import _auto_tag_plan_file

        content = (
            "### Sprint P7 - Analyse\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports\n"
            "- Bericht bauen\n"
        )
        path = self._write("sprint-p7.md", content)
        plan = self._plan_record(path)
        original_lines = content.splitlines()

        applied = _auto_tag_plan_file(plan, self.backup_dir)
        self.assertEqual(applied, 2)

        with open(path, "r", encoding="utf-8") as f:
            new_content = f.read()
        new_lines = new_content.splitlines()

        # Invariante: Zeilenanzahl unveraendert
        self.assertEqual(len(original_lines), len(new_lines))

        # Invariante: Nicht-Heading-Zeilen byte-identisch
        HEADING_RE = re.compile(r"^#{1,6}\s+")
        for i, (orig, new) in enumerate(zip(original_lines, new_lines)):
            if HEADING_RE.match(orig):
                continue
            self.assertEqual(orig, new, f"Content-Zeile {i+1} modifiziert")

        # Invariante: Nur Tag-Suffixe an Heading-Zeilen
        for i, (orig, new) in enumerate(zip(original_lines, new_lines)):
            if orig == new:
                continue
            self.assertTrue(HEADING_RE.match(orig), f"Zeile {i+1} ist kein Heading")
            suffix = new[len(orig):]
            self.assertRegex(
                suffix, r"^\s+#(sprint|spec)-[a-z0-9][a-z0-9-]*$",
                f"Zeile {i+1}: unerwarteter Suffix {suffix!r}",
            )

        # Invariante: plan-Record wurde in-place aktualisiert
        self.assertEqual(plan["content"], new_content)

    def test_idempotent_second_run_no_writes(self):
        from services.plans_sync_service import _auto_tag_plan_file

        content = "### Sprint A\n#### Spec 1\ninhalt\n"
        path = self._write("sprint-a.md", content)
        plan1 = self._plan_record(path)

        first = _auto_tag_plan_file(plan1, self.backup_dir)
        self.assertGreater(first, 0)

        plan2 = self._plan_record(path)
        second = _auto_tag_plan_file(plan2, self.backup_dir)
        self.assertEqual(second, 0, "Zweiter Lauf sollte idempotent sein")

    def test_protected_filename_not_tagged(self):
        from services.plans_sync_service import _auto_tag_plan_file

        content = "### Sprint X\ninhalt\n"
        path = self._write("CLAUDE.md", content)
        plan = self._plan_record(path)

        applied = _auto_tag_plan_file(plan, self.backup_dir)
        self.assertEqual(applied, 0)

        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content, "CLAUDE.md darf nicht modifiziert werden")

    def test_claude_plans_source_blacklisted(self):
        from services.plans_sync_service import _auto_tag_plan_file

        content = "### Sprint Y\ninhalt\n"
        path = self._write("project-plan.md", content)
        plan = self._plan_record(path, source_kind="claude_plans")

        applied = _auto_tag_plan_file(plan, self.backup_dir)
        self.assertEqual(applied, 0, "claude_plans-Quelle darf nicht getaggt werden")

    def test_mtime_drift_skips_file(self):
        from services.plans_sync_service import _auto_tag_plan_file

        content = "### Sprint Z\ninhalt\n"
        path = self._write("sprint-z.md", content)
        plan = self._plan_record(path)
        # Kuenstliche Drift vortaeuschen: discovery-mtime viel aelter als live
        plan["mtime"] = plan["mtime"] - 100.0

        applied = _auto_tag_plan_file(plan, self.backup_dir)
        self.assertEqual(applied, 0, "mtime-Drift sollte Skip ausloesen")

    def test_backup_created_before_overwrite(self):
        from services.plans_sync_service import _auto_tag_plan_file

        content = "### Sprint B\ninhalt\n"
        path = self._write("sprint-b.md", content)
        plan = self._plan_record(path)

        applied = _auto_tag_plan_file(plan, self.backup_dir)
        self.assertGreater(applied, 0)

        # Backup-Verzeichnis muss existieren und die Original-Datei enthalten
        self.assertTrue(os.path.isdir(self.backup_dir))
        backups = os.listdir(self.backup_dir)
        self.assertEqual(len(backups), 1)
        with open(os.path.join(self.backup_dir, backups[0]), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content, "Backup muss Original enthalten")

    def test_opt_out_via_config_flag(self):
        from services import plans_sync_service

        content = "### Sprint C\ninhalt\n"
        path = self._write("sprint-c.md", content)
        plan = self._plan_record(path)

        with mock.patch("config.PLAN_AUTO_TAG_ENABLED", False):
            metrics = plans_sync_service._auto_tag_all_plans([plan])

        self.assertTrue(metrics.get("disabled"))
        self.assertEqual(metrics["tagged"], 0)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content, "Bei disabled keine Modifikation")


if __name__ == "__main__":
    unittest.main()
