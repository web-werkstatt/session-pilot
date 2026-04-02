"""
Zentraler Handoff-Service: Pro Projekt genau eine handoff.md.

Einzige Wahrheit = DB (project_plans, plan_sections).
handoff.md ist abgeleitetes Produkt, liegt immer unter:
  /mnt/projects/<project_id>/handoff.md

Kein anderer Code darf Handoff-Dateien direkt via Pfad schreiben.
Alles muss ueber write_handoff(project_id) laufen.
"""
import os

from config import PROJECTS_DIR
from services.db_service import execute, ensure_plans_schema


def get_handoff_path(project_id):
    """Liefert den absoluten Pfad zur Handoff-Datei fuer ein Projekt.

    Beispiel:
        project_dashboard -> /mnt/projects/project_dashboard/handoff.md
    """
    return os.path.join(PROJECTS_DIR, project_id, "handoff.md")


def build_handoff_markdown(project_id):
    """Erzeugt den aktuellen Handoff-Markdown fuer dieses Projekt
    auf Basis der bestehenden Daten (Plans, Workflow, Signale).

    Returns:
        Markdown-String oder None wenn Projekt nicht in DB.
    """
    ensure_plans_schema()

    plans = execute(
        """SELECT id, title, status, category, plan_type,
                  workflow_stage, current_state, target_state, next_action,
                  latest_executor_status, latest_review_status,
                  latest_quality_score, latest_audit_status, governance_status
           FROM project_plans
           WHERE project_name = %s AND status != 'archived'
           ORDER BY
               CASE WHEN status = 'active' THEN 0 ELSE 1 END,
               updated_at DESC NULLS LAST""",
        (project_id,), fetch=True,
    ) or []

    if not plans:
        return None

    lead = plans[0]
    stage = lead.get("workflow_stage") or "n/a"
    scope = f"{len(plans)} Plan(s) fuer {project_id}"

    plan_refs = []
    for p in plans[:5]:
        plan_refs.append(f"- [{p.get('status', 'draft')}] Plan {p['id']}: {p['title']}")

    ist_lines = []
    for p in plans:
        line = f"- **{p['title']}** (ID {p['id']}, {p['status']})"
        if p.get("current_state"):
            line += f": {p['current_state']}"
        ist_lines.append(line)

    quality = lead.get("latest_quality_score") or "n/a"
    audit = lead.get("latest_audit_status") or "n/a"
    governance = lead.get("governance_status") or "n/a"
    exec_status = lead.get("latest_executor_status") or "n/a"
    review_status = lead.get("latest_review_status") or "n/a"

    next_action = lead.get("next_action") or "n/a"
    target = lead.get("target_state") or "n/a"

    sec_info = ""
    try:
        sec_row = execute(
            """SELECT COUNT(*) as total,
                      COUNT(*) FILTER (WHERE status = 'done') as done,
                      COUNT(*) FILTER (WHERE status = 'in_progress') as wip
               FROM plan_sections
               WHERE plan_id IN (
                   SELECT id FROM project_plans
                   WHERE project_name = %s AND status != 'archived'
               )""",
            (project_id,), fetchone=True,
        )
        if sec_row and sec_row["total"] > 0:
            sec_info = f"\n- Sections: {sec_row['total']} total, {sec_row['done']} done, {sec_row['wip']} in_progress"
    except Exception:
        pass

    md = f"""---
handoff:
  project_id: "{project_id}"
  type: "executor"
  stage: "{stage}"
  scope: "{scope}"
  expected_output: "SPRINT-EXECUTOR-ERGEBNIS"
  priority: "must"
---

# Handoff fuer Projekt {project_id}

## Aktueller Stand (IST)
{chr(10).join(ist_lines)}
- Quality-Score: {quality}
- Audit-Status: {audit}
- Governance: {governance}
- Executor-Status: {exec_status}
- Review-Status: {review_status}{sec_info}

## Offene Plans
{chr(10).join(plan_refs)}

## Naechster konkreter Auftrag
- {next_action}

## Soll-Bild
- {target}

## Nicht-Ziele
- Keine Aenderungen an nicht betroffenen Modulen
- Keine neuen DB-Tabellen ohne Absprache
- Kein UI-Redesign ausserhalb des Plan-Scopes

## Erwartetes Ergebnisformat
- Patch-Diff fuer betroffene Dateien
- Bestehende Tests gruen
- Neue Tests falls Logik-Aenderungen
"""
    return md.strip() + "\n"


def write_handoff(project_id):
    """Baut den Handoff-Markdown, schreibt ihn in die eine handoff.md
    des Projekts und gibt den Pfad zurueck.

    Returns:
        (filepath, markdown) oder (None, None) bei Fehler.
    """
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.isdir(project_dir):
        return None, None

    md = build_handoff_markdown(project_id)
    if md is None:
        return None, None

    filepath = get_handoff_path(project_id)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    return filepath, md
