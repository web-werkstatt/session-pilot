"""
CWO Sprint Ticket 1.3: Check 8 — Token-Budget Gesamt.

Diagnostischer Check: bewertet den geschaetzten Gesamt-Token-Verbrauch
eines Projekts beim Session-Start gegen die definierten Schwellwerte.

Dieser Check ist rein informativ und schlaegt keine direkten Aktionen vor —
die Einzel-Checks (1-7) identifizieren konkrete Optimierungsmoeglichkeiten.
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
    SEVERITY_INFO,
    SEVERITY_WARN,
    TOKEN_BUDGET_ERROR,
    TOKEN_BUDGET_INFO,
    TOKEN_BUDGET_WARN,
)


@register_check
class TokenBudgetCheck(BaseCWOCheck):
    """Check 8: Gesamt-Token-Budget-Bewertung."""

    check_id = "token_budget"
    title = "Token-Budget Gesamt"

    def run(self, context: dict) -> List[CWOFinding]:
        total_tokens = context.get("total_tokens", 0)

        if total_tokens >= TOKEN_BUDGET_ERROR:
            return [self._finding(
                severity=SEVERITY_ERROR,
                total=total_tokens,
                threshold=TOKEN_BUDGET_ERROR,
                detail=(
                    f"Geschaetzter Startup-Kontext: {total_tokens:,} Tokens "
                    f"(Limit: {TOKEN_BUDGET_ERROR:,}). "
                    "Dringend optimieren — hoher Token-Verbrauch reduziert "
                    "die verfuegbare Arbeits-Kapazitaet erheblich."
                ),
                recommendation=(
                    "Einzelne Checks (1-7) pruefen und vorgeschlagene "
                    "Migrationen umsetzen."
                ),
            )]

        if total_tokens >= TOKEN_BUDGET_WARN:
            return [self._finding(
                severity=SEVERITY_WARN,
                total=total_tokens,
                threshold=TOKEN_BUDGET_WARN,
                detail=(
                    f"Geschaetzter Startup-Kontext: {total_tokens:,} Tokens "
                    f"(Warnschwelle: {TOKEN_BUDGET_WARN:,}). "
                    "Optimierung empfohlen."
                ),
                recommendation=(
                    "Einzelne Checks (1-7) auf Optimierungsvorschlaege pruefen."
                ),
            )]

        if total_tokens >= TOKEN_BUDGET_INFO:
            return [self._finding(
                severity=SEVERITY_INFO,
                total=total_tokens,
                threshold=TOKEN_BUDGET_INFO,
                detail=(
                    f"Geschaetzter Startup-Kontext: {total_tokens:,} Tokens "
                    f"(Info-Schwelle: {TOKEN_BUDGET_INFO:,}). "
                    "Akzeptabel, aber Wachstum beobachten."
                ),
                recommendation="Regelmaessig pruefen.",
            )]

        # Unter allen Schwellwerten — kein Finding
        return []

    def _finding(
        self,
        severity: str,
        total: int,
        threshold: int,
        detail: str,
        recommendation: str,
    ) -> CWOFinding:
        return CWOFinding(
            check_id=self.check_id,
            severity=severity,
            title=self.title,
            detail=detail,
            current_value=total,
            threshold=threshold,
            estimated_tokens=total,
            actionable=False,
            recommendation=recommendation,
        )
