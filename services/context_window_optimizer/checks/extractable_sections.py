"""
CWO Sprint Ticket 1.5: Check 7 — Auslagerbare Listen-Sektionen.

Erkennt CLAUDE.md-Sektionen die ueberwiegend aus Aufzaehlungen
(Listen, Tabellen) bestehen und mehr als EXTRACTABLE_LIST_MIN_ITEMS
Eintraege haben. Solche Sektionen sind gute Kandidaten fuer
Auslagerung in Unterverzeichnis-CLAUDE.md oder eigene Dateien.
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
    EXTRACTABLE_LIST_MIN_ITEMS,
    LOAD_MODE_AUTO_SUBDIR,
    SEVERITY_INFO,
    TOKEN_FACTOR_MARKDOWN,
)


@register_check
class ExtractableSectionsCheck(BaseCWOCheck):
    """Check 7: Auslagerbare Listen-Sektionen in CLAUDE.md."""

    check_id = "extractable_sections"
    title = "Auslagerbare Listen-Sektion"

    def run(self, context: dict) -> List[CWOFinding]:
        sections = context.get("claude_md_sections", [])
        if not sections:
            return []

        findings = []
        for sec in sections:
            list_items = sec.get("list_items", 0)
            is_list_heavy = sec.get("is_list_heavy", False)

            if not is_list_heavy or list_items < EXTRACTABLE_LIST_MIN_ITEMS:
                continue

            sec_lines = sec.get("lines", 0)
            tokens = sec_lines * TOKEN_FACTOR_MARKDOWN
            title = sec["title"]

            target, condition = _suggest_target(title)

            migrations = [MigrationEntry(
                section_title=f"{title} ({sec_lines} Zeilen, {list_items} Eintraege)",
                source=f"CLAUDE.md Zeile {sec['start_line']}-{sec['end_line']}",
                target=target,
                load_mode=LOAD_MODE_AUTO_SUBDIR,
                load_condition=condition,
                tokens_saved=tokens,
            )]

            findings.append(CWOFinding(
                check_id=self.check_id,
                severity=SEVERITY_INFO,
                title=self.title,
                detail=(
                    f"Sektion '{title}' besteht ueberwiegend aus "
                    f"Aufzaehlungen ({list_items} Eintraege in "
                    f"{sec_lines} Zeilen). "
                    f"~{tokens:,} Tokens auslagerbar."
                ),
                current_value=list_items,
                threshold=EXTRACTABLE_LIST_MIN_ITEMS,
                estimated_tokens=tokens,
                actionable=True,
                action_id=ACTION_CREATE_SUBDIR,
                migration_map=migrations,
                recommendation=(
                    "Sektion in Unterverzeichnis-CLAUDE.md oder "
                    "eigene Datei auslagern. Wird dann nur bei "
                    "Bedarf geladen."
                ),
            ))

        return findings


def _suggest_target(section_title: str) -> tuple[str, str]:
    """Schlaegt Zielort fuer eine auslagerbare Sektion vor.

    Returns:
        (target_path, load_condition)
    """
    lower = section_title.lower()

    dir_keywords = {
        "route": ("routes/CLAUDE.md", "Automatisch bei Arbeit in routes/"),
        "service": ("services/CLAUDE.md", "Automatisch bei Arbeit in services/"),
        "template": ("templates/CLAUDE.md", "Automatisch bei Arbeit in templates/"),
        "static": ("static/CLAUDE.md", "Automatisch bei Arbeit in static/"),
        "sprint": ("sprints/CLAUDE.md", "Automatisch bei Arbeit in sprints/"),
        "test": ("tests/CLAUDE.md", "Automatisch bei Arbeit in tests/"),
        "import": ("services/CLAUDE.md", "Automatisch bei Arbeit in services/"),
        "marker": ("services/CLAUDE.md", "Automatisch bei Arbeit in services/"),
        "workflow": ("services/CLAUDE.md", "Automatisch bei Arbeit in services/"),
        "policy": ("services/CLAUDE.md", "Automatisch bei Arbeit in services/"),
    }

    for keyword, result in dir_keywords.items():
        if keyword in lower:
            return result

    return (
        f"docs/{section_title.lower().replace(' ', '-')}.md",
        "Manuell bei Bedarf lesbar",
    )
