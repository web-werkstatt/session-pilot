"""
Project Scanner Service - Projekt-Erkennung und Analyse
"""
import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROJECTS_DIR

# Schema-Version für project.json - erhöhen wenn neue Felder hinzugefügt werden
SCHEMA_VERSION = 2  # v2: topic Feld hinzugefügt

# Aktuelle Pflichtfelder für project.json
SCHEMA_FIELDS = {
    "name": "",
    "description": "",
    "category": "",
    "topic": "",           # NEU in v2
    "tags": [],
    "group": None,
    "priority": None,
    "status": "active",
    "project_type": "project",
    "schema_version": SCHEMA_VERSION
}
from services.git_service import get_local_git_info
from services.docker_service import load_yaml_simple
from services.cache_service import load_cache, save_cache, is_cache_valid, get_cached_activity, set_cached_activity


def load_project_json(project_path):
    """Lädt project.json aus dem Projektverzeichnis"""
    for filename in ["project.json", ".project.json"]:
        json_path = os.path.join(project_path, filename)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Vercel/Netlify Config erkennen und ignorieren
                    if "projectId" in data or "orgId" in data:
                        return None
                    return data
            except:
                pass
    return None


def detect_project_type(project_path, project_name):
    """Erkennt den Projekttyp automatisch"""
    # Prüfe auf verschiedene Indikatoren
    has_git = os.path.isdir(os.path.join(project_path, ".git"))
    has_docker = any(os.path.exists(os.path.join(project_path, f))
                     for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"])
    has_package_json = os.path.exists(os.path.join(project_path, "package.json"))
    has_requirements = os.path.exists(os.path.join(project_path, "requirements.txt"))
    has_pyproject = os.path.exists(os.path.join(project_path, "pyproject.toml"))

    # Monorepo-Indikatoren
    has_apps_dir = os.path.isdir(os.path.join(project_path, "apps"))
    has_packages_dir = os.path.isdir(os.path.join(project_path, "packages"))
    has_workspaces = False
    if has_package_json:
        try:
            with open(os.path.join(project_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                has_workspaces = "workspaces" in pkg
        except:
            pass

    # Services-Ordner mit mehreren Sub-Projekten = Monorepo
    has_services_monorepo = False
    services_dir = os.path.join(project_path, "services")
    if os.path.isdir(services_dir):
        try:
            service_subdirs = [d for d in os.listdir(services_dir)
                              if os.path.isdir(os.path.join(services_dir, d)) and not d.startswith('.')]
            # Mindestens 3 Service-Ordner = Monorepo
            if len(service_subdirs) >= 3:
                has_services_monorepo = True
        except:
            pass

    # Root-Level Sub-Projekte erkennen (z.B. python_extractor neben services/)
    has_root_subprojects = False
    excluded_root_dirs = {
        '.git', '.github', '.vscode', '.idea', '.claude', '.playwright-mcp',
        'node_modules', '__pycache__', 'venv', '.venv', 'vendor', 'dist', 'build',
        'logs', 'tmp', 'cache', 'backups', '_archive', 'docs', 'static',
        'tests', 'migrations', 'scripts', 'data', 'config', 'templates',
        'shared', 'infrastructure', 'apps', 'packages', 'services', 'modules',
        'session-logs', 'sprints', 'problems', 'upload', 'domain-bestand',
    }
    try:
        root_items = os.listdir(project_path)
        root_subproject_count = 0
        for item in root_items:
            if item.startswith('.') or item.lower() in excluded_root_dirs:
                continue
            item_path = os.path.join(project_path, item)
            if os.path.isdir(item_path):
                # Prüfe ob es wie ein Sub-Projekt aussieht
                try:
                    sub_files = os.listdir(item_path)
                    is_subproject = any([
                        "requirements.txt" in sub_files,
                        "package.json" in sub_files,
                        "Dockerfile" in sub_files,
                        "docker-compose.yml" in sub_files,
                        os.path.isdir(os.path.join(item_path, "app")),
                        any(f.startswith("sprint") and f.endswith(".md") for f in sub_files),
                        "CLAUDE.md" in sub_files,
                    ])
                    if is_subproject:
                        root_subproject_count += 1
                except:
                    pass
        # Mindestens 1 Root-Level Sub-Projekt = Monorepo
        if root_subproject_count >= 1 and (has_services_monorepo or has_apps_dir or has_packages_dir):
            has_root_subprojects = True
    except:
        pass

    # Fork/Clone-Indikatoren
    has_license = os.path.exists(os.path.join(project_path, "LICENSE"))
    has_contributing = os.path.exists(os.path.join(project_path, "CONTRIBUTING.md"))
    has_github_workflows = os.path.isdir(os.path.join(project_path, ".github", "workflows"))

    # Dokumentations-Indikatoren
    source_extensions = [".py", ".js", ".ts", ".php", ".go", ".rs", ".java"]
    has_source_code = False
    try:
        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)
            if os.path.isfile(item_path):
                if any(item.endswith(ext) for ext in source_extensions):
                    has_source_code = True
                    break
            elif os.path.isdir(item_path) and item not in [".git", "node_modules", "__pycache__", ".venv"]:
                for subitem in os.listdir(item_path)[:20]:  # Limit für Performance
                    if any(subitem.endswith(ext) for ext in source_extensions):
                        has_source_code = True
                        break
    except:
        pass

    # Projekttyp bestimmen
    if has_apps_dir or has_packages_dir or has_workspaces or has_services_monorepo or has_root_subprojects:
        return "monorepo"

    if has_license and has_contributing and has_github_workflows:
        return "fork"

    if project_name.startswith("tool_"):
        return "tool"

    if not has_source_code and not has_docker:
        # Prüfe ob nur Dokumentation
        try:
            md_count = len([f for f in os.listdir(project_path) if f.endswith(".md")])
            total_files = len([f for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))])
            if total_files > 0 and md_count / total_files > 0.5:
                return "documentation"
        except PermissionError:
            pass
        return "archive"

    return "project"


