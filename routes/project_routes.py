"""
Projekt-bezogene Routes: Info, Detail, Save, Search, Export, Assets
"""
import os
import json
import html as html_mod
import subprocess
from datetime import datetime
from flask import Blueprint, jsonify, request, send_from_directory, abort

from config import PROJECTS_DIR
from services.path_resolver import resolve_project_path
from services import (
    scan_projects, get_docker_containers, update_project_json,
)

project_bp = Blueprint('projects', __name__)


def _escape(text):
    """HTML-Escape für sichere Ausgabe"""
    return html_mod.escape(str(text)) if text else ""


@project_bp.route('/project/<path:name>')
def project_detail(name):
    from flask import render_template
    return render_template('project_detail.html', project_name=name, active_page='dashboard')


@project_bp.route('/api/info')
def get_info():
    """Gibt umfassende Info für ein Projekt zurück"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Name fehlt"}), 400

    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"description": f"Projekt '{_escape(name)}' nicht gefunden.", "source": "", "name": name})

    sections = []

    # 1. project.json Metadaten
    pj = {}
    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                pj = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    if pj.get("description"):
        sections.append(f"<h3>Beschreibung</h3><p>{_escape(pj['description'])}</p>")

    # Metadaten-Tabelle
    meta = []
    if pj.get("project_type"):
        meta.append(("Typ", _escape(pj["project_type"])))
    if pj.get("group"):
        meta.append(("Gruppe", _escape(pj["group"])))
    if pj.get("priority"):
        icons = {"high": "Hoch", "medium": "Mittel", "low": "Niedrig"}
        meta.append(("Priorität", _escape(icons.get(pj["priority"], pj["priority"]))))
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

    # 2. Technologie-Stack erkennen
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

    # 3. Git Info
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

    # 4. README.md
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

    # 5. Screenshots
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

    # 6. Meilensteine
    if pj.get("milestones"):
        ms_html = "".join(
            f"<div style='padding:4px 0;font-size:13px'>"
            f"{'✅' if m.get('done') else '⬜'} {_escape(m.get('name', ''))}</div>"
            for m in pj["milestones"]
        )
        sections.append(f"<h3>Meilensteine</h3>{ms_html}")

    # 7. Beziehungen
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
                note = f" — {_escape(r.get('note'))}" if r.get('note') else ""
                rel_html += (
                    f"<div style='padding:4px 0;font-size:13px'>"
                    f"{_escape(t.get('icon', '🔗'))} {_escape(t.get('name', r.get('type', '')))} → "
                    f"<strong>{_escape(r.get('target', ''))}</strong>{note}</div>"
                )
            for r in incoming:
                t = rel_types.get(r.get("type"), {})
                note = f" — {_escape(r.get('note'))}" if r.get('note') else ""
                rel_html += (
                    f"<div style='padding:4px 0;font-size:13px'>"
                    f"{_escape(t.get('icon', '🔗'))} {_escape(t.get('name', r.get('type', '')))} ← "
                    f"<strong>{_escape(r.get('source', ''))}</strong>{note}</div>"
                )
            sections.append(f"<h3>Beziehungen</h3>{rel_html}")
    except Exception:
        pass

    # 8. Claude Sessions (letzte 5)
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

    # 9. Zugehörige Container
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
                    "🟢" if "Running" in c.get("status", "") or "Healthy" in c.get("status", "") else "🔴"
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

    description = "".join(sections) if sections else f"Keine Informationen für '{_escape(name)}' gefunden."
    return jsonify({"description": description, "source": "project", "name": name})


@project_bp.route('/api/project/<path:name>')
def get_project(name):
    """Lädt project.json für ein Projekt (inkl. Sub-Projekte)"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        except (json.JSONDecodeError, OSError) as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({
        "name": name, "description": "", "group": None,
        "priority": None, "deadline": None, "progress": None, "milestones": []
    })


