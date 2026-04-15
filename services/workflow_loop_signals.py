"""
Signal-Aggregation fuer den Workflow-Loop.

Baut Priority-Hints (Governance, Quality, Audit, Dead-Code, Dispatch) aus
Governance-Gate, Quality-Report und Marker-Risiko-Text. Ausgelagert aus
workflow_loop_service.py wegen Dateigroessen-Limit.
"""
from services.governance_service import get_governance_gate


def _append_hint(hints, seen, item):
    key = (item["marker_id"], item["label"], item["hint"])
    if key in seen:
        return
    seen.add(key)
    hints.append(item)


def _append_marker_hints(hints, seen, marker):
    risk_text = str(getattr(marker, "risiko", "") or "").lower()
    if "governance" in risk_text:
        _append_hint(hints, seen, {
            "marker_id": marker.marker_id,
            "label": "Governance-Risiko",
            "level": "high" if "red" in risk_text else "medium",
            "hint": "bevorzugt bearbeiten",
        })
    if "audit" in risk_text:
        _append_hint(hints, seen, {
            "marker_id": marker.marker_id,
            "label": "Audit-Risiko",
            "level": "high" if "fail" in risk_text else "medium",
            "hint": "bevorzugt bearbeiten",
        })
    if "quality" in risk_text:
        _append_hint(hints, seen, {
            "marker_id": marker.marker_id,
            "label": "Quality-Risiko",
            "level": "high" if "krit" in risk_text or "red" in risk_text else "medium",
            "hint": "Quality-kritisch",
        })


def build_signals(project_name, markers, next_marker):
    gate = get_governance_gate(project_name) or {}
    quality_summary = gate.get("quality_summary") or {}
    audit_summary = gate.get("audit_summary") or {}
    next_marker_id = str((next_marker or {}).get("marker_id") or "")

    hints = []
    seen = set()

    for marker in markers:
        _append_marker_hints(hints, seen, marker)

    if next_marker_id and gate.get("status") in ("yellow", "red"):
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Governance-Risiko",
            "level": "high" if gate.get("status") == "red" else "medium",
            "hint": "bevorzugt bearbeiten",
        })

    quality_score = quality_summary.get("score_numeric")
    if next_marker_id and quality_score is not None and int(quality_score) < 60:
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Quality-Risiko",
            "level": "high" if int(quality_score) < 40 else "medium",
            "hint": "Quality-kritisch",
        })

    audit_status = str(audit_summary.get("overall_status") or "").strip()
    if next_marker_id and audit_status and audit_status.upper() in ("FAIL", "PARTIAL", "UNSICHER"):
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Audit-Risiko",
            "level": "high" if audit_status.upper() == "FAIL" else "medium",
            "hint": "bevorzugt bearbeiten",
        })

    # Dead-Code-Signal aus Quality-Report
    dead_code = quality_summary.get("dead_code_summary") or {}
    dead_total = dead_code.get("total", 0)
    if next_marker_id and dead_total > 0:
        parts = []
        if dead_code.get("unused_imports"):
            parts.append(f"{dead_code['unused_imports']} ungenutzte Imports")
        if dead_code.get("orphaned_files"):
            parts.append(f"{dead_code['orphaned_files']} verwaiste Dateien")
        if dead_code.get("unused_deps"):
            parts.append(f"{dead_code['unused_deps']} ungenutzte Dependencies")
        if dead_code.get("orphaned_assets"):
            parts.append(f"{dead_code['orphaned_assets']} verwaiste Assets")
        _append_hint(hints, seen, {
            "marker_id": next_marker_id,
            "label": "Dead Code",
            "level": "high" if dead_total > 20 else "medium",
            "hint": ", ".join(parts[:3]) if parts else f"{dead_total} Findings",
        })

    # Dispatch-Status pro Marker + Hints fuer unzugewiesene Marker
    try:
        from services.dispatch_service import get_dispatch_status_map
        dispatch_status = get_dispatch_status_map(project_name)
    except Exception:
        dispatch_status = {}
    for marker in markers:
        mid = marker.marker_id
        if marker.status in ("in_progress", "todo"):
            ds = dispatch_status.get(mid)
            if not ds:
                _append_hint(hints, seen, {
                    "marker_id": mid,
                    "label": "Dispatch",
                    "level": "low",
                    "hint": "Kein Tool zugewiesen",
                })

    return {
        "governance_status": gate.get("status") or "unknown",
        "audit_status": (audit_status or "unknown").lower(),
        "quality_score": quality_score if quality_score is not None else None,
        "dead_code_summary": dead_code if dead_code else None,
        "dispatch_status": dispatch_status,
        "priority_hints": hints[:8],
    }
