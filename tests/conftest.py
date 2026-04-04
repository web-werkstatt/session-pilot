"""
Shared test fixtures for the SessionPilot test suite.

Provides:
  - Flask test client with TESTING mode
  - Auto-mocks for external services (Perplexity, Docker, Gitea)
  - Safe defaults so no test accidentally calls external APIs

Eval-Fixtures in conftest_eval.py (via pytest_plugins).
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from app import app as flask_app

pytest_plugins = ["tests.conftest_eval"]


# ---------------------------------------------------------------------------
# Flask Test Client
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Shared Flask test client — TESTING mode, no side effects."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def app():
    """Access to the Flask app instance for advanced test scenarios."""
    flask_app.config["TESTING"] = True
    return flask_app


# ---------------------------------------------------------------------------
# External Service Mocks (auto-used in smoke tests via request)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_perplexity():
    """Mock Perplexity API — prevents real LLM calls."""
    fake_response = {
        "content": "Mocked Perplexity response",
        "model": "sonar-test",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "raw": {},
    }
    with patch(
        "services.perplexity_service.query_perplexity",
        return_value=fake_response,
    ) as mock:
        yield mock


@pytest.fixture
def mock_docker():
    """Mock Docker service — prevents real container operations."""
    with patch("services.docker_service.get_containers", return_value=[]) as m1, \
         patch("services.docker_service.get_container_logs", return_value="") as m2:
        yield {"get_containers": m1, "get_container_logs": m2}


@pytest.fixture
def mock_gitea():
    """Mock Gitea API — prevents real remote calls."""
    with patch("services.gitea_service.get_repos", return_value=[]) as m1, \
         patch("services.gitea_service.get_commits", return_value=[]) as m2:
        yield {"get_repos": m1, "get_commits": m2}


@pytest.fixture
def mock_scanner():
    """Mock project scanner — prevents filesystem scanning."""
    fake_projects = {
        "test-project": {
            "name": "test-project",
            "path": "/mnt/projects/test-project",
            "description": "A test project",
            "type": "python-app",
            "activity_score": 50,
            "git": {"branch": "main", "dirty": False},
        }
    }
    with patch(
        "services.project_scanner.scan_projects",
        return_value=fake_projects,
    ) as mock:
        yield mock


@pytest.fixture
def safe_mocks(mock_perplexity, mock_docker, mock_gitea, mock_scanner):
    """Bundle all external mocks for smoke tests."""
    return {
        "perplexity": mock_perplexity,
        "docker": mock_docker,
        "gitea": mock_gitea,
        "scanner": mock_scanner,
    }


@pytest.fixture
def mock_copilot_db(monkeypatch):
    """In-Memory-Fake fuer Copilot-Runs ohne Postgres."""
    import services.copilot_service as copilot_service

    runs = []
    next_id = 1

    def fake_execute(query, params=None, fetch=False, fetchone=False):
        nonlocal next_id
        q = " ".join(str(query).lower().split())
        params = params or ()

        if "insert into copilot_runs" in q:
            created_at = datetime.now(timezone.utc)
            run = {
                "id": next_id,
                "project_id": params[0],
                "thread_id": params[1],
                "user_message": params[2],
                "assistant_reply": params[3],
                "model": params[4],
                "status": params[5],
                "error_info": params[6],
                "plan_id": params[7],
                "images": params[8] if len(params) > 8 else None,
                "created_at": created_at,
            }
            runs.append(run)
            next_id += 1
            return {"id": run["id"], "created_at": created_at} if fetchone else None

        if "from copilot_runs" in q and "select" in q:
            filtered = list(runs)
            if "project_id = %s" in q:
                project_id = params[0]
                filtered = [run for run in filtered if run["project_id"] == project_id]
            if "thread_id = %s" in q:
                idx = 1 if "project_id = %s" in q else 0
                thread_id = params[idx]
                filtered = [run for run in filtered if run["thread_id"] == thread_id]
            if "plan_id = %s" in q:
                idx = 0
                if "project_id = %s" in q:
                    idx += 1
                if "thread_id = %s" in q:
                    idx += 1
                plan_id = params[idx]
                filtered = [run for run in filtered if run["plan_id"] == plan_id]
            limit = params[-1] if params else 50
            filtered = filtered[:limit]
            if fetchone:
                return filtered[0] if filtered else None
            if fetch:
                return filtered
            return None

        return None

    monkeypatch.setattr(copilot_service, "execute", fake_execute)
    monkeypatch.setattr(copilot_service, "ensure_copilot_schema", lambda: None)
    monkeypatch.setattr(copilot_service, "_schema_ready", True)
    monkeypatch.setattr(copilot_service, "_schema_migrations_ready", True)
    return runs


@pytest.fixture
def mock_plan_handoff_db(monkeypatch, tmp_path):
    """Kleiner In-Memory-Store fuer Plan-Handoff-/Workflow-Tests ohne Postgres."""
    import tests.test_plan_workflow as test_plan_workflow_module
    import services.plan_workflow_service as plan_workflow_service
    import services.project_handoff_service as project_handoff_service
    import routes.plans_routes as plans_routes

    project_root = tmp_path / "project_dashboard"
    project_root.mkdir()

    plans = {}
    next_id = 1

    def _now():
        return datetime.now(timezone.utc)

    def fake_execute(query, params=None, fetch=False, fetchone=False):
        nonlocal next_id
        q = " ".join(str(query).lower().split())
        params = params or ()

        if "insert into project_plans" in q:
            project_name = params[2] if len(params) >= 5 else None
            status = params[3] if len(params) >= 5 else params[2]
            category = params[4] if len(params) >= 5 else params[3]
            plan = {
                "id": next_id,
                "filename": params[0],
                "title": params[1],
                "project_name": project_name,
                "status": status,
                "category": category,
                "plan_type": "plan",
                "workflow_stage": "idea",
                "current_state": None,
                "target_state": None,
                "next_action": None,
                "latest_executor_status": None,
                "latest_review_status": None,
                "open_items_count": 0,
                "latest_audit_status": None,
                "latest_quality_score": None,
                "governance_status": None,
                "spec_ref": None,
                "prompt_ref": None,
                "last_run_at": None,
                "created_at": _now(),
                "updated_at": _now(),
            }
            plans[next_id] = plan
            next_id += 1
            return {"id": plan["id"]} if fetchone else None

        if q.startswith("delete from project_plans where id = %s"):
            plans.pop(params[0], None)
            return None

        if q.startswith("update project_plans set "):
            plan_id = params[-1]
            plan = plans.get(plan_id)
            if not plan:
                return None
            assignments = q.split("set ", 1)[1].split(" where", 1)[0].split(", ")
            for idx, assignment in enumerate(assignments):
                if assignment == "updated_at = now()":
                    plan["updated_at"] = _now()
                    continue
                field = assignment.split(" = ", 1)[0]
                plan[field] = params[idx]
            if "updated_at = now()" not in assignments:
                plan["updated_at"] = _now()
            return None

        if "from project_plans where id = %s" in q:
            plan = plans.get(params[0])
            if not plan:
                return None if fetchone else []
            if fetchone:
                return dict(plan)
            return [dict(plan)]

        if "from project_plans where project_name = %s and status != 'archived'" in q:
            project_name = params[0]
            rows = [dict(plan) for plan in plans.values() if plan.get("project_name") == project_name and plan.get("status") != "archived"]
            rows.sort(key=lambda item: (0 if item.get("status") == "active" else 1, -(item.get("updated_at") or _now()).timestamp()))
            return rows if fetch else (rows[0] if rows and fetchone else None)

        if "from project_plans where project_name = %s" in q:
            project_name = params[0]
            rows = [dict(plan) for plan in plans.values() if plan.get("project_name") == project_name]
            return rows if fetch else (rows[0] if rows and fetchone else None)

        if "select id from project_plans where id = %s" in q:
            plan = plans.get(params[0])
            return {"id": plan["id"]} if plan and fetchone else ( [{"id": plan["id"]}] if plan and fetch else [] )

        if "from information_schema.columns" in q or "from information_schema.tables" in q:
            return [] if fetch else None

        if "from audit_runs" in q:
            return None if fetchone else []

        return [] if fetch else None

    monkeypatch.setattr(plan_workflow_service, "execute", fake_execute)
    monkeypatch.setattr(project_handoff_service, "execute", fake_execute)
    monkeypatch.setattr(plans_routes, "execute", fake_execute)
    monkeypatch.setattr(test_plan_workflow_module, "execute", fake_execute)

    monkeypatch.setattr(plan_workflow_service, "ensure_plan_workflow_schema", lambda: None)
    monkeypatch.setattr(project_handoff_service, "ensure_plans_schema", lambda: None)
    monkeypatch.setattr(test_plan_workflow_module, "ensure_plan_workflow_schema", lambda: None)

    monkeypatch.setattr(plan_workflow_service, "_fetch_live_signals", lambda project_name: {})
    monkeypatch.setattr(project_handoff_service, "resolve_project_path", lambda project_id: str(project_root) if project_id == "project_dashboard" else None)
    monkeypatch.setattr(project_handoff_service, "PROJECTS_DIR", str(tmp_path))

    return {"plans": plans, "project_root": Path(project_root)}


@pytest.fixture
def mock_plan_sections_db(monkeypatch):
    """In-Memory-Fake fuer plan_section_service (Threads + Messages) ohne Postgres.

    Registriert ausserdem section_bp, falls noch nicht geschehen.
    """
    import services.plan_section_service as pss
    from routes.section_routes import section_bp

    # Blueprint einmalig registrieren (idempotent pruefen)
    if "sections" not in flask_app.blueprints:
        flask_app.register_blueprint(section_bp)

    threads = []
    messages = []
    next_thread_id = 1
    next_msg_id = 1

    def fake_execute(query, params=None, fetch=False, fetchone=False):
        nonlocal next_thread_id, next_msg_id
        q = " ".join(str(query).lower().split())
        params = params or ()

        # --- copilot_threads ---
        if "select" in q and "from copilot_threads" in q and "section_id = %s" in q:
            section_id = params[0]
            found = [t for t in threads if t["section_id"] == section_id]
            if fetchone:
                return found[0] if found else None
            return found if fetch else None

        if "insert into copilot_threads" in q:
            t = {
                "id": next_thread_id,
                "project_id": params[0],
                "plan_id": params[1],
                "section_id": params[2],
                "created_by_id": params[3] if len(params) > 3 else None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            threads.append(t)
            next_thread_id += 1
            return {"id": t["id"], "created_at": t["created_at"]} if fetchone else None

        # --- copilot_messages ---
        if "insert into copilot_messages" in q:
            import json as _json
            m = {
                "id": next_msg_id,
                "thread_id": params[0],
                "project_id": params[1],
                "plan_id": params[2],
                "section_id": params[3],
                "role": params[4],
                "content": params[5],
                "images": _json.loads(params[6]) if params[6] else None,
                "provider": params[7],
                "model": params[8],
                "input_tokens": params[9],
                "output_tokens": params[10],
                "total_tokens": params[11],
                "cost_usd": params[12],
                "duration_ms": params[13],
                "meta": params[14],
                "created_by_id": params[15] if len(params) > 15 else None,
                "created_at": datetime.now(timezone.utc),
            }
            messages.append(m)
            next_msg_id += 1
            return {"id": m["id"], "created_at": m["created_at"]} if fetchone else None

        if "from copilot_messages" in q and "thread_id = %s" in q:
            thread_id = params[0]
            limit = params[1] if len(params) > 1 else 50
            found = [m for m in messages if m["thread_id"] == thread_id][:limit]
            if fetch:
                return found
            return None

        return [] if fetch else None

    monkeypatch.setattr(pss, "execute", fake_execute)
    monkeypatch.setattr(pss, "ensure_section_schema", lambda: None)
    monkeypatch.setattr(pss, "_schema_ready", True)
    return {"threads": threads, "messages": messages}



# mock_eval_db ist in conftest_eval.py (via pytest_plugins)
