"""
Gitea API Service
"""
import json
import ssl
import urllib.request
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GITEA_URL, GITEA_TOKEN, GITEA_USER

# In-Memory Cache für Commits (60 Sekunden TTL)
_commits_cache = {"data": {}, "updated_at": None}
_COMMITS_CACHE_TTL = 60  # Sekunden


def get_gitea_repos():
    """Holt alle Repositories von Gitea"""
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            f"{GITEA_URL}/api/v1/user/repos?limit=100",
            headers={
                "Authorization": f"token {GITEA_TOKEN}",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            repos = json.loads(response.read().decode())
            return [{
                "name": r.get("name", ""),
                "full_name": r.get("full_name", ""),
                "description": r.get("description", ""),
                "html_url": r.get("html_url", ""),
                "clone_url": r.get("clone_url", ""),
                "updated_at": r.get("updated_at", "")[:16].replace("T", " ") if r.get("updated_at") else "",
                "stars": r.get("stars_count", 0),
                "open_issues": r.get("open_issues_count", 0),
                "default_branch": r.get("default_branch", "main")
            } for r in repos]
    except Exception as e:
        print(f"Gitea API Fehler: {e}")
        return []


def get_gitea_repo_commits():
    """Holt letzten Commit für jedes Gitea-Repo (mit In-Memory Cache)"""
    global _commits_cache

    # Cache prüfen
    if _commits_cache["updated_at"]:
        age = (datetime.now() - _commits_cache["updated_at"]).total_seconds()
        if age < _COMMITS_CACHE_TTL:
            return _commits_cache["data"]

    # Cache abgelaufen oder leer - neu laden
    repo_commits = {}
    try:
        ctx = ssl.create_default_context()
        repos = get_gitea_repos()

        for repo in repos:
            try:
                req = urllib.request.Request(
                    f"{GITEA_URL}/api/v1/repos/{GITEA_USER}/{repo['name']}/commits?limit=1",
                    headers={
                        "Authorization": f"token {GITEA_TOKEN}",
                        "Accept": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                    commits = json.loads(response.read().decode())
                    if commits:
                        repo_commits[repo['name']] = {
                            "sha": commits[0].get("sha", "")[:7],
                            "message": commits[0].get("commit", {}).get("message", "").split("\n")[0][:50],
                            "date": commits[0].get("commit", {}).get("author", {}).get("date", "")[:16].replace("T", " ")
                        }
            except:
                pass

        # Cache aktualisieren
        _commits_cache = {"data": repo_commits, "updated_at": datetime.now()}

    except Exception as e:
        print(f"Gitea Commits Fehler: {e}")

    return repo_commits
