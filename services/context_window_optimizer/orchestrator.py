"""
CWO Sprint Ticket 1.6: Orchestrator fuer Context Window Optimizer.

Orchestriert den Analyse-Flow: Context Collector -> Checks -> Findings
aggregieren -> token_budget_rating ableiten -> Storage (DB-Persistierung).

context_hash-Dedup: Wenn sich am Projekt-Kontext nichts geaendert hat,
wird die bestehende Analyse aus der DB zurueckgegeben (force=True
uebergeht das).
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional

from services.context_window_optimizer.checks import CWOFinding, run_all_checks
from services.context_window_optimizer.constants import (
    TOKEN_BUDGET_ERROR,
    TOKEN_BUDGET_INFO,
    TOKEN_BUDGET_WARN,
)
from services.context_window_optimizer.context_collector import build_cwo_context
from services.context_window_optimizer.storage import (
    load_analysis,
    save_analysis,
)

log = logging.getLogger(__name__)


def analyze_project(
    project_name: str,
    *,
    force: bool = False,
    now_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Fuehrt eine CWO-Analyse fuer ein einzelnes Projekt durch.

    Args:
        project_name: Name des Projekts unter /mnt/projects/.
        force: Wenn True, wird auch bei identischem context_hash
               neu analysiert.
        now_fn: Optional fuer Tests. Liefert aktuellen Zeitstempel.

    Returns:
        Analyse-Ergebnis als Dict (wie in der DB gespeichert).
    """
    # 1. Context sammeln
    context = build_cwo_context(project_name)
    if context is None:
        return {
            "project_name": project_name,
            "error": "project_not_found",
            "total_tokens": 0,
            "token_budget_rating": "unknown",
            "findings": [],
            "migration_map": [],
            "file_inventory": [],
        }

    context_hash = context.get("context_hash", "")

    # 2. Dedup-Check: existierende Analyse mit gleichem Hash?
    if not force:
        existing = load_analysis(project_name)
        if existing and existing.get("context_hash") == context_hash:
            existing["dedup_hit"] = True
            return existing

    # 3. Checks ausfuehren
    findings = run_all_checks(context)

    # 4. Aggregation
    total_tokens = context.get("total_tokens", 0)
    rating = _derive_rating(total_tokens)
    findings_dicts = [_finding_to_dict(f) for f in findings]
    migration_map = _aggregate_migration_map(findings)
    file_inventory = _build_file_inventory(context)

    # 5. Ergebnis zusammenbauen
    result = {
        "project_name": project_name,
        "total_tokens": total_tokens,
        "token_budget_rating": rating,
        "findings": findings_dicts,
        "migration_map": migration_map,
        "file_inventory": file_inventory,
        "context_hash": context_hash,
        "error": None,
        "finding_counts": _count_by_severity(findings),
    }

    # 6. Persistieren
    save_analysis(project_name, result, now_fn=now_fn)

    return result


def analyze_all_projects(
    *,
    force: bool = False,
    now_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Analysiert alle Projekte unter /mnt/projects/.

    Returns:
        Dict mit 'projects' (Liste der Einzel-Ergebnisse),
        'total' (Anzahl), 'analyzed' (neu analysiert),
        'dedup' (uebersprungen wg. context_hash).
    """
    from services.project_scanner import scan_projects

    projects = scan_projects()
    results: List[Dict[str, Any]] = []
    analyzed = 0
    dedup = 0
    errors = 0

    for name in projects:
        try:
            result = analyze_project(name, force=force, now_fn=now_fn)
            results.append(result)
            if result.get("dedup_hit"):
                dedup += 1
            elif result.get("error"):
                errors += 1
            else:
                analyzed += 1
        except Exception:
            log.exception("CWO-Analyse fehlgeschlagen: %s", name)
            errors += 1
            results.append({
                "project_name": name,
                "error": "analysis_failed",
                "total_tokens": 0,
                "token_budget_rating": "unknown",
                "findings": [],
            })

    # Nach Token-Verbrauch sortieren (groesster zuerst)
    results.sort(key=lambda r: r.get("total_tokens", 0), reverse=True)

    return {
        "projects": results,
        "total": len(results),
        "analyzed": analyzed,
        "dedup": dedup,
        "errors": errors,
    }


# --- Hilfsfunktionen ---


def _derive_rating(total_tokens: int) -> str:
    """Leitet das Token-Budget-Rating aus der Gesamtzahl ab."""
    if total_tokens >= TOKEN_BUDGET_ERROR:
        return "error"
    if total_tokens >= TOKEN_BUDGET_WARN:
        return "warning"
    if total_tokens >= TOKEN_BUDGET_INFO:
        return "info"
    return "ok"


def _finding_to_dict(finding: CWOFinding) -> Dict[str, Any]:
    """Konvertiert ein CWOFinding in ein JSON-serialisierbares Dict."""
    d = asdict(finding)
    # MigrationEntry-Objekte sind durch asdict() bereits Dicts
    return d


def _aggregate_migration_map(findings: List[CWOFinding]) -> List[Dict[str, Any]]:
    """Sammelt alle MigrationEntry-Objekte aus allen Findings."""
    entries = []
    for f in findings:
        for m in f.migration_map:
            entries.append(asdict(m))
    return entries


def _build_file_inventory(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Erstellt eine kompakte Datei-Uebersicht aus dem Context.

    Zeigt alle Tool-Files, next-session.md und Unterverz.-CLAUDE.md
    mit Zeilen und Tokens.
    """
    inventory = []

    # Tool-Files
    for key, info in context.get("tool_files", {}).items():
        if info.get("exists"):
            inventory.append({
                "file": info.get("path", ""),
                "type": f"tool_file_{key}",
                "lines": info.get("lines", 0),
                "tokens": info.get("tokens", 0),
            })

    # next-session.md
    ns = context.get("next_session", {})
    if ns.get("exists"):
        inventory.append({
            "file": ns.get("path", ""),
            "type": "next_session",
            "lines": ns.get("lines", 0),
            "tokens": ns.get("tokens", 0),
        })

    # Unterverz.-CLAUDE.md
    for info in context.get("subdir_claude_md", {}).get("existing", []):
        inventory.append({
            "file": info.get("path", ""),
            "type": "subdir_claude_md",
            "lines": info.get("lines", 0),
            "tokens": info.get("tokens", 0),
        })

    # Global Rules
    for rule in context.get("global_rules", []):
        inventory.append({
            "file": rule.get("path", ""),
            "type": "global_rule",
            "lines": rule.get("lines", 0),
            "tokens": rule.get("lines", 0) * 18,
        })

    return inventory


def _count_by_severity(findings: List[CWOFinding]) -> Dict[str, int]:
    """Zaehlt Findings pro Severity-Level."""
    counts: Dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts
