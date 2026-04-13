"""
CWO Sprint Ticket 1.5: Check 6 — Fehlende Unterverzeichnis-CLAUDE.md.

Prueft ob Verzeichnisse mit ausreichend Code-Dateien eine eigene
CLAUDE.md haben. Fehlende Unterverzeichnis-CLAUDE.md bedeutet, dass
Detail-Informationen im Root-CLAUDE.md stehen muessen und nicht
automatisch per auto_subdir geladen werden koennen.
"""
from __future__ import annotations

from typing import List

from services.context_window_optimizer.checks import (
    BaseCWOCheck,
    CWOFinding,
    register_check,
)
from services.context_window_optimizer.constants import (
    ACTION_CREATE_SUBDIR,
    LOAD_MODE_AUTO_SUBDIR,
    SEVERITY_INFO,
    SEVERITY_WARN,
    SUBDIR_QUALIFYING_FILES,
)

# Ab dieser Anzahl relevanter Dateien wird aus info ein warn
_WARN_FILE_THRESHOLD = 8


@register_check
class MissingSubdirClaudeCheck(BaseCWOCheck):
    """Check 6: Verzeichnisse ohne CLAUDE.md trotz relevanter Dateien."""

    check_id = "missing_subdir_claude"
    title = "Fehlende Unterverzeichnis-CLAUDE.md"

    def run(self, context: dict) -> List[CWOFinding]:
        subdir_data = context.get("subdir_claude_md", {})
        qualifying = subdir_data.get("qualifying_without", [])

        if not qualifying:
            return []

        findings = []
        for entry in qualifying:
            dir_name = entry["dir_name"]
            file_count = entry["relevant_files"]

            severity = (
                SEVERITY_WARN if file_count >= _WARN_FILE_THRESHOLD
                else SEVERITY_INFO
            )

            findings.append(CWOFinding(
                check_id=self.check_id,
                severity=severity,
                title=self.title,
                detail=(
                    f"Verzeichnis '{dir_name}/' hat {file_count} "
                    f"relevante Dateien (Minimum: {SUBDIR_QUALIFYING_FILES}), "
                    f"aber keine CLAUDE.md. Detail-Kontext muss im "
                    f"Root-CLAUDE.md stehen."
                ),
                current_value=file_count,
                threshold=SUBDIR_QUALIFYING_FILES,
                estimated_tokens=0,
                actionable=True,
                action_id=ACTION_CREATE_SUBDIR,
                recommendation=(
                    f"CLAUDE.md in '{dir_name}/' erstellen — wird "
                    f"automatisch geladen bei Arbeit in diesem Verzeichnis "
                    f"(load_mode: {LOAD_MODE_AUTO_SUBDIR})."
                ),
            ))

        return findings
