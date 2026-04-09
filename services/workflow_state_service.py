"""
Sprint Workflow-v2: Persistente Workflow-Zustandslogik mit Transition-Regeln.

Statuses: planned, ready, active, write_back, rating, done, blocked
"""
from datetime import datetime, timezone

from services.db_service import ensure_workflow_state_schema, execute


# --- Erlaubte Uebergaenge ---------------------------------------------------

VALID_STATUSES = {"planned", "ready", "active", "write_back", "rating", "done", "blocked"}

# from_status -> set of allowed to_statuses
ALLOWED_TRANSITIONS = {
    "planned":    {"ready", "blocked"},
    "ready":      {"active", "blocked", "planned"},
    "active":     {"write_back", "blocked"},
    "write_back": {"rating", "blocked", "active"},
    "rating":     {"done", "active"},
    "done":       {"active"},           # Reaktivierung
    "blocked":    {"planned", "ready", "active"},
}

# Welche Felder bei Statuswechsel automatisch gesetzt werden
_AUTO_FIELDS = {
    "active":     lambda now: {"started_at": now},
    "done":       lambda now: {"completed_at": now},
    "write_back": lambda _: {},
    "rating":     lambda _: {},
    "blocked":    lambda _: {},
    "planned":    lambda _: {"started_at": None, "completed_at": None},
    "ready":      lambda _: {"completed_at": None},
}


# --- CRUD --------------------------------------------------------------------

def get_workflow_state(project_name, marker_id):
    """Liest den persistierten Workflow-State eines Markers."""
    ensure_workflow_state_schema()
    row = execute(
        """SELECT * FROM marker_workflow_states
           WHERE project_name = %s AND marker_id = %s""",
        (project_name, marker_id),
        fetchone=True,
    )
    return dict(row) if row else None


def get_workflow_states_for_project(project_name):
    """Alle persistierten Workflow-States eines Projekts."""
    ensure_workflow_state_schema()
    rows = execute(
        """SELECT * FROM marker_workflow_states
           WHERE project_name = %s
           ORDER BY last_transition_at DESC""",
        (project_name,),
        fetch=True,
    ) or []
    return [dict(r) for r in rows]


def ensure_workflow_state(project_name, marker_id, initial_status="planned"):
    """Erstellt einen Workflow-State falls noch keiner existiert. Gibt den State zurueck."""
    ensure_workflow_state_schema()
    existing = get_workflow_state(project_name, marker_id)
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    execute(
        """INSERT INTO marker_workflow_states
               (project_name, marker_id, workflow_status, created_at, updated_at, last_transition_at)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (project_name, marker_id) DO NOTHING""",
        (project_name, marker_id, initial_status, now, now, now),
    )
    return get_workflow_state(project_name, marker_id)


