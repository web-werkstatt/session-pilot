"""
CWO Sprint Ticket 1.4: Check 4 — next-session.md Wachstum.

Prueft ob next-session.md die Zeilenschwellwerte ueberschreitet.
Diese Datei waechst ueber Sessions hinweg und wird beim Start
komplett geladen. Rotation archiviert den alten Inhalt und
startet mit einem frischen Dokument.
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
    ACTION_ROTATE_NEXT_SESSION,
    LOAD_MODE_ARCHIVED,
    NEXT_SESSION_ERROR,
    NEXT_SESSION_WARN,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    TOKEN_FACTOR_MARKDOWN,
)


@register_check
class NextSessionGrowthCheck(BaseCWOCheck):
    """Check 4: next-session.md Zeilenanzahl / Wachstum."""

    check_id = "next_session_growth"
    title = "next-session.md Wachstum"

    def run(self, context: dict) -> List[CWOFinding]:
        ns_info = context.get("next_session", {})
        if not ns_info.get("exists"):
            return []

        lines = ns_info.get("lines", 0)
        if lines < NEXT_SESSION_WARN:
            return []

        severity = SEVERITY_ERROR if lines >= NEXT_SESSION_ERROR else SEVERITY_WARN
        threshold = NEXT_SESSION_ERROR if severity == SEVERITY_ERROR else NEXT_SESSION_WARN

        # Geschaetzte Einsparung: ~80% durch Rotation (Archiv wird nicht geladen)
        tokens_saved = int(lines * TOKEN_FACTOR_MARKDOWN * 0.8)

        migrations = [MigrationEntry(
            section_title=f"next-session.md ({lines} Zeilen)",
            source="next-session.md",
            target="next-session.archive.md",
            load_mode=LOAD_MODE_ARCHIVED,
            load_condition="Archiv wird nicht automatisch geladen",
            tokens_saved=tokens_saved,
            content_loss="archived",
            risk="low",
        )]

        return [CWOFinding(
            check_id=self.check_id,
            severity=severity,
            title=self.title,
            detail=(
                f"next-session.md hat {lines} Zeilen "
                f"(Schwelle: {threshold}). "
                "Wird beim Session-Start komplett geladen. "
                "Aeltere Eintraege sind oft nicht mehr relevant."
            ),
            current_value=lines,
            threshold=threshold,
            estimated_tokens=lines * TOKEN_FACTOR_MARKDOWN,
            actionable=True,
            action_id=ACTION_ROTATE_NEXT_SESSION,
            migration_map=migrations,
            recommendation=(
                "next-session.md rotieren: aktuellen Inhalt archivieren, "
                "frisches Dokument mit letztem Eintrag starten."
            ),
        )]
