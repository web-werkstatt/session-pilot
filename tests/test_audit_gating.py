"""
SPEC-AUDIT-ANALYZER-GATING-001: Tests fuer Gating-Logik im LLM-Analyzer.
"""
from unittest.mock import patch, call

from audit.models import (
    AuditResult,
    Priority,
    Requirement,
    RequirementStatus,
    Spec,
)
from audit.analyzers import (
    run_analyzers,
    _should_run_llm,
    _parse_csv_filter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_spec(risk_level="medium"):
    return Spec(
        spec_id="GATE-TEST-001",
        title="Gating Test Spec",
        risk_level=risk_level,
        requirements=[
            Requirement(key="R1", title="Must-Req", priority=Priority.MUST),
            Requirement(key="R2", title="Should-Req", priority=Priority.SHOULD),
            Requirement(key="R3", title="Could-Req", priority=Priority.COULD),
        ],
    )


def _make_results():
    return [
        AuditResult(requirement_key="R1", status=RequirementStatus.ERFUELLT, evidence={}),
        AuditResult(requirement_key="R2", status=RequirementStatus.TEILWEISE, evidence={}),
        AuditResult(requirement_key="R3", status=RequirementStatus.UNSICHER, evidence={}),
    ]


INPUT_FACTS = {"changed_files": ["services/db_service.py"]}

FAKE_RESPONSE = {
    "provider": "perplexity",
    "model": "sonar",
    "content": '{"opinion": "confirm", "comment": "ok"}',
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    "raw": {},
}


# ---------------------------------------------------------------------------
# _parse_csv_filter
# ---------------------------------------------------------------------------

class TestParseCsvFilter:

    def test_empty_string(self):
        assert _parse_csv_filter("") == set()

    def test_single_value(self):
        assert _parse_csv_filter("must") == {"must"}

    def test_multiple_values(self):
        assert _parse_csv_filter("must,should") == {"must", "should"}

    def test_whitespace_handling(self):
        assert _parse_csv_filter(" must , should ") == {"must", "should"}

    def test_none(self):
        assert _parse_csv_filter(None) == set()


# ---------------------------------------------------------------------------
# _should_run_llm - Globale Switches
# ---------------------------------------------------------------------------

class TestGlobalSwitches:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "off")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    def test_default_mode_off(self):
        """DEFAULT_MODE=off -> immer False, egal welches Requirement."""
        spec = _make_spec()
        assert _should_run_llm(spec, spec.requirements[0]) is False

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", False)
    def test_analyzer_disabled(self):
        """ANALYZER_ENABLED=False -> False."""
        spec = _make_spec()
        assert _should_run_llm(spec, spec.requirements[0]) is False

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", set())
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_all_enabled_no_filters(self):
        """Alles enabled, keine Filter -> True."""
        spec = _make_spec()
        assert _should_run_llm(spec, spec.requirements[0]) is True


# ---------------------------------------------------------------------------
# _should_run_llm - Per-Requirement Override
# ---------------------------------------------------------------------------

class TestPerRequirementOverride:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", set())
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_llm_mode_off(self):
        """Requirement mit llm_mode=off -> False."""
        spec = _make_spec()
        req = Requirement(key="X1", title="Test", llm_mode="off")
        assert _should_run_llm(spec, req) is False

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_llm_mode_on_bypasses_filters(self):
        """Requirement mit llm_mode=on -> True, auch wenn Priority nicht matcht."""
        spec = _make_spec()
        req = Requirement(key="X2", title="Test", priority=Priority.COULD, llm_mode="on")
        assert _should_run_llm(spec, req) is True

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "off")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    def test_llm_mode_on_blocked_by_global_off(self):
        """llm_mode=on hilft nicht wenn DEFAULT_MODE=off."""
        spec = _make_spec()
        req = Requirement(key="X3", title="Test", llm_mode="on")
        assert _should_run_llm(spec, req) is False


# ---------------------------------------------------------------------------
# _should_run_llm - Priority Filter
# ---------------------------------------------------------------------------

class TestPriorityFilter:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_must_allowed(self):
        spec = _make_spec()
        assert _should_run_llm(spec, spec.requirements[0]) is True  # R1: must

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_should_blocked(self):
        spec = _make_spec()
        assert _should_run_llm(spec, spec.requirements[1]) is False  # R2: should

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must", "should"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_multiple_priorities(self):
        spec = _make_spec()
        assert _should_run_llm(spec, spec.requirements[0]) is True   # must
        assert _should_run_llm(spec, spec.requirements[1]) is True   # should
        assert _should_run_llm(spec, spec.requirements[2]) is False  # could


# ---------------------------------------------------------------------------
# _should_run_llm - Risk Level Filter
# ---------------------------------------------------------------------------

class TestRiskLevelFilter:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", set())
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", {"high", "critical"})
    def test_medium_risk_blocked(self):
        spec = _make_spec(risk_level="medium")
        assert _should_run_llm(spec, spec.requirements[0]) is False

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", set())
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", {"high", "critical"})
    def test_high_risk_allowed(self):
        spec = _make_spec(risk_level="high")
        assert _should_run_llm(spec, spec.requirements[0]) is True


