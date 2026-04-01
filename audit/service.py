"""
SPEC-AUDIT-001 T5: Audit-Service — orchestriert Spec-Laden, Bewertung, Response.
audit_runs werden in v0.1 nicht persistent gespeichert (nur Response-Objekt).
"""
from datetime import datetime, timezone

from audit.models import (
    AuditResponse,
    AuditResult,
    OverallStatus,
    RequirementStatus,
    Spec,
)
from audit.repository import get_spec, SpecNotFoundError
from audit.rules import evaluate_requirement


def run_audit(spec_id: str, input_facts: dict) -> AuditResponse:
    """Fuehrt einen Audit-Lauf gegen eine gespeicherte Spec aus.

    Args:
        spec_id: ID der Spec in der DB.
        input_facts: Dict mit Fakten. In v0.1 nur 'changed_files' (list[str]).

    Returns:
        AuditResponse mit Einzelergebnissen und overall_status.

    Raises:
        SpecNotFoundError: wenn spec_id nicht existiert.
        ValueError: wenn Spec keine Requirements hat.
    """
    started_at = datetime.now(timezone.utc)

    spec = get_spec(spec_id)

    if not spec.requirements:
        raise ValueError(
            f"Spec '{spec_id}' hat keine Requirements — "
            f"Audit kann nicht als PASS enden"
        )

    changed_files = input_facts.get("changed_files", [])

    # Regelbasierte Bewertung pro Requirement
    results = [
        evaluate_requirement(req, changed_files)
        for req in spec.requirements
    ]

    # Analyzer-Hook: spaetere Analyzer koennen results ergaenzen/ueberschreiben
    results = _run_analyzers(spec, results, input_facts)

    overall = _compute_overall_status(spec, results)

    return AuditResponse(
        spec_id=spec_id,
        spec_title=spec.title,
        overall_status=overall,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        input_facts={"changed_files": changed_files},
        results=results,
    )


def _compute_overall_status(
    spec: Spec, results: list[AuditResult]
) -> OverallStatus:
    """Berechnet overall_status aus Einzelergebnissen unter Beruecksichtigung
    der Requirement-Prioritaeten.

    Regeln:
    1. Kein must-Requirement darf FEHLT sein → sonst FAIL
    2. Kein must-Requirement darf UNSICHER sein → sonst maximal PARTIAL
    3. Alle must-Requirements ERFUELLT, aber should/could offen → PARTIAL
    4. Alle Requirements ERFUELLT → PASS
    5. Mindestens ein must TEILWEISE ERFUELLT, keines FEHLT → PARTIAL
    """
    # Requirement-Prioritaet per key nachschlagen
    priority_map = {req.key: req.priority.value for req in spec.requirements}
    result_keys = {r.requirement_key for r in results}

    # Sicherheitscheck: jedes must-Requirement muss ein Ergebnis haben
    for req in spec.requirements:
        if req.priority.value == "must" and req.key not in result_keys:
            return OverallStatus.FAIL

    has_must_fehlt = False
    has_must_unsicher = False
    has_must_teilweise = False
    has_non_must_open = False
    all_erfuellt = True

    for r in results:
        prio = priority_map.get(r.requirement_key, "must")
        is_must = prio == "must"

        if r.status == RequirementStatus.ERFUELLT:
            continue

        all_erfuellt = False

        if is_must:
            if r.status == RequirementStatus.FEHLT:
                has_must_fehlt = True
            elif r.status == RequirementStatus.UNSICHER:
                has_must_unsicher = True
            elif r.status == RequirementStatus.TEILWEISE:
                has_must_teilweise = True
        else:
            has_non_must_open = True

    if all_erfuellt:
        return OverallStatus.PASS

    if has_must_fehlt:
        return OverallStatus.FAIL

    if has_must_unsicher:
        return OverallStatus.UNSICHER

    if has_must_teilweise:
        return OverallStatus.PARTIAL

    # Alle must erfuellt, aber should/could offen
    if has_non_must_open:
        return OverallStatus.PARTIAL

    return OverallStatus.PASS


def _run_analyzers(
    spec: Spec,
    results: list[AuditResult],
    input_facts: dict,
) -> list[AuditResult]:
    """Hook fuer spaetere Analyzer (z.B. LLM-basiert).
    In v0.1: gibt results unveraendert zurueck.
    """
    return results
