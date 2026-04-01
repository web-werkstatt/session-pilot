"""
Sprint C: Abnahmetests fuer Governance Gate (Health-Status).
Deckt Gate-Logik, API-Endpoint und Randfaelle ab.
"""
import json
import os
import pytest
from unittest.mock import patch

from services.governance_service import (
    get_governance_gate,
    GATE_THRESHOLDS,
    _load_quality_summary,
)


# --- Gate-Logik Tests ---

class TestGateLogic:
    """Tests fuer die deterministische green/yellow/red Ableitung."""

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_green_when_all_good(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = {"score_numeric": 85, "score": "B",
                                      "total_issues": 5, "errors": 0, "warnings": 5,
                                      "scanned_at": "2026-04-01T10:00:00Z"}
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "PASS", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "green"
        assert gate["project"] == "test_project"
        assert gate["policy_level"] == "sandbox"
        assert gate["quality_summary"] is not None
        assert gate["audit_summary"] is not None

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_red_when_quality_below_red_threshold(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = {"score_numeric": 20, "score": "F",
                                      "total_issues": 50, "errors": 10, "warnings": 40,
                                      "scanned_at": "2026-04-01T10:00:00Z"}
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "PASS", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "red"
        assert any("unter 40" in r for r in gate["reasons"])

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_yellow_when_quality_between_thresholds(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "controlled"}
        mock_quality.return_value = {"score_numeric": 50, "score": "D",
                                      "total_issues": 20, "errors": 2, "warnings": 18,
                                      "scanned_at": "2026-04-01T10:00:00Z"}
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "PASS", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "yellow"
        assert any("unter 60" in r for r in gate["reasons"])

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_red_when_audit_fail(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = {"score_numeric": 85, "score": "B",
                                      "total_issues": 5, "errors": 0, "warnings": 5,
                                      "scanned_at": "2026-04-01T10:00:00Z"}
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "FAIL", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "red"
        assert any("FAIL" in r for r in gate["reasons"])

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_yellow_when_audit_partial(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = {"score_numeric": 85, "score": "B",
                                      "total_issues": 5, "errors": 0, "warnings": 5,
                                      "scanned_at": "2026-04-01T10:00:00Z"}
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "PARTIAL", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "yellow"
        assert any("PARTIAL" in r for r in gate["reasons"])

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_yellow_when_no_quality_report(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = None
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "PASS", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "yellow"
        assert any("Kein Quality" in r for r in gate["reasons"])

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_yellow_when_no_audit(self, mock_policy, mock_quality, mock_audit):
        mock_policy.return_value = {"level_name": "critical"}
        mock_quality.return_value = {"score_numeric": 85, "score": "B",
                                      "total_issues": 5, "errors": 0, "warnings": 5,
                                      "scanned_at": "2026-04-01T10:00:00Z"}
        mock_audit.return_value = None

        gate = get_governance_gate("test_project")
        assert gate["status"] == "yellow"
        assert gate["policy_level"] == "critical"
        assert any("Kein Audit" in r for r in gate["reasons"])

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_red_trumps_yellow(self, mock_policy, mock_quality, mock_audit):
        """Red (Audit FAIL) + Yellow (kein Quality) = Red."""
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = None  # yellow signal
        mock_audit.return_value = {"run_id": 1, "spec_id": "SPEC-1",
                                    "overall_status": "FAIL", "started_at": "2026-04-01T10:00:00Z"}

        gate = get_governance_gate("test_project")
        assert gate["status"] == "red"
        assert len(gate["reasons"]) >= 2

    @patch("services.governance_service._load_audit_summary")
    @patch("services.governance_service._load_quality_summary")
    @patch("services.governance_service.get_project_policy")
    def test_response_structure(self, mock_policy, mock_quality, mock_audit):
        """Alle Pflichtfelder vorhanden."""
        mock_policy.return_value = {"level_name": "sandbox"}
        mock_quality.return_value = None
        mock_audit.return_value = None

        gate = get_governance_gate("test_project")
        assert "project" in gate
        assert "status" in gate
        assert "reasons" in gate
        assert "policy_level" in gate
        assert "quality_summary" in gate
        assert "audit_summary" in gate
        assert gate["status"] in ("green", "yellow", "red")
        assert isinstance(gate["reasons"], list)


# --- API-Endpoint Tests ---

class TestGateEndpoint:
    @pytest.fixture
    def client(self):
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_gate_returns_200(self, client):
        r = client.get("/api/governance/gate/project_dashboard")
        assert r.status_code == 200
        d = r.get_json()
        assert d["project"] == "project_dashboard"
        assert d["status"] in ("green", "yellow", "red")
        assert isinstance(d["reasons"], list)

    def test_gate_nonexistent_project(self, client):
        """Nicht-existentes Projekt gibt trotzdem 200 mit yellow/reasons."""
        r = client.get("/api/governance/gate/nonexistent_project_xyz")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] in ("yellow", "red")
