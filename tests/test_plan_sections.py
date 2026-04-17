"""
Sprint H: Tests fuer plan_sections, copilot_threads, copilot_messages.
"""
import json
import uuid
import pytest
from unittest.mock import patch

from services.plan_section_service import (
    ensure_section_schema,
    create_plan_section,
    list_plan_sections,
    get_plan_section,
    update_plan_section,
    get_or_create_thread,
    create_message,
    list_messages,
    chat_with_section,
    VALID_SECTION_KINDS,
    VALID_SECTION_STATUSES,
    VALID_SECTION_STAGES,
)
from services.db_service import execute, ensure_plans_schema


@pytest.fixture
def test_plan():
    """Erstellt einen Test-Plan in project_plans, rauemt nach dem Test auf."""
    ensure_plans_schema()
    unique = str(uuid.uuid4())[:8]
    row = execute(
        """INSERT INTO project_plans (filename, title, project_name, status, category)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (f"test-sec-{unique}.md", "[TEST] Section Plan", "project_dashboard", "active", "feature"),
        fetchone=True,
    )
    plan_id = row["id"]
    yield plan_id
    # Cleanup: Messages → Threads → Sections → Plan
    execute("""DELETE FROM copilot_messages WHERE thread_id IN
               (SELECT id FROM copilot_threads WHERE plan_id = %s)""", (plan_id,))
    execute("DELETE FROM copilot_threads WHERE plan_id = %s", (plan_id,))
    execute("DELETE FROM plan_sections WHERE plan_id = %s", (plan_id,))
    execute("DELETE FROM project_plans WHERE id = %s", (plan_id,))


@pytest.fixture
def test_section(test_plan):
    """Erstellt eine Test-Section."""
    result = create_plan_section(
        plan_id=test_plan, kind="spec", title="Test Spec Section",
        summary="Eine Test-Spec", spec_ref="SPEC-TEST-001",
    )
    return result["id"]


# --- DB1: plan_sections ---

class TestPlanSectionsSchema:
    def test_tables_exist(self):
        ensure_section_schema()
        for table in ("plan_sections", "copilot_threads", "copilot_messages"):
            rows = execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (table,), fetch=True,
            )
            assert len(rows) == 1, f"Tabelle {table} existiert nicht"


class TestPlanSectionsService:
    def test_create_section(self, test_plan):
        result = create_plan_section(test_plan, "section", "Abschnitt A")
        assert result["id"] > 0

    def test_create_spec(self, test_plan):
        result = create_plan_section(test_plan, "spec", "SPEC-X", spec_ref="SPEC-X-001")
        assert result["id"] > 0

    def test_invalid_kind_rejected(self, test_plan):
        with pytest.raises(ValueError, match="Ungueltiger kind"):
            create_plan_section(test_plan, "invalid", "Nope")

    def test_list_sections(self, test_plan):
        create_plan_section(test_plan, "section", "A", position=1)
        create_plan_section(test_plan, "spec", "B", position=0)
        sections = list_plan_sections(test_plan)
        assert len(sections) >= 2
        # Sortiert nach position
        positions = [s["position"] for s in sections]
        assert positions == sorted(positions)

    def test_get_section(self, test_section):
        sec = get_plan_section(test_section)
        assert sec is not None
        assert sec["title"] == "Test Spec Section"
        assert sec["kind"] == "spec"

    def test_update_section(self, test_section):
        result = update_plan_section(test_section, {
            "title": "Updated Title",
            "workflow_stage": "executing",
            "status": "in_progress",
        })
        assert result["title"] == "Updated Title"
        assert result["workflow_stage"] == "executing"
        assert result["status"] == "in_progress"

    def test_update_invalid_status_rejected(self, test_section):
        with pytest.raises(ValueError, match="Ungueltiger status"):
            update_plan_section(test_section, {"status": "bogus"})

    def test_update_nonexistent_returns_none(self):
        result = update_plan_section(999999, {"title": "Nope"})
        assert result is None

    def test_auto_position(self, test_plan):
        s1 = create_plan_section(test_plan, "section", "First")
        s2 = create_plan_section(test_plan, "section", "Second")
        sec1 = get_plan_section(s1["id"])
        sec2 = get_plan_section(s2["id"])
        assert sec2["position"] > sec1["position"]


# --- DB2: copilot_threads ---

class TestCopilotThreads:
    def test_create_thread(self, test_section):
        result = get_or_create_thread(None, 1, test_section)
        assert result["thread_id"] > 0
        assert result["created"] is True

    def test_get_existing_thread(self, test_section):
        r1 = get_or_create_thread(None, 1, test_section)
        r2 = get_or_create_thread(None, 1, test_section)
        assert r1["thread_id"] == r2["thread_id"]
        assert r2["created"] is False


# --- DB3: copilot_messages ---

class TestCopilotMessages:
    def test_create_and_list(self, test_section):
        thr = get_or_create_thread(None, 1, test_section)
        tid = thr["thread_id"]

        m1 = create_message(tid, "user", "Hallo", section_id=test_section)
        assert m1["id"] > 0
        assert m1["role"] == "user"

        m2 = create_message(tid, "assistant", "Hi!", section_id=test_section,
                           provider="perplexity", model="sonar", input_tokens=10,
                           output_tokens=20, total_tokens=30, cost_usd=0.00003,
                           duration_ms=150)
        assert m2["cost_usd"] == 0.00003

        msgs = list_messages(tid)
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles
        assert "assistant" in roles

    def test_message_with_images(self, test_section):
        thr = get_or_create_thread(None, 1, test_section)
        images = [{"filename": "test.png", "url": "/static/uploads/copilot/x.png", "mime_type": "image/png"}]
        msg = create_message(thr["thread_id"], "user", "Bild", section_id=test_section, images=images)
        assert msg["images"] is not None
        assert msg["images"][0]["filename"] == "test.png"


# --- API1: Sections Endpoints ---

class TestSectionsAPI:
    def test_list_sections(self, client, test_plan):
        create_plan_section(test_plan, "section", "API Test Section")
        r = client.get(f"/api/plans/{test_plan}/sections")
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["sections"]) >= 1

    def test_create_section_via_api(self, client, test_plan):
        r = client.post(f"/api/plans/{test_plan}/sections",
                        data=json.dumps({"title": "New via API", "kind": "spec"}),
                        content_type="application/json")
        assert r.status_code == 201
        assert r.get_json()["id"] > 0

    def test_create_section_missing_title(self, client, test_plan):
        r = client.post(f"/api/plans/{test_plan}/sections",
                        data=json.dumps({"kind": "section"}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_update_section_via_api(self, client, test_section):
        r = client.put(f"/api/plan-sections/{test_section}",
                       data=json.dumps({"workflow_stage": "done"}),
                       content_type="application/json")
        assert r.status_code == 200
        assert r.get_json()["workflow_stage"] == "done"

    def test_update_section_404(self, client):
        r = client.put("/api/plan-sections/999999",
                       data=json.dumps({"title": "Nope"}),
                       content_type="application/json")
        assert r.status_code == 404

    def test_get_section_via_api(self, client, test_section):
        r = client.get(f"/api/plan-sections/{test_section}")
        assert r.status_code == 200
        assert r.get_json()["kind"] == "spec"


# --- API2: Section-Chat ---

class TestSectionChat:
    @patch("services.perplexity_service.query_perplexity")
    def test_section_chat_success(self, mock_llm, client, test_plan, test_section):
        mock_llm.return_value = {
            "content": "Section-Antwort",
            "model": "sonar-test",
            "provider": "perplexity",
            "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        }
        r = client.post("/api/copilot/section-chat",
                        data=json.dumps({
                            "message": "Was ist der Status?",
                            "plan_id": test_plan,
                            "section_id": test_section,
                        }),
                        content_type="application/json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "success"
        assert d["thread_id"] > 0
        assert d["assistant_message"]["content"] == "Section-Antwort"
        assert d["assistant_message"]["input_tokens"] == 50

    def test_section_chat_missing_section(self, client, test_plan):
        r = client.post("/api/copilot/section-chat",
                        data=json.dumps({"message": "Test", "plan_id": test_plan}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_section_chat_missing_message(self, client, test_plan, test_section):
        r = client.post("/api/copilot/section-chat",
                        data=json.dumps({"plan_id": test_plan, "section_id": test_section}),
                        content_type="application/json")
        assert r.status_code == 400


# --- API3: Messages ---

@pytest.mark.usefixtures("mock_plan_sections_db")
class TestMessagesAPI:
    def test_list_messages_via_api(self, client):
        thr = get_or_create_thread(None, 1, 999)
        create_message(thr["thread_id"], "user", "API-Test-Msg", section_id=999)

        r = client.get(f"/api/copilot/messages?thread_id={thr['thread_id']}")
        assert r.status_code == 200
        msgs = r.get_json()["messages"]
        assert len(msgs) >= 1

    def test_list_messages_missing_thread(self, client):
        r = client.get("/api/copilot/messages")
        assert r.status_code == 400


# --- UI1: /copilot?plan_id=X ---

class TestCopilotBoardUI:
    def test_copilot_board_renders(self, client):
        r = client.get("/copilot?plan_id=1")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "sectionsBoard" in html
        assert "copilot_board.js" in html
        assert "sectionPanel" in html
        assert "panelChatInput" in html

    def test_copilot_without_plan_id_redirects(self, client):
        """/copilot ohne plan_id redirectet zum letzten Plan oder nach /plans."""
        r = client.get("/copilot", follow_redirects=False)
        assert r.status_code in (302, 303)
        location = r.headers.get("Location", "")
        assert location.startswith("/copilot?plan_id=") or location == "/plans"

    def test_plans_page_no_copilot_elements(self, client):
        """Plans-Seite enthaelt keine Copilot-/Section-Elemente (nur Links)."""
        r = client.get("/plans")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "planChatMessages" not in html
        assert "copilot-inline" not in html
        assert "sectionChat" not in html
        # Aber plans.js enthaelt den copilotLink-Builder
        assert "plans.js" in html
