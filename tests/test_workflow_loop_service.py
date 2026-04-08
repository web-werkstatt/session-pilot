from services.copilot_marker_format import Marker
from services.workflow_loop_service import build_workflow_loop_data


def test_build_workflow_loop_data_with_active_and_pending_rating(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    markers = [
        Marker(
            marker_id="MK-1",
            titel="Aktiver Marker",
            plan_id="42",
            status="in_progress",
            ziel="Ziel A",
            naechster_schritt="Thread fortsetzen",
            prompt="Prompt",
            checks=["Check A"],
            last_session="ses-1",
            updated_at="2026-04-08T10:00:00+00:00",
            risiko="Governance: yellow",
        ),
        Marker(
            marker_id="MK-2",
            titel="Done ohne Rating",
            plan_id="42",
            status="done",
            ziel="Ziel B",
            naechster_schritt="Rating nachholen",
            prompt="Prompt",
            checks=["Check B"],
            updated_at="2026-04-08T11:00:00+00:00",
        ),
        Marker(
            marker_id="MK-3",
            titel="Naechster Marker",
            plan_id="99",
            status="todo",
            ziel="Ziel C",
            naechster_schritt="Starten",
            prompt="",
            checks=[],
            updated_at="2026-04-08T09:00:00+00:00",
            risiko="Quality: kritisch",
        ),
    ]

    monkeypatch.setattr("services.workflow_loop_service.resolve_project_path", lambda name: str(project_dir))
    monkeypatch.setattr("services.workflow_loop_service._load_markers_with_regeneration", lambda project: markers)
    monkeypatch.setattr(
        "services.workflow_loop_service.execute",
        lambda query, params=None, fetch=False, fetchone=False: [
            {"id": 42, "title": "Plan 42"},
            {"id": 99, "title": "Plan 99"},
        ],
    )
    monkeypatch.setattr(
        "services.workflow_loop_service.get_governance_gate",
        lambda project: {
            "status": "yellow",
            "quality_summary": {"score_numeric": 35},
            "audit_summary": {"overall_status": "FAIL"},
        },
    )

    data = build_workflow_loop_data("demo")

    assert data["project_id"] == "demo"
    assert data["current_step"] == "rating"
    assert len(data["steps"]) == 5
    assert data["current_marker"]["marker_id"] == "MK-1"
    assert data["current_marker"]["plan_title"] == "Plan 42"
    assert data["next_marker"]["marker_id"] == "MK-3"
    assert data["next_marker"]["gate_status"] == "blocked"
    assert data["pending_ratings"][0]["status_label"] == "Abschluss unvollstaendig"
    assert any(item["label"] == "Governance-Risiko" for item in data["signals"]["priority_hints"])
    assert any(item["hint"] == "Quality-kritisch" for item in data["signals"]["priority_hints"])


def test_build_workflow_loop_data_without_markers(monkeypatch, tmp_path):
    project_dir = tmp_path / "empty"
    project_dir.mkdir()

    monkeypatch.setattr("services.workflow_loop_service.resolve_project_path", lambda name: str(project_dir))
    monkeypatch.setattr("services.workflow_loop_service._load_markers_with_regeneration", lambda project: [])
    monkeypatch.setattr("services.workflow_loop_service.execute", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "services.workflow_loop_service.get_governance_gate",
        lambda project: {
            "status": "green",
            "quality_summary": {"score_numeric": 88},
            "audit_summary": {"overall_status": "PASS"},
        },
    )

    data = build_workflow_loop_data("empty")

    assert data["current_marker"] == {}
    assert data["next_marker"] == {}
    assert data["pending_ratings"] == []
    assert data["current_step"] == "gate_ready"
    assert len(data["steps"]) == 5