def transition_workflow(project_name, marker_id, to_status, *,
                        triggered_by="user", reason=None, owner=None,
                        blocked_reason=None, last_session=None):
    """Fuehrt einen Statuswechsel durch, wenn er gueltig ist.

    Returns:
        dict mit neuem State bei Erfolg

    Raises:
        ValueError bei ungueltigem Uebergang
    """
    ensure_workflow_state_schema()
    to_status = str(to_status).strip()
    if to_status not in VALID_STATUSES:
        raise ValueError(f"Ungueltiger Zielstatus: {to_status}")

    state = ensure_workflow_state(project_name, marker_id)
    from_status = state["workflow_status"]

    if from_status == to_status:
        return state  # Idempotent: gleicher Status ist kein Fehler

    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(
            f"Uebergang {from_status} -> {to_status} nicht erlaubt. "
            f"Erlaubt: {', '.join(sorted(allowed))}"
        )

    now = datetime.now(timezone.utc)

    # Auto-Felder berechnen
    auto = _AUTO_FIELDS.get(to_status, lambda _: {})(now)

    # Update-Felder zusammenbauen
    update_parts = [
        "workflow_status = %s",
        "last_transition_at = %s",
        "updated_at = %s",
    ]
    params = [to_status, now, now]

    if "started_at" in auto:
        update_parts.append("started_at = %s")
        params.append(auto["started_at"])
    if "completed_at" in auto:
        update_parts.append("completed_at = %s")
        params.append(auto["completed_at"])

    if owner is not None:
        update_parts.append("owner = %s")
        params.append(owner)

    if to_status == "blocked" and blocked_reason:
        update_parts.append("blocked_reason = %s")
        params.append(str(blocked_reason).strip())
    elif to_status != "blocked":
        update_parts.append("blocked_reason = NULL")

    if last_session is not None:
        update_parts.append("last_session = %s")
        params.append(str(last_session).strip())

    params.extend([project_name, marker_id])

    execute(
        f"""UPDATE marker_workflow_states
            SET {', '.join(update_parts)}
            WHERE project_name = %s AND marker_id = %s""",
        tuple(params),
    )

    # Transition-Log
    execute(
        """INSERT INTO workflow_transitions
               (project_name, marker_id, from_status, to_status, triggered_by, reason)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (project_name, marker_id, from_status, to_status,
         triggered_by or "user", reason),
    )

    return get_workflow_state(project_name, marker_id)


def get_allowed_transitions(project_name, marker_id):
    """Gibt erlaubte naechste Schritte fuer einen Marker zurueck."""
    state = get_workflow_state(project_name, marker_id)
    if not state:
        return {"current_status": None, "allowed": []}
    current = state["workflow_status"]
    allowed = sorted(ALLOWED_TRANSITIONS.get(current, set()))
    return {
        "current_status": current,
        "allowed": allowed,
        "owner": state.get("owner"),
        "blocked_reason": state.get("blocked_reason"),
    }


def get_transition_history(project_name, marker_id, limit=20):
    """Gibt die Transition-Historie eines Markers zurueck."""
    ensure_workflow_state_schema()
    rows = execute(
        """SELECT * FROM workflow_transitions
           WHERE project_name = %s AND marker_id = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (project_name, marker_id, limit),
        fetch=True,
    ) or []
    return [dict(r) for r in rows]


def sync_marker_to_workflow(project_name, marker_id, marker_status, last_session=None, gate_ready=None, execution_score=None):
    """Synchronisiert den Marker-Status (aus handoff.md) in den Workflow-State.

    Mappt die bestehenden Marker-Statuses auf Workflow-Statuses:
      todo       -> planned
      in_progress -> active
      done       -> done (oder rating, wenn kein Score)
      blocked    -> blocked
    """
    marker_status = str(marker_status or "").strip()
    current_state = get_workflow_state(project_name, marker_id)

    mapped = _derive_sync_target_status(
        marker_status,
        current_state.get("workflow_status") if current_state else None,
        gate_ready=gate_ready,
        execution_score=execution_score,
    )
    if not mapped:
        return None

    if not current_state:
        return ensure_workflow_state(project_name, marker_id, initial_status=mapped)

    current = current_state["workflow_status"]
    if current == mapped:
        # Nur last_session updaten falls noetig
        if last_session and current_state.get("last_session") != last_session:
            execute(
                """UPDATE marker_workflow_states
                   SET last_session = %s, updated_at = NOW()
                   WHERE project_name = %s AND marker_id = %s""",
                (last_session, project_name, marker_id),
            )
        return get_workflow_state(project_name, marker_id)

    # Versuch den Uebergang — bei ungueltigem Pfad ueberspringen
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if mapped in allowed:
        return transition_workflow(
            project_name, marker_id, mapped,
            triggered_by="sync",
            reason=f"Sync aus handoff.md (marker_status={marker_status})",
            last_session=last_session,
        )

    return state


def _derive_sync_target_status(marker_status, current_status=None, gate_ready=None, execution_score=None):
    marker_status = str(marker_status or "").strip()
    current_status = str(current_status or "").strip()

    if marker_status == "todo":
        return "ready" if gate_ready else "planned"

    if marker_status == "in_progress":
        if current_status == "write_back":
            return "write_back"
        return "active"

    if marker_status == "done":
        if execution_score is None:
            if current_status == "write_back":
                return "write_back"
            return "rating"
        return "done"

    if marker_status == "blocked":
        return "blocked"

    return None
