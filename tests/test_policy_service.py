"""
Tests fuer ADR-002 Stufe 1b: Policy-Service.

Nutzt ein monkeypatch-basiertes In-Memory-DB-Fake ohne echte PostgreSQL.
Simuliert die 4 Policy-Tabellen inkl. Versionierung und Suggestion-Flow.
"""
from datetime import datetime, timezone

import pytest

import services.policy_service as ps


# ---------------------------------------------------------------------------
# Fixture: In-Memory-DB
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_policy_db(monkeypatch):
    state = {
        "roles": {},
        "tool_profiles": {},
        "policies": [],
        "suggestions": {},
        "next_policy_id": 1,
        "next_suggestion_id": 1,
    }

    def _now():
        return datetime.now(timezone.utc)

    def fake_execute(sql, params=None, fetch=False, fetchone=False):
        q = " ".join(str(sql).lower().split())
        params = params or ()

        if "create table" in q or "create index" in q:
            return None

        # ROLES
        if "insert into roles" in q:
            rid = params[0]
            existing_created = state["roles"].get(rid, {}).get("created_at")
            state["roles"][rid] = {
                "role_id": rid,
                "name": params[1],
                "description": params[2],
                "active": params[3],
                "created_at": existing_created or _now(),
                "updated_at": _now(),
            }
            return None

        if "from roles where role_id = %s" in q:
            return state["roles"].get(params[0])

        if "from roles" in q:
            only_active = "active = true" in q
            rows = [r for r in state["roles"].values()
                    if not only_active or r["active"]]
            rows.sort(key=lambda r: r["role_id"])
            return rows if fetch else None

        # TOOL PROFILES
        if "insert into tool_profiles" in q:
            tid = params[0]
            existing_created = state["tool_profiles"].get(tid, {}).get("created_at")
            state["tool_profiles"][tid] = {
                "tool_id": tid,
                "cli": params[1],
                "model": params[2],
                "provider": params[3],
                "strengths": params[4],
                "weaknesses": params[5],
                "notes": params[6],
                "active": params[7],
                "created_at": existing_created or _now(),
                "updated_at": _now(),
            }
            return None

        if "from tool_profiles where tool_id = %s" in q:
            return state["tool_profiles"].get(params[0])

        if "from tool_profiles" in q:
            only_active = "active = true" in q
            rows = [r for r in state["tool_profiles"].values()
                    if not only_active or r["active"]]
            rows.sort(key=lambda r: r["tool_id"])
            return rows if fetch else None

        # ROLE_TOOL_POLICIES - supersede
        if "update role_tool_policies" in q and "valid_until = now()" in q:
            role_id, tool_id = params
            for p in state["policies"]:
                if (p["role_id"] == role_id and p["tool_id"] == tool_id
                        and p["valid_until"] is None):
                    p["valid_until"] = _now()
            return None

        # ROLE_TOOL_POLICIES - insert
        if "insert into role_tool_policies" in q:
            pid = state["next_policy_id"]
            state["next_policy_id"] += 1
            policy = {
                "policy_id": pid,
                "role_id": params[0],
                "tool_id": params[1],
                "rank": params[2],
                "confidence": params[3],
                "rationale": params[4],
                "source": params[5],
                "valid_from": _now(),
                "valid_until": None,
                "approved_by": params[6],
                "approved_at": params[7],
                "created_at": _now(),
            }
            state["policies"].append(policy)
            return {"policy_id": pid} if fetchone else None

        # ROLE_TOOL_POLICIES - select active
        if ("from role_tool_policies" in q
                and "valid_until is null" in q
                and "approved_by is not null" in q):
            rows = [p for p in state["policies"]
                    if p["valid_until"] is None and p["approved_by"] is not None]
            if "role_id = %s" in q:
                rows = [p for p in rows if p["role_id"] == params[0]]
            rows.sort(key=lambda p: (p["role_id"], p["rank"], -p["policy_id"]))
            return rows if fetch else None

        # POLICY_REVIEW_SUGGESTIONS - dedup check
        if "from policy_review_suggestions" in q and "context_hash = %s" in q:
            ch = params[0]
            for sid, s in state["suggestions"].items():
                if s["context_hash"] == ch and s["status"] == "pending":
                    return {"suggestion_id": sid}
            return None

        # POLICY_REVIEW_SUGGESTIONS - update updated_at only
        if ("update policy_review_suggestions set updated_at" in q
                and "where suggestion_id = %s" in q
                and "status" not in q):
            sid = params[0]
            if sid in state["suggestions"]:
                state["suggestions"][sid]["updated_at"] = _now()
            return None

        # POLICY_REVIEW_SUGGESTIONS - insert
        if "insert into policy_review_suggestions" in q:
            sid = state["next_suggestion_id"]
            state["next_suggestion_id"] += 1
            state["suggestions"][sid] = {
                "suggestion_id": sid,
                "reviewer_tool": params[0],
                "suggestion_type": params[1],
                "payload": params[2],
                "rationale": params[3],
                "evidence": params[4],
                "context_hash": params[5],
                "status": "pending",
                "decided_by": None,
                "decided_at": None,
                "applied_policy_id": None,
                "created_at": _now(),
                "updated_at": _now(),
            }
            return {"suggestion_id": sid} if fetchone else None

        # POLICY_REVIEW_SUGGESTIONS - select by id
        if "from policy_review_suggestions where suggestion_id = %s" in q:
            return state["suggestions"].get(params[0])

        # POLICY_REVIEW_SUGGESTIONS - list pending
        if "from policy_review_suggestions" in q and "status = 'pending'" in q:
            rows = [s for s in state["suggestions"].values()
                    if s["status"] == "pending"]
            rows.sort(key=lambda s: -s["suggestion_id"])
            return rows if fetch else None

        # POLICY_REVIEW_SUGGESTIONS - mark applied
        if "status = 'applied'" in q and "update policy_review_suggestions" in q:
            decided_by, applied_policy_id, sid = params
            if sid in state["suggestions"]:
                s = state["suggestions"][sid]
                s["status"] = "applied"
                s["decided_by"] = decided_by
                s["decided_at"] = _now()
                s["applied_policy_id"] = applied_policy_id
                s["updated_at"] = _now()
            return None

        # POLICY_REVIEW_SUGGESTIONS - reject
        if "status = 'rejected'" in q and "update policy_review_suggestions" in q:
            decided_by, reason, sid = params
            if sid in state["suggestions"]:
                s = state["suggestions"][sid]
                if s["status"] == "pending":
                    s["status"] = "rejected"
                    s["decided_by"] = decided_by
                    s["decided_at"] = _now()
                    if reason:
                        s["rationale"] = reason
                    s["updated_at"] = _now()
            return None

        return [] if fetch else None

    import services.db_service as db_service
    import services.db_policy_schema as schema_mod
    monkeypatch.setattr(db_service, "execute", fake_execute)
    monkeypatch.setattr(schema_mod, "ensure_policy_schema", lambda: None)
    return state


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

