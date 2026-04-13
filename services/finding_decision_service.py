"""
Finding-Decision-Service: Entscheidungen (Approve/Dismiss/Ignore) fuer Review-Findings.

Generisches System fuer Setup-Reviewer und CWO-Findings. Findings werden ueber
einen deterministischen Fingerprint (SHA256) identifiziert. Ein Enrichment-Schritt
haengt Entscheidungsstatus und Fingerprint an jedes Finding an, bevor es ans
Frontend geliefert wird.

Reaktivierung: Dismissed Findings kommen zurueck wenn sich ihr Kontext wesentlich
aendert (andere Severity, anderes Problem, andere Empfehlung).
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from services.db_finding_decisions_schema import ensure_finding_decisions_schema

log = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "approved", "dismissed", "ignored_once"}
VALID_DISMISS_REASONS = {"bewusst_so", "runtime_datei", "kein_projektziel", "dupliziert"}


# ---------------------------------------------------------------------------
# Fingerprint + Context-Signature
# ---------------------------------------------------------------------------

def compute_finding_fingerprint(
    project_name: str, review_type: str, finding: Dict[str, Any],
) -> str:
    """Deterministischer SHA256-Fingerprint fuer ein Finding.

    Basiert auf stabilen Feldern (area/check_id + title), NICHT auf
    variablen Feldern (problem, detail) die sich bei jedem Run aendern.
    """
    if review_type == "cwo":
        area_or_check = (finding.get("check_id") or "").lower()
    else:
        area_or_check = (finding.get("area") or "").lower()

    title = (finding.get("title") or "").lower()
    canonical = f"{project_name.lower()}|{review_type}|{area_or_check}|{title}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def compute_context_signature(finding: Dict[str, Any], review_type: str) -> str:
    """SHA256 ueber variable Felder — aendert sich wenn der Kontext sich aendert.

    Wird fuer die Reaktivierungs-Logik verwendet: Wenn die Signatur
    sich seit dem Dismiss geaendert hat, wird das Finding reaktiviert.
    """
    severity = (finding.get("severity") or "").lower()

    if review_type == "cwo":
        problem = (finding.get("detail") or "").lower()
        recommendation = (finding.get("recommendation") or "").lower()
    else:
        problem = (finding.get("problem") or "").lower()
        recommendation = (finding.get("recommended_change") or "").lower()

    canonical = f"{severity}|{problem}|{recommendation}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def enrich_findings_with_decisions(
    project_name: str, review_type: str, findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Haengt Entscheidungsstatus und Fingerprint an jedes Finding an.

    - Laedt alle Decisions fuer (project_name, review_type) in einem Query
    - Berechnet Fingerprint pro Finding und matched gegen DB
    - Reaktiviert dismissed Findings mit geaenderter context_signature
    - Fuegt _fingerprint, _decision_status, _decision_id, _hidden an

    Returns:
        Die gleiche Liste, aber mit zusaetzlichen _-Feldern pro Finding.
    """
    if not findings:
        return findings

    ensure_finding_decisions_schema()
    from services.db_service import execute

    rows = execute(
        """
        SELECT id, fingerprint, status, context_signature
        FROM finding_decisions
        WHERE project_name = %s AND review_type = %s
          AND status IN ('dismissed', 'approved', 'ignored_once')
        """,
        (project_name, review_type),
        fetch=True,
    ) or []

    decisions_by_fp = {r["fingerprint"]: r for r in rows}

    reactivate_ids = []

    for f in findings:
        fp = compute_finding_fingerprint(project_name, review_type, f)
        ctx_sig = compute_context_signature(f, review_type)
        f["_fingerprint"] = fp
        f["_review_type"] = review_type

        decision = decisions_by_fp.get(fp)
        if not decision:
            f["_decision_status"] = "pending"
            f["_decision_id"] = None
            f["_hidden"] = False
            continue

        # Reaktivierung: context_signature hat sich geaendert
        # Nur wenn eine gespeicherte Signatur existiert (schuetzt vor
        # Reaktivierung durch unvollstaendige Snapshots beim Erstaufruf)
        stored_sig = decision.get("context_signature")
        if decision["status"] == "dismissed" and stored_sig and stored_sig != ctx_sig:
            reactivate_ids.append(decision["id"])
            f["_decision_status"] = "pending"
            f["_decision_id"] = decision["id"]
            f["_hidden"] = False
            continue

        f["_decision_status"] = decision["status"]
        f["_decision_id"] = decision["id"]
        f["_hidden"] = decision["status"] in ("dismissed", "ignored_once")

    # Reaktivierungen ausfuehren
    if reactivate_ids:
        execute(
            """
            UPDATE finding_decisions
            SET status = 'pending', decided_at = NULL, decided_by = NULL,
                dismiss_reason = NULL, dismiss_note = NULL, updated_at = NOW()
            WHERE id = ANY(%s)
            """,
            (reactivate_ids,),
        )
        log.info(
            "Finding-Decisions reaktiviert: project=%s, count=%d",
            project_name, len(reactivate_ids),
        )

    return findings


