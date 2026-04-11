"""
ADR-002 Stufe 1b: Read-Only-Helpers fuer Policy-Reviewer-Input.

Stellt aggregierte Session-Daten bereit, die der Policy-Reviewer als
Evidence-Quelle nutzen kann. In Stufe 1b nur ein minimaler Helper - echtes
Join mit tool_profiles und outcome-gewichtete Stats kommen in Stufe 3,
wenn der Arbeits-Reviewer zuerst Session-Ratings generiert.
"""
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


def get_session_stats_per_tool(days: int = 30) -> Dict[str, Dict[str, Any]]:
    """Aggregiert Sessions pro account (Tool-Identitaet) fuer ein Zeitfenster.

    Die sessions-Tabelle nutzt `account` (claude, codex, gemini, ...) als
    Tool-Identifier. Das Mapping account -> tool_id (claude-code-opus-4-6,
    ...) kommt in Stufe 3, wenn mehrere Profile pro account sinnvoll sind.

    Args:
        days: Zeitfenster in Tagen (Default 30).

    Returns:
        Dict {account: {session_count, distinct_projects, total_tokens}}.
        Leeres Dict bei Fehler oder wenn keine Sessions vorhanden sind.
    """
    from services.db_service import execute

    try:
        days_int = max(1, int(days))
    except (TypeError, ValueError):
        days_int = 30

    try:
        rows = execute(
            """
            SELECT
                account,
                COUNT(*) AS session_count,
                COUNT(DISTINCT project_name) AS distinct_projects,
                COALESCE(SUM(total_input_tokens + total_output_tokens), 0) AS total_tokens
            FROM sessions
            WHERE started_at > NOW() - INTERVAL '%s days'
              AND account IS NOT NULL
            GROUP BY account
            ORDER BY session_count DESC
            """ % days_int,
            fetch=True,
        ) or []
    except Exception as exc:
        log.warning("get_session_stats_per_tool fehlgeschlagen: %s", exc)
        return {}

    return {
        row["account"]: {
            "session_count": row["session_count"],
            "distinct_projects": row["distinct_projects"],
            "total_tokens": int(row.get("total_tokens") or 0),
        }
        for row in rows
    }
