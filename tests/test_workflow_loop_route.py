def test_project_workflow_loop_route_success(client, monkeypatch):
    monkeypatch.setattr(
        "routes.project_routes.build_workflow_loop_data",
        lambda name: {
            "project_id": name,
            "project_label": name,
            "current_step": "execution",
            "steps": [
                {"id": "gate_ready", "label": "Gate Ready", "number": 1, "status": "done", "attention_level": "none", "cta_label": "Marker pruefen", "marker_ref": "MK-1"},
                {"id": "active", "label": "Aktiv", "number": 2, "status": "done", "attention_level": "none", "cta_label": "Execution oeffnen", "marker_ref": "MK-1"},
                {"id": "execution", "label": "Execution", "number": 3, "status": "active", "attention_level": "medium", "cta_label": "Thread fortsetzen", "marker_ref": "MK-1"},
                {"id": "write_back", "label": "Write Back", "number": 4, "status": "pending", "attention_level": "none", "cta_label": "Abschluss vorbereiten", "marker_ref": "MK-1"},
                {"id": "rating", "label": "Rating", "number": 5, "status": "pending", "attention_level": "none", "cta_label": "Rating nachholen", "marker_ref": "MK-1"},
            ],
            "current_marker": {"marker_id": "MK-1"},
            "next_marker": {},
            "signals": {"governance_status": "yellow", "audit_status": "partial", "quality_score": 71, "priority_hints": []},
            "pending_ratings": [],
        },
    )

    response = client.get("/api/project/demo/workflow-loop")
    assert response.status_code == 200
    data = response.get_json()
    assert data["project_id"] == "demo"
    assert data["current_step"] == "execution"
    assert len(data["steps"]) == 5


def test_project_workflow_loop_route_404(client, monkeypatch):
    monkeypatch.setattr(
        "routes.project_routes.build_workflow_loop_data",
        lambda name: (_ for _ in ()).throw(FileNotFoundError(name)),
    )

    response = client.get("/api/project/missing/workflow-loop")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Project not found"
