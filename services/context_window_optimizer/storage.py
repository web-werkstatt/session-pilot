"""
CWO Sprint Ticket 1.6: Storage-Schicht fuer CWO-Analysen.

save_analysis / load_analysis / load_all_analyses bedienen die
`cwo_analyses`-Tabelle mit Upsert. Inline-Imports fuer db_service
und Schema, damit Tests per monkeypatch ersetzen koennen.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


def save_analysis(
    project_name: str,
    result: Dict[str, Any],
    *,
    now_fn: Optional[Callable] = None,
) -> None:
    """Persistiert ein Analyse-Ergebnis in cwo_analyses (Upsert)."""
    from services.db_service import execute, ensure_cwo_schema

    ensure_cwo_schema()

    now = (now_fn or _default_now)()

    params = (
        project_name,
        result.get("total_tokens", 0),
        result.get("token_budget_rating", "ok"),
        json.dumps(result.get("findings") or [], ensure_ascii=True),
        json.dumps(result.get("migration_map") or [], ensure_ascii=True),
        json.dumps(result.get("file_inventory") or [], ensure_ascii=True),
        result.get("context_hash"),
        result.get("error"),
        now,
        now,
    )

    execute(
        """
        INSERT INTO cwo_analyses (
            project_name, total_tokens, token_budget_rating,
            findings, migration_map, file_inventory,
            context_hash, error, created_at, updated_at
        ) VALUES (
            %s, %s, %s,
            %s::jsonb, %s::jsonb, %s::jsonb,
            %s, %s, %s, %s
        )
        ON CONFLICT (project_name) DO UPDATE SET
            total_tokens = EXCLUDED.total_tokens,
            token_budget_rating = EXCLUDED.token_budget_rating,
            findings = EXCLUDED.findings,
            migration_map = EXCLUDED.migration_map,
            file_inventory = EXCLUDED.file_inventory,
            context_hash = EXCLUDED.context_hash,
            error = EXCLUDED.error,
            updated_at = EXCLUDED.updated_at
        """,
        params,
    )


def load_analysis(project_name: str) -> Optional[Dict[str, Any]]:
    """Laedt die letzte Analyse fuer ein Projekt aus der DB."""
    from services.db_service import execute, ensure_cwo_schema

    ensure_cwo_schema()

    row = execute(
        """
        SELECT project_name, total_tokens, token_budget_rating,
               findings, migration_map, file_inventory,
               context_hash, perplexity_review, perplexity_confidence,
               review_context_hash, error,
               created_at, updated_at
        FROM cwo_analyses
        WHERE project_name = %s
        """,
        (project_name,),
        fetchone=True,
    )
    if not row:
        return None
    return _row_to_dict(row)


def load_all_analyses() -> List[Dict[str, Any]]:
    """Laedt alle Analysen fuer die Uebersichtsseite.

    Sortiert nach total_tokens absteigend (groesster Verbraucher zuerst).
    """
    from services.db_service import execute, ensure_cwo_schema

    ensure_cwo_schema()

    rows = execute(
        """
        SELECT project_name, total_tokens, token_budget_rating,
               findings, migration_map, file_inventory,
               context_hash, perplexity_review, perplexity_confidence,
               review_context_hash, error,
               created_at, updated_at
        FROM cwo_analyses
        ORDER BY total_tokens DESC
        """,
        fetch=True,
    )
    return [_row_to_dict(r) for r in (rows or [])]


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Normalisiert eine DB-Zeile zu einem serialisierbaren Dict.

    psycopg2 RealDictCursor liefert Dicts; JSONB-Felder kommen als
    Python-Objekte. Timestamps werden zu ISO-Strings.
    """
    raw = dict(row)
    # JSONB-Felder normalisieren (falls als String zurueck)
    for key in ("findings", "migration_map", "file_inventory",
                "perplexity_review"):
        val = raw.get(key)
        if isinstance(val, (bytes, bytearray)):
            val = val.decode("utf-8")
        if isinstance(val, str):
            try:
                raw[key] = json.loads(val)
            except json.JSONDecodeError:
                pass
    # Timestamps zu ISO-Strings
    for key in ("created_at", "updated_at"):
        val = raw.get(key)
        if isinstance(val, datetime):
            raw[key] = val.isoformat()
    return raw


def _default_now() -> datetime:
    return datetime.now(timezone.utc)
