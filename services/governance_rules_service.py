"""Governance Rule-Anwendung, Effectiveness und Policy-Snippets."""

import os
import json
from datetime import datetime, timezone

from config import PROJECTS_DIR
from services.project_scanner import load_project_json
from services.db_service import execute


def apply_rule_to_project(project_name, reason, rule_text):
    """Speichert eine angewandte Regel in project.json (rules_applied)."""
    from services.governance_service import _default_policy

    project_path = os.path.join(PROJECTS_DIR, project_name)
    json_path = os.path.join(project_path, "project.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"project.json nicht gefunden: {project_name}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    policy = data.setdefault("ai_policy", _default_policy())
    rules = policy.setdefault("rules_applied", [])

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
    from services.governance_service import get_project_policy

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
