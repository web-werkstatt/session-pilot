"""
Tests fuer ADR-001 Prio 5: Write-Back Core -> handoff.md (Mirror).

Prueft:
- write_handoff_mirror serialisiert DB-Marker in valide handoff.md
- Schreiboperationen laufen ueber write_guard (SOURCE_ALLOWLIST)
- Idempotenz: zweiter Aufruf ohne DB-Aenderung erzeugt keinen Diff
- update_marker_field / update_marker_state triggern den Mirror
- Mirror-Fehler brechen die DB-Operation nicht ab
"""
import os

import pytest

from services import workflow_core_service
from services.copilot_marker_format import Marker, parse_markers


def _fake_marker(
    marker_id="001",
    titel="Test-Marker",
    plan_id="42",
    status="todo",
    prompt="Prompt gesetzt",
    checks=None,
):
    return Marker(
        marker_id=marker_id,
        titel=titel,
        plan_id=plan_id,
        status=status,
        ziel="Ziel definiert",
        naechster_schritt="Naechster Schritt",
        prompt=prompt,
        checks=list(checks or ["Check eins"]),
        updated_at="2026-04-10T10:00:00+00:00",
    )


@pytest.fixture
def mirror_fixture(tmp_path, monkeypatch):
    """Isoliertes Projekt-Verzeichnis + In-Memory-DB fuer Mirror-Tests."""
    projects_dir = tmp_path
    project_name = "demo_mirror"
    project_root = projects_dir / project_name
    project_root.mkdir()

    # PROJECTS_DIR patchen, damit Mirror im tmp-Dir landet
    monkeypatch.setattr(workflow_core_service, "PROJECTS_DIR", str(projects_dir))
    monkeypatch.setattr(
        workflow_core_service,
        "resolve_project_path",
        lambda name: str(project_root) if name == project_name else None,
    )

    # In-Memory-Store fuer Marker
    db_markers = {}

    def fake_execute(sql, params=None, fetch=False, fetchone=False):
        q = " ".join(str(sql).lower().split())
        params = params or ()

        if "select * from markers where project_name = %s and marker_id = %s" in q:
            key = (params[0], params[1])
            row = db_markers.get(key)
            return dict(row) if row else None

        if "select * from markers" in q and "where project_name = %s and plan_id = %s" in q:
            proj = params[0]
            pid = params[1]
            rows = [
                dict(v)
                for (p, _), v in db_markers.items()
                if p == proj and str(v.get("plan_id")) == str(pid)
            ]
            return rows if fetch else (rows[0] if rows else None)

        if "select * from markers" in q and "where project_name = %s" in q:
            proj = params[0]
            rows = [dict(v) for (p, _), v in db_markers.items() if p == proj]
            return rows if fetch else (rows[0] if rows else None)

        if "update markers set" in q and "where project_name = %s and marker_id = %s" in q:
            key = (params[-2], params[-1])
            row = db_markers.get(key)
            if not row:
                return None
            # Grobes Parsing der SET-Klausel
            set_clause = q.split("update markers set", 1)[1].split("where", 1)[0]
            parts = [p.strip() for p in set_clause.split(",")]
            value_params = params[: -2]
            vi = 0
            for part in parts:
                name = part.split("=", 1)[0].strip()
                if "now()" in part:
                    continue
                if vi < len(value_params):
                    row[name] = value_params[vi]
                    vi += 1
            return None

        return None if fetchone else ([] if fetch else None)

    monkeypatch.setattr(workflow_core_service, "execute", fake_execute)
    monkeypatch.setattr(workflow_core_service, "ensure_marker_schema", lambda: None)
    monkeypatch.setattr(workflow_core_service, "sync_marker_to_workflow", lambda *a, **k: None)
    monkeypatch.setattr(workflow_core_service, "get_workflow_state", lambda *a, **k: None)
    monkeypatch.setattr(
        workflow_core_service,
        "import_markers_from_handoff",
        lambda *a, **k: {"created": 0, "updated": 0, "skipped": 0, "errors": []},
    )

    def seed(marker, project=project_name):
        key = (project, marker.marker_id)
        db_markers[key] = {
            "marker_id": marker.marker_id,
            "titel": marker.titel,
            "plan_id": marker.plan_id,
            "status": marker.status,
            "ziel": marker.ziel,
            "naechster_schritt": marker.naechster_schritt,
            "prompt": marker.prompt,
            "prompt_suggestion": marker.prompt_suggestion,
            "risiko": marker.risiko,
            "checks": list(marker.checks),
            "last_session": marker.last_session,
            "updated_at": marker.updated_at,
            "execution_score": marker.execution_score,
            "execution_comment": marker.execution_comment,
            "last_execution_at": marker.last_execution_at,
            "sprint_tag": marker.sprint_tag,
            "spec_tag": marker.spec_tag,
            "sprint_plan_id": marker.sprint_plan_id,
            "spec_id": marker.spec_id,
        }

    return {
        "project_name": project_name,
        "project_root": project_root,
        "handoff_path": project_root / "handoff.md",
        "db_markers": db_markers,
        "seed": seed,
    }


