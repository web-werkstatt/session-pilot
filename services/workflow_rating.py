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


def is_rating_pending(marker):
    """True nur wenn Marker auf done, kein Score UND innerhalb RATING_PENDING_WINDOW."""
    if getattr(marker, "status", None) != "done":
        return False
    if getattr(marker, "execution_score", None) is not None:
        return False
    updated = parse_iso_ts(getattr(marker, "updated_at", None))
    if not updated:
        return False
    return datetime.now(timezone.utc) - updated <= RATING_PENDING_WINDOW
