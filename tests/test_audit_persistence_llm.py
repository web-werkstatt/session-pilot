"""
SPEC-AUDIT-PERSISTENCE-LLM-001: Tests fuer LLM Evidence Round-Trip Persistence.
DB-Zugriffe vollstaendig gemockt via monkeypatch auf db_service.execute.
"""
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

from audit.models import (
    AuditResponse,
    AuditResult,
    OverallStatus,
    RequirementStatus,
)
from audit.repository import (
    save_audit_response,
    load_audit_results,
    _to_json,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_response_with_llm_review():
    """AuditResponse mit llm_review und llm_review_error Evidence."""
    return AuditResponse(
        spec_id="TEST-PERSIST-001",
        spec_title="Persistence Test",
        overall_status=OverallStatus.PASS,
        started_at=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 1, 10, 0, 5, tzinfo=timezone.utc),
        input_facts={"changed_files": ["services/db_service.py"]},
        results=[
            AuditResult(
                requirement_key="R1",
                status=RequirementStatus.ERFUELLT,
                notes="Regelbasiert ERFUELLT",
                evidence={
                    "matched_areas": ["services/db_service.py"],
                    "llm_review": {
                        "opinion": "confirm",
                        "comment": "Dateien decken Requirement ab",
                        "model": "perplexity/sonar",
                        "created_at": "2026-04-01T10:00:03+00:00",
                        "analyzer_version": "0.1.0",
                    },
                },
            ),
            AuditResult(
                requirement_key="R2",
                status=RequirementStatus.TEILWEISE,
                evidence={
                    "matched_areas": ["tests/"],
                    "llm_review_error": {
                        "code": "connector_error",
                        "message": "Timeout",
                        "status_code": None,
                    },
                },
            ),
        ],
    )


