"""
Sprint 3 Sections fuer Projekt-Detail-Ansicht: GitHub, Health, Security
"""
import html as html_mod

from services.github_service import get_github_info_for_project
from services.health_check_service import get_health_for_project
from services.security_scanner import get_security_for_project


def _escape(text):
    return html_mod.escape(str(text)) if text else ""


def add_github_section(sections, project_path):
    """GitHub-Infos: Stars, Forks, Issues, PRs, CI/CD (Sprint 3)"""
    try:
        gh = get_github_info_for_project(project_path)
        if not gh:
            return
        rows = f"<tr><td style='color:#888;padding:4px 12px 4px 0'>Repository</td>"
        rows += f"<td><a href='https://github.com/{_escape(gh['full_name'])}' target='_blank' "
        rows += f"style='color:#4fc3f7'>{_escape(gh['full_name'])}</a></td></tr>"
        for label, key in [("Stars", "stars"), ("Forks", "forks"), ("Issues", "open_issues"),
                           ("Pull Requests", "open_prs"), ("Sprache", "language")]:
            val = gh.get(key)
            if val:
                rows += f"<tr><td style='color:#888;padding:4px 12px 4px 0'>{label}</td><td>{_escape(val)}</td></tr>"

        if gh.get("ci_status"):
            ci_colors = {"success": "#4caf50", "failure": "#ff5252", "cancelled": "#ffd740", "in_progress": "#42a5f5"}
            conclusion = gh.get("ci_conclusion") or gh["ci_status"]
            color = ci_colors.get(conclusion, "#888")
            workflow = _escape(gh.get("ci_workflow") or "Actions")
            rows += (
                f"<tr><td style='color:#888;padding:4px 12px 4px 0'>CI/CD</td>"
                f"<td><span style='color:{color}'>{_escape(conclusion)}</span> ({workflow})</td></tr>"
            )

        if gh.get("is_fork"):
            rows += "<tr><td style='color:#888;padding:4px 12px 4px 0'>Fork</td><td>Ja</td></tr>"

        sections.append(f"<h3>GitHub</h3><table style='font-size:13px'>{rows}</table>")
    except Exception:
        pass


def add_health_section(sections, name, pj, project_path):
    """Health-Check Status (Sprint 3)"""
    try:
        port = pj.get("port")
        health_url = pj.get("health_url")
        if not port and not health_url:
            return
        health = get_health_for_project(name, port=port, health_url=health_url)
        if not health:
            return
        status_colors = {"up": "#4caf50", "down": "#ff5252", "error": "#ff9800"}
        status_labels = {"up": "Erreichbar", "down": "Nicht erreichbar", "error": "Fehler"}
        s = health["status"]
        color = status_colors.get(s, "#888")
        label = status_labels.get(s, s)
        code_html = f" (HTTP {health['code']})" if health.get("code") else ""
        sections.append(
            f"<h3>Health-Check</h3>"
            f"<div style='font-size:13px'>"
            f"<span style='color:{color};font-weight:bold'>{label}</span>{code_html}"
            f" — {_escape(health.get('url', ''))} ({health.get('ms', 0)}ms)</div>"
        )
    except Exception:
        pass


def add_security_section(sections, name, project_path):
    """Security-Scan Ergebnisse (Sprint 3)"""
    try:
        result = get_security_for_project(name, project_path)
        if not result:
            return
        vulns = result.get("vulnerabilities", {})
        total = vulns.get("total", 0)
        if total == 0 and not vulns.get("note"):
            sections.append(
                f"<h3>Security</h3>"
                f"<div style='font-size:13px;color:#4caf50'>Keine bekannten Schwachstellen ({result['type']})</div>"
            )
            return
        if total == -1:
            sections.append(
                f"<h3>Security</h3>"
                f"<div style='font-size:13px;color:#888'>npm audit nicht moeglich (kein package-lock.json)</div>"
            )
            return
        if vulns.get("note") == "pip_audit_not_installed":
            sections.append(
                f"<h3>Security</h3>"
                f"<div style='font-size:13px;color:#888'>pip-audit nicht installiert</div>"
            )
            return

        sev_colors = {"critical": "#ff1744", "high": "#ff5252", "moderate": "#ff9800", "low": "#ffd740"}
        badges = ""
        for sev in ["critical", "high", "moderate", "low"]:
            count = vulns.get(sev, 0)
            if count > 0:
                badges += (
                    f"<span style='background:{sev_colors[sev]};color:#fff;padding:2px 8px;"
                    f"border-radius:4px;font-size:12px;margin-right:4px'>"
                    f"{count} {sev}</span>"
                )
        sections.append(
            f"<h3>Security <span style='font-weight:normal;color:#ff5252;font-size:12px'>"
            f"({total} Schwachstellen)</span></h3>"
            f"<div style='font-size:13px'>{badges}</div>"
        )
    except Exception:
        pass
