"""
CWO Sprint Ticket 1.4: Check 1 — CLAUDE.md Uebergroesse.

Prueft ob die Root-CLAUDE.md eines Projekts die Zeilenschwellwerte
ueberschreitet. Bei Ueberschreitung werden auslagerbare Sektionen
als MigrationEntry-Vorschlaege zurueckgegeben.
"""
from __future__ import annotations

from typing import List

from services.context_window_optimizer.checks import (
    BaseCWOCheck,
    CWOFinding,
    MigrationEntry,
    register_check,
)
from services.context_window_optimizer.constants import (
    ACTION_CREATE_SUBDIR,
    CLAUDE_MD_ERROR,
    CLAUDE_MD_WARN,
    LOAD_MODE_AUTO_SUBDIR,
    LOAD_MODE_SKILL,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    TOKEN_FACTOR_MARKDOWN,
)


@register_check
class OversizeClaudeMdCheck(BaseCWOCheck):
    """Check 1: CLAUDE.md Zeilenanzahl."""

    check_id = "oversize_claude_md"
    title = "CLAUDE.md Uebergroesse"

    def run(self, context: dict) -> List[CWOFinding]:
        claude_info = context.get("tool_files", {}).get("claude", {})
        if not claude_info.get("exists"):
            return []

        lines = claude_info.get("lines", 0)
        if lines < CLAUDE_MD_WARN:
            return []

        severity = SEVERITY_ERROR if lines >= CLAUDE_MD_ERROR else SEVERITY_WARN
        threshold = CLAUDE_MD_ERROR if severity == SEVERITY_ERROR else CLAUDE_MD_WARN

        migrations = self._build_migration_map(context)

        saved_tokens = sum(m.tokens_saved for m in migrations)

        return [CWOFinding(
            check_id=self.check_id,
            severity=severity,
            title=self.title,
            detail=(
                f"CLAUDE.md hat {lines} Zeilen "
                f"(Schwelle: {threshold}). "
                f"{len(migrations)} Sektionen koennten ausgelagert werden "
                f"(~{saved_tokens:,} Tokens einsparbar)."
            ),
            current_value=lines,
            threshold=threshold,
            estimated_tokens=lines * TOKEN_FACTOR_MARKDOWN,
            actionable=bool(migrations),
            action_id=ACTION_CREATE_SUBDIR if migrations else None,
            migration_map=migrations,
            recommendation=(
                "Listen-lastige Sektionen in Unterverzeichnis-CLAUDE.md "
                "oder Skills auslagern."
            ),
        )]

    def _build_migration_map(self, context: dict) -> List[MigrationEntry]:
        """Identifiziert auslagerbare Sektionen aus claude_md_sections."""
        sections = context.get("claude_md_sections", [])
        migrations = []

        for sec in sections:
            # Nur listen-lastige Sektionen mit > 10 Zeilen vorschlagen
            if not sec.get("is_list_heavy") or sec.get("lines", 0) < 10:
                continue

            title = sec["title"]
            line_count = sec["lines"]
            tokens = sec["tokens"]

            # Heuristik: wohin koennte die Sektion?
            target, load_mode, condition = _suggest_target(title)

            migrations.append(MigrationEntry(
                section_title=f"{title} ({line_count} Zeilen)",
                source=f"CLAUDE.md Zeile {sec['start_line']}-{sec['end_line']}",
                target=target,
                load_mode=load_mode,
                load_condition=condition,
                tokens_saved=tokens,
            ))

        return migrations


def _suggest_target(section_title: str) -> tuple[str, str, str]:
    """Schlaegt Zielort fuer eine CLAUDE.md-Sektion vor.

    Returns:
        (target_path, load_mode, load_condition)
    """
    lower = section_title.lower()

    # Bekannte Verzeichnis-bezogene Sektionen
    dir_keywords = {
        "route": ("routes/CLAUDE.md", LOAD_MODE_AUTO_SUBDIR,
                  "Automatisch bei Arbeit in routes/"),
        "service": ("services/CLAUDE.md", LOAD_MODE_AUTO_SUBDIR,
                    "Automatisch bei Arbeit in services/"),
        "template": ("templates/CLAUDE.md", LOAD_MODE_AUTO_SUBDIR,
                     "Automatisch bei Arbeit in templates/"),
        "static": ("static/CLAUDE.md", LOAD_MODE_AUTO_SUBDIR,
                   "Automatisch bei Arbeit in static/"),
        "sprint": ("sprints/CLAUDE.md", LOAD_MODE_AUTO_SUBDIR,
                   "Automatisch bei Arbeit in sprints/"),
        "test": ("tests/CLAUDE.md", LOAD_MODE_AUTO_SUBDIR,
                 "Automatisch bei Arbeit in tests/"),
    }

    for keyword, result in dir_keywords.items():
        if keyword in lower:
            return result

    # Betrieb / Ops -> Skill
    if any(kw in lower for kw in ("betrieb", "ops", "deploy", "docker")):
        return ("Skill /project-ops", LOAD_MODE_SKILL,
                "On-demand per /project-ops")

    # Default: manuell lesbares Dokument
    return (f"docs/{section_title.lower().replace(' ', '-')}.md",
            LOAD_MODE_AUTO_SUBDIR,
            "Manuell bei Bedarf lesbar")
