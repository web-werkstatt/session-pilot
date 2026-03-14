#!/usr/bin/env python3
"""
Projekt-Dashboard: Web-GUI für Projekt- und Container-Übersicht
Modulare Version
"""
import sys
import os

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request, send_from_directory, abort
from datetime import datetime
import json

from config import PROJECTS_DIR, HOST, PORT
from services import (
    get_gitea_repos,
    get_gitea_repo_commits,
    scan_projects,
    load_project_json,
    get_docker_containers,
    load_cache,
    save_cache,
    update_project_json
)

app = Flask(__name__)

# Session-Blueprints registrieren
from routes import register_blueprints
register_blueprints(app)

# Pfad zur Gruppen-Konfiguration
GROUPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'groups.json')

# Favoriten
FAVORITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'favorites.json')


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_favorites(favs):
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favs, f)


def load_groups():
    """Lädt die benutzerdefinierten Gruppen"""
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # Standard-Gruppen wenn Datei nicht existiert
    return {
        "groups": [
            {"id": "private", "name": "Privat", "icon": "🏠", "color": "#6b5b95", "description": "Private Projekte"},
            {"id": "business", "name": "Geschäftlich", "icon": "🏢", "color": "#0077b6", "description": "Geschäftliche Projekte"},
            {"id": "customer", "name": "Kunde", "icon": "👤", "color": "#2d6a4f", "description": "Kundenprojekte"}
        ]
    }


def save_groups(data):
    """Speichert die benutzerdefinierten Gruppen"""
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_valid_group_ids():
    """Gibt Liste aller gültigen Gruppen-IDs zurück"""
    groups_data = load_groups()
    return [g['id'] for g in groups_data.get('groups', [])]


@app.route('/api/favorites')
def get_favorites():
    return jsonify(load_favorites())


@app.route('/api/favorites', methods=['POST'])
def toggle_favorite():
    data = request.get_json()
    name = data.get('name', '')
    if not name:
        return jsonify({"error": "Name fehlt"}), 400
    favs = load_favorites()
    if name in favs:
        favs.remove(name)
        action = "removed"
    else:
        favs.append(name)
        action = "added"
    save_favorites(favs)
    return jsonify({"success": True, "action": action, "favorites": favs})


@app.route('/')
def index():
    return render_template('index.html', active_page='dashboard')


