from services.copilot_marker_service import Marker, _write_marker, parse_markers
from scripts.markdown_tag_migration import run_apply, run_check


class TestMarkdownTagMigration:
    def test_run_check_reports_missing_tags(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        target = project_dir / "sprint-demo.md"
        target.write_text(
            "### Sprint P7 - Analyse\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports\n"
            "- Bericht bauen\n",
            encoding="utf-8",
        )

        markdown_results, marker_issues = run_check(str(project_dir))

        assert len(markdown_results) == 1
        assert marker_issues == []
        assert len(markdown_results[0]["updates"]) == 2

    def test_run_apply_writes_missing_tags_idempotently(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        target = project_dir / "sprint-demo.md"
        target.write_text(
            "### Sprint P7 - Analyse\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports\n"
            "- Bericht bauen\n",
            encoding="utf-8",
        )

        changed, marker_changes, marker_issues = run_apply(str(project_dir))

        assert len(changed) == 1
        assert marker_changes == []
        assert marker_issues == []
        content = target.read_text(encoding="utf-8")
        assert "#sprint-sprint-p7-analyse" in content
        assert "#spec-usage-reports" in content

        second_run, second_marker_changes, second_marker_issues = run_apply(str(project_dir))
        assert second_run == []
        assert second_marker_changes == []
        assert second_marker_issues == []

    def test_run_check_suggests_marker_backfill_from_unique_plan_and_task_match(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        target = project_dir / "sprint-demo.md"
        target.write_text(
            "### Sprint P7 - Analyse #sprint-p7\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports #spec-usage-reports\n"
            "- Bericht bauen\n",
            encoding="utf-8",
        )
        _write_marker(str(handoff_path), Marker(
            marker_id="m1",
            titel="Bericht bauen",
            plan_id="sprint-p7",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        markdown_results, marker_issues = run_check(str(project_dir), handoff_path=str(handoff_path))

        assert markdown_results == []
        assert len(marker_issues) == 1
        assert marker_issues[0]["suggested_sprint_tag"] == "#sprint-p7"
        assert marker_issues[0]["suggested_spec_tag"] == "#spec-usage-reports"

    def test_run_apply_backfills_marker_tags_idempotently(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir()
        handoff_path = project_dir / "handoff.md"
        target = project_dir / "sprint-demo.md"
        target.write_text(
            "### Sprint P7 - Analyse #sprint-p7\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports #spec-usage-reports\n"
            "- Bericht bauen\n",
            encoding="utf-8",
        )
        _write_marker(str(handoff_path), Marker(
            marker_id="m1",
            titel="Bericht bauen",
            plan_id="sprint-p7",
            status="todo",
            ziel="Ziel",
            naechster_schritt="Schritt",
            prompt="Prompt",
            checks=["Check eins"],
        ))

        changed, marker_changes, marker_issues = run_apply(str(project_dir), handoff_path=str(handoff_path))

        assert changed == []
        assert len(marker_changes) == 1
        assert marker_issues == []
        parsed = parse_markers(str(handoff_path))
        assert parsed[0].sprint_tag == "#sprint-p7"
        assert parsed[0].spec_tag == "#spec-usage-reports"

        second_changed, second_marker_changes, second_marker_issues = run_apply(str(project_dir), handoff_path=str(handoff_path))
        assert second_changed == []
        assert second_marker_changes == []
        assert second_marker_issues == []
