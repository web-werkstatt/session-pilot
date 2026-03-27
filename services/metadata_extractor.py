"""
Projekt-Metadaten-Extraktion: Version, Lizenz, Repo-Groesse, LOC, Changelog
"""
import os
import re
import json
import subprocess


def extract_version(project_path):
    """Extrahiert die Projektversion aus Package-Dateien"""
    # package.json
    pkg_path = os.path.join(project_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                v = pkg.get("version")
                if v and v != "0.0.0" and v != "1.0.0":
                    return v
                if v:
                    return v
        except (json.JSONDecodeError, OSError):
            pass

    # pyproject.toml
    pyproject_path = os.path.join(project_path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except OSError:
            pass

    # Cargo.toml
    cargo_path = os.path.join(project_path, "Cargo.toml")
    if os.path.exists(cargo_path):
        try:
            with open(cargo_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except OSError:
            pass

    # composer.json
    composer_path = os.path.join(project_path, "composer.json")
    if os.path.exists(composer_path):
        try:
            with open(composer_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                v = data.get("version")
                if v:
                    return v
        except (json.JSONDecodeError, OSError):
            pass

    return None


def detect_license(project_path):
    """Erkennt die Lizenz aus LICENSE-Datei oder Package-Dateien"""
    license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "LICENCE"]
    for lf in license_files:
        lpath = os.path.join(project_path, lf)
        if os.path.exists(lpath):
            try:
                with open(lpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)
                    patterns = [
                        (r'MIT License', "MIT"),
                        (r'Apache License.*2\.0', "Apache-2.0"),
                        (r'GNU GENERAL PUBLIC LICENSE.*Version 3', "GPL-3.0"),
                        (r'GNU GENERAL PUBLIC LICENSE.*Version 2', "GPL-2.0"),
                        (r'GNU LESSER GENERAL PUBLIC', "LGPL"),
                        (r'BSD\s+[23]-Clause', lambda m: m.group(0).replace(' ', '-')),
                        (r'ISC License', "ISC"),
                        (r'Mozilla Public License', "MPL-2.0"),
                        (r'The Unlicense', "Unlicense"),
                    ]
                    for pattern, result in patterns:
                        m = re.search(pattern, content, re.IGNORECASE)
                        if m:
                            return result if isinstance(result, str) else result(m)
            except OSError:
                pass

    # Fallback: package.json
    pkg_path = os.path.join(project_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                if pkg.get("license"):
                    return pkg["license"]
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: pyproject.toml
    pyproject_path = os.path.join(project_path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'license\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except OSError:
            pass

    return None


def get_repo_size(project_path):
    """Ermittelt die Projektgroesse (ohne node_modules, .git, venv)"""
    try:
        result = subprocess.run(
            ["du", "-sh", "--exclude=node_modules", "--exclude=.git",
             "--exclude=venv", "--exclude=.venv", "--exclude=__pycache__",
             "--exclude=dist", "--exclude=build", project_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            size = result.stdout.strip().split('\t')[0]
            return size
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def count_lines_of_code(project_path):
    """Zaehlt Codezeilen gruppiert nach Sprache"""
    extensions = {
        '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
        '.jsx': 'React JSX', '.tsx': 'React TSX', '.vue': 'Vue',
        '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS',
        '.php': 'PHP', '.go': 'Go', '.rs': 'Rust', '.java': 'Java',
        '.sh': 'Shell', '.sql': 'SQL',
    }
    exclude_dirs = {
        'node_modules', '.git', '__pycache__', 'venv', '.venv',
        'vendor', 'dist', 'build', '.next', '.nuxt', 'coverage',
        'logs', '.cache', '.turbo',
    }
    stats = {}
    total = 0
    try:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            rel = os.path.relpath(root, project_path)
            if rel.count(os.sep) > 5:
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in extensions:
                    continue
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                        lines = sum(1 for _ in fh)
                    lang = extensions[ext]
                    stats[lang] = stats.get(lang, 0) + lines
                    total += lines
                except OSError:
                    pass
    except OSError:
        pass
    if not stats:
        return None
    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
    sorted_stats['total'] = total
    return sorted_stats


def parse_changelog(project_path):
    """Parst CHANGELOG.md und gibt den letzten Eintrag zurueck"""
    for cl_name in ["CHANGELOG.md", "HISTORY.md", "CHANGES.md", "changelog.md"]:
        cl_path = os.path.join(project_path, cl_name)
        if os.path.exists(cl_path):
            try:
                with open(cl_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)
                match = re.search(
                    r'^##\s*\[?v?(\d+\.\d+(?:\.\d+)?)\]?(?:\s*[-–]\s*(\d{4}[-/]\d{2}[-/]\d{2}))?(.+?)(?=\n##\s|\Z)',
                    content, re.MULTILINE | re.DOTALL
                )
                if match:
                    summary = match.group(3).strip()
                    summary = re.sub(r'\n+', ' ', summary)[:200]
                    return {
                        "version": match.group(1),
                        "date": match.group(2),
                        "summary": summary
                    }
            except OSError:
                pass
    return None