@app.route('/api/info')
def get_info():
    """Gibt umfassende Info für ein Projekt zurück"""
    import subprocess
    name = request.args.get('name', '')

    if not name:
        return jsonify({"error": "Name fehlt"}), 400

    # Projektpfad ermitteln (inkl. Sub-Projekte)
    if '/' in name:
        parts = name.split('/', 1)
        parent = parts[0]
        sub = parts[1]
        possible = [
            os.path.join(PROJECTS_DIR, parent, sub),
            os.path.join(PROJECTS_DIR, parent, "apps", sub),
            os.path.join(PROJECTS_DIR, parent, "packages", sub),
            os.path.join(PROJECTS_DIR, parent, "services", sub),
            os.path.join(PROJECTS_DIR, parent, "modules", sub),
        ]
        project_path = next((p for p in possible if os.path.isdir(p)), None)
    else:
        project_path = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(project_path):
            # Fallback: Bindestrich <-> Underscore
            alt = name.replace('-', '_') if '-' in name else name.replace('_', '-')
            project_path = os.path.join(PROJECTS_DIR, alt)
            if not os.path.isdir(project_path):
                project_path = None

    if not project_path:
        return jsonify({"description": f"Projekt '{name}' nicht gefunden.", "source": "", "name": name})

    sections = []

    # 1. project.json Metadaten
    pj = {}
    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                pj = json.load(f)
        except Exception:
            pass

    if pj.get("description"):
        sections.append(f"<h3>Beschreibung</h3><p>{pj['description']}</p>")

    # Metadaten-Tabelle
    meta = []
    if pj.get("project_type"):
        meta.append(("Typ", pj["project_type"]))
    if pj.get("group"):
        meta.append(("Gruppe", pj["group"]))
    if pj.get("priority"):
        icons = {"high": "🔴 Hoch", "medium": "🟡 Mittel", "low": "🟢 Niedrig"}
        meta.append(("Priorität", icons.get(pj["priority"], pj["priority"])))
    if pj.get("deadline"):
        meta.append(("Deadline", pj["deadline"]))
    if pj.get("progress") is not None:
        meta.append(("Fortschritt", f"{pj['progress']}%"))
    meta.append(("Pfad", project_path))

    if meta:
        rows = "".join(f"<tr><td style='color:#888;padding:4px 12px 4px 0'>{k}</td><td style='padding:4px 0'>{v}</td></tr>" for k, v in meta)
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
    except Exception:
        pass
    if tech:
        badges = " ".join(f"<code style='background:#1a3a5c;color:#4fc3f7;padding:2px 8px;border-radius:4px;font-size:12px'>{t}</code>" for t in tech)
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
                        commits_html += f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'><code style='color:#888'>{parts[0]}</code><span style='flex:1'>{parts[1]}</span><span style='color:#666;font-size:11px'>{parts[2]}</span></div>"
            if commits_html:
                sections.append(f"<h3>Letzte Commits</h3>{commits_html}")

        # Branch
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=project_path, capture_output=True, text=True, timeout=3)
        if branch.returncode == 0 and branch.stdout.strip():
            sections.append(f"<p style='font-size:12px;color:#888'>Branch: <code>{branch.stdout.strip()}</code></p>")
    except Exception:
        pass

    # 4. README.md
    for readme in ["README.md", "readme.md", "Readme.md"]:
        rpath = os.path.join(project_path, readme)
        if os.path.exists(rpath):
            try:
                with open(rpath, 'r', encoding='utf-8') as f:
                    content = f.read()[:3000]
                # Basic Markdown rendering
                import html as html_mod
                safe = html_mod.escape(content)
                safe = safe.replace('\n\n', '</p><p>').replace('\n', '<br>')
                sections.append(f"<h3>README</h3><div style='font-size:13px;color:#aaa;max-height:300px;overflow-y:auto;background:#141414;padding:12px;border-radius:6px'><p>{safe}</p></div>")
            except Exception:
                pass
            break

    # 5. Screenshots
    try:
        screenshots = [f"/{name}/{f}" for f in os.listdir(project_path)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))]
        if screenshots:
            imgs = "".join(f'<img src="{s}" alt="{os.path.basename(s)}" style="max-width:200px;max-height:150px;border-radius:6px;cursor:pointer;margin:4px">' for s in screenshots[:6])
            sections.append(f"<h3>Screenshots</h3><div style='display:flex;flex-wrap:wrap;gap:8px'>{imgs}</div>")
    except Exception:
        pass

    # 6. Meilensteine
    if pj.get("milestones"):
        ms_html = "".join(
            f"<div style='padding:4px 0;font-size:13px'>{'✅' if m.get('done') else '⬜'} {m.get('name','')}</div>"
            for m in pj["milestones"]
        )
        sections.append(f"<h3>Meilensteine</h3>{ms_html}")

    # 7. Beziehungen
    try:
        rel_data = load_relations()
        outgoing = [r for r in rel_data.get("relations", []) if r.get("source") == name]
        incoming = [r for r in rel_data.get("relations", []) if r.get("target") == name]
        rel_types = {t["id"]: t for t in rel_data.get("relation_types", [])}
        if outgoing or incoming:
            rel_html = ""
            for r in outgoing:
                t = rel_types.get(r.get("type"), {})
                rel_html += f"<div style='padding:4px 0;font-size:13px'>{t.get('icon','🔗')} {t.get('name',r.get('type',''))} → <strong>{r.get('target','')}</strong>{' — ' + r.get('note') if r.get('note') else ''}</div>"
            for r in incoming:
                t = rel_types.get(r.get("type"), {})
                rel_html += f"<div style='padding:4px 0;font-size:13px'>{t.get('icon','🔗')} {t.get('name',r.get('type',''))} ← <strong>{r.get('source','')}</strong>{' — ' + r.get('note') if r.get('note') else ''}</div>"
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
            (f"%{name.replace('_','-').replace('proj-','proj_')}%",), fetch=True
        )
        if sessions:
            sess_html = ""
            for s in sessions:
                dt = s["started_at"].strftime("%d.%m.%y %H:%M") if s.get("started_at") else "-"
                dur_s = (s.get("duration_ms") or 0) // 1000
                dur = f"{dur_s // 3600}h {(dur_s % 3600) // 60}m" if dur_s >= 3600 else f"{dur_s // 60}m {dur_s % 60}s" if dur_s >= 60 else f"{dur_s}s"
                msgs = (s.get("user_message_count") or 0) + (s.get("assistant_message_count") or 0)
                sess_html += f"<a href='/sessions/{s['session_uuid']}' style='display:flex;gap:12px;padding:6px 0;font-size:13px;color:#ccc;text-decoration:none'>"
                sess_html += f"<span style='color:#888'>{dt}</span><span>{dur}</span><span style='color:#888'>{msgs} msgs</span>"
                sess_html += f"<span style='color:#666;margin-left:auto'>{(s.get('model') or '').replace('claude-','')}</span></a>"
            sections.append(f"<h3>Claude Sessions</h3>{sess_html}")
    except Exception:
        pass

    # 9. Zugehörige Container
    try:
        from services.docker_service import get_docker_containers
        containers = get_docker_containers()
        proj_containers = [c for c in containers if name.lower().replace('_', '-') in c.get("name", "").lower() or name.lower().replace('-', '_') in c.get("name", "").lower()]
        if proj_containers:
            cont_html = ""
            for c in proj_containers:
                status_icon = "🟢" if "Running" in c.get("status", "") or "Healthy" in c.get("status", "") else "🔴"
                port = f":{c['port']}" if c.get("port") else ""
                cont_html += f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>{status_icon} <strong>{c.get('name','')}</strong><span style='color:#888'>{c.get('image','')}</span><span style='color:#666'>{port}</span></div>"
            sections.append(f"<h3>Container</h3>{cont_html}")
    except Exception:
        pass

    description = "".join(sections) if sections else f"Keine Informationen für '{name}' gefunden."
    return jsonify({"description": description, "source": "project", "name": name})


