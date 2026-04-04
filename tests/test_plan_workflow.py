"""
Sprint E: Abnahmetests fuer Plan-Workflow Micro-Ebene.
Deckt M1-M8 ab: DB, API, Workflow-Logik, Signale, Copilot-Binding.
"""
import json
import uuid
import pytest
from unittest.mock import patch

from services.plan_workflow_service import (
    get_plan_workflow,
    update_plan_workflow,
    get_project_plan_workflows,
    WORKFLOW_STAGES,
    EXECUTOR_STATUSES,
    REVIEW_STATUSES,
)
from services.project_handoff_service import build_handoff_markdown
from services.db_service import execute, ensure_plan_workflow_schema


@pytest.fixture
def test_plan():
    """Erstellt einen Test-Plan in der DB, rauemt nach dem Test auf."""
    ensure_plan_workflow_schema()
    unique = str(uuid.uuid4())[:8]
    row = execute(
        """INSERT INTO project_plans (filename, title, project_name, status, category)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING id""",
        (f"test-wf-{unique}.md", "[TEST] Workflow Plan", "project_dashboard", "active", "feature"),
        fetchone=True,
    )
    plan_id = row["id"]
    yield plan_id
    # Cleanup: Copilot-Daten und Plan entfernen
    execute("DELETE FROM copilot_messages WHERE thread_id IN (SELECT id FROM copilot_threads WHERE plan_id = %s)", (plan_id,))
    execute("DELETE FROM copilot_threads WHERE plan_id = %s", (plan_id,))
    execute("DELETE FROM project_plans WHERE id = %s", (plan_id,))


# --- M1: DB-Persistenz ---

class TestM1Persistence:
    def test_workflow_columns_exist(self):
        ensure_plan_workflow_schema()
        rows = execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_name = 'project_plans'
               AND column_name IN ('workflow_stage','current_state','target_state',
                   'next_action','latest_executor_status','latest_review_status',
                   'open_items_count','latest_audit_status','latest_quality_score',
                   'governance_status','spec_ref','prompt_ref','last_run_at','plan_type')
               ORDER BY column_name""",
            fetch=True,
        )
        cols = [r["column_name"] for r in rows]
        expected = ["current_state", "governance_status", "last_run_at",
                    "latest_audit_status", "latest_executor_status", "latest_quality_score",
                    "latest_review_status", "next_action", "open_items_count",
                    "plan_type", "prompt_ref", "spec_ref", "target_state", "workflow_stage"]
        assert sorted(cols) == sorted(expected)

    def test_copilot_plan_id_exists(self):
        ensure_plan_workflow_schema()
        rows = execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_name = 'copilot_runs' AND column_name = 'plan_id'""",
            fetch=True,
        )
        assert len(rows) == 1


# --- M2: API ---

