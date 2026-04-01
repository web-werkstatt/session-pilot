"""
SPEC-AUDIT-ANALYZER-LLM-001: Tests fuer LLM-basierten Audit-Analyzer.
Perplexity-Connector vollstaendig gemockt.
"""
import pytest
from unittest.mock import patch

from audit.models import (
    AuditResult,
    Priority,
    Requirement,
    RequirementStatus,
    Spec,
)
from audit.analyzers import (
    run_analyzers,
    _parse_llm_response,
    _build_user_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_spec():
    return Spec(
        spec_id="TEST-LLM-001",
        title="Test-Spec fuer LLM Analyzer",
        requirements=[
            Requirement(
                key="R1",
                title="Schema existiert",
                description="DB-Tabelle muss angelegt sein",
                priority=Priority.MUST,
                acceptance_criteria=["CREATE TABLE vorhanden"],
                affected_areas=["services/db_service.py"],
            ),
            Requirement(
                key="R2",
                title="Tests vorhanden",
                priority=Priority.SHOULD,
                affected_areas=["tests/"],
            ),
        ],
    )


def _make_results():
    return [
        AuditResult(
            requirement_key="R1",
            status=RequirementStatus.ERFUELLT,
            evidence={"matched_areas": ["services/db_service.py"]},
        ),
        AuditResult(
            requirement_key="R2",
            status=RequirementStatus.TEILWEISE,
            evidence={"matched_areas": ["tests/"]},
        ),
    ]


CHANGED_FILES = ["services/db_service.py", "tests/test_something.py"]
INPUT_FACTS = {"changed_files": CHANGED_FILES}


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------

class TestParseLlmResponse:

    def test_valid_json(self):
        result = _parse_llm_response('{"opinion": "confirm", "comment": "Passt"}')
        assert result == {"opinion": "confirm", "comment": "Passt"}

    def test_valid_json_in_codeblock(self):
        text = '```json\n{"opinion": "question", "comment": "Unklar"}\n```'
        result = _parse_llm_response(text)
        assert result["opinion"] == "question"

    def test_invalid_opinion_becomes_unknown(self):
        result = _parse_llm_response('{"opinion": "maybe", "comment": "Hmm"}')
        assert result["opinion"] == "unknown"

    def test_missing_comment_gets_default(self):
        result = _parse_llm_response('{"opinion": "confirm"}')
        assert result["comment"] == "(kein Kommentar)"

    def test_invalid_json_returns_none(self):
        assert _parse_llm_response("This is not JSON") is None

    def test_empty_string_returns_none(self):
        assert _parse_llm_response("") is None


# ---------------------------------------------------------------------------
# _build_user_prompt
# ---------------------------------------------------------------------------

class TestBuildUserPrompt:

    def test_contains_spec_id(self):
        spec = _make_spec()
        req = spec.requirements[0]
        prompt = _build_user_prompt("TEST-001", req, "ERFÜLLT", CHANGED_FILES)
        assert "TEST-001" in prompt
        assert "R1" in prompt
        assert "Schema existiert" in prompt

    def test_contains_changed_files(self):
        spec = _make_spec()
        req = spec.requirements[0]
        prompt = _build_user_prompt("TEST-001", req, "ERFÜLLT", CHANGED_FILES)
        assert "db_service.py" in prompt


# ---------------------------------------------------------------------------
# run_analyzers - Flag off
# ---------------------------------------------------------------------------

class TestFlagOff:

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", False)
    def test_returns_results_unchanged(self):
        spec = _make_spec()
        results = _make_results()
        original_evidence = [dict(r.evidence) for r in results]

        out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == len(results)
        for i, r in enumerate(out):
            assert r.status == results[i].status
            assert r.evidence == original_evidence[i]

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", False)
    def test_no_perplexity_call(self):
        """Bei Flag off darf query_perplexity nie aufgerufen werden."""
        spec = _make_spec()
        results = _make_results()

        with patch("audit.analyzers._analyze_single_requirement") as mock_analyze:
            run_analyzers(spec, results, INPUT_FACTS)
            mock_analyze.assert_not_called()


# ---------------------------------------------------------------------------
# run_analyzers - Flag on + success
# ---------------------------------------------------------------------------

class TestFlagOnSuccess:

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    def test_adds_llm_review_evidence(self):
        spec = _make_spec()
        results = _make_results()

        fake_response = {
            "provider": "perplexity",
            "model": "sonar",
            "content": '{"opinion": "confirm", "comment": "Dateien decken Requirement ab"}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "raw": {},
        }

        with patch("services.perplexity_service.query_perplexity", return_value=fake_response):
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == 2
        # Mindestens ein Result hat llm_review
        has_llm = any(
            r.evidence and "llm_review" in r.evidence
            for r in out
        )
        assert has_llm, "Kein AuditResult hat llm_review evidence"

        # Pruefe dass opinion korrekt ist
        for r in out:
            if r.evidence and "llm_review" in r.evidence:
                assert r.evidence["llm_review"]["opinion"] == "confirm"
                assert "Dateien" in r.evidence["llm_review"]["comment"]

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    def test_status_not_modified(self):
        """LLM-Analyzer darf status niemals aendern."""
        spec = _make_spec()
        results = _make_results()
        original_statuses = [r.status for r in results]

        fake_response = {
            "provider": "perplexity",
            "model": "sonar",
            "content": '{"opinion": "question", "comment": "Zweifel"}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "raw": {},
        }

        with patch("services.perplexity_service.query_perplexity", return_value=fake_response):
            out = run_analyzers(spec, results, INPUT_FACTS)

        for i, r in enumerate(out):
            assert r.status == original_statuses[i], f"Status von {r.requirement_key} wurde veraendert!"

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 1)
    def test_respects_max_requirements_limit(self):
        """Nur max N Requirements werden analysiert."""
        spec = _make_spec()
        results = _make_results()

        fake_response = {
            "provider": "perplexity",
            "model": "sonar",
            "content": '{"opinion": "confirm", "comment": "ok"}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "raw": {},
        }

        with patch("services.perplexity_service.query_perplexity", return_value=fake_response):
            out = run_analyzers(spec, results, INPUT_FACTS)

        llm_count = sum(1 for r in out if r.evidence and "llm_review" in r.evidence)
        assert llm_count == 1, f"Erwartet 1 LLM-Review, bekam {llm_count}"


