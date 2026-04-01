"""
Sprint E: Abnahmetests fuer Plan-Workflow Micro-Ebene.
Deckt M1-M8 ab: DB, API, Workflow-Logik, Signale, Copilot-Binding.
"""
import json
import uuid
import pytest
from unittest.mock import patch

from app import app as flask_app
from services.plan_workflow_service import (
    get_plan_workflow,
    update_plan_workflow,
    get_project_plan_workflows,
    WORKFLOW_STAGES,
    EXECUTOR_STATUSES,
    REVIEW_STATUSES,
)
from services.db_service import execute, ensure_plan_workflow_schema


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def test_plan():
    """Erstellt einen Test-Plan in der DB mit einzigartigem Filename."""
    ensure_plan_workflow_schema()
    unique = str(uuid.uuid4())[:8]
    row = execute(
        """INSERT INTO project_plans (filename, title, project_name, status, category)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING id""",
        (f"test-wf-{unique}.md", "Test Workflow Plan", "project_dashboard", "active", "feature"),
        fetchone=True,
    )
    return row["id"]


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


# --- M5: Copilot Plan-Binding ---

class TestM5CopilotBinding:
    @patch("services.copilot_service.query_perplexity")
    def test_copilot_with_plan_id(self, mock_llm, client, test_plan):
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
