"""
ADR-002 Stufe 2a: Dispatch-Reviewer (Perplexity-Integration).

Zwei Modi:
- review: bewertet ein konkretes Assignment (Risiko, Tool-Eignung, Scope)
- suggest: schlaegt Assignments fuer offene Marker vor

Perplexity schreibt NIE direkt in work_assignments. Im Review-Modus
wird das Ergebnis in `perplexity_review` JSONB gespeichert. Im
Suggest-Modus werden proposed Assignments erzeugt mit
`created_by='perplexity'`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

REVIEWER_TOOL = "perplexity"


# ---------------------------------------------------------------------------
# Context-Collectors
# ---------------------------------------------------------------------------

def build_review_context(assignment_id: int) -> Dict[str, Any]:
    """Sammelt Assignment + Marker + Tool-Profil + Policies fuer Review-Modus."""
    from services.dispatch_service import get_assignment
    from services.policy_service import get_active_policies, list_tool_profiles

    assignment = get_assignment(assignment_id)
    if not assignment:
        raise ValueError(f"Assignment {assignment_id} nicht gefunden")

    # Marker laden (falls vorhanden)
    marker = None
    if assignment.get("marker_id"):
        try:
            from services.workflow_core_service import get_marker
            marker = get_marker(assignment["marker_id"])
        except Exception:
            log.debug("Marker %s nicht ladbar", assignment["marker_id"])

    # Tool-Profil
    tool_profile = None
    if assignment.get("executor_tool"):
        profiles = list_tool_profiles(include_inactive=True)
        for p in profiles:
            if p.get("tool_id") == assignment["executor_tool"]:
                tool_profile = p
                break

    return {
        "schema_version": 1,
        "mode": "review",
        "assignment": _sanitize_assignment(assignment),
        "marker": marker,
        "tool_profile": tool_profile,
        "active_policies": [
            _policy_summary(p) for p in get_active_policies()
        ],
    }


def build_suggest_context(project_name: str) -> Dict[str, Any]:
    """Sammelt offene Marker + Tools + Policies fuer Suggest-Modus."""
    from services.dispatch_service import list_assignments
    from services.policy_service import get_active_policies, list_tool_profiles

    # Offene Marker (ohne aktives Assignment)
    open_markers = _get_open_markers(project_name)

    # Tool-Profile mit Dispatch-Settings
    profiles = list_tool_profiles(include_inactive=False)

    # Aktive Assignments (um Duplikate zu vermeiden)
    active = list_assignments(
        project_name=project_name,
        status="claimed",
    )
    approved = list_assignments(
        project_name=project_name,
        status="approved",
    )

    return {
        "schema_version": 1,
        "mode": "suggest",
        "project_name": project_name,
        "open_markers": open_markers,
        "tool_profiles": [_tool_summary(p) for p in profiles],
        "active_policies": [
            _policy_summary(p) for p in get_active_policies()
        ],
        "active_assignments": [
            _sanitize_assignment(a) for a in (active + approved)
        ],
    }


def _get_open_markers(project_name: str) -> List[Dict[str, Any]]:
    """Marker ohne aktives Assignment."""
    try:
        from services.workflow_core_service import get_markers
        all_markers = get_markers(project_name=project_name)
    except Exception:
        log.debug("Marker fuer %s nicht ladbar", project_name)
        return []

    from services.dispatch_service import list_assignments
    assigned_ids = set()
    for state in ("proposed", "approved", "claimed"):
        for a in list_assignments(project_name=project_name, status=state):
            if a.get("marker_id"):
                assigned_ids.add(a["marker_id"])

    return [m for m in all_markers if m.get("marker_id") not in assigned_ids]


def _sanitize_assignment(a: Dict[str, Any]) -> Dict[str, Any]:
    """Assignment fuer Perplexity-Context aufbereiten (keine Timestamps)."""
    return {
        "assignment_id": a.get("assignment_id"),
        "project_name": a.get("project_name"),
        "marker_id": a.get("marker_id"),
        "executor_tool": a.get("executor_tool"),
        "role_id": a.get("role_id"),
        "scope_ref": a.get("scope_ref"),
        "risk_level": a.get("risk_level"),
        "dispatch_mode": a.get("dispatch_mode"),
        "approval_state": a.get("approval_state"),
    }


def _tool_summary(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool_id": p.get("tool_id"),
        "cli": p.get("cli"),
        "model": p.get("model"),
        "strengths": p.get("strengths"),
        "weaknesses": p.get("weaknesses"),
        "dispatch_manual": p.get("dispatch_manual"),
        "dispatch_pull": p.get("dispatch_pull"),
        "max_concurrent": p.get("max_concurrent"),
    }


def _policy_summary(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role_id": p.get("role_id"),
        "tool_id": p.get("tool_id"),
        "rank": p.get("rank"),
        "confidence": p.get("confidence"),
    }


# ---------------------------------------------------------------------------
# Review-Modus
# ---------------------------------------------------------------------------

def review_assignment(
    assignment_id: int,
    query_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Bewertet ein Assignment via Perplexity (oder injected query_fn).

    Speichert Ergebnis in work_assignments.perplexity_review.
    """
    if query_fn is None:
        from services.perplexity_service import query_perplexity
        query_fn = query_perplexity

    context = build_review_context(assignment_id)
    context_hash = _compute_hash(context)

    # Dedup: bereits reviewed?
    from services.dispatch_service import get_assignment
    existing = get_assignment(assignment_id)
    if existing and existing.get("perplexity_review"):
        review = existing["perplexity_review"]
        if isinstance(review, str):
            review = json.loads(review)
        if isinstance(review, dict) and review.get("context_hash") == context_hash:
            log.info("Dispatch-Review Dedup: hash=%s", context_hash[:12])
            return {"dedup_hit": True, "review": review}

    system_prompt = _load_prompt()
    user_content = json.dumps(context, ensure_ascii=True, indent=2,
                              sort_keys=True, default=str)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response = query_fn(messages, temperature=0.0)
    except Exception as exc:
        log.exception("Dispatch-Review Query fehlgeschlagen")
        error_review = {"error": "query_failed", "detail": str(exc),
                        "context_hash": context_hash}
        _store_review(assignment_id, error_review)
        return {"error": "query_failed", "review": error_review}

    raw = response.get("content", "") if isinstance(response, dict) else ""

    try:
        parsed = _parse_response(raw)
    except Exception as exc:
        log.warning("Dispatch-Review nicht parsbar: %s", exc)
        error_review = {"error": "parse_failed", "raw_response": raw[:2000],
                        "context_hash": context_hash}
        _store_review(assignment_id, error_review)
        return {"error": "parse_failed", "review": error_review}

    parsed["context_hash"] = context_hash
    parsed["reviewer_tool"] = REVIEWER_TOOL
    _store_review(assignment_id, parsed)

    return {"error": None, "review": parsed}


