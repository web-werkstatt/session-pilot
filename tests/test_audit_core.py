"""
SPEC-AUDIT-001 T6: Tests fuer Audit-Core.
Gate nach T5 — muessen gruen sein bevor T7 startet.

Alle Tests laufen ohne DB-Verbindung: Service-Logik wird mit
in-Memory-Specs getestet, get_spec() wird per monkeypatch ersetzt.
"""
import pytest
from datetime import datetime, timezone

from audit.models import (
    AuditResponse,
    AuditResult,
    OverallStatus,
    Priority,
    Requirement,
    RequirementStatus,
    Spec,
)
from audit.repository import SpecNotFoundError
from audit.rules import evaluate_requirement
from audit.service import _compute_overall_status, run_audit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_spec(spec_id="TEST-001", requirements=None):
    """Erzeugt eine Spec mit Default-Werten."""
    if requirements is None:
        requirements = [
            Requirement(
                key="REQ-001",
                title="DB-Schema",
                priority=Priority.MUST,
                affected_areas=["audit/models.py", "services/db_service.py"],
            ),
            Requirement(
                key="REQ-002",
                title="Repository",
                priority=Priority.MUST,
                affected_areas=["audit/repository.py"],
            ),
            Requirement(
                key="REQ-003",
                title="Dokumentation",
                priority=Priority.SHOULD,
                affected_areas=["docs/"],
            ),
        ]
    return Spec(
        spec_id=spec_id,
        title="Test-Spezifikation",
        summary="Fuer Unit-Tests",
        project_mode="mature_product",
        lifecycle_stage="active",
        risk_level="medium",
        requirements=requirements,
    )


# ---------------------------------------------------------------------------
# T6-Pflicht: Leere changed_files → kein must auf ERFUELLT
# ---------------------------------------------------------------------------

class TestEmptyChangedFiles:
    """REQ-005: Bei leerer Faktenlage darf kein must-Requirement ERFUELLT sein."""

    def test_must_not_erfuellt_with_empty_files(self):
        spec = _make_spec()
        for req in spec.requirements:
            if req.priority == Priority.MUST:
                r = evaluate_requirement(req, [])
                assert r.status != RequirementStatus.ERFUELLT, (
                    f"{req.key} wurde bei leeren files als ERFUELLT bewertet"
                )

    def test_must_is_fehlt_with_empty_files(self):
        req = Requirement(
            key="R1", title="T", priority=Priority.MUST,
            affected_areas=["audit/models.py"],
        )
        r = evaluate_requirement(req, [])
        assert r.status == RequirementStatus.FEHLT

    def test_should_is_unsicher_with_empty_files(self):
        req = Requirement(
            key="R1", title="T", priority=Priority.SHOULD,
            affected_areas=["docs/"],
        )
        r = evaluate_requirement(req, [])
        assert r.status == RequirementStatus.UNSICHER


# ---------------------------------------------------------------------------
# T6-Pflicht: Passende changed_files → mindestens TEILWEISE moeglich
# ---------------------------------------------------------------------------

class TestMatchingChangedFiles:
    """REQ-005: Passende Dateien muessen mindestens TEILWEISE ergeben."""

    def test_partial_match(self):
        req = Requirement(
            key="R1", title="T", priority=Priority.MUST,
            affected_areas=["audit/models.py", "audit/service.py"],
        )
        r = evaluate_requirement(req, ["audit/models.py"])
        assert r.status == RequirementStatus.TEILWEISE

    def test_full_match(self):
        req = Requirement(
            key="R1", title="T", priority=Priority.MUST,
            affected_areas=["audit/models.py"],
        )
        r = evaluate_requirement(req, ["audit/models.py", "other.py"])
        assert r.status == RequirementStatus.ERFUELLT

    def test_directory_match(self):
        req = Requirement(
            key="R1", title="T", priority=Priority.MUST,
            affected_areas=["audit/"],
        )
        r = evaluate_requirement(req, ["audit/rules.py"])
        assert r.status == RequirementStatus.ERFUELLT


# ---------------------------------------------------------------------------
# T6-Pflicht: Unbekannte spec_id → definierter Fehler
# ---------------------------------------------------------------------------