@project_bp.route('/api/project/save', methods=['POST'])
def save_project():
    """Speichert project.json für ein Projekt (inkl. Sub-Projekte)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine Daten erhalten"}), 400

    project_name = data.get('name')
    if not project_name:
        return jsonify({"error": "Projektname fehlt"}), 400

    project_path = resolve_project_path(project_name)
    if not project_path:
        return jsonify({"error": f"Projekt '{project_name}' nicht gefunden"}), 404

    json_path = os.path.join(project_path, "project.json")

    existing = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    existing["name"] = project_name
    if "description" in data:
        existing["description"] = data["description"]
    if "group" in data:
        from routes.group_routes import get_valid_group_ids
        valid_groups = get_valid_group_ids()
        existing["group"] = data["group"] if data["group"] in valid_groups else None
    if "priority" in data:
        existing["priority"] = data["priority"] if data["priority"] in ["high", "medium", "low"] else None
    if "deadline" in data:
        existing["deadline"] = data["deadline"] if data["deadline"] else None
    if "progress" in data:
        try:
            existing["progress"] = int(data["progress"]) if data["progress"] is not None else None
        except (ValueError, TypeError):
            existing["progress"] = None
    if "milestones" in data:
        existing["milestones"] = data["milestones"]

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True, "message": f"project.json für {project_name} gespeichert"})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route('/api/projects/search')
def search_projects():
    """Ajax-Suche für Projekte"""
    query = request.args.get('q', '').lower().strip()
    limit = int(request.args.get('limit', 15))

    projects = scan_projects()
    results = []

    for p_name, p_data in projects.items():
        if query and query not in p_name.lower():
            continue
        results.append({
            'name': p_name,
            'type': p_data.get('project_type', 'project'),
            'description': p_data.get('function', '')[:60],
            'group': p_data.get('group')
        })

    results.sort(key=lambda x: (0 if x['name'].lower().startswith(query) else 1, x['name'].lower()))
    return jsonify(results[:limit])


@project_bp.route('/api/projects/refresh', methods=['POST'])
def refresh_all_projects():
    """Aktualisiert alle project.json Dateien mit neuen Erkennungen"""
    force_descriptions = request.args.get('force_descriptions', 'false').lower() == 'true'
    updated = []
    errors = []

    for item in os.listdir(PROJECTS_DIR):
        item_path = os.path.join(PROJECTS_DIR, item)
        if not os.path.isdir(item_path) or item.startswith('.'):
            continue
        if item == "project_dashboard":
            continue

        try:
            result = update_project_json(item_path, item, force_description=force_descriptions)
            if result:
                updated.append({
                    "name": item,
                    "description": result.get("description", "")[:80],
                    "topic": result.get("topic", "")
                })
        except Exception as e:
            errors.append({"name": item, "error": str(e)})

    return jsonify({
        "success": True, "updated": len(updated),
        "force_descriptions": force_descriptions,
        "projects": updated, "errors": errors
    })


@project_bp.route('/api/project/<path:name>/readme')
def get_readme(name):
    """Gibt README.md als Raw-Markdown und gerenderten HTML zurück"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    raw = ""
    filename = None
    for readme in ["README.md", "readme.md", "Readme.md"]:
        rpath = os.path.join(project_path, readme)
        if os.path.exists(rpath):
            try:
                with open(rpath, 'r', encoding='utf-8') as f:
                    raw = f.read()
                filename = readme
            except OSError as e:
                return jsonify({"error": str(e)}), 500
            break

    rendered = ""
    if raw:
        import markdown as md_lib
        rendered = md_lib.markdown(raw, extensions=["fenced_code", "tables", "toc"])

    return jsonify({"raw": raw, "html": rendered, "filename": filename or "README.md", "path": project_path})


@project_bp.route('/api/project/<path:name>/readme', methods=['PUT'])
def save_readme(name):
    """Speichert README.md"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    data = request.get_json()
    content = data.get('content', '')
    filename = data.get('filename', 'README.md')

    if filename not in ["README.md", "readme.md", "Readme.md"]:
        filename = "README.md"

    filepath = os.path.join(project_path, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True, "message": f"{filename} gespeichert", "path": filepath})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route('/api/project/<path:name>/export')
def export_project(name):
    """Exportiert Projekt-Infos als HTML/MD/JSON"""
    from flask import Response
    fmt = request.args.get('format', 'json')

    project_path = resolve_project_path(name)
    pj = {}
    if project_path:
        json_path = os.path.join(project_path, "project.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    pj = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

    if fmt == 'json':
        return Response(
            json.dumps({"project": pj}, indent=2, ensure_ascii=False, default=str),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={name}.json"}
        )
    elif fmt == 'md':
        md_parts = [f"# {_escape(name)}\n"]
        if pj.get("description"):
            md_parts.append(f"\n{pj['description']}\n")
        if pj.get("project_type"):
            md_parts.append(f"\n**Typ:** {pj['project_type']}")
        return Response(
            "\n".join(md_parts),
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={name}.md"}
        )
    elif fmt == 'html':
        desc = _escape(pj.get("description", ""))
        export_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8"><title>{_escape(name)}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #1e1e1e; color: #ddd; max-width: 900px; margin: 0 auto; padding: 30px; }}
h1 {{ color: #4fc3f7; }} h3 {{ color: #4fc3f7; border-bottom: 1px solid #333; padding-bottom: 5px; }}
@media print {{ body {{ background: white; color: black; }} h1,h3 {{ color: #0078d4; }} }}
</style>
</head>
<body>
<h1>{_escape(name)}</h1>
<p>{desc}</p>
<footer style="margin-top:40px;padding-top:20px;border-top:1px solid #333;color:#666;font-size:12px">
Generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')} — Projekt-Dashboard
</footer>
</body></html>"""
        return Response(
            export_html, mimetype="text/html",
            headers={"Content-Disposition": f"attachment; filename={name}.html"}
        )

    return jsonify({"error": f"Unbekanntes Format: {fmt}"}), 400


# === PROJEKT-ASSETS (Bilder) ===

ALLOWED_ASSET_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico'}


@project_bp.route('/<path:project_path>')
def serve_project_asset(project_path):
    """Serviert Bilder und andere Assets aus Projekten"""
    if '..' in project_path:
        abort(403)

    ext = os.path.splitext(project_path)[1].lower()
    if ext not in ALLOWED_ASSET_EXTENSIONS:
        abort(404)

    full_path = os.path.join(PROJECTS_DIR, project_path)
    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename)

    abort(404)
