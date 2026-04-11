"""
ADR-002 Stufe 1b: Policy-Service.

CRUD + Versionierung + Suggestion-Flow fuer die vier Policy-Tabellen.

Design:
- Versionierung statt Update: neue Policy = neue Zeile, alte bekommt
  valid_until. Audit-Trail bleibt komplett.
- Dedup per context_hash: identischer Reviewer-Input erzeugt keinen
  neuen Eintrag, sondern aktualisiert updated_at.
- Apply-Pfad trennt Suggestion-Annahme von Policy-Insert, mit
  Verknuepfung ueber applied_policy_id.
- Read-Pfad fuer aktive Policies filtert valid_until IS NULL
  AND approved_by IS NOT NULL.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.db_policy_schema import ensure_policy_schema


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

def list_roles(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """Liefert Rollen, standardmaessig nur aktive."""
    ensure_policy_schema()
    from services.db_service import execute
    if include_inactive:
        sql = "SELECT * FROM roles ORDER BY role_id"
    else:
        sql = "SELECT * FROM roles WHERE active = TRUE ORDER BY role_id"
    return execute(sql, fetch=True) or []


def get_role(role_id: str) -> Optional[Dict[str, Any]]:
    ensure_policy_schema()
    from services.db_service import execute
    return execute(
        "SELECT * FROM roles WHERE role_id = %s",
        (role_id,),
        fetchone=True,
    )


def upsert_role(
    role_id: str,
    name: str,
    description: Optional[str] = None,
    active: bool = True,
) -> None:
    """Legt eine Rolle an oder aktualisiert Name/Description/Active."""
    ensure_policy_schema()
    from services.db_service import execute
    execute(
        """
        INSERT INTO roles (role_id, name, description, active, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (role_id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            active = EXCLUDED.active,
            updated_at = NOW()
        """,
        (role_id, name, description, active),
    )


# ---------------------------------------------------------------------------
# Tool Profiles
# ---------------------------------------------------------------------------

def list_tool_profiles(include_inactive: bool = False) -> List[Dict[str, Any]]:
    ensure_policy_schema()
    from services.db_service import execute
    if include_inactive:
        sql = "SELECT * FROM tool_profiles ORDER BY tool_id"
    else:
        sql = "SELECT * FROM tool_profiles WHERE active = TRUE ORDER BY tool_id"
    rows = execute(sql, fetch=True) or []
    return [_decode_tool_profile(r) for r in rows]


def get_tool_profile(tool_id: str) -> Optional[Dict[str, Any]]:
    ensure_policy_schema()
    from services.db_service import execute
    row = execute(
        "SELECT * FROM tool_profiles WHERE tool_id = %s",
        (tool_id,),
        fetchone=True,
    )
    return _decode_tool_profile(row) if row else None


def upsert_tool_profile(
    tool_id: str,
    cli: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    strengths: Optional[List[str]] = None,
    weaknesses: Optional[List[str]] = None,
    notes: Optional[str] = None,
    active: bool = True,
) -> None:
    """Legt ein Tool-Profil an oder aktualisiert es."""
    ensure_policy_schema()
    from services.db_service import execute
    execute(
        """
        INSERT INTO tool_profiles (
            tool_id, cli, model, provider, strengths, weaknesses, notes, active, updated_at
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, NOW())
        ON CONFLICT (tool_id) DO UPDATE SET
            cli = EXCLUDED.cli,
            model = EXCLUDED.model,
            provider = EXCLUDED.provider,
            strengths = EXCLUDED.strengths,
            weaknesses = EXCLUDED.weaknesses,
            notes = EXCLUDED.notes,
            active = EXCLUDED.active,
            updated_at = NOW()
        """,
        (
            tool_id, cli, model, provider,
            json.dumps(strengths or []),
            json.dumps(weaknesses or []),
            notes, active,
        ),
    )


def _decode_tool_profile(row: Any) -> Dict[str, Any]:
    """Dekodiert JSONB-Felder falls sie als String zurueckkommen."""
    if not row:
        return row
    raw = dict(row)
    for k in ("strengths", "weaknesses"):
        v = raw.get(k)
        if isinstance(v, str):
            try:
                raw[k] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return raw


# ---------------------------------------------------------------------------
# Role-Tool Policies (versioniert)
# ---------------------------------------------------------------------------

def get_active_policies(role_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Liest nur genehmigte und aktuell gueltige Policies.

    Filter: valid_until IS NULL AND approved_by IS NOT NULL.
    """
    ensure_policy_schema()
    from services.db_service import execute
    if role_id:
        sql = """
            SELECT * FROM role_tool_policies
            WHERE valid_until IS NULL AND approved_by IS NOT NULL
            AND role_id = %s
            ORDER BY role_id, rank ASC, policy_id DESC
        """
        params: Tuple[Any, ...] = (role_id,)
    else:
        sql = """
            SELECT * FROM role_tool_policies
            WHERE valid_until IS NULL AND approved_by IS NOT NULL
            ORDER BY role_id, rank ASC, policy_id DESC
        """
        params = ()
    return execute(sql, params, fetch=True) or []


def insert_policy(
    role_id: str,
    tool_id: str,
    rank: int,
    confidence: int,
    rationale: Optional[str],
    source: str,
    approved_by: Optional[str],
) -> int:
    """Legt neue Policy-Zeile an, setzt alte aktive Zeile auf valid_until=NOW().

    Returns:
        policy_id der neuen Zeile.
    """
    ensure_policy_schema()
    from services.db_service import execute

    # Alte aktive Zeile stilllegen
    execute(
        """
        UPDATE role_tool_policies
        SET valid_until = NOW()
        WHERE role_id = %s AND tool_id = %s AND valid_until IS NULL
        """,
        (role_id, tool_id),
    )

    approved_at = datetime.now(timezone.utc) if approved_by else None
    row = execute(
        """
        INSERT INTO role_tool_policies
            (role_id, tool_id, rank, confidence, rationale, source,
             approved_by, approved_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING policy_id
        """,
        (role_id, tool_id, rank, confidence, rationale, source,
         approved_by, approved_at),
        fetchone=True,
    )
    return row["policy_id"] if row else -1


# ---------------------------------------------------------------------------
# Suggestions (Perplexity-Vorschlaege, approval-pflichtig)
# ---------------------------------------------------------------------------

def list_pending_suggestions() -> List[Dict[str, Any]]:
    ensure_policy_schema()
    from services.db_service import execute
    rows = execute(
        """
        SELECT * FROM policy_review_suggestions
        WHERE status = 'pending'
        ORDER BY created_at DESC
        """,
        fetch=True,
    ) or []
    return [_decode_suggestion(r) for r in rows]


def record_suggestion(
    reviewer_tool: str,
    suggestion_type: str,
    payload: Dict[str, Any],
    rationale: Optional[str],
    evidence: Optional[Dict[str, Any]],
    context_hash: Optional[str],
) -> int:
    """Legt eine Suggestion an oder aktualisiert updated_at bei identischem Hash.

    Returns:
        suggestion_id der Zeile.
    """
    ensure_policy_schema()
    from services.db_service import execute

    if context_hash:
        existing = execute(
            """
            SELECT suggestion_id FROM policy_review_suggestions
            WHERE context_hash = %s AND status = 'pending'
            """,
            (context_hash,),
            fetchone=True,
        )
        if existing:
            execute(
                "UPDATE policy_review_suggestions SET updated_at = NOW() WHERE suggestion_id = %s",
                (existing["suggestion_id"],),
            )
            return existing["suggestion_id"]

    row = execute(
        """
        INSERT INTO policy_review_suggestions
            (reviewer_tool, suggestion_type, payload, rationale, evidence, context_hash)
        VALUES (%s, %s, %s::jsonb, %s, %s::jsonb, %s)
        RETURNING suggestion_id
        """,
        (
            reviewer_tool,
            suggestion_type,
            json.dumps(payload),
            rationale,
            json.dumps(evidence) if evidence else None,
            context_hash,
        ),
        fetchone=True,
    )
    return row["suggestion_id"] if row else -1


def apply_suggestion(suggestion_id: int, decided_by: str) -> Optional[int]:
    """Markiert Suggestion als applied, erzeugt Policy-Zeile aus payload.

    Nur fuer suggestion_type in ('new_policy', 'update_policy') wird eine
    Policy-Zeile erzeugt. Andere Typen werden nur als applied markiert.

    Returns:
        policy_id der erzeugten Policy, oder None bei anderen Typen / Fehler.
    """
    ensure_policy_schema()
    from services.db_service import execute

    row = execute(
        "SELECT * FROM policy_review_suggestions WHERE suggestion_id = %s",
        (suggestion_id,),
        fetchone=True,
    )
    if not row:
        return None
    if row["status"] != "pending":
        return None

    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    if row["suggestion_type"] not in ("new_policy", "update_policy"):
        _mark_applied(suggestion_id, decided_by, None)
        return None

    if not payload.get("role_id") or not payload.get("tool_id"):
        return None

    policy_id = insert_policy(
        role_id=payload["role_id"],
        tool_id=payload["tool_id"],
        rank=int(payload.get("rank", 1)),
        confidence=int(payload.get("confidence", 50)),
        rationale=row.get("rationale") or payload.get("reason_short"),
        source=f"suggestion_{row['reviewer_tool']}",
        approved_by=decided_by,
    )

    _mark_applied(suggestion_id, decided_by, policy_id)
    return policy_id


def reject_suggestion(
    suggestion_id: int,
    decided_by: str,
    reason: Optional[str] = None,
) -> bool:
    """Markiert eine pending Suggestion als rejected."""
    ensure_policy_schema()
    from services.db_service import execute
    execute(
        """
        UPDATE policy_review_suggestions
        SET status = 'rejected',
            decided_by = %s,
            rationale = COALESCE(%s, rationale),
            decided_at = NOW(),
            updated_at = NOW()
        WHERE suggestion_id = %s AND status = 'pending'
        """,
        (decided_by, reason, suggestion_id),
    )
    return True


def _mark_applied(
    suggestion_id: int,
    decided_by: str,
    applied_policy_id: Optional[int],
) -> None:
    from services.db_service import execute
    execute(
        """
        UPDATE policy_review_suggestions
        SET status = 'applied',
            decided_by = %s,
            applied_policy_id = %s,
            decided_at = NOW(),
            updated_at = NOW()
        WHERE suggestion_id = %s
        """,
        (decided_by, applied_policy_id, suggestion_id),
    )


def _decode_suggestion(row: Any) -> Dict[str, Any]:
    if not row:
        return row
    raw = dict(row)
    for k in ("payload", "evidence"):
        v = raw.get(k)
        if isinstance(v, str):
            try:
                raw[k] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return raw
