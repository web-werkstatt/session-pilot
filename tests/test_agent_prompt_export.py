"""
Sprint sprint-agent-orchestrator-executor-handoff Commit 1 (2026-04-17):
Tests fuer Prompt-Export (Service + Route).

Scope:
  * `agent_prompt_export_service.build_prompt_markdown` fuer alle Kombinationen
    (mit/ohne Handoff, mit/ohne Marker, mit/ohne Plan, leere Listen).
  * `GET /api/agent-tasks/<id>/prompt` fuer Auth (401 ohne/falscher Token),
    404 fuer unbekannte Tasks, 200 mit korrektem Token, Query-Param-Uebergabe
    an `resolve_context`.

Keine echte DB, keine echten Dateien: alle externen Abhaengigkeiten werden
per Monkeypatch ersetzt.
"""
from __future__ import annotations

import pytest

import services.agent_prompt_export_service as prompt_export
import services.agent_task_auth as agent_task_auth


def _sample_task(**overrides):
    task = {
        "task_id": 42,
        "session_id": "ses_42",
        "project_id": None,
        "title": "Testtask",
        "goal": "Teste den Prompt-Export.",
        "mode": "executor",
        "allowed_files": ["services/foo.py", "tests/test_foo.py"],
        "forbidden_actions": ["git push", "rm -rf /"],
        "required_verification": [
            {"type": "command_exit_zero", "command": "pytest tests/test_foo.py"},
            {"type": "append_only_diff", "path": "next-session.md"},
        ],
        "required_outputs": [],
        "stop_conditions": ["scope_violation_detected"],
        "created_at": "2026-04-17T10:00:00Z",
    }
    task.update(overrides)
    return task


def _sample_context(handoff_path="/tmp/handoff.md", handoff_exists=True,
                    marker=None, plan=None):
    return {
        "project_id": "demo_project",
        "handoff_path": handoff_path,
        "handoff_exists": handoff_exists,
        "active_marker": marker,
        "relevant_plan": plan,
        "start_scope": [],
        "notes": [],
    }


# ---------------------------------------------------------------------------
# Service: build_prompt_markdown — Pflicht-Abschnitte + Varianten
# ---------------------------------------------------------------------------

def test_prompt_has_all_eight_sections_with_full_context():
    """AC1: Vollstaendiger Markdown-Block mit allen acht Abschnitten."""
    task = _sample_task()
    context = _sample_context(
        marker={"marker_id": "m-001", "titel": "Foo-Marker"},
        plan={"id": 7, "title": "Sprint Foo",
              "source_path": "sprints/sprint-foo.md"},
    )
    md = prompt_export.build_prompt_markdown(
        task,
        context=context,
        handoff_tail_lines=3,
        read_handoff_fn=lambda _p: "alpha\nbeta\ngamma\ndelta\nepsilon\n",
    )

    assert md.startswith("# Agent-Task 42: Testtask\n")
    for heading in (
        "## Erlaubte Dateien",
        "## Verbotene Aktionen",
        "## Geforderte Nachweise beim Abschluss",
        "## Stop-Bedingungen",
        "## Handoff-Kontext",
        "## Abschluss-Protokoll",
    ):
        assert heading in md

    assert "Teste den Prompt-Export." in md
    assert "- services/foo.py" in md
    assert "- tests/test_foo.py" in md
    assert "- git push" in md
    assert "command_exit_zero" in md
    assert "command=`pytest tests/test_foo.py`" in md
    assert "append_only_diff" in md
    assert "path=`next-session.md`" in md
    assert "- scope_violation_detected" in md

    # Handoff: nur letzte 3 Zeilen
    assert "`/tmp/handoff.md`" in md
    assert "Letzte 3 Zeilen:" in md
    assert "gamma" in md
    assert "delta" in md
    assert "epsilon" in md
    assert "alpha" not in md
    assert "beta" not in md

    # Marker + Plan in Kompaktform (ID + Titel)
    assert "Aktiver Marker: `m-001` — Foo-Marker" in md
    assert "Relevanter Plan: `7` — Sprint Foo" in md
    assert "sprints/sprint-foo.md" in md

    # Abschluss-Protokoll: 3 Shell-Zeilen + UI-Fallback-Hinweis
    assert "claude-task finish 42" in md
    assert "claude-task verify 42" in md
    assert "claude-task close 42" in md
    assert "Execution-Result pasten" in md