@app.route('/project/<path:name>')
def project_detail(name):
    return render_template('project_detail.html', project_name=name, active_page='dashboard')


@app.route('/api/project/<path:name>/export')
def export_project(name):
    """Exportiert Projekt-Infos als HTML/MD/JSON"""
    fmt = request.args.get('format', 'json')

    # Info laden (intern)
    import urllib.parse
    with app.test_request_context(f'/api/info?name={urllib.parse.quote(name)}'):
        info_resp = get_info()
        info_data = info_resp.get_json()

    if fmt == 'json':
        # Projekt-Daten als JSON
        pj = {}
        project_path = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(project_path):
            alt = name.replace('-', '_') if '-' in name else name.replace('_', '-')
            project_path = os.path.join(PROJECTS_DIR, alt)
        json_path = os.path.join(project_path, "project.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    pj = json.load(f)
            except Exception:
                pass
        from flask import Response
        return Response(
            json.dumps({"project": pj, "info_html": info_data.get("description", "")}, indent=2, ensure_ascii=False, default=str),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={name}.json"}
        )

    elif fmt == 'md':
        # Markdown Export
        import re
        html = info_data.get("description", "")
        # Einfache HTML->MD Konvertierung
        md = html
        md = re.sub(r'<h3>(.*?)</h3>', r'\n## \1\n', md)
        md = re.sub(r'<strong>(.*?)</strong>', r'**\1**', md)
        md = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', md)
        md = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r'![](\1)', md)
        md = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', md)
        md = re.sub(r'<br\s*/?>', '\n', md)
        md = re.sub(r'<[^>]+>', '', md)
        md = f"# {name}\n\n{md}"
        from flask import Response
        return Response(md, mimetype="text/markdown",
                       headers={"Content-Disposition": f"attachment; filename={name}.md"})

    elif fmt == 'html':
        # Standalone HTML Export (Dark Theme, druckbar)
        html_content = info_data.get("description", "")
        export_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #1e1e1e; color: #ddd; max-width: 900px; margin: 0 auto; padding: 30px; }}
