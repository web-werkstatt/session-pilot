"""
Implementierungs-Fortschritt pro Marker automatisch aus vorhandenen
Signalen berechnen — keine manuelle Eingabe, kein LLM, keine neuen Quellen.

Liefert percent (0-100) + Signal-Liste (welches Kriterium erfuellt ist).
"""
import subprocess


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
