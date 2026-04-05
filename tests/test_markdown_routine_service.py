from services.markdown_routine_service import (
    apply_tag_update_plan,
    build_tag_update_plan,
    classify_markdown_content,
    compute_content_hash,
    detect_semantic_split_points,
    extract_markdown_tags,
    read_markdown_with_fallback,
    scan_markdown_structure,
    suggest_tag_from_title,
)


class TestMarkdownRoutineService:
    def test_read_markdown_with_fallback_reads_latin1_file(self, tmp_path):
        target = tmp_path / "latin1.md"
        target.write_bytes("### Sprint Umlaute\n\nGr\xfc\xdfe".encode("cp1252"))

        result = read_markdown_with_fallback(str(target))

        assert result["encoding"] == "latin-1" or result["encoding"] == "cp1252"
        assert "Gr" in result["content"]

    def test_compute_content_hash_ignores_hash_markers(self):
        text_a = (
            "<!-- HASH: abc -->\n"
            "<!-- File-Hash: def -->\n"
            "## Sprint\n\n"
            "- Aufgabe A\n"
        )
        text_b = (
            "<!-- HASH: xyz -->\n"
            "<!-- Generated: 2026-04-04 -->\n"
            "## Sprint\n\n"
            "- Aufgabe A\n"
        )

        assert compute_content_hash(text_a) == compute_content_hash(text_b)

    def test_extract_markdown_tags_reads_heading_and_meta_lines(self):
        content = (
            "### Sprint P3 - Prompt Chain #sprint-p3\n\n"
            "#### Usage Reports\n"
            "Spec-ID: #spec-usage-reports\n"
        )

        tags = extract_markdown_tags(content)

        assert [tag["tag"] for tag in tags] == ["#sprint-p3", "#spec-usage-reports"]
        assert tags[0]["source"] == "heading"
        assert tags[1]["source"] == "meta"

    def test_scan_markdown_structure_extracts_sprints_specs_and_tasks(self):
        content = (
            "### Sprint P3 - Prompt Chain #sprint-p3\n"
            "Plan-ID: sprint-p3\n"
            "Kurzbeschreibung Sprint\n\n"
            "- Direktaufgabe A\n\n"
            "#### Usage Reports #spec-usage-reports\n"
            "Spec Beschreibung\n"
            "- Task 1\n"
            "- Task 2\n"
        )

        structure = scan_markdown_structure(content, "demo.md")

        assert structure["classification"]["classification"] == "sprint_like"
        assert len(structure["sprints"]) == 1
        sprint = structure["sprints"][0]
        assert sprint["sprint_tag"] == "#sprint-p3"
        assert sprint["plan_id"] == "sprint-p3"
        assert sprint["tasks"] == ["Direktaufgabe A"]
        assert len(sprint["specs"]) == 1
        spec = sprint["specs"][0]
        assert spec["spec_tag"] == "#spec-usage-reports"
        assert spec["tasks"] == ["Task 1", "Task 2"]

    def test_classify_markdown_content_detects_technical_documentation(self):
        result = classify_markdown_content(
            "README.md",
            "## Installation\nnpm run dev\n## API\n",
        )

        assert result["classification"] == "technical_documentation"

    def test_detect_semantic_split_points_returns_headings_and_legacy_questions(self):
        content = (
            "# Titel\n"
            "## Abschnitt\n"
            "### **F1.1: Frage**\n"
            "---\n"
        )

        points = detect_semantic_split_points(content)

        assert any(point["reason"] == "heading" for point in points)
        assert any(point["reason"] == "legacy_question" for point in points)
        assert any(point["reason"] == "separator" for point in points)

    def test_suggest_tag_from_title_builds_stable_slug(self):
        assert suggest_tag_from_title("Usage Reports Seite", "spec") == "#spec-usage-reports-seite"

    def test_build_tag_update_plan_finds_missing_sprint_and_spec_tags(self):
        content = (
            "### Sprint P7 - Analyse\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports\n"
            "- Bericht bauen\n"
        )

        updates = build_tag_update_plan(content)

        assert len(updates) == 2
        assert updates[0]["kind"] == "sprint"
        assert updates[0]["tag"] == "#sprint-sprint-p7-analyse"
        assert updates[1]["kind"] == "spec"
        assert updates[1]["tag"] == "#spec-usage-reports"

    def test_apply_tag_update_plan_writes_tags_idempotently(self):
        content = (
            "### Sprint P7 - Analyse\n"
            "Plan-ID: sprint-p7\n\n"
            "#### Usage Reports\n"
            "- Bericht bauen\n"
        )

        updated = apply_tag_update_plan(content, build_tag_update_plan(content))
        second = apply_tag_update_plan(updated, build_tag_update_plan(updated))

        assert "#sprint-sprint-p7-analyse" in updated
        assert "#spec-usage-reports" in updated
        assert updated == second
