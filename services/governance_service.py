"""
Sprint 12: Governance Service - Policy-Verwaltung pro Projekt.
Liest/schreibt ai_policy in project.json, liefert Governance-Uebersicht.
"""
import os
import json
from datetime import datetime, timezone

from config import PROJECTS_DIR
from services.project_scanner import load_project_json
from services.db_service import execute


POLICY_LEVELS = {
    1: {
        "level_name": "sandbox",
        "restrictions": {
            "allow_write": True,
            "require_review": False,
            "allow_deploy": True,
        },
        "default_workflow": {
            "uses_sprints": False,
            "require_session_review": "none",
            "session_end_mode": "free",
            "governance_mode": "relaxed",
        },
    },
    2: {
        "level_name": "controlled",
        "restrictions": {
            "allow_write": True,
            "require_review": True,
            "allow_deploy": False,
        },
        "default_workflow": {
            "uses_sprints": True,
            "require_session_review": "reminder",
            "session_end_mode": "commit_flow",
            "governance_mode": "balanced",
        },
    },
    3: {
        "level_name": "critical",
        "restrictions": {
            "allow_write": False,
            "require_review": True,
            "allow_deploy": False,
        },
        "default_workflow": {
            "uses_sprints": True,
            "require_session_review": "mandatory",
            "session_end_mode": "commit_flow",
            "governance_mode": "strict",
        },
    },
}


def get_project_policy(project_name):
    """Liefert ai_policy fuer ein Projekt. Fallback auf Sandbox-Default."""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    data = load_project_json(project_path)
    if not data:
        return _default_policy()
    policy = data.get("ai_policy")
    if not policy:
        return _default_policy()
    return policy


def _default_policy():
    """Default-Policy: Sandbox (Level 1)."""
    lvl = POLICY_LEVELS[1]
    return {
        "level": 1,
        "level_name": lvl["level_name"],
        "restrictions": lvl["restrictions"],
        "allowed_models": None,
        "max_ai_write_scope": None,
        "preferred_workflow": lvl["default_workflow"],
        "rules_applied": [],
        "notes": "",
        "updated_at": None,
    }