def _store_review(assignment_id: int, review: Dict[str, Any]) -> None:
    """Speichert Review-Ergebnis in perplexity_review JSONB."""
    from services.db_dispatch_schema import ensure_dispatch_schema
    ensure_dispatch_schema()

    from services.db_service import execute
    execute(
        """
        UPDATE work_assignments
        SET perplexity_review = %s, updated_at = NOW()
        WHERE assignment_id = %s
        """,
        (json.dumps(review, ensure_ascii=True, default=str), assignment_id),
    )


# ---------------------------------------------------------------------------
# Suggest-Modus
# ---------------------------------------------------------------------------

def suggest_assignments(
    project_name: str,
    query_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Schlaegt Assignments fuer offene Marker vor.

    Erzeugt proposed Assignments mit created_by='perplexity'.
    """
    if query_fn is None:
        from services.perplexity_service import query_perplexity
        query_fn = query_perplexity

    context = build_suggest_context(project_name)
    context_hash = _compute_hash(context)

    if not context.get("open_markers"):
        return {"error": None, "suggestions": [],
                "note": "Keine offenen Marker"}

    system_prompt = _load_prompt()
    user_content = json.dumps(context, ensure_ascii=True, indent=2,
                              sort_keys=True, default=str)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response = query_fn(messages, temperature=0.0)
    except Exception as exc:
        log.exception("Dispatch-Suggest Query fehlgeschlagen")
        return {"error": "query_failed", "suggestions": [],
                "detail": str(exc)}

    raw = response.get("content", "") if isinstance(response, dict) else ""

    try:
        parsed = _parse_response(raw)
    except Exception as exc:
        log.warning("Dispatch-Suggest nicht parsbar: %s", exc)
        return {"error": "parse_failed", "suggestions": [],
                "raw_response": raw[:2000]}

    # Vorschlaege als proposed Assignments persistieren
    from services.dispatch_service import create_assignment

    created = []
    for sugg in parsed.get("suggested_assignments") or []:
        marker_id = sugg.get("marker_id")
        tool_id = sugg.get("executor_tool")
        if not marker_id or not tool_id:
            continue

        # Dedup: kein Assignment fuer denselben Marker+Tool wenn schon eins existiert
        if _assignment_exists(project_name, marker_id, tool_id):
            log.info("Suggest-Dedup: %s/%s existiert bereits", marker_id, tool_id)
            continue

        try:
            a = create_assignment(
                project_name=project_name,
                executor_tool=tool_id,
                marker_id=marker_id,
                role_id=sugg.get("role_id"),
                scope_ref=sugg.get("scope_ref"),
                risk_level=sugg.get("risk_level", "medium"),
                created_by="perplexity",
            )
            created.append({
                "assignment_id": a["assignment_id"],
                "marker_id": marker_id,
                "executor_tool": tool_id,
            })
        except Exception as exc:
            log.warning("Suggest: Assignment fuer %s fehlgeschlagen: %s",
                        marker_id, exc)

    return {
        "error": None,
        "suggestions": created,
        "skipped": parsed.get("skipped_markers") or [],
        "context_hash": context_hash,
    }


def _assignment_exists(project_name: str, marker_id: str,
                       executor_tool: str) -> bool:
    """Prueft ob ein nicht-terminales Assignment fuer diesen Marker+Tool existiert."""
    from services.db_dispatch_schema import ensure_dispatch_schema
    ensure_dispatch_schema()

    from services.db_service import execute
    row = execute(
        """
        SELECT 1 FROM work_assignments
        WHERE project_name = %s
          AND marker_id = %s
          AND executor_tool = %s
          AND approval_state NOT IN ('completed', 'failed', 'rejected', 'revoked', 'expired')
        LIMIT 1
        """,
        (project_name, marker_id, executor_tool),
        fetchone=True,
    )
    return row is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_hash(data: Dict[str, Any]) -> str:
    canonical = json.dumps(data, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_prompt() -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "prompts", "dispatch_reviewer.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_response(content: str) -> Dict[str, Any]:
    """Parst JSON-Antwort, akzeptiert Code-Fence-Blocks."""
    if not content:
        raise ValueError("empty content")
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Antwort ist kein JSON-Objekt")
    return parsed
