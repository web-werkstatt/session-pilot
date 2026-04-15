"""
Implementierungs-Fortschritt pro Marker automatisch aus vorhandenen
Signalen berechnen — keine manuelle Eingabe, kein LLM, keine neuen Quellen.

Liefert percent (0-100) + Signal-Liste (welches Kriterium erfuellt ist).

Persistierung (Sprint sprint-impl-check-persisting): Ergebnisse werden in
`markers.implementation_percent|_signals|_checked_at` gecached. Live-Berechnung
nur bei Cache-Miss, TTL-Ablauf oder wenn `updated_at > checked_at`.
"""
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

DEFAULT_TTL_MINUTES = 5


SIGNAL_WEIGHTS = [
    ("prompt_defined", 10, "Prompt formuliert"),
    ("checks_defined", 10, "Checks definiert"),
    ("activated", 10, "Aktiviert"),
    ("session_exists", 15, "Session existiert"),
    ("commit_found", 20, "Commit vorhanden"),
    ("status_done", 15, "Auf done gesetzt"),
    ("rated_positive", 20, "Positiv bewertet (≥3)"),
]


def _has_commit(project_path, marker_id, plan_id, mode):
    """Git-log nach Marker-ID und/oder Plan-ID durchsuchen.

    mode:
      marker_id - nur nach marker_id grepen
      plan_id   - nur nach plan_id grepen (grosszuegiger)
      both      - Treffer wenn eine der beiden IDs auftaucht
    """
    if not project_path:
        return False
    needles = []
    if mode in ("marker_id", "both") and marker_id:
        needles.append(str(marker_id))
    if mode in ("plan_id", "both") and plan_id:
        needles.append(str(plan_id))
    if not needles:
        return False
    try:
        for needle in needles:
            result = subprocess.run(
                ["git", "-C", project_path, "log",
                 "--grep=" + needle, "--oneline", "-1"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    return False


def _collect_signals(marker, workflow_state, project_path, commit_mode):
    prompt_len = len(str(getattr(marker, "prompt", "") or "").strip())
    checks = getattr(marker, "checks", None) or []
    last_session = str(getattr(marker, "last_session", "") or "").strip()
    status = getattr(marker, "status", None)
    score = getattr(marker, "execution_score", None)
    ws_status = str((workflow_state or {}).get("workflow_status") or "").strip() if workflow_state else ""

    return {
        "prompt_defined": prompt_len >= 20,
        "checks_defined": len(checks) >= 1,
        "activated": ws_status in ("active", "write_back", "rating", "done") or status == "in_progress" or status == "done",
        "session_exists": bool(last_session),
        "commit_found": _has_commit(project_path, marker.marker_id, marker.plan_id, commit_mode),
        "status_done": status == "done",
        "rated_positive": score is not None and int(score) >= 3,
    }


def calculate_progress(marker, workflow_state=None, project_path=None, commit_mode="both"):
    """Liefert dict mit percent (0-100) + signals (Liste mit label, weight, done)."""
    if not marker:
        return {"percent": 0, "signals": []}
    flags = _collect_signals(marker, workflow_state, project_path, commit_mode)
    total_weight = 0
    earned = 0
    signals = []
    for key, weight, label in SIGNAL_WEIGHTS:
        done = bool(flags.get(key))
        total_weight += weight
        if done:
            earned += weight
        signals.append({"key": key, "label": label, "weight": weight, "done": done})
    percent = int(round((earned / total_weight) * 100)) if total_weight else 0
    return {"percent": percent, "signals": signals}


# ---------------------------------------------------------------------------
# DB-Cache (Sprint sprint-impl-check-persisting, Commit 2)
# ---------------------------------------------------------------------------

def _now_utc():
    return datetime.now(timezone.utc)


def _parse_ts(value):
    """DB-Timestamp auf aware datetime normalisieren."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _is_cache_fresh(checked_at, marker_updated_at, ttl_minutes):
    """Cache ist frisch wenn checked_at existiert, nicht abgelaufen und nach updated_at."""
    if not checked_at:
        return False
    if ttl_minutes and _now_utc() - checked_at > timedelta(minutes=ttl_minutes):
        return False
    if marker_updated_at and marker_updated_at > checked_at:
        return False
    return True


def _persist_progress(project_name, marker_id, percent, signals):
    """UPDATE markers SET implementation_*. Fehler werden geloggt, nicht gethrown."""
    from services.db_service import execute
    try:
        execute(
            """UPDATE markers
                  SET implementation_percent = %s,
                      implementation_signals = %s::jsonb,
                      implementation_checked_at = NOW()
                WHERE project_name = %s AND marker_id = %s""",
            (percent, json.dumps(signals), project_name, marker_id),
        )
    except Exception as exc:
        log.warning("Persist implementation-progress fehlgeschlagen fuer %s/%s: %s",
                    project_name, marker_id, exc)


def load_cached_progress_map(project_name):
    """Bulk-Load der gecachten Fortschritts-Werte pro Marker eines Projekts.

    Returns:
        dict[marker_id] -> {"percent", "signals", "checked_at", "updated_at"}
        Bei DB-Fehler leeres Dict (Aufrufer rechnet dann live).
    """
    from services.db_service import execute
    if not project_name:
        return {}
    try:
        rows = execute(
            """SELECT marker_id,
                      implementation_percent,
                      implementation_signals,
                      implementation_checked_at,
                      updated_at
                 FROM markers
                WHERE project_name = %s""",
            (project_name,),
            fetch=True,
        ) or []
    except Exception as exc:
        log.warning("load_cached_progress_map fehlgeschlagen fuer %s: %s", project_name, exc)
        return {}

    out = {}
    for row in rows:
        row = dict(row)
        signals = row.get("implementation_signals")
        if isinstance(signals, str):
            try:
                signals = json.loads(signals)
            except ValueError:
                signals = None
        out[row["marker_id"]] = {
            "percent": row.get("implementation_percent"),
            "signals": signals,
            "checked_at": _parse_ts(row.get("implementation_checked_at")),
            "updated_at": _parse_ts(row.get("updated_at")),
        }
    return out


def get_or_calculate_progress(marker, workflow_state=None, project_path=None,
                               commit_mode="both", project_name=None,
                               cached=None, ttl_minutes=DEFAULT_TTL_MINUTES):
    """Liefert Fortschritt (percent + signals) aus Cache oder berechnet live.

    Args:
        marker: Marker-Dataclass
        cached: Optional Eintrag aus load_cached_progress_map (vermeidet N+1)
        project_name: Fuer Persistierung noetig; wenn None, kein Cache-Write

    Bei Cache-Miss/-Ablauf/-Invalidation wird live gerechnet und das Ergebnis
    (wenn project_name gesetzt) in die DB geschrieben.
    """
    if not marker:
        return {"percent": 0, "signals": []}

    cache_entry = cached
    if cache_entry is None and project_name:
        from services.db_service import execute
        try:
            row = execute(
                """SELECT implementation_percent,
                          implementation_signals,
                          implementation_checked_at,
                          updated_at
                     FROM markers
                    WHERE project_name = %s AND marker_id = %s""",
                (project_name, marker.marker_id),
                fetchone=True,
            )
            if row:
                row = dict(row)
                signals = row.get("implementation_signals")
                if isinstance(signals, str):
                    try:
                        signals = json.loads(signals)
                    except ValueError:
                        signals = None
                cache_entry = {
                    "percent": row.get("implementation_percent"),
                    "signals": signals,
                    "checked_at": _parse_ts(row.get("implementation_checked_at")),
                    "updated_at": _parse_ts(row.get("updated_at")),
                }
        except Exception as exc:
            log.warning("Cache-Read fehlgeschlagen fuer %s/%s: %s",
                        project_name, marker.marker_id, exc)

    if cache_entry and cache_entry.get("percent") is not None and cache_entry.get("signals"):
        if _is_cache_fresh(cache_entry.get("checked_at"),
                           cache_entry.get("updated_at"), ttl_minutes):
            return {
                "percent": int(cache_entry["percent"]),
                "signals": cache_entry["signals"],
            }

    result = calculate_progress(marker, workflow_state=workflow_state,
                                project_path=project_path, commit_mode=commit_mode)
    if project_name:
        _persist_progress(project_name, marker.marker_id,
                          result["percent"], result["signals"])
    return result


def invalidate_implementation_progress(project_name, marker_id=None):
    """Setzt implementation_checked_at=NULL -> naechster Read rechnet neu.

    Args:
        project_name: Pflicht, wenn marker_id gesetzt. Ohne marker_id werden
                       alle Marker des Projekts invalidiert. Mit None fuer beide
                       werden ALLE Marker aller Projekte invalidiert (Settings-Change).
    """
    from services.db_service import execute
    try:
        if project_name and marker_id:
            execute(
                """UPDATE markers SET implementation_checked_at = NULL
                    WHERE project_name = %s AND marker_id = %s""",
                (project_name, marker_id),
            )
        elif project_name:
            execute(
                "UPDATE markers SET implementation_checked_at = NULL WHERE project_name = %s",
                (project_name,),
            )
        else:
            execute("UPDATE markers SET implementation_checked_at = NULL")
    except Exception as exc:
        log.warning("Invalidation fehlgeschlagen (project=%s, marker=%s): %s",
                    project_name, marker_id, exc)
