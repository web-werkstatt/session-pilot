"""
ADR-002 Stufe 2a: Dispatch-Service Core.

CRUD + vollstaendiger Lifecycle fuer work_assignments.
Jede State-Transition wird im dispatch_audit_log protokolliert.
Atomic Claim via single UPDATE mit WHERE-Guard (Race-Condition-Schutz).
"""
from typing import Any, Dict, List, Optional

from services.db_dispatch_schema import ensure_dispatch_schema

# Erlaubte State-Transitions (Stufe 2a, kein 'dispatched')
ALLOWED_TRANSITIONS = {
    "proposed": ["approved", "rejected"],
    "approved": ["claimed", "revoked", "expired"],
    "claimed": ["completed", "failed"],
}

# Terminale Zustaende — keine weiteren Transitions moeglich
TERMINAL_STATES = {"completed", "failed", "rejected", "revoked", "expired"}


def _execute(sql, params=None, fetch=False, fetchone=False):
    """Lazy Import von db_service.execute."""
    from services.db_service import execute
    return execute(sql, params, fetch=fetch, fetchone=fetchone)


def _log_transition(assignment_id: int, from_state: Optional[str],
                    to_state: str, changed_by: str,
                    reason: Optional[str] = None) -> None:
    """Schreibt einen Eintrag in dispatch_audit_log."""
    _execute(
        """
        INSERT INTO dispatch_audit_log
            (assignment_id, from_state, to_state, changed_by, reason)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (assignment_id, from_state, to_state, changed_by, reason),
    )


def _validate_transition(current: str, target: str) -> None:
    """Wirft ValueError wenn Transition nicht erlaubt."""
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise ValueError(
            f"Transition {current!r} -> {target!r} nicht erlaubt. "
            f"Erlaubt: {allowed}"
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_assignment(
    project_name: str,
    executor_tool: str,
    marker_id: Optional[str] = None,
    role_id: Optional[str] = None,
    scope_ref: Optional[Dict] = None,
    input_payload: Optional[Dict] = None,
    risk_level: str = "medium",
    automation_level: int = 1,
    dispatch_mode: str = "manual",
    approval_required: bool = True,
    allowed_write_scope: Optional[List] = None,
    timeout_hours: Optional[int] = None,
    created_by: str = "joseph",
) -> Dict[str, Any]:
    """Legt ein neues Assignment mit status=proposed an."""
    ensure_dispatch_schema()
    import json

    timeout_expr = "NULL"
    params = [
        project_name, marker_id, role_id, executor_tool,
        json.dumps(scope_ref or {}),
        json.dumps(input_payload or {}),
        risk_level, automation_level, dispatch_mode,
        approval_required, "proposed",
        json.dumps(allowed_write_scope or []),
        created_by,
    ]

    if timeout_hours:
        timeout_expr = "NOW() + INTERVAL '%s hours'"
        params.append(timeout_hours)

    # Baue SQL dynamisch fuer optionalen timeout_at
    timeout_col = ", timeout_at" if timeout_hours else ""
    timeout_val = f", {timeout_expr}" if timeout_hours else ""

    row = _execute(
        f"""
        INSERT INTO work_assignments
            (project_name, marker_id, role_id, executor_tool,
             scope_ref, input_payload, risk_level, automation_level,
             dispatch_mode, approval_required, approval_state,
             allowed_write_scope, created_by{timeout_col})
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s{timeout_val})
        RETURNING *
        """,
        params,
        fetchone=True,
    )

    _log_transition(row["assignment_id"], None, "proposed", created_by)
    return dict(row)


def get_assignment(assignment_id: int) -> Optional[Dict[str, Any]]:
    """Einzelnes Assignment laden."""
    ensure_dispatch_schema()
    row = _execute(
        "SELECT * FROM work_assignments WHERE assignment_id = %s",
        (assignment_id,),
        fetchone=True,
    )
    return dict(row) if row else None


def list_assignments(
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    executor_tool: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Gefilterte Assignment-Liste."""
    ensure_dispatch_schema()
    conditions = []
    params: list = []

    if project_name:
        conditions.append("project_name = %s")
        params.append(project_name)
    if status:
        conditions.append("approval_state = %s")
        params.append(status)
    if executor_tool:
        conditions.append("executor_tool = %s")
        params.append(executor_tool)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    rows = _execute(
        f"""
        SELECT * FROM work_assignments
        {where}
        ORDER BY created_at DESC
        LIMIT %s
        """,
        params,
        fetch=True,
    )
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# Lifecycle-Transitions
# ---------------------------------------------------------------------------

