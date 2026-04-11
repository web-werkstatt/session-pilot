"""
ADR-002 Stufe 1a: Storage-Schicht fuer Setup-Reviews.

save_review / load_review bedienen die `project_reviews`-Tabelle mit
Upsert. Imports von db_service und db_tool_setup_review_schema sind
bewusst inline innerhalb der Funktionen gehalten, damit Tests per
monkeypatch die Attribute im jeweiligen Modul ersetzen koennen.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from services.tool_setup_review.constants import REVIEW_TYPE, REVIEWER_TOOL_DEFAULT


def save_review(
    project_name: str,
    result: Dict[str, Any],
    *,
    now_fn: Optional[Callable] = None,
) -> None:
    """Persistiert ein Review-Ergebnis in project_reviews (Upsert)."""
    from services.db_service import execute
    from services.db_tool_setup_review_schema import ensure_tool_setup_review_schema

    ensure_tool_setup_review_schema()

    now = (now_fn or _default_now)()

    params = (
        project_name,
        result.get("review_type", REVIEW_TYPE),
        result.get("reviewer_tool", REVIEWER_TOOL_DEFAULT),
        json.dumps(result.get("reviewed_tools") or []),
        result.get("setup_ok"),
        result.get("priority"),
        result.get("summary"),
        json.dumps(result.get("findings") or []),
        json.dumps(result.get("suggested_blocks") or {}),
        json.dumps(result.get("project_json_patch")) if result.get("project_json_patch") is not None else None,
        result.get("implementation_scope"),
        json.dumps(result.get("notes") or []),
        json.dumps(result.get("context_drift")) if result.get("context_drift") is not None else None,
        result.get("context_hash"),
        result.get("reviewer_model"),
        result.get("raw_response"),
        result.get("error"),
        now,
    )

    execute(
        """
        INSERT INTO project_reviews (
            project_name, review_type, reviewer_tool, reviewed_tools,
            setup_ok, priority, summary, findings, suggested_blocks,
            project_json_patch, implementation_scope, notes,
            context_drift, context_hash, reviewer_model, raw_response,
            error, updated_at
        ) VALUES (
            %s, %s, %s, %s::jsonb,
            %s, %s, %s, %s::jsonb, %s::jsonb,
            %s::jsonb, %s, %s::jsonb,
            %s::jsonb, %s, %s, %s,
            %s, %s
        )
        ON CONFLICT (project_name, review_type) DO UPDATE SET
            reviewer_tool = EXCLUDED.reviewer_tool,
            reviewed_tools = EXCLUDED.reviewed_tools,
            setup_ok = EXCLUDED.setup_ok,
            priority = EXCLUDED.priority,
            summary = EXCLUDED.summary,
            findings = EXCLUDED.findings,
            suggested_blocks = EXCLUDED.suggested_blocks,
            project_json_patch = EXCLUDED.project_json_patch,
            implementation_scope = EXCLUDED.implementation_scope,
            notes = EXCLUDED.notes,
            context_drift = EXCLUDED.context_drift,
            context_hash = EXCLUDED.context_hash,
            reviewer_model = EXCLUDED.reviewer_model,
            raw_response = EXCLUDED.raw_response,
            error = EXCLUDED.error,
            updated_at = EXCLUDED.updated_at
        """,
        params,
    )


def load_review(
    project_name: str, review_type: str = REVIEW_TYPE
) -> Optional[Dict[str, Any]]:
    """Laedt das zuletzt gespeicherte Review-Ergebnis aus der DB."""
    from services.db_service import execute
    from services.db_tool_setup_review_schema import ensure_tool_setup_review_schema

    ensure_tool_setup_review_schema()

    row = execute(
        """
        SELECT project_name, review_type, reviewer_tool, reviewed_tools,
               setup_ok, priority, summary, findings, suggested_blocks,
               project_json_patch, implementation_scope, notes,
               context_drift, context_hash, reviewer_model, raw_response,
               error, created_at, updated_at
        FROM project_reviews
        WHERE project_name = %s AND review_type = %s
        """,
        (project_name, review_type),
        fetchone=True,
    )
    if not row:
        return None
    return _row_to_dict(row)


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Normalisiert eine DB-Zeile zu einem serialisierbaren Dict.

    psycopg2 mit RealDictCursor liefert bereits Dicts; JSONB-Felder werden
    als Python-Objekte zurueckgegeben. Diese Funktion akzeptiert sowohl
    echte DB-Zeilen als auch Test-Fake-Rows.
    """
    def _decode(value):
        if isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8")
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    raw = dict(row)
    for key in (
        "reviewed_tools",
        "findings",
        "suggested_blocks",
        "project_json_patch",
        "notes",
        "context_drift",
    ):
        if key in raw and raw[key] is not None:
            raw[key] = _decode(raw[key])
    return raw


def _default_now() -> datetime:
    return datetime.now(timezone.utc)