def generate_subproject_json(subproject_path, subproject_name, parent_name, subproject_type):
    """Generiert project.json für ein Sub-Projekt"""
    json_path = os.path.join(subproject_path, "project.json")

    # Wenn bereits vorhanden, nur laden und zurückgeben
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass

    # Beschreibung extrahieren
    description = extract_description(subproject_path, subproject_name)

    # Tags erkennen
    tags = set()
    if os.path.exists(os.path.join(subproject_path, "package.json")):
        tags.add("nodejs")
        try:
            with open(os.path.join(subproject_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps:
                    tags.add("react")
                if "vue" in deps:
                    tags.add("vue")
                if "next" in deps:
                    tags.add("nextjs")
        except:
            pass
    if os.path.exists(os.path.join(subproject_path, "requirements.txt")):
        tags.add("python")
    if os.path.exists(os.path.join(subproject_path, "Dockerfile")):
        tags.add("docker")

    project_data = {
        "name": subproject_name,
        "description": description or f"Sub-Projekt von {parent_name}",
        "category": subproject_type,
        "topic": detect_topic(subproject_path, subproject_name, description),
        "tags": sorted(list(tags)),
        "group": None,
        "priority": None,
        "status": "active",
        "project_type": "subproject",
        "parent_project": parent_name,
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "auto_generated": True,
        "schema_version": SCHEMA_VERSION
    }

    # Speichern
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        return project_data
    except Exception as e:
        print(f"Fehler beim Erstellen von project.json für Sub-Projekt {subproject_name}: {e}")
        return project_data


def is_valid_subproject(item_path):
    """Prüft ob ein Ordner ein gültiges Sub-Projekt ist"""
    try:
        files = os.listdir(item_path)
    except PermissionError:
        return False

    # Prüfe auf bekannte Projekt-Indikatoren
    has_indicator = any([
        # Package Manager Dateien
        "package.json" in files,
        "requirements.txt" in files,
        "pyproject.toml" in files,
        "composer.json" in files,
        "Cargo.toml" in files,
        "go.mod" in files,
        "bun.lockb" in files,
        # Docker
        "Dockerfile" in files,
        "docker-compose.yml" in files,
        "docker-compose.yaml" in files,
        "compose.yml" in files,
        # Quellcode-Ordner
        os.path.isdir(os.path.join(item_path, "src")),
        os.path.isdir(os.path.join(item_path, "app")),
        os.path.isdir(os.path.join(item_path, "lib")),
        # Einstiegsdateien
        "index.js" in files,
        "index.ts" in files,
        "main.py" in files,
        "app.py" in files,
        "manage.py" in files,
        "server.js" in files,
        "server.ts" in files,
        "cli.py" in files,
        # Konfigurationsdateien
        "Makefile" in files,
        "tsconfig.json" in files,
        "vite.config.js" in files,
        "vite.config.ts" in files,
        "next.config.js" in files,
        "astro.config.mjs" in files,
        # Sprint-Pläne als starker Indikator
        any(f.startswith("sprint") and f.endswith(".md") for f in files),
        # CLAUDE.md als Projekt-Indikator
        "CLAUDE.md" in files,
    ])

    if has_indicator:
        return True

    # Fallback: Prüfe ob Ordner Code-Dateien enthält
    try:
        code_files = [f for f in files if f.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.php'))
                      and os.path.isfile(os.path.join(item_path, f))]
        return len(code_files) >= 2
    except:
        return False


def detect_subprojects(project_path, parent_name=None, auto_generate_json=True):
    """Erkennt Sub-Projekte in Monorepos und erstellt optional project.json"""
    subprojects = []

    # Ordner die NICHT als Sub-Projekte gelten
    excluded_dirs = {
        # Versteckte / System
        '.git', '.github', '.vscode', '.idea', '.claude', '.next', '.nuxt', '.svelte-kit',
        '.playwright-mcp', 'session-logs', 'test-results',
        # Dependencies / Build
        'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache',
        'venv', '.venv', 'env', 'vendor', 'dist', 'build', 'out', '.turbo',
        # Logs / Temp
        'logs', 'tmp', 'temp', 'cache', '.cache',
        'backups', 'backup', '_archive', 'archive',
        # Dokumentation / Assets
        'docs', 'documentation', 'static', 'assets', 'public',
        'uploads', 'upload', 'media', 'images', 'img', 'icons', 'fonts',
        # Tests
        'tests', 'test', 'spec', 'specs', '__tests__', 'e2e', 'cypress',
        # Datenbank / Daten
        'migrations', 'fixtures', 'seeds', 'prisma',
        'data', 'database', 'db',
        # Konfiguration
        'config', 'configs', 'configuration', 'settings',
        'scripts', 'bin', 'tools',
        # Code-Struktur-Ordner (KEINE eigenständigen Projekte!)
        'app', 'pages', 'routes', 'api',           # Next.js / Remix / App-Struktur
        'components', 'ui', 'widgets', 'features',  # React/Vue Komponenten
        'hooks', 'composables', 'stores', 'store',  # State/Hooks
        'types', 'interfaces', 'models', 'schemas', # TypeScript Types
        'utils', 'helpers', 'lib', 'libs', 'core',  # Utilities
        'styles', 'css', 'scss', 'sass',            # Styling
        'layouts', 'templates', 'views',            # Views/Layouts
        'contexts', 'providers', 'wrappers',        # React Contexts
        'actions', 'reducers', 'selectors',         # Redux
        'shared', 'common', 'constants',
        # Sonstiges
        'infrastructure', 'deploy', 'deployment',
        'output', 'projects', 'sprints', 'problems',
        'certs', 'ssl', 'secrets',
        # Spezifische Altes-Ordner
        'Altes', 'altes', 'old', 'legacy', 'deprecated',
    }

    # Bekannte Sub-Projekt-Ordner mit Typ-Mapping
    subproject_dirs = {
        "apps": "app",
        "packages": "package",
        "services": "service",
        "modules": "module",
        "libs": "library",
        "plugins": "plugin",
        "themes": "theme",
        "sites": "site"
    }

    def add_subproject(item_name, item_path, relative_path, sub_type):
        """Fügt ein Sub-Projekt zur Liste hinzu"""
        subproject_info = {
            "name": item_name,
            "path": relative_path,
            "full_path": item_path,
            "type": sub_type
        }

        # project.json für Sub-Projekt generieren
        if auto_generate_json and parent_name:
            sub_meta = generate_subproject_json(item_path, item_name, parent_name, sub_type)
            if sub_meta:
                subproject_info["description"] = sub_meta.get("description", "")
                subproject_info["tags"] = sub_meta.get("tags", [])
                subproject_info["group"] = sub_meta.get("group")
                subproject_info["priority"] = sub_meta.get("priority")

        subprojects.append(subproject_info)

    # 1. Durchsuche bekannte Sub-Projekt-Ordner (apps/, services/, etc.)
    for dir_name, sub_type in subproject_dirs.items():
        sub_dir = os.path.join(project_path, dir_name)
        if os.path.isdir(sub_dir):
            try:
                for item in os.listdir(sub_dir):
                    item_path = os.path.join(sub_dir, item)
                    if not os.path.isdir(item_path) or item.startswith('.'):
                        continue
                    if is_valid_subproject(item_path):
                        add_subproject(item, item_path, f"{dir_name}/{item}", sub_type)
            except PermissionError:
                pass

    # 2. Durchsuche Root-Level Ordner nach Sub-Projekten
    try:
        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)

            # Überspringe Nicht-Ordner und versteckte
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue

            # Überspringe bekannte Sub-Projekt-Ordner (schon verarbeitet)
            if item in subproject_dirs:
                continue

            # Überspringe ausgeschlossene Ordner
            if item.lower() in excluded_dirs:
                continue

            # Prüfe ob es ein gültiges Sub-Projekt ist
            if is_valid_subproject(item_path):
                # Bestimme Typ basierend auf Inhalt
                sub_type = "component"  # Default
                try:
                    files = os.listdir(item_path)
                    if "Dockerfile" in files or "docker-compose.yml" in files:
                        sub_type = "service"
                    elif "package.json" in files:
                        sub_type = "app"
                    elif "requirements.txt" in files or "pyproject.toml" in files:
                        sub_type = "module"
                    elif any(f.startswith("sprint") and f.endswith(".md") for f in files):
                        sub_type = "sprint-project"
                except:
                    pass

                add_subproject(item, item_path, item, sub_type)
    except PermissionError:
        pass

    return subprojects


def extract_description(project_path, project_name):
    """Extrahiert Beschreibung aus verschiedenen Quellen - verbesserte Version"""
    import re

    description = ""

    # 1. Versuche README.md (erweiterte Analyse)
    for readme_name in ["README.md", "readme.md", "Readme.md", "README.rst", "README.txt", "README"]:
        readme_path = os.path.join(project_path, readme_name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # Mehr Zeichen für bessere Analyse
                    lines = content.split('\n')

                    # Strategie 1: Suche nach Description/About Sektion
                    in_description_section = False
                    for i, line in enumerate(lines):
                        line_lower = line.lower().strip()
                        # Erkenne Beschreibungs-Sektionen
                        if re.match(r'^#{1,3}\s*(description|about|overview|introduction|was ist|über)', line_lower):
                            in_description_section = True
                            continue
                        # Neue Sektion beendet Description
                        if in_description_section and line.strip().startswith('#'):
                            break
                        # Sammle Text aus Description-Sektion
                        if in_description_section and line.strip() and not line.startswith('!') and not line.startswith('['):
                            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)  # Links entfernen
                            clean = re.sub(r'[*_`#>]', '', clean).strip()
                            if len(clean) > 15:
                                description = clean[:200]
                                break

                    # Strategie 2: Erste sinnvolle Zeile nach Titel
                    if not description:
                        skip_next = False
                        for line in lines:
                            line = line.strip()
                            # Überspringe Titel, Badges, leere Zeilen, HTML
                            if not line or line.startswith('#') or line.startswith('!') or line.startswith('<'):
                                continue
                            if line.startswith('[') and '](' in line:  # Badge/Link-Zeile
                                continue
                            if len(line) < 15:  # Zu kurz
                                continue
                            if line.startswith('```') or line.startswith('---'):
                                skip_next = not skip_next
                                continue
                            if skip_next:
                                continue
                            # Bereinige Markdown
                            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
                            clean = re.sub(r'[*_`>]', '', clean).strip()
                            if clean and len(clean) > 15:
                                description = clean[:200]
                                break
            except:
                pass
            if description:
                break

    # 2. Versuche package.json
    if not description:
        pkg_path = os.path.join(project_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                    if pkg.get("description") and len(pkg["description"]) > 5:
                        description = pkg["description"][:200]
            except:
                pass

    # 3. Versuche pyproject.toml
    if not description:
        pyproject_path = os.path.join(project_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                    if match and len(match.group(1)) > 5:
                        description = match.group(1)[:200]
            except:
                pass

    # 4. Versuche composer.json (PHP)
    if not description:
        composer_path = os.path.join(project_path, "composer.json")
        if os.path.exists(composer_path):
            try:
                with open(composer_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("description") and len(data["description"]) > 5:
                        description = data["description"][:200]
            except:
                pass

    # 5. Versuche Cargo.toml (Rust)
    if not description:
        cargo_path = os.path.join(project_path, "Cargo.toml")
        if os.path.exists(cargo_path):
            try:
                with open(cargo_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                    if match and len(match.group(1)) > 5:
                        description = match.group(1)[:200]
            except:
                pass

    # 6. Versuche setup.py (Python legacy)
    if not description:
        setup_path = os.path.join(project_path, "setup.py")
        if os.path.exists(setup_path):
            try:
                with open(setup_path, 'r', encoding='utf-8') as f:
                    content = f.read(3000)
                    match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                    if match and len(match.group(1)) > 5:
                        description = match.group(1)[:200]
            except:
                pass

    # 7. Versuche docker-compose.yml (Service-Labels)
    if not description:
        for compose_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]:
            compose_path = os.path.join(project_path, compose_name)
            if os.path.exists(compose_path):
                try:
                    with open(compose_path, 'r', encoding='utf-8') as f:
                        content = f.read(2000)
                        # Suche nach Kommentar am Anfang
                        first_lines = content.split('\n')[:10]
                        for line in first_lines:
                            if line.startswith('#') and len(line) > 10:
                                clean = line.lstrip('#').strip()
                                if len(clean) > 15 and not clean.startswith('!') and 'version' not in clean.lower():
                                    description = clean[:200]
                                    break
                except:
                    pass
                if description:
                    break

    # 8. Versuche Hauptdatei-Docstring (main.py, app.py, index.js, etc.)
    if not description:
        main_files = ["main.py", "app.py", "__init__.py", "index.js", "index.ts", "main.js", "main.ts", "src/main.py", "src/app.py", "src/index.js", "src/index.ts"]
        for main_file in main_files:
            main_path = os.path.join(project_path, main_file)
            if os.path.exists(main_path):
                try:
                    with open(main_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)
                        # Python Docstring
                        match = re.search(r'^["\']["\']["\'](.+?)["\']["\']["\']', content, re.DOTALL)
                        if match:
                            doc = match.group(1).strip().split('\n')[0].strip()
                            if len(doc) > 10:
                                description = doc[:200]
                                break
                        # JavaScript/TypeScript Kommentar
                        match = re.search(r'^/\*\*?\s*\n?\s*\*?\s*(.+?)(?:\n|\*/)', content)
                        if match:
                            doc = match.group(1).strip()
                            if len(doc) > 10:
                                description = doc[:200]
                                break
                        # Erste Kommentarzeile
                        for line in content.split('\n')[:15]:
                            if line.startswith('#') and not line.startswith('#!'):
                                clean = line.lstrip('#').strip()
                                if len(clean) > 15:
                                    description = clean[:200]
                                    break
                            elif line.strip().startswith('//'):
                                clean = line.strip().lstrip('/').strip()
                                if len(clean) > 15:
                                    description = clean[:200]
                                    break
                        if description:
                            break
                except:
                    pass

    # 9. Versuche Makefile (Erstes Target oder Kommentar)
    if not description:
        makefile_path = os.path.join(project_path, "Makefile")
        if os.path.exists(makefile_path):
            try:
                with open(makefile_path, 'r', encoding='utf-8') as f:
                    for line in f.read(1000).split('\n')[:10]:
                        if line.startswith('#') and len(line) > 10:
                            clean = line.lstrip('#').strip()
                            if len(clean) > 15:
                                description = clean[:200]
                                break
            except:
                pass

    # 10. Fallback: Intelligente Namenserkennung
    if not description:
        description = generate_description_from_name(project_path, project_name)

    return description


def generate_description_from_name(project_path, project_name):
    """Generiert eine Beschreibung basierend auf Projektname und Struktur"""
    import re

    # Präfixe entfernen und aufbereiten
    name = project_name
    prefixes = {"proj_": "Projekt", "tool_": "Tool", "app_": "Anwendung", "plugin_": "Plugin", "lib_": "Bibliothek"}

    project_type = ""
    for prefix, ptype in prefixes.items():
        if name.startswith(prefix):
            project_type = ptype
            name = name[len(prefix):]
            break

    # CamelCase und snake_case aufteilen
    name = re.sub(r'[-_]', ' ', name)
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    name = name.title()

    # Technologie-Erkennung für bessere Beschreibung
    techs = []
    if os.path.exists(os.path.join(project_path, "package.json")):
        try:
            with open(os.path.join(project_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps or "next" in deps:
                    techs.append("React")
                elif "vue" in deps or "nuxt" in deps:
                    techs.append("Vue")
                elif "svelte" in deps:
                    techs.append("Svelte")
                elif "express" in deps or "fastify" in deps:
                    techs.append("Node.js API")
        except:
            pass
    if os.path.exists(os.path.join(project_path, "requirements.txt")) or os.path.exists(os.path.join(project_path, "pyproject.toml")):
        if os.path.exists(os.path.join(project_path, "templates")):
            techs.append("Flask/Django")
        else:
            techs.append("Python")
    if os.path.exists(os.path.join(project_path, "Dockerfile")) or os.path.exists(os.path.join(project_path, "docker-compose.yml")):
        techs.append("Docker")

    # Beschreibung zusammenbauen
    if project_type:
        if techs:
            return f"{project_type}: {name} ({', '.join(techs[:2])})"
        return f"{project_type}: {name}"
    elif techs:
        return f"{name} - {', '.join(techs[:2])}"
    else:
        return name


def detect_topic(project_path, project_name, description=""):
    """Erkennt das Thema/Bereich eines Projekts automatisch"""
    name_lower = project_name.lower()
    desc_lower = description.lower()
    combined = f"{name_lower} {desc_lower}"

    # Topic-Keywords mapping
    topic_keywords = {
        "webseite": ["website", "webseite", "landing", "homepage", "blog", "cms", "wordpress", "wp-"],
        "api": ["api", "rest", "graphql", "endpoint", "backend", "service"],
        "tool": ["tool", "utility", "helper", "cli", "script", "automation"],
        "app": ["app", "application", "anwendung", "mobile", "desktop", "electron"],
        "dashboard": ["dashboard", "admin", "panel", "monitoring", "analytics"],
        "devops": ["docker", "kubernetes", "k8s", "deploy", "ci/cd", "pipeline", "infrastructure"],
        "ai": ["ai", "ml", "machine learning", "neural", "gpt", "llm", "claude", "openai"],
        "ecommerce": ["shop", "store", "ecommerce", "payment", "cart", "checkout"],
        "documentation": ["doc", "docs", "documentation", "wiki", "guide"],
        "library": ["lib", "library", "package", "module", "component", "vorlage", "template"],
        "plugin": ["plugin", "extension", "addon", "modul"],
        "scraper": ["scraper", "crawler", "spider", "bot", "automation"],
        "database": ["database", "db", "sql", "postgres", "mysql", "mongodb"],
    }

    # Prüfe Dateistruktur für zusätzliche Hinweise
    has_routes = any(os.path.exists(os.path.join(project_path, d))
                     for d in ["routes", "api", "endpoints"])
    has_templates = any(os.path.exists(os.path.join(project_path, d))
                        for d in ["templates", "views", "pages"])
    has_components = os.path.exists(os.path.join(project_path, "components"))

    # Erkenne Topic
    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in combined:
                return topic

    # Fallback basierend auf Struktur
    if has_routes and not has_templates:
        return "api"
    if has_templates or has_components:
        return "webseite"

    return "projekt"  # Default


def generate_project_json(project_path, project_name):
    """Generiert automatisch eine project.json für neue Projekte"""
    project_type = detect_project_type(project_path, project_name)
    subprojects = detect_subprojects(project_path, parent_name=project_name, auto_generate_json=True)

    # Beschreibung extrahieren
    description = extract_description(project_path, project_name)

    # Basis-Struktur
    project_data = {
        "name": project_name,
        "description": description,
        "category": "",
        "topic": "",
        "tags": [],
        "group": None,
        "priority": None,
        "status": "active",
        "project_type": project_type,
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "auto_generated": True
    }

    # Kategorie aus Projektname ableiten
    if project_name.startswith("proj_"):
        project_data["category"] = "project"
        if not description:
            clean_name = project_name[5:].replace("_", " ").title()
            project_data["description"] = clean_name
    elif project_name.startswith("tool_"):
        project_data["category"] = "tool"
        if not description:
            clean_name = project_name[5:].replace("_", " ").title()
            project_data["description"] = clean_name
    elif project_name.startswith("app_"):
        project_data["category"] = "application"
        if not description:
            clean_name = project_name[4:].replace("_", " ").title()
            project_data["description"] = clean_name
    elif project_name.startswith("plugin_"):
        project_data["category"] = "plugin"
        if not description:
            clean_name = project_name[7:].replace("_", " ").title()
            project_data["description"] = clean_name

    # Topic erkennen
    project_data["topic"] = detect_topic(project_path, project_name, description)

    # Tags aus erkannten Technologien (als Set für keine Duplikate)
    tags = set()
    if os.path.exists(os.path.join(project_path, "package.json")):
        tags.add("nodejs")
        # Framework-Erkennung aus package.json
        try:
            with open(os.path.join(project_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "react" in deps:
                    tags.add("react")
                if "vue" in deps:
                    tags.add("vue")
                if "next" in deps:
                    tags.add("nextjs")
                if "express" in deps:
                    tags.add("express")
                if "fastify" in deps:
                    tags.add("fastify")
        except:
            pass
    if os.path.exists(os.path.join(project_path, "requirements.txt")):
        tags.add("python")
    if os.path.exists(os.path.join(project_path, "pyproject.toml")):
        tags.add("python")
    if any(os.path.exists(os.path.join(project_path, f))
           for f in ["docker-compose.yml", "docker-compose.yaml", "Dockerfile"]):
        tags.add("docker")
    if os.path.exists(os.path.join(project_path, "Cargo.toml")):
        tags.add("rust")
    if os.path.exists(os.path.join(project_path, "go.mod")):
        tags.add("go")
    if any(os.path.exists(os.path.join(project_path, f))
           for f in ["composer.json", "wp-config.php"]):
        tags.add("php")

    project_data["tags"] = sorted(list(tags))

    # Sub-Projekte hinzufügen wenn vorhanden
    if subprojects:
        project_data["subprojects"] = subprojects
        project_data["project_type"] = "monorepo"

    # Speichern
    json_path = os.path.join(project_path, "project.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        return project_data
    except Exception as e:
        print(f"Fehler beim Erstellen von project.json für {project_name}: {e}")
        return None


def needs_schema_update(project_data):
    """Prüft ob project.json auf neue Schema-Version aktualisiert werden muss"""
    current_version = project_data.get("schema_version", 1)
    return current_version < SCHEMA_VERSION


def update_project_json(project_path, project_name, force_description=False):
    """Aktualisiert eine existierende project.json mit neuen Erkennungen

    Args:
        force_description: Wenn True, wird Beschreibung auch bei existierender überschrieben

    Automatische Schema-Migration:
        - Fügt fehlende Felder hinzu
        - Aktualisiert Schema-Version
        - Behält existierende Werte bei
    """
    json_path = os.path.join(project_path, "project.json")
    if not os.path.exists(json_path):
        return generate_project_json(project_path, project_name)

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
    except:
        return None

    modified = False

    # Schema-Migration: Fehlende Felder aus SCHEMA_FIELDS hinzufügen
    for field, default_value in SCHEMA_FIELDS.items():
        if field not in project_data:
            project_data[field] = default_value
            modified = True

    # Schema-Version aktualisieren
    if needs_schema_update(project_data):
        project_data["schema_version"] = SCHEMA_VERSION
        modified = True

    # Beschreibung aktualisieren wenn leer oder generisch
    current_desc = project_data.get("description", "")
    if force_description or not current_desc or "Beschreibung hinzufügen" in current_desc:
        new_desc = extract_description(project_path, project_name)
        if new_desc and new_desc != current_desc:
            project_data["description"] = new_desc
            modified = True

    # Topic aktualisieren wenn leer
    if not project_data.get("topic"):
        project_data["topic"] = detect_topic(
            project_path, project_name,
            project_data.get("description", "")
        )
        modified = True

    # Tags aktualisieren (merge mit existierenden, Duplikate entfernen)
    existing_tags = set(project_data.get("tags", []))
    new_tags = set()

    if os.path.exists(os.path.join(project_path, "package.json")):
        new_tags.add("nodejs")
    if os.path.exists(os.path.join(project_path, "requirements.txt")):
        new_tags.add("python")
    if os.path.exists(os.path.join(project_path, "pyproject.toml")):
        new_tags.add("python")
    if any(os.path.exists(os.path.join(project_path, f))
           for f in ["docker-compose.yml", "docker-compose.yaml", "Dockerfile"]):
        new_tags.add("docker")

    merged_tags = existing_tags | new_tags
    if merged_tags != existing_tags:
        project_data["tags"] = sorted(list(merged_tags))
        modified = True

    # Speichern wenn modifiziert
    if modified:
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
        except:
            pass

    return project_data


def is_valid_project(project_path, project_name):
    """Prüft ob es sich um ein gültiges Projekt handelt"""
    # Ausschluss-Kriterien
    if project_name in ["node_modules", "__pycache__", ".git", "venv", ".venv"]:
        return False

    # Prüfe ob Ordner leer oder nur versteckte Dateien
    try:
        visible_items = [f for f in os.listdir(project_path) if not f.startswith('.')]
        if len(visible_items) == 0:
            return False
    except:
        return False

    # Prüfe auf Mindest-Indikatoren für ein Projekt
    has_any_config = any(os.path.exists(os.path.join(project_path, f)) for f in [
        "package.json", "requirements.txt", "pyproject.toml", "Cargo.toml",
        "docker-compose.yml", "docker-compose.yaml", "compose.yml",
        "Makefile", "CMakeLists.txt", "pom.xml", "build.gradle"
    ])

    has_source = False
    for ext in [".py", ".js", ".ts", ".php", ".go", ".rs", ".java", ".vue", ".jsx", ".tsx"]:
        try:
            for item in os.listdir(project_path):
                if item.endswith(ext):
                    has_source = True
                    break
                item_path = os.path.join(project_path, item)
                if os.path.isdir(item_path) and item not in ["node_modules", ".git", "__pycache__"]:
                    for subitem in os.listdir(item_path)[:10]:
                        if subitem.endswith(ext):
                            has_source = True
                            break
        except:
            pass
        if has_source:
            break

    return has_any_config or has_source


def get_project_last_activity(project_path):
    """Ermittelt letzte Aktivität eines Projekts via Git und Dateiänderung"""
    result = {
        "last_commit": None,
        "last_commit_msg": "",
        "last_file_change": None,
        "git_status": "unbekannt"
    }

    # Git-Informationen holen
    try:
        git_log = subprocess.run(
            ["git", "-C", project_path, "log", "-1", "--format=%ci|%s"],
            capture_output=True, text=True, timeout=5
        )
        if git_log.returncode == 0 and git_log.stdout.strip():
            parts = git_log.stdout.strip().split('|', 1)
            if parts:
                result["last_commit"] = parts[0][:16]
                result["last_commit_msg"] = parts[1][:50] if len(parts) > 1 else ""

        git_status = subprocess.run(
            ["git", "-C", project_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if git_status.returncode == 0:
            if git_status.stdout.strip():
                result["git_status"] = "geändert"
            else:
                result["git_status"] = "sauber"
    except:
        pass

    # Letzte Dateiänderung
    try:
        find_result = subprocess.run(
            f'find "{project_path}" -maxdepth 4 -type f '
            r'\( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.php" '
            r'-o -name "*.html" -o -name "*.css" -o -name "*.vue" -o -name "*.jsx" '
            r'-o -name "*.tsx" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" '
            r'-o -name "*.sh" -o -name "*.sql" \) '
            r'! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/logs/*" '
            r'! -name "project.json" '
            r'-printf "%T@ %p\n" 2>/dev/null | sort -rn | head -1',
            shell=True, capture_output=True, text=True, timeout=15
        )
        if find_result.returncode == 0 and find_result.stdout.strip():
            parts = find_result.stdout.strip().split(' ', 1)
            if len(parts) == 2:
                timestamp = float(parts[0])
                result["last_file_change"] = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except:
        pass

    return result


def scan_projects(auto_generate=True):
    """Scannt alle Projekte mit Cache-Unterstützung für Aktivitätsdaten

    Args:
        auto_generate: Wenn True, wird project.json automatisch für neue Projekte erstellt
    """
    projects = {}
    cache = load_cache()
    cache_modified = False

    for item in os.listdir(PROJECTS_DIR):
        item_path = os.path.join(PROJECTS_DIR, item)
        if not os.path.isdir(item_path) or item.startswith('.'):
            continue

        # Eigenen Dashboard-Ordner überspringen
        if item == "project_dashboard":
            continue

        # Prüfe ob es ein gültiges Projekt ist
        if not is_valid_project(item_path, item):
            continue

        project = {
            "name": item,
            "function": "",
            "category": "",
            "topic": "",
            "group": None,
            "tags": [],
            "priority": None,
            "deadline": None,
            "progress": None,
            "milestones": [],
            "container_patterns": [],
            "has_docker": False,
            "port": None,
            "project_type": "project",
            "subprojects": []
        }

        # project.json laden oder automatisch generieren
        project_meta = load_project_json(item_path)

        if not project_meta and auto_generate:
            # Automatisch project.json erstellen für neue Projekte
            project_meta = generate_project_json(item_path, item)
        elif project_meta and auto_generate:
            # Schema-Migration: Aktualisiere wenn veraltet
            if needs_schema_update(project_meta):
                project_meta = update_project_json(item_path, item)

        if project_meta:
            project["function"] = project_meta.get("description", project_meta.get("function", ""))
            project["category"] = project_meta.get("category", "")
            project["topic"] = project_meta.get("topic", "")
            project["tags"] = project_meta.get("tags", [])
            # Gruppe dynamisch akzeptieren (nicht mehr hardcoded)
            grp = project_meta.get("group")
            if grp:
                project["group"] = grp
            prio = project_meta.get("priority")
            if prio in ["high", "medium", "low"]:
                project["priority"] = prio
            project["deadline"] = project_meta.get("deadline")
            project["progress"] = project_meta.get("progress")
            project["milestones"] = project_meta.get("milestones", [])
            project["container_patterns"] = project_meta.get("container_patterns", [])
            if project_meta.get("port"):
                project["port"] = project_meta.get("port")
            # Neue Felder - Projekttyp IMMER dynamisch erkennen (nicht aus JSON)
            # Das stellt sicher, dass Monorepos korrekt erkannt werden
            detected_type = detect_project_type(item_path, item)
            project["project_type"] = detected_type
            # Sub-Projekte werden später erkannt
            project["subprojects"] = []

        # docker-compose.yml prüfen
        for compose_file in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]:
            compose_path = os.path.join(item_path, compose_file)
            if os.path.exists(compose_path):
                project["has_docker"] = True
                services, container_names, ports = load_yaml_simple(compose_path)
                if container_names:
                    project["container_patterns"].extend(container_names)
                elif services:
                    project["container_patterns"].extend([f"{item}*{s}*" for s in services])
                if ports and not project["port"]:
                    project["port"] = ports[0]
                break

        # Git-Infos
        git_info = get_local_git_info(item_path)
        project["local_sha"] = git_info["local_sha"]
        project["has_gitea"] = git_info["has_remote"]
        project["gitea_repo"] = git_info["remote_name"]

        # Letzte Aktivität (mit Cache)
        if is_cache_valid(cache, item):
            cached_activity = get_cached_activity(cache, item)
            if cached_activity:
                project.update(cached_activity)
            else:
                activity = get_project_last_activity(item_path)
                project.update(activity)
                set_cached_activity(cache, item, activity)
                cache_modified = True
        else:
            activity = get_project_last_activity(item_path)
            project.update(activity)
            set_cached_activity(cache, item, activity)
            cache_modified = True

        projects[item] = project

        # Sub-Projekte auch als separate Einträge hinzufügen (für Suche)
        if project.get("project_type") == "monorepo" or project.get("subprojects"):
            detected_subprojects = detect_subprojects(item_path, parent_name=item, auto_generate_json=auto_generate)
            for sub in detected_subprojects:
                sub_path = sub.get("full_path")
                if not sub_path:
                    continue

                sub_name = f"{item}/{sub['name']}"
                sub_project = {
                    "name": sub_name,
                    "display_name": sub['name'],
                    "function": sub.get("description", f"Sub-Projekt: {sub['type']}"),
                    "category": sub.get("type", "subproject"),
                    "topic": "",
                    "group": sub.get("group"),
                    "tags": sub.get("tags", []),
                    "priority": sub.get("priority"),
                    "deadline": None,
                    "progress": None,
                    "milestones": [],
                    "container_patterns": [],
                    "has_docker": os.path.exists(os.path.join(sub_path, "Dockerfile")),
                    "port": None,
                    "project_type": "subproject",
                    "parent_project": item,
                    "subproject_path": sub.get("path"),
                    "subprojects": []
                }

                # Sub-Projekt project.json laden
                sub_meta = load_project_json(sub_path)
                if sub_meta:
                    sub_project["function"] = sub_meta.get("description", sub_project["function"])
                    sub_project["topic"] = sub_meta.get("topic", "")
                    sub_project["tags"] = sub_meta.get("tags", [])
                    if sub_meta.get("group"):
                        sub_project["group"] = sub_meta.get("group")
                    if sub_meta.get("priority"):
                        sub_project["priority"] = sub_meta.get("priority")

                projects[sub_name] = sub_project

    # Cache speichern wenn modifiziert
    if cache_modified:
        save_cache(cache)

    # Nach letzter Aktivität sortieren
    sorted_projects = dict(sorted(
        projects.items(),
        key=lambda x: x[1].get("last_file_change") or x[1].get("last_commit") or "0000",
        reverse=True
    ))

    return sorted_projects