def test_roles_empty_initially(fake_policy_db):
    assert ps.list_roles() == []


def test_upsert_and_get_role(fake_policy_db):
    ps.upsert_role("programming", "Programming / Backend", "Coding")
    role = ps.get_role("programming")
    assert role is not None
    assert role["name"] == "Programming / Backend"
    assert role["active"] is True


def test_upsert_role_updates_existing(fake_policy_db):
    ps.upsert_role("programming", "Old Name", "old")
    ps.upsert_role("programming", "New Name", "new")
    role = ps.get_role("programming")
    assert role["name"] == "New Name"
    assert role["description"] == "new"


def test_list_roles_filters_inactive(fake_policy_db):
    ps.upsert_role("a", "A")
    ps.upsert_role("b", "B", active=False)
    assert len(ps.list_roles()) == 1
    assert len(ps.list_roles(include_inactive=True)) == 2


# ---------------------------------------------------------------------------
# Tool Profiles
# ---------------------------------------------------------------------------

def test_upsert_tool_profile(fake_policy_db):
    ps.upsert_tool_profile(
        "claude-opus", "claude-code",
        model="claude-opus-4-6", provider="anthropic",
        strengths=["refactor", "long-context"],
    )
    profile = ps.get_tool_profile("claude-opus")
    assert profile["cli"] == "claude-code"
    assert profile["provider"] == "anthropic"
    assert "refactor" in profile["strengths"]


def test_list_tool_profiles(fake_policy_db):
    ps.upsert_tool_profile("a", "cli-a")
    ps.upsert_tool_profile("b", "cli-b", active=False)
    assert len(ps.list_tool_profiles()) == 1
    assert len(ps.list_tool_profiles(include_inactive=True)) == 2


# ---------------------------------------------------------------------------
# Policies: Versionierung
# ---------------------------------------------------------------------------

def test_insert_policy_versioning(fake_policy_db):
    ps.upsert_role("programming", "Programming")
    ps.upsert_tool_profile("claude-opus", "claude-code")

    pid1 = ps.insert_policy(
        role_id="programming", tool_id="claude-opus",
        rank=1, confidence=80, rationale="initial",
        source="manual", approved_by="joseph",
    )
    active = ps.get_active_policies()
    assert len(active) == 1
    assert active[0]["policy_id"] == pid1

    pid2 = ps.insert_policy(
        role_id="programming", tool_id="claude-opus",
        rank=1, confidence=90, rationale="updated",
        source="manual", approved_by="joseph",
    )
    active = ps.get_active_policies()
    assert len(active) == 1
    assert active[0]["policy_id"] == pid2
    assert active[0]["confidence"] == 90

    all_policies = fake_policy_db["policies"]
    assert len(all_policies) == 2
    old = [p for p in all_policies if p["policy_id"] == pid1][0]
    assert old["valid_until"] is not None


