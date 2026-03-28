"""Check: Architektur-Regeln (Schicht-Verletzungen)."""

import os
import re

from auto_coder.checks import BaseCheck
from auto_coder.config import IGNORE_DIRS
from auto_coder.report import Issue, issue_id

ARCHITECTURE_RULES = [
    {
        "name": "db_in_routes",
        "pattern": re.compile(r"(?:import\s+psycopg2|from\s+psycopg2|import\s+sqlite3|\.execute\s*\()"),
        "restricted_dirs": ["routes"],
        "message": "Direkter DB-Zugriff in Routes",
        "fix": "Verschiebe DB-Zugriffe aus {file} in einen Service unter services/.",
    },
    {
        "name": "subprocess_in_routes",
        "pattern": re.compile(r"(?:import\s+subprocess|subprocess\.(?:run|call|Popen|check_output))"),
        "restricted_dirs": ["routes"],
        "message": "subprocess in Routes",
        "fix": "Verschiebe subprocess-Aufrufe aus {file} in einen Service unter services/.",
    },
    {
        "name": "file_io_in_routes",
        "pattern": re.compile(r"(?:^|\s)open\s*\([^)]*['\"][rwab]"),
        "restricted_dirs": ["routes"],
        "message": "Datei-I/O in Routes",
        "fix": "Verschiebe Datei-I/O aus {file} in einen Service unter services/.",
    },
]


class ArchitectureCheck(BaseCheck):
    name = "architecture"
    description = "Prueft Schicht-Regeln (kein DB/subprocess/I/O in Routes)"

    def run(self, project_path: str) -> list[Issue]:
        issues = []
        idx = 0

        for rule in ARCHITECTURE_RULES:
            for restricted_dir in rule["restricted_dirs"]:
                dir_path = os.path.join(project_path, restricted_dir)
                if not os.path.isdir(dir_path):
                    continue
                for root, dirs, files in os.walk(dir_path):
                    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                    for fname in files:
                        if not fname.endswith(".py"):
                            continue
                        fpath = os.path.join(root, fname)
                        rel = os.path.relpath(fpath, project_path)
                        try:
                            with open(fpath, errors="ignore") as f:
                                content = f.read()
                        except OSError:
                            continue
                        if rule["pattern"].search(content):
                            idx += 1
                            issues.append(Issue(
                                id=issue_id(self.name, idx),
                                level="warning",
                                category=self.name,
                                title=f"{rule['message']}: {rel}",
                                files=[rel],
                                fix_prompt=rule["fix"].format(file=rel),
                            ))
        return issues
