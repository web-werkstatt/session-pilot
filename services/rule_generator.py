"""
Sprint 12: Rule Generator - Automatische Regel-Vorschlaege aus Outcome-Reasons.
Analysiert die haeufigsten Fehlergruende und generiert CLAUDE.md-Regeln.
"""
from services.db_service import execute


RULE_TEMPLATES = {
    "missing_tests": {
        "rule": "Bei jeder Code-Aenderung muessen Tests geschrieben/aktualisiert werden.",
        "enforcement": "Hook: pre-commit Test-Coverage pruefen",
        "claude_md": "IMMER Tests schreiben fuer neue Funktionen und Bugfixes.",
        "category": "quality",
    },
    "wrong_approach": {
        "rule": "Bestehende Patterns studieren bevor neuer Code geschrieben wird.",
        "enforcement": "Review-Checklist: Bestehende Patterns pruefen",
        "claude_md": "VOR Implementierung: bestehende Patterns und Architektur studieren.",
        "category": "architecture",
    },
    "type_error": {
        "rule": "TypeScript strict mode, keine any-Types ausser dokumentierte Ausnahmen.",
        "enforcement": "Hook: tsc --noEmit vor Commit",
        "claude_md": "Keine `any` Types. Bestehende Interfaces/Types wiederverwenden.",
        "category": "types",
    },
    "logic_error": {
        "rule": "Edge Cases explizit behandeln, Guard Clauses verwenden.",
        "enforcement": "Review-Fokus auf Boundary-Conditions",
        "claude_md": "Edge Cases (null, empty, boundary) explizit pruefen.",
        "category": "logic",
    },
    "syntax_error": {
        "rule": "Code vor Commit syntaktisch pruefen (Linter/Compiler).",
        "enforcement": "Hook: Linter vor Commit ausfuehren",
        "claude_md": "Code muss syntaktisch korrekt sein. Linter-Fehler vor Commit beheben.",
        "category": "quality",
    },
    "wrong_file": {
        "rule": "Aenderungen nur in den richtigen Dateien vornehmen, Pfade verifizieren.",
        "enforcement": "Review: Datei-Pfade im Diff pruefen",
        "claude_md": "VOR Aenderung: Datei-Pfad und Kontext verifizieren.",
        "category": "navigation",
    },
    "incomplete": {
        "rule": "Tasks vollstaendig abschliessen, keine TODO-Kommentare hinterlassen.",
        "enforcement": "Review: keine offenen TODOs im Diff",
        "claude_md": "Keine TODO/FIXME hinterlassen. Aufgabe vollstaendig erledigen.",
        "category": "completeness",
    },
    "broke_existing": {
        "rule": "Bestehende Funktionalitaet nicht brechen, Regressionstests durchfuehren.",
        "enforcement": "Hook: Test-Suite vor Commit ausfuehren",
        "claude_md": "VOR Aenderung: bestehende Funktionalitaet verifizieren. Keine Regressionen.",
        "category": "stability",
    },
    "wrong_scope": {
        "rule": "Nur angefragte Aenderungen vornehmen, kein Scope Creep.",
        "enforcement": "Review: Diff auf nicht-angefragte Aenderungen pruefen",
        "claude_md": "NUR die angeforderten Aenderungen umsetzen. Kein Scope Creep.",
        "category": "scope",
    },
    "regression": {
        "rule": "Regressionstests fuer geaenderte Bereiche sicherstellen.",
        "enforcement": "Hook: Betroffene Tests vor Commit ausfuehren",
        "claude_md": "Bei Aenderungen: betroffene Tests ausfuehren und Ergebnis pruefen.",
        "category": "stability",
    },
    "performance_issue": {
        "rule": "N+1 Queries vermeiden, Batch-Operationen bevorzugen.",
        "enforcement": "Review: SQL-Queries auf N+1 pruefen",
        "claude_md": "Keine Queries in Schleifen. JOINs und Batch-Ops verwenden.",
        "category": "performance",
    },
    "test_failure": {
        "rule": "Alle Tests muessen vor Commit bestehen.",
        "enforcement": "Hook: Test-Suite als pre-commit Gate",
        "claude_md": "Tests muessen IMMER bestehen bevor Code committed wird.",
        "category": "quality",
    },
    "missing_import": {
        "rule": "Imports verifizieren, fehlende Abhaengigkeiten sofort beheben.",
        "enforcement": "Linter: unused/missing imports pruefen",
        "claude_md": "Alle Imports verifizieren. Fehlende Imports sofort hinzufuegen.",
        "category": "imports",
    },
    "not_requested": {
        "rule": "Nur explizit angefragte Features implementieren.",
        "enforcement": "Review: Feature gegen Anforderung pruefen",
        "claude_md": "NUR implementieren was explizit angefragt wurde.",
        "category": "scope",
    },
    "needs_followup": {
        "rule": "Alle offenen Punkte in der Session abschliessen.",
        "enforcement": "Session-Review: offene Punkte pruefen",
        "claude_md": "Offene Punkte vor Session-Ende abschliessen oder dokumentieren.",
        "category": "completeness",
    },
    "incomplete_refactor": {
        "rule": "Refactoring vollstaendig durchfuehren, keine Halbloesungen.",
        "enforcement": "Review: Refactoring-Vollstaendigkeit pruefen",
        "claude_md": "Refactoring vollstaendig durchfuehren. Keine toten Code-Pfade hinterlassen.",
        "category": "completeness",
    },
    "manual_fix_needed": {
        "rule": "Aenderungen so implementieren, dass kein manueller Nacharbeit noetig ist.",
        "enforcement": "Review: Vollstaendigkeit der Implementierung",
        "claude_md": "Implementierung muss vollstaendig sein. Kein manueller Fix noetig.",
        "category": "completeness",
    },
}


