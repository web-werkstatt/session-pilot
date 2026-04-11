"""
Projekt-bezogene Routes: Detail, Save, Search, Export, Assets
"""
import os
import json
import html as html_mod
from datetime import datetime
from flask import Blueprint, jsonify, request, send_from_directory, abort

from config import PROJECTS_DIR
from services.dashboard_settings_service import should_include_self_project
from services.path_resolver import resolve_project_path
from services.workflow_loop_service import build_workflow_loop_data
from services import scan_projects, update_project_json

project_bp = Blueprint('projects', __name__)


def _escape(text):
    """HTML-Escape fuer sichere Ausgabe"""
    return html_mod.escape(str(text)) if text else ""


@project_bp.route('/project/<path:name>')
def project_detail(name):
    from flask import render_template
    return render_template('project_detail.html', project_name=name, active_page='projects')


@project_bp.route('/api/project/<path:name>')
def get_project(name):
    """Lädt project.json für ein Projekt (inkl. Sub-Projekte)"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

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


@project_bp.route('/api/project/<path:name>/workflow-loop')
def get_project_workflow_loop(name):
    try:
        return jsonify(build_workflow_loop_data(name))
    except FileNotFoundError:
        return jsonify({"error": "Project not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route('/api/project/save', methods=['POST'])
def save_project():
    """Speichert project.json für ein Projekt (inkl. Sub-Projekte)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    project_name = data.get('name')
    if not project_name:
        return jsonify({"error": "Project name missing"}), 400

    project_path = resolve_project_path(project_name)
    if not project_path:
        return jsonify({"error": f"Project '{project_name}' not found"}), 404

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
        return jsonify({"success": True, "message": f"project.json for {project_name} saved"})
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
    include_self_project = should_include_self_project()

    for item in os.listdir(PROJECTS_DIR):
        item_path = os.path.join(PROJECTS_DIR, item)
        if not os.path.isdir(item_path) or item.startswith('.'):
            continue
        if item == "project_dashboard" and not include_self_project:
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
        return jsonify({"error": "Project not found"}), 404

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
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    content = data.get('content', '')
    filename = data.get('filename', 'README.md')

    if filename not in ["README.md", "readme.md", "Readme.md"]:
        filename = "README.md"

    filepath = os.path.join(project_path, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True, "message": f"{filename} saved", "path": filepath})
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
            md_parts.append(f"\n**Type:** {pj['project_type']}")
        return Response(
            "\n".join(md_parts),
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={name}.md"}
        )
    elif fmt == 'html':
        desc = _escape(pj.get("description", ""))
        export_html = f"""<!DOCTYPE html>
<html lang="en">
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
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} — Project Dashboard
</footer>
</body></html>"""
        return Response(
            export_html, mimetype="text/html",
            headers={"Content-Disposition": f"attachment; filename={name}.html"}
        )

    return jsonify({"error": f"Unknown format: {fmt}"}), 400


def _tool_profile_meta(project_path):
    """Baut die Metadaten fuer den DASHBOARD-GENERATED-Block."""
    from services.project_scanner import load_project_json
    pjson = load_project_json(project_path) or {}
    return {
        "type": pjson.get("project_type") or pjson.get("type"),
        "description": pjson.get("description"),
    }


def _tool_profile_serialize(result):
    """Konvertiert ToolUpdateResult in ein JSON-taugliches Dict."""
    return {
        "tool": result.tool,
        "filename": os.path.basename(result.filepath) if result.filepath else "",
        "mode": result.mode,
        "written": result.written,
        "diff": result.diff,
        "violations": list(result.violations),
        "error": result.error,
    }


@project_bp.route('/api/project/<path:name>/tool-profile/preview')
def preview_tool_profile(name):
    """Dry-Run: zeigt Diff pro Tool-Datei, schreibt nichts."""
    from services.tool_profile_adapter_service import regenerate_all
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    meta = _tool_profile_meta(project_path)
    results = regenerate_all(project_path, name, meta, dry_run=True)
    return jsonify({
        "project": name,
        "results": [_tool_profile_serialize(r) for r in results],
    })


@project_bp.route('/api/project/<path:name>/tool-profile/regenerate', methods=['POST'])
def regenerate_tool_profile(name):
    """Schreibt DASHBOARD-GENERATED-Bloecke in CLAUDE.md/AGENTS.md/GEMINI.md."""
    from services.tool_profile_adapter_service import regenerate_all
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    meta = _tool_profile_meta(project_path)
    results = regenerate_all(project_path, name, meta, dry_run=False)
    serialized = [_tool_profile_serialize(r) for r in results]
    all_ok = all(r["written"] or r["mode"] == "noop" for r in serialized)
    status = 200 if all_ok else 409
    return jsonify({
        "project": name,
        "results": serialized,
        "ok": all_ok,
    }), status


@project_bp.route('/api/project/<path:name>/archive', methods=['POST'])
def archive_project(name):
    """Archiviert oder stellt ein Projekt wieder her"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json() or {}
    archived = data.get('archived', True)

    json_path = os.path.join(project_path, "project.json")
    existing = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    existing["archived"] = bool(archived)
    existing.setdefault("name", name)

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        action = "archived" if archived else "restored"
        return jsonify({"success": True, "message": f"Project '{name}' {action}"})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


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
