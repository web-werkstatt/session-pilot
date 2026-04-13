"""
CWO Sprint: Action-Framework fuer Context Window Optimizer.

Definiert das BaseAction-Interface. Wird in Phase 2 (Ticket 2.1)
vollstaendig implementiert.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class BaseAction:
    """Basis-Interface fuer alle CWO-Aktionen.

    Jede Aktion implementiert `preview()` (Diff-Vorschau) und
    `execute()` (tatsaechliche Durchfuehrung nach Approval).
    """
    action_id: str = ""
    title: str = ""
    requires_approval: bool = True

    def preview(self, project_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Erstellt eine Vorschau der geplanten Aenderungen."""
        raise NotImplementedError

    def execute(self, project_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Fuehrt die Aktion aus. Nur nach Approval aufrufen."""
        raise NotImplementedError
