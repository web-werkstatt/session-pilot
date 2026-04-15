"""
Aggregiert den Workflow-Loop fuer die Projekt-Control-Plane.
"""
from datetime import datetime, timezone

from services.workflow_rating import is_rating_pending as _is_rating_pending

from services.governance_service import get_governance_gate
from services.path_resolver import resolve_project_path
from services.db_service import execute
from services.workflow_core_service import get_markers as core_get_markers
from services.workflow_state_service import (
    get_allowed_transitions,
    get_workflow_states_for_project,
    sync_marker_to_workflow,
)


STEP_DEFINITIONS = [
    {"id": "gate_ready", "label": "Gate Ready", "number": 1},
    {"id": "active", "label": "Aktiv", "number": 2},
    {"id": "execution", "label": "Execution", "number": 3},
    {"id": "write_back", "label": "Write Back", "number": 4},
    {"id": "rating", "label": "Rating", "number": 5},
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

    current_marker = _build_current_marker(markers, plan_titles)
    next_marker = _build_next_marker(markers, plan_titles, current_marker)
    pending_ratings = _build_pending_ratings(markers)
    signals = _build_signals(project_name, markers, next_marker)
    current_step = _derive_current_step(markers, current_marker, next_marker, pending_ratings)
    steps = _build_steps(current_step, current_marker, next_marker)
    marker_groups = _build_marker_groups(project_name, markers, plan_titles, workflow_states, current_marker, next_marker)

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


def _build_current_marker(markers, plan_titles):
    active = next((marker for marker in markers if marker.status == "in_progress"), None)
    if active:
        return _serialize_marker_focus(active, plan_titles)

    pending = _latest_marker([marker for marker in markers if _is_rating_pending(marker)])
    if pending:
        return _serialize_marker_focus(pending, plan_titles)

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


def _build_pending_ratings(markers):
    pending = [marker for marker in markers if _is_rating_pending(marker)]
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


def _build_signals(project_name, markers, next_marker):
    gate = get_governance_gate(project_name) or {}
    quality_summary = gate.get("quality_summary") or {}
    audit_summary = gate.get("audit_summary") or {}
    next_marker_id = str((next_marker or {}).get("marker_id") or "")

    hints = []
    seen = set()

    for marker in markers:
        _append_marker_hints(hints, seen, marker)

    if next_marker_id and gate.get("status") in ("yellow", "red"):
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Governance-Risiko",
            "level": "high" if gate.get("status") == "red" else "medium",
            "hint": "bevorzugt bearbeiten",
        })

    quality_score = quality_summary.get("score_numeric")
    if next_marker_id and quality_score is not None and int(quality_score) < 60:
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Quality-Risiko",
            "level": "high" if int(quality_score) < 40 else "medium",
            "hint": "Quality-kritisch",
        })

    audit_status = str(audit_summary.get("overall_status") or "").strip()
    if next_marker_id and audit_status and audit_status.upper() in ("FAIL", "PARTIAL", "UNSICHER"):
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Audit-Risiko",
            "level": "high" if audit_status.upper() == "FAIL" else "medium",
            "hint": "bevorzugt bearbeiten",
        })

    # Dead-Code-Signal aus Quality-Report
    dead_code = quality_summary.get("dead_code_summary") or {}
    dead_total = dead_code.get("total", 0)
    if next_marker_id and dead_total > 0:
        parts = []
        if dead_code.get("unused_imports"):
            parts.append(f"{dead_code['unused_imports']} ungenutzte Imports")
        if dead_code.get("orphaned_files"):
            parts.append(f"{dead_code['orphaned_files']} verwaiste Dateien")
        if dead_code.get("unused_deps"):
            parts.append(f"{dead_code['unused_deps']} ungenutzte Dependencies")
        if dead_code.get("orphaned_assets"):
            parts.append(f"{dead_code['orphaned_assets']} verwaiste Assets")
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Dead Code",
            "level": "high" if dead_total > 20 else "medium",
            "hint": ", ".join(parts[:3]) if parts else f"{dead_total} Findings",
        })

    # Dispatch-Status pro Marker + Hints fuer unzugewiesene Marker
    try:
        from services.dispatch_service import get_dispatch_status_map
        dispatch_status = get_dispatch_status_map(project_name)
    except Exception:
        dispatch_status = {}
    for marker in markers:
        mid = marker.marker_id
        if marker.status in ("in_progress", "todo"):
            ds = dispatch_status.get(mid)
            if not ds:
                _append_hint(hints, seen, {
                    "marker_id": mid,
                    "label": "Dispatch",
                    "level": "low",
                    "hint": "Kein Tool zugewiesen",
                })

    return {
        "governance_status": gate.get("status") or "unknown",
        "audit_status": (audit_status or "unknown").lower(),
        "quality_score": quality_score if quality_score is not None else None,
        "dead_code_summary": dead_code if dead_code else None,
        "dispatch_status": dispatch_status,
        "priority_hints": hints[:8],
    }


def _derive_current_step(markers, current_marker, next_marker, pending_ratings):
    if pending_ratings:
        return "rating"
    if current_marker and current_marker.get("status") == "in_progress":
        if current_marker.get("last_session"):
            return "execution"
        return "active"
    if _latest_marker([marker for marker in markers if marker.status in ("done", "blocked")]):
        return "write_back"
    if next_marker:
        return "gate_ready"
    return "gate_ready"


