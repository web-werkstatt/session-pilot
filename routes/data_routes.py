"""
Daten-Aggregation Routes: /api/data, /api/containers
"""
from datetime import datetime
from flask import Blueprint, jsonify

from services import (
    scan_projects, get_docker_containers,
    load_cache, save_cache,
    get_gitea_repos, get_gitea_repo_commits,
)

data_bp = Blueprint('data', __name__)


def _container_stats(containers):
    """Berechnet Container-Statistiken"""
    running = sum(1 for c in containers if "Running" in c.get("status", "") or "Healthy" in c.get("status", ""))
    stopped = sum(1 for c in containers if "Stopped" in c.get("status", ""))
    unhealthy = sum(1 for c in containers if "Unhealthy" in c.get("status", ""))
    return {"total": len(containers), "running": running, "stopped": stopped, "unhealthy": unhealthy}


@data_bp.route('/api/data')
def get_data():
    projects = scan_projects()
    containers = get_docker_containers()
    gitea_repos = get_gitea_repos()
    gitea_commits = get_gitea_repo_commits()

    for proj_name, proj_info in projects.items():
        if proj_info.get("has_gitea") and proj_info.get("gitea_repo"):
            repo_name = proj_info["gitea_repo"]
            if repo_name in gitea_commits:
                remote_sha = gitea_commits[repo_name]["sha"]
                local_sha = proj_info.get("local_sha", "")
                if local_sha and remote_sha:
                    proj_info["sync_status"] = "synced" if local_sha == remote_sha else "differs"
                    proj_info["remote_sha"] = remote_sha
                else:
                    proj_info["sync_status"] = "unknown"
            else:
                proj_info["sync_status"] = "not_on_gitea"
        else:
            proj_info["sync_status"] = "no_remote"

    cache = load_cache()
    cached_projects = set(cache.get("projects", {}).keys())
    current_projects = set(projects.keys())
    new_projects = list(current_projects - cached_projects)

    for proj_name in new_projects:
        if proj_name not in cache.get("projects", {}):
            if "projects" not in cache:
                cache["projects"] = {}
            cache["projects"][proj_name] = {"name": proj_name}
    cache["last_update"] = datetime.now().isoformat()
    save_cache(cache)

    # Commit-Detection fuer Notifications
    try:
        from services.notification_service import load_state, save_state, add_notification
        state = load_state()
        prev_commits = state.get("last_commits", {})
        for proj_name, proj_info in projects.items():
            sha = proj_info.get("local_sha", "")
            if sha and prev_commits.get(proj_name) and prev_commits[proj_name] != sha:
                add_notification(
                    "new_commit", "info",
                    f"Neuer Commit: {proj_name}",
                    proj_info.get("last_commit_msg", "")[:80],
                    project=proj_name
                )
            if sha:
                prev_commits[proj_name] = sha
        state["last_commits"] = prev_commits
        save_state(state)
    except Exception:
        pass  # Notifications duerfen /api/data nicht blockieren

    stats = _container_stats(containers)
    stats["total_projects"] = len(projects)
    stats["total_containers"] = stats.pop("total")
    stats["gitea_repos"] = len(gitea_repos)

    return jsonify({
        "projects": list(projects.values()),
        "containers": containers,
        "gitea_repos": gitea_repos,
        "new_projects": new_projects,
        "stats": stats,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })


@data_bp.route('/api/containers')
def api_containers():
    containers = get_docker_containers()
    return jsonify({
        "containers": containers,
        "stats": _container_stats(containers),
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    })
