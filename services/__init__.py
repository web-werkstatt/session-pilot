"""
Services für das Projekt-Dashboard
"""
from services.gitea_service import get_gitea_repos, get_gitea_repo_commits
from services.git_service import get_local_git_info
from services.docker_service import get_docker_containers, load_yaml_simple, container_action, get_container_logs
from services.project_scanner import scan_projects, load_project_json, get_project_last_activity, update_project_json
from services.cache_service import load_cache, save_cache
from services.github_service import get_github_repo_info, get_github_info_for_project
from services.health_check_service import check_health, get_health_for_project
from services.security_scanner import get_security_for_project

__all__ = [
    'get_gitea_repos',
    'get_gitea_repo_commits',
    'get_local_git_info',
    'get_docker_containers',
    'load_yaml_simple',
    'container_action',
    'get_container_logs',
    'scan_projects',
    'load_project_json',
    'get_project_last_activity',
    'update_project_json',
    'load_cache',
    'save_cache',
    'get_github_repo_info',
    'get_github_info_for_project',
    'check_health',
    'get_health_for_project',
    'get_security_for_project',
]
