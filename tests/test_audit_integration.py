"""
SPEC-AUDIT-INTEGRATION-V1-001: Abnahmetests fuer Audit-API-Endpoints.
Deckt R1 (POST success), R2 (GET run_id), R3 (GET latest), R4 (llm evidence),
R6 (error mapping) und einen 404-Fall ab.
"""
import json
import pytest
from datetime import datetime, timezone

from app import app as flask_app
from audit.models import (
    AuditResponse, AuditResult, RequirementStatus, OverallStatus,
    Spec, Requirement, Priority,
)
from audit.repository import save_spec, save_audit_response


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def seeded_spec():
    """Legt eine Spec in der DB an und gibt spec_id zurueck."""
    spec = Spec(
        spec_id="SPEC-INTEG-TEST",
        title="Integration Test Spec",
        requirements=[
            Requirement(key="R1", title="Req 1", priority=Priority.MUST,
                        affected_areas=["audit/service.py"]),
            Requirement(key="R2", title="Req 2", priority=Priority.SHOULD,
                        affected_areas=["audit/rules.py"]),
        ],
    )
    save_spec(spec)
    return spec.spec_id


@pytest.fixture
def seeded_run_with_llm():
    """Persistiert einen Run mit llm_review und llm_review_error."""
    response = AuditResponse(
        spec_id="SPEC-LLM-INTEG",
        spec_title="LLM Integration Test",
        overall_status=OverallStatus.PARTIAL,
        started_at=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 1, 10, 0, 2, tzinfo=timezone.utc),
        input_facts={"changed_files": ["a.py"]},
        results=[
            AuditResult(
                requirement_key="R1",
                status=RequirementStatus.ERFUELLT,
                notes="OK",
                evidence={
                    "matched_areas": ["a.py"],
                    "unmatched_areas": [],
                    "coverage": 1.0,
                    "llm_review": {
                        "opinion": "confirm",
                        "comment": "Passt",
                        "model": "sonar",
                        "created_at": "2026-04-01T10:00:01Z",
                        "analyzer_version": "0.1.0",
                    },
                },
            ),
            AuditResult(
                requirement_key="R2",
                status=RequirementStatus.UNSICHER,
                notes="LLM Error",
                evidence={
                    "matched_areas": [],
                    "unmatched_areas": ["b.py"],
                    "coverage": 0.0,
                    "llm_review_error": {
                        "code": "timeout",
                        "message": "30s exceeded",
                    },
                },
            ),
        ],
    )
    run_id = save_audit_response(response)
    return run_id, response


# --- R1: POST /api/audits/run success ---

class TestPostRun:
    def test_success(self, client, seeded_spec):
        r = client.post("/api/audits/run",
            data=json.dumps({
                "spec_id": seeded_spec,
                "input_facts": {"changed_files": ["audit/service.py"]},
            }),
            content_type="application/json")

        assert r.status_code == 200
        d = r.get_json()

        # Alle Pflichtfelder vorhanden
        for key in ("spec_id", "spec_title", "overall_status", "started_at",
                     "finished_at", "duration_ms", "summary", "input_facts",
                     "results", "run_id"):
            assert key in d, f"Feld '{key}' fehlt in Response"

        assert d["spec_id"] == seeded_spec
        assert isinstance(d["results"], list)
        assert len(d["results"]) == 2
        assert d["duration_ms"] >= 0
        assert isinstance(d["run_id"], int)

    def test_invalid_request_400(self, client):
        r = client.post("/api/audits/run",
            data=json.dumps({"spec_id": "", "input_facts": {}}),
            content_type="application/json")
        assert r.status_code == 400

    def test_not_found_404(self, client):
        r = client.post("/api/audits/run",
            data=json.dumps({"spec_id": "NONEXISTENT", "input_facts": {}}),
            content_type="application/json")
        assert r.status_code == 404

    def test_unrunnable_422(self, client):
        # Spec ohne Requirements -> ValueError -> 422
        save_spec(Spec(spec_id="SPEC-EMPTY", title="Empty", requirements=[]))
        r = client.post("/api/audits/run",
            data=json.dumps({"spec_id": "SPEC-EMPTY", "input_facts": {}}),
            content_type="application/json")
        assert r.status_code == 422


# --- R2: GET /api/audits/<run_id> ---

class TestGetByRunId:
    def test_success(self, client, seeded_run_with_llm):
        run_id, original = seeded_run_with_llm
        r = client.get(f"/api/audits/{run_id}")

        assert r.status_code == 200
        d = r.get_json()
        assert d["run_id"] == run_id
        assert d["overall_status"] == "PARTIAL"
        assert len(d["results"]) == 2

    def test_not_found_404(self, client):
        r = client.get("/api/audits/999999")
        assert r.status_code == 404


# --- R3: GET /api/audits/spec/<spec_id>/latest ---

class TestGetLatest:
    def test_success(self, client, seeded_spec):
        # Erst einen Run erzeugen
        client.post("/api/audits/run",
            data=json.dumps({
                "spec_id": seeded_spec,
                "input_facts": {"changed_files": []},
            }),
            content_type="application/json")

        r = client.get(f"/api/audits/spec/{seeded_spec}/latest")
        assert r.status_code == 200
        d = r.get_json()
        assert d["spec_id"] == seeded_spec
        assert "results" in d
        assert "spec_title" in d

    def test_not_found_404(self, client):
        r = client.get("/api/audits/spec/NONEXISTENT-999/latest")
        assert r.status_code == 404


# --- R4: llm_review / llm_review_error roundtrip ---

class TestLlmEvidenceRoundtrip:
    def test_llm_review_unchanged(self, client, seeded_run_with_llm):
        run_id, original = seeded_run_with_llm
        r = client.get(f"/api/audits/{run_id}")
        d = r.get_json()

        api_evidence = d["results"][0]["evidence"]
        orig_evidence = original.results[0].evidence

        assert "llm_review" in api_evidence
        assert api_evidence["llm_review"] == orig_evidence["llm_review"]

    def test_llm_review_error_unchanged(self, client, seeded_run_with_llm):
        run_id, original = seeded_run_with_llm
        r = client.get(f"/api/audits/{run_id}")
        d = r.get_json()

        api_evidence = d["results"][1]["evidence"]
        orig_evidence = original.results[1].evidence

        assert "llm_review_error" in api_evidence
        assert api_evidence["llm_review_error"] == orig_evidence["llm_review_error"]
