"""
Dokumenten-System Routes: Lazy-Loading Baum, Viewer, Editor, Export
"""
import os
import json
import base64
import zipfile
import io
import mimetypes
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, send_from_directory

from config import PROJECTS_DIR

documents_bp = Blueprint('documents', __name__)

# Erlaubte Dateitypen
DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp'}
ALL_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS

# Verzeichnisse die uebersprungen werden
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
    '.next', '.nuxt', 'dist', 'build', '.cache', '.tox',
    'vendor', 'bower_components', '.idea', '.vscode',
}

# Max Dateigroesse fuer Inhalts-Anzeige (5 MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


def _resolve_project_path(name):
    """Loest Projektpfad auf inkl. Bindestrich/Underscore Fallback"""
    if '/' in name:
        parts = name.split('/', 1)
        for sub_dir in ['', 'apps/', 'packages/', 'services/', 'modules/']:
            p = os.path.join(PROJECTS_DIR, parts[0], sub_dir + parts[1])
            if os.path.isdir(p):
                return p
        return None
    p = os.path.join(PROJECTS_DIR, name)
    if os.path.isdir(p):
        return p
    alt = name.replace('-', '_') if '-' in name else name.replace('_', '-')
    p = os.path.join(PROJECTS_DIR, alt)
    return p if os.path.isdir(p) else None


def _human_size(size):
    """Konvertiert Bytes in lesbare Groesse"""
    for unit in ['B', 'KB', 'MB']:
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _list_directory(project_path, rel_dir):
    """Listet Dateien und Unterverzeichnisse eines einzelnen Verzeichnisses"""
    if rel_dir and rel_dir != '.':
        abs_dir = os.path.join(project_path, rel_dir)
    else:
        abs_dir = project_path
        rel_dir = '.'

    # Sicherheitscheck
    real_project = os.path.realpath(project_path)
    real_dir = os.path.realpath(abs_dir)
    if not real_dir.startswith(real_project):
        return None, None

    if not os.path.isdir(abs_dir):
        return None, None

    files = []
    subdirs = []

    try:
        entries = sorted(os.listdir(abs_dir))
    except PermissionError:
        return [], []

    for entry_name in entries:
        entry_path = os.path.join(abs_dir, entry_name)

        if os.path.isdir(entry_path):
            if entry_name in SKIP_DIRS or entry_name.startswith('.'):
                continue
            # Pruefen ob Unterverzeichnis relevante Dateien hat (schneller Check)
            subdirs.append({
                'name': entry_name,
                'path': entry_name if rel_dir == '.' else os.path.join(rel_dir, entry_name),
            })
        elif os.path.isfile(entry_path):
            ext = os.path.splitext(entry_name)[1].lower()
            if ext not in ALL_EXTENSIONS:
                continue
            try:
                stat = os.stat(entry_path)
                if stat.st_size > MAX_FILE_SIZE:
                    continue
                files.append({
                    'name': entry_name,
                    'path': entry_name if rel_dir == '.' else os.path.join(rel_dir, entry_name),
                    'type': 'document' if ext in DOC_EXTENSIONS else 'image',
                    'extension': ext,
                    'size': stat.st_size,
                    'size_human': _human_size(stat.st_size),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                })
            except OSError:
                continue

    return files, subdirs


@documents_bp.route('/api/project/<path:name>/documents')
def get_documents(name):
    """Lazy-Loading: Listet nur ein Verzeichnis (default: root)"""
    project_path = _resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    rel_dir = request.args.get('dir', '.')

    files, subdirs = _list_directory(project_path, rel_dir)
    if files is None:
        return jsonify({"error": "Verzeichnis nicht gefunden"}), 404

    return jsonify({
        'directory': rel_dir,
        'files': files,
        'subdirs': subdirs,
        'counts': {
            'files': len(files),
            'documents': sum(1 for f in files if f['type'] == 'document'),
            'images': sum(1 for f in files if f['type'] == 'image'),
            'subdirs': len(subdirs),
        },
    })