def _transition(assignment_id: int, target_state: str,
                changed_by: str, reason: Optional[str] = None,
                extra_sets: Optional[str] = None,
                extra_params: Optional[list] = None) -> Dict[str, Any]:
    """Generischer Transition-Helper mit Validierung + Audit."""
    ensure_dispatch_schema()
    current = _execute(
        "SELECT approval_state FROM work_assignments WHERE assignment_id = %s",
        (assignment_id,),
        fetchone=True,
    )
    if not current:
        raise ValueError(f"Assignment {assignment_id} nicht gefunden")

    from_state = current["approval_state"]
    _validate_transition(from_state, target_state)

    sets = "approval_state = %s, updated_at = NOW()"
    params: list = [target_state]

    if extra_sets:
        sets += ", " + extra_sets
        params.extend(extra_params or [])

    params.append(assignment_id)
    row = _execute(
        f"""
        UPDATE work_assignments
        SET {sets}
        WHERE assignment_id = %s
        RETURNING *
        """,
        params,
        fetchone=True,
    )

    _log_transition(assignment_id, from_state, target_state, changed_by, reason)
    return dict(row)


def approve_assignment(assignment_id: int,
                       approved_by: str = "joseph") -> Dict[str, Any]:
    """proposed -> approved"""
    return _transition(assignment_id, "approved", approved_by)


def reject_assignment(assignment_id: int, rejected_by: str = "joseph",
                      reason: Optional[str] = None) -> Dict[str, Any]:
    """proposed -> rejected"""
    return _transition(assignment_id, "rejected", rejected_by, reason)


def revoke_assignment(assignment_id: int, revoked_by: str = "joseph",
                      reason: Optional[str] = None) -> Dict[str, Any]:
    """approved -> revoked"""
    return _transition(assignment_id, "revoked", revoked_by, reason)


def complete_assignment(assignment_id: int,
                        result_ref: Optional[Dict] = None) -> Dict[str, Any]:
    """claimed -> completed"""
    import json
    extra = "completed_at = NOW(), result_ref = %s"
    return _transition(
        assignment_id, "completed", "system", None,
        extra_sets=extra,
        extra_params=[json.dumps(result_ref) if result_ref else None],
    )


def fail_assignment(assignment_id: int,
                    reason: Optional[str] = None) -> Dict[str, Any]:
    """claimed -> failed"""
    return _transition(
        assignment_id, "failed", "system", reason,
        extra_sets="completed_at = NOW()",
    )


# ---------------------------------------------------------------------------
# Atomic Claim (Race-Condition-Schutz)
# ---------------------------------------------------------------------------

def claim_assignment(assignment_id: int,
                     claimed_by: str) -> Dict[str, Any]:
    """approved -> claimed. Atomar via single UPDATE mit WHERE-Guard.

    Prueft:
    1. Assignment ist approved UND noch nicht geclaimed
    2. Tool-Profil hat dispatch_pull oder dispatch_manual erlaubt
    3. max_concurrent nicht ueberschritten

    Gibt das geclaimte Assignment zurueck oder wirft ValueError (nicht
    gefunden / falscher State) bzw. RuntimeError (bereits geclaimed /
    max_concurrent erreicht).
    """
    ensure_dispatch_schema()

    # Atomarer UPDATE: nur wenn approved + unclaimed + max_concurrent ok
    row = _execute(
        """
        UPDATE work_assignments wa
        SET approval_state = 'claimed',
            claimed_at = NOW(),
            claimed_by = %s,
            updated_at = NOW()
        WHERE wa.assignment_id = %s
          AND wa.approval_state = 'approved'
          AND wa.claimed_at IS NULL
          AND (
              SELECT COUNT(*) FROM work_assignments wa2
              WHERE wa2.executor_tool = wa.executor_tool
                AND wa2.approval_state = 'claimed'
          ) < (
              SELECT COALESCE(tp.max_concurrent, 1)
              FROM tool_profiles tp
              WHERE tp.tool_id = wa.executor_tool
          )
        RETURNING *
        """,
        (claimed_by, assignment_id),
        fetchone=True,
    )

    if not row:
        # Grund ermitteln: existiert nicht, falscher State, oder Race?
        existing = _execute(
            "SELECT approval_state, claimed_at, executor_tool "
            "FROM work_assignments WHERE assignment_id = %s",
            (assignment_id,),
            fetchone=True,
        )
        if not existing:
            raise ValueError(f"Assignment {assignment_id} nicht gefunden")
        if existing["approval_state"] != "approved":
            raise ValueError(
                f"Assignment {assignment_id} ist im State "
                f"{existing['approval_state']!r}, nicht 'approved'"
            )
        if existing["claimed_at"] is not None:
            raise RuntimeError(
                f"Assignment {assignment_id} wurde bereits geclaimed "
                f"(Race Condition)"
            )
        # Sonst: max_concurrent erreicht
        raise RuntimeError(
            f"max_concurrent fuer Tool {existing['executor_tool']!r} erreicht"
        )

    _log_transition(
        assignment_id, "approved", "claimed", claimed_by, "atomic claim"
    )
    return dict(row)


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------

