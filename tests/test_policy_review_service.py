"""
Tests fuer ADR-002 Stufe 1b: Policy-Reviewer.

Patcht die Policy-Service-Aufrufe direkt im policy_review_service-Modul,
damit der Reviewer isoliert getestet werden kann (keine DB-Fake-
Nachbildung noetig). Perplexity wird ueber injected query_fn gemockt.
"""
import json

import pytest

import services.policy_review_service as prs


@pytest.fixture
def patched_policy_service(monkeypatch):
    """Patcht die Policy-Service-Aufrufe im Review-Modul."""
    state = {"suggestions": [], "next_sid": 100}

    def fake_list_roles(include_inactive=False):
        return [
            {
                "role_id": "programming",
                "name": "Programming / Backend",
                "description": "Backend-Implementierung",
            },
            {
                "role_id": "ux_ui",
                "name": "UX / UI",
                "description": "Frontend-Feinschliff",
            },
        ]

    def fake_list_tool_profiles(include_inactive=False):
        return [
            {
                "tool_id": "claude-code-opus-4-6",
                "cli": "claude-code",
                "model": "claude-opus-4-6",
                "provider": "anthropic",
                "strengths": [],
                "weaknesses": [],
                "notes": "Claude Code CLI mit Opus 4.6 (1M Context).",
            },
            {
                "tool_id": "codex",
                "cli": "codex",
                "model": None,
                "provider": "openai",
                "strengths": [],
                "weaknesses": [],
                "notes": "OpenAI Codex CLI.",
            },
        ]

    def fake_get_active_policies(role_id=None):
        return []

    def fake_record_suggestion(reviewer_tool, suggestion_type, payload,
                                rationale, evidence, context_hash):
        sid = state["next_sid"]
        state["next_sid"] += 1
        state["suggestions"].append({
            "suggestion_id": sid,
            "reviewer_tool": reviewer_tool,
            "suggestion_type": suggestion_type,
            "payload": payload,
            "rationale": rationale,
            "evidence": evidence,
            "context_hash": context_hash,
        })
        return sid

    monkeypatch.setattr(prs, "list_roles", fake_list_roles)
    monkeypatch.setattr(prs, "list_tool_profiles", fake_list_tool_profiles)
    monkeypatch.setattr(prs, "get_active_policies", fake_get_active_policies)
    monkeypatch.setattr(prs, "record_suggestion", fake_record_suggestion)

    return state


def _fake_query(content):
    """Erzeugt eine query_fn, die eine vorgegebene Antwort liefert."""
    def _fn(messages, temperature=0.0, **kwargs):
        return {
            "provider": "perplexity",
            "model": "sonar-test",
            "content": content,
            "usage": {},
            "raw": {},
        }
    return _fn


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

def test_build_context_has_expected_fields(patched_policy_service):
    ctx = prs.build_policy_review_context()
    assert ctx["schema_version"] == 1
    assert len(ctx["roles"]) == 2
    assert len(ctx["tool_profiles"]) == 2
    assert ctx["active_policies"] == []
    assert ctx["roles"][0]["role_id"] == "programming"
    assert ctx["tool_profiles"][0]["tool_id"] == "claude-code-opus-4-6"


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def test_context_hash_deterministic(patched_policy_service):
    ctx1 = prs.build_policy_review_context()
    ctx2 = prs.build_policy_review_context()
    h1 = prs._compute_context_hash(ctx1)
    h2 = prs._compute_context_hash(ctx2)
    assert h1 == h2


def test_context_hash_differs_with_content():
    h1 = prs._compute_context_hash({"a": 1})
    h2 = prs._compute_context_hash({"a": 2})
    assert h1 != h2


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def test_parse_plain_json():
    result = prs._parse_reviewer_response('{"suggestions": []}')
    assert result == {"suggestions": []}


def test_parse_code_fence():
    content = '```json\n{"suggestions": [], "summary": "ok"}\n```'
    result = prs._parse_reviewer_response(content)
    assert result["summary"] == "ok"


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        prs._parse_reviewer_response("")


