"""
Konfiguration für das Projekt-Dashboard
Sensible Werte werden aus Umgebungsvariablen geladen.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _env_flag(name, default=False):
    """Liest Bool-Flags robust aus der Umgebung."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# Pfade
PROJECTS_DIR = os.environ.get("DASHBOARD_PROJECTS_DIR", "/mnt/projects")
CACHE_FILE = os.path.join(PROJECTS_DIR, ".project_dashboard_cache.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_settings.json')
INCLUDE_SELF_PROJECT = _env_flag("DASHBOARD_INCLUDE_SELF_PROJECT", True)
PLAN_AUTO_TAG_ENABLED = _env_flag("DASHBOARD_PLAN_AUTO_TAG", True)
PLAN_AUTO_TAG_BACKUP_DIR = os.environ.get(
    "DASHBOARD_PLAN_AUTO_TAG_BACKUP_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups", "plan-auto-tagging"),
)

# Server
HOST = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
PORT = int(os.environ.get("DASHBOARD_PORT", "5055"))

# Gitea Konfiguration
GITEA_URL = os.environ.get("GITEA_URL", "https://git.webideas24.com")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")
GITEA_USER = os.environ.get("GITEA_USER", "webideas24")

# Portainer Konfiguration (Phase 7, 2026-04-14): optional, leer bedeutet "nicht anzeigen"
PORTAINER_URL = os.environ.get("PORTAINER_URL", "")

# PostgreSQL
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "project_dashboard"),
    "user": os.environ.get("DB_USER", "autodns"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

# Audit LLM Analyzer
AUDIT_LLM_ANALYZER_ENABLED = os.environ.get("AUDIT_LLM_ANALYZER_ENABLED", "0") == "1"
AUDIT_LLM_MAX_REQUIREMENTS = int(os.environ.get("AUDIT_LLM_MAX_REQUIREMENTS", "10"))
AUDIT_LLM_DEFAULT_MODE = os.environ.get("AUDIT_LLM_DEFAULT_MODE", "auto")
AUDIT_LLM_ALLOWED_PRIORITIES = os.environ.get("AUDIT_LLM_ALLOWED_PRIORITIES", "")
AUDIT_LLM_ALLOWED_RISK_LEVELS = os.environ.get("AUDIT_LLM_ALLOWED_RISK_LEVELS", "")

# Perplexity API
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_BASE_URL = os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai/chat/completions")
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar")
PERPLEXITY_TIMEOUT = int(os.environ.get("PERPLEXITY_TIMEOUT_SECONDS", "30"))

# Claude Code Accounts
CLAUDE_ACCOUNTS = [
    {"name": "claude", "config_dir": os.path.expanduser("~/.claude")},
    {"name": "claude1", "config_dir": os.path.expanduser("~/.claude-account1")},
    {"name": "minimax", "config_dir": os.path.expanduser("~/.claude-minimax")},
]