def test_prompt_without_context_keeps_structure():
    """Kein Handoff gesetzt -> klarer Hinweis, alle anderen Abschnitte stehen."""
    task = _sample_task()
    md = prompt_export.build_prompt_markdown(task, context=None)

    assert "## Handoff-Kontext" in md
    assert "_Kein Handoff konfiguriert._" in md
    assert "## Abschluss-Protokoll" in md
    assert "claude-task finish 42" in md


def test_prompt_with_handoff_path_but_missing_file():
    task = _sample_task()
    context = _sample_context(
        handoff_path="/tmp/no-handoff.md", handoff_exists=False
    )
    md = prompt_export.build_prompt_markdown(task, context=context)

    assert "`/tmp/no-handoff.md`" in md
    assert "existiert nicht" in md
    assert "Letzte" not in md  # kein Tail, wenn die Datei fehlt


def test_prompt_without_marker_and_plan():
    task = _sample_task()
    context = _sample_context()
    md = prompt_export.build_prompt_markdown(
        task, context=context, read_handoff_fn=lambda _p: "inhalt\n"
    )

    assert "Aktiver Marker: _keiner_" in md
    assert "Relevanter Plan: _keiner_" in md


def test_prompt_with_marker_but_no_plan():
    task = _sample_task()
    context = _sample_context(
        marker={"marker_id": "m-x", "titel": "Nur Marker"},
    )
    md = prompt_export.build_prompt_markdown(
        task, context=context, read_handoff_fn=lambda _p: ""
    )
    assert "Aktiver Marker: `m-x` — Nur Marker" in md
    assert "Relevanter Plan: _keiner_" in md


def test_prompt_with_empty_task_scope_uses_placeholders():
    task = _sample_task(allowed_files=[], forbidden_actions=[],
                        required_verification=[], stop_conditions=[],
                        goal="")
    md = prompt_export.build_prompt_markdown(task, context=None)
    assert "_Kein Ziel-Text hinterlegt._" in md
    assert "_Kein Scope gesetzt._" in md
    assert "_Keine Einschraenkungen gesetzt._" in md
    assert "_Keine Nachweise konfiguriert._" in md
    assert "_Keine Stop-Bedingungen definiert._" in md


def test_prompt_rejects_empty_task():
    with pytest.raises(ValueError):
        prompt_export.build_prompt_markdown(None)


def test_prompt_handoff_tail_defaults_to_50_lines():
    """Default: letzte 50 Zeilen aus handoff_path."""
    task = _sample_task()
    context = _sample_context(
        handoff_path="/tmp/h.md", handoff_exists=True
    )
    many_lines = "\n".join(f"line-{i}" for i in range(1, 101)) + "\n"
    md = prompt_export.build_prompt_markdown(
        task, context=context, read_handoff_fn=lambda _p: many_lines,
    )

    assert "Letzte 50 Zeilen:" in md
    assert "line-51" in md
    assert "line-100" in md
    assert "line-50" not in md  # 51..100 = letzte 50


# ---------------------------------------------------------------------------
# Route: GET /api/agent-tasks/<id>/prompt
# ---------------------------------------------------------------------------

@pytest.fixture
def prompt_client(monkeypatch, tmp_path):
    """Flask test_client mit gemocktem Token und gemockter Orchestrator-DB."""
    token_file = tmp_path / ".agent-task-token"
    token_file.write_text("secret-token-v1\n", encoding="utf-8")
    monkeypatch.setattr(agent_task_auth, "DEFAULT_TOKEN_PATH", token_file)

    import services.agent_orchestrator_service as orchestrator
    monkeypatch.setattr(
        orchestrator, "ensure_agent_orchestrator_schema", lambda: None
    )

    from app import app
    return app.test_client()


