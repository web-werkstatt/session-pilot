"""
Projekt-Typ-Erkennung, Sub-Projekt-Erkennung und Validierung
"""
import os
import json
from datetime import datetime

from services.description_extractor import extract_description, detect_topic

# Schema-Version für project.json
SCHEMA_VERSION = 3

# Aktuelle Pflichtfelder für project.json
SCHEMA_FIELDS = {
    "name": "",
    "description": "",
    "category": "",
    "topic": "",
    "tags": [],
    "group": None,
    "priority": None,
    "status": "active",
    "project_type": "project",
    "version": None,
    "license": None,
    "schema_version": SCHEMA_VERSION
}

# Ordner die NICHT als Sub-Projekte gelten
EXCLUDED_SUBPROJECT_DIRS = {
    '.git', '.github', '.vscode', '.idea', '.claude', '.next', '.nuxt', '.svelte-kit',
    '.playwright-mcp', 'session-logs', 'test-results',
    'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache',
    'venv', '.venv', 'env', 'vendor', 'dist', 'build', 'out', '.turbo',
    'logs', 'tmp', 'temp', 'cache', '.cache',
    'backups', 'backup', '_archive', 'archive',
    'docs', 'documentation', 'static', 'assets', 'public',
    'uploads', 'upload', 'media', 'images', 'img', 'icons', 'fonts',
    'tests', 'test', 'spec', 'specs', '__tests__', 'e2e', 'cypress',
    'migrations', 'fixtures', 'seeds', 'prisma', 'data', 'database', 'db',
    'config', 'configs', 'configuration', 'settings', 'scripts', 'bin', 'tools',
    'app', 'pages', 'routes', 'api',
    'components', 'ui', 'widgets', 'features',
    'hooks', 'composables', 'stores', 'store',
    'types', 'interfaces', 'models', 'schemas',
    'utils', 'helpers', 'lib', 'libs', 'core',
    'styles', 'css', 'scss', 'sass',
    'layouts', 'templates', 'views',
    'contexts', 'providers', 'wrappers',
    'actions', 'reducers', 'selectors',
    'shared', 'common', 'constants',
    'infrastructure', 'deploy', 'deployment',
    'output', 'projects', 'sprints', 'problems',
    'certs', 'ssl', 'secrets',
    'Altes', 'altes', 'old', 'legacy', 'deprecated',
}

# Bekannte Sub-Projekt-Ordner mit Typ-Mapping
SUBPROJECT_DIRS = {
    "apps": "app", "packages": "package", "services": "service",
    "modules": "module", "libs": "library", "plugins": "plugin",
    "themes": "theme", "sites": "site",
}


