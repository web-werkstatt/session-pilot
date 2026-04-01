"""
SPEC-AUDIT-001 T4: Regelbasierte Bewertungslogik ohne LLM.
Matcht affected_areas eines Requirements gegen changed_files aus input_facts.
"""
import os
from audit.models import Requirement, AuditResult, RequirementStatus


def evaluate_requirement(req: Requirement, changed_files: list[str]) -> AuditResult:
    """Bewertet ein einzelnes Requirement gegen die geaenderten Dateien.

    Bewertungslogik:
    - Keine affected_areas definiert → UNSICHER (keine Aussage moeglich)
    - affected_areas definiert, aber keine changed_files → FEHLT
    - affected_areas definiert, Treffer vorhanden → Anteil bestimmt Status
    """
    if not req.affected_areas:
        return AuditResult(
            requirement_key=req.key,
            status=RequirementStatus.UNSICHER,
            notes="Requirement hat keine affected_areas definiert, "
                  "automatische Bewertung nicht moeglich",
        )

    if not changed_files:
        status = (
            RequirementStatus.FEHLT
            if req.priority.value == "must"
            else RequirementStatus.UNSICHER
        )
        return AuditResult(
            requirement_key=req.key,
            status=status,
            notes="Keine changed_files vorhanden",
        )

    matched, unmatched = _match_areas(req.affected_areas, changed_files)

    if not matched:
        status = (
            RequirementStatus.FEHLT
            if req.priority.value == "must"
            else RequirementStatus.UNSICHER
        )
        return AuditResult(
            requirement_key=req.key,
            status=status,
            notes=f"Keine der affected_areas wurde geaendert: "
                  f"{', '.join(req.affected_areas)}",
        )

    coverage = len(matched) / len(req.affected_areas)

    if coverage >= 1.0:
        status = RequirementStatus.ERFUELLT
        notes = f"Alle affected_areas abgedeckt: {', '.join(sorted(matched))}"
    elif coverage > 0:
        status = RequirementStatus.TEILWEISE
        notes = (
            f"Abdeckung {coverage:.0%}: "
            f"getroffen={', '.join(sorted(matched))}; "
            f"fehlend={', '.join(sorted(unmatched))}"
        )
    else:
        status = RequirementStatus.FEHLT
        notes = "Keine Abdeckung"

    return AuditResult(
        requirement_key=req.key,
        status=status,
        notes=notes,
        evidence={"matched_areas": sorted(matched),
                  "unmatched_areas": sorted(unmatched),
                  "coverage": round(coverage, 2)},
    )


def _match_areas(
    affected_areas: list[str], changed_files: list[str]
) -> tuple[set[str], set[str]]:
    """Prueft welche affected_areas durch changed_files abgedeckt sind.

    Matching-Regeln:
    - affected_area endet mit '/' → Verzeichnis-Prefix-Match
      (z.B. 'audit/' matcht 'audit/models.py')
    - affected_area ist exakter Dateiname → exakter Match
      (z.B. 'audit/models.py' matcht 'audit/models.py')
    - Normalisiert Pfade (entfernt fuehrende ./)

    Returns:
        (matched_areas, unmatched_areas)
    """
    normalized_files = {_normalize(f) for f in changed_files}

    matched = set()
    unmatched = set()

    for area in affected_areas:
        norm_area = _normalize(area)
        if _area_covered(norm_area, normalized_files):
            matched.add(area)
        else:
            unmatched.add(area)

    return matched, unmatched


def _area_covered(area: str, files: set[str]) -> bool:
    """Prueft ob eine einzelne area durch mindestens eine Datei abgedeckt ist."""
    if area.endswith("/"):
        return any(f.startswith(area) or f.startswith(area.rstrip("/")) for f in files)
    return area in files


def _normalize(path: str) -> str:
    """Normalisiert einen Pfad: entfernt ./ Prefix, normalisiert Separatoren.
    Behaelt trailing slash bei (Verzeichnis-Markierung).
    """
    is_dir = path.rstrip().endswith("/")
    path = path.strip()
    path = os.path.normpath(path)
    if path.startswith("./"):
        path = path[2:]
    if is_dir and not path.endswith("/"):
        path += "/"
    return path