# ---------------------------------------------------------------------------
# run_analyzers - Integration: Global off
# ---------------------------------------------------------------------------

class TestRunAnalyzersGlobalOff:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "off")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    def test_default_mode_off_no_calls(self):
        spec = _make_spec()
        results = _make_results()
        out = run_analyzers(spec, results, INPUT_FACTS)
        assert len(out) == 3
        for r in out:
            assert r.evidence == {} or "llm_review" not in (r.evidence or {})

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", False)
    def test_analyzer_disabled_no_calls(self):
        spec = _make_spec()
        results = _make_results()
        out = run_analyzers(spec, results, INPUT_FACTS)
        assert len(out) == 3


# ---------------------------------------------------------------------------
# run_analyzers - Integration: Global on + Priority Filter
# ---------------------------------------------------------------------------

class TestRunAnalyzersWithFilter:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_only_must_gets_llm(self):
        """Nur R1 (must) bekommt LLM-Review, R2 (should) und R3 (could) nicht."""
        spec = _make_spec()
        results = _make_results()

        with patch("services.perplexity_service.query_perplexity", return_value=FAKE_RESPONSE) as mock_qp:
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == 3  # Gleiche Anzahl

        # R1 hat llm_review
        r1 = next(r for r in out if r.requirement_key == "R1")
        assert "llm_review" in r1.evidence

        # R2 und R3 haben kein llm_review
        r2 = next(r for r in out if r.requirement_key == "R2")
        r3 = next(r for r in out if r.requirement_key == "R3")
        assert "llm_review" not in (r2.evidence or {})
        assert "llm_review" not in (r3.evidence or {})

        # query_perplexity wurde genau 1x aufgerufen
        assert mock_qp.call_count == 1


# ---------------------------------------------------------------------------
# run_analyzers - Integration: Per-Requirement llm_mode
# ---------------------------------------------------------------------------

class TestRunAnalyzersLlmMode:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", set())
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_llm_mode_off_skips(self):
        """Requirement mit llm_mode=off wird uebersprungen."""
        spec = Spec(
            spec_id="GATE-002",
            title="Mode Test",
            requirements=[
                Requirement(key="A1", title="Active", llm_mode="inherit"),
                Requirement(key="A2", title="Blocked", llm_mode="off"),
            ],
        )
        results = [
            AuditResult(requirement_key="A1", status=RequirementStatus.ERFUELLT, evidence={}),
            AuditResult(requirement_key="A2", status=RequirementStatus.TEILWEISE, evidence={}),
        ]

        with patch("services.perplexity_service.query_perplexity", return_value=FAKE_RESPONSE) as mock_qp:
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == 2
        a1 = next(r for r in out if r.requirement_key == "A1")
        a2 = next(r for r in out if r.requirement_key == "A2")
        assert "llm_review" in a1.evidence
        assert "llm_review" not in (a2.evidence or {})
        assert mock_qp.call_count == 1

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_llm_mode_on_bypasses_priority_filter(self):
        """llm_mode=on laesst LLM laufen, obwohl Priority nicht matcht."""
        spec = Spec(
            spec_id="GATE-003",
            title="Override Test",
            requirements=[
                Requirement(key="B1", title="Should-but-on", priority=Priority.SHOULD, llm_mode="on"),
            ],
        )
        results = [
            AuditResult(requirement_key="B1", status=RequirementStatus.TEILWEISE, evidence={}),
        ]

        with patch("services.perplexity_service.query_perplexity", return_value=FAKE_RESPONSE) as mock_qp:
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert "llm_review" in out[0].evidence
        assert mock_qp.call_count == 1


# ---------------------------------------------------------------------------
# run_analyzers - Result count unchanged
# ---------------------------------------------------------------------------

class TestResultCountUnchanged:

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", set())
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_same_count_with_llm(self):
        spec = _make_spec()
        results = _make_results()

        with patch("services.perplexity_service.query_perplexity", return_value=FAKE_RESPONSE):
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == len(results)

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "off")
    def test_same_count_without_llm(self):
        spec = _make_spec()
        results = _make_results()
        out = run_analyzers(spec, results, INPUT_FACTS)
        assert len(out) == len(results)

    @patch("audit.analyzers.AUDIT_LLM_DEFAULT_MODE", "auto")
    @patch("audit.analyzers.AUDIT_LLM_ANALYZER_ENABLED", True)
    @patch("audit.analyzers.AUDIT_LLM_MAX_REQUIREMENTS", 10)
    @patch("audit.analyzers._ALLOWED_PRIORITIES", {"must"})
    @patch("audit.analyzers._ALLOWED_RISK_LEVELS", set())
    def test_same_count_with_filter(self):
        spec = _make_spec()
        results = _make_results()

        with patch("services.perplexity_service.query_perplexity", return_value=FAKE_RESPONSE):
            out = run_analyzers(spec, results, INPUT_FACTS)

        assert len(out) == len(results)
