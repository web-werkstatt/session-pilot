"""
Tests fuer ADR-002 Stufe 1a: Setup-Reviewer (Collector + Review + Storage).

Nutzt monkeypatch fuer `execute` und `path_resolver`, damit keine echte
DB oder Filesystem-Abhaengigkeit gebraucht wird. Der Reviewer selbst wird
mit einem injected `query_fn` getestet, nicht mit echtem Perplexity.
"""
import json
from datetime import datetime, timezone

import pytest

import services.tool_setup_review as tsr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_project(tmp_path):
    """Legt ein minimales Projekt mit project.json + optionalen Tool-Files an."""
    project_dir = tmp_path / "fake-project"
    project_dir.mkdir()
    (project_dir / "project.json").write_text(
        json.dumps(
            {
                "name": "fake-project",
                "project_type": "python-app",
                "description": "test",
                "tags": ["python"],
            }
        ),
        encoding="utf-8",
    )
    return project_dir


@pytest.fixture
def fake_db(monkeypatch):
    """In-Memory-Fake fuer die project_reviews-Tabelle."""
    rows = {}

    def fake_execute(sql, params=None, fetch=False, fetchone=False):
        sql_norm = " ".join(str(sql).lower().split())
        params = params or ()

        if "insert into project_reviews" in sql_norm:
            key = (params[0], params[1])
            rows[key] = {
                "project_name": params[0],
                "review_type": params[1],
                "reviewer_tool": params[2],
                "reviewed_tools": json.loads(params[3]) if params[3] else [],
                "setup_ok": params[4],
                "priority": params[5],
                "summary": params[6],
                "findings": json.loads(params[7]) if params[7] else [],
                "suggested_blocks": json.loads(params[8]) if params[8] else {},
                "project_json_patch": json.loads(params[9]) if params[9] else None,
                "implementation_scope": params[10],
                "notes": json.loads(params[11]) if params[11] else [],
                "context_drift": json.loads(params[12]) if params[12] else None,
                "context_hash": params[13],
                "reviewer_model": params[14],
                "raw_response": params[15],
                "error": params[16],
                "updated_at": params[17],
                "created_at": params[17],
            }
            return None

        if "select" in sql_norm and "from project_reviews" in sql_norm:
            key = (params[0], params[1] if len(params) > 1 else "setup")
            row = rows.get(key)
            if fetchone:
                return row
            return [row] if row else []

        if sql_norm.startswith("create table") or sql_norm.startswith("create index"):
            return None

        return [] if fetch else None

    def fake_ensure_schema():
        return None

    import services.db_service as db_service
    import services.db_tool_setup_review_schema as tsr_schema

    monkeypatch.setattr(db_service, "execute", fake_execute)
    monkeypatch.setattr(
        tsr_schema, "ensure_tool_setup_review_schema", fake_ensure_schema
    )
    return rows


@pytest.fixture
def patch_project_resolver(fake_project, monkeypatch):
    """resolve_project_path liefert das Fake-Projekt-Verzeichnis."""
    import services.path_resolver as path_resolver

    def fake_resolve(name):
        if name == "fake-project":
            return str(fake_project)
        return None

    monkeypatch.setattr(path_resolver, "resolve_project_path", fake_resolve)
    return fake_resolve


@pytest.fixture
def patch_project_scanner(monkeypatch, fake_project):
    """load_project_json gibt ein minimales Dict."""
    import services.project_scanner as scanner

    def fake_load(path):
        return {
            "name": "fake-project",
            "project_type": "python-app",
            "description": "test",
            "tags": ["python"],
        }

    monkeypatch.setattr(scanner, "load_project_json", fake_load)
    return fake_load


@pytest.fixture
def patch_workflow_core(monkeypatch):
    """workflow_core_service.get_markers liefert leere Liste per default."""
    import services.workflow_core_service as wcs

    monkeypatch.setattr(wcs, "get_markers", lambda name, plan_id=None: [])
    return wcs


@pytest.fixture
def reviewer_ready(
    fake_project,
    fake_db,
    patch_project_resolver,
    patch_project_scanner,
    patch_workflow_core,
):
    """Bundelt alle Fixtures, die ein reviewer-faehiges Setup liefern."""
    return {"project": fake_project, "db": fake_db}


# ---------------------------------------------------------------------------
# Collector-Tests
# ---------------------------------------------------------------------------

def test_collector_returns_none_for_unknown_project(patch_project_resolver):
    result = tsr.build_tool_setup_context("nonexistent-project")
    assert result is None