class TestM2API:
    def test_get_workflow(self, client, test_plan):
        r = client.get(f"/api/plans/{test_plan}/workflow")
        assert r.status_code == 200
        d = r.get_json()
        assert d["plan_id"] == test_plan
        assert d["workflow_stage"] == "idea"
        assert "current_state" in d
        assert "target_state" in d
        assert "next_action" in d

    def test_get_workflow_404(self, client):
        r = client.get("/api/plans/999999/workflow")
        assert r.status_code == 404

    def test_put_workflow(self, client, test_plan):
        r = client.put(f"/api/plans/{test_plan}/workflow",
                       data=json.dumps({
                           "workflow_stage": "executing",
                           "current_state": "Code wird geschrieben",
                           "target_state": "Feature fertig + getestet",
                           "next_action": "Tests ergaenzen",
                       }),
                       content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["workflow_stage"] == "executing"
        assert d["current_state"] == "Code wird geschrieben"
        assert d["target_state"] == "Feature fertig + getestet"
        assert d["next_action"] == "Tests ergaenzen"

    def test_put_workflow_invalid_stage(self, client, test_plan):
        r = client.put(f"/api/plans/{test_plan}/workflow",
                       data=json.dumps({"workflow_stage": "invalid_stage"}),
                       content_type="application/json")
        assert r.status_code == 400

    def test_put_workflow_404(self, client):
        r = client.put("/api/plans/999999/workflow",
                       data=json.dumps({"next_action": "test"}),
                       content_type="application/json")
        assert r.status_code == 404

    def test_get_project_workflows(self, client, test_plan):
        r = client.get("/api/plans/workflow?project_id=project_dashboard")
        assert r.status_code == 200
        d = r.get_json()
        assert "workflows" in d
        ids = [w["plan_id"] for w in d["workflows"]]
        assert test_plan in ids


# --- M3: Workflow-Logik ---

class TestM3WorkflowLogic:
    def test_all_stages_valid(self, test_plan):
        for stage in WORKFLOW_STAGES:
            result = update_plan_workflow(test_plan, {"workflow_stage": stage})
            assert result["workflow_stage"] == stage

    def test_executor_and_review_separate(self, test_plan):
        result = update_plan_workflow(test_plan, {
            "workflow_stage": "review_pending",
            "latest_executor_status": "done",
            "latest_review_status": "fail",
        })
        assert result["workflow_stage"] == "review_pending"
        assert result["latest_executor_status"] == "done"
        assert result["latest_review_status"] == "fail"

    def test_invalid_executor_status_rejected(self, test_plan):
        with pytest.raises(ValueError, match="Ungueltiger latest_executor_status"):
            update_plan_workflow(test_plan, {"latest_executor_status": "bogus"})


# --- D: Drag & Drop Workflow-Update ---

class TestDragDropWorkflow:
    """Tests fuer Drag & Drop Board: workflow_stage per API aendern."""

    def test_drag_drop_stage_update_via_api(self, client, test_plan):
        """D2: PUT /api/plans/<id>/workflow setzt workflow_stage korrekt."""
        for stage in WORKFLOW_STAGES:
            r = client.put(f"/api/plans/{test_plan}/workflow",
                           data=json.dumps({"workflow_stage": stage}),
                           content_type="application/json")
            assert r.status_code == 200
            d = r.get_json()
            assert d["workflow_stage"] == stage

    def test_drag_drop_invalid_stage_rejected(self, client, test_plan):
        """D4: Ungueltige workflow_stage-Werte werden abgewiesen (400)."""
        invalid_stages = ["planning", "in_progress", "testing", "deployed", "", "DONE"]
        for stage in invalid_stages:
            r = client.put(f"/api/plans/{test_plan}/workflow",
                           data=json.dumps({"workflow_stage": stage}),
                           content_type="application/json")
            assert r.status_code == 400, f"Stage '{stage}' haette abgewiesen werden muessen"

    def test_drag_drop_preserves_other_fields(self, client, test_plan):
        """D2: Stage-Aenderung ueberschreibt nicht current_state/target_state/next_action."""
        # Erst Ist/Soll/Next setzen
        client.put(f"/api/plans/{test_plan}/workflow",
                   data=json.dumps({
                       "workflow_stage": "idea",
                       "current_state": "Entwurf liegt vor",
                       "target_state": "Spec fertig",
                       "next_action": "Review durch Team",
                   }),
                   content_type="application/json")

        # Nur workflow_stage aendern (wie beim Board-Drop)
        r = client.put(f"/api/plans/{test_plan}/workflow",
                       data=json.dumps({"workflow_stage": "spec_ready"}),
                       content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["workflow_stage"] == "spec_ready"
        assert d["current_state"] == "Entwurf liegt vor"
        assert d["target_state"] == "Spec fertig"
        assert d["next_action"] == "Review durch Team"

    def test_drag_drop_stage_reflected_in_listing(self, client, test_plan):
        """D3: Nach Stage-Update zeigt GET /api/plans den neuen Stage."""
        client.put(f"/api/plans/{test_plan}/workflow",
                   data=json.dumps({"workflow_stage": "executing"}),
                   content_type="application/json")

        r = client.get("/api/plans")
        plans = r.get_json()["plans"]
        plan = next((p for p in plans if p["id"] == test_plan), None)
        assert plan is not None
        assert plan["workflow_stage"] == "executing"

    def test_drag_drop_nonexistent_plan(self, client):
        """D2: Drop auf nicht-existierenden Plan gibt 404."""
        r = client.put("/api/plans/999999/workflow",
                       data=json.dumps({"workflow_stage": "done"}),
                       content_type="application/json")
        assert r.status_code == 404

    def test_drag_drop_no_body(self, client, test_plan):
        """D2: Leerer Body gibt 400."""
        r = client.put(f"/api/plans/{test_plan}/workflow",
                       content_type="application/json")
        assert r.status_code == 400


# --- M5: Copilot Plan-Binding ---

class TestM5CopilotBinding:
    @patch("services.copilot_service.query_perplexity")
    def test_copilot_with_plan_id(self, mock_llm, client, test_plan, mock_copilot_db):
        mock_llm.return_value = {"content": "Reply", "model": "sonar", "usage": {}}
        r = client.post("/api/copilot/chat",
                        data=json.dumps({
                            "message": "Test mit Plan",
                            "plan_id": test_plan,
                            "project_id": "project_dashboard",
                        }),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["plan_id"] == test_plan


# --- M6: Ist/Soll/Next ---

class TestM6IstSollNext:
    def test_ist_soll_next_roundtrip(self, client, test_plan):
        # Setzen
        client.put(f"/api/plans/{test_plan}/workflow",
                   data=json.dumps({
                       "current_state": "Scanner laeuft, aber Score F",
                       "target_state": "Score B oder besser",
                       "next_action": "Top-5 Issues fixen",
                   }),
                   content_type="application/json")

        # Lesen
        r = client.get(f"/api/plans/{test_plan}/workflow")
        d = r.get_json()
        assert d["current_state"] == "Scanner laeuft, aber Score F"
        assert d["target_state"] == "Score B oder besser"
        assert d["next_action"] == "Top-5 Issues fixen"

    def test_ist_soll_in_plan_listing(self, client, test_plan):
        # Setzen
        client.put(f"/api/plans/{test_plan}/workflow",
                   data=json.dumps({"current_state": "Test-Ist", "target_state": "Test-Soll"}),
                   content_type="application/json")

        # In Listing pruefen
        r = client.get("/api/plans")
        plans = r.get_json()["plans"]
        plan = next((p for p in plans if p["id"] == test_plan), None)
        assert plan is not None
        assert plan["current_state"] == "Test-Ist"
        assert plan["target_state"] == "Test-Soll"


# --- M7: Signal-Integration ---

class TestM7Signals:
    def test_quality_score_in_workflow(self, client, test_plan):
        r = client.get(f"/api/plans/{test_plan}/workflow")
        d = r.get_json()
        # project_dashboard hat einen Quality-Report
        assert "latest_quality_score" in d
        assert isinstance(d["latest_quality_score"], (int, type(None)))

    def test_governance_status_in_workflow(self, client, test_plan):
        r = client.get(f"/api/plans/{test_plan}/workflow")
        d = r.get_json()
        assert "governance_status" in d
        # project_dashboard hat Governance-Gate
        assert d["governance_status"] in ("green", "yellow", "red", None)


# --- N: Plan-Handoff Markdown ---

@pytest.mark.usefixtures("mock_plan_handoff_db")
class TestPlanHandoff:
    """Tests fuer build_handoff_markdown und GET /api/plans/<id>/handoff."""

    def test_handoff_full_plan(self, mock_plan_handoff_db, test_plan):
        """N1/N3: Projekt-Handoff enthaelt Marker-Header und den Plan als Marker."""
        # Plan mit Workflow-Daten befuellen
        update_plan_workflow(test_plan, {
            "workflow_stage": "executing",
            "current_state": "Implementierung laeuft",
            "target_state": "Feature fertig + Tests gruen",
            "next_action": "Unit-Tests ergaenzen",
            "latest_executor_status": "running",
            "latest_review_status": "pending",
            "spec_ref": "SPEC-TEST-001",
            "open_items_count": 3,
        })

        md = build_handoff_markdown("project_dashboard")
        assert md is not None

        # YAML-Frontmatter / Marker-Format
        assert md.startswith("---\n")
        assert "handoff:" in md
        assert 'stage: "executing"' in md
        assert 'state_format: "copilot_markers_v1"' in md
        assert "# Handoff fuer Projekt project_dashboard" in md
        assert "## Copilot Markers" in md
        assert f'<!-- MARKER:{test_plan}' in md

        # Inhaltliche Werte
        assert "Feature fertig + Tests gruen" in md
        assert "Unit-Tests ergaenzen" in md
        assert "Soll-Zustand: Feature fertig + Tests gruen." in md
        assert "Naechster Schritt: Unit-Tests ergaenzen." in md

    def test_handoff_missing_signals(self, mock_plan_handoff_db):
        """N1: Plan ohne Projekt-Zuordnung gibt heute bewusst keinen Projekt-Handoff."""
        # Plan ohne Projekt-Zuordnung → kein Projekt-Handoff moeglich
        ensure_plan_workflow_schema()
        unique = str(uuid.uuid4())[:8]
        row = execute(
            """INSERT INTO project_plans (filename, title, project_name, status, category)
               VALUES (%s, %s, NULL, %s, %s)
               RETURNING id""",
            (f"test-handoff-{unique}.md", "[TEST] Handoff No-Project", "draft", "plan"),
            fetchone=True,
        )
        plan_id = row["id"]

        try:
            md = build_handoff_markdown("project_dashboard")
            assert md is None
        finally:
            execute("DELETE FROM project_plans WHERE id = %s", (plan_id,))

    def test_handoff_nonexistent_plan(self, mock_plan_handoff_db):
        """N1: Nicht-existierendes Projekt gibt None."""
        md = build_handoff_markdown("does_not_exist_999999")
        assert md is None

    def test_handoff_stage_for_idea(self, mock_plan_handoff_db, test_plan):
        """N1: stage spiegelt idea/spec_ready im Projekt-Handoff."""
        update_plan_workflow(test_plan, {"workflow_stage": "idea"})
        md = build_handoff_markdown("project_dashboard")
        assert 'stage: "idea"' in md

        update_plan_workflow(test_plan, {"workflow_stage": "spec_ready"})
        md = build_handoff_markdown("project_dashboard")
        assert 'stage: "spec_ready"' in md

    def test_handoff_stage_review_pending(self, mock_plan_handoff_db, test_plan):
        """N1: stage spiegelt review_pending im Projekt-Handoff."""
        update_plan_workflow(test_plan, {"workflow_stage": "review_pending"})
        md = build_handoff_markdown("project_dashboard")
        assert 'stage: "review_pending"' in md

    def test_handoff_api_200(self, client, mock_plan_handoff_db, test_plan):
        """N2: GET /api/plans/<id>/handoff liefert 200 + text/markdown."""
        r = client.get(f"/api/plans/{test_plan}/handoff")
        assert r.status_code == 200
        assert r.content_type.startswith("text/markdown")
        data = r.data.decode("utf-8")
        assert "---" in data
        assert "## Copilot Markers" in data

    def test_handoff_api_404(self, client, mock_plan_handoff_db):
        """N2: GET /api/plans/999999/handoff liefert 404."""
        r = client.get("/api/plans/999999/handoff")
        assert r.status_code == 404

    def test_handoff_marker_header_order(self, mock_plan_handoff_db, test_plan):
        """N3: Header kommt vor den Marker-Bloecken."""
        update_plan_workflow(test_plan, {"workflow_stage": "executing"})
        md = build_handoff_markdown("project_dashboard")

        sections = [
            "# Handoff fuer Projekt project_dashboard",
            "## Copilot Markers",
            f"<!-- MARKER:{test_plan}",
        ]
        positions = [md.index(s) for s in sections]
        assert positions == sorted(positions), "Marker-Header nicht in korrekter Reihenfolge"

    def test_handoff_maps_completed_plan_to_done_marker(self, mock_plan_handoff_db, test_plan):
        """N1: Abgeschlossene Plans werden als done-Marker serialisiert."""
        execute("UPDATE project_plans SET status = %s WHERE id = %s", ("completed", test_plan))
        md = build_handoff_markdown("project_dashboard")
        assert f'"marker_id": "{test_plan}"' in md
        assert '"status": "done"' in md
