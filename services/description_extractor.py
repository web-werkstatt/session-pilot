"""
Beschreibungs-Extraktion, Topic-Erkennung und Dependency-Analyse
"""
import os
import re
import json


def extract_description(project_path, project_name):
    """Extrahiert Beschreibung aus verschiedenen Quellen"""
    description = ""

    # 1. README.md
    for readme_name in ["README.md", "readme.md", "Readme.md", "README.rst", "README.txt", "README"]:
        readme_path = os.path.join(project_path, readme_name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)
                    lines = content.split('\n')

                    # Strategie 1: Description/About Sektion
                    in_description_section = False
                    for line in lines:
                        line_lower = line.lower().strip()
                        if re.match(r'^#{1,3}\s*(description|about|overview|introduction|was ist|über)', line_lower):
                            in_description_section = True
                            continue
                        if in_description_section and line.strip().startswith('#'):
                            break
                        if in_description_section and line.strip() and not line.startswith('!') and not line.startswith('['):
                            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
                            clean = re.sub(r'[*_`#>]', '', clean).strip()
                            if len(clean) > 15:
                                description = clean[:200]
                                break

                    # Strategie 2: Erste sinnvolle Zeile nach Titel
                    if not description:
                        skip_next = False
                        for line in lines:
                            line = line.strip()
                            if not line or line.startswith('#') or line.startswith('!') or line.startswith('<'):
                                continue
                            if line.startswith('[') and '](' in line:
                                continue
                            if len(line) < 15:
                                continue
                            if line.startswith('```') or line.startswith('---'):
                                skip_next = not skip_next
                                continue
                            if skip_next:
                                continue
                            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
                            clean = re.sub(r'[*_`>]', '', clean).strip()
                            if clean and len(clean) > 15:
                                description = clean[:200]
                                break
            except OSError:
                pass
            if description:
                break

    # 2. package.json
    if not description:
        pkg_path = os.path.join(project_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                    if pkg.get("description") and len(pkg["description"]) > 5:
                        description = pkg["description"][:200]
            except (json.JSONDecodeError, OSError):
                pass

    # 3. pyproject.toml
    if not description:
        pyproject_path = os.path.join(project_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                    if match and len(match.group(1)) > 5:
                        description = match.group(1)[:200]
            except OSError:
                pass

    # 4. composer.json (PHP)
    if not description:
        composer_path = os.path.join(project_path, "composer.json")
        if os.path.exists(composer_path):
            try:
                with open(composer_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("description") and len(data["description"]) > 5:
                        description = data["description"][:200]
            except (json.JSONDecodeError, OSError):
                pass

    # 5. Cargo.toml (Rust)
    if not description:
        cargo_path = os.path.join(project_path, "Cargo.toml")
        if os.path.exists(cargo_path):
            try:
                with open(cargo_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                    if match and len(match.group(1)) > 5:
                        description = match.group(1)[:200]
            except OSError:
                pass

    # 6. setup.py
    if not description:
        setup_path = os.path.join(project_path, "setup.py")
        if os.path.exists(setup_path):
            try:
                with open(setup_path, 'r', encoding='utf-8') as f:
                    content = f.read(3000)
                    match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                    if match and len(match.group(1)) > 5:
                        description = match.group(1)[:200]
            except OSError:
                pass

    # 7. docker-compose.yml Kommentar
    if not description:
        for compose_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]:
            compose_path = os.path.join(project_path, compose_name)
            if os.path.exists(compose_path):
                try:
                    with open(compose_path, 'r', encoding='utf-8') as f:
                        for line in f.read(2000).split('\n')[:10]:
                            if line.startswith('#') and len(line) > 10:
                                clean = line.lstrip('#').strip()
                                if len(clean) > 15 and not clean.startswith('!') and 'version' not in clean.lower():
                                    description = clean[:200]
                                    break
                except OSError:
                    pass
                if description:
                    break

    # 8. Hauptdatei-Docstring
    if not description:
        main_files = [
            "main.py", "app.py", "__init__.py", "index.js", "index.ts",
            "main.js", "main.ts", "src/main.py", "src/app.py", "src/index.js", "src/index.ts"
        ]
        for main_file in main_files:
            main_path = os.path.join(project_path, main_file)
            if os.path.exists(main_path):
                try:
                    with open(main_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)
                        match = re.search(r'^["\']["\']["\'](.+?)["\']["\']["\']', content, re.DOTALL)
                        if match:
                            doc = match.group(1).strip().split('\n')[0].strip()
                            if len(doc) > 10:
                                description = doc[:200]
                                break
                        match = re.search(r'^/\*\*?\s*\n?\s*\*?\s*(.+?)(?:\n|\*/)', content)
                        if match:
                            doc = match.group(1).strip()
                            if len(doc) > 10:
                                description = doc[:200]
                                break
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
                except OSError:
                    pass

    # 9. Makefile
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
            except OSError:
                pass

    # 10. Fallback: Intelligente Namenserkennung
    if not description:
        description = _generate_description_from_name(project_path, project_name)

    return description


def _generate_description_from_name(project_path, project_name):
    """Generiert eine Beschreibung basierend auf Projektname und Struktur"""
    name = project_name
    prefixes = {"proj_": "Projekt", "tool_": "Tool", "app_": "Anwendung", "plugin_": "Plugin", "lib_": "Bibliothek"}

    project_type = ""
    for prefix, ptype in prefixes.items():
        if name.startswith(prefix):
            project_type = ptype
            name = name[len(prefix):]
            break

    name = re.sub(r'[-_]', ' ', name)
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    name = name.title()

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
        except (json.JSONDecodeError, OSError):
            pass
    if os.path.exists(os.path.join(project_path, "requirements.txt")) or \
       os.path.exists(os.path.join(project_path, "pyproject.toml")):
        if os.path.exists(os.path.join(project_path, "templates")):
            techs.append("Flask/Django")
        else:
            techs.append("Python")
    if os.path.exists(os.path.join(project_path, "Dockerfile")) or \
       os.path.exists(os.path.join(project_path, "docker-compose.yml")):
        techs.append("Docker")

    if project_type:
        return f"{project_type}: {name} ({', '.join(techs[:2])})" if techs else f"{project_type}: {name}"
    elif techs:
        return f"{name} - {', '.join(techs[:2])}"
    return name


def detect_topic(project_path, project_name, description=""):
    """Erkennt das Thema/Bereich eines Projekts automatisch"""
    combined = f"{project_name.lower()} {(description or '').lower()}"

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

    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in combined:
                return topic

    has_routes = any(os.path.exists(os.path.join(project_path, d)) for d in ["routes", "api", "endpoints"])
    has_templates = any(os.path.exists(os.path.join(project_path, d)) for d in ["templates", "views", "pages"])
    has_components = os.path.exists(os.path.join(project_path, "components"))

    if has_routes and not has_templates:
        return "api"
    if has_templates or has_components:
        return "webseite"
    return "projekt"


def extract_dependencies(project_path, all_project_names=None):
    """Extrahiert Abhängigkeiten aus verschiedenen Package-Dateien"""
    dependencies = {"internal": [], "external": [], "dev": [], "frameworks": []}
    all_projects = all_project_names or []
    all_projects_lower = [p.lower() for p in all_projects]

    # 1. package.json
    pkg_path = os.path.join(project_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                for dep in pkg.get("dependencies", {}).keys():
                    dep_lower = dep.lower().replace('@', '').replace('/', '-')
                    if any(dep_lower in p or p in dep_lower for p in all_projects_lower):
                        dependencies["internal"].append(dep)
                    else:
                        dependencies["external"].append(dep)
                    if dep in ["react", "vue", "angular", "svelte", "next", "nuxt", "astro"]:
                        dependencies["frameworks"].append(dep)
                for dep in pkg.get("devDependencies", {}).keys():
                    dependencies["dev"].append(dep)
                workspaces = pkg.get("workspaces", [])
                if isinstance(workspaces, dict):
                    workspaces = workspaces.get("packages", [])
                for ws in workspaces:
                    if isinstance(ws, str) and not ws.startswith("!"):
                        ws_name = ws.replace("packages/", "").replace("apps/", "").replace("/*", "")
                        if ws_name:
                            dependencies["internal"].append(f"workspace:{ws_name}")
        except (json.JSONDecodeError, OSError):
            pass

    # 2. requirements.txt
    req_path = os.path.join(project_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('-'):
                        continue
                    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if match:
                        dep = match.group(1)
                        dep_lower = dep.lower().replace('_', '-')
                        if any(dep_lower in p or p in dep_lower for p in all_projects_lower):
                            dependencies["internal"].append(dep)
                        else:
                            dependencies["external"].append(dep)
                        if dep.lower() in ["flask", "django", "fastapi", "tornado", "bottle", "pyramid"]:
                            dependencies["frameworks"].append(dep)
        except OSError:
            pass

    # 3. pyproject.toml
    pyproject_path = os.path.join(project_path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
                if deps_match:
                    for match in re.findall(r'["\']([a-zA-Z0-9_-]+)', deps_match.group(1)):
                        if match.lower() not in [d.lower() for d in dependencies["external"]]:
                            dependencies["external"].append(match)
        except OSError:
            pass

    # 4. composer.json
    composer_path = os.path.join(project_path, "composer.json")
    if os.path.exists(composer_path):
        try:
            with open(composer_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for dep in data.get("require", {}).keys():
                    if dep != "php" and not dep.startswith("ext-"):
                        dependencies["external"].append(dep)
                        if "laravel" in dep or "symfony" in dep:
                            dependencies["frameworks"].append(dep.split("/")[-1])
                for dep in data.get("require-dev", {}).keys():
                    dependencies["dev"].append(dep)
        except (json.JSONDecodeError, OSError):
            pass

    # 5. go.mod
    gomod_path = os.path.join(project_path, "go.mod")
    if os.path.exists(gomod_path):
        try:
            with open(gomod_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = re.match(r'^\t([^\s]+)', line)
                    if match:
                        dependencies["external"].append(match.group(1))
        except OSError:
            pass

    # Deduplizieren und sortieren
    dependencies["internal"] = sorted(set(dependencies["internal"]))
    dependencies["external"] = sorted(set(dependencies["external"]))[:50]
    dependencies["dev"] = sorted(set(dependencies["dev"]))[:30]
    dependencies["frameworks"] = sorted(set(dependencies["frameworks"]))

    return dependencies


def parse_env_example(project_path):
    """Liest .env.example und gibt die definierten Keys zurueck.
    Returns: [{"key": str, "comment": str, "has_default": bool}]
    """
    result = []
    for env_file in [".env.example", ".env.sample", ".env.template", "env.example"]:
        env_path = os.path.join(project_path, env_file)
        if os.path.exists(env_path):
            try:
                last_comment = ""
                with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            last_comment = ""
                            continue
                        if line.startswith('#'):
                            last_comment = line.lstrip('#').strip()
                            continue
                        if '=' in line:
                            key, _, value = line.partition('=')
                            key = key.strip()
                            value = value.strip()
                            if key and re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                                result.append({
                                    "key": key,
                                    "comment": last_comment,
                                    "has_default": bool(value and value not in ('""', "''", "your_value_here", "xxx", ""))
                                })
                            last_comment = ""
            except OSError:
                pass
            break
    return result
