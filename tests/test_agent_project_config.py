"""
Sprint sprint-agent-orchestrator-project-config (2026-04-17):
Tests fuer agent_project_config_service.

Abgedeckt:
  * get_config(None) liefert Defaults ohne DB-Zugriff
  * get_config(id) ohne DB-Eintrag liefert Defaults
  * set_config ueberschreibt nur uebergebene Felder (feldweise)
  * set_config lehnt unbekannte Felder ab
  * delete_config setzt auf Defaults zurueck
"""
from __future__ import annotations

import json
from typing import Any

import pytest

import services.agent_project_config_service as config_service


@pytest.fixture
def fake_db(monkeypatch):
    store: dict[int, dict[str, Any]] = {}

    def fake_execute(query, params=None, fetch=False, fetchone=False):
        q = " ".join(str(query).lower().split())
        p = tuple(params or ())

        if q.startswith("select project_id from agent_project_configs"):
            row = store.get(p[0])
            return {"project_id": row["project_id"]} if row else None

        if q.startswith("select project_id,") and "from agent_project_configs" in q:
            row = store.get(p[0])
            return dict(row) if row else None

        if q.startswith("insert into agent_project_configs"):
            pid = p[0]
            store[pid] = {
                "project_id": pid,
                "sensitive_files_json": _parse(p[1]),
                "append_only_block_start_regex": p[2],
                "append_only_block_end_regex": p[3],
                "handoff_path_relative": p[4],
                "docs_paths_json": _parse(p[5]),
            }
            return None

        if q.startswith("update agent_project_configs"):
            # project_id ist immer der letzte Parameter.
            pid = p[-1]
            row = store.get(pid)
            if row is None:
                return None
            # Assignments aus Query und Werte aus params[:-1] zuordnen.
            assignments = _split_assignments(q)
            for col, val in zip(assignments, p[:-1]):
                if col.startswith("sensitive_files_json"):
                    row["sensitive_files_json"] = _parse(val)
                elif col.startswith("docs_paths_json"):
                    row["docs_paths_json"] = _parse(val)
                elif col.startswith("updated_at"):
                    continue
                else:
                    row[col.split(" =")[0].strip()] = val
            return None

        if q.startswith("delete from agent_project_configs"):
            store.pop(p[0], None)
            return None

        return None

    monkeypatch.setattr(config_service, "execute", fake_execute)
    monkeypatch.setattr(config_service, "ensure_agent_project_config_schema", lambda: None)
    return store


def _parse(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _split_assignments(q):
    # "update agent_project_configs set a = %s, b = %s where project_id = %s"
    set_part = q.split("set", 1)[1].split("where")[0]
    return [part.strip() for part in set_part.split(",") if part.strip()]


def test_get_config_without_project_id_returns_defaults():
    cfg = config_service.get_config(None)
    assert cfg["sensitive_files"] == config_service.DEFAULT_SENSITIVE_FILES
    assert cfg["append_only_block_start_regex"] == config_service.DEFAULT_BLOCK_START_REGEX
    assert cfg["handoff_path_relative"] == config_service.DEFAULT_HANDOFF_PATH_RELATIVE
    assert cfg["docs_paths"] == config_service.DEFAULT_DOCS_PATHS
    assert cfg["project_id"] is None


def test_get_config_without_row_returns_defaults(fake_db):
    cfg = config_service.get_config(42)
    assert cfg["project_id"] == 42
    assert cfg["sensitive_files"] == config_service.DEFAULT_SENSITIVE_FILES
    assert cfg["handoff_path_relative"] == config_service.DEFAULT_HANDOFF_PATH_RELATIVE


def test_set_config_overrides_only_given_field(fake_db):
    updated = config_service.set_config(42, sensitive_files=["foo.md"])
    assert updated["sensitive_files"] == ["foo.md"]
    # Andere Felder bleiben auf Default.
    assert updated["append_only_block_start_regex"] == config_service.DEFAULT_BLOCK_START_REGEX
    assert updated["docs_paths"] == config_service.DEFAULT_DOCS_PATHS

    # Nur docs_paths ueberschreiben, sensitive_files muss erhalten bleiben.
    updated2 = config_service.set_config(42, docs_paths=["docs/", "README.md"])
    assert updated2["sensitive_files"] == ["foo.md"]
    assert updated2["docs_paths"] == ["docs/", "README.md"]


def test_set_config_custom_block_regex(fake_db):
    updated = config_service.set_config(
        7,
        append_only_block_start_regex=r"<!--\s*GENERATED:START",
        append_only_block_end_regex=r"<!--\s*GENERATED:END",
    )
    assert updated["append_only_block_start_regex"] == r"<!--\s*GENERATED:START"
    assert updated["append_only_block_end_regex"] == r"<!--\s*GENERATED:END"
    # sensitive_files bleibt Default.
    assert updated["sensitive_files"] == config_service.DEFAULT_SENSITIVE_FILES


def test_set_config_rejects_unknown_field(fake_db):
    with pytest.raises(ValueError):
        config_service.set_config(1, foo="bar")


def test_set_config_rejects_none_project_id(fake_db):
    with pytest.raises(ValueError):
        config_service.set_config(None, sensitive_files=[])


def test_delete_config_falls_back_to_defaults(fake_db):
    config_service.set_config(99, sensitive_files=["x.md"])
    cfg = config_service.get_config(99)
    assert cfg["sensitive_files"] == ["x.md"]

    config_service.delete_config(99)
    cfg_after = config_service.get_config(99)
    assert cfg_after["sensitive_files"] == config_service.DEFAULT_SENSITIVE_FILES


# ---------------------------------------------------------------------------
# Admin-API (Commit 6)
# ---------------------------------------------------------------------------

def test_api_get_returns_defaults_without_row(fake_db):
    from app import app
    client = app.test_client()
    resp = client.get("/api/agent-projects/123/config")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["project_id"] == 123
    assert body["sensitive_files"] == config_service.DEFAULT_SENSITIVE_FILES
    assert body["handoff_path_relative"] == config_service.DEFAULT_HANDOFF_PATH_RELATIVE


def test_api_put_stores_fields_and_get_returns_them(fake_db):
    from app import app
    client = app.test_client()
    resp = client.put(
        "/api/agent-projects/123/config",
        json={
            "sensitive_files": ["foo.md", "bar.md"],
            "docs_paths": ["docs/"],
        },
    )
    assert resp.status_code == 200, resp.data
    body = resp.get_json()
    assert body["sensitive_files"] == ["foo.md", "bar.md"]
    assert body["docs_paths"] == ["docs/"]

    get_resp = client.get("/api/agent-projects/123/config")
    assert get_resp.status_code == 200
    get_body = get_resp.get_json()
    assert get_body["sensitive_files"] == ["foo.md", "bar.md"]
    assert get_body["docs_paths"] == ["docs/"]
    # Nicht gesetzte Felder fallen auf Default zurueck.
    assert get_body["append_only_block_start_regex"] == config_service.DEFAULT_BLOCK_START_REGEX


def test_api_put_rejects_unknown_field(fake_db):
    from app import app
    client = app.test_client()
    resp = client.put(
        "/api/agent-projects/123/config",
        json={"foo": "bar"},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "foo" in body["error"]