@documents_bp.route('/api/project/<path:name>/document/<path:doc_path>')
def get_document(name, doc_path):
    """Liest ein einzelnes Dokument"""
    project_path = _resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    filepath = os.path.join(project_path, doc_path)

    # Sicherheitscheck
    real_project = os.path.realpath(project_path)
    real_file = os.path.realpath(filepath)
    if not real_file.startswith(real_project):
        return jsonify({"error": "Zugriff verweigert"}), 403

    if not os.path.isfile(filepath):
        return jsonify({"error": "Datei nicht gefunden"}), 404

    ext = os.path.splitext(doc_path)[1].lower()

    if ext in DOC_EXTENSIONS:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()

        html = ""
        if ext == '.md':
            import markdown as md_lib
            html = md_lib.markdown(content, extensions=["fenced_code", "tables", "toc"])

        return jsonify({
            'content': content,
            'html': html,
            'type': 'document',
            'extension': ext,
            'path': doc_path,
        })

    elif ext in IMAGE_EXTENSIONS:
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            mime = mimetypes.guess_type(filepath)[0] or 'image/png'
            b64 = base64.b64encode(data).decode('utf-8')
            return jsonify({
                'data_url': f"data:{mime};base64,{b64}",
                'type': 'image',
                'extension': ext,
                'path': doc_path,
                'size': len(data),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Dateityp nicht unterstuetzt"}), 400


@documents_bp.route('/api/project/<path:name>/document/<path:doc_path>', methods=['PUT'])
def save_document(name, doc_path):
    """Speichert ein Dokument"""
    project_path = _resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    filepath = os.path.join(project_path, doc_path)

    real_project = os.path.realpath(project_path)
    real_file = os.path.realpath(filepath)
    if not real_file.startswith(real_project):
        return jsonify({"error": "Zugriff verweigert"}), 403

    ext = os.path.splitext(doc_path)[1].lower()
    if ext not in DOC_EXTENSIONS:
        return jsonify({"error": "Nur Textdateien koennen bearbeitet werden"}), 400

    data = request.get_json()
    content = data.get('content', '')

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True, "message": f"{doc_path} gespeichert"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@documents_bp.route('/api/project/<path:name>/document-image/<path:img_path>')
def serve_document_image(name, img_path):
    """Serviert ein Bild direkt (fuer img src)"""
    project_path = _resolve_project_path(name)
    if not project_path:
        return '', 404

    filepath = os.path.join(project_path, img_path)

    real_project = os.path.realpath(project_path)
    real_file = os.path.realpath(filepath)
    if not real_file.startswith(real_project):
        return '', 403

    if not os.path.isfile(filepath):
        return '', 404

    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return send_from_directory(directory, filename)


@documents_bp.route('/api/project/<path:name>/export-bundle', methods=['POST'])
def export_bundle(name):
    """Exportiert ausgewaehlte Dokumente als Bundle"""
    project_path = _resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    data = request.get_json()
    selected_files = data.get('files', [])
    export_format = data.get('format', 'zip')

    if not selected_files:
        return jsonify({"error": "Keine Dateien ausgewaehlt"}), 400

    # Max 500 Dateien pro Export
    selected_files = selected_files[:500]

    files_data = []
    real_project = os.path.realpath(project_path)
    for rel_path in selected_files:
        filepath = os.path.join(project_path, rel_path)
        real_file = os.path.realpath(filepath)
        if not real_file.startswith(real_project) or not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(rel_path)[1].lower()
        if ext in DOC_EXTENSIONS:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_data.append({'path': rel_path, 'type': 'document', 'content': content, 'ext': ext})
            except Exception:
                pass
        elif ext in IMAGE_EXTENSIONS:
            try:
                with open(filepath, 'rb') as f:
                    binary = f.read()
                files_data.append({'path': rel_path, 'type': 'image', 'binary': binary, 'ext': ext})
            except Exception:
                pass

    if export_format == 'zip':
        return _export_zip(name, files_data)
    elif export_format == 'html':
        return _export_html_bundle(name, files_data)
    elif export_format == 'markdown':
        return _export_markdown(name, files_data)
    elif export_format == 'json':
        return _export_json(name, files_data)

    return jsonify({"error": "Unbekanntes Format"}), 400


def _export_zip(name, files_data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files_data:
            if f['type'] == 'document':
                zf.writestr(f['path'], f['content'])
            else:
                zf.writestr(f['path'], f['binary'])
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename={name}-dokumente.zip'}
    )


def _export_html_bundle(name, files_data):
    import markdown as md_lib
    sections = []
    for f in files_data:
        if f['type'] == 'document':
            if f['ext'] == '.md':
                html = md_lib.markdown(f['content'], extensions=["fenced_code", "tables", "toc"])
            else:
                html = f'<pre>{f["content"]}</pre>'
            sections.append(f'<section><h2>{f["path"]}</h2>{html}</section>')
        else:
            mime = mimetypes.guess_type(f['path'])[0] or 'image/png'
            b64 = base64.b64encode(f['binary']).decode('utf-8')
            sections.append(
                f'<section><h2>{f["path"]}</h2>'
                f'<img src="data:{mime};base64,{b64}" style="max-width:100%;border-radius:8px"></section>'
            )

    html_doc = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>{name} - Dokumentation</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 20px; background: #fff; color: #333; line-height: 1.7; }}
h1 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; }}
h2 {{ color: #555; font-size: 16px; margin-top: 40px; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
section {{ margin-bottom: 30px; }}
pre {{ background: #f5f5f5; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
pre code {{ background: none; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f5f5; }}
img {{ max-width: 100%; }}
blockquote {{ border-left: 3px solid #4fc3f7; padding: 8px 16px; margin: 12px 0; color: #666; background: #f9f9f9; }}
@media print {{ body {{ max-width: none; }} }}
</style>
</head>
<body>
<h1>{name}</h1>
<p style="color:#888;font-size:13px">Exportiert am {datetime.now().strftime('%d.%m.%Y %H:%M')} &middot; {len(files_data)} Dateien</p>
{''.join(sections)}
</body>
</html>"""

    return Response(
        html_doc,
        mimetype='text/html',
        headers={'Content-Disposition': f'attachment; filename={name}-dokumentation.html'}
    )


def _export_markdown(name, files_data):
    parts = [f"# {name}\n\n"]
    for f in files_data:
        if f['type'] == 'document':
            parts.append(f"---\n\n## {f['path']}\n\n{f['content']}\n\n")
    return Response(
        ''.join(parts),
        mimetype='text/markdown',
        headers={'Content-Disposition': f'attachment; filename={name}-dokumentation.md'}
    )


def _export_json(name, files_data):
    result = {
        'project': name,
        'exported_at': datetime.now().isoformat(),
        'files': []
    }
    for f in files_data:
        entry = {'path': f['path'], 'type': f['type'], 'extension': f['ext']}
        if f['type'] == 'document':
            entry['content'] = f['content']
        else:
            mime = mimetypes.guess_type(f['path'])[0] or 'image/png'
            entry['data_url'] = f"data:{mime};base64,{base64.b64encode(f['binary']).decode('utf-8')}"
        result['files'].append(entry)

    return Response(
        json.dumps(result, indent=2, ensure_ascii=False),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={name}-dokumente.json'}
    )
