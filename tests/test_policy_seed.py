"""
Tests fuer ADR-002 Stufe 1b: Policy-Seed-Defaults.

Nutzt ein minimales In-Memory-DB-Fake, das nur roles + tool_profiles
simuliert (kein Policies/Suggestions-Handling), damit die Test-Datei
kompakt bleibt.
"""
from datetime import datetime, timezone

import pytest

import services.policy_seed as seed
import services.policy_service as ps


@pytest.fixture
def fake_seed_db(monkeypatch):
    """Minimaler In-Memory-Fake fuer roles + tool_profiles."""
    state = {"roles": {}, "tool_profiles": {}}

    def _now():
        return datetime.now(timezone.utc)

    def fake_execute(sql, params=None, fetch=False, fetchone=False):
        q = " ".join(str(sql).lower().split())
        params = params or ()

        if "create" in q:
            return None

        # roles insert
        if "insert into roles" in q:
            rid = params[0]
            state["roles"][rid] = {
                "role_id": rid,
                "name": params[1],
                "description": params[2],
                "active": params[3],
                "created_at": _now(),
                "updated_at": _now(),
            }
            return None

        # roles select single
        if "from roles where role_id = %s" in q:
            return state["roles"].get(params[0])

        # roles list
        if "from roles" in q:
            rows = list(state["roles"].values())
            rows.sort(key=lambda r: r["role_id"])
            return rows if fetch else None

        # tool_profiles insert
        if "insert into tool_profiles" in q:
            tid = params[0]
            state["tool_profiles"][tid] = {
                "tool_id": tid,
                "cli": params[1],
                "model": params[2],
                "provider": params[3],
                "strengths": params[4],
                "weaknesses": params[5],
                "notes": params[6],
                "active": params[7],
                "created_at": _now(),
                "updated_at": _now(),
            }
            return None

        # tool_profiles select single
        if "from tool_profiles where tool_id = %s" in q:
            return state["tool_profiles"].get(params[0])

        # tool_profiles list
        if "from tool_profiles" in q:
            rows = list(state["tool_profiles"].values())
            rows.sort(key=lambda r: r["tool_id"])
            return rows if fetch else None

        return [] if fetch else None

    import services.db_service as db_service
    import services.db_policy_schema as schema_mod
    monkeypatch.setattr(db_service, "execute", fake_execute)
    monkeypatch.setattr(schema_mod, "ensure_policy_schema", lambda: None)
    return state


def test_seed_creates_all_defaults(fake_seed_db):
    """Seed legt alle 6 Rollen + 5 Tool-Profile an."""
    result = seed.seed_defaults()
    assert result["roles_created"] == 6
    assert result["tool_profiles_created"] == 5

    roles = ps.list_roles()
    assert len(roles) == 6
    role_ids = {r["role_id"] for r in roles}
    assert role_ids == {
        "programming", "saas_webdesign", "ux_ui",
        "code_fix", "quality_review", "research_review",
    }

    profiles = ps.list_tool_profiles()
    assert len(profiles) == 5
    tool_ids = {p["tool_id"] for p in profiles}
    assert tool_ids == {
        "claude-code-opus-4-6", "codex", "gemini-cli",
        "hermes", "perplexity",
    }


def test_seed_is_idempotent(fake_seed_db):
    """Zweiter Seed-Aufruf erzeugt keine neuen Eintraege."""
    seed.seed_defaults()
    result = seed.seed_defaults()
    assert result["roles_created"] == 0
    assert result["tool_profiles_created"] == 0

    # Anzahl unveraendert
    assert len(ps.list_roles()) == 6
    assert len(ps.list_tool_profiles()) == 5


def test_seed_preserves_user_edits(fake_seed_db):
    """Wenn Joseph eine Rolle anpasst, bleibt die Anpassung beim Re-Seed erhalten."""
    seed.seed_defaults()

    # Joseph aendert eine Rolle
    ps.upsert_role(
        role_id="programming",
        name="Custom Programming Name",
        description="My edit",
        active=False,
    )

    # Re-Seed
    result = seed.seed_defaults()
    assert result["roles_created"] == 0  # Nichts neu angelegt

    # Josephs Aenderungen bleiben erhalten
    role = ps.get_role("programming")
    assert role["name"] == "Custom Programming Name"
    assert role["description"] == "My edit"
    assert role["active"] is False


def test_seed_adds_new_defaults_without_touching_existing(fake_seed_db):
    """Wenn Joseph eine Rolle deaktiviert hat, aber ein neuer Default ergaenzt
    wird, soll nur der neue Default hinzukommen - der deaktivierte bleibt."""
    seed.seed_defaults()

    ps.upsert_role("programming", "Programming", active=False)

    # Simuliere einen neuen Default durch direkten Insert einer Rolle, die
    # nicht in DEFAULT_ROLES steht (wir koennen das nicht in der Liste aendern,
    # aber wir koennen einen "Partial"-Test machen, indem wir eine Rolle
    # manuell entfernen und sehen, ob Re-Seed sie wieder anlegt)
    fake_seed_db["roles"].pop("quality_review")

    result = seed.seed_defaults()
    assert result["roles_created"] == 1  # Nur quality_review wieder angelegt

    # programming bleibt deaktiviert
    assert ps.get_role("programming")["active"] is False
    # quality_review ist wieder da
    assert ps.get_role("quality_review") is not None


def test_seed_tool_profiles_content(fake_seed_db):
    """Seed-Tool-Profile haben die erwarteten Metadaten."""
    seed.seed_defaults()

    claude = ps.get_tool_profile("claude-code-opus-4-6")
    assert claude["cli"] == "claude-code"
    assert claude["provider"] == "anthropic"
    assert claude["model"] == "claude-opus-4-6"

    perplexity = ps.get_tool_profile("perplexity")
    assert perplexity["provider"] == "perplexity"
    assert perplexity["model"] == "sonar"


def test_default_counts_match_constants(fake_seed_db):
    """Die Konstanten und die Seed-Logik bleiben synchron."""
    assert len(seed.DEFAULT_ROLES) == 6
    assert len(seed.DEFAULT_TOOL_PROFILES) == 5

    result = seed.seed_defaults()
    assert result["roles_created"] == len(seed.DEFAULT_ROLES)
    assert result["tool_profiles_created"] == len(seed.DEFAULT_TOOL_PROFILES)
