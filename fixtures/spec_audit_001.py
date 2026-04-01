"""
SPEC-AUDIT-001 T8: Beispiel-Specs und Audit-Szenarien.
Nutzung: Import in Tests oder direkter Aufruf fuer manuelle Smoke-Checks.

    python3 -m fixtures.spec_audit_001
"""
from audit.models import Spec, Requirement, Priority


# ---------------------------------------------------------------------------
# Beispiel-Spec 1: Audit-Core (angelehnt an SPEC-AUDIT-001, vereinfacht)
# ---------------------------------------------------------------------------

SPEC_AUDIT_CORE = Spec(
    spec_id="SPEC-AUDIT-001",
    title="DB-backed Spec-vs-Diff Audit Core",
    summary="Internes Audit-Modul mit regelbasierter Pruefung",
    project_mode="mature_product",
    lifecycle_stage="active",
    risk_level="medium",
    requirements=[
        Requirement(
            key="REQ-001",
            title="Spec-Hauptdatensatz in DB",
            priority=Priority.MUST,
            affected_areas=["audit/models.py", "services/db_service.py"],
        ),
        Requirement(
            key="REQ-002",
            title="Requirement-Datensaetze pro Spec",
            priority=Priority.MUST,
            affected_areas=["audit/models.py", "services/db_service.py"],
        ),
        Requirement(
            key="REQ-003",
            title="Audit-Request laedt Spec aus DB",
            priority=Priority.MUST,
            affected_areas=["audit/repository.py"],
        ),
        Requirement(
            key="REQ-004",
            title="Strukturierter Audit-Run",
            priority=Priority.MUST,
            affected_areas=["audit/service.py"],
        ),
        Requirement(
            key="REQ-005",
            title="Regelbasierte Basisbewertung ohne LLM",
            priority=Priority.MUST,
            affected_areas=["audit/rules.py", "audit/service.py"],
        ),
        Requirement(
            key="REQ-006",
            title="Maschinenlesbarer Audit-Response",
            priority=Priority.MUST,
            affected_areas=["audit/models.py", "audit/service.py"],
        ),
        Requirement(
            key="REQ-007",
            title="Vorbereitete Erweiterbarkeit fuer spaetere Analyzer",
            priority=Priority.SHOULD,
            affected_areas=["audit/analyzers/"],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Beispiel-Spec 2: Minimal-Spec (2 Requirements, mixed priority)
# ---------------------------------------------------------------------------

SPEC_MINIMAL = Spec(
    spec_id="SPEC-MINI-001",
    title="Minimale Beispiel-Spec",
    summary="Zum schnellen Testen mit wenigen Requirements",
    project_mode="prototype",
    lifecycle_stage="planning",
    risk_level="low",
    requirements=[
        Requirement(
            key="REQ-A",
            title="Haupt-Feature",
            priority=Priority.MUST,
            affected_areas=["src/feature.py"],
        ),
        Requirement(
            key="REQ-B",
            title="Dokumentation",
            priority=Priority.SHOULD,
            affected_areas=["docs/"],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Audit-Szenarien: definierte changed_files fuer reproduzierbare Ergebnisse
# ---------------------------------------------------------------------------

SCENARIOS = {
    "audit_core_pass": {
        "spec": SPEC_AUDIT_CORE,
        "changed_files": [
            "audit/models.py",
            "services/db_service.py",
            "audit/repository.py",
            "audit/service.py",
            "audit/rules.py",
            "audit/analyzers/__init__.py",
        ],
        "expected_overall": "PASS",
        "description": "Alle affected_areas abgedeckt → PASS",
    },
    "audit_core_partial": {
        "spec": SPEC_AUDIT_CORE,
        "changed_files": [
            "audit/models.py",
            "audit/repository.py",
            "audit/service.py",
            "audit/rules.py",
        ],
        "expected_overall": "PARTIAL",
        "description": "services/db_service.py fehlt → REQ-001/002 nur TEILWEISE → PARTIAL",
    },
    "audit_core_fail": {
        "spec": SPEC_AUDIT_CORE,
        "changed_files": [],
        "expected_overall": "FAIL",
        "description": "Keine Dateien geaendert → alle must FEHLT → FAIL",
    },
    "minimal_pass": {
        "spec": SPEC_MINIMAL,
        "changed_files": ["src/feature.py", "docs/readme.md"],
        "expected_overall": "PASS",
        "description": "Beide Requirements abgedeckt → PASS",
    },
    "minimal_must_only": {
        "spec": SPEC_MINIMAL,
        "changed_files": ["src/feature.py"],
        "expected_overall": "PARTIAL",
        "description": "must ok, should offen → PARTIAL",
    },
}


# ---------------------------------------------------------------------------
# Direkt aufrufbar: python3 -m fixtures.spec_audit_001
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from audit.service import _compute_overall_status
    from audit.rules import evaluate_requirement

    for name, scenario in SCENARIOS.items():
        spec = scenario["spec"]
        files = scenario["changed_files"]
        expected = scenario["expected_overall"]

        results = [evaluate_requirement(req, files) for req in spec.requirements]
        overall = _compute_overall_status(spec, results)

        ok = "OK" if overall.value == expected else "FAIL"
        print(f"[{ok}] {name}: {overall.value} (erwartet: {expected})")
        print(f"      {scenario['description']}")
        for r in results:
            print(f"      {r.requirement_key}: {r.status.value}")
        print()