def test_parse_list_raises():
    with pytest.raises(ValueError):
        prs._parse_reviewer_response("[1,2,3]")


# ---------------------------------------------------------------------------
# Review-Flow
# ---------------------------------------------------------------------------

def test_review_success_persists_suggestions(patched_policy_service):
    fake_content = json.dumps({
        "schema_version": 1,
        "summary": "Zwei Rollen ohne Policy",
        "suggestions": [
            {
                "suggestion_type": "new_policy",
                "payload": {
                    "role_id": "programming",
                    "tool_id": "claude-code-opus-4-6",
                    "rank": 1,
                    "confidence": 70,
                    "reason_short": "1M Context",
                },
                "rationale": "Claude hat langen Context gemaess notes.",
                "evidence": {"from_field": "notes"},
            }
        ],
        "notes": [],
    })

    result = prs.review_policies(query_fn=_fake_query(fake_content))

    assert result["error"] is None
    assert result["summary"] == "Zwei Rollen ohne Policy"
    assert len(result["suggestions"]) == 1
    assert result["suggestions"][0]["suggestion_type"] == "new_policy"
    assert result["suggestions"][0]["suggestion_id"] == 100

    # Persistiert im Fake-State
    assert len(patched_policy_service["suggestions"]) == 1
    stored = patched_policy_service["suggestions"][0]
    assert stored["reviewer_tool"] == "perplexity"
    assert stored["context_hash"] == result["context_hash"]


def test_review_multiple_suggestions_persisted(patched_policy_service):
    fake_content = json.dumps({
        "suggestions": [
            {
                "suggestion_type": "new_policy",
                "payload": {"role_id": "programming", "tool_id": "claude-code-opus-4-6", "rank": 1, "confidence": 70},
                "rationale": "a",
                "evidence": {},
            },
            {
                "suggestion_type": "new_policy",
                "payload": {"role_id": "ux_ui", "tool_id": "codex", "rank": 1, "confidence": 55},
                "rationale": "b",
                "evidence": {},
            },
        ],
    })
    result = prs.review_policies(query_fn=_fake_query(fake_content))
    assert len(result["suggestions"]) == 2
    assert len(patched_policy_service["suggestions"]) == 2


def test_review_empty_suggestions_is_valid(patched_policy_service):
    fake_content = json.dumps({
        "summary": "Input zu duenn, kein Vorschlag",
        "suggestions": [],
    })
    result = prs.review_policies(query_fn=_fake_query(fake_content))
    assert result["error"] is None
    assert result["suggestions"] == []
    assert len(patched_policy_service["suggestions"]) == 0


def test_review_parse_error(patched_policy_service):
    result = prs.review_policies(query_fn=_fake_query("not json at all"))
    assert result["error"] == "parse_failed"
    assert result["suggestions"] == []
    assert "raw_response" in result
    assert len(patched_policy_service["suggestions"]) == 0


def test_review_query_error(patched_policy_service):
    def broken_query(messages, temperature=0.0, **kwargs):
        raise RuntimeError("network down")

    result = prs.review_policies(query_fn=broken_query)
    assert result["error"] == "query_failed"
    assert result["suggestions"] == []
    assert "network down" in result["raw_response"]
    assert len(patched_policy_service["suggestions"]) == 0


def test_review_skips_suggestions_without_type(patched_policy_service):
    fake_content = json.dumps({
        "suggestions": [
            {
                "suggestion_type": "new_policy",
                "payload": {"role_id": "programming", "tool_id": "claude-code-opus-4-6", "rank": 1},
                "rationale": "ok",
            },
            {
                "payload": {"role_id": "ux_ui", "tool_id": "codex", "rank": 1},
                "rationale": "no type",
            },
        ],
    })
    result = prs.review_policies(query_fn=_fake_query(fake_content))
    assert len(result["suggestions"]) == 1  # Das eine ohne suggestion_type wird verworfen
    assert len(patched_policy_service["suggestions"]) == 1
