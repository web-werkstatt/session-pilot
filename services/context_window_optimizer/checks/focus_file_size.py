"""
CWO Sprint Ticket 1.4: Check 3 — Grosse Dateien im Fokusauftrag.

Prueft ob Dateien, die im marker-context.md referenziert werden,
die Zeilenschwellwerte ueberschreiten. Fokusauftrag-Dateien werden
oft komplett gelesen und verbrauchen erhebliches Token-Budget.
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
    ACTION_CREATE_SUMMARY,
    ACTION_UPDATE_FOCUS,
    FOCUS_FILE_ERROR,
    FOCUS_FILE_WARN,
    LOAD_MODE_SUMMARIZED,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    TOKEN_FACTOR_MARKDOWN,
)


@register_check
class FocusFileSizeCheck(BaseCWOCheck):
    """Check 3: Dateigroesse von Fokusauftrag-referenzierten Dateien."""

    check_id = "focus_file_size"
    title = "Grosse Datei im Fokusauftrag"

    def run(self, context: dict) -> List[CWOFinding]:
        focus_files = context.get("focus_files", [])
        if not focus_files:
            return []

        findings = []
        for finfo in focus_files:
            lines = finfo.get("lines", 0)
            if lines < FOCUS_FILE_WARN:
                continue

            severity = SEVERITY_ERROR if lines >= FOCUS_FILE_ERROR else SEVERITY_WARN
            threshold = FOCUS_FILE_ERROR if severity == SEVERITY_ERROR else FOCUS_FILE_WARN
            reference = finfo.get("reference", finfo.get("path", "?"))

            migrations = []
            if lines >= FOCUS_FILE_WARN:
                tokens_saved = int(lines * TOKEN_FACTOR_MARKDOWN * 0.7)
                migrations.append(MigrationEntry(
                    section_title=f"Fokus-Datei: {reference} ({lines} Zeilen)",
                    source=reference,
                    target=f"{reference}.summary.md",
                    load_mode=LOAD_MODE_SUMMARIZED,
                    load_condition="Summary statt Vollversion im Fokusauftrag",
                    tokens_saved=tokens_saved,
                    content_loss="summarized",
                    risk="low",
                ))

            action_id = ACTION_CREATE_SUMMARY
            if severity == SEVERITY_ERROR:
                action_id = ACTION_UPDATE_FOCUS

            findings.append(CWOFinding(
                check_id=self.check_id,
                severity=severity,
                title=self.title,
                detail=(
                    f"Fokusauftrag referenziert '{reference}' "
                    f"mit {lines} Zeilen (Schwelle: {threshold}). "
                    "Wird bei Marker-Aktivierung komplett gelesen."
                ),
                current_value=lines,
                threshold=threshold,
                estimated_tokens=lines * TOKEN_FACTOR_MARKDOWN,
                actionable=True,
                action_id=action_id,
                migration_map=migrations,
                recommendation=(
                    "Summary-Datei erstellen und im Fokusauftrag "
                    "auf die Summary verweisen."
                ),
            ))

        return findings
