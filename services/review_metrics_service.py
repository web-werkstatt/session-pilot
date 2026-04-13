"""
Review-Metriken-Service: Aggregiert Counter-Daten aus allen Reviewern.

Liefert KPIs fuer das Metrics-Dashboard:
- Signal-Ratio (shown / generated)
- Dismiss-Rate (filtered_dismissed / generated)
- Noise-Rate (alle gefilterten / generated)
- Finding-Decision-Statistiken
- Policy-Suggestion-Statistiken
- Per-Projekt-Breakdown fuer Charts
"""
from __future__ import annotations

import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


def get_review_metrics() -> Dict[str, Any]:
    """Aggregiert Review-Metriken aus allen Quellen."""
    setup = _get_setup_review_metrics()
    cwo = _get_cwo_review_metrics()
    decisions = _get_finding_decision_stats()
    policy = _get_policy_suggestion_stats()

    # Globale KPIs berechnen
    total_generated = setup["total_generated"] + cwo["total_generated"]
    total_shown = setup["total_shown"] + cwo["total_shown"]
    total_filtered = (
        setup["total_filtered_dismissed"]
        + setup["total_filtered_low_conf"]
        + cwo["total_filtered_low_conf"]
    )

    signal_ratio = round(total_shown / total_generated, 3) if total_generated else 1.0
    noise_rate = round(total_filtered / total_generated, 3) if total_generated else 0.0
    dismiss_filter_rate = (
        round(setup["total_filtered_dismissed"] / total_generated, 3)
        if total_generated
        else 0.0
    )

    return {
        "kpis": {
            "signal_ratio": signal_ratio,
            "noise_rate": noise_rate,
            "dismiss_filter_rate": dismiss_filter_rate,
            "total_generated": total_generated,
            "total_shown": total_shown,
            "total_filtered": total_filtered,
            "decision_dismiss_rate": decisions["dismiss_rate"],
            "decision_approve_rate": decisions["approve_rate"],
            "policy_reject_rate": policy["reject_rate"],
        },
        "setup_reviews": setup,
        "cwo_reviews": cwo,
        "decisions": decisions,
        "policy_suggestions": policy,
    }


def _get_setup_review_metrics() -> Dict[str, Any]:
    """Aggregiert Counter aus project_reviews."""
    from services.db_service import execute
    from services.db_tool_setup_review_schema import ensure_tool_setup_review_schema

    ensure_tool_setup_review_schema()

    row = execute(
        """
        SELECT
            COUNT(*) AS review_count,
            COALESCE(SUM(generated_count), 0) AS total_generated,
            COALESCE(SUM(shown_count), 0) AS total_shown,
            COALESCE(SUM(filtered_dismissed_count), 0) AS total_filtered_dismissed,
            COALESCE(SUM(filtered_low_confidence_count), 0) AS total_filtered_low_conf
        FROM project_reviews
        WHERE error IS NULL
        """,
        fetchone=True,
    )

    per_project = execute(
        """
        SELECT project_name,
               COALESCE(generated_count, 0) AS generated,
               COALESCE(shown_count, 0) AS shown,
               COALESCE(filtered_dismissed_count, 0) AS filtered_dismissed,
               COALESCE(filtered_low_confidence_count, 0) AS filtered_low_conf,
               updated_at
        FROM project_reviews
        WHERE error IS NULL
        ORDER BY updated_at DESC
        """,
        fetch=True,
    ) or []

    return {
        "review_count": row["review_count"] if row else 0,
        "total_generated": row["total_generated"] if row else 0,
        "total_shown": row["total_shown"] if row else 0,
        "total_filtered_dismissed": row["total_filtered_dismissed"] if row else 0,
        "total_filtered_low_conf": row["total_filtered_low_conf"] if row else 0,
        "per_project": [dict(r) for r in per_project],
    }