class TestUnknownSpecId:
    """REQ-003: Unbekannte spec_id muss sauberen Fehler erzeugen."""

    def test_unknown_spec_raises_error(self, monkeypatch):
        def fake_get_spec(spec_id):
            raise SpecNotFoundError(f"Spec '{spec_id}' nicht gefunden")

        monkeypatch.setattr("audit.service.get_spec", fake_get_spec)

        with pytest.raises(SpecNotFoundError, match="NONEXISTENT"):
            run_audit("NONEXISTENT", {"changed_files": ["a.py"]})

    def test_error_message_contains_spec_id(self, monkeypatch):
        def fake_get_spec(spec_id):
            raise SpecNotFoundError(f"Spec '{spec_id}' nicht gefunden")

        monkeypatch.setattr("audit.service.get_spec", fake_get_spec)

        with pytest.raises(SpecNotFoundError) as exc_info:
            run_audit("UNKNOWN-999", {})
        assert "UNKNOWN-999" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T6-Pflicht: Spec ohne Requirements → kein Silent-Pass
# ---------------------------------------------------------------------------

class TestEmptyRequirements:
    """REQ-003: Spec ohne Requirements darf nicht stillschweigend PASS werden."""

    def test_empty_requirements_raises_error(self, monkeypatch):
        empty_spec = _make_spec(requirements=[])

        monkeypatch.setattr("audit.service.get_spec", lambda _: empty_spec)

        with pytest.raises(ValueError, match="keine Requirements"):
            run_audit("EMPTY", {"changed_files": ["a.py"]})


# ---------------------------------------------------------------------------
# End-to-End: run_audit() mit Beispiel-Spec
# ---------------------------------------------------------------------------

class TestRunAuditEndToEnd:
    """Kompletter Audit-Durchlauf mit gemocktem get_spec()."""

    def _run(self, monkeypatch, changed_files):
        spec = _make_spec()
        monkeypatch.setattr("audit.service.get_spec", lambda _: spec)
        return run_audit("TEST-001", {"changed_files": changed_files})

    def test_response_structure(self, monkeypatch):
        resp = self._run(monkeypatch, ["audit/models.py"])
        assert isinstance(resp, AuditResponse)
        assert resp.spec_id == "TEST-001"
        assert resp.spec_title == "Test-Spezifikation"
        assert resp.started_at is not None
        assert resp.finished_at is not None
        assert resp.finished_at >= resp.started_at
        assert resp.duration_ms is not None
        assert resp.duration_ms >= 0
        assert len(resp.results) == 3  # 3 Requirements in Fixture

    def test_all_files_changed_partial(self, monkeypatch):
        """Nur ein Teil der affected_areas abgedeckt → nicht PASS."""
        resp = self._run(monkeypatch, ["audit/models.py"])
        # REQ-001 hat 2 areas, nur 1 getroffen → TEILWEISE
        r1 = next(r for r in resp.results if r.requirement_key == "REQ-001")
        assert r1.status == RequirementStatus.TEILWEISE
        assert resp.overall_status != OverallStatus.PASS

    def test_all_must_covered(self, monkeypatch):
        """Alle must-areas abgedeckt, should offen → PARTIAL (nicht PASS)."""
        resp = self._run(monkeypatch, [
            "audit/models.py", "services/db_service.py",  # REQ-001
            "audit/repository.py",                         # REQ-002
        ])
        r1 = next(r for r in resp.results if r.requirement_key == "REQ-001")
        r2 = next(r for r in resp.results if r.requirement_key == "REQ-002")
        r3 = next(r for r in resp.results if r.requirement_key == "REQ-003")
        assert r1.status == RequirementStatus.ERFUELLT
        assert r2.status == RequirementStatus.ERFUELLT
        assert r3.status != RequirementStatus.ERFUELLT  # docs/ nicht geaendert
        assert resp.overall_status == OverallStatus.PARTIAL

    def test_everything_covered(self, monkeypatch):
        """Alle areas inkl. should abgedeckt → PASS."""
        resp = self._run(monkeypatch, [
            "audit/models.py", "services/db_service.py",
            "audit/repository.py",
            "docs/readme.md",  # matcht docs/
        ])
        assert resp.overall_status == OverallStatus.PASS

    def test_no_files_at_all(self, monkeypatch):
        """Leere changed_files → FAIL (must-Requirements FEHLT)."""
        resp = self._run(monkeypatch, [])
        assert resp.overall_status == OverallStatus.FAIL
        for r in resp.results:
            assert r.status != RequirementStatus.ERFUELLT

    def test_input_facts_in_response(self, monkeypatch):
        """input_facts werden im Response gespeichert."""
        resp = self._run(monkeypatch, ["audit/models.py"])
        assert resp.input_facts == {"changed_files": ["audit/models.py"]}

    def test_input_facts_missing_changed_files(self, monkeypatch):
        """Fehlender changed_files-Key → leere Liste, kein Crash."""
        spec = _make_spec()
        monkeypatch.setattr("audit.service.get_spec", lambda _: spec)
        resp = run_audit("TEST-001", {})
        assert resp.input_facts == {"changed_files": []}
        assert resp.overall_status == OverallStatus.FAIL