def _build_steps(current_step, current_marker, next_marker):
    current_index = STEP_INDEX.get(current_step, 0)
    current_marker_id = str((current_marker or {}).get("marker_id") or "")
    next_marker_id = str((next_marker or {}).get("marker_id") or "")
    next_blocked = bool(next_marker and next_marker.get("gate_status") == "blocked")
    steps = []

    for step in STEP_DEFINITIONS:
        step_id = step["id"]
        status = "pending"
        attention_level = "none"
        marker_ref = current_marker_id or next_marker_id or ""
        cta_label = _step_cta_label(step_id, current_marker, next_marker)

        if marker_ref:
            if STEP_INDEX[step_id] < current_index:
                status = "done"
            elif STEP_INDEX[step_id] == current_index:
                if step_id == "rating":
                    status = "attention"
                    attention_level = "high"
                elif step_id == "gate_ready" and next_blocked:
                    status = "blocked"
                    attention_level = "high"
                elif step_id == "write_back":
                    status = "attention"
                    attention_level = "medium"
                else:
                    status = "active"
                    attention_level = "medium" if step_id == "execution" else "low"
            elif step_id == "gate_ready" and next_blocked:
                status = "blocked"
                attention_level = "high"

        steps.append({
            "id": step_id,
            "label": step["label"],
            "number": step["number"],
            "status": status,
            "attention_level": attention_level,
            "cta_label": cta_label,
            "marker_ref": marker_ref,
        })

    return steps


def _serialize_marker_focus(marker, plan_titles):
    gate_status = "ready" if getattr(marker, "prompt", "").strip() and len(getattr(marker, "checks", []) or []) >= 1 else "blocked"
    gate_reason = "" if gate_status == "ready" else _derive_gate_reason(marker)
    rating_pending = _is_rating_pending(marker)
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
    }


def _build_marker_groups(project_name, markers, plan_titles, workflow_states, current_marker, next_marker):
    groups = {
        "active": {"id": "active", "label": "Aktiv", "tone": "green", "cards": []},
        "waiting": {"id": "waiting", "label": "Wartet", "tone": "amber", "cards": []},
        "blocked": {"id": "blocked", "label": "Blockiert", "tone": "red", "cards": []},
    }
    current_marker_id = str((current_marker or {}).get("marker_id") or "")
    next_marker_id = str((next_marker or {}).get("marker_id") or "")

    for marker in sorted(list(markers or []), key=_marker_sort_key, reverse=True):
        card = _serialize_marker_card(project_name, marker, plan_titles, workflow_states, current_marker_id, next_marker_id)
        groups[card["group"]]["cards"].append(card)

    return [groups["active"], groups["waiting"], groups["blocked"]]


def _serialize_marker_card(project_name, marker, plan_titles, workflow_states, current_marker_id, next_marker_id):
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
        "rating_pending": _is_rating_pending(marker),
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "checks_count": len(getattr(marker, "checks", []) or []),
        "allowed_transitions": allowed.get("allowed", []),
        "is_current": marker.marker_id == current_marker_id,
        "is_next": marker.marker_id == next_marker_id,
        "updated_at": getattr(marker, "updated_at", "") or "",
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


def _append_marker_hints(hints, seen, marker):
    risk_text = str(getattr(marker, "risiko", "") or "").lower()
    if "governance" in risk_text:
        _append_hint(hints, seen, {
            "marker_id": marker.marker_id,
            "label": "Governance-Risiko",
            "level": "high" if "red" in risk_text else "medium",
            "hint": "bevorzugt bearbeiten",
        })
    if "audit" in risk_text:
        _append_hint(hints, seen, {
            "marker_id": marker.marker_id,
            "label": "Audit-Risiko",
            "level": "high" if "fail" in risk_text else "medium",
            "hint": "bevorzugt bearbeiten",
        })
    if "quality" in risk_text:
        _append_hint(hints, seen, {
            "marker_id": marker.marker_id,
            "label": "Quality-Risiko",
            "level": "high" if "krit" in risk_text or "red" in risk_text else "medium",
            "hint": "Quality-kritisch",
        })


def _append_hint(hints, seen, item):
    key = (item["marker_id"], item["label"], item["hint"])
    if key in seen:
        return
    seen.add(key)
    hints.append(item)


def _marker_has_signal(marker, signal_name):
    risk_text = str(getattr(marker, "risiko", "") or "").lower()
    return signal_name in risk_text


def _derive_gate_reason(marker):
    if not getattr(marker, "prompt", "").strip():
        return "prompt ist leer"
    if len(getattr(marker, "checks", []) or []) < 1:
        return "keine checks definiert"
    return ""


def _step_cta_label(step_id, current_marker, next_marker):
    if step_id == "rating":
        return "Rating nachholen" if current_marker and current_marker.get("rating_pending") else "Verlauf ansehen"
    if step_id == "write_back": return "Abschluss vorbereiten"
    if step_id == "execution": return "Thread fortsetzen" if current_marker else "Execution oeffnen"
    if step_id == "active": return "Execution oeffnen"
    return "Marker pruefen"


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
