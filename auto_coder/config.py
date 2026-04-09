"""Zentrale Konfiguration fuer auto_coder."""

import os

QUALITY_DIR = ".quality"
REPORT_FILE = "report.json"
PROJECTS_ROOT = os.environ.get("PROJECTS_ROOT", "/mnt/projects")

SCORE_WEIGHTS = {
    "duplication": -5,
    "complexity": -3,
    "file_size": -2,
    "css_tokens": -2,
    "css_undefined": -1,
    "architecture": -5,
    "test_failure": -5,
    "dead_code": -2,
    "dead_deps": -1,
    "dead_frontend": -2,
}

FILE_SIZE_LIMITS = {
    ".py": 500,
    ".tsx": 300,
    ".jsx": 300,
    ".ts": 500,
    ".js": 500,
    ".css": 400,
    ".html": 300,
    ".astro": 300,
}

LEVELS = [
    ("A", 90),
    ("B", 75),
    ("C", 60),
    ("D", 40),
    ("F", 0),
]

RADON_MIN_GRADE = "C"

IGNORE_DIRS = {
    "node_modules", ".git", "venv", "__pycache__", ".quality",
    "dist", "build", ".venv", "env", ".env",
    ".claude", ".jscpd", "backups", "_archive",
    ".next", ".nuxt", ".svelte-kit",
}

MAX_HISTORY_ENTRIES = 90
BASELINE_FILE = "baseline.json"