class TestWriteHandoffMirror:
    def test_empty_project_writes_stub_handoff(self, mirror_fixture):
        project = mirror_fixture["project_name"]
        handoff = mirror_fixture["handoff_path"]

        filepath, markdown = workflow_core_service.write_handoff_mirror(project)

        assert filepath == str(handoff)
        assert handoff.exists()
        assert 'state_format: "copilot_markers_v1"' in markdown
        assert "noch keine Marker vorhanden" in markdown
        assert parse_markers(str(handoff)) == []

    def test_writes_markers_from_db(self, mirror_fixture):
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="m1", titel="Alpha", plan_id="10"))
        mirror_fixture["seed"](_fake_marker(marker_id="m2", titel="Beta", plan_id="20"))

        filepath, markdown = workflow_core_service.write_handoff_mirror(project)

        assert filepath is not None
        assert markdown is not None
        assert "Alpha" in markdown
        assert "Beta" in markdown
        parsed = parse_markers(filepath)
        assert {m.marker_id for m in parsed} == {"m1", "m2"}
        assert "## Copilot Markers" in markdown

    def test_preserves_existing_preamble(self, mirror_fixture):
        """Manueller Preamble oberhalb von ## Copilot Markers bleibt erhalten."""
        project = mirror_fixture["project_name"]
        handoff = mirror_fixture["handoff_path"]
        custom_preamble = (
            "---\n"
            'handoff:\n'
            '  project_id: "demo_mirror"\n'
            '  state_format: "copilot_markers_v1"\n'
            '  stage: "custom-stage"\n'
            '  scope: "4711 Plan(s) fuer demo_mirror"\n'
            "---\n"
            "\n"
            "# Custom Handoff Titel\n"
            "\n"
            "Eigene Einleitung die bleiben muss.\n"
            "\n"
            "## Copilot Markers\n"
        )
        handoff.write_text(custom_preamble, encoding="utf-8")
        mirror_fixture["seed"](_fake_marker(marker_id="m1", titel="Alpha"))

        _, markdown = workflow_core_service.write_handoff_mirror(project)

        assert markdown is not None
        assert 'stage: "custom-stage"' in markdown
        assert 'scope: "4711 Plan(s) fuer demo_mirror"' in markdown
        assert "Custom Handoff Titel" in markdown
        assert "Eigene Einleitung die bleiben muss." in markdown
        # Marker wird darunter eingefuegt
        assert "Alpha" in markdown

    def test_idempotent_no_diff_on_second_call(self, mirror_fixture):
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="m1", titel="Idem"))

        _, md1 = workflow_core_service.write_handoff_mirror(project)
        _, md2 = workflow_core_service.write_handoff_mirror(project)

        assert md1 == md2

    def test_deterministic_ordering_by_plan_then_marker(self, mirror_fixture):
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="z", plan_id="99"))
        mirror_fixture["seed"](_fake_marker(marker_id="a", plan_id="10"))
        mirror_fixture["seed"](_fake_marker(marker_id="b", plan_id="10"))

        _, markdown = workflow_core_service.write_handoff_mirror(project)

        pos_a = markdown.find("MARKER:a")
        pos_b = markdown.find("MARKER:b")
        pos_z = markdown.find("MARKER:z")
        assert 0 <= pos_a < pos_b < pos_z

    def test_returns_none_for_unknown_project_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(workflow_core_service, "PROJECTS_DIR", str(tmp_path))
        monkeypatch.setattr(
            workflow_core_service, "resolve_project_path", lambda name: None
        )
        filepath, markdown = workflow_core_service.write_handoff_mirror("no_such_project")
        assert filepath is None
        assert markdown is None


class TestMirrorTrigger:
    def test_update_marker_field_triggers_mirror(self, mirror_fixture):
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="m1", status="todo"))

        workflow_core_service.update_marker_field(project, "m1", status="in_progress")

        assert mirror_fixture["handoff_path"].exists()
        parsed = parse_markers(str(mirror_fixture["handoff_path"]))
        assert len(parsed) == 1
        assert parsed[0].status == "in_progress"

    def test_update_marker_state_triggers_mirror(self, mirror_fixture):
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="m1", status="todo"))

        workflow_core_service.update_marker_state(project, "m1", "in_progress")

        assert mirror_fixture["handoff_path"].exists()
        parsed = parse_markers(str(mirror_fixture["handoff_path"]))
        assert parsed[0].status == "in_progress"

    def test_mirror_failure_does_not_break_core_write(self, mirror_fixture, monkeypatch):
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="m1"))

        def broken_mirror(_pname):
            raise RuntimeError("mirror kaputt")

        monkeypatch.setattr(workflow_core_service, "write_handoff_mirror", broken_mirror)

        # Sollte NICHT propagieren
        result = workflow_core_service.update_marker_field(project, "m1", prompt="neuer prompt")
        assert result is not None


class TestWriteGuardIntegration:
    def test_mirror_goes_through_write_guard_source_allowlist(self, mirror_fixture, monkeypatch):
        """Mirror-Write muss die korrekte writer_source verwenden."""
        project = mirror_fixture["project_name"]
        mirror_fixture["seed"](_fake_marker(marker_id="m1"))

        captured = {}
        import services.write_guard as write_guard

        real_safe_write = write_guard.safe_write

        def spy_safe_write(filepath, content, source):
            captured["filepath"] = filepath
            captured["source"] = source
            return real_safe_write(filepath, content, source)

        monkeypatch.setattr(write_guard, "safe_write", spy_safe_write)

        workflow_core_service.write_handoff_mirror(project)

        assert captured["source"] == "workflow_core_service"
        assert captured["filepath"].endswith("/handoff.md")
