"""
Volltextsuche ueber alle Projekt-Dokumente
"""
import os
import subprocess
import re
from flask import Blueprint, jsonify, request

from config import PROJECTS_DIR
from services.path_resolver import resolve_project_path

search_bp = Blueprint('search', __name__)

# Dateitypen fuer Volltextsuche
SEARCHABLE_EXTENSIONS = (
    '*.md', '*.txt', '*.rst', '*.adoc',
    '*.py', '*.js', '*.ts', '*.jsx', '*.tsx',
    '*.html', '*.css', '*.scss',
    '*.json', '*.yml', '*.yaml', '*.toml',
    '*.sh', '*.sql', '*.vue', '*.php',
)

# Verzeichnisse die uebersprungen werden
SKIP_PATTERNS = [
    '--glob=!node_modules/', '--glob=!.git/', '--glob=!__pycache__/',
    '--glob=!.venv/', '--glob=!venv/', '--glob=!dist/', '--glob=!build/',
    '--glob=!.next/', '--glob=!.nuxt/', '--glob=!vendor/',
    '--glob=!*.min.js', '--glob=!*.min.css', '--glob=!package-lock.json',
    '--glob=!yarn.lock', '--glob=!pnpm-lock.yaml',
]


@search_bp.route('/api/search')
def fulltext_search():
    """Volltextsuche ueber alle Projekte oder ein bestimmtes Projekt"""
    query = request.args.get('q', '').strip()
    project = request.args.get('project', '')
    file_type = request.args.get('type', '')  # 'docs', 'code', 'config'
    limit = min(int(request.args.get('limit', 50)), 200)

    if not query or len(query) < 2:
        return jsonify({"error": "Suchbegriff muss mindestens 2 Zeichen haben"}), 400

    search_path = PROJECTS_DIR
    if project:
        resolved = resolve_project_path(project)
        if resolved:
            search_path = resolved
        else:
            return jsonify({"error": "Projekt nicht gefunden"}), 404

    # rg (ripgrep) oder grep nutzen
    use_rg = _has_command('rg')

    if use_rg:
        if not project:
            # Bei Suche ueber alle Projekte: einzeln durchsuchen fuer Performance
            results = _search_rg_all_projects(query, file_type, limit)
        else:
            results = _search_rg(query, search_path, file_type, limit)
    else:
        results = _search_grep(query, search_path, file_type, limit)

    return jsonify({
        "query": query,
        "project": project or "(alle)",
        "results": results,
        "total": len(results),
        "truncated": len(results) >= limit,
    })


def _has_command(cmd):
    """Prueft ob ein Kommando verfuegbar ist"""
    try:
        subprocess.run([cmd, '--version'], capture_output=True, timeout=3)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _search_rg_all_projects(query, file_type, limit):
    """Durchsucht alle Projekte einzeln (vermeidet .pnpm-store etc.)"""
    all_results = {}
    skip_dirs = {'.pnpm-store', 'lost+found', 'backups', '.cache', 'node_modules'}

    try:
        entries = sorted(os.listdir(PROJECTS_DIR))
    except OSError:
        return []

    for entry in entries:
        if entry.startswith('.') or entry in skip_dirs:
            continue
        entry_path = os.path.join(PROJECTS_DIR, entry)
        if not os.path.isdir(entry_path):
            continue

        results = _search_rg(query, entry_path, file_type, limit - len(all_results))
        for r in results:
            r['project'] = entry
            key = f"{entry}/{r['file']}"
            if key not in all_results:
                all_results[key] = r

        if len(all_results) >= limit:
            break

    return sorted(all_results.values(), key=lambda x: x['project'])[:limit]


def _search_rg(query, search_path, file_type, limit):
    """Suche mit ripgrep (schnell, vimgrep-Format)"""
    cmd = [
        'rg', '--vimgrep', '-i', '--max-count=3',
        '--max-filesize=500K', '--max-depth=5',
        '--glob=!node_modules/', '--glob=!.git/', '--glob=!__pycache__/',
        '--glob=!.venv/', '--glob=!venv/', '--glob=!dist/', '--glob=!build/',
        '--glob=!.pnpm-store/', '--glob=!lost+found/', '--glob=!backups/',
        '--glob=!*.min.js', '--glob=!*.min.css',
        '--glob=!package-lock.json', '--glob=!yarn.lock', '--glob=!pnpm-lock.yaml',
    ]

    if file_type == 'docs':
        cmd.extend(['-t', 'md', '-t', 'txt', '-t', 'rst'])
    elif file_type == 'code':
        cmd.extend(['-t', 'py', '-t', 'js', '-t', 'ts', '-t', 'php'])
    elif file_type == 'config':
        cmd.extend(['-t', 'json', '-t', 'yaml', '-t', 'toml'])
    else:
        cmd.extend(['-t', 'md', '-t', 'txt', '-t', 'py', '-t', 'js', '-t', 'ts',
                    '-t', 'html', '-t', 'css', '-t', 'json', '-t', 'yaml', '-t', 'php'])

    cmd.extend([query, search_path])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return []

    return _parse_search_output(result.stdout, r'^(.+?):(\d+):\d+:(.*)$', limit)


def _search_grep(query, search_path, file_type, limit):
    """Fallback-Suche mit grep"""
    include_args = []
    if file_type == 'docs':
        include_args = ['--include=*.md', '--include=*.txt', '--include=*.rst']
    elif file_type == 'code':
        include_args = ['--include=*.py', '--include=*.js', '--include=*.ts', '--include=*.php']
    elif file_type == 'config':
        include_args = ['--include=*.json', '--include=*.yml', '--include=*.yaml']
    else:
        for ext in SEARCHABLE_EXTENSIONS:
            include_args.append(f'--include={ext}')

    cmd = [
        'grep', '-r', '-i', '-n', '--max-count=3',
        '--exclude-dir=node_modules', '--exclude-dir=.git',
        '--exclude-dir=__pycache__', '--exclude-dir=.venv',
        '--exclude-dir=dist', '--exclude-dir=build',
    ]
    cmd.extend(include_args)
    cmd.extend([query, search_path])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return []

    return _parse_search_output(result.stdout, r'^(.+?):(\d+):(.*)$', limit)


def _parse_search_output(stdout, pattern, limit):
    """Parst grep/rg Output in strukturierte Ergebnisse"""
    matches_by_file = {}

    for line in stdout.split('\n'):
        if not line.strip():
            continue
        match = re.match(pattern, line)
        if not match:
            continue

        filepath = match.group(1)
        line_number = int(match.group(2))
        line_text = match.group(3).strip()

        rel_path = os.path.relpath(filepath, PROJECTS_DIR)
        parts = rel_path.split(os.sep, 1)
        project_name = parts[0] if parts else ''
        file_in_project = parts[1] if len(parts) > 1 else parts[0]

        if rel_path not in matches_by_file:
            matches_by_file[rel_path] = {
                'project': project_name,
                'file': file_in_project,
                'extension': os.path.splitext(filepath)[1].lower(),
                'matches': [],
            }

        if len(matches_by_file[rel_path]['matches']) < 3:
            matches_by_file[rel_path]['matches'].append({
                'line': line_number,
                'text': line_text[:300],
            })

        if len(matches_by_file) >= limit:
            break

    return sorted(matches_by_file.values(), key=lambda x: x['project'])
