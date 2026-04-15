"""
Sprint sprint-task-backfill (2026-04-15):
Fuzzy-Match-Service fuer Bestands-Marker (task_id=NULL) gegen plan_tasks.

Design:
- Mehrstufiger Score: exakter Norm-Match (1.0) > Jaccard-Token > SequenceMatcher-Ratio
- Nur innerhalb desselben `sprint_plan_id` matchen (kein Cross-Plan)
- Score-Schwellen: 0.5 = persistieren, 0.7 = Suggestion, 0.9 = auto_apply_hint
- Suggestions sind idempotent (UNIQUE(marker_id, task_id)) — ON CONFLICT DO NOTHING
- Approve setzt `markers.task_id` und markiert Suggestion als approved
- Reject entfernt nur den Vorschlag, Marker bleibt unzugeordnet
"""
import re
from difflib import SequenceMatcher

from services.db_service import (
    ensure_plan_task_match_schema,
    ensure_plan_task_schema,
    execute,
)

PERSIST_MIN_SCORE = 0.5
AUTO_APPLY_MIN_SCORE = 0.9
_TOKEN_STOPWORDS = {"der", "die", "das", "und", "oder", "im", "in", "an", "auf", "fuer", "mit", "von", "zu", "the", "a", "an", "of", "to", "for", "and", "or"}


def _normalize(title):
    lowered = str(title or "").strip().lower()
    return re.sub(r"\s+", " ", lowered)


