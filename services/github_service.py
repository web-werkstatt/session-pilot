"""
GitHub API Service - Stars, Issues, PRs, CI/CD-Status
Nutzt urllib (keine externen HTTP-Libraries), In-Memory Cache mit TTL.
"""
import json
import re
import ssl
import urllib.request
from datetime import datetime

# In-Memory Cache (5 Minuten TTL - GitHub hat Rate-Limits)
_github_cache = {"data": {}, "updated_at": None}
_GITHUB_CACHE_TTL = 300  # Sekunden


def _extract_github_info(remote_url):
    """Extrahiert owner/repo und optionalen Token aus GitHub Remote-URL.
    Unterstuetzt: https://github.com/owner/repo.git
                  https://TOKEN@github.com/owner/repo.git
    """
    if not remote_url or "github.com" not in remote_url:
        return None

    # Token aus URL extrahieren
    token = None
    token_match = re.search(r'https?://([^@]+)@github\.com', remote_url)
    if token_match:
        token = token_match.group(1)

    # Owner/Repo extrahieren
    repo_match = re.search(r'github\.com[/:]([^/]+)/([^/.]+)', remote_url)
    if not repo_match:
        return None

    return {
        "owner": repo_match.group(1),
        "repo": repo_match.group(2),
        "token": token,
        "full_name": f"{repo_match.group(1)}/{repo_match.group(2)}"
    }


def _github_api(path, token=None):
    """GitHub API Request mit optionalem Token"""
    ctx = ssl.create_default_context()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:  # noqa: E501
        if e.code == 404:
            return None
        if e.code == 403:  # Rate-Limit
            return {"error": "rate_limit"}
        return None
    except Exception:
        return None


def get_github_repo_info(remote_url):
    """Holt Repository-Infos: Stars, Forks, Issues, PRs, Sprache.
    Returns: dict oder None
    """
    info = _extract_github_info(remote_url)
    if not info:
        return None

    full_name = info["full_name"]

    # Cache pruefen
    global _github_cache
    if _github_cache["updated_at"]:
        age = (datetime.now() - _github_cache["updated_at"]).total_seconds()
        if age < _GITHUB_CACHE_TTL and full_name in _github_cache["data"]:
            return _github_cache["data"][full_name]

    token = info["token"]
    result = {
        "full_name": full_name,
        "owner": info["owner"],
        "repo": info["repo"],
        "stars": 0,
        "forks": 0,
        "open_issues": 0,
        "open_prs": 0,
        "language": None,
        "is_fork": False,
        "ci_status": None,
        "ci_conclusion": None,
        "ci_workflow": None,
    }

    # Repo-Infos
    repo_data = _github_api(f"/repos/{full_name}", token)
    if not repo_data or "error" in repo_data:
        return None

    result["stars"] = repo_data.get("stargazers_count", 0)
    result["forks"] = repo_data.get("forks_count", 0)
    result["open_issues"] = repo_data.get("open_issues_count", 0)  # Issues + PRs
    result["language"] = repo_data.get("language")
    result["is_fork"] = repo_data.get("fork", False)

    # Open PRs separat zaehlen (open_issues_count enthaelt PRs)
    prs = _github_api(f"/repos/{full_name}/pulls?state=open&per_page=1", token)
    if isinstance(prs, list):
        # Header-basierte Pagination waere besser, aber fuer Count reicht das
        all_prs = _github_api(f"/repos/{full_name}/pulls?state=open&per_page=100", token)
        if isinstance(all_prs, list):
            result["open_prs"] = len(all_prs)
            # Issues = open_issues_count - open_prs
            result["open_issues"] = max(0, result["open_issues"] - result["open_prs"])

    # CI/CD Status - letzter Workflow-Run auf Default-Branch
    default_branch = repo_data.get("default_branch", "main")
    runs = _github_api(
        f"/repos/{full_name}/actions/runs?branch={default_branch}&per_page=1",
        token
    )
    if runs and isinstance(runs, dict) and runs.get("workflow_runs"):
        run = runs["workflow_runs"][0]
        result["ci_status"] = run.get("status")  # completed, in_progress, queued
        result["ci_conclusion"] = run.get("conclusion")  # success, failure, cancelled
        result["ci_workflow"] = run.get("name")

    # Cache speichern
    _github_cache["data"][full_name] = result
    _github_cache["updated_at"] = datetime.now()

    return result


def get_github_info_for_project(project_path):
    """Convenience: Liest Remote-URL aus Git und holt GitHub-Infos"""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", project_path, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode != 0:
            return None
        remote_url = r.stdout.strip()
        if "github.com" not in remote_url:
            return None
        return get_github_repo_info(remote_url)
    except (OSError, subprocess.TimeoutExpired):
        return None
