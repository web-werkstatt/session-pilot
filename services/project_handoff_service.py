"""
Zentraler Handoff-Service: Pro Projekt genau eine handoff.md.

Einzige Wahrheit = DB (project_plans, plan_sections).
handoff.md ist abgeleitetes Produkt, liegt immer unter:
  /mnt/projects/<project_id>/handoff.md

Kein anderer Code darf Handoff-Dateien direkt via Pfad schreiben.
Alles muss ueber write_handoff(project_id) laufen.
"""
import os
from datetime import timezone

from config import PROJECTS_DIR
from services.copilot_marker_service import Marker, _serialize_marker
from services.db_service import execute, ensure_plans_schema
from services.path_resolver import resolve_project_path


def get_handoff_path(project_id):
    """Liefert den absoluten Pfad zur Handoff-Datei fuer ein Projekt.

    Beispiel:
        project_dashboard -> /mnt/projects/project_dashboard/handoff.md
    """
    project_id = str(project_id).strip()
    project_root = resolve_project_path(project_id)
    if project_root:
        return os.path.join(project_root, "handoff.md")
    return os.path.join(PROJECTS_DIR, project_id, "handoff.md")


def build_handoff_markdown(project_id):
    """Erzeugt den aktuellen Handoff-Markdown im Marker-Format fuer dieses Projekt.

    Returns:
        Markdown-String oder None wenn Projekt nicht in DB.
    """
    ensure_plans_schema()

    plans = execute(
        """SELECT id, title, status, category, plan_type,
                  workflow_stage, current_state, target_state, next_action,
                  latest_executor_status, latest_review_status,
                  latest_quality_score, latest_audit_status, governance_status,
                  updated_at
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

    header = f"""---
handoff:
  project_id: "{project_id}"
  state_format: "copilot_markers_v1"
  stage: "{stage}"
  scope: "{scope}"
---

# Handoff fuer Projekt {project_id}

## Copilot Markers
"""

    blocks = []
    for plan in plans:
        updated_at = plan.get("updated_at")
        marker = Marker(
            marker_id=str(plan["id"]),
            titel=plan["title"],
            plan_id=str(plan["id"]),
            status=_map_plan_status(plan.get("status")),
            ziel=(plan.get("target_state") or plan.get("current_state") or plan["title"]).strip(),
            naechster_schritt=(plan.get("next_action") or "Noch nicht definiert").strip(),
            prompt="",
            prompt_suggestion=_build_prompt_suggestion(plan),
            risiko=_build_risk_summary(plan),
            checks=_build_default_checks(plan),
            last_session="",
            updated_at=updated_at.astimezone(timezone.utc).isoformat() if updated_at else "",
        )
        blocks.append(_serialize_marker(marker).rstrip())

    return header.strip() + "\n\n" + "\n\n".join(blocks) + "\n"


def _map_plan_status(status):
    mapping = {
        "draft": "todo",
        "active": "in_progress",
        "completed": "done",
        "blocked": "blocked",
    }
    return mapping.get((status or "").strip(), "todo")


def _build_prompt_suggestion(plan):
    title = (plan.get("title") or "").strip()
    target = (plan.get("target_state") or "").strip()
    current = (plan.get("current_state") or "").strip()
    next_action = (plan.get("next_action") or "").strip()

    parts = [f"Arbeite an: {title}."]
    if current:
        parts.append(f"Ist-Zustand: {current}.")
    if target:
        parts.append(f"Soll-Zustand: {target}.")
    if next_action:
        parts.append(f"Naechster Schritt: {next_action}.")
    return " ".join(parts)


def _build_risk_summary(plan):
    risks = []
    if plan.get("latest_audit_status") and str(plan.get("latest_audit_status")).lower() not in ("ok", "pass", "n/a"):
        risks.append(f"Audit: {plan.get('latest_audit_status')}")
    if plan.get("governance_status") and str(plan.get("governance_status")).lower() not in ("green", "ok", "n/a"):
        risks.append(f"Governance: {plan.get('governance_status')}")
    if plan.get("latest_review_status") and str(plan.get("latest_review_status")).lower() not in ("pass", "done", "n/a"):
        risks.append(f"Review: {plan.get('latest_review_status')}")
    if not risks:
        return ""
    return " | ".join(risks)


def _build_default_checks(plan):
    checks = []
    if (plan.get("target_state") or "").strip():
        checks.append("Soll-Zustand ist im Prompt beruecksichtigt")
    if (plan.get("next_action") or "").strip():
        checks.append("Naechster Schritt ist konkret benannt")
    if not checks:
        checks.append("Marker vor Ausfuehrung kurz gegen Plan-Kontext pruefen")
    return checks


def write_handoff(project_id):
    """Baut den Handoff-Markdown, schreibt ihn in die eine handoff.md
    des Projekts und gibt den Pfad zurueck.

    Returns:
        (filepath, markdown) oder (None, None) bei Fehler.
    """
    project_id = str(project_id).strip()
    project_dir = resolve_project_path(project_id) or os.path.join(PROJECTS_DIR, project_id)
    if not os.path.isdir(project_dir):
        return None, None

    md = build_handoff_markdown(project_id)
    if md is None:
        return None, None

    filepath = get_handoff_path(project_id)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    return filepath, md
