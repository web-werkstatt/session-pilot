"""
Rating-Fenster-Logik fuer den Workflow-Loop.

Retrospektives Rating ist wertlos — wer einen Marker nicht zeitnah nach
Abschluss bewertet, hat die Erinnerung verloren und wuerde raten. Daher
schneiden wir das Pending-Signal nach einem Zeitfenster ab. Alte done-
Marker ohne Rating bleiben in der DB (NULL), triggern aber keine Hints
mehr und werden nicht als "abzuarbeiten" angezeigt.
"""
from datetime import datetime, timedelta, timezone

RATING_PENDING_WINDOW = timedelta(hours=48)


def parse_iso_ts(value):
    """ISO-Timestamp tolerant parsen (inkl. 'Z'-Suffix, TZ-Fallback UTC)."""
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def is_rating_pending(marker, done_since=None):
    """True nur wenn Marker done, kein Score, Session existiert UND < 48h
    seit Done-Transition.

    done_since: Timestamp der letzten done-Transition (str ISO oder datetime).
    Vorzugsweise aus marker_workflow_states.completed_at. Fallback auf
    marker.updated_at, aber dieser kippt bei jeder Feldaenderung — daher
    unzuverlaessig und nur Notloesung.

    Zusaetzliche Bedingung last_session: ohne aktive Session gibt es keine
    Ausfuehrung zu bewerten (z.B. Marker manuell auf done gesetzt ohne Lauf).
    """
    if getattr(marker, "status", None) != "done":
        return False
    if getattr(marker, "execution_score", None) is not None:
        return False
    if getattr(marker, "rating_skipped", False):
        return False
    if not str(getattr(marker, "last_session", "") or "").strip():
        return False
    ref = done_since if done_since is not None else getattr(marker, "updated_at", None)
    ref_dt = parse_iso_ts(ref) if not hasattr(ref, "tzinfo") else ref
    if not ref_dt:
        return False
    return datetime.now(timezone.utc) - ref_dt <= RATING_PENDING_WINDOW


def get_done_since(workflow_state):
    """Liest completed_at aus einem Workflow-State-Dict (marker_workflow_states)."""
    if not workflow_state:
        return None
    val = workflow_state.get("completed_at") if isinstance(workflow_state, dict) else None
    if val is None:
        return None
    return val if hasattr(val, "tzinfo") else parse_iso_ts(val)