# ---------------------------------------------------------------------------
# overall_status Berechnungslogik
# ---------------------------------------------------------------------------

class TestOverallStatus:
    """Isolierte Tests fuer _compute_overall_status."""

    def _result(self, key, status):
        return AuditResult(requirement_key=key, status=status)

    def test_all_pass(self):
        spec = _make_spec(requirements=[
            Requirement(key="R1", title="T", priority=Priority.MUST, affected_areas=["a"]),
        ])
        results = [self._result("R1", RequirementStatus.ERFUELLT)]
        assert _compute_overall_status(spec, results) == OverallStatus.PASS

    def test_must_fehlt_is_fail(self):
        spec = _make_spec(requirements=[
            Requirement(key="R1", title="T", priority=Priority.MUST, affected_areas=["a"]),
        ])
        results = [self._result("R1", RequirementStatus.FEHLT)]
        assert _compute_overall_status(spec, results) == OverallStatus.FAIL

    def test_must_unsicher_not_pass(self):
        spec = _make_spec(requirements=[
            Requirement(key="R1", title="T", priority=Priority.MUST, affected_areas=["a"]),
        ])
        results = [self._result("R1", RequirementStatus.UNSICHER)]
        status = _compute_overall_status(spec, results)
        assert status != OverallStatus.PASS
        assert status == OverallStatus.UNSICHER

    def test_missing_must_result_is_fail(self):
        spec = _make_spec(requirements=[
            Requirement(key="R1", title="T", priority=Priority.MUST, affected_areas=["a"]),
            Requirement(key="R2", title="T", priority=Priority.MUST, affected_areas=["b"]),
        ])
        results = [self._result("R1", RequirementStatus.ERFUELLT)]  # R2 fehlt
        assert _compute_overall_status(spec, results) == OverallStatus.FAIL

    def test_fehlt_trumps_unsicher(self):
        spec = _make_spec(requirements=[
            Requirement(key="R1", title="T", priority=Priority.MUST, affected_areas=["a"]),
            Requirement(key="R2", title="T", priority=Priority.MUST, affected_areas=["b"]),
        ])
        results = [
            self._result("R1", RequirementStatus.FEHLT),
            self._result("R2", RequirementStatus.UNSICHER),
        ]
        assert _compute_overall_status(spec, results) == OverallStatus.FAIL


# ---------------------------------------------------------------------------
# T7: AuditResponse-Felder und Helper
# ---------------------------------------------------------------------------

