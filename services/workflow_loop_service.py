"""
Aggregiert den Workflow-Loop fuer die Projekt-Control-Plane.
"""
from datetime import datetime, timezone

from services.workflow_rating import is_rating_pending as _is_rating_pending, get_done_since
from services.marker_implementation import calculate_progress as _calculate_progress
from services.dashboard_settings_service import get_commit_match_mode

from services.path_resolver import resolve_project_path
from services.db_service import execute
from services.workflow_core_service import get_markers as core_get_markers
from services.workflow_state_service import (
    get_allowed_transitions,
    get_workflow_states_for_project,
    sync_marker_to_workflow,
)
from services.workflow_loop_signals import build_signals as _build_signals


STEP_DEFINITIONS = [
    {
        "id": "gate_prompt", "number": 1,
        "label": "Prompt",
        "title": "Prompt formulieren",
        "description": "Der Marker braucht eine klare Anweisung fuer Claude Code, bevor er aktiviert werden kann.",
        "cta_label": "Prompt bearbeiten",
        "tab": "output", "focus": "prompt",
    },
    {
        "id": "gate_checks", "number": 2,
        "label": "Checks",
        "title": "Checks definieren",
        "description": "Mindestens ein Abnahme-Check (Definition of Done) fehlt. Im Prompt-Abschnitt ergaenzen.",
        "cta_label": "Checks ergaenzen",
        "tab": "output", "focus": "prompt",
    },
    {
        "id": "ready", "number": 3,
        "label": "Bereit",
        "title": "Marker aktivieren",
        "description": "Prompt und Checks sind bereit. Kontext fuer Claude Code schreiben und Session starten.",
        "cta_label": "Aktivieren",
        "action": "activate",
    },
    {
        "id": "running", "number": 4,
        "label": "Session",
        "title": "Session laeuft",
        "description": "Thread fortsetzen oder bei Fertigstellung abschliessen und bewerten.",
        "cta_label": "Thread oeffnen",
        "tab": "chat",
        "secondary": {"label": "Abschliessen + bewerten", "action": "close_with_rating"},
    },
    {
        "id": "close", "number": 5,
        "label": "Abschluss",
        "title": "Abschliessen + bewerten",
        "description": "Marker ist fertig, Bewertung steht noch aus. Jetzt bewerten, solange die Erinnerung frisch ist.",
        "cta_label": "Jetzt bewerten",
        "action": "close_with_rating",
        "secondary": {"label": "Ignorieren", "action": "skip_rating"},
    },
]

STEP_INDEX = {step["id"]: index for index, step in enumerate(STEP_DEFINITIONS)}


def build_workflow_loop_data(project_name):
    project_name = str(project_name or "").strip()
    if not project_name:
        raise FileNotFoundError("project_missing")

    project_path = resolve_project_path(project_name)
    if not project_path:
        raise FileNotFoundError(project_name)

    markers = list(core_get_markers(project_name) or [])
    plan_titles = _load_plan_titles(project_name)

    # Sync: Marker-Status aus handoff.md in persistierten Workflow-State uebernehmen
    _sync_markers_to_workflow(project_name, markers)
    workflow_states = _load_workflow_states_map(project_name)

    commit_mode = get_commit_match_mode()
    current_marker = _build_current_marker(markers, plan_titles, workflow_states, project_path, commit_mode)
    next_marker = _build_next_marker(markers, plan_titles, current_marker)
    pending_ratings = _build_pending_ratings(markers, workflow_states)
    signals = _build_signals(project_name, markers, next_marker)
    current_step = _derive_current_step(markers, current_marker, next_marker, pending_ratings)
    steps = _build_steps(current_step, current_marker, next_marker)
    marker_groups = _build_marker_groups(project_name, markers, plan_titles, workflow_states, current_marker, next_marker, project_path, commit_mode)

    return {
        "project_id": project_name,
        "project_label": project_name,
        "current_step": current_step,
        "steps": steps,
        "current_marker": current_marker,
        "next_marker": next_marker,
        "signals": signals,
        "pending_ratings": pending_ratings,
        "workflow_states": workflow_states,
        "marker_groups": marker_groups,
    }