def _tokens(title):
    norm = re.sub(r"[^\wäöüß\s]", " ", _normalize(title))
    parts = [t for t in norm.split() if len(t) > 2 and t not in _TOKEN_STOPWORDS]
    return set(parts)


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _ratio(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _score_pair(marker_title, task_title, task_normalized):
    """Liefert (score, method). Normalized-Match = 1.0, sonst max(jaccard, ratio)."""
    marker_norm = _normalize(marker_title)
    if marker_norm and marker_norm == task_normalized:
        return 1.0, "normalized_exact"

    jacc = _jaccard(_tokens(marker_title), _tokens(task_title))
    rat = _ratio(marker_norm, task_normalized)
    if jacc >= rat:
        return round(jacc, 3), "jaccard_tokens"
    return round(rat, 3), "seq_ratio"


def _list_orphan_markers(plan_id):
    """Bestands-Marker des Plans mit task_id=NULL."""
    rows = execute(
        """
        SELECT id, titel, sprint_tag, spec_tag
        FROM markers
        WHERE sprint_plan_id = %s AND task_id IS NULL
        ORDER BY id
        """,
        (plan_id,),
        fetch=True,
    ) or []
    return [dict(r) for r in rows]


def _list_plan_tasks(plan_id):
    rows = execute(
        """
        SELECT id, section_key, spec_key, title, normalized_title
        FROM plan_tasks
        WHERE plan_id = %s
        """,
        (plan_id,),
        fetch=True,
    ) or []
    return [dict(r) for r in rows]


def compute_suggestions(plan_id):
    """
    Berechnet Match-Suggestions fuer alle Orphan-Marker eines Plans.

    - Persistiert nur score >= PERSIST_MIN_SCORE
    - Pro Marker maximal der beste Task-Treffer (vermeidet Review-Noise)
    - Idempotent via ON CONFLICT (marker_id, task_id)

    Returns: dict {created, skipped_low_score, skipped_existing, orphans, tasks}
    """
    ensure_plan_task_schema()
    ensure_plan_task_match_schema()

    orphans = _list_orphan_markers(plan_id)
    tasks = _list_plan_tasks(plan_id)

    stats = {
        "created": 0,
        "skipped_low_score": 0,
        "skipped_existing": 0,
        "orphans": len(orphans),
        "tasks": len(tasks),
    }

    if not orphans or not tasks:
        return stats

    for marker in orphans:
        best = None
        for task in tasks:
            score, method = _score_pair(
                marker["titel"], task["title"], task["normalized_title"]
            )
            if best is None or score > best[0]:
                best = (score, method, task)

        if not best:
            continue
        score, method, task = best

        if score < PERSIST_MIN_SCORE:
            stats["skipped_low_score"] += 1
            continue

        result = execute(
            """
            INSERT INTO plan_task_match_suggestions
                (marker_id, task_id, score, method, status)
            VALUES (%s, %s, %s, %s, 'pending')
            ON CONFLICT (marker_id, task_id) DO NOTHING
            RETURNING id
            """,
            (marker["id"], task["id"], score, method),
            fetchone=True,
        )
        if result:
            stats["created"] += 1
        else:
            stats["skipped_existing"] += 1

    return stats


def list_suggestions(plan_id, status="pending"):
    """Liefert Suggestions mit Marker- und Task-Kontext fuer UI."""
    ensure_plan_task_match_schema()
    rows = execute(
        """
        SELECT s.id, s.marker_id, s.task_id, s.score, s.method,
               s.status, s.created_at, s.decided_at, s.decided_by,
               m.titel AS marker_title, m.status AS marker_status,
               m.sprint_tag AS marker_sprint_tag, m.spec_tag AS marker_spec_tag,
               t.title AS task_title, t.section_key AS task_section_key,
               t.spec_key AS task_spec_key
        FROM plan_task_match_suggestions s
        JOIN markers m ON m.id = s.marker_id
        JOIN plan_tasks t ON t.id = s.task_id
        WHERE m.sprint_plan_id = %s AND s.status = %s
        ORDER BY s.score DESC, s.id
        """,
        (plan_id, status),
        fetch=True,
    ) or []
    return [_serialize(row) for row in rows]


def _serialize(row):
    if not row:
        return None
    score = float(row.get("score") or 0.0)
    return {
        "id": row["id"],
        "marker_id": row["marker_id"],
        "task_id": row["task_id"],
        "score": round(score, 3),
        "method": row.get("method") or "",
        "status": row.get("status") or "pending",
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "decided_at": row["decided_at"].isoformat() if row.get("decided_at") else None,
        "decided_by": row.get("decided_by") or None,
        "auto_apply_hint": score >= AUTO_APPLY_MIN_SCORE,
        "marker": {
            "id": row["marker_id"],
            "titel": row.get("marker_title") or "",
            "status": row.get("marker_status") or "",
            "sprint_tag": row.get("marker_sprint_tag") or "",
            "spec_tag": row.get("marker_spec_tag") or "",
        },
        "task": {
            "id": row["task_id"],
            "title": row.get("task_title") or "",
            "section_key": row.get("task_section_key") or "",
            "spec_key": row.get("task_spec_key") or "",
        },
    }


def approve(suggestion_id, decided_by=None):
    """
    Wendet Suggestion an: markers.task_id = suggestion.task_id.
    Markiert Suggestion als approved. Alle anderen pending Suggestions
    desselben Markers werden auto-rejected (ein Marker = ein Task).
    """
    ensure_plan_task_match_schema()
    sugg = execute(
        "SELECT id, marker_id, task_id, status FROM plan_task_match_suggestions WHERE id = %s",
        (suggestion_id,),
        fetchone=True,
    )
    if not sugg:
        return None
    if sugg["status"] != "pending":
        return dict(sugg)

    execute(
        "UPDATE markers SET task_id = %s WHERE id = %s",
        (sugg["task_id"], sugg["marker_id"]),
    )
    execute(
        """
        UPDATE plan_task_match_suggestions
        SET status = 'approved', decided_at = NOW(), decided_by = %s
        WHERE id = %s
        """,
        (decided_by, suggestion_id),
    )
    execute(
        """
        UPDATE plan_task_match_suggestions
        SET status = 'rejected', decided_at = NOW(),
            decided_by = COALESCE(decided_by, %s)
        WHERE marker_id = %s AND id <> %s AND status = 'pending'
        """,
        (decided_by, sugg["marker_id"], suggestion_id),
    )
    return {"id": suggestion_id, "status": "approved", "marker_id": sugg["marker_id"], "task_id": sugg["task_id"]}


def reject(suggestion_id, decided_by=None):
    ensure_plan_task_match_schema()
    row = execute(
        """
        UPDATE plan_task_match_suggestions
        SET status = 'rejected', decided_at = NOW(), decided_by = %s
        WHERE id = %s AND status = 'pending'
        RETURNING id, marker_id, task_id
        """,
        (decided_by, suggestion_id),
        fetchone=True,
    )
    return dict(row) if row else None


def auto_apply(plan_id, min_score=AUTO_APPLY_MIN_SCORE, decided_by=None):
    """Wendet alle pending Suggestions mit score >= min_score an. Returns count."""
    ensure_plan_task_match_schema()
    rows = execute(
        """
        SELECT s.id
        FROM plan_task_match_suggestions s
        JOIN markers m ON m.id = s.marker_id
        WHERE m.sprint_plan_id = %s AND s.status = 'pending' AND s.score >= %s
        ORDER BY s.score DESC, s.id
        """,
        (plan_id, min_score),
        fetch=True,
    ) or []
    applied = 0
    for row in rows:
        result = approve(row["id"], decided_by=decided_by)
        if result and result.get("status") == "approved":
            applied += 1
    return {"applied": applied, "candidates": len(rows)}


def count_orphans(plan_id):
    """Hilfsfunktion fuer UI-Refresh nach Approve."""
    row = execute(
        "SELECT COUNT(*) AS n FROM markers WHERE sprint_plan_id = %s AND task_id IS NULL",
        (plan_id,),
        fetchone=True,
    )
    return int(row["n"]) if row else 0
