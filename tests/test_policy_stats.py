"""
Tests fuer ADR-002 Stufe 1b: Session-Stats Read-Helper.

Patcht db_service.execute mit einem Fake, der simulierte sessions-Zeilen
zurueckgibt. Keine echte PostgreSQL-Abhaengigkeit.
"""
import pytest

import services.policy_stats as stats


@pytest.fixture
def fake_sessions_db(monkeypatch):
    state = {"rows": []}

    def fake_execute(sql, params=None, fetch=False, fetchone=False):
        q = " ".join(str(sql).lower().split())
        if "from sessions" in q and "group by account" in q:
            return list(state["rows"]) if fetch else None
        return [] if fetch else None

    import services.db_service as db_service
    monkeypatch.setattr(db_service, "execute", fake_execute)
    return state


def test_empty_sessions_returns_empty_dict(fake_sessions_db):
    result = stats.get_session_stats_per_tool()
    assert result == {}


def test_single_account(fake_sessions_db):
    fake_sessions_db["rows"] = [
        {
            "account": "claude",
            "session_count": 10,
            "distinct_projects": 3,
            "total_tokens": 50000,
        }
    ]
    result = stats.get_session_stats_per_tool(days=30)
    assert "claude" in result
    assert result["claude"]["session_count"] == 10
    assert result["claude"]["distinct_projects"] == 3
    assert result["claude"]["total_tokens"] == 50000


def test_multiple_accounts(fake_sessions_db):
    fake_sessions_db["rows"] = [
        {"account": "claude", "session_count": 10, "distinct_projects": 3, "total_tokens": 50000},
        {"account": "codex", "session_count": 5, "distinct_projects": 2, "total_tokens": 20000},
        {"account": "gemini", "session_count": 2, "distinct_projects": 1, "total_tokens": 8000},
    ]
    result = stats.get_session_stats_per_tool()
    assert len(result) == 3
    assert result["codex"]["session_count"] == 5
    assert result["gemini"]["total_tokens"] == 8000


def test_none_tokens_coerced_to_zero(fake_sessions_db):
    fake_sessions_db["rows"] = [
        {
            "account": "claude",
            "session_count": 1,
            "distinct_projects": 1,
            "total_tokens": None,
        }
    ]
    result = stats.get_session_stats_per_tool()
    assert result["claude"]["total_tokens"] == 0


def test_db_error_returns_empty(monkeypatch):
    def broken_execute(sql, params=None, fetch=False, fetchone=False):
        raise RuntimeError("db down")

    import services.db_service as db_service
    monkeypatch.setattr(db_service, "execute", broken_execute)

    result = stats.get_session_stats_per_tool()
    assert result == {}


def test_invalid_days_fallback(fake_sessions_db):
    fake_sessions_db["rows"] = [
        {"account": "claude", "session_count": 1, "distinct_projects": 1, "total_tokens": 10}
    ]
    # "abc" sollte zu Default 30 fallback, nicht crash
    result = stats.get_session_stats_per_tool(days="abc")  # type: ignore
    assert "claude" in result


def test_zero_days_coerced_to_min_one(fake_sessions_db):
    fake_sessions_db["rows"] = []
    # Sollte nicht crashen
    result = stats.get_session_stats_per_tool(days=0)
    assert result == {}
