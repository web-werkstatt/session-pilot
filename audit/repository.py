"""
SPEC-AUDIT-001 T3: Repository fuer Spec-Zugriffe.
Lokales Pattern nur fuer das Audit-Modul, kein projektweiter Umbau.
DB-Zugriffe ueber bestehenden db_service.
"""
from services.db_service import execute, ensure_audit_schema
from audit.models import Spec, Requirement


class SpecNotFoundError(Exception):
    """Spec mit gegebener spec_id existiert nicht in der DB."""
    pass


def get_spec(spec_id: str) -> Spec:
    """Laedt eine Spec inkl. Requirements aus der DB.

    Raises:
        SpecNotFoundError: wenn spec_id nicht existiert.
    """
    ensure_audit_schema()

    row = execute(
        "SELECT * FROM specs WHERE spec_id = %s",
        (spec_id,),
        fetchone=True,
    )
    if not row:
        raise SpecNotFoundError(f"Spec '{spec_id}' nicht gefunden")

    req_rows = execute(
        """SELECT key, title, description, priority, source,
                  acceptance_criteria, affected_areas, sort_order
           FROM spec_requirements
           WHERE spec_pk = %s
           ORDER BY sort_order, id""",
        (row["id"],),
        fetch=True,
    ) or []

    requirements = [
        Requirement(
            key=r["key"],
            title=r["title"],
            description=r.get("description"),
            priority=r.get("priority", "must"),
            source=r.get("source"),
            acceptance_criteria=r.get("acceptance_criteria") or [],
            affected_areas=r.get("affected_areas") or [],
            sort_order=r.get("sort_order", 0),
        )
        for r in req_rows
    ]

    return Spec(
        spec_id=row["spec_id"],
        title=row["title"],
        summary=row.get("summary"),
        project_mode=row.get("project_mode"),
        lifecycle_stage=row.get("lifecycle_stage"),
        risk_level=row.get("risk_level"),
        status=row.get("status", "draft"),
        requirements=requirements,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def save_spec(spec: Spec) -> Spec:
    """Speichert eine Spec mit Requirements (upsert).

    Gibt die gespeicherte Spec zurueck (mit created_at/updated_at aus DB).
    """
    ensure_audit_schema()

    existing = execute(
        "SELECT id FROM specs WHERE spec_id = %s",
        (spec.spec_id,),
        fetchone=True,
    )

    if existing:
        spec_pk = existing["id"]
        execute(
            """UPDATE specs
               SET title = %s, summary = %s, project_mode = %s,
                   lifecycle_stage = %s, risk_level = %s, status = %s,
                   updated_at = NOW()
               WHERE id = %s""",
            (spec.title, spec.summary, spec.project_mode,
             spec.lifecycle_stage, spec.risk_level, spec.status, spec_pk),
        )
    else:
        row = execute(
            """INSERT INTO specs (spec_id, title, summary, project_mode,
                                  lifecycle_stage, risk_level, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (spec.spec_id, spec.title, spec.summary, spec.project_mode,
             spec.lifecycle_stage, spec.risk_level, spec.status),
            fetchone=True,
        )
        spec_pk = row["id"]

    # Requirements: DELETE + INSERT (atomarer Ersatz)
    execute("DELETE FROM spec_requirements WHERE spec_pk = %s", (spec_pk,))

    for i, req in enumerate(spec.requirements):
        execute(
            """INSERT INTO spec_requirements
                   (spec_pk, key, title, description, priority, source,
                    acceptance_criteria, affected_areas, sort_order)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)""",
            (spec_pk, req.key, req.title, req.description,
             req.priority.value, req.source,
             _to_json(req.acceptance_criteria),
             _to_json(req.affected_areas),
             i),
        )

    return get_spec(spec.spec_id)


def _to_json(value) -> str:
    """Konvertiert Listen/Dicts zu JSON-String fuer JSONB-Spalten."""
    import json
    return json.dumps(value, ensure_ascii=True)