def test_collector_returns_context_for_empty_project(reviewer_ready):
    ctx = tsr.build_tool_setup_context("fake-project")
    assert ctx is not None
    assert ctx["project"]["name"] == "fake-project"
    assert ctx["project"]["type"] == "python-app"
    assert ctx["schema_version"] == tsr.SCHEMA_VERSION

    # Alle drei Tool-Files existieren nicht im leeren Projekt
    for fname in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
        assert ctx["tool_files"][fname]["exists"] is False
        assert ctx["tool_files"][fname]["has_generated_block"] is False


def test_collector_with_tool_file(reviewer_ready, fake_project):
    (fake_project / "CLAUDE.md").write_text(
        "# Manual Rules\n\nSome text without generated block\n",
        encoding="utf-8",
    )
    ctx = tsr.build_tool_setup_context("fake-project")
    claude_info = ctx["tool_files"]["CLAUDE.md"]
    assert claude_info["exists"] is True
    assert claude_info["has_generated_block"] is False
    assert "Manual Rules" in claude_info["manual_excerpt_head"]


def test_collector_detects_generated_block(reviewer_ready, fake_project):
    content = (
        "# Manual\n\nText\n\n"
        "<!-- DASHBOARD-GENERATED:START source=tool_profile_adapter updated=2026-04-11 -->\n"
        "## Snapshot\n\nHello\n"
        "<!-- DASHBOARD-GENERATED:END -->\n"
    )
    (fake_project / "CLAUDE.md").write_text(content, encoding="utf-8")
    ctx = tsr.build_tool_setup_context("fake-project")
    claude_info = ctx["tool_files"]["CLAUDE.md"]
    assert claude_info["exists"] is True
    assert claude_info["has_generated_block"] is True
    assert claude_info["generated_block_source"] == "tool_profile_adapter"
    assert claude_info["generated_block_updated"] == "2026-04-11"


# ---------------------------------------------------------------------------
# Context-Drift-Tests
# ---------------------------------------------------------------------------

def test_drift_no_files_existing():
    result = tsr.detect_context_drift({
        "CLAUDE.md": {"exists": False},
        "AGENTS.md": {"exists": False},
        "GEMINI.md": {"exists": False},
    })
    assert result["has_drift"] is False


def test_drift_no_generated_blocks():
    result = tsr.detect_context_drift({
        "CLAUDE.md": {"exists": True, "has_generated_block": False},
        "AGENTS.md": {"exists": True, "has_generated_block": False},
    })
    assert result["has_drift"] is False


def test_drift_all_blocks_identical():
    same = "## Snapshot\n- Projekt: fake\n"
    result = tsr.detect_context_drift({
        "CLAUDE.md": {
            "exists": True,
            "has_generated_block": True,
            "generated_block_content": same,
            "generated_block_updated": "2026-04-11",
        },
        "AGENTS.md": {
            "exists": True,
            "has_generated_block": True,
            "generated_block_content": same,
            "generated_block_updated": "2026-04-11",
        },
        "GEMINI.md": {
            "exists": True,
            "has_generated_block": True,
            "generated_block_content": same,
            "generated_block_updated": "2026-04-11",
        },
    })
    assert result["has_drift"] is False


def test_drift_blocks_differ():
    result = tsr.detect_context_drift({
        "CLAUDE.md": {
            "exists": True,
            "has_generated_block": True,
            "generated_block_content": "## V1\n",
            "generated_block_updated": "2026-04-11",
        },
        "AGENTS.md": {
            "exists": True,
            "has_generated_block": True,
            "generated_block_content": "## V2\n",
            "generated_block_updated": "2026-04-08",
        },
    })
    assert result["has_drift"] is True
    assert "CLAUDE.md" in result["drifted_files"]
    assert "AGENTS.md" in result["drifted_files"]


def test_drift_some_files_missing_block():
    result = tsr.detect_context_drift({
        "CLAUDE.md": {
            "exists": True,
            "has_generated_block": True,
            "generated_block_content": "## Snapshot\n",
            "generated_block_updated": "2026-04-11",
        },
        "AGENTS.md": {"exists": True, "has_generated_block": False},
    })
    assert result["has_drift"] is True
    assert "AGENTS.md" in result["drifted_files"]


# ---------------------------------------------------------------------------
# Parser-Tests
# ---------------------------------------------------------------------------

def test_parse_plain_json():
    result = tsr._parse_reviewer_response('{"setup_ok": true, "findings": []}')
    assert result == {"setup_ok": True, "findings": []}


def test_parse_code_fence_json():
    content = '```json\n{"setup_ok": false, "priority": "high"}\n```'
    result = tsr._parse_reviewer_response(content)
    assert result["setup_ok"] is False
    assert result["priority"] == "high"


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        tsr._parse_reviewer_response("")