def test_get_active_policies_filters_unapproved(fake_policy_db):
    ps.upsert_role("programming", "Programming")
    ps.upsert_tool_profile("claude-opus", "claude-code")
    ps.insert_policy(
        role_id="programming", tool_id="claude-opus",
        rank=1, confidence=50, rationale="pending",
        source="perplexity", approved_by=None,
    )
    assert ps.get_active_policies() == []


def test_get_active_policies_filtered_by_role(fake_policy_db):
    ps.upsert_role("programming", "Programming")
    ps.upsert_role("ui", "UI")
    ps.upsert_tool_profile("claude-opus", "claude-code")
    ps.upsert_tool_profile("codex", "codex-cli")

    ps.insert_policy("programming", "claude-opus", 1, 80, "a", "manual", "joseph")
    ps.insert_policy("ui", "codex", 1, 70, "b", "manual", "joseph")

    prog_only = ps.get_active_policies(role_id="programming")
    assert len(prog_only) == 1
    assert prog_only[0]["role_id"] == "programming"


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

def test_record_suggestion_dedup(fake_policy_db):
    sid1 = ps.record_suggestion(
        reviewer_tool="perplexity",
        suggestion_type="new_policy",
        payload={"role_id": "programming", "tool_id": "claude-opus", "rank": 1},
        rationale="first",
        evidence=None,
        context_hash="hash-a",
    )
    sid2 = ps.record_suggestion(
        reviewer_tool="perplexity",
        suggestion_type="new_policy",
        payload={"role_id": "programming", "tool_id": "claude-opus", "rank": 1},
        rationale="different text same hash",
        evidence=None,
        context_hash="hash-a",
    )
    assert sid1 == sid2


def test_apply_suggestion_creates_policy(fake_policy_db):
    ps.upsert_role("programming", "Programming")
    ps.upsert_tool_profile("claude-opus", "claude-code")

    sid = ps.record_suggestion(
        reviewer_tool="perplexity",
        suggestion_type="new_policy",
        payload={
            "role_id": "programming",
            "tool_id": "claude-opus",
            "rank": 1,
            "confidence": 75,
        },
        rationale="Good fit",
        evidence=None,
        context_hash="hash-b",
    )

    policy_id = ps.apply_suggestion(sid, decided_by="joseph")
    assert policy_id is not None

    active = ps.get_active_policies()
    assert len(active) == 1
    assert active[0]["policy_id"] == policy_id
    assert active[0]["approved_by"] == "joseph"
    assert active[0]["source"] == "suggestion_perplexity"

    assert ps.list_pending_suggestions() == []
    suggestion = fake_policy_db["suggestions"][sid]
    assert suggestion["status"] == "applied"
    assert suggestion["applied_policy_id"] == policy_id


def test_apply_suggestion_twice_is_noop(fake_policy_db):
    ps.upsert_role("programming", "Programming")
    ps.upsert_tool_profile("claude-opus", "claude-code")
    sid = ps.record_suggestion(
        reviewer_tool="perplexity",
        suggestion_type="new_policy",
        payload={"role_id": "programming", "tool_id": "claude-opus", "rank": 1},
        rationale="first",
        evidence=None,
        context_hash="h1",
    )
    ps.apply_suggestion(sid, decided_by="joseph")
    # Zweite Anwendung
    result = ps.apply_suggestion(sid, decided_by="joseph")
    assert result is None


def test_reject_suggestion(fake_policy_db):
    sid = ps.record_suggestion(
        reviewer_tool="perplexity",
        suggestion_type="new_policy",
        payload={"role_id": "programming", "tool_id": "claude-opus", "rank": 1},
        rationale="bad fit",
        evidence=None,
        context_hash="h-rej",
    )
    ps.reject_suggestion(sid, decided_by="joseph", reason="not needed")

    assert ps.list_pending_suggestions() == []
    suggestion = fake_policy_db["suggestions"][sid]
    assert suggestion["status"] == "rejected"
    assert suggestion["decided_by"] == "joseph"


def test_list_pending_filters_applied_and_rejected(fake_policy_db):
    ps.upsert_role("programming", "Programming")
    ps.upsert_tool_profile("claude-opus", "claude-code")

    sid1 = ps.record_suggestion(
        "perplexity", "new_policy",
        {"role_id": "programming", "tool_id": "claude-opus", "rank": 1},
        "one", None, "h1",
    )
    sid2 = ps.record_suggestion(
        "perplexity", "new_policy",
        {"role_id": "programming", "tool_id": "claude-opus", "rank": 2},
        "two", None, "h2",
    )
    sid3 = ps.record_suggestion(
        "perplexity", "new_policy",
        {"role_id": "programming", "tool_id": "claude-opus", "rank": 3},
        "three", None, "h3",
    )

    ps.apply_suggestion(sid1, decided_by="joseph")
    ps.reject_suggestion(sid2, decided_by="joseph")

    pending = ps.list_pending_suggestions()
    assert len(pending) == 1
    assert pending[0]["suggestion_id"] == sid3
