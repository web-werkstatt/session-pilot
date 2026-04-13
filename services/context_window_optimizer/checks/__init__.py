"""
CWO Sprint: Check-Framework fuer Context Window Optimizer.

Definiert das BaseCWOCheck-Interface und die Check-Registry.
Wird in Ticket 1.3 vollstaendig implementiert.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


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
    return list(_check_registry)