def test_parse_not_object_raises():
    with pytest.raises(ValueError):
        tsr._parse_reviewer_response('["just","a","list"]')


# ---------------------------------------------------------------------------
# Context-Hash-Tests
# ---------------------------------------------------------------------------

def test_context_hash_deterministic():
    ctx1 = {"a": 1, "b": 2}
    ctx2 = {"b": 2, "a": 1}  # andere Reihenfolge
    assert tsr._compute_context_hash(ctx1) == tsr._compute_context_hash(ctx2)


def test_context_hash_different_content():
    h1 = tsr._compute_context_hash({"a": 1})
    h2 = tsr._compute_context_hash({"a": 2})
    assert h1 != h2


# ---------------------------------------------------------------------------
# Review-Flow-Tests (mit injected query_fn)
# ---------------------------------------------------------------------------

def _make_fake_query(content):
    def _fn(messages, temperature=0.0, **kwargs):
        return {
            "provider": "perplexity",
            "model": "sonar-test",
            "content": content,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "raw": {},
        }
    return _fn


def test_review_success_flow(reviewer_ready):
    fake_content = json.dumps({
        "schema_version": 1,
        "setup_ok": False,
        "priority": "medium",
        "summary": "Testprojekt ohne Tool-Files",
        "findings": [
            {
                "area": "claude_md",
                "severity": "warn",
                "title": "Keine CLAUDE.md",
                "problem": "fehlt",
                "why_it_matters": "Tools kennen keinen Startkontext",
                "recommended_change": "anlegen",
                "can_autofix": False,
            }
        ],
        "suggested_blocks": {"CLAUDE.md": "Snapshot"},
        "suggested_project_json_patch": None,
        "implementation_scope": "small",
        "notes": [],
    })

    result = tsr.review_tool_setup("fake-project", query_fn=_make_fake_query(fake_content))
    assert result["error"] is None
    assert result["setup_ok"] is False
    assert result["priority"] == "medium"
    assert len(result["findings"]) == 1
    assert result["reviewer_tool"] == "perplexity"
    assert result["reviewer_model"] == "sonar-test"
    assert result["context_hash"]  # gesetzt


def test_review_parse_error_persists(reviewer_ready):
    result = tsr.review_tool_setup(
        "fake-project", query_fn=_make_fake_query("not json at all")
    )
    assert result["error"] == "parse_failed"
    assert result["setup_ok"] is None
    assert "raw_response" in result


def test_review_query_error_persists(reviewer_ready):
    def broken_query(messages, temperature=0.0, **kwargs):
        raise RuntimeError("network down")

    result = tsr.review_tool_setup("fake-project", query_fn=broken_query)
    assert result["error"] == "query_failed"
    assert result["setup_ok"] is None
    assert "network down" in (result["raw_response"] or "")


def test_review_dedup_hit(reviewer_ready):
    fake_content = json.dumps({
        "schema_version": 1,
        "setup_ok": True,
        "priority": "low",
        "summary": "alles gut",
        "findings": [],
        "suggested_blocks": {},
        "suggested_project_json_patch": None,
        "implementation_scope": "tiny",
        "notes": [],
    })
    query_calls = []

    def counting_query(messages, temperature=0.0, **kwargs):
        query_calls.append(1)
        return {
            "provider": "perplexity",
            "model": "sonar-test",
            "content": fake_content,
            "usage": {},
            "raw": {},
        }

    first = tsr.review_tool_setup("fake-project", query_fn=counting_query)
    assert first["error"] is None
    assert len(query_calls) == 1

    second = tsr.review_tool_setup("fake-project", query_fn=counting_query)
    # Dedup: gleicher Context-Hash, kein zweiter Query-Call
    assert len(query_calls) == 1
    assert second.get("dedup_hit") is True


def test_review_project_not_found(reviewer_ready):
    result = tsr.review_tool_setup("ghost-project", query_fn=_make_fake_query("{}"))
    assert result["error"] == "project_not_found"


# ---------------------------------------------------------------------------
# Marker-Context-Tests
# ---------------------------------------------------------------------------

def test_marker_context_testmarker_detection(fake_project):
    marker_path = fake_project / "marker-context.md"
    marker_path.write_text(
        "# Marker-Kontext\n\n- marker_id: test-cockpit-2026-04-05\n",
        encoding="utf-8",
    )
    info = tsr._inspect_marker_context(str(marker_path))
    assert info["status"] == "testmarker_detected"
    assert info["warning"] is not None


def test_marker_context_missing():
    info = tsr._inspect_marker_context("/nonexistent/path/marker-context.md")
    assert info["exists"] is False
    assert info["status"] == "absent"
