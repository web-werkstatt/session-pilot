"""
Sprint E: Plan-Workflow Micro-Ebene.
Liest/schreibt Workflow-Daten pro Plan, integriert vorhandene Signale.
"""
import json
import os
from datetime import datetime, timezone

from config import PROJECTS_DIR
from services.db_service import execute, ensure_plan_workflow_schema

# Gueltige Workflow-Stages (M3)
WORKFLOW_STAGES = (
    "idea", "spec_ready", "prompt_ready", "executing",
    "review_pending", "fixed", "done", "blocked",
)

# Gueltige Executor/Review-Status
EXECUTOR_STATUSES = ("pending", "running", "done", "failed")
REVIEW_STATUSES = ("pending", "pass", "fail", "partial")


def get_plan_workflow(plan_id):
    """Laedt Workflow-Daten fuer einen Plan inkl. integrierter Signale (M2, M6, M7)."""
    ensure_plan_workflow_schema()

    row = execute(
        """SELECT id, project_name, title, plan_type, status,
                  workflow_stage, current_state, target_state, next_action,
                  latest_executor_status, latest_review_status,
                  open_items_count, latest_audit_status, latest_quality_score,
                  governance_status, spec_ref, prompt_ref, last_run_at, updated_at
           FROM project_plans WHERE id = %s""",
        (plan_id,),
        fetchone=True,
    )
    if not row:
        return None

    result = {
        "plan_id": row["id"],
        "project_name": row.get("project_name"),
        "title": row.get("title"),
        "plan_type": row.get("plan_type") or "plan",
        "status": row.get("status"),
        "workflow_stage": row.get("workflow_stage") or "idea",
        "current_state": row.get("current_state"),
        "target_state": row.get("target_state"),
        "next_action": row.get("next_action"),
        "latest_executor_status": row.get("latest_executor_status"),
        "latest_review_status": row.get("latest_review_status"),
        "open_items_count": row.get("open_items_count") or 0,
        "latest_audit_status": row.get("latest_audit_status"),
        "latest_quality_score": row.get("latest_quality_score"),
        "governance_status": row.get("governance_status"),
        "spec_ref": row.get("spec_ref"),
        "prompt_ref": row.get("prompt_ref"),
        "last_run_at": row["last_run_at"].isoformat() if row.get("last_run_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }

    # M7: Live-Signale integrieren wenn Projekt bekannt
    project = row.get("project_name")
    if project:
        result.update(_fetch_live_signals(project))

    return result


def update_plan_workflow(plan_id, data):
    """Aktualisiert Workflow-Felder fuer einen Plan (M2)."""
    ensure_plan_workflow_schema()

    # Pruefen ob Plan existiert
    existing = execute("SELECT id FROM project_plans WHERE id = %s", (plan_id,), fetchone=True)
    if not existing:
        return None

    allowed_fields = {
        "current_state": str,
        "target_state": str,
        "workflow_stage": str,
        "next_action": str,
        "latest_executor_status": str,
        "latest_review_status": str,
        "open_items_count": int,
        "spec_ref": str,
        "prompt_ref": str,
        "plan_type": str,
    }

    updates = []
    params = []

    for field, expected_type in allowed_fields.items():
        if field in data:
            value = data[field]
            # Validierung
            if field == "workflow_stage" and value not in WORKFLOW_STAGES:
                raise ValueError(f"Ungueltiger workflow_stage: {value}. Erlaubt: {', '.join(WORKFLOW_STAGES)}")
            if field == "latest_executor_status" and value and value not in EXECUTOR_STATUSES:
                raise ValueError(f"Ungueltiger latest_executor_status: {value}")
            if field == "latest_review_status" and value and value not in REVIEW_STATUSES:
                raise ValueError(f"Ungueltiger latest_review_status: {value}")
            updates.append(f"{field} = %s")
            params.append(value)

    if not updates:
        raise ValueError("Keine aktualisierbaren Felder angegeben")

    updates.append("updated_at = NOW()")
    params.append(plan_id)

    execute(
        f"UPDATE project_plans SET {', '.join(updates)} WHERE id = %s",
        params,
    )

    return get_plan_workflow(plan_id)


def get_project_plan_workflows(project_id):
    """Laedt Workflow-Daten fuer alle Plans eines Projekts."""
    ensure_plan_workflow_schema()

    rows = execute(
        """SELECT id, title, plan_type, status, workflow_stage,
                  current_state, target_state, next_action,
                  latest_executor_status, latest_review_status,
                  open_items_count, spec_ref, last_run_at, updated_at
           FROM project_plans
           WHERE project_name = %s
           ORDER BY updated_at DESC NULLS LAST, created_at DESC""",
        (project_id,),
        fetch=True,
    ) or []

    return [
        {
            "plan_id": r["id"],
            "title": r.get("title"),
            "plan_type": r.get("plan_type") or "plan",
            "status": r.get("status"),
            "workflow_stage": r.get("workflow_stage") or "idea",
            "current_state": r.get("current_state"),
            "target_state": r.get("target_state"),
            "next_action": r.get("next_action"),
            "latest_executor_status": r.get("latest_executor_status"),
            "latest_review_status": r.get("latest_review_status"),
            "open_items_count": r.get("open_items_count") or 0,
            "spec_ref": r.get("spec_ref"),
            "last_run_at": r["last_run_at"].isoformat() if r.get("last_run_at") else None,
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        }
        for r in rows
    ]


def _fetch_live_signals(project_name):
    """M7: Laedt aktuelle Audit/Quality/Governance-Signale fuer ein Projekt."""
    signals = {}

    # Quality-Score
    report_path = os.path.join(PROJECTS_DIR, project_name, ".quality", "report.json")
    if os.path.exists(report_path):
        try:
            with open(report_path, "r") as f:
                data = json.load(f)
            signals["latest_quality_score"] = data.get("score_numeric", 0)
        except (json.JSONDecodeError, OSError):
            pass

    # Governance-Gate
    try:
        from services.governance_service import get_governance_gate
        gate = get_governance_gate(project_name)
        signals["governance_status"] = gate.get("status")
    except Exception:
        pass

    # Letzter Audit-Status
    try:
        row = execute(
            """SELECT overall_status FROM audit_runs
               WHERE spec_id ILIKE %s
               ORDER BY started_at DESC LIMIT 1""",
            (f"%{project_name}%",),
            fetchone=True,
        )
        if row:
            signals["latest_audit_status"] = row["overall_status"]
    except Exception:
        pass

    return signals