def expire_stale_assignments() -> int:
    """Setzt approved Assignments mit timeout_at < NOW() auf expired.

    Gibt Anzahl betroffener Assignments zurueck.
    """
    ensure_dispatch_schema()
    rows = _execute(
        """
        UPDATE work_assignments
        SET approval_state = 'expired', updated_at = NOW()
        WHERE approval_state = 'approved'
          AND timeout_at IS NOT NULL
          AND timeout_at < NOW()
        RETURNING assignment_id
        """,
        fetch=True,
    )
    expired = rows or []
    for r in expired:
        _log_transition(r["assignment_id"], "approved", "expired",
                        "system", "timeout")
    return len(expired)


# ---------------------------------------------------------------------------
# Audit-Log lesen
# ---------------------------------------------------------------------------

def get_audit_log(assignment_id: int) -> List[Dict[str, Any]]:
    """Audit-Trail fuer ein Assignment."""
    ensure_dispatch_schema()
    rows = _execute(
        """
        SELECT * FROM dispatch_audit_log
        WHERE assignment_id = %s
        ORDER BY created_at
        """,
        (assignment_id,),
        fetch=True,
    )
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# Dispatch-Settings (Commit 5)
# ---------------------------------------------------------------------------

_SETTINGS_DEFAULTS = {
    "perplexity_mode": "review_only",
    "auto_expire_hours": 48,
}


def get_effective_settings(
    project_name: Optional[str] = None,
    tool_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Merged Settings: global -> project -> tool (spezifischste gewinnt).

    Fehlende Scopes fallen auf den naechst-allgemeineren zurueck.
    """
    ensure_dispatch_schema()

    scopes = [("global", None)]
    if project_name:
        scopes.append(("project", project_name))
    if tool_id:
        scopes.append(("tool", tool_id))

    merged = dict(_SETTINGS_DEFAULTS)

    for scope, ref in scopes:
        row = _execute(
            "SELECT * FROM dispatch_settings "
            "WHERE scope = %s AND scope_ref = %s",
            (scope, ref or ""),
            fetchone=True,
        )
        if row:
            row = dict(row)
            for key in ("perplexity_mode", "auto_expire_hours"):
                if row.get(key) is not None:
                    merged[key] = row[key]
            merged["_source_scope"] = scope
            merged["_source_ref"] = ref

    return merged


def update_settings(
    scope: str,
    scope_ref: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Upsert fuer Dispatch-Settings.

    scope: 'global' | 'project' | 'tool'
    scope_ref: None (global), project_name, oder tool_id
    kwargs: perplexity_mode, auto_expire_hours
    """
    ensure_dispatch_schema()

    # NULL -> '' normalisieren (UNIQUE-Constraint braucht NOT NULL)
    ref = scope_ref or ""

    allowed_keys = {"perplexity_mode", "auto_expire_hours"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_keys}

    if not updates:
        raise ValueError("Keine gueltigen Felder zum Aktualisieren")

    cols = list(updates.keys())
    vals = list(updates.values())
    set_parts = ", ".join(f"{k} = EXCLUDED.{k}" for k in cols)

    row = _execute(
        f"""
        INSERT INTO dispatch_settings (scope, scope_ref, {', '.join(cols)})
        VALUES (%s, %s, {', '.join(['%s'] * len(vals))})
        ON CONFLICT (scope, scope_ref)
        DO UPDATE SET {set_parts}, updated_at = NOW()
        RETURNING *
        """,
        [scope, ref] + vals,
        fetchone=True,
    )
    return dict(row) if row else {}


def is_dispatch_allowed(tool_id: str, mode: str) -> bool:
    """Prueft ob ein Dispatch-Modus fuer ein Tool erlaubt ist.

    mode: 'manual' | 'pull' | 'push'
    """
    ensure_dispatch_schema()
    col = f"dispatch_{mode}"
    if col not in ("dispatch_manual", "dispatch_pull", "dispatch_push"):
        return False

    row = _execute(
        f"SELECT {col} FROM tool_profiles WHERE tool_id = %s",
        (tool_id,),
        fetchone=True,
    )
    return bool(row and row[col])


def get_perplexity_mode(
    project_name: Optional[str] = None,
) -> str:
    """Effektiver Perplexity-Modus (off | review_only | suggest)."""
    settings = get_effective_settings(project_name=project_name)
    return settings.get("perplexity_mode", "review_only")


def get_dispatch_status_map(
    project_name: str,
) -> Dict[str, Dict[str, Any]]:
    """Baut dispatch_status Map: marker_id -> {assignment_id, executor_tool, approval_state, risk_level}.

    Zeigt pro Marker ob ein aktives (non-terminal) Assignment existiert.
    """
    result: Dict[str, Dict[str, Any]] = {}
    for state in ("proposed", "approved", "claimed"):
        for a in list_assignments(project_name=project_name, status=state):
            mid = str(a.get("marker_id") or "")
            if mid and mid not in result:
                result[mid] = {
                    "assignment_id": a.get("assignment_id"),
                    "executor_tool": a.get("executor_tool", ""),
                    "approval_state": a.get("approval_state", ""),
                    "risk_level": a.get("risk_level", "medium"),
                }
    return result