def _load_plan_titles(project_name):
    rows = execute(
        """SELECT id, title
           FROM project_plans
           WHERE project_name = %s""",
        (project_name,),
        fetch=True,
    ) or []
    return {str(row.get("id")): row.get("title") or f"Plan {row.get('id')}" for row in rows}


def _build_current_marker(markers, plan_titles, workflow_states=None, project_path=None, commit_mode="both"):
    active = next((marker for marker in markers if marker.status == "in_progress"), None)
    if active:
        return _serialize_marker_focus(active, plan_titles, workflow_states, project_path, commit_mode)

    ws = workflow_states or {}
    pending = _latest_marker([
        marker for marker in markers
        if _is_rating_pending(marker, get_done_since(ws.get(marker.marker_id)))
    ])
    if pending:
        return _serialize_marker_focus(pending, plan_titles, workflow_states, project_path, commit_mode)

    return {}


def _build_next_marker(markers, plan_titles, current_marker):
    current_marker_id = str((current_marker or {}).get("marker_id") or "")
    for marker in markers:
        if marker.marker_id == current_marker_id:
            continue
        if marker.status not in ("todo", "blocked"):
            continue
        gate_status = "ready" if getattr(marker, "prompt", "").strip() and len(getattr(marker, "checks", []) or []) >= 1 else "blocked"
        gate_reason = "" if gate_status == "ready" else _derive_gate_reason(marker)
        recommendation_reason = "Gate bereit fuer Aktivierung"
        if gate_status == "blocked":
            recommendation_reason = "Gate blockiert: " + gate_reason
        elif _marker_has_signal(marker, "governance"):
            recommendation_reason = "wegen Governance-Risiko bevorzugt bearbeiten"
        elif _marker_has_signal(marker, "audit"):
            recommendation_reason = "wegen Audit-Risiko bevorzugt bearbeiten"
        elif _marker_has_signal(marker, "quality"):
            recommendation_reason = "wegen Quality-Risiko bevorzugt bearbeiten"
        return {
            "marker_id": marker.marker_id,
            "title": marker.titel,
            "status": marker.status,
            "recommended": gate_status == "ready",
            "recommendation_reason": recommendation_reason,
            "plan_id": str(marker.plan_id or ""),
            "plan_title": plan_titles.get(str(marker.plan_id), f"Plan {marker.plan_id}"),
            "gate_status": gate_status,
            "gate_reason": gate_reason,
        }
    return {}


def _build_pending_ratings(markers, workflow_states=None):
    ws = workflow_states or {}
    pending = [
        marker for marker in markers
        if _is_rating_pending(marker, get_done_since(ws.get(marker.marker_id)))
    ]
    pending.sort(key=_marker_sort_key, reverse=True)
    result = []
    for marker in pending[:5]:
        result.append({
            "marker_id": marker.marker_id,
            "title": marker.titel,
            "status_label": "Abschluss unvollstaendig",
            "cta_label": "Rating nachholen",
            "plan_id": str(marker.plan_id or ""),
        })
    return result


def _derive_current_step(markers, current_marker, next_marker, pending_ratings):
    # Abschluss + Bewertung offen -> Step 5
    if pending_ratings:
        return "close"
    # Aktive Session -> Step 4
    if current_marker and current_marker.get("status") == "in_progress":
        return "running"
    # Naechster Marker vorhanden: Gate pruefen
    if next_marker:
        gr = str(next_marker.get("gate_reason", "") or "").lower()
        if "prompt" in gr:
            return "gate_prompt"
        if "check" in gr:
            return "gate_checks"
        return "ready"
    # Current ohne Session, aber todo/in_progress -> "ready" als Default
    return "ready"