# ---------------------------------------------------------------------------
# Record + List
# ---------------------------------------------------------------------------

def record_decision(
    project_name: str,
    review_type: str,
    fingerprint: str,
    status: str,
    finding_snapshot: Dict[str, Any],
    *,
    dismiss_reason: Optional[str] = None,
    dismiss_note: Optional[str] = None,
    decided_by: str = "joseph",
) -> int:
    """Speichert eine Entscheidung (Upsert auf fingerprint).

    Returns:
        ID der finding_decisions-Zeile.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Ungueltiger Status: {status}")
    if dismiss_reason and dismiss_reason not in VALID_DISMISS_REASONS:
        raise ValueError(f"Ungueltiger dismiss_reason: {dismiss_reason}")

    ensure_finding_decisions_schema()
    from services.db_service import execute

    ctx_sig = compute_context_signature(finding_snapshot, review_type)
    snapshot_json = json.dumps(finding_snapshot, ensure_ascii=True)

    row = execute(
        """
        INSERT INTO finding_decisions
            (project_name, review_type, fingerprint, status,
             dismiss_reason, dismiss_note, decided_by, decided_at,
             context_signature, finding_snapshot)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s::jsonb)
        ON CONFLICT (project_name, review_type, fingerprint) DO UPDATE SET
            status = EXCLUDED.status,
            dismiss_reason = EXCLUDED.dismiss_reason,
            dismiss_note = EXCLUDED.dismiss_note,
            decided_by = EXCLUDED.decided_by,
            decided_at = NOW(),
            context_signature = EXCLUDED.context_signature,
            finding_snapshot = EXCLUDED.finding_snapshot,
            updated_at = NOW()
        RETURNING id
        """,
        (
            project_name, review_type, fingerprint, status,
            dismiss_reason, dismiss_note, decided_by,
            ctx_sig, snapshot_json,
        ),
        fetchone=True,
    )
    return row["id"] if row else -1


def list_decisions(
    project_name: str,
    review_type: Optional[str] = None,
    *,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Listet Entscheidungen fuer ein Projekt auf."""
    ensure_finding_decisions_schema()
    from services.db_service import execute

    conditions = ["project_name = %s"]
    params: list = [project_name]

    if review_type:
        conditions.append("review_type = %s")
        params.append(review_type)
    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    where = " AND ".join(conditions)
    rows = execute(
        f"SELECT * FROM finding_decisions WHERE {where} ORDER BY updated_at DESC",
        tuple(params),
        fetch=True,
    ) or []

    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("finding_snapshot"), str):
            d["finding_snapshot"] = json.loads(d["finding_snapshot"])
        result.append(d)
    return result


def reset_decision(project_name: str, review_type: str, fingerprint: str) -> bool:
    """Setzt eine Entscheidung auf 'pending' zurueck."""
    ensure_finding_decisions_schema()
    from services.db_service import execute

    execute(
        """
        UPDATE finding_decisions
        SET status = 'pending', decided_at = NULL, decided_by = NULL,
            dismiss_reason = NULL, dismiss_note = NULL, updated_at = NOW()
        WHERE project_name = %s AND review_type = %s AND fingerprint = %s
        """,
        (project_name, review_type, fingerprint),
    )
    return True
