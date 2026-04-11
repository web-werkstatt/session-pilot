"""
Tests fuer ADR-002 Stufe 1b: Policy-REST-Endpoints.

Patcht die Policy-Service-Aufrufe direkt im Route-Modul, damit keine
echte DB oder Perplexity-API gebraucht wird.
"""
import pytest


@pytest.fixture
def patched_policy_routes(monkeypatch):
    """Patcht alle Service-Calls im routes.policy_routes Modul."""
    import routes.policy_routes as routes_mod

    state = {
        "roles": [
            {"role_id": "programming", "name": "Programming", "active": True},
            {"role_id": "ux_ui", "name": "UX/UI", "active": True},
        ],
        "tool_profiles": [
            {"tool_id": "claude-opus", "cli": "claude-code", "active": True},
        ],
        "policies": [
            {
                "policy_id": 1,
                "role_id": "programming",
                "tool_id": "claude-opus",
                "rank": 1,
                "confidence": 80,
                "source": "manual",
                "approved_by": "joseph",
            }
        ],
        "suggestions": [
            {
                "suggestion_id": 10,
                "reviewer_tool": "perplexity",
                "suggestion_type": "new_policy",
                "payload": {"role_id": "ux_ui", "tool_id": "claude-opus"},
                "status": "pending",
            }
        ],
        "applied": {},
        "rejected": {},
        "review_result": None,
        "seed_result": None,
    }

    def fake_list_roles(include_inactive=False):
        if include_inactive:
            return list(state["roles"])
        return [r for r in state["roles"] if r["active"]]

    def fake_list_tool_profiles(include_inactive=False):
        if include_inactive:
            return list(state["tool_profiles"])
        return [p for p in state["tool_profiles"] if p["active"]]

    def fake_get_active_policies(role_id=None):
        if role_id:
            return [p for p in state["policies"] if p["role_id"] == role_id]
        return list(state["policies"])

    def fake_list_pending():
        return [s for s in state["suggestions"] if s["status"] == "pending"]

    def fake_review_policies():
        state["review_result"] = {
            "schema_version": 1,
            "summary": "ok",
            "suggestions": [],
            "error": None,
        }
        return state["review_result"]

    def fake_apply_suggestion(sid, decided_by):
        state["applied"][sid] = decided_by
        for s in state["suggestions"]:
            if s["suggestion_id"] == sid:
                s["status"] = "applied"
        return 42  # fake policy_id

    def fake_reject_suggestion(sid, decided_by, reason=None):
        state["rejected"][sid] = (decided_by, reason)
        for s in state["suggestions"]:
            if s["suggestion_id"] == sid:
                s["status"] = "rejected"
        return True

    monkeypatch.setattr(routes_mod, "list_roles", fake_list_roles)
    monkeypatch.setattr(routes_mod, "list_tool_profiles", fake_list_tool_profiles)
    monkeypatch.setattr(routes_mod, "get_active_policies", fake_get_active_policies)
    monkeypatch.setattr(routes_mod, "list_pending_suggestions", fake_list_pending)
    monkeypatch.setattr(routes_mod, "review_policies", fake_review_policies)
    monkeypatch.setattr(routes_mod, "apply_suggestion", fake_apply_suggestion)
    monkeypatch.setattr(routes_mod, "reject_suggestion", fake_reject_suggestion)

    # seed_defaults wird lazy importiert - direkt in services.policy_seed patchen
    import services.policy_seed as seed_mod

    def fake_seed_defaults():
        state["seed_result"] = {"roles_created": 6, "tool_profiles_created": 5}
        return state["seed_result"]

    monkeypatch.setattr(seed_mod, "seed_defaults", fake_seed_defaults)

    return state


# ---------------------------------------------------------------------------
# Read-Endpoints
# ---------------------------------------------------------------------------

def test_get_roles(client, patched_policy_routes):
    resp = client.get("/api/policies/roles")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["roles"]) == 2
    assert data["roles"][0]["role_id"] == "programming"


def test_get_tool_profiles(client, patched_policy_routes):
    resp = client.get("/api/policies/tool-profiles")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["tool_profiles"]) == 1


def test_get_assignments_all(client, patched_policy_routes):
    resp = client.get("/api/policies/assignments")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["policies"]) == 1


def test_get_assignments_filtered_by_role(client, patched_policy_routes):
    resp = client.get("/api/policies/assignments?role_id=programming")
    assert resp.status_code == 200
    data = resp.get_json()
    assert all(p["role_id"] == "programming" for p in data["policies"])


def test_get_assignments_filtered_no_match(client, patched_policy_routes):
    resp = client.get("/api/policies/assignments?role_id=ux_ui")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["policies"] == []


def test_get_suggestions_pending(client, patched_policy_routes):
    resp = client.get("/api/policies/suggestions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["suggestions"]) == 1
    assert data["suggestions"][0]["suggestion_id"] == 10


def test_get_suggestions_unsupported_status(client, patched_policy_routes):
    resp = client.get("/api/policies/suggestions?status=applied")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "status_unsupported"


# ---------------------------------------------------------------------------
# Write-Endpoints
# ---------------------------------------------------------------------------

def test_trigger_review(client, patched_policy_routes):
    resp = client.post("/api/policies/review")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["error"] is None
    assert data["summary"] == "ok"


def test_approve_suggestion(client, patched_policy_routes):
    resp = client.post("/api/policies/suggestions/10/approve")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["suggestion_id"] == 10
    assert data["applied_policy_id"] == 42
    assert data["decided_by"] == "joseph"
    assert patched_policy_routes["applied"][10] == "joseph"


def test_approve_suggestion_with_custom_decided_by(client, patched_policy_routes):
    resp = client.post(
        "/api/policies/suggestions/10/approve",
        json={"decided_by": "admin"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["decided_by"] == "admin"


def test_reject_suggestion(client, patched_policy_routes):
    resp = client.post(
        "/api/policies/suggestions/10/reject",
        json={"reason": "not fitting"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "rejected"
    assert patched_policy_routes["rejected"][10] == ("joseph", "not fitting")


def test_seed_defaults_endpoint(client, patched_policy_routes):
    resp = client.post("/api/policies/seed-defaults")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["roles_created"] == 6
    assert data["tool_profiles_created"] == 5
