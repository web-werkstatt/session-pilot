from services.copilot_marker_service import Marker
from services.plan_structure_service import (
    derive_tagged_plan_sections,
    get_project_planning_hierarchy,
    resolve_marker_structure_refs,
)


class TestPlanStructureService:
    def test_derive_tagged_plan_sections_maps_markers_by_sprint_and_spec_tags(self):
        content = (
            "### Sprint P3 - Prompt Chain #sprint-p3\n"
            "Plan-ID: sprint-p3\n"
            "Kurzbeschreibung\n"
            "- Direktaufgabe\n\n"
            "#### Usage Reports #spec-usage-reports\n"
            "Reports bauen\n"
            "- Report Task\n"
        )
        markers = [
            Marker(
                marker_id="m1",
                titel="Direktaufgabe",
                plan_id="legacy-plan",
                status="todo",
                ziel="Ziel",
                naechster_schritt="Schritt",
                prompt="Prompt",
                checks=["Check"],
                sprint_tag="#sprint-p3",
            ),
            Marker(
                marker_id="m2",
                titel="Report Task",
                plan_id="legacy-plan",
                status="todo",
                ziel="Ziel",
                naechster_schritt="Schritt",
                prompt="Prompt",
                checks=["Check"],
                sprint_tag="#sprint-p3",
                spec_tag="#spec-usage-reports",
            ),
        ]

        sections = derive_tagged_plan_sections(content, markers, source_path="plan.md")

        assert len(sections) == 1
        sprint = sections[0]
        assert sprint["sprint_tag"] == "#sprint-p3"
        assert len(sprint["direct_markers"]) == 1
        assert sprint["direct_markers"][0]["marker_id"] == "m1"
        assert len(sprint["specs"]) == 1
        assert sprint["specs"][0]["spec_tag"] == "#spec-usage-reports"
        assert len(sprint["specs"][0]["markers"]) == 1
        assert sprint["specs"][0]["markers"][0]["marker_id"] == "m2"

    def test_derive_tagged_plan_sections_falls_back_to_plan_id_when_marker_has_no_sprint_tag(self):
        content = (
            "### Sprint P7 - Analyse #sprint-p7\n"
            "Plan-ID: sprint-p7\n"
            "- Aufgabe A\n"
        )
        markers = [
            Marker(
                marker_id="m1",
                titel="Aufgabe A",
                plan_id="sprint-p7",
                status="todo",
                ziel="Ziel",
                naechster_schritt="Schritt",
                prompt="Prompt",
                checks=["Check"],
            ),
        ]

        sections = derive_tagged_plan_sections(content, markers, source_path="plan.md")

        assert len(sections) == 1
        assert len(sections[0]["markers"]) == 1
        assert sections[0]["markers"][0]["marker_id"] == "m1"

    def test_resolve_marker_structure_refs_prefers_spec_tag_anchor(self, monkeypatch):
        rows = {
            ("SELECT * FROM sprint_plans WHERE project_id = %s AND plan_id = %s", ("demo", "sprint-p7")): {
                "id": 11,
                "plan_id": "sprint-p7",
            },
            (
                """SELECT * FROM specs
               WHERE sprint_plan_id = %s AND LOWER(anchor) = LOWER(%s)
               ORDER BY id ASC LIMIT 1""",
                (11, "spec-usage-reports"),
            ): {
                "id": 21,
                "anchor": "spec-usage-reports",
                "title": "Usage Reports",
            },
        }

        def fake_execute(sql, params=None, fetch=False, fetchone=False):
            return rows.get((sql, params))

        monkeypatch.setattr("services.plan_structure_service.ensure_plan_structure_schema", lambda: None)
        monkeypatch.setattr("services.plan_structure_service.execute", fake_execute)

        sprint_plan_id, spec_id = resolve_marker_structure_refs(
            "demo",
            "sprint-p7",
            spec_title="Usage Reports",
            spec_tag="#spec-usage-reports",
        )

        assert sprint_plan_id == 11
        assert spec_id == 21

    def test_get_project_planning_hierarchy_groups_plan_with_tagged_sprints(self, monkeypatch, tmp_path):
        handoff_path = tmp_path / "handoff.md"
        handoff_path.write_text(
            "<!-- MARKER:m1\n"
            "{\n"
            '  "marker_id": "m1",\n'
            '  "titel": "Report Task",\n'
            '  "plan_id": "legacy-plan",\n'
            '  "status": "todo",\n'
            '  "ziel": "Ziel",\n'
            '  "naechster_schritt": "Schritt",\n'
            '  "prompt": "Prompt",\n'
            '  "checks": ["Check"],\n'
            '  "sprint_tag": "#sprint-p3",\n'
            '  "spec_tag": "#spec-usage-reports"\n'
            "}\n"
            "-->\n\n"
            "## Report Task · todo\n\n"
            "**Ziel:** Ziel\n"
            "**Naechster Schritt:** Schritt\n"
            "**Risiko:** -\n"
            "**Execution Score:** -\n"
            "**Execution Comment:** -\n"
            "**Last Execution:** -\n"
            "**Sprint Tag:** #sprint-p3\n"
            "**Spec Tag:** #spec-usage-reports\n\n"
            "**Prompt:**\nPrompt\n\n"
            "**Checks:**\n- Check\n\n---\n",
            encoding="utf-8",
        )

        rows = [{
            "id": 5,
            "title": "Master Plan",
            "project_name": "demo",
            "context_summary": "Summary",
            "content": (
                "### Sprint P3 - Prompt Chain #sprint-p3\n"
                "Plan-ID: sprint-p3\n"
                "Kurzbeschreibung\n"
                "- Direktaufgabe\n\n"
                "#### Usage Reports #spec-usage-reports\n"
                "Reports bauen\n"
                "- Report Task\n"
            ),
            "category": "plan",
            "status": "active",
            "workflow_stage": "spec_ready",
            "current_state": "Ist",
            "target_state": "Soll",
            "next_action": "Weiter",
            "created_at": None,
            "updated_at": None,
        }]

        def fake_execute(sql, params=None, fetch=False, fetchone=False):
            if "FROM project_plans" in sql:
                return rows
            return []

        monkeypatch.setattr("services.plan_structure_service.ensure_plan_structure_schema", lambda: None)
        monkeypatch.setattr("services.plan_structure_service.execute", fake_execute)

        result = get_project_planning_hierarchy("demo", str(handoff_path))

        assert len(result) == 1
        assert result[0]["plan"]["title"] == "Master Plan"
        assert result[0]["stats"]["sprint_count"] == 1
        assert result[0]["sprints"][0]["title"] == "Sprint P3 - Prompt Chain"
        assert result[0]["sprints"][0]["specs"][0]["markers"][0]["marker_id"] == "m1"
        assert result[0]["sprints"][0]["specs"][0]["markers"][0]["ziel"] == "Ziel"