def _build_steps(current_step, current_marker, next_marker):
    current_index = STEP_INDEX.get(current_step, 0)
    current_marker_id = str((current_marker or {}).get("marker_id") or "")
    next_marker_id = str((next_marker or {}).get("marker_id") or "")
    steps = []

    for step in STEP_DEFINITIONS:
        step_id = step["id"]
        idx = STEP_INDEX[step_id]
        marker_ref = current_marker_id or next_marker_id or ""

        if idx < current_index:
            status, attention_level = "done", "none"
        elif idx == current_index:
            if step_id in ("gate_prompt", "gate_checks"):
                status, attention_level = "blocked", "high"
            elif step_id == "close":
                status, attention_level = "attention", "high"
            else:
                status, attention_level = "active", "medium"
        else:
            status, attention_level = "pending", "none"

        entry = {
            "id": step_id,
            "label": step["label"],
            "number": step["number"],
            "title": step["title"],
            "description": step["description"],
            "status": status,
            "attention_level": attention_level,
            "cta_label": step["cta_label"],
            "marker_ref": marker_ref,
        }
        if "tab" in step: entry["tab"] = step["tab"]
        if "focus" in step: entry["focus"] = step["focus"]
        if "action" in step: entry["action"] = step["action"]
        if "secondary" in step: entry["secondary"] = step["secondary"]
        steps.append(entry)

    return steps


def _serialize_marker_focus(marker, plan_titles, workflow_states=None, project_path=None, commit_mode="both"):
    gate_status = "ready" if getattr(marker, "prompt", "").strip() and len(getattr(marker, "checks", []) or []) >= 1 else "blocked"
    gate_reason = "" if gate_status == "ready" else _derive_gate_reason(marker)
    ws = (workflow_states or {}).get(marker.marker_id) if workflow_states else None
    done_since = get_done_since(ws)
    rating_pending = _is_rating_pending(marker, done_since)
    impl = _calculate_progress(marker, ws, project_path, commit_mode)
    return {
        "marker_id": marker.marker_id,
        "title": marker.titel,
        "status": marker.status,
        "next_step": marker.naechster_schritt,
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "plan_id": str(marker.plan_id or ""),
        "plan_title": plan_titles.get(str(marker.plan_id), f"Plan {marker.plan_id}"),
        "last_session": marker.last_session or "",
        "execution_score": marker.execution_score,
        "rating_pending": rating_pending,
        "done_since": done_since.isoformat() if done_since else None,
        "implementation_percent": impl["percent"],
        "implementation_signals": impl["signals"],
    }


def _build_marker_groups(project_name, markers, plan_titles, workflow_states, current_marker, next_marker, project_path=None, commit_mode="both"):
    groups = {
        "active": {"id": "active", "label": "Aktiv", "tone": "green", "cards": []},
        "waiting": {"id": "waiting", "label": "Wartet", "tone": "amber", "cards": []},
        "blocked": {"id": "blocked", "label": "Blockiert", "tone": "red", "cards": []},
    }
    current_marker_id = str((current_marker or {}).get("marker_id") or "")
    next_marker_id = str((next_marker or {}).get("marker_id") or "")

    for marker in sorted(list(markers or []), key=_marker_sort_key, reverse=True):
        card = _serialize_marker_card(project_name, marker, plan_titles, workflow_states, current_marker_id, next_marker_id, project_path, commit_mode)
        groups[card["group"]]["cards"].append(card)

    return [groups["active"], groups["waiting"], groups["blocked"]]


def _serialize_marker_card(project_name, marker, plan_titles, workflow_states, current_marker_id, next_marker_id, project_path=None, commit_mode="both"):
    plan_id = str(marker.plan_id or "")
    gate_ready = bool(getattr(marker, "prompt", "").strip() and len(getattr(marker, "checks", []) or []) >= 1)
    gate_status = "ready" if gate_ready else "blocked"
    gate_reason = "" if gate_ready else _derive_gate_reason(marker)
    state = workflow_states.get(marker.marker_id) or {}
    workflow_status = str(state.get("workflow_status") or _derive_card_status(marker, gate_ready)).strip() or "planned"
    try:
        allowed = get_allowed_transitions(project_name, marker.marker_id)
    except Exception:
        allowed = {
            "current_status": workflow_status,
            "allowed": _fallback_allowed_transitions(workflow_status),
            "owner": state.get("owner"),
            "blocked_reason": state.get("blocked_reason"),
        }

    impl = _calculate_progress(marker, state, project_path, commit_mode)
    return {
        "marker_id": marker.marker_id,
        "title": marker.titel,
        "goal": marker.ziel,
        "next_step": marker.naechster_schritt,
        "plan_id": plan_id,
        "plan_title": plan_titles.get(plan_id, f"Plan {marker.plan_id}"),
        "marker_status": marker.status,
        "workflow_status": workflow_status,
        "workflow_status_label": _workflow_status_label(workflow_status),
        "group": _workflow_group(workflow_status),
        "owner": state.get("owner") or "",
        "blocked_reason": state.get("blocked_reason") or "",
        "last_session": state.get("last_session") or marker.last_session or "",
        "execution_score": marker.execution_score,
        "execution_comment": marker.execution_comment or "",
        "rating_pending": _is_rating_pending(marker, get_done_since(state)),
        "done_since": (get_done_since(state).isoformat() if get_done_since(state) else None),
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "checks_count": len(getattr(marker, "checks", []) or []),
        "allowed_transitions": allowed.get("allowed", []),
        "is_current": marker.marker_id == current_marker_id,
        "is_next": marker.marker_id == next_marker_id,
        "updated_at": getattr(marker, "updated_at", "") or "",
        "implementation_percent": impl["percent"],
        "implementation_signals": impl["signals"],
    }