def _get_cwo_review_metrics() -> Dict[str, Any]:
    """Aggregiert Counter aus cwo_analyses (nur Zeilen mit Review)."""
    from services.db_service import execute, ensure_cwo_schema

    ensure_cwo_schema()

    row = execute(
        """
        SELECT
            COUNT(*) AS review_count,
            COALESCE(SUM(generated_count), 0) AS total_generated,
            COALESCE(SUM(shown_count), 0) AS total_shown,
            COALESCE(SUM(filtered_low_confidence_count), 0) AS total_filtered_low_conf,
            SUM(CASE WHEN low_confidence_warning THEN 1 ELSE 0 END) AS low_conf_warnings
        FROM cwo_analyses
        WHERE perplexity_review IS NOT NULL AND error IS NULL
        """,
        fetchone=True,
    )

    per_project = execute(
        """
        SELECT project_name,
               COALESCE(generated_count, 0) AS generated,
               COALESCE(shown_count, 0) AS shown,
               COALESCE(filtered_low_confidence_count, 0) AS filtered_low_conf,
               COALESCE(low_confidence_warning, FALSE) AS low_conf_warning,
               perplexity_confidence AS confidence,
               updated_at
        FROM cwo_analyses
        WHERE perplexity_review IS NOT NULL AND error IS NULL
        ORDER BY updated_at DESC
        """,
        fetch=True,
    ) or []

    return {
        "review_count": row["review_count"] if row else 0,
        "total_generated": row["total_generated"] if row else 0,
        "total_shown": row["total_shown"] if row else 0,
        "total_filtered_low_conf": row["total_filtered_low_conf"] if row else 0,
        "low_conf_warnings": row["low_conf_warnings"] if row else 0,
        "per_project": [dict(r) for r in per_project],
    }


def _get_finding_decision_stats() -> Dict[str, Any]:
    """Statistiken aus finding_decisions."""
    from services.db_finding_decisions_schema import ensure_finding_decisions_schema
    from services.db_service import execute

    ensure_finding_decisions_schema()

    rows = execute(
        """
        SELECT status, COUNT(*) AS cnt
        FROM finding_decisions
        GROUP BY status
        """,
        fetch=True,
    ) or []

    by_status = {r["status"]: r["cnt"] for r in rows}
    total = sum(by_status.values())
    dismissed = by_status.get("dismissed", 0)
    approved = by_status.get("approved", 0)

    # Noisiest findings: Die am haeufigsten ueber Projekte hinweg auftauchenden
    noisiest = execute(
        """
        SELECT fingerprint, review_type,
               finding_snapshot->>'title' AS title,
               finding_snapshot->>'severity' AS severity,
               COUNT(DISTINCT project_name) AS project_count,
               COUNT(*) AS total_decisions
        FROM finding_decisions
        GROUP BY fingerprint, review_type,
                 finding_snapshot->>'title',
                 finding_snapshot->>'severity'
        HAVING COUNT(DISTINCT project_name) >= 1
        ORDER BY COUNT(DISTINCT project_name) DESC, COUNT(*) DESC
        LIMIT 10
        """,
        fetch=True,
    ) or []

    return {
        "total": total,
        "by_status": by_status,
        "dismiss_rate": round(dismissed / total, 3) if total else 0.0,
        "approve_rate": round(approved / total, 3) if total else 0.0,
        "noisiest_findings": [dict(r) for r in noisiest],
    }


def _get_policy_suggestion_stats() -> Dict[str, Any]:
    """Statistiken aus policy_review_suggestions."""
    from services.db_policy_schema import ensure_policy_schema
    from services.db_service import execute

    ensure_policy_schema()

    rows = execute(
        """
        SELECT status, COUNT(*) AS cnt
        FROM policy_review_suggestions
        GROUP BY status
        """,
        fetch=True,
    ) or []

    by_status = {r["status"]: r["cnt"] for r in rows}
    total = sum(by_status.values())
    rejected = by_status.get("rejected", 0)

    return {
        "total": total,
        "by_status": by_status,
        "reject_rate": round(rejected / total, 3) if total else 0.0,
        "pending_count": by_status.get("pending", 0),
    }
