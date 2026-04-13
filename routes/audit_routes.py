"""
SPEC-AUDIT-INTEGRATION-V1-001: Audit API-Endpoints und Dashboard-Seite.
POST /api/audits/run, GET /api/audits/<run_id>, GET /api/audits/spec/<spec_id>/latest.
"""
from flask import Blueprint, jsonify, request, render_template
from routes.api_utils import api_route
from audit.repository import (
    SpecNotFoundError,
    save_audit_response,
    load_audit_run,
    load_audit_results,
    load_latest_run_for_spec,
)
from audit.service import run_audit
audit_bp = Blueprint("audit", __name__)


def _serialize_response(response) -> dict:
    """Serialisiert AuditResponse zu JSON-kompatiblem Dict."""
    return {
        "spec_id": response.spec_id,
        "spec_title": response.spec_title,
        "overall_status": response.overall_status.value,
        "started_at": response.started_at.isoformat(),
        "finished_at": response.finished_at.isoformat() if response.finished_at else None,
        "duration_ms": response.duration_ms,
        "summary": response.summary,
        "input_facts": response.input_facts,
        "results": [
            {
                "requirement_key": r.requirement_key,
                "status": r.status.value,
                "notes": r.notes,
                "evidence": r.evidence,
            }
            for r in response.results
        ],
    }


def _serialize_persisted_run(run: dict, results: list) -> dict:
    """Serialisiert persistierten Run + Results zu JSON-kompatiblem Dict."""
    started = run.get("started_at")
    finished = run.get("finished_at")
    duration_ms = None
    if started and finished:
        duration_ms = int((finished - started).total_seconds() * 1000)

    result_dicts = [
        {
            "requirement_key": r.requirement_key,
            "status": r.status.value,
            "notes": r.notes,
            "evidence": r.evidence,
        }
        for r in results
    ]

    # Summary berechnen
    from audit.models import RequirementStatus
    counts = {s.value: 0 for s in RequirementStatus}
    for r in results:
        counts[r.status.value] += 1
    summary = {"total": len(results), "by_status": counts}

    return {
        "run_id": run["id"],
        "spec_id": run["spec_id"],
        "spec_title": run.get("spec_title") or "",
        "overall_status": run.get("overall_status"),
        "started_at": started.isoformat() if started else None,
        "finished_at": finished.isoformat() if finished else None,
        "duration_ms": duration_ms,
        "summary": summary,
        "input_facts": run.get("input_facts") or {},
        "results": result_dicts,
    }


# --- Page Route ---

@audit_bp.route("/audits")
def audits_page():
    return render_template("audit.html", active_page="audits")


# --- API Endpoints ---


@audit_bp.route("/api/audits/specs")
@api_route
def api_list_specs():
    """Liefert alle Specs mit Requirement-Count und letztem Run-Status."""
    from services.db_service import execute, ensure_audit_schema
    ensure_audit_schema()

    rows = execute(
        """
        SELECT s.spec_id, s.title, s.summary, s.status, s.risk_level,
               s.updated_at,
               COUNT(sr.id) AS requirement_count
        FROM specs s
        LEFT JOIN spec_requirements sr ON sr.spec_pk = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        """,
        fetch=True,
    ) or []

    specs = []
    for r in rows:
        latest_run = load_latest_run_for_spec(r["spec_id"])
        specs.append({
            "spec_id": r["spec_id"],
            "title": r["title"],
            "summary": r.get("summary"),
            "status": r.get("status"),
            "risk_level": r.get("risk_level"),
            "requirement_count": r["requirement_count"],
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
            "latest_run": {
                "run_id": latest_run["id"],
                "overall_status": latest_run.get("overall_status"),
                "started_at": latest_run["started_at"].isoformat() if latest_run.get("started_at") else None,
            } if latest_run else None,
        })

    return jsonify({"specs": specs}), 200


@audit_bp.route("/api/audits/recent")
@api_route
def api_recent_runs():
    """Liefert die letzten 20 Audit-Runs mit Status."""
    from services.db_service import execute, ensure_audit_schema
    ensure_audit_schema()

    rows = execute(
        """
        SELECT ar.id, ar.spec_id, ar.overall_status,
               ar.started_at, ar.finished_at, ar.input_facts,
               s.title AS spec_title
        FROM audit_runs ar
        LEFT JOIN specs s ON s.spec_id = ar.spec_id
        ORDER BY ar.started_at DESC
        LIMIT 20
        """,
        fetch=True,
    ) or []

    runs = []
    for r in rows:
        started = r.get("started_at")
        finished = r.get("finished_at")
        duration_ms = int((finished - started).total_seconds() * 1000) if started and finished else None
        runs.append({
            "run_id": r["id"],
            "spec_id": r["spec_id"],
            "spec_title": r.get("spec_title") or r["spec_id"],
            "overall_status": r.get("overall_status"),
            "started_at": started.isoformat() if started else None,
            "duration_ms": duration_ms,
        })

    return jsonify({"runs": runs}), 200


@audit_bp.route("/api/audits/run", methods=["POST"])
def api_audit_run():
    """Fuehrt einen Audit-Lauf aus und persistiert das Ergebnis."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request-Body muss JSON sein"}), 400

    spec_id = data.get("spec_id")
    input_facts = data.get("input_facts")

    if not spec_id or not isinstance(spec_id, str) or not spec_id.strip():
        return jsonify({"error": "spec_id ist erforderlich (nicht-leerer String)"}), 400
    if not isinstance(input_facts, dict):
        return jsonify({"error": "input_facts muss ein Objekt sein"}), 400

    # Unbekannte Felder ablehnen
    allowed_keys = {"spec_id", "input_facts"}
    extra = set(data.keys()) - allowed_keys
    if extra:
        return jsonify({"error": f"Unbekannte Felder: {', '.join(sorted(extra))}"}), 400

    try:
        response = run_audit(spec_id.strip(), input_facts)
    except SpecNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Interner Fehler: {str(e)}"}), 500

    # Persistieren
    try:
        run_id = save_audit_response(response)
    except Exception as e:
        return jsonify({"error": f"Audit ausgefuehrt, aber Persistierung fehlgeschlagen: {str(e)}"}), 500

    result = _serialize_response(response)
    result["run_id"] = run_id
    return jsonify(result)


@audit_bp.route("/api/audits/<int:run_id>")
@api_route
def api_audit_by_run_id(run_id):
    """Laedt einen persistierten Audit-Run nach ID."""
    try:
        run = load_audit_run(run_id)
    except Exception:
        return jsonify({"error": f"Audit-Run {run_id} nicht gefunden"}), 404
    if not run:
        return jsonify({"error": f"Audit-Run {run_id} nicht gefunden"}), 404

    try:
        results = load_audit_results(run_id)
    except Exception:
        return jsonify({"error": f"Audit-Run {run_id} nicht gefunden"}), 404
    return jsonify(_serialize_persisted_run(run, results))


@audit_bp.route("/api/audits/spec/<path:spec_id>/latest")
@api_route
def api_audit_latest_by_spec(spec_id):
    """Laedt den neuesten Audit-Run fuer eine Spec."""
    if not spec_id or not spec_id.strip():
        return jsonify({"error": "spec_id darf nicht leer sein"}), 400

    run = load_latest_run_for_spec(spec_id.strip())
    if not run:
        return jsonify({"error": f"Kein Audit-Run fuer Spec '{spec_id}' gefunden"}), 404

    results = load_audit_results(run["id"])
    return jsonify(_serialize_persisted_run(run, results))
