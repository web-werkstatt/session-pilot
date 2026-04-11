"""
ADR-002 Stufe 1b: Policy-Reviewer.

Orchestriert den Policy-Review-Flow:
- Collector liest aktuelle Rollen, Tool-Profile und aktive Policies
  (read-only, aus policy_service)
- Reviewer-Call via Perplexity (oder injected query_fn fuer Tests)
- Parser wandelt strukturierte Antwort in Suggestions
- Persistiert jede Suggestion in policy_review_suggestions mit
  context_hash-Dedup

Perplexity schreibt NIE direkt in role_tool_policies. Der einzige
Schreibpfad in die aktive Policy-Tabelle ist der Approval-Pfad in
policy_service.apply_suggestion, den Joseph manuell triggert.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from services.policy_service import (
    get_active_policies,
    list_roles,
    list_tool_profiles,
    record_suggestion,
)

log = logging.getLogger(__name__)

REVIEWER_TOOL_DEFAULT = "perplexity"


# ---------------------------------------------------------------------------
# Observe: Context-Collector
# ---------------------------------------------------------------------------

def build_policy_review_context() -> Dict[str, Any]:
    """Sammelt Rollen, Tool-Profile und aktive Policies als Input fuer den Reviewer.

    Reine Leseoperation. Keine Bewertung, keine Heuristik.
    """
    roles = list_roles(include_inactive=False)
    tool_profiles = list_tool_profiles(include_inactive=False)
    policies = get_active_policies()

    return {
        "schema_version": 1,
        "roles": [_role_summary(r) for r in roles],
        "tool_profiles": [_tool_profile_summary(p) for p in tool_profiles],
        "active_policies": [_policy_summary(p) for p in policies],
    }


def _role_summary(role: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role_id": role.get("role_id"),
        "name": role.get("name"),
        "description": role.get("description"),
    }


def _tool_profile_summary(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool_id": profile.get("tool_id"),
        "cli": profile.get("cli"),
        "model": profile.get("model"),
        "provider": profile.get("provider"),
        "strengths": profile.get("strengths"),
        "weaknesses": profile.get("weaknesses"),
        "notes": profile.get("notes"),
    }


def _policy_summary(policy: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role_id": policy.get("role_id"),
        "tool_id": policy.get("tool_id"),
        "rank": policy.get("rank"),
        "confidence": policy.get("confidence"),
        "source": policy.get("source"),
        "rationale": policy.get("rationale"),
    }


# ---------------------------------------------------------------------------
# Review: Orchestrator
# ---------------------------------------------------------------------------

def review_policies(query_fn: Optional[Callable] = None) -> Dict[str, Any]:
    """Fuehrt einen Policy-Review aus.

    Args:
        query_fn: Optional. Reviewer-Query-Function. Default ist
                  services.perplexity_service.query_perplexity. Tests
                  injizieren eine Fake-Function.

    Returns:
        Dict mit summary, persistierten Suggestions (mit suggestion_id)
        und error (query_failed / parse_failed / None).
    """
    if query_fn is None:
        from services.perplexity_service import query_perplexity
        query_fn = query_perplexity

    context = build_policy_review_context()
    context_hash = _compute_context_hash(context)

    system_prompt = _load_system_prompt()
    user_content = json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response = query_fn(messages, temperature=0.0)
    except Exception as exc:
        log.exception("Policy-Review Query fehlgeschlagen")
        return {
            "schema_version": 1,
            "summary": None,
            "suggestions": [],
            "notes": [],
            "reviewer_tool": REVIEWER_TOOL_DEFAULT,
            "reviewer_model": None,
            "context_hash": context_hash,
            "error": "query_failed",
            "raw_response": str(exc),
        }

    raw_content = response.get("content", "") if isinstance(response, dict) else ""
    reviewer_model = response.get("model") if isinstance(response, dict) else None

    try:
        parsed = _parse_reviewer_response(raw_content)
    except Exception as exc:
        log.warning("Policy-Reviewer-Antwort nicht parsbar: %s", exc)
        return {
            "schema_version": 1,
            "summary": None,
            "suggestions": [],
            "notes": [],
            "reviewer_tool": REVIEWER_TOOL_DEFAULT,
            "reviewer_model": reviewer_model,
            "context_hash": context_hash,
            "error": "parse_failed",
            "raw_response": raw_content,
        }

    persisted: List[Dict[str, Any]] = []
    for sugg in parsed.get("suggestions") or []:
        suggestion_type = sugg.get("suggestion_type")
        if not suggestion_type:
            continue
        sid = record_suggestion(
            reviewer_tool=REVIEWER_TOOL_DEFAULT,
            suggestion_type=suggestion_type,
            payload=sugg.get("payload") or {},
            rationale=sugg.get("rationale"),
            evidence=sugg.get("evidence"),
            context_hash=context_hash,
        )
        persisted.append({
            "suggestion_id": sid,
            "suggestion_type": suggestion_type,
            "payload": sugg.get("payload") or {},
        })

    return {
        "schema_version": parsed.get("schema_version", 1),
        "summary": parsed.get("summary"),
        "suggestions": persisted,
        "notes": parsed.get("notes") or [],
        "reviewer_tool": REVIEWER_TOOL_DEFAULT,
        "reviewer_model": reviewer_model,
        "context_hash": context_hash,
        "error": None,
    }


def _compute_context_hash(context: Dict[str, Any]) -> str:
    """Deterministischer SHA256-Hash ueber den Context-Snapshot."""
    canonical = json.dumps(context, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_system_prompt() -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(here, "prompts", "policy_reviewer.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_reviewer_response(content: str) -> Dict[str, Any]:
    """Parst die Reviewer-Antwort als JSON. Akzeptiert optionale Code-Fence-Blocks."""
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
        raise ValueError("Reviewer antwortete nicht mit JSON-Objekt")
    return parsed
