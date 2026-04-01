"""
SPEC-AUDIT-001 T3: Repository fuer Spec-Zugriffe.
Lokales Pattern nur fuer das Audit-Modul, kein projektweiter Umbau.
DB-Zugriffe ueber bestehenden db_service.
"""
from services.db_service import execute, ensure_audit_schema
from audit.models import AuditResponse, AuditResult, RequirementStatus, OverallStatus, Spec, Requirement


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


def save_audit_response(response: AuditResponse) -> int:
    """Speichert einen Audit-Lauf mit Einzelergebnissen in der DB.

    Returns:
        run_id des gespeicherten Laufs.
    """
    ensure_audit_schema()

    row = execute(
        """INSERT INTO audit_runs (spec_id, started_at, finished_at,
                                    overall_status, input_facts)
           VALUES (%s, %s, %s, %s, %s::jsonb)
           RETURNING id""",
        (response.spec_id, response.started_at, response.finished_at,
         response.overall_status.value, _to_json(response.input_facts)),
        fetchone=True,
    )
    run_id = row["id"]

    for result in response.results:
        execute(
            """INSERT INTO audit_results (run_id, requirement_key, status,
                                          notes, evidence)
               VALUES (%s, %s, %s, %s, %s::jsonb)""",
            (run_id, result.requirement_key, result.status.value,
             result.notes, _to_json(result.evidence) if result.evidence else None),
        )

    return run_id


def load_audit_results(run_id: int) -> list[AuditResult]:
    """Laedt Audit-Ergebnisse fuer einen Run aus der DB.

    Returns:
        Liste von AuditResult-Objekten mit evidence aus JSONB.
    """
    ensure_audit_schema()

    rows = execute(
        """SELECT requirement_key, status, notes, evidence
           FROM audit_results
           WHERE run_id = %s
           ORDER BY id""",
        (run_id,),
        fetch=True,
    ) or []

    return [
        AuditResult(
            requirement_key=r["requirement_key"],
            status=RequirementStatus(r["status"]),
            notes=r.get("notes"),
            evidence=r.get("evidence"),
        )
        for r in rows
    ]


def load_audit_run(run_id: int) -> dict:
    """Laedt einen Audit-Run (Metadaten ohne Results), inkl. spec_title."""
    ensure_audit_schema()

    row = execute(
        """SELECT ar.*, s.title AS spec_title
           FROM audit_runs ar
           LEFT JOIN specs s ON s.spec_id = ar.spec_id
           WHERE ar.id = %s""",
        (run_id,),
        fetchone=True,
    )
    return dict(row) if row else None


def load_latest_run_for_spec(spec_id: str) -> dict | None:
    """Laedt den neuesten Audit-Run fuer eine spec_id, inkl. spec_title.

    Returns:
        Dict mit Run-Metadaten oder None wenn kein Run existiert.
    """
    ensure_audit_schema()

    row = execute(
        """SELECT ar.*, s.title AS spec_title
           FROM audit_runs ar
           LEFT JOIN specs s ON s.spec_id = ar.spec_id
           WHERE ar.spec_id = %s
           ORDER BY ar.started_at DESC
           LIMIT 1""",
        (spec_id,),
        fetchone=True,
    )
    return dict(row) if row else None


def _to_json(value) -> str:
    """Konvertiert Listen/Dicts zu JSON-String fuer JSONB-Spalten."""
    import json
    return json.dumps(value, ensure_ascii=True)
