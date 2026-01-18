"""
Cache Service - Projekt-Cache Verwaltung
"""
import os
import sys
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CACHE_FILE

# Cache TTL in Sekunden (2 Minuten für frischere Daten)
CACHE_TTL_SECONDS = 120


def load_cache():
    """Lädt den Cache"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"projects": {}, "last_update": None}


def is_cache_valid(cache, project_name):
    """Prüft ob der Cache-Eintrag für ein Projekt noch gültig ist"""
    entry = cache.get("projects", {}).get(project_name, {})
    cached_at = entry.get("cached_at")
    if not cached_at:
        return False
    try:
        cached_time = datetime.fromisoformat(cached_at)
        age_seconds = (datetime.now() - cached_time).total_seconds()
        return age_seconds < CACHE_TTL_SECONDS
    except:
        return False


def get_cached_activity(cache, project_name):
    """Holt gecachte Aktivitätsdaten für ein Projekt"""
    entry = cache.get("projects", {}).get(project_name, {})
    return entry.get("activity")


def set_cached_activity(cache, project_name, activity_data):
    """Speichert Aktivitätsdaten im Cache"""
    if "projects" not in cache:
        cache["projects"] = {}
    cache["projects"][project_name] = {
        "activity": activity_data,
        "cached_at": datetime.now().isoformat()
    }


def save_cache(cache_data):
    """Speichert den Cache"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except:
        pass
