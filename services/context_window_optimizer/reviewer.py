"""
CWO Sprint Ticket 1.10: Perplexity-Reviewer fuer Context Window Optimizer.

Orchestriert den Review-Flow:
- Laedt bestehende Analyse aus cwo_analyses (Findings + Migration-Map)
- Baut Review-Input zusammen (ohne Datei-Inhalte, nur Metadaten)
- Ruft Perplexity auf mit dem CWO-Prompt
- Parst die JSON-Antwort (Migration-Assessments)
- Persistiert Review in cwo_analyses (perplexity_review, perplexity_confidence)

context_hash-Dedup: Wenn sich an der Analyse nichts geaendert hat,
wird das bestehende Review zurueckgegeben (force=True uebergeht das).

Perplexity schreibt NIE direkt in Projektdateien. Das Review ist
eine Bewertung, die Joseph als Entscheidungsgrundlage dient.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from services.context_window_optimizer.constants import (
    REVIEWER_TOOL_DEFAULT,
    SCHEMA_VERSION,
)
from services.context_window_optimizer.storage import (
    load_analysis,
    load_review,
    save_review,
)

log = logging.getLogger(__name__)


def review_project(
    project_name: str,
    query_fn: Optional[Callable] = None,
    *,
    force: bool = False,
    now_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Fuehrt ein Perplexity-Review fuer eine bestehende CWO-Analyse durch.

    Args:
        project_name: Name des Projekts unter /mnt/projects/.
        query_fn: Optional. Default: perplexity_service.query_perplexity.
                  Tests injizieren eine Fake-Function.
        force: Wenn True, wird auch bei identischem review_context_hash
               neu reviewed.
        now_fn: Optional fuer Tests (Timestamp-Provider).

    Returns:
        Dict mit perplexity_review, perplexity_confidence,
        review_context_hash, error, reviewer_tool, reviewer_model.
    """
    if query_fn is None:
        from services.perplexity_service import query_perplexity
        query_fn = query_perplexity

    # 1. Bestehende Analyse laden
    analysis = load_analysis(project_name)
    if not analysis:
        return _error_result(project_name, "no_analysis")

    if analysis.get("error"):
        return _error_result(project_name, "analysis_has_error")

    # 2. Review-Input zusammenbauen
    review_input = _build_review_input(analysis)
    review_hash = _compute_review_hash(review_input)

    # 3. Dedup-Check
    if not force:
        existing = load_review(project_name)
        if existing and existing.get("review_context_hash") == review_hash:
            return {
                "project_name": project_name,
                "perplexity_review": existing.get("perplexity_review"),
                "perplexity_confidence": existing.get("perplexity_confidence"),
                "review_context_hash": review_hash,
                "reviewer_tool": REVIEWER_TOOL_DEFAULT,
                "reviewer_model": None,
                "error": None,
                "dedup_hit": True,
            }

    # 4. Prompt laden + Perplexity aufrufen
    system_prompt = _load_system_prompt()
    user_content = json.dumps(review_input, ensure_ascii=True, indent=2, sort_keys=True)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        response = query_fn(messages, temperature=0.0)
    except Exception as exc:
        log.exception("CWO-Review Query fehlgeschlagen: %s", project_name)
        result = _error_result(
            project_name, "query_failed", raw_response=str(exc),
            review_hash=review_hash,
        )
        save_review(project_name, result, now_fn=now_fn)
        return result

    raw_content = response.get("content", "") if isinstance(response, dict) else ""
    reviewer_model = response.get("model") if isinstance(response, dict) else None

    # 5. JSON-Antwort parsen
    try:
        parsed = _parse_reviewer_response(raw_content)
    except Exception as exc:
        log.warning("CWO-Reviewer-Antwort nicht parsbar: %s (%s)", project_name, exc)
        result = _error_result(
            project_name, "parse_failed", raw_response=raw_content,
            review_hash=review_hash, reviewer_model=reviewer_model,
        )
        save_review(project_name, result, now_fn=now_fn)
        return result

    # 6. Ergebnis zusammenbauen + Confidence/Dismiss-Filter (Issue #23)
    from services.finding_decision_service import parse_confidence

    confidence = parse_confidence(parsed.get("overall_confidence"))
    low_confidence_warning = confidence > 0 and confidence < 30

    if low_confidence_warning:
        log.warning(
            "CWO-Review %s: overall_confidence=%d < 30, low_confidence_warning gesetzt",
            project_name, confidence,
        )

    # Migration-Assessments mit Confidence < 50 filtern
    assessments = parsed.get("migration_assessments") or []
    filtered_assessments = []
    filtered_low_confidence_count = 0

    for ma in assessments:
        ma_conf = parse_confidence(ma.get("confidence"))
        if ma_conf > 0 and ma_conf < 50:
            filtered_low_confidence_count += 1
            log.info(
                "CWO-Migration-Assessment gefiltert (confidence=%d < 50): %s",
                ma_conf, ma.get("section_title", "?"),
            )
            continue
        filtered_assessments.append(ma)

    if filtered_low_confidence_count:
        log.info(
            "CWO-Review %s: %d low-confidence Assessments gefiltert (von %d)",
            project_name, filtered_low_confidence_count, len(assessments),
        )

    parsed["migration_assessments"] = filtered_assessments

    result = {
        "project_name": project_name,
        "perplexity_review": parsed,
        "perplexity_confidence": confidence,
        "review_context_hash": review_hash,
        "reviewer_tool": REVIEWER_TOOL_DEFAULT,
        "reviewer_model": reviewer_model,
        "error": None,
        "raw_response": raw_content,
        "low_confidence_warning": low_confidence_warning,
        "filtered_low_confidence_count": filtered_low_confidence_count,
    }

    save_review(project_name, result, now_fn=now_fn)
    return result


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _build_review_input(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Baut den Review-Input aus einer bestehenden Analyse zusammen.

    Entfernt Datei-Inhalte (content-Felder), behaelt nur Metadaten
    die Perplexity zur Bewertung braucht.
    """
    findings = analysis.get("findings") or []
    cleaned_findings = []
    for f in findings:
        cleaned = {k: v for k, v in f.items() if k != "content"}
        cleaned_findings.append(cleaned)

    return {
        "schema_version": SCHEMA_VERSION,
        "project_name": analysis.get("project_name", ""),
        "total_tokens": analysis.get("total_tokens", 0),
        "token_budget_rating": analysis.get("token_budget_rating", "ok"),
        "findings": cleaned_findings,
        "migration_map": analysis.get("migration_map") or [],
        "file_inventory": analysis.get("file_inventory") or [],
    }


def _compute_review_hash(review_input: Dict[str, Any]) -> str:
    """Deterministischer SHA256-Hash ueber den Review-Input fuer Dedup."""
    canonical = json.dumps(review_input, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _load_system_prompt() -> str:
    """Laedt den Perplexity-Prompt aus prompts/context_window_optimizer.md."""
    # reviewer.py ist unter services/context_window_optimizer/ -> 3x dirname zum Projekt-Root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prompt_path = os.path.join(project_root, "prompts", "context_window_optimizer.md")
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


def _error_result(
    project_name: str,
    error: str,
    *,
    raw_response: str = "",
    review_hash: str = "",
    reviewer_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Erstellt ein standardisiertes Error-Ergebnis."""
    return {
        "project_name": project_name,
        "perplexity_review": None,
        "perplexity_confidence": None,
        "review_context_hash": review_hash,
        "reviewer_tool": REVIEWER_TOOL_DEFAULT,
        "reviewer_model": reviewer_model,
        "error": error,
        "raw_response": raw_response,
    }