def _make_response_without_evidence():
    """AuditResponse ohne evidence."""
    return AuditResponse(
        spec_id="TEST-PERSIST-002",
        spec_title="No Evidence Test",
        overall_status=OverallStatus.PASS,
        started_at=datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 1, 10, 0, 1, tzinfo=timezone.utc),
        input_facts={},
        results=[
            AuditResult(
                requirement_key="R1",
                status=RequirementStatus.ERFUELLT,
                evidence=None,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Evidence Shape: llm_review
# ---------------------------------------------------------------------------

class TestLlmReviewShape:

    def test_required_fields_present(self):
        """llm_review muss mindestens opinion und comment haben."""
        resp = _make_response_with_llm_review()
        review = resp.results[0].evidence["llm_review"]
        assert "opinion" in review
        assert "comment" in review

    def test_opinion_valid_value(self):
        resp = _make_response_with_llm_review()
        review = resp.results[0].evidence["llm_review"]
        assert review["opinion"] in {"confirm", "strengthen", "question", "unknown"}

    def test_optional_fields(self):
        resp = _make_response_with_llm_review()
        review = resp.results[0].evidence["llm_review"]
        assert "model" in review
        assert "created_at" in review
        assert "analyzer_version" in review


# ---------------------------------------------------------------------------
# Evidence Shape: llm_review_error
# ---------------------------------------------------------------------------

class TestLlmReviewErrorShape:

    def test_required_fields_present(self):
        """llm_review_error muss mindestens code und message haben."""
        resp = _make_response_with_llm_review()
        error = resp.results[1].evidence["llm_review_error"]
        assert "code" in error
        assert "message" in error

    def test_code_valid_value(self):
        resp = _make_response_with_llm_review()
        error = resp.results[1].evidence["llm_review_error"]
        assert error["code"] in {"connector_error", "timeout", "invalid_response", "disabled_by_gate"}


# ---------------------------------------------------------------------------
# Stable Key Names (R1)
# ---------------------------------------------------------------------------

class TestStableKeyNames:

    def test_keys_exactly_named(self):
        """Evidence verwendet genau llm_review und llm_review_error."""
        resp = _make_response_with_llm_review()
        r1_keys = set(resp.results[0].evidence.keys())
        assert "llm_review" in r1_keys

        r2_keys = set(resp.results[1].evidence.keys())
        assert "llm_review_error" in r2_keys


# ---------------------------------------------------------------------------
# Round-Trip Persistence (R4) - Mocked DB
# ---------------------------------------------------------------------------

class TestRoundTripPersistence:

    def test_save_preserves_evidence_shape(self):
        """save_audit_response sendet evidence als unveraendertes JSONB."""
        resp = _make_response_with_llm_review()
        saved_evidence = []

        original_execute = None

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if "INSERT INTO audit_results" in sql and params:
                # params[4] ist das evidence JSON
                saved_evidence.append(params[4])
            if "INSERT INTO audit_runs" in sql:
                return {"id": 42}
            return None

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                save_audit_response(resp)

        assert len(saved_evidence) == 2

        # R1 hat llm_review
        r1_evidence = json.loads(saved_evidence[0])
        assert "llm_review" in r1_evidence
        assert r1_evidence["llm_review"]["opinion"] == "confirm"
        assert r1_evidence["llm_review"]["model"] == "perplexity/sonar"

        # R2 hat llm_review_error
        r2_evidence = json.loads(saved_evidence[1])
        assert "llm_review_error" in r2_evidence
        assert r2_evidence["llm_review_error"]["code"] == "connector_error"

    def test_load_restores_evidence_shape(self):
        """load_audit_results gibt evidence mit llm_* Keys zurueck."""
        stored_rows = [
            {
                "requirement_key": "R1",
                "status": "ERFÜLLT",
                "notes": "ok",
                "evidence": {
                    "matched_areas": ["services/db_service.py"],
                    "llm_review": {
                        "opinion": "confirm",
                        "comment": "Passt",
                        "model": "sonar",
                        "created_at": "2026-04-01T10:00:03+00:00",
                        "analyzer_version": "0.1.0",
                    },
                },
            },
            {
                "requirement_key": "R2",
                "status": "TEILWEISE ERFÜLLT",
                "notes": None,
                "evidence": {
                    "llm_review_error": {
                        "code": "timeout",
                        "message": "Request timed out",
                    },
                },
            },
        ]

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if fetch:
                return stored_rows
            return None

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                results = load_audit_results(42)

        assert len(results) == 2

        # R1 llm_review intakt
        assert results[0].evidence["llm_review"]["opinion"] == "confirm"
        assert results[0].evidence["llm_review"]["model"] == "sonar"
        assert results[0].evidence["llm_review"]["analyzer_version"] == "0.1.0"

        # R2 llm_review_error intakt
        assert results[1].evidence["llm_review_error"]["code"] == "timeout"
        assert results[1].evidence["llm_review_error"]["message"] == "Request timed out"

    def test_full_round_trip(self):
        """Save + Load ergibt identische Evidence-Struktur."""
        original_evidence = {
            "matched_areas": ["audit/models.py"],
            "llm_review": {
                "opinion": "strengthen",
                "comment": "Mehr als erwartet",
                "model": "sonar",
                "created_at": "2026-04-01T12:00:00+00:00",
                "analyzer_version": "0.1.0",
            },
        }

        captured_json = {}

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if "INSERT INTO audit_runs" in sql:
                return {"id": 99}
            if "INSERT INTO audit_results" in sql and params:
                captured_json["saved"] = params[4]
            if fetch:
                # Simuliert Laden: parsed das gespeicherte JSON zurueck
                saved = json.loads(captured_json.get("saved", "null"))
                return [{
                    "requirement_key": "R1",
                    "status": "ERFÜLLT",
                    "notes": None,
                    "evidence": saved,
                }]
            return None

        resp = AuditResponse(
            spec_id="RT-001",
            overall_status=OverallStatus.PASS,
            started_at=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
            results=[
                AuditResult(
                    requirement_key="R1",
                    status=RequirementStatus.ERFUELLT,
                    evidence=original_evidence,
                ),
            ],
        )

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                save_audit_response(resp)
                loaded = load_audit_results(99)

        assert loaded[0].evidence == original_evidence


# ---------------------------------------------------------------------------
# Backwards Compatibility (R6)
# ---------------------------------------------------------------------------

class TestBackwardsCompatibility:

    def test_load_without_llm_keys(self):
        """Bestehende Rows ohne llm_* Keys laden ohne Fehler."""
        stored_rows = [
            {
                "requirement_key": "R1",
                "status": "ERFÜLLT",
                "notes": None,
                "evidence": {"matched_areas": ["services/db_service.py"]},
            },
        ]

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if fetch:
                return stored_rows
            return None

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                results = load_audit_results(1)

        assert len(results) == 1
        assert "llm_review" not in results[0].evidence
        assert "llm_review_error" not in results[0].evidence

    def test_load_with_null_evidence(self):
        """Rows mit evidence=NULL laden als None."""
        stored_rows = [
            {
                "requirement_key": "R1",
                "status": "ERFÜLLT",
                "notes": None,
                "evidence": None,
            },
        ]

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if fetch:
                return stored_rows
            return None

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                results = load_audit_results(1)

        assert results[0].evidence is None


# ---------------------------------------------------------------------------
# No Double-Writing (R5): Analyzer sets, repository persists as-is
# ---------------------------------------------------------------------------

class TestNoDoubleWriting:

    def test_save_does_not_add_llm_keys(self):
        """Repository fuegt keine llm_* Keys hinzu wenn sie nicht in evidence sind."""
        resp = _make_response_without_evidence()
        saved_evidence = []

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if "INSERT INTO audit_results" in sql and params:
                saved_evidence.append(params[4])
            if "INSERT INTO audit_runs" in sql:
                return {"id": 1}
            return None

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                save_audit_response(resp)

        # evidence war None -> None in DB
        assert saved_evidence[0] is None

    def test_remove_error_persists(self):
        """Wenn llm_review_error aus evidence entfernt und gesaved wird, fehlt es auch nach Load."""
        evidence_with_error = {
            "llm_review_error": {"code": "timeout", "message": "slow"},
        }
        evidence_without_error = {
            "llm_review": {"opinion": "confirm", "comment": "ok"},
        }

        saved_jsons = []

        def mock_execute(sql, params=None, fetch=False, fetchone=False):
            if "INSERT INTO audit_results" in sql and params:
                saved_jsons.append(params[4])
            if "INSERT INTO audit_runs" in sql:
                return {"id": 1}
            return None

        # Erst mit error speichern
        resp1 = AuditResponse(
            spec_id="REM-001",
            overall_status=OverallStatus.PASS,
            started_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            results=[AuditResult(
                requirement_key="R1",
                status=RequirementStatus.ERFUELLT,
                evidence=evidence_with_error,
            )],
        )

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                save_audit_response(resp1)

        j1 = json.loads(saved_jsons[0])
        assert "llm_review_error" in j1

        # Dann ohne error speichern
        saved_jsons.clear()
        resp2 = AuditResponse(
            spec_id="REM-001",
            overall_status=OverallStatus.PASS,
            started_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            results=[AuditResult(
                requirement_key="R1",
                status=RequirementStatus.ERFUELLT,
                evidence=evidence_without_error,
            )],
        )

        with patch("audit.repository.execute", side_effect=mock_execute):
            with patch("audit.repository.ensure_audit_schema"):
                save_audit_response(resp2)

        j2 = json.loads(saved_jsons[0])
        assert "llm_review_error" not in j2
        assert "llm_review" in j2
