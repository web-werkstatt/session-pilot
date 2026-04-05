"""
Project Scanner Service - Scannt Projekte und verwaltet project.json
"""
import os
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from config import PROJECTS_DIR
from services.git_service import get_local_git_info, get_activity_score
from services.docker_service import load_yaml_simple
from services.cache_service import load_cache, save_cache, is_cache_valid, get_cached_activity, set_cached_activity
from services.dashboard_settings_service import should_include_self_project
from services.project_detector import (
    SCHEMA_VERSION, SCHEMA_FIELDS,
    detect_project_type, detect_subprojects,
    detect_tags, is_valid_project, needs_schema_update,
)
from services.description_extractor import (
    extract_description, detect_topic, extract_dependencies,
)
from services.metadata_extractor import extract_version, detect_license


def load_project_json(project_path):
    """Lädt project.json aus dem Projektverzeichnis"""
    for filename in ["project.json", ".project.json"]:
        json_path = os.path.join(project_path, filename)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "projectId" in data or "orgId" in data:
                        return None
                    return data
            except (json.JSONDecodeError, OSError):
                pass
    return None


def generate_project_json(project_path, project_name):
    """Generiert automatisch eine project.json für neue Projekte"""
    project_type = detect_project_type(project_path, project_name)
    subprojects = detect_subprojects(project_path, parent_name=project_name, auto_generate_json=True)
    description = extract_description(project_path, project_name)

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
    prefix_map = {"proj_": "project", "tool_": "tool", "app_": "application", "plugin_": "plugin"}
    for prefix, category in prefix_map.items():
        if project_name.startswith(prefix):
            project_data["category"] = category
            if not description:
                project_data["description"] = project_name[len(prefix):].replace("_", " ").title()
            break

    project_data["topic"] = detect_topic(project_path, project_name, description)

    project_data["tags"] = detect_tags(project_path)

    if subprojects:
        project_data["subprojects"] = subprojects
        project_data["project_type"] = "monorepo"

    json_path = os.path.join(project_path, "project.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        return project_data
    except OSError as e:
        print(f"Fehler beim Erstellen von project.json für {project_name}: {e}")
        return None


def update_project_json(project_path, project_name, force_description=False):
    """Aktualisiert eine existierende project.json mit neuen Erkennungen"""
    json_path = os.path.join(project_path, "project.json")
    if not os.path.exists(json_path):
        return generate_project_json(project_path, project_name)

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    modified = False

    # Schema-Migration
    for field, default_value in SCHEMA_FIELDS.items():
        if field not in project_data:
            project_data[field] = default_value
            modified = True

    if needs_schema_update(project_data):
        project_data["schema_version"] = SCHEMA_VERSION
        modified = True

    # Beschreibung aktualisieren
    current_desc = project_data.get("description", "")
    if force_description or not current_desc or "Beschreibung hinzufügen" in current_desc:
        new_desc = extract_description(project_path, project_name)
        if new_desc and new_desc != current_desc:
            project_data["description"] = new_desc
            modified = True

    # Topic
    if not project_data.get("topic"):
        project_data["topic"] = detect_topic(project_path, project_name, project_data.get("description", ""))
        modified = True

    # Tags
    existing_tags = set(project_data.get("tags", []))
    new_tags = set(detect_tags(project_path))
    merged_tags = existing_tags | new_tags
    if merged_tags != existing_tags:
        project_data["tags"] = sorted(merged_tags)
        modified = True

    if modified:
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    return project_data


def get_project_last_activity(project_path):
    """Ermittelt letzte Aktivität eines Projekts via Git und Dateiänderung"""
    result = {"last_commit": None, "last_commit_msg": "", "last_file_change": None, "git_status": "unbekannt"}

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
            result["git_status"] = "geändert" if git_status.stdout.strip() else "sauber"
    except (OSError, subprocess.TimeoutExpired):
        pass

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
                result["last_file_change"] = datetime.fromtimestamp(float(parts[0])).strftime("%Y-%m-%d %H:%M")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass

    return result


def _scan_single_project(item, cache, auto_generate):
    """Scannt ein einzelnes Projekt. Thread-safe (kein shared mutable state)."""
    item_path = os.path.join(PROJECTS_DIR, item)
    cache_updated = False

    project = {
        "name": item, "function": "", "category": "", "topic": "",
        "group": None, "tags": [], "priority": None, "deadline": None,
        "progress": None, "milestones": [], "container_patterns": [],
        "has_docker": False, "port": None, "project_type": "project", "subprojects": []
    }

    # project.json laden oder generieren
    project_meta = load_project_json(item_path)
    if not project_meta and auto_generate:
        project_meta = generate_project_json(item_path, item)
    elif project_meta and auto_generate and needs_schema_update(project_meta):
        project_meta = update_project_json(item_path, item)

    if project_meta:
        project["function"] = project_meta.get("description", project_meta.get("function", ""))
        project["category"] = project_meta.get("category", "")
        project["topic"] = project_meta.get("topic", "")
        project["tags"] = project_meta.get("tags", [])
        if project_meta.get("group"):
            project["group"] = project_meta["group"]
        prio = project_meta.get("priority")
        if prio in ["high", "medium", "low"]:
            project["priority"] = prio
        project["deadline"] = project_meta.get("deadline")
        project["progress"] = project_meta.get("progress")
        project["milestones"] = project_meta.get("milestones", [])
        project["container_patterns"] = project_meta.get("container_patterns", [])
        project["archived"] = project_meta.get("archived", False)
        # AI-Policy fuer Dashboard-Badge (Default: Sandbox)
        ai_pol = project_meta.get("ai_policy", {})
        project["policy_level"] = ai_pol.get("level", 1)
        project["policy_level_name"] = ai_pol.get("level_name", "sandbox")
        if project_meta.get("port"):
            project["port"] = project_meta["port"]
        project["project_type"] = detect_project_type(item_path, item)
        project["subprojects"] = []

    # docker-compose.yml
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

    # Neue Metadaten: Version, Lizenz (schnell, Datei-basiert)
    project["version"] = extract_version(item_path)
    project["license"] = detect_license(item_path)

    # Git-Infos
    git_info = get_local_git_info(item_path)
    project["local_sha"] = git_info["local_sha"]
    project["has_gitea"] = git_info["has_remote"]
    project["gitea_repo"] = git_info["remote_name"]

    # Aktivitaets-Score
    if git_info["local_sha"]:
        project["activity_score"] = get_activity_score(item_path)
    else:
        project["activity_score"] = {"commits_7d": 0, "commits_30d": 0, "score": 0, "level": "inactive"}

    # Branch-Count (schnell, ohne Details)
    try:
        r = subprocess.run(
            ["git", "-C", item_path, "branch", "--list"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0:
            branches = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
            project["branch_count"] = len(branches)
        else:
            project["branch_count"] = 0
    except (OSError, subprocess.TimeoutExpired):
        project["branch_count"] = 0

    # GitHub/Health nur in Projekt-Detail (/api/info/slow), nicht im Dashboard-Scan
    project["github"] = None
    project["health"] = None

    # Letzte Aktivität (mit Cache)
    if is_cache_valid(cache, item):
        cached_activity = get_cached_activity(cache, item)
        if cached_activity:
            project.update(cached_activity)
        else:
            activity = get_project_last_activity(item_path)
            project.update(activity)
            cache_updated = True
    else:
        activity = get_project_last_activity(item_path)
        project.update(activity)
        cache_updated = True

    # Sub-Projekte
    sub_projects = {}
    if project.get("project_type") == "monorepo" or project.get("subprojects"):
        detected_subprojects = detect_subprojects(item_path, parent_name=item, auto_generate_json=auto_generate)
        for sub in detected_subprojects:
            sub_path = sub.get("full_path")
            if not sub_path:
                continue
            sub_name = f"{item}/{sub['name']}"
            sub_project = {
                "name": sub_name, "display_name": sub['name'],
                "function": sub.get("description", f"Sub-Projekt: {sub['type']}"),
                "category": sub.get("type", "subproject"), "topic": "",
                "group": sub.get("group"), "tags": sub.get("tags", []),
                "priority": sub.get("priority"), "deadline": None,
                "progress": None, "milestones": [], "container_patterns": [],
                "has_docker": os.path.exists(os.path.join(sub_path, "Dockerfile")),
                "port": None, "project_type": "subproject",
                "parent_project": item, "subproject_path": sub.get("path"),
                "subprojects": []
            }
            sub_meta = load_project_json(sub_path)
            if sub_meta:
                sub_project["function"] = sub_meta.get("description", sub_project["function"])
                sub_project["topic"] = sub_meta.get("topic", "")
                sub_project["tags"] = sub_meta.get("tags", [])
                if sub_meta.get("group"):
                    sub_project["group"] = sub_meta["group"]
                if sub_meta.get("priority"):
                    sub_project["priority"] = sub_meta["priority"]
            # Sub-Projekte erben Policy-Level vom Elternprojekt
            sub_project["policy_level"] = project.get("policy_level", 1)
            sub_project["policy_level_name"] = project.get("policy_level_name", "sandbox")
            sub_projects[sub_name] = sub_project

    return item, project, sub_projects, cache_updated


def scan_projects(auto_generate=True):
    """Scannt alle Projekte parallel mit ThreadPoolExecutor"""
    projects = {}
    cache = load_cache()
    cache_modified = False
    include_self_project = should_include_self_project()

    # Projektliste sammeln
    items = []
    for item in os.listdir(PROJECTS_DIR):
        item_path = os.path.join(PROJECTS_DIR, item)
        if not os.path.isdir(item_path) or item.startswith('.'):
            continue
        if item == "project_dashboard" and not include_self_project:
            continue
        if not is_valid_project(item_path, item):
            continue
        items.append(item)

    # Parallel scannen (max 8 Threads fuer Git/IO)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_scan_single_project, item, cache, auto_generate): item
            for item in items
        }
        for future in as_completed(futures):
            try:
                item, project, sub_projects, updated = future.result()
                projects[item] = project
                projects.update(sub_projects)
                if updated:
                    set_cached_activity(cache, item, {
                        k: project.get(k) for k in
                        ["last_commit", "last_commit_msg", "last_file_change", "git_status"]
                    })
                    cache_modified = True
            except Exception:
                pass

    if cache_modified:
        save_cache(cache)

    # Dependencies (zweiter Durchlauf)
    all_project_names = list(projects.keys())
    for proj_name, proj_data in projects.items():
        if proj_data.get("parent_project"):
            proj_path = os.path.join(PROJECTS_DIR, proj_data["parent_project"], proj_data.get("subproject_path", ""))
        else:
            proj_path = os.path.join(PROJECTS_DIR, proj_name)
        if os.path.isdir(proj_path):
            proj_data["dependencies"] = extract_dependencies(proj_path, all_project_names)

    # Port-Konflikt-Check
    port_map = {}
    for proj_name, proj_data in projects.items():
        port = proj_data.get("port")
        if port:
            port_str = str(port)
            if port_str not in port_map:
                port_map[port_str] = []
            port_map[port_str].append(proj_name)
    for port_str, proj_names in port_map.items():
        if len(proj_names) > 1:
            for pn in proj_names:
                projects[pn]["port_conflict"] = [p for p in proj_names if p != pn]

    return dict(sorted(
        projects.items(),
        key=lambda x: x[1].get("last_file_change") or x[1].get("last_commit") or "0000",
        reverse=True
    ))