def detect_project_type(project_path, project_name):
    """Erkennt den Projekttyp automatisch"""
    has_docker = any(os.path.exists(os.path.join(project_path, f))
                     for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"])
    has_package_json = os.path.exists(os.path.join(project_path, "package.json"))

    # Monorepo-Indikatoren
    has_apps_dir = os.path.isdir(os.path.join(project_path, "apps"))
    has_packages_dir = os.path.isdir(os.path.join(project_path, "packages"))
    has_workspaces = False
    if has_package_json:
        try:
            with open(os.path.join(project_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                has_workspaces = "workspaces" in pkg
        except (json.JSONDecodeError, OSError):
            pass

    has_services_monorepo = False
    services_dir = os.path.join(project_path, "services")
    if os.path.isdir(services_dir):
        try:
            service_subdirs = [d for d in os.listdir(services_dir)
                               if os.path.isdir(os.path.join(services_dir, d)) and not d.startswith('.')]
            if len(service_subdirs) >= 3:
                has_services_monorepo = True
        except OSError:
            pass

    # Root-Level Sub-Projekte
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
        root_subproject_count = 0
        for item in os.listdir(project_path):
            if item.startswith('.') or item.lower() in excluded_root_dirs:
                continue
            item_path = os.path.join(project_path, item)
            if os.path.isdir(item_path):
                try:
                    sub_files = os.listdir(item_path)
                    is_subproject = any([
                        "requirements.txt" in sub_files, "package.json" in sub_files,
                        "Dockerfile" in sub_files, "docker-compose.yml" in sub_files,
                        os.path.isdir(os.path.join(item_path, "app")),
                        any(f.startswith("sprint") and f.endswith(".md") for f in sub_files),
                        "CLAUDE.md" in sub_files,
                    ])
                    if is_subproject:
                        root_subproject_count += 1
                except OSError:
                    pass
        if root_subproject_count >= 1 and (has_services_monorepo or has_apps_dir or has_packages_dir):
            has_root_subprojects = True
    except OSError:
        pass

    # Fork/Clone-Indikatoren
    has_license = os.path.exists(os.path.join(project_path, "LICENSE"))
    has_contributing = os.path.exists(os.path.join(project_path, "CONTRIBUTING.md"))
    has_github_workflows = os.path.isdir(os.path.join(project_path, ".github", "workflows"))

    # Quellcode-Check
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
                for subitem in os.listdir(item_path)[:20]:
                    if any(subitem.endswith(ext) for ext in source_extensions):
                        has_source_code = True
                        break
    except OSError:
        pass

    # Projekttyp bestimmen
    if has_apps_dir or has_packages_dir or has_workspaces or has_services_monorepo or has_root_subprojects:
        return "monorepo"
    if has_license and has_contributing and has_github_workflows:
        return "fork"
    if project_name.startswith("tool_"):
        return "tool"
    if not has_source_code and not has_docker:
        try:
            md_count = len([f for f in os.listdir(project_path) if f.endswith(".md")])
            total_files = len([f for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))])
            if total_files > 0 and md_count / total_files > 0.5:
                return "documentation"
        except PermissionError:
            pass
        return "archive"
    return "project"


def is_valid_subproject(item_path):
    """Prüft ob ein Ordner ein gültiges Sub-Projekt ist"""
    try:
        files = os.listdir(item_path)
    except PermissionError:
        return False

    has_indicator = any([
        "package.json" in files, "requirements.txt" in files,
        "pyproject.toml" in files, "composer.json" in files,
        "Cargo.toml" in files, "go.mod" in files, "bun.lockb" in files,
        "Dockerfile" in files, "docker-compose.yml" in files,
        "docker-compose.yaml" in files, "compose.yml" in files,
        os.path.isdir(os.path.join(item_path, "src")),
        os.path.isdir(os.path.join(item_path, "app")),
        os.path.isdir(os.path.join(item_path, "lib")),
        "index.js" in files, "index.ts" in files,
        "main.py" in files, "app.py" in files, "manage.py" in files,
        "server.js" in files, "server.ts" in files, "cli.py" in files,
        "Makefile" in files, "tsconfig.json" in files,
        "vite.config.js" in files, "vite.config.ts" in files,
        "next.config.js" in files, "astro.config.mjs" in files,
        any(f.startswith("sprint") and f.endswith(".md") for f in files),
        "CLAUDE.md" in files,
    ])
    if has_indicator:
        return True

    try:
        code_files = [f for f in files if f.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.php'))
                      and os.path.isfile(os.path.join(item_path, f))]
        return len(code_files) >= 2
    except OSError:
        return False


def is_valid_project(project_path, project_name):
    """Prüft ob es sich um ein gültiges Projekt handelt"""
    if project_name in ["node_modules", "__pycache__", ".git", "venv", ".venv"]:
        return False
    try:
        visible_items = [f for f in os.listdir(project_path) if not f.startswith('.')]
        if len(visible_items) == 0:
            return False
    except OSError:
        return False

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
        except OSError:
            pass
        if has_source:
            break

    return has_any_config or has_source


def generate_subproject_json(subproject_path, subproject_name, parent_name, subproject_type):
    """Generiert project.json für ein Sub-Projekt"""
    json_path = os.path.join(subproject_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    description = extract_description(subproject_path, subproject_name)
    tags = set()
    if os.path.exists(os.path.join(subproject_path, "package.json")):
        tags.add("nodejs")
        try:
            with open(os.path.join(subproject_path, "package.json"), 'r') as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                for lib, tag in [("react", "react"), ("vue", "vue"), ("next", "nextjs")]:
                    if lib in deps:
                        tags.add(tag)
        except (json.JSONDecodeError, OSError):
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
        "group": None, "priority": None, "status": "active",
        "project_type": "subproject", "parent_project": parent_name,
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "auto_generated": True, "schema_version": SCHEMA_VERSION
    }
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"Fehler beim Erstellen von project.json für Sub-Projekt {subproject_name}: {e}")
    return project_data


def detect_subprojects(project_path, parent_name=None, auto_generate_json=True):
    """Erkennt Sub-Projekte in Monorepos und erstellt optional project.json"""
    subprojects = []

    def add_subproject(item_name, item_path, relative_path, sub_type):
        subproject_info = {
            "name": item_name, "path": relative_path,
            "full_path": item_path, "type": sub_type
        }
        if auto_generate_json and parent_name:
            sub_meta = generate_subproject_json(item_path, item_name, parent_name, sub_type)
            if sub_meta:
                subproject_info["description"] = sub_meta.get("description", "")
                subproject_info["tags"] = sub_meta.get("tags", [])
                subproject_info["group"] = sub_meta.get("group")
                subproject_info["priority"] = sub_meta.get("priority")
        subprojects.append(subproject_info)

    # 1. Bekannte Sub-Projekt-Ordner (apps/, services/, etc.)
    for dir_name, sub_type in SUBPROJECT_DIRS.items():
        sub_dir = os.path.join(project_path, dir_name)
        if os.path.isdir(sub_dir):
            try:
                for item in os.listdir(sub_dir):
                    item_path = os.path.join(sub_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('.') and is_valid_subproject(item_path):
                        add_subproject(item, item_path, f"{dir_name}/{item}", sub_type)
            except PermissionError:
                pass

    # 2. Root-Level Ordner
    try:
        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue
            if item in SUBPROJECT_DIRS or item.lower() in EXCLUDED_SUBPROJECT_DIRS:
                continue
            if is_valid_subproject(item_path):
                sub_type = "component"
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
                except OSError:
                    pass
                add_subproject(item, item_path, item, sub_type)
    except PermissionError:
        pass

    return subprojects


def needs_schema_update(project_data):
    """Prüft ob project.json auf neue Schema-Version aktualisiert werden muss"""
    return project_data.get("schema_version", 1) < SCHEMA_VERSION
