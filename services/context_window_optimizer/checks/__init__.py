"""
CWO Sprint Ticket 1.3: Check-Framework fuer Context Window Optimizer.

Definiert das BaseCWOCheck-Interface, die Check-Registry und run_all_checks().
Check-Module in diesem Package registrieren sich via @register_check Decorator.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, List, Optional

from services.context_window_optimizer.constants import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARN,
)

log = logging.getLogger(__name__)

# Severity-Ranking fuer Sortierung (hoeher = dringender)
_SEVERITY_RANK = {
    SEVERITY_ERROR: 3,
    SEVERITY_WARN: 2,
    SEVERITY_INFO: 1,
}


@dataclass
class MigrationEntry:
    """Eine Zeile der Migrations-Map: beschreibt wohin ein Inhalt verschoben wird."""
    section_title: str
    source: str
    target: str
    load_mode: str
    load_condition: str
    tokens_saved: int
    content_loss: str = "none"
    risk: str = "none"


@dataclass
class CWOFinding:
    """Ergebnis eines einzelnen Checks."""
    check_id: str
    severity: str
    title: str
    detail: str
    current_value: Any
    threshold: Any
    estimated_tokens: int
    actionable: bool
    action_id: Optional[str] = None
    migration_map: List[MigrationEntry] = field(default_factory=list)
    recommendation: str = ""


class BaseCWOCheck:
    """Basis-Interface fuer alle CWO-Checks.

    Jeder Check implementiert `run()` und gibt eine Liste von
    CWOFinding-Objekten zurueck. Leere Liste = kein Problem gefunden.
    """
    check_id: str = ""
    title: str = ""

    def run(self, context: dict) -> List[CWOFinding]:
        raise NotImplementedError


# Registry: wird von jedem Check-Modul befuellt
_check_registry: List[BaseCWOCheck] = []


def register_check(check_class: type) -> type:
    """Decorator: registriert einen Check in der globalen Registry."""
    _check_registry.append(check_class())
    return check_class


def get_all_checks() -> List[BaseCWOCheck]:
    """Gibt alle registrierten Checks zurueck."""
    _auto_discover_checks()
    return list(_check_registry)


def run_all_checks(context: dict) -> List[CWOFinding]:
    """Fuehrt alle registrierten Checks gegen den Context aus.

    Returns:
        Findings sortiert nach Severity (error > warning > info).
    """
    _auto_discover_checks()

    findings: List[CWOFinding] = []
    for check in _check_registry:
        try:
            results = check.run(context)
            findings.extend(results)
        except Exception:
            log.exception("Check %s fehlgeschlagen", check.check_id)
            findings.append(CWOFinding(
                check_id=check.check_id,
                severity=SEVERITY_ERROR,
                title=f"Check-Fehler: {check.title}",
                detail=f"Check {check.check_id} hat einen unerwarteten Fehler geworfen.",
                current_value=None,
                threshold=None,
                estimated_tokens=0,
                actionable=False,
            ))

    findings.sort(
        key=lambda f: _SEVERITY_RANK.get(f.severity, 0),
        reverse=True,
    )
    return findings


# --- Auto-Discovery ---

_checks_discovered = False


def _auto_discover_checks():
    """Importiert alle Module in diesem Package, damit @register_check greift."""
    global _checks_discovered
    if _checks_discovered:
        return
    _checks_discovered = True

    package = importlib.import_module(__package__ or __name__)
    for _, modname, _ in pkgutil.iter_modules(package.__path__):
        if modname.startswith("_"):
            continue
        try:
            importlib.import_module(f"{__package__}.{modname}")
        except Exception:
            log.exception("Check-Modul %s konnte nicht geladen werden", modname)
