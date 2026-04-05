"""
Persistente Dashboard-Einstellungen mit Env-Fallback.
"""
import json
import os

from config import INCLUDE_SELF_PROJECT, SETTINGS_FILE


DEFAULT_SETTINGS = {
    "include_self_project": INCLUDE_SELF_PROJECT,
    "account_badge_styles": {
        "claude": {"background": "rgba(79,195,247,0.12)", "text": "#4fc3f7", "border": "rgba(79,195,247,0.28)"},
        "account1": {"background": "rgba(79,195,247,0.12)", "text": "#4fc3f7", "border": "rgba(79,195,247,0.28)"},
        "claude1": {"background": "rgba(207,111,247,0.12)", "text": "#cf6ff7", "border": "rgba(207,111,247,0.28)"},
        "codex": {"background": "rgba(255,152,0,0.14)", "text": "#ffb74d", "border": "rgba(255,183,77,0.34)"},
        "minimax": {"background": "rgba(111,247,176,0.12)", "text": "#6ff7b0", "border": "rgba(111,247,176,0.28)"},
        "gemini": {"background": "rgba(66,133,244,0.14)", "text": "#7fb1ff", "border": "rgba(66,133,244,0.32)"},
        "copilot": {"background": "rgba(255,255,255,0.08)", "text": "#d8dee9", "border": "rgba(255,255,255,0.18)"},
        "amazonq": {"background": "rgba(255,153,0,0.15)", "text": "#ffb74d", "border": "rgba(255,153,0,0.30)"},
        "opencode": {"background": "rgba(236,72,153,0.14)", "text": "#f472b6", "border": "rgba(244,114,182,0.32)"},
        "kilo": {"background": "rgba(168,85,247,0.14)", "text": "#c084fc", "border": "rgba(192,132,252,0.32)"},
        "hermes": {"background": "rgba(251,191,36,0.14)", "text": "#fbbf24", "border": "rgba(251,191,36,0.32)"},
    },
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
    settings["account_badge_styles"] = _normalize_badge_styles(
        stored.get("account_badge_styles"),
        DEFAULT_SETTINGS["account_badge_styles"],
    )
    return settings


def save_dashboard_settings(data):
    settings = load_dashboard_settings()
    settings["include_self_project"] = _normalize_bool(
        data.get("include_self_project"),
        settings["include_self_project"],
    )
    settings["account_badge_styles"] = _normalize_badge_styles(
        data.get("account_badge_styles"),
        settings.get("account_badge_styles") or DEFAULT_SETTINGS["account_badge_styles"],
    )

    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    return settings


def should_include_self_project():
    return load_dashboard_settings()["include_self_project"]


def _normalize_badge_styles(value, defaults):
    styles = {}
    if isinstance(defaults, dict):
        for key, config in defaults.items():
            norm_key = _normalize_badge_key(key)
            if not norm_key or not isinstance(config, dict):
                continue
            styles[norm_key] = {
                "background": str(config.get("background") or ""),
                "text": str(config.get("text") or ""),
                "border": str(config.get("border") or ""),
            }

    if not isinstance(value, dict):
        return styles

    for key, config in value.items():
        norm_key = _normalize_badge_key(key)
        if not norm_key or not isinstance(config, dict):
            continue
        styles[norm_key] = {
            "background": str(config.get("background") or ""),
            "text": str(config.get("text") or ""),
            "border": str(config.get("border") or ""),
        }
    return styles


def _normalize_badge_key(value):
    text = str(value or "").strip().lower()
    return "".join(ch for ch in text if ch.isalnum())