class TestAuditResponseFields:
    """T7: spec_title, duration_ms, summary."""

    def _run(self, monkeypatch, changed_files):
        spec = _make_spec()
        monkeypatch.setattr("audit.service.get_spec", lambda _: spec)
        return run_audit("TEST-001", {"changed_files": changed_files})

    def test_spec_title_populated(self, monkeypatch):
        resp = self._run(monkeypatch, ["audit/models.py"])
        assert resp.spec_title == "Test-Spezifikation"

    def test_duration_ms_positive(self, monkeypatch):
        resp = self._run(monkeypatch, ["audit/models.py"])
        assert resp.duration_ms is not None
        assert resp.duration_ms >= 0

    def test_duration_ms_none_without_finished(self):
        from datetime import timezone
        resp = AuditResponse(
            spec_id="X", overall_status=OverallStatus.FAIL,
            started_at=datetime.now(timezone.utc),
            finished_at=None, results=[],
        )
        assert resp.duration_ms is None

    def test_summary_counts(self, monkeypatch):
        resp = self._run(monkeypatch, [
            "audit/models.py", "services/db_service.py",  # REQ-001 → ERFUELLT
            "audit/repository.py",                         # REQ-002 → ERFUELLT
        ])
        s = resp.summary
        assert s["total"] == 3
        assert s["by_status"]["ERFÜLLT"] == 2
        # REQ-003 (should, docs/) nicht abgedeckt → UNSICHER
        assert s["by_status"]["UNSICHER"] == 1

    def test_summary_all_fehlt(self, monkeypatch):
        resp = self._run(monkeypatch, [])
        s = resp.summary
        assert s["total"] == 3
        assert s["by_status"]["FEHLT"] >= 2  # must-Reqs

    def test_model_dump_includes_computed(self, monkeypatch):
        """model_dump() enthaelt die Basis-Felder (properties sind excluded)."""
        resp = self._run(monkeypatch, ["audit/models.py"])
        d = resp.model_dump()
        assert "spec_id" in d
        assert "spec_title" in d
        assert "overall_status" in d
        assert "results" in d


# ---------------------------------------------------------------------------
# T8: Smoke-Checks mit Fixture-Szenarien
# ---------------------------------------------------------------------------

class TestFixtureSmokeChecks:
    """T8: End-to-End Smoke-Checks mit Beispiel-Specs aus fixtures/."""

    def _audit(self, monkeypatch, spec, changed_files):
        monkeypatch.setattr("audit.service.get_spec", lambda _: spec)
        return run_audit(spec.spec_id, {"changed_files": changed_files})

    def test_audit_core_pass(self, monkeypatch):
        """SPEC-AUDIT-001 mit allen Dateien → PASS."""
        from fixtures.spec_audit_001 import SCENARIOS
        s = SCENARIOS["audit_core_pass"]
        resp = self._audit(monkeypatch, s["spec"], s["changed_files"])
        assert resp.overall_status == OverallStatus.PASS
        assert resp.spec_title == "DB-backed Spec-vs-Diff Audit Core"
        assert all(
            r.status == RequirementStatus.ERFUELLT for r in resp.results
        )

    def test_audit_core_partial(self, monkeypatch):
        """SPEC-AUDIT-001 ohne db_service.py → PARTIAL."""
        from fixtures.spec_audit_001 import SCENARIOS
        s = SCENARIOS["audit_core_partial"]
        resp = self._audit(monkeypatch, s["spec"], s["changed_files"])
        assert resp.overall_status == OverallStatus.PARTIAL
        teilweise = [r for r in resp.results
                     if r.status == RequirementStatus.TEILWEISE]
        assert len(teilweise) >= 1

    def test_audit_core_fail(self, monkeypatch):
        """SPEC-AUDIT-001 ohne Dateien → FAIL."""
        from fixtures.spec_audit_001 import SCENARIOS
        s = SCENARIOS["audit_core_fail"]
        resp = self._audit(monkeypatch, s["spec"], s["changed_files"])
        assert resp.overall_status == OverallStatus.FAIL
        assert resp.summary["by_status"]["FEHLT"] >= 6

    def test_minimal_pass(self, monkeypatch):
        """Minimal-Spec komplett abgedeckt → PASS."""
        from fixtures.spec_audit_001 import SCENARIOS
        s = SCENARIOS["minimal_pass"]
        resp = self._audit(monkeypatch, s["spec"], s["changed_files"])
        assert resp.overall_status == OverallStatus.PASS
        assert resp.summary["total"] == 2

    def test_minimal_must_only(self, monkeypatch):
        """Minimal-Spec nur must abgedeckt → PARTIAL."""
        from fixtures.spec_audit_001 import SCENARIOS
        s = SCENARIOS["minimal_must_only"]
        resp = self._audit(monkeypatch, s["spec"], s["changed_files"])
        assert resp.overall_status == OverallStatus.PARTIAL
