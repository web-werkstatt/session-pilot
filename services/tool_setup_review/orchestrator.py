"""
ADR-002 Stufe 1a: Review-Orchestrator.

Orchestriert den Review-Flow: Context-Collect -> Perplexity-Call -> Parsing
-> Storage. Dependency-Injection fuer Tests via `query_fn`.

Parse-Fehler werden persistiert, nicht geworfen, damit der UI-Pfad immer
einen Zustand anzeigen kann.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from services.tool_setup_review.constants import (
    REVIEW_TYPE,
    REVIEWER_TOOL_DEFAULT,
    SCHEMA_VERSION,
    TOOL_FILES,
)
from services.tool_setup_review.context_collector import build_tool_setup_context
from services.tool_setup_review.storage import load_review, save_review

log = logging.getLogger(__name__)


def review_tool_setup(
    project_name: str,
    query_fn: Optional[Callable] = None,
    *,
    force: bool = False,
    now_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Fuehrt einen Setup-Review aus.

    Args:
        project_name: Projekt, das reviewed werden soll.
        query_fn: Optional. Reviewer-Query-Function. Default ist
                  `services.perplexity_service.query_perplexity`. Tests
                  injizieren hier eine Fake-Function.
        force: Wenn True, wird der Review auch bei identischem context_hash
               erneut durchgefuehrt.
        now_fn: Optional fuer Tests. Liefert aktuellen Zeitstempel.

    Returns:
        Review-Ergebnis als Dict (wie in der DB gespeichert).
    """
    if query_fn is None:
        from services.perplexity_service import query_perplexity

        query_fn = query_perplexity

    context = build_tool_setup_context(project_name)
    if context is None:
        return {
            "project_name": project_name,
            "error": "project_not_found",
            "setup_ok": None,
        }

    context_hash = _compute_context_hash(context)

    if not force:
        existing = load_review(project_name)
        if existing and existing.get("context_hash") == context_hash:
            existing["dedup_hit"] = True
            return existing

    system_prompt = _load_system_prompt()
    user_content = json.dumps(context, ensure_ascii=True, indent=2, sort_keys=True)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    reviewed_tools = sorted(TOOL_FILES.keys())

    try:
        response = query_fn(messages, temperature=0.0)
    except Exception as e:
        result = {
            "project_name": project_name,
            "review_type": REVIEW_TYPE,
            "schema_version": SCHEMA_VERSION,
            "setup_ok": None,
            "priority": None,
            "summary": None,
            "findings": [],
            "suggested_blocks": {},
            "project_json_patch": None,
            "implementation_scope": None,
            "notes": [],
            "context_drift": context.get("context_drift"),
            "context_hash": context_hash,
            "reviewer_tool": REVIEWER_TOOL_DEFAULT,
            "reviewed_tools": reviewed_tools,
            "reviewer_model": None,
            "raw_response": str(e),
            "error": "query_failed",
        }
        save_review(project_name, result, now_fn=now_fn)
        return result

    raw_content = response.get("content", "") if isinstance(response, dict) else ""
    reviewer_model = response.get("model") if isinstance(response, dict) else None

    try:
        parsed = _parse_reviewer_response(raw_content)
    except Exception as e:
        result = {
            "project_name": project_name,
            "review_type": REVIEW_TYPE,
            "schema_version": SCHEMA_VERSION,
            "setup_ok": None,
            "priority": None,
            "summary": None,
            "findings": [],
            "suggested_blocks": {},
            "project_json_patch": None,
            "implementation_scope": None,
            "notes": [f"parse_error: {e}"],
            "context_drift": context.get("context_drift"),
            "context_hash": context_hash,
            "reviewer_tool": REVIEWER_TOOL_DEFAULT,
            "reviewed_tools": reviewed_tools,
            "reviewer_model": reviewer_model,
            "raw_response": raw_content,
            "error": "parse_failed",
        }
        save_review(project_name, result, now_fn=now_fn)
        return result

    # --- Dismiss-Filter + Confidence-Filter (Issue #23) ---
    from services.finding_decision_service import (
        compute_finding_fingerprint,
        compute_context_signature,
        get_dismissed_fingerprints,
        is_finding_dismissed,
        parse_confidence,
    )

    raw_findings = parsed.get("findings") or []
    dismissed = get_dismissed_fingerprints(project_name, REVIEW_TYPE)
    filtered_findings = []
    filtered_dismissed_count = 0
    filtered_low_confidence_count = 0

    for f in raw_findings:
        fp = compute_finding_fingerprint(project_name, REVIEW_TYPE, f)
        ctx_sig = compute_context_signature(f, REVIEW_TYPE)

        if is_finding_dismissed(fp, ctx_sig, dismissed):
            filtered_dismissed_count += 1
            continue

        confidence = parse_confidence(f.get("confidence"))
        if confidence > 0 and confidence < 50:
            filtered_low_confidence_count += 1
            log.info(
                "Setup-Finding gefiltert (confidence=%d < 50): %s",
                confidence, f.get("title", "?"),
            )
            continue

        filtered_findings.append(f)

    if filtered_dismissed_count or filtered_low_confidence_count:
        log.info(
            "Setup-Review %s: %d dismissed, %d low-confidence gefiltert (von %d)",
            project_name, filtered_dismissed_count,
            filtered_low_confidence_count, len(raw_findings),
        )

    result = {
        "project_name": project_name,
        "review_type": REVIEW_TYPE,
        "schema_version": parsed.get("schema_version", SCHEMA_VERSION),
        "setup_ok": parsed.get("setup_ok"),
        "priority": parsed.get("priority"),
        "summary": parsed.get("summary"),
        "findings": filtered_findings,
        "suggested_blocks": parsed.get("suggested_blocks") or {},
        "project_json_patch": parsed.get("suggested_project_json_patch"),
        "implementation_scope": parsed.get("implementation_scope"),
        "notes": parsed.get("notes") or [],
        "context_drift": context.get("context_drift"),
        "context_hash": context_hash,
        "reviewer_tool": REVIEWER_TOOL_DEFAULT,
        "reviewed_tools": reviewed_tools,
        "reviewer_model": reviewer_model,
        "raw_response": raw_content,
        "error": None,
        "filtered_dismissed_count": filtered_dismissed_count,
        "filtered_low_confidence_count": filtered_low_confidence_count,
    }
    save_review(project_name, result, now_fn=now_fn)
    return result


def _compute_context_hash(context: Dict[str, Any]) -> str:
    """Deterministischer SHA256-Hash ueber den Context-Snapshot."""
    canonical = json.dumps(context, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_system_prompt() -> str:
    """Laedt den Reviewer-System-Prompt als Markdown-Datei."""
    here = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    prompt_path = os.path.join(here, "prompts", "setup_reviewer.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        log.error("Setup-Reviewer-Prompt nicht lesbar: %s (%s)", prompt_path, e)
        raise


def _parse_reviewer_response(content: str) -> Dict[str, Any]:
    """Parst die Reviewer-Antwort als JSON.

    Akzeptiert sowohl reines JSON als auch JSON in einem Code-Fence-Block
    (```json ... ```).
    """
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