def update_project_policy(project_name, level, notes=None, allowed_models=None,
                          max_ai_write_scope=None, preferred_workflow=None):
    """Aktualisiert ai_policy in project.json."""
    if level not in POLICY_LEVELS:
        raise ValueError(f"Ungueltiges Policy-Level: {level}. Erlaubt: 1, 2, 3")

    project_path = os.path.join(PROJECTS_DIR, project_name)
    json_path = os.path.join(project_path, "project.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"project.json nicht gefunden: {project_name}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lvl = POLICY_LEVELS[level]
    existing_policy = data.get("ai_policy", {})

    policy = {
        "level": level,
        "level_name": lvl["level_name"],
        "restrictions": lvl["restrictions"],
        "allowed_models": allowed_models,
        "max_ai_write_scope": max_ai_write_scope,
        "preferred_workflow": preferred_workflow or lvl["default_workflow"],
        "rules_applied": existing_policy.get("rules_applied", []),
        "notes": notes or existing_policy.get("notes", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    data["ai_policy"] = policy
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return policy


def get_governance_overview():
    """Uebersicht aller Projekte mit Policy-Level und Rework-Rate."""
    projects = []
    summary = {"sandbox": 0, "controlled": 0, "critical": 0}

    rework_map = _get_rework_rates()

    if not os.path.isdir(PROJECTS_DIR):
        return {"summary": summary, "projects": []}

    for entry in sorted(os.listdir(PROJECTS_DIR)):
        project_path = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(project_path) or entry.startswith("."):
            continue
        json_path = os.path.join(project_path, "project.json")
        if not os.path.exists(json_path):
            continue

        data = load_project_json(project_path)
        if not data:
            continue

        policy = data.get("ai_policy", {})
        level = policy.get("level", 1)
        level_name = policy.get("level_name", "sandbox")
        summary[level_name] = summary.get(level_name, 0) + 1

        rework = rework_map.get(entry, 0.0)
        projects.append({
            "name": entry,
            "level": level,
            "level_name": level_name,
            "rework_rate": rework,
            "notes": policy.get("notes", ""),
            "allowed_models": policy.get("allowed_models"),
            "rules_applied_count": len(policy.get("rules_applied", [])),
            "updated_at": policy.get("updated_at"),
        })

    projects.sort(key=lambda p: (-p["level"], p["name"]))
    return {"summary": summary, "projects": projects}


def _get_rework_rates():
    """Rework-Rate pro Projekt aus Sessions-DB."""
    try:
        rows = execute("""
            SELECT project_name,
                   COUNT(*) FILTER (WHERE outcome IN ('needs_fix', 'reverted')) AS rework,
                   COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS rated
            FROM sessions
            WHERE started_at > NOW() - INTERVAL '90 days'
              AND project_name IS NOT NULL
            GROUP BY project_name
        """, fetch=True)
        result = {}
        for r in rows or []:
            rated = r["rated"] or 0
            if rated > 0:
                result[r["project_name"]] = round(r["rework"] / rated * 100, 1)
        return result
    except Exception:
        return {}


def get_unreviewed_critical_count():
    """Zaehlt Sessions in critical-Projekten ohne Review."""
    critical_projects = []
    if not os.path.isdir(PROJECTS_DIR):
        return 0
    for entry in os.listdir(PROJECTS_DIR):
        project_path = os.path.join(PROJECTS_DIR, entry)
        data = load_project_json(project_path) if os.path.isdir(project_path) else None
        if data and data.get("ai_policy", {}).get("level", 1) == 3:
            critical_projects.append(entry)

    if not critical_projects:
        return 0

    try:
        row = execute("""
            SELECT COUNT(*) AS cnt FROM sessions
            WHERE project_name = ANY(%s)
              AND outcome IS NULL
              AND started_at > NOW() - INTERVAL '30 days'
        """, (critical_projects,), fetchone=True)
        return row["cnt"] if row else 0
    except Exception:
        return 0


def apply_rule_to_project(project_name, reason, rule_text):
    """Speichert eine angewandte Regel in project.json (rules_applied)."""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    json_path = os.path.join(project_path, "project.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"project.json nicht gefunden: {project_name}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    policy = data.setdefault("ai_policy", _default_policy())
    rules = policy.setdefault("rules_applied", [])

    # Duplikat-Check
    if any(r["reason"] == reason for r in rules):
        return policy

    rules.append({
        "reason": reason,
        "rule_text": rule_text,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "source": "auto_generated",
    })

    data["ai_policy"] = policy
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return policy


def get_rule_effectiveness(project_name):
    """Vergleicht Fehlerraten vor/nach Regel-Einfuehrung."""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    data = load_project_json(project_path)
    if not data:
        return []

    rules = data.get("ai_policy", {}).get("rules_applied", [])
    if not rules:
        return []

    results = []
    for rule in rules:
        applied_at = rule.get("applied_at")
        reason = rule.get("reason")
        if not applied_at or not reason:
            continue

        try:
            row_before = execute("""
                SELECT COUNT(*) FILTER (WHERE outcome_reason = %s) AS reason_cnt,
                       COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS total
                FROM sessions
                WHERE project_name = %s
                  AND started_at BETWEEN %s::timestamptz - INTERVAL '30 days' AND %s::timestamptz
            """, (reason, project_name, applied_at, applied_at), fetchone=True)

            row_after = execute("""
                SELECT COUNT(*) FILTER (WHERE outcome_reason = %s) AS reason_cnt,
                       COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS total
                FROM sessions
                WHERE project_name = %s
                  AND started_at > %s::timestamptz
            """, (reason, project_name, applied_at), fetchone=True)

            before_pct = (row_before["reason_cnt"] / row_before["total"] * 100) if row_before and row_before["total"] else 0
            after_pct = (row_after["reason_cnt"] / row_after["total"] * 100) if row_after and row_after["total"] else 0
            diff = round(after_pct - before_pct, 1)

            if diff <= -10:
                verdict = "wirksam"
            elif diff >= 0:
                verdict = "unwirksam"
            else:
                verdict = "unklar"

            results.append({
                "reason": reason,
                "rule_text": rule.get("rule_text", ""),
                "applied_at": applied_at,
                "before_pct": round(before_pct, 1),
                "after_pct": round(after_pct, 1),
                "diff_pp": diff,
                "verdict": verdict,
                "before_total": row_before["total"] if row_before else 0,
                "after_total": row_after["total"] if row_after else 0,
            })
        except Exception:
            continue

    return results


def generate_policy_snippets(project_name):
    """Generiert exportierbare Snippets fuer CLAUDE.md, AGENTS.md, pre-commit."""
    policy = get_project_policy(project_name)
    level_name = policy.get("level_name", "sandbox")
    restrictions = policy.get("restrictions", {})
    allowed_models = policy.get("allowed_models")
    rules = policy.get("rules_applied", [])

    models_str = ", ".join(allowed_models) if allowed_models else "alle"
    rules_lines = "\n".join(f"- {r['rule_text']}" for r in rules) if rules else "- Keine automatischen Regeln aktiv."

    claude_md = f"""## Project Policy: {level_name}
- AI darf Code schreiben: {"Ja" if restrictions.get("allow_write") else "Nein"}
- Review vor Merge: {"Erforderlich" if restrictions.get("require_review") else "Optional"}
- Deploy durch AI: {"Erlaubt" if restrictions.get("allow_deploy") else "Nicht erlaubt"}
- Erlaubte Modelle: {models_str}

### AI-Generated Rules
{rules_lines}"""

    agents_md = f"""## Restrictions ({level_name})
{"- Do not deploy or push to production." if not restrictions.get("allow_deploy") else ""}
{"- All code changes require human review before merge." if restrictions.get("require_review") else ""}
{"- Do not write or modify code files." if not restrictions.get("allow_write") else ""}
- Follow project conventions and existing patterns.""".strip()

    hook_lines = []
    if not restrictions.get("allow_write"):
        hook_lines.append('echo "WARNING: This project has restricted AI write access"')
    if restrictions.get("require_review"):
        hook_lines.append('echo "REMINDER: This commit requires human review before merge"')

    pre_commit = f"""#!/bin/bash
# AI-Policy: {level_name} - Auto-generated checks
{chr(10).join(hook_lines) if hook_lines else "# No restrictions for this policy level"}""" if hook_lines else None

    return {
        "claude_md": claude_md,
        "agents_md": agents_md,
        "pre_commit": pre_commit,
    }
