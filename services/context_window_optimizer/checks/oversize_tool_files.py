"""
CWO Sprint Ticket 1.4: Check 2 — AGENTS.md / GEMINI.md Uebergroesse.

Prueft ob Tool-Files (AGENTS.md, GEMINI.md) die Zeilenschwellwerte
ueberschreiten. Diese Dateien werden beim Session-Start komplett geladen
und verbrauchen Token-Budget.
"""
from __future__ import annotations

from typing import List

from services.context_window_optimizer.checks import (
    BaseCWOCheck,
    CWOFinding,
    register_check,
)
from services.context_window_optimizer.constants import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    TOKEN_FACTOR_MARKDOWN,
    TOOL_FILE_ERROR,
    TOOL_FILE_WARN,
)


@register_check
class OversizeToolFilesCheck(BaseCWOCheck):
    """Check 2: AGENTS.md / GEMINI.md Zeilenanzahl."""

    check_id = "oversize_tool_files"
    title = "Tool-Files Uebergroesse"

    # Welche Keys aus tool_files pruefen (ohne "claude" — das ist Check 1)
    _KEYS = {
        "codex": "AGENTS.md",
        "gemini": "GEMINI.md",
    }

    def run(self, context: dict) -> List[CWOFinding]:
        tool_files = context.get("tool_files", {})
        findings = []

        for key, display_name in self._KEYS.items():
            info = tool_files.get(key, {})
            if not info.get("exists"):
                continue

            lines = info.get("lines", 0)
            if lines < TOOL_FILE_WARN:
                continue

            severity = SEVERITY_ERROR if lines >= TOOL_FILE_ERROR else SEVERITY_WARN
            threshold = TOOL_FILE_ERROR if severity == SEVERITY_ERROR else TOOL_FILE_WARN

            findings.append(CWOFinding(
                check_id=self.check_id,
                severity=severity,
                title=f"{display_name} Uebergroesse",
                detail=(
                    f"{display_name} hat {lines} Zeilen "
                    f"(Schwelle: {threshold}). "
                    "Wird beim Session-Start komplett geladen."
                ),
                current_value=lines,
                threshold=threshold,
                estimated_tokens=lines * TOKEN_FACTOR_MARKDOWN,
                actionable=False,
                recommendation=(
                    f"{display_name} kuerzen: redundante Sektionen entfernen, "
                    "Detail-Listen in auto_subdir-Dateien auslagern."
                ),
            ))

        return findings
