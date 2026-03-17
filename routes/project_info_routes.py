"""
Projekt-Info Route: /api/info - Umfassende Projekt-Detailansicht
"""
import os
import json
import html as html_mod
import subprocess
from flask import Blueprint, jsonify, request

from services.path_resolver import resolve_project_path
from services import get_docker_containers

project_info_bp = Blueprint('project_info', __name__)


def _escape(text):
    """HTML-Escape fuer sichere Ausgabe"""
    return html_mod.escape(str(text)) if text else ""


@project_info_bp.route('/api/info')
def get_info():
    """Gibt umfassende Info fuer ein Projekt zurueck"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Name fehlt"}), 400

    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"description": f"Projekt '{_escape(name)}' nicht gefunden.", "source": "", "name": name})

    sections = []

    # 1. project.json Metadaten
    pj = _load_project_json(project_path)

    if pj.get("description"):
        sections.append(f"<h3>Beschreibung</h3><p>{_escape(pj['description'])}</p>")

    _add_metadata_section(sections, pj, project_path)
    _add_tech_stack_section(sections, project_path)
    _add_git_section(sections, project_path)
    _add_readme_section(sections, project_path)
    _add_screenshots_section(sections, name, project_path)
    _add_milestones_section(sections, pj)
    _add_relations_section(sections, name)
    _add_sessions_section(sections, name)
    _add_containers_section(sections, name)

    description = "".join(sections) if sections else f"Keine Informationen fuer '{_escape(name)}' gefunden."
    return jsonify({"description": description, "source": "project", "name": name})


def _load_project_json(project_path):
    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _add_metadata_section(sections, pj, project_path):
    meta = []
    if pj.get("project_type"):
        meta.append(("Typ", _escape(pj["project_type"])))
    if pj.get("group"):
        meta.append(("Gruppe", _escape(pj["group"])))
    if pj.get("priority"):
        icons = {"high": "Hoch", "medium": "Mittel", "low": "Niedrig"}
        meta.append(("Prioritaet", _escape(icons.get(pj["priority"], pj["priority"]))))
    if pj.get("deadline"):
        meta.append(("Deadline", _escape(pj["deadline"])))
    if pj.get("progress") is not None:
        meta.append(("Fortschritt", f"{_escape(pj['progress'])}%"))
    meta.append(("Pfad", _escape(project_path)))

    if meta:
        rows = "".join(
            f"<tr><td style='color:#888;padding:4px 12px 4px 0'>{k}</td><td style='padding:4px 0'>{v}</td></tr>"
            for k, v in meta
        )
        sections.append(f"<h3>Details</h3><table style='font-size:13px'>{rows}</table>")


def _add_tech_stack_section(sections, project_path):
    tech = []
    markers = {
        "package.json": "Node.js", "tsconfig.json": "TypeScript", "next.config": "Next.js",
        "astro.config": "Astro", "nuxt.config": "Nuxt", "vite.config": "Vite",
        "requirements.txt": "Python", "pyproject.toml": "Python", "Pipfile": "Python",
        "app.py": "Flask", "manage.py": "Django", "Cargo.toml": "Rust",
        "go.mod": "Go", "composer.json": "PHP", "Gemfile": "Ruby",
        "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose", ".env": "Env Config",
        "tailwind.config": "Tailwind CSS", "CLAUDE.md": "Claude Code",
    }
    try:
        for f in os.listdir(project_path):
            for marker, label in markers.items():
                if f.startswith(marker) and label not in tech:
                    tech.append(label)
    except OSError:
        pass
    if tech:
        badges = " ".join(
            f"<code style='background:#1a3a5c;color:#4fc3f7;padding:2px 8px;border-radius:4px;font-size:12px'>"
            f"{_escape(t)}</code>"
            for t in tech
        )
        sections.append(f"<h3>Tech-Stack</h3><p>{badges}</p>")


def _add_git_section(sections, project_path):
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%h|%s|%ar", "-n", "5"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            commits_html = ""
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|', 2)
                    if len(parts) >= 3:
                        commits_html += (
                            f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>"
                            f"<code style='color:#888'>{_escape(parts[0])}</code>"
                            f"<span style='flex:1'>{_escape(parts[1])}</span>"
                            f"<span style='color:#666;font-size:11px'>{_escape(parts[2])}</span></div>"
                        )
            if commits_html:
                sections.append(f"<h3>Letzte Commits</h3>{commits_html}")

        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path, capture_output=True, text=True, timeout=3
        )
        if branch.returncode == 0 and branch.stdout.strip():
            sections.append(
                f"<p style='font-size:12px;color:#888'>Branch: <code>{_escape(branch.stdout.strip())}</code></p>"
            )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _add_readme_section(sections, project_path):
    for readme in ["README.md", "readme.md", "Readme.md"]:
        rpath = os.path.join(project_path, readme)
        if os.path.exists(rpath):
            try:
                with open(rpath, 'r', encoding='utf-8') as f:
                    content = f.read()[:3000]
                safe = html_mod.escape(content)
                safe = safe.replace('\n\n', '</p><p>').replace('\n', '<br>')
                sections.append(
                    f"<h3>README</h3><div style='font-size:13px;color:#aaa;max-height:300px;"
                    f"overflow-y:auto;background:#141414;padding:12px;border-radius:6px'><p>{safe}</p></div>"
                )
            except OSError:
                pass
            break


def _add_screenshots_section(sections, name, project_path):
    try:
        screenshots = [
            f"/{name}/{f}" for f in os.listdir(project_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
        ]
        if screenshots:
            imgs = "".join(
                f'<img src="{_escape(s)}" alt="{_escape(os.path.basename(s))}" '
                f'style="max-width:200px;max-height:150px;border-radius:6px;cursor:pointer;margin:4px">'
                for s in screenshots[:6]
            )
            sections.append(f"<h3>Screenshots</h3><div style='display:flex;flex-wrap:wrap;gap:8px'>{imgs}</div>")
    except OSError:
        pass


def _add_milestones_section(sections, pj):
    if pj.get("milestones"):
        ms_html = "".join(
            f"<div style='padding:4px 0;font-size:13px'>"
            f"{'done' if m.get('done') else 'pending'} {_escape(m.get('name', ''))}</div>"
            for m in pj["milestones"]
        )
        sections.append(f"<h3>Meilensteine</h3>{ms_html}")


def _add_relations_section(sections, name):
    try:
        from routes.relation_routes import load_relations
        rel_data = load_relations()
        outgoing = [r for r in rel_data.get("relations", []) if r.get("source") == name]
        incoming = [r for r in rel_data.get("relations", []) if r.get("target") == name]
        rel_types = {t["id"]: t for t in rel_data.get("relation_types", [])}
        if outgoing or incoming:
            rel_html = ""
            for r in outgoing:
                t = rel_types.get(r.get("type"), {})
                note = f" - {_escape(r.get('note'))}" if r.get('note') else ""
                rel_html += (
                    f"<div style='padding:4px 0;font-size:13px'>"
                    f"{_escape(t.get('icon', 'link'))} {_escape(t.get('name', r.get('type', '')))} -> "
                    f"<strong>{_escape(r.get('target', ''))}</strong>{note}</div>"
                )
            for r in incoming:
                t = rel_types.get(r.get("type"), {})
                note = f" - {_escape(r.get('note'))}" if r.get('note') else ""
                rel_html += (
                    f"<div style='padding:4px 0;font-size:13px'>"
                    f"{_escape(t.get('icon', 'link'))} {_escape(t.get('name', r.get('type', '')))} <- "
                    f"<strong>{_escape(r.get('source', ''))}</strong>{note}</div>"
                )
            sections.append(f"<h3>Beziehungen</h3>{rel_html}")
    except Exception:
        pass


def _add_sessions_section(sections, name):
    try:
        from services.db_service import execute
        sessions = execute(
            """SELECT session_uuid, slug, started_at, duration_ms, model,
                      user_message_count, assistant_message_count, total_input_tokens, total_output_tokens
               FROM sessions WHERE project_name ILIKE %s
               ORDER BY started_at DESC LIMIT 5""",
            (f"%{name.replace('_', '-').replace('proj-', 'proj_')}%",), fetch=True
        )
        if sessions:
            sess_html = ""
            for s in sessions:
                dt = s["started_at"].strftime("%d.%m.%y %H:%M") if s.get("started_at") else "-"
                dur_s = (s.get("duration_ms") or 0) // 1000
                dur = (
                    f"{dur_s // 3600}h {(dur_s % 3600) // 60}m" if dur_s >= 3600
                    else f"{dur_s // 60}m {dur_s % 60}s" if dur_s >= 60
                    else f"{dur_s}s"
                )
                msgs = (s.get("user_message_count") or 0) + (s.get("assistant_message_count") or 0)
                model_short = _escape((s.get('model') or '').replace('claude-', ''))
                sess_html += (
                    f"<a href='/sessions/{s['session_uuid']}' "
                    f"style='display:flex;gap:12px;padding:6px 0;font-size:13px;color:#ccc;text-decoration:none'>"
                    f"<span style='color:#888'>{dt}</span><span>{dur}</span>"
                    f"<span style='color:#888'>{msgs} msgs</span>"
                    f"<span style='color:#666;margin-left:auto'>{model_short}</span></a>"
                )
            sections.append(f"<h3>Claude Sessions</h3>{sess_html}")
    except Exception:
        pass


def _add_containers_section(sections, name):
    try:
        containers = get_docker_containers()
        proj_containers = [
            c for c in containers
            if name.lower().replace('_', '-') in c.get("name", "").lower()
            or name.lower().replace('-', '_') in c.get("name", "").lower()
        ]
        if proj_containers:
            cont_html = ""
            for c in proj_containers:
                status_icon = (
                    "running" if "Running" in c.get("status", "") or "Healthy" in c.get("status", "") else "stopped"
                )
                port = f":{c['port']}" if c.get("port") else ""
                cont_html += (
                    f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>"
                    f"{status_icon} <strong>{_escape(c.get('name', ''))}</strong>"
                    f"<span style='color:#888'>{_escape(c.get('image', ''))}</span>"
                    f"<span style='color:#666'>{_escape(port)}</span></div>"
                )
            sections.append(f"<h3>Container</h3>{cont_html}")
    except Exception:
        pass