def get_top_reasons(project=None, period="90d", limit=3):
    """Holt die haeufigsten Outcome-Reasons aus der DB."""
    days = int(period.rstrip("d")) if period.endswith("d") else 90

    where = "WHERE outcome_reason IS NOT NULL AND started_at > NOW() - INTERVAL '%s days'"
    params = [days]

    if project:
        where += " AND project_name = %s"
        params.append(project)

    # psycopg2 kann kein %s fuer INTERVAL, daher string formatting fuer days
    sql = f"""
        SELECT outcome_reason AS reason, COUNT(*) AS count
        FROM sessions
        WHERE outcome_reason IS NOT NULL
          AND started_at > NOW() - INTERVAL '{days} days'
          {"AND project_name = %s" if project else ""}
        GROUP BY outcome_reason
        ORDER BY count DESC
        LIMIT %s
    """
    query_params = []
    if project:
        query_params.append(project)
    query_params.append(limit)

    try:
        rows = execute(sql, query_params, fetch=True)
        return [{"reason": r["reason"], "count": r["count"]} for r in rows] if rows else []
    except Exception:
        return []


def generate_rules(project=None, period="90d", limit=5):
    """Generiert Regel-Vorschlaege aus Top-Fehlergruenden."""
    reasons = get_top_reasons(project=project, period=period, limit=limit)
    if not reasons:
        return []

    rules = []
    for r in reasons:
        reason = r["reason"]
        if reason not in RULE_TEMPLATES:
            continue
        template = RULE_TEMPLATES[reason]
        rules.append({
            "reason": reason,
            "count": r["count"],
            "rule": template["rule"],
            "enforcement": template["enforcement"],
            "claude_md": template["claude_md"],
            "category": template["category"],
            "confidence": "high" if r["count"] >= 5 else "medium" if r["count"] >= 2 else "low",
        })

    return rules


def get_feedback_loop_analysis(period="90d"):
    """Fehler-Kategorien gruppiert nach Policy-Level aller Projekte."""
    import os
    from config import PROJECTS_DIR
    from services.project_scanner import load_project_json

    # Projekte nach Policy-Level gruppieren
    level_projects = {"sandbox": [], "controlled": [], "critical": []}
    if os.path.isdir(PROJECTS_DIR):
        for entry in os.listdir(PROJECTS_DIR):
            ppath = os.path.join(PROJECTS_DIR, entry)
            if not os.path.isdir(ppath) or entry.startswith("."):
                continue
            data = load_project_json(ppath)
            if not data:
                continue
            level_name = data.get("ai_policy", {}).get("level_name", "sandbox")
            if level_name in level_projects:
                level_projects[level_name].append(entry)

    days = int(period.rstrip("d")) if period.endswith("d") else 90
    result = {}

    for level_name, projects in level_projects.items():
        if not projects:
            result[level_name] = {"project_count": 0, "top_reasons": []}
            continue

        try:
            rows = execute(f"""
                SELECT outcome_reason AS reason, COUNT(*) AS count
                FROM sessions
                WHERE outcome_reason IS NOT NULL
                  AND project_name = ANY(%s)
                  AND started_at > NOW() - INTERVAL '{days} days'
                GROUP BY outcome_reason
                ORDER BY count DESC
                LIMIT 3
            """, (projects,), fetch=True)

            total = sum(r["count"] for r in rows) if rows else 0
            top = []
            for r in (rows or []):
                pct = round(r["count"] / total * 100, 1) if total else 0
                template = RULE_TEMPLATES.get(r["reason"], {})
                top.append({
                    "reason": r["reason"],
                    "count": r["count"],
                    "percentage": pct,
                    "suggestion": template.get("claude_md", ""),
                })

            result[level_name] = {
                "project_count": len(projects),
                "top_reasons": top,
            }
        except Exception:
            result[level_name] = {"project_count": len(projects), "top_reasons": []}

    return result