def test_prompt_endpoint_requires_token(prompt_client, monkeypatch):
    import services.agent_orchestrator_service as orchestrator
    monkeypatch.setattr(orchestrator, "get_task",
                        lambda tid: _sample_task(task_id=tid))

    resp = prompt_client.get("/api/agent-tasks/42/prompt")
    assert resp.status_code == 401


def test_prompt_endpoint_rejects_wrong_token(prompt_client, monkeypatch):
    import services.agent_orchestrator_service as orchestrator
    monkeypatch.setattr(orchestrator, "get_task",
                        lambda tid: _sample_task(task_id=tid))

    resp = prompt_client.get(
        "/api/agent-tasks/42/prompt",
        headers={"X-Agent-Task-Token": "wrong"},
    )
    assert resp.status_code == 401


def test_prompt_endpoint_missing_token_file_returns_401(monkeypatch, tmp_path):
    """Ohne konfigurierte Token-Datei -> Standard 401, nicht offen."""
    token_file = tmp_path / "does-not-exist"
    monkeypatch.setattr(agent_task_auth, "DEFAULT_TOKEN_PATH", token_file)

    import services.agent_orchestrator_service as orchestrator
    monkeypatch.setattr(
        orchestrator, "ensure_agent_orchestrator_schema", lambda: None
    )
    monkeypatch.setattr(orchestrator, "get_task",
                        lambda tid: _sample_task(task_id=tid))

    from app import app
    client = app.test_client()
    resp = client.get(
        "/api/agent-tasks/42/prompt",
        headers={"X-Agent-Task-Token": "anything"},
    )
    assert resp.status_code == 401


def test_prompt_endpoint_returns_markdown(prompt_client, monkeypatch):
    import services.agent_orchestrator_service as orchestrator
    monkeypatch.setattr(orchestrator, "get_task",
                        lambda tid: _sample_task(task_id=tid))

    resp = prompt_client.get(
        "/api/agent-tasks/42/prompt",
        headers={"X-Agent-Task-Token": "secret-token-v1"},
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    body = resp.get_data(as_text=True)
    assert "# Agent-Task 42: Testtask" in body
    assert "claude-task finish 42" in body
    # Ohne Query-Param: kein Resolver, kein Handoff
    assert "_Kein Handoff konfiguriert._" in body


def test_prompt_endpoint_404_for_unknown_task(prompt_client, monkeypatch):
    import services.agent_orchestrator_service as orchestrator
    monkeypatch.setattr(orchestrator, "get_task", lambda _tid: None)

    resp = prompt_client.get(
        "/api/agent-tasks/9999/prompt",
        headers={"X-Agent-Task-Token": "secret-token-v1"},
    )
    assert resp.status_code == 404


def test_prompt_endpoint_query_params_build_context(prompt_client, monkeypatch):
    """Query-Params project/plan/marker werden durch den Resolver gereicht."""
    import services.agent_orchestrator_service as orchestrator

    monkeypatch.setattr(orchestrator, "get_task",
                        lambda tid: _sample_task(task_id=tid))

    called = {}

    def fake_resolve(project_id, plan_id=None, marker_id=None):
        called["project_id"] = project_id
        called["plan_id"] = plan_id
        called["marker_id"] = marker_id
        plan_int = int(plan_id) if plan_id is not None else 0
        return _sample_context(
            handoff_path="/tmp/h.md",
            handoff_exists=False,
            marker={"marker_id": marker_id, "titel": "Dynamisch"},
            plan={"id": plan_int, "title": "Dynamischer Plan",
                  "source_path": "sprints/dyn.md"},
        )

    monkeypatch.setattr(orchestrator, "resolve_context", fake_resolve)

    resp = prompt_client.get(
        "/api/agent-tasks/42/prompt?project=demo_project&plan=9&marker=m-007",
        headers={"X-Agent-Task-Token": "secret-token-v1"},
    )
    assert resp.status_code == 200
    assert called == {
        "project_id": "demo_project",
        "plan_id": "9",
        "marker_id": "m-007",
    }
    body = resp.get_data(as_text=True)
    assert "Aktiver Marker: `m-007` — Dynamisch" in body
    assert "Relevanter Plan: `9` — Dynamischer Plan" in body
