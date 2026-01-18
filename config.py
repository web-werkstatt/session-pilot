"""
Konfiguration für das Projekt-Dashboard
"""
import os

# Pfade
PROJECTS_DIR = "/mnt/projects"
CACHE_FILE = os.path.join(PROJECTS_DIR, ".project_dashboard_cache.json")

# Server
HOST = "0.0.0.0"
PORT = 5055

# Gitea Konfiguration
GITEA_URL = "https://git.webideas24.com"
GITEA_TOKEN = "b09199352f9f13608490a4736a89d76438aea320"
GITEA_USER = "webideas24"