h1 {{ color: #4fc3f7; margin-bottom: 20px; }}
h3 {{ color: #4fc3f7; margin: 25px 0 10px; border-bottom: 1px solid #333; padding-bottom: 5px; }}
table {{ font-size: 14px; }}
code {{ background: #141414; color: #4fc3f7; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
img {{ max-width: 300px; border-radius: 8px; margin: 6px; cursor: pointer; }}
a {{ color: #4fc3f7; text-decoration: none; }}
pre {{ background: #141414; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
@media print {{ body {{ background: white; color: black; }} h1,h3 {{ color: #0078d4; }} }}
</style>
</head>
<body>
<h1>{name}</h1>
{html_content}
<footer style="margin-top:40px;padding-top:20px;border-top:1px solid #333;color:#666;font-size:12px">
Generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')} — Projekt-Dashboard
</footer>
</body>
</html>"""
        from flask import Response
        return Response(export_html, mimetype="text/html",
                       headers={"Content-Disposition": f"attachment; filename={name}.html"})

    return jsonify({"error": f"Unbekanntes Format: {fmt}"}), 400


@app.route('/containers')
def containers():
    return render_template('containers.html', active_page='containers')


@app.route('/api/projects/search')
def search_projects():
    """Ajax-Suche für Projekte"""
    query = request.args.get('q', '').lower().strip()
    limit = int(request.args.get('limit', 15))

    projects = scan_projects()
    results = []

    for name, data in projects.items():
        if query and query not in name.lower():
            continue
        results.append({
            'name': name,
            'type': data.get('project_type', 'project'),
            'description': data.get('function', '')[:60],
            'group': data.get('group')
        })

    # Sortieren: exakte Matches zuerst, dann alphabetisch
    results.sort(key=lambda x: (0 if x['name'].lower().startswith(query) else 1, x['name'].lower()))

    return jsonify(results[:limit])


@app.route('/api/data')
def get_data():
    projects = scan_projects()
    containers = get_docker_containers()
    gitea_repos = get_gitea_repos()
    gitea_commits = get_gitea_repo_commits()

    # Sync-Status für jedes Projekt berechnen
    for proj_name, proj_info in projects.items():
        if proj_info.get("has_gitea") and proj_info.get("gitea_repo"):
            repo_name = proj_info["gitea_repo"]
            if repo_name in gitea_commits:
                remote_sha = gitea_commits[repo_name]["sha"]
                local_sha = proj_info.get("local_sha", "")
                if local_sha and remote_sha:
                    if local_sha == remote_sha:
                        proj_info["sync_status"] = "synced"
                    else:
                        proj_info["sync_status"] = "differs"
                    proj_info["remote_sha"] = remote_sha
                else:
                    proj_info["sync_status"] = "unknown"
            else:
                proj_info["sync_status"] = "not_on_gitea"
        else:
            proj_info["sync_status"] = "no_remote"

    # Cache laden und neue Projekte erkennen
    cache = load_cache()
    cached_projects = set(cache.get("projects", {}).keys())
    current_projects = set(projects.keys())
    new_projects = list(current_projects - cached_projects)

    # Cache aktualisieren - Aktivitätsdaten werden in project_scanner.py verwaltet
    # Hier nur last_update und neue Projekte registrieren
    for proj_name in new_projects:
        if proj_name not in cache.get("projects", {}):
            if "projects" not in cache:
                cache["projects"] = {}
            cache["projects"][proj_name] = {"name": proj_name}
    cache["last_update"] = datetime.now().isoformat()
    save_cache(cache)

    # Container-Stats
    running = sum(1 for c in containers if "Running" in c.get("status", "") or "Healthy" in c.get("status", ""))
    stopped = sum(1 for c in containers if "Stopped" in c.get("status", ""))
    unhealthy = sum(1 for c in containers if "Unhealthy" in c.get("status", ""))

    return jsonify({
        "projects": list(projects.values()),
        "containers": containers,
        "gitea_repos": gitea_repos,
        "new_projects": new_projects,
        "stats": {
            "total_projects": len(projects),
            "total_containers": len(containers),
            "running": running,
            "stopped": stopped,
            "unhealthy": unhealthy,
            "gitea_repos": len(gitea_repos)
        },
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })


@app.route('/api/containers')
def api_containers():
    containers = get_docker_containers()
    running = sum(1 for c in containers if "Running" in c.get("status", "") or "Healthy" in c.get("status", ""))
    stopped = sum(1 for c in containers if "Stopped" in c.get("status", ""))
    unhealthy = sum(1 for c in containers if "Unhealthy" in c.get("status", ""))

    return jsonify({
        "containers": containers,
        "stats": {
            "total": len(containers),
            "running": running,
            "stopped": stopped,
            "unhealthy": unhealthy
        },
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })


@app.route('/api/project/save', methods=['POST'])
def save_project():
    """Speichert project.json für ein Projekt (inkl. Sub-Projekte)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine Daten erhalten"}), 400

    project_name = data.get('name')
    if not project_name:
        return jsonify({"error": "Projektname fehlt"}), 400

    # Unterstütze Sub-Projekte: "parent/subproject" -> PROJECTS_DIR/parent/apps/subproject etc.
    if '/' in project_name:
        parts = project_name.split('/', 1)
        parent_name = parts[0]
        sub_path = parts[1]
        # Suche Sub-Projekt in bekannten Ordnern UND im Root des Parent-Projekts
        possible_paths = [
            # Root-Level Sub-Projekt (z.B. python_extractor direkt im Projekt)
            os.path.join(PROJECTS_DIR, parent_name, sub_path),
            # Standard Sub-Projekt-Ordner
            os.path.join(PROJECTS_DIR, parent_name, "apps", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "packages", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "services", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "modules", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "libs", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "plugins", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "themes", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "sites", sub_path),
        ]
        project_path = None
        for p in possible_paths:
            if os.path.isdir(p):
                project_path = p
                break
        if not project_path:
            return jsonify({"error": f"Sub-Projekt '{project_name}' nicht gefunden"}), 404
    else:
        project_path = os.path.join(PROJECTS_DIR, project_name)
        if not os.path.isdir(project_path):
            return jsonify({"error": "Projekt nicht gefunden"}), 404

    json_path = os.path.join(project_path, "project.json")

    # Bestehende project.json laden oder neue erstellen
    existing = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass

    # Felder aktualisieren
    existing["name"] = project_name
    if "description" in data:
        existing["description"] = data["description"]
    if "group" in data:
        valid_groups = get_valid_group_ids()
        existing["group"] = data["group"] if data["group"] in valid_groups else None
    if "priority" in data:
        existing["priority"] = data["priority"] if data["priority"] in ["high", "medium", "low"] else None
    if "deadline" in data:
        existing["deadline"] = data["deadline"] if data["deadline"] else None
    if "progress" in data:
        try:
            existing["progress"] = int(data["progress"]) if data["progress"] is not None else None
        except:
            existing["progress"] = None
    if "milestones" in data:
        existing["milestones"] = data["milestones"]

    # Speichern
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True, "message": f"project.json für {project_name} gespeichert"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/projects/refresh', methods=['POST'])
def refresh_all_projects():
    """Aktualisiert alle project.json Dateien mit neuen Erkennungen

    Query-Parameter:
        force_descriptions=true  - Überschreibt auch existierende Beschreibungen
    """
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
        "success": True,
        "updated": len(updated),
        "force_descriptions": force_descriptions,
        "projects": updated,
        "errors": errors
    })


# ============== RELATIONS / ABHÄNGIGKEITEN ==============

RELATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'relations.json')


def load_relations():
    """Lädt die Projekt-Beziehungen"""
    if os.path.exists(RELATIONS_FILE):
        try:
            with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "relations": [],
        "relation_types": [
            {"id": "depends_on", "name": "hängt ab von", "icon": "🔗", "color": "#3498db"},
            {"id": "replaces", "name": "ersetzt", "icon": "🔄", "color": "#e74c3c"},
            {"id": "extends", "name": "erweitert", "icon": "➕", "color": "#2ecc71"},
            {"id": "uses", "name": "nutzt", "icon": "⚙️", "color": "#9b59b6"},
            {"id": "related", "name": "verwandt mit", "icon": "🔀", "color": "#f39c12"},
            {"id": "fork_of", "name": "Fork von", "icon": "🍴", "color": "#1abc9c"}
        ]
    }


def save_relations(data):
    """Speichert die Projekt-Beziehungen"""
    with open(RELATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route('/dependencies')
def dependencies_page():
    """Projekt-Abhängigkeiten Seite"""
    return render_template('dependencies.html', active_page='dependencies')


@app.route('/api/relations')
def get_relations():
    """Gibt alle Projekt-Beziehungen zurück"""
    data = load_relations()
    return jsonify(data)


@app.route('/api/relations', methods=['POST'])
def add_relation():
    """Fügt eine neue Beziehung hinzu"""
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    source = req.get("source")
    target = req.get("target")
    relation_type = req.get("type")
    note = req.get("note", "")

    if not source or not target or not relation_type:
        return jsonify({"error": "source, target und type sind erforderlich"}), 400

    if source == target:
        return jsonify({"error": "Projekt kann nicht mit sich selbst verknüpft werden"}), 400

    data = load_relations()

    # Prüfe ob Beziehung bereits existiert
    for rel in data["relations"]:
        if rel["source"] == source and rel["target"] == target and rel["type"] == relation_type:
            return jsonify({"error": "Diese Beziehung existiert bereits"}), 400

    # Neue Beziehung hinzufügen
    new_relation = {
        "id": f"{source}_{target}_{relation_type}_{datetime.now().timestamp()}",
        "source": source,
        "target": target,
        "type": relation_type,
        "note": note,
        "created": datetime.now().isoformat()
    }
    data["relations"].append(new_relation)
    save_relations(data)

    return jsonify({"success": True, "relation": new_relation})


@app.route('/api/relations/<relation_id>', methods=['DELETE'])
def delete_relation(relation_id):
    """Löscht eine Beziehung"""
    data = load_relations()
    original_count = len(data["relations"])
    data["relations"] = [r for r in data["relations"] if r.get("id") != relation_id]

    if len(data["relations"]) == original_count:
        return jsonify({"error": "Beziehung nicht gefunden"}), 404

    save_relations(data)
    return jsonify({"success": True})


@app.route('/api/relations/types')
def get_relation_types():
    """Gibt alle Beziehungstypen zurück"""
    data = load_relations()
    return jsonify(data.get("relation_types", []))


@app.route('/api/relations/types', methods=['POST'])
def add_relation_type():
    """Fügt einen neuen Beziehungstyp hinzu"""
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    type_id = req.get("id", "").lower().replace(" ", "_")
    name = req.get("name")
    icon = req.get("icon", "🔗")
    color = req.get("color", "#666666")

    if not type_id or not name:
        return jsonify({"error": "id und name sind erforderlich"}), 400

    data = load_relations()

    # Prüfe ob Typ bereits existiert
    if any(t["id"] == type_id for t in data["relation_types"]):
        return jsonify({"error": "Dieser Beziehungstyp existiert bereits"}), 400

    new_type = {"id": type_id, "name": name, "icon": icon, "color": color}
    data["relation_types"].append(new_type)
    save_relations(data)

    return jsonify({"success": True, "type": new_type})


@app.route('/api/project/<path:project_name>/relations')
def get_project_relations(project_name):
    """Gibt alle Beziehungen für ein bestimmtes Projekt zurück"""
    data = load_relations()
    project_relations = {
        "outgoing": [],  # Dieses Projekt → andere
        "incoming": []   # Andere → dieses Projekt
    }

    for rel in data["relations"]:
        if rel["source"] == project_name:
            project_relations["outgoing"].append(rel)
        elif rel["target"] == project_name:
            project_relations["incoming"].append(rel)

    return jsonify(project_relations)


# ============== IDEAS / NOTIZEN ==============

IDEAS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ideas.json')


def load_ideas():
    """Lädt die Ideen/Notizen"""
    if os.path.exists(IDEAS_FILE):
        try:
            with open(IDEAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "ideas": [],
        "categories": [
            {"id": "feature", "name": "Feature-Idee", "icon": "💡", "color": "#f1c40f"},
            {"id": "improvement", "name": "Verbesserung", "icon": "🔧", "color": "#3498db"},
            {"id": "bug", "name": "Bug/Problem", "icon": "🐛", "color": "#e74c3c"},
            {"id": "note", "name": "Notiz", "icon": "📝", "color": "#9b59b6"},
            {"id": "research", "name": "Recherche", "icon": "🔍", "color": "#1abc9c"},
            {"id": "question", "name": "Frage", "icon": "❓", "color": "#e67e22"}
        ]
    }


def save_ideas(data):
    """Speichert die Ideen/Notizen"""
    with open(IDEAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route('/api/ideas')
def get_ideas():
    """Gibt alle Ideen zurück"""
    data = load_ideas()
    # Nach Datum sortieren (neueste zuerst)
    data["ideas"] = sorted(data["ideas"], key=lambda x: x.get("created", ""), reverse=True)
    return jsonify(data)


@app.route('/api/ideas', methods=['POST'])
def add_idea():
    """Fügt eine neue Idee hinzu"""
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    title = req.get("title", "").strip()
    content = req.get("content", "").strip()
    category = req.get("category", "note")
    project = req.get("project")  # Optional: zugehöriges Projekt
    priority = req.get("priority", "normal")  # low, normal, high

    if not title:
        return jsonify({"error": "Titel ist erforderlich"}), 400

    data = load_ideas()

    new_idea = {
        "id": f"idea_{datetime.now().timestamp()}",
        "title": title,
        "content": content,
        "category": category,
        "project": project,
        "priority": priority,
        "status": "open",  # open, in_progress, done, archived
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }
    data["ideas"].append(new_idea)
    save_ideas(data)

    return jsonify({"success": True, "idea": new_idea})


@app.route('/api/ideas/<idea_id>', methods=['PUT'])
def update_idea(idea_id):
    """Aktualisiert eine Idee"""
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    data = load_ideas()

    for idea in data["ideas"]:
        if idea["id"] == idea_id:
            if "title" in req:
                idea["title"] = req["title"]
            if "content" in req:
                idea["content"] = req["content"]
            if "category" in req:
                idea["category"] = req["category"]
            if "project" in req:
                idea["project"] = req["project"]
            if "priority" in req:
                idea["priority"] = req["priority"]
            if "status" in req:
                idea["status"] = req["status"]
            idea["updated"] = datetime.now().isoformat()
            save_ideas(data)
            return jsonify({"success": True, "idea": idea})

    return jsonify({"error": "Idee nicht gefunden"}), 404


@app.route('/api/ideas/<idea_id>', methods=['DELETE'])
def delete_idea(idea_id):
    """Löscht eine Idee"""
    data = load_ideas()
    original_count = len(data["ideas"])
    data["ideas"] = [i for i in data["ideas"] if i.get("id") != idea_id]

    if len(data["ideas"]) == original_count:
        return jsonify({"error": "Idee nicht gefunden"}), 404

    save_ideas(data)
    return jsonify({"success": True})


@app.route('/api/ideas/categories')
def get_idea_categories():
    """Gibt alle Ideen-Kategorien zurück"""
    data = load_ideas()
    return jsonify(data.get("categories", []))


@app.route('/news')
def news_page():
    """News-Detailseite"""
    return render_template('news.html', active_page='news')


@app.route('/vorlagen')
def vorlagen_page():
    """Vorlagen-Sammlung"""
    return render_template('vorlagen.html', active_page='vorlagen')


@app.route('/api/vorlagen')
def get_vorlagen():
    """Listet alle verfügbaren Vorlagen"""
    vorlagen_dir = os.path.join(PROJECTS_DIR, 'vorlagen')
    vorlagen = []

    if os.path.isdir(vorlagen_dir):
        for item in os.listdir(vorlagen_dir):
            item_path = os.path.join(vorlagen_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                vorlage = {
                    "name": item,
                    "path": f"/mnt/projects/vorlagen/{item}",
                    "files": [],
                    "readme": None,
                    "preview": None
                }

                # Dateien auflisten
                for f in os.listdir(item_path):
                    if not f.startswith('.'):
                        vorlage["files"].append(f)
                        if f.lower() == 'readme.md':
                            try:
                                with open(os.path.join(item_path, f), 'r') as rf:
                                    vorlage["readme"] = rf.read()
                            except:
                                pass
                        if f.endswith('.html'):
                            vorlage["preview"] = f

                vorlagen.append(vorlage)

    return jsonify({
        "vorlagen": vorlagen,
        "total": len(vorlagen),
        "path": vorlagen_dir
    })


@app.route('/api/news')
def get_news():
    """Sammelt aktuelle Neuigkeiten aus allen Projekten"""
    projects = scan_projects(auto_generate=False)
    gitea_commits = get_gitea_repo_commits()

    news_items = []
    now = datetime.now()

    for proj_name, proj_info in projects.items():
        # Letzte Commits als News
        if proj_info.get("last_commit"):
            try:
                commit_date = datetime.strptime(proj_info["last_commit"][:16], "%Y-%m-%d %H:%M")
                days_ago = (now - commit_date).days
                if days_ago <= 7:  # Nur letzte 7 Tage
                    news_items.append({
                        "type": "commit",
                        "project": proj_name,
                        "title": f"Commit in {proj_name}",
                        "message": proj_info.get("last_commit_msg", ""),
                        "date": proj_info["last_commit"],
                        "days_ago": days_ago,
                        "icon": "git-commit"
                    })
            except:
                pass

        # Letzte Dateiänderungen
        if proj_info.get("last_file_change"):
            try:
                change_date = datetime.strptime(proj_info["last_file_change"], "%Y-%m-%d %H:%M")
                days_ago = (now - change_date).days
                if days_ago <= 3:  # Nur letzte 3 Tage
                    news_items.append({
                        "type": "file_change",
                        "project": proj_name,
                        "title": f"Dateien geändert in {proj_name}",
                        "message": f"Letzte Änderung: {proj_info['last_file_change']}",
                        "date": proj_info["last_file_change"],
                        "days_ago": days_ago,
                        "icon": "file-edit"
                    })
            except:
                pass

        # Neue Projekte (auto_generated heute)
        if proj_info.get("project_type") == "project":
            project_path = os.path.join(PROJECTS_DIR, proj_name, "project.json")
            if os.path.exists(project_path):
                try:
                    mtime = os.path.getmtime(project_path)
                    create_date = datetime.fromtimestamp(mtime)
                    days_ago = (now - create_date).days
                    if days_ago <= 1:  # Neu erstellt heute/gestern
                        news_items.append({
                            "type": "new_project",
                            "project": proj_name,
                            "title": f"Neues Projekt: {proj_name}",
                            "message": proj_info.get("function", "Keine Beschreibung"),
                            "date": create_date.strftime("%Y-%m-%d %H:%M"),
                            "days_ago": days_ago,
                            "icon": "folder-plus"
                        })
                except:
                    pass

        # Sync-Status Probleme
        if proj_info.get("sync_status") == "differs":
            news_items.append({
                "type": "sync_warning",
                "project": proj_name,
                "title": f"Sync-Konflikt: {proj_name}",
                "message": "Lokale und Remote-Version unterscheiden sich",
                "date": now.strftime("%Y-%m-%d %H:%M"),
                "days_ago": 0,
                "icon": "alert-triangle"
            })

    # Nach Datum sortieren (neueste zuerst)
    news_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Limit auf 50 Items
    news_items = news_items[:50]

    # Headlines für Ticker (Top 5)
    headlines = news_items[:5]

    return jsonify({
        "news": news_items,
        "headlines": headlines,
        "total": len(news_items),
        "timestamp": now.strftime("%d.%m.%Y %H:%M:%S")
    })


@app.route('/api/news/detail/<project>')
def get_news_detail(project):
    """Holt detaillierte News-Informationen für ein Projekt"""
    import subprocess

    project_path = os.path.join(PROJECTS_DIR, project)
    if not os.path.isdir(project_path):
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    details = {
        "project": project,
        "path": project_path,
        "commits": [],
        "recent_files": [],
        "project_info": {},
        "git_status": None
    }

    # Projekt-Info laden
    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                details["project_info"] = json.load(f)
        except:
            pass

    # Letzte 5 Commits holen
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%H|%s|%an|%ar", "-n", "5"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line and '|' in line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        details["commits"].append({
                            "sha": parts[0][:8],
                            "message": parts[1],
                            "author": parts[2],
                            "when": parts[3]
                        })
    except:
        pass

    # Git Status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            details["git_status"] = {
                "clean": len(changes) == 0,
                "changes": len(changes),
                "modified": len([c for c in changes if c.startswith(' M') or c.startswith('M ')]),
                "untracked": len([c for c in changes if c.startswith('??')]),
                "staged": len([c for c in changes if c.startswith('A ') or c.startswith('M ')])
            }
    except:
        pass

    # Kürzlich geänderte Dateien (letzte 10)
    try:
        result = subprocess.run(
            ["find", ".", "-type", "f", "-mtime", "-3", "-not", "-path", "./.git/*",
             "-not", "-name", "*.pyc", "-not", "-path", "./node_modules/*",
             "-not", "-path", "./__pycache__/*"],
            cwd=project_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            files = [f.lstrip('./') for f in result.stdout.strip().split('\n') if f and f != '.']
            # Nach Änderungszeit sortieren
            file_times = []
            for f in files[:20]:
                try:
                    full_path = os.path.join(project_path, f)
                    mtime = os.path.getmtime(full_path)
                    file_times.append((f, mtime))
                except:
                    pass
            file_times.sort(key=lambda x: x[1], reverse=True)
            details["recent_files"] = [
                {
                    "name": f[0],
                    "modified": datetime.fromtimestamp(f[1]).strftime("%d.%m.%Y %H:%M")
                }
                for f in file_times[:10]
            ]
    except:
        pass

    return jsonify(details)


@app.route('/api/project/<path:name>')
def get_project(name):
    """Lädt project.json für ein Projekt (inkl. Sub-Projekte)"""
    # Unterstütze Sub-Projekte: "parent/subproject"
    if '/' in name:
        parts = name.split('/', 1)
        parent_name = parts[0]
        sub_path = parts[1]
        # Suche Sub-Projekt in Root UND bekannten Ordnern
        possible_paths = [
            # Root-Level Sub-Projekt (z.B. python_extractor direkt im Projekt)
            os.path.join(PROJECTS_DIR, parent_name, sub_path),
            # Standard Sub-Projekt-Ordner
            os.path.join(PROJECTS_DIR, parent_name, "apps", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "packages", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "services", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "modules", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "libs", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "plugins", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "themes", sub_path),
            os.path.join(PROJECTS_DIR, parent_name, "sites", sub_path),
        ]
        project_path = None
        for p in possible_paths:
            if os.path.isdir(p):
                project_path = p
                break
        if not project_path:
            return jsonify({"error": f"Sub-Projekt '{name}' nicht gefunden"}), 404
    else:
        project_path = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(project_path):
            return jsonify({"error": "Projekt nicht gefunden"}), 404

    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Leere Struktur zurückgeben wenn keine project.json existiert
    return jsonify({
        "name": name,
        "description": "",
        "group": None,
        "priority": None,
        "deadline": None,
        "progress": None,
        "milestones": []
    })


# === GRUPPEN API ===

@app.route('/api/groups')
def api_get_groups():
    """Gibt alle benutzerdefinierten Gruppen zurück"""
    return jsonify(load_groups())


@app.route('/api/groups', methods=['POST'])
def api_create_group():
    """Erstellt eine neue Gruppe"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine Daten erhalten"}), 400

    group_id = data.get('id', '').strip().lower()
    group_name = data.get('name', '').strip()
    group_icon = data.get('icon', '📁')
    group_color = data.get('color', '#666666')
    group_desc = data.get('description', '')

    if not group_id or not group_name:
        return jsonify({"error": "ID und Name sind erforderlich"}), 400

    # ID validieren (nur alphanumerisch und Unterstriche)
    import re
    if not re.match(r'^[a-z0-9_]+$', group_id):
        return jsonify({"error": "ID darf nur Kleinbuchstaben, Zahlen und Unterstriche enthalten"}), 400

    groups_data = load_groups()

    # Prüfen ob ID bereits existiert
    existing_ids = [g['id'] for g in groups_data['groups']]
    if group_id in existing_ids:
        return jsonify({"error": f"Gruppe mit ID '{group_id}' existiert bereits"}), 400

    # Neue Gruppe hinzufügen
    groups_data['groups'].append({
        "id": group_id,
        "name": group_name,
        "icon": group_icon,
        "color": group_color,
        "description": group_desc
    })

    save_groups(groups_data)
    return jsonify({"success": True, "message": f"Gruppe '{group_name}' erstellt"})


@app.route('/api/groups/<group_id>', methods=['PUT'])
def api_update_group(group_id):
    """Aktualisiert eine bestehende Gruppe"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Keine Daten erhalten"}), 400

    groups_data = load_groups()

    # Gruppe finden
    group_idx = None
    for i, g in enumerate(groups_data['groups']):
        if g['id'] == group_id:
            group_idx = i
            break

    if group_idx is None:
        return jsonify({"error": f"Gruppe '{group_id}' nicht gefunden"}), 404

    # Felder aktualisieren
    if 'name' in data:
        groups_data['groups'][group_idx]['name'] = data['name']
    if 'icon' in data:
        groups_data['groups'][group_idx]['icon'] = data['icon']
    if 'color' in data:
        groups_data['groups'][group_idx]['color'] = data['color']
    if 'description' in data:
        groups_data['groups'][group_idx]['description'] = data['description']

    save_groups(groups_data)
    return jsonify({"success": True, "message": f"Gruppe '{group_id}' aktualisiert"})


@app.route('/api/groups/<group_id>', methods=['DELETE'])
def api_delete_group(group_id):
    """Löscht eine Gruppe"""
    groups_data = load_groups()

    # Gruppe finden
    group_idx = None
    for i, g in enumerate(groups_data['groups']):
        if g['id'] == group_id:
            group_idx = i
            break

    if group_idx is None:
        return jsonify({"error": f"Gruppe '{group_id}' nicht gefunden"}), 404

    # Gruppe entfernen
    removed = groups_data['groups'].pop(group_idx)
    save_groups(groups_data)

    return jsonify({"success": True, "message": f"Gruppe '{removed['name']}' gelöscht"})


# === PROJEKT-ASSETS (Bilder) ===

@app.route('/<path:project_path>')
def serve_project_asset(project_path):
    """Serviert Bilder und andere Assets aus Projekten"""
    # Erlaubte Dateiendungen
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico'}

    # Sicherheitscheck: Keine Pfad-Traversal erlauben
    if '..' in project_path:
        abort(403)

    # Dateiendung prüfen
    ext = os.path.splitext(project_path)[1].lower()
    if ext not in allowed_extensions:
        abort(404)

    # Voller Pfad zur Datei (direkt)
    full_path = os.path.join(PROJECTS_DIR, project_path)

    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename)

    # Fallback: Suche in Sub-Verzeichnissen (für Sub-Projekte)
    # z.B. /archon-ui-main/public/img.png -> /Archon/archon-ui-main/public/img.png
    try:
        for entry in os.listdir(PROJECTS_DIR):
            subdir = os.path.join(PROJECTS_DIR, entry)
            if os.path.isdir(subdir):
                candidate = os.path.join(subdir, project_path)
                if os.path.isfile(candidate):
                    directory = os.path.dirname(candidate)
                    filename = os.path.basename(candidate)
                    return send_from_directory(directory, filename)
    except Exception as e:
        print(f"Asset-Fehler: {e}")

    abort(404)


if __name__ == '__main__':
    print(f"🚀 Projekt-Dashboard startet auf http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