# ---------------------------------------------------------------------------
# run_analyzers - Flag on + Connector-Error
# ---------------------------------------------------------------------------

class TestFlagOnError:

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    def test_connector_error_does_not_crash(self):
        """Perplexity-Fehler darf run_analyzers nicht abbrechen."""
        from services.perplexity_service import PerplexityRequestError

        spec = _make_spec()
        results = _make_results()

        with patch(
            "services.perplexity_service.query_perplexity",
            side_effect=PerplexityRequestError("Timeout"),
        ):
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == 2
        # Results muessen zurueckkommen, ggf. mit error-evidence
        for r in out:
            if r.evidence and "llm_review_error" in r.evidence:
                assert r.evidence["llm_review_error"]["code"] == "timeout"
                assert "Timeout" in r.evidence["llm_review_error"]["message"]

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    def test_api_error_contained(self):
        """PerplexityAPIError wird gefangen, nicht weitergereicht."""
        from services.perplexity_service import PerplexityAPIError

        spec = _make_spec()
        results = _make_results()

        with patch(
            "services.perplexity_service.query_perplexity",
            side_effect=PerplexityAPIError("Rate limit", status_code=429),
        ):
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == 2


# ---------------------------------------------------------------------------
# run_analyzers - Malformed LLM payload
# ---------------------------------------------------------------------------

class TestMalformedLlmPayload:

    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    def test_non_json_llm_response(self):
        """LLM gibt Freitext statt JSON -> opinion=unknown."""
        spec = _make_spec()
        results = _make_results()

        fake_response = {
            "provider": "perplexity",
            "model": "sonar",
            "content": "Ich bin mir nicht sicher, ob das passt.",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "raw": {},
        }

        with patch("services.perplexity_service.query_perplexity", return_value=fake_response):
            out = run_analyzers(spec, results, INPUT_FACTS)

        for r in out:
            if r.evidence and "llm_review" in r.evidence:
                assert r.evidence["llm_review"]["opinion"] == "unknown"
