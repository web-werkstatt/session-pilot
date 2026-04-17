"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
Projektspezifische Verify-Gate-Tests (docs_updated + Custom-Block-Regex).

Ausgelagert aus tests/test_agent_verify.py, damit die Hauptdatei unter dem
500-Zeilen-Limit bleibt. Fake-DB kommt aus tests/_agent_verify_fake.py.
"""
from __future__ import annotations

import pytest

import services.agent_orchestrator_service as orchestrator
import services.agent_verify_service as verify_service

from tests._agent_verify_fake import install_fake_db


@pytest.fixture
def fake_db(monkeypatch):
    return install_fake_db(monkeypatch)


def _patch_project_config(monkeypatch, docs_paths, block_start=None, block_end=None):
    import services.agent_project_config_service as cfg

    def fake_get_config(project_id):
        return {
            "project_id": project_id,
            "sensitive_files": cfg.DEFAULT_SENSITIVE_FILES,
            "append_only_block_start_regex": block_start or cfg.DEFAULT_BLOCK_START_REGEX,
            "append_only_block_end_regex": block_end or cfg.DEFAULT_BLOCK_END_REGEX,
            "handoff_path_relative": cfg.DEFAULT_HANDOFF_PATH_RELATIVE,
            "docs_paths": docs_paths,
        }

    monkeypatch.setattr(cfg, "get_config", fake_get_config)


# ---------------------------------------------------------------------------
# Claim docs_updated
# ---------------------------------------------------------------------------

def test_docs_updated_fails_when_no_matching_diff(fake_db, monkeypatch):
    _patch_project_config(monkeypatch, docs_paths=["docs/", "README.md"])

    task = orchestrator.create_task({
        "title": "Docs Task",
        "project_id": 42,
        "allowed_files": ["services/foo.py"],
        "required_verification": [{"type": "docs_updated", "claim": "docs_updated"}],
    })
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["services/foo.py"],
        "claims": [],
    })
    gate = verify_service.run_verify_gate(task["task_id"])
    assert gate["status"] == "fail"
    assert "docs_updated" in gate["unverified_claims"]


def test_docs_updated_passes_when_doc_path_matched(fake_db, monkeypatch):
    _patch_project_config(monkeypatch, docs_paths=["docs/", "README.md"])

    task = orchestrator.create_task({
        "title": "Docs Task 2",
        "project_id": 42,
        "allowed_files": ["docs/guide.md"],
        "required_verification": [{"type": "docs_updated", "claim": "docs_updated"}],
    })
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["docs/guide.md"],
        "claims": [],
    })
    gate = verify_service.run_verify_gate(task["task_id"])
    assert gate["status"] == "pass"
    docs_check = next(c for c in gate["checks"] if c.get("claim") == "docs_updated")
    assert docs_check["status"] == "pass"
    assert "docs/guide.md" in docs_check["details"]


def test_docs_updated_fails_when_only_non_doc_paths_changed(fake_db, monkeypatch):
    _patch_project_config(monkeypatch, docs_paths=["docs/"])

    task = orchestrator.create_task({
        "title": "Docs Task 3",
        "project_id": 42,
        "allowed_files": ["services/foo.py"],
        "required_verification": [{"type": "docs_updated", "claim": "docs_updated"}],
    })
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["services/foo.py", "tests/test_foo.py"],
        "claims": [],
    })
    gate = verify_service.run_verify_gate(task["task_id"])
    docs_check = next(c for c in gate["checks"] if c.get("claim") == "docs_updated")
    assert docs_check["status"] == "fail"


def test_docs_updated_blocked_when_config_has_no_docs_paths(fake_db, monkeypatch):
    _patch_project_config(monkeypatch, docs_paths=[])

    task = orchestrator.create_task({
        "title": "Docs Task 4",
        "project_id": 42,
        "required_verification": [{"type": "docs_updated", "claim": "docs_updated"}],
    })
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["docs/guide.md"],
        "claims": [],
    })
    gate = verify_service.run_verify_gate(task["task_id"])
    docs_check = next(c for c in gate["checks"] if c.get("claim") == "docs_updated")
    assert docs_check["status"] == "blocked"
    assert "docs_paths empty" in docs_check["details"]


def test_docs_updated_use_git_diff_runs_runner(fake_db, monkeypatch):
    _patch_project_config(monkeypatch, docs_paths=["docs/"])

    task = orchestrator.create_task({
        "title": "Docs Task 5",
        "project_id": 42,
        "allowed_files": ["services/foo.py", "docs/guide.md"],
        "required_verification": [
            {"type": "docs_updated", "claim": "docs_updated",
             "use_git_diff": True, "base": "main"}
        ],
    })
    verify_service.record_execution(task["task_id"], {
        "changed_files": [],
        "claims": [],
    })
    calls = []

    def runner(cmd):
        calls.append(cmd)
        return 0, "services/foo.py\ndocs/guide.md\n"

    gate = verify_service.run_verify_gate(task["task_id"], command_runner=runner)
    assert calls == ["git diff --name-only main..HEAD"]
    docs_check = next(c for c in gate["checks"] if c.get("claim") == "docs_updated")
    assert docs_check["status"] == "pass"


# ---------------------------------------------------------------------------
# Append-only-Diff mit projekt-spezifischem Block-Regex
# ---------------------------------------------------------------------------

def test_append_only_uses_project_specific_block_regex(fake_db, monkeypatch):
    _patch_project_config(
        monkeypatch,
        docs_paths=[],
        block_start=r"<!--\s*GENERATED:START",
        block_end=r"<!--\s*GENERATED:END",
    )

    file_before = (
        "# Handoff\n"
        "\n"
        "<!-- GENERATED:START -->\n"
        "old content\n"
        "<!-- GENERATED:END -->\n"
        "\n"
        "## Manuell\n"
        "safe line\n"
    )
    diff = (
        "@@ -4,1 +4,1 @@\n"
        "-old content\n"
        "+new content\n"
    )

    task = orchestrator.create_task({
        "title": "Custom Block",
        "project_id": 42,
        "allowed_files": ["handoff.md"],
        "required_verification": [{
            "type": "append_only_diff",
            "claim": "append_only_respected",
            "path": "handoff.md",
            "diff": diff,
            "file_content_before": file_before,
        }],
    })
    verify_service.record_execution(task["task_id"], {
        "changed_files": ["handoff.md"],
        "claims": [],
    })
    gate = verify_service.run_verify_gate(task["task_id"])
    assert gate["status"] == "pass"
