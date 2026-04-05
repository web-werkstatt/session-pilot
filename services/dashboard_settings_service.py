"""
Persistente Dashboard-Einstellungen mit Env-Fallback.
"""
import json
import os

from config import INCLUDE_SELF_PROJECT, SETTINGS_FILE


DEFAULT_SETTINGS = {
    "include_self_project": INCLUDE_SELF_PROJECT,
}


def _normalize_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def load_dashboard_settings():
    settings = dict(DEFAULT_SETTINGS)
    if not os.path.exists(SETTINGS_FILE):
        return settings

    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            stored = json.load(f)
    except (OSError, json.JSONDecodeError):
        return settings

    settings["include_self_project"] = _normalize_bool(
        stored.get("include_self_project"),
        DEFAULT_SETTINGS["include_self_project"],
    )
    return settings


def save_dashboard_settings(data):
    settings = load_dashboard_settings()
    settings["include_self_project"] = _normalize_bool(
        data.get("include_self_project"),
        settings["include_self_project"],
    )

    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    return settings


def should_include_self_project():
    return load_dashboard_settings()["include_self_project"]