_FALLBACK_TRANSITIONS = {
    "planned": ["blocked", "ready"], "ready": ["active", "blocked", "planned"],
    "active": ["blocked", "write_back"], "write_back": ["active", "blocked", "rating"],
    "rating": ["active", "done"], "done": ["active"],
    "blocked": ["planned", "ready", "active"],
}


def _fallback_allowed_transitions(workflow_status):
    return _FALLBACK_TRANSITIONS.get(str(workflow_status or "").strip(), [])


def _derive_card_status(marker, gate_ready):
    st = marker.status
    if st == "in_progress": return "active"
    if st == "blocked": return "blocked"
    if st == "done": return "rating" if marker.execution_score is None else "done"
    if st == "todo": return "ready" if gate_ready else "planned"
    return "planned"


_WORKFLOW_GROUPS = {"blocked": "blocked", "active": "active",
                    "write_back": "waiting", "rating": "waiting"}


def _workflow_group(workflow_status):
    return _WORKFLOW_GROUPS.get(str(workflow_status or "").strip(), "waiting")


_WORKFLOW_LABELS = {
    "planned": "Noch nicht bereit", "ready": "Bereit zum Start",
    "active": "Aktiv in Execution", "write_back": "Write Back offen",
    "rating": "Rating offen", "done": "Sauber abgeschlossen", "blocked": "Blockiert",
}


def _workflow_status_label(workflow_status):
    return _WORKFLOW_LABELS.get(str(workflow_status or "").strip(), workflow_status or "Unbekannt")


def _marker_has_signal(marker, signal_name):
    risk_text = str(getattr(marker, "risiko", "") or "").lower()
    return signal_name in risk_text


def _derive_gate_reason(marker):
    if not getattr(marker, "prompt", "").strip():
        return "prompt ist leer"
    if len(getattr(marker, "checks", []) or []) < 1:
        return "keine checks definiert"
    return ""


def _latest_marker(markers):
    items = list(markers or [])
    if not items:
        return None
    items.sort(key=_marker_sort_key, reverse=True)
    return items[0]


def _marker_sort_key(marker):
    value = str(getattr(marker, "updated_at", "") or "").strip()
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _sync_markers_to_workflow(project_name, markers):
    """Synchronisiert alle Marker-Statuses in die persistierte Workflow-State-Tabelle."""
    for marker in markers:
        try:
            sync_marker_to_workflow(
                project_name,
                marker.marker_id,
                marker.status,
                last_session=marker.last_session or None,
                gate_ready=bool(getattr(marker, "prompt", "").strip() and len(getattr(marker, "checks", []) or []) >= 1),
                execution_score=getattr(marker, "execution_score", None),
            )
        except Exception:
            pass  # Sync-Fehler duerfen den Loop nicht blockieren


def _load_workflow_states_map(project_name):
    """Laedt alle Workflow-States als dict {marker_id: state}."""
    try:
        states = get_workflow_states_for_project(project_name)
        return {s["marker_id"]: s for s in states}
    except Exception:
        return {}
