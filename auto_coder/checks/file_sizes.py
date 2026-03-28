"""Check: Dateigroessen-Limits."""

import os

from auto_coder.checks import BaseCheck
from auto_coder.config import FILE_SIZE_LIMITS, IGNORE_DIRS
from auto_coder.report import Issue, issue_id


class FileSizeCheck(BaseCheck):
    name = "file_size"
    description = "Prueft Dateigroessen gegen konfigurierte Limits"

    def run(self, project_path: str) -> list[Issue]:
        issues = []
        idx = 0
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                limit = FILE_SIZE_LIMITS.get(ext)
                if not limit:
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, errors="ignore") as f:
                        line_count = sum(1 for _ in f)
                except OSError:
                    continue
                if line_count <= limit:
                    continue
                idx += 1
                ratio = line_count / limit
                level = "error" if ratio > 1.5 else "warning"
                rel = os.path.relpath(fpath, project_path)
                issues.append(Issue(
                    id=issue_id(self.name, idx),
                    level=level,
                    category=self.name,
                    title=f"{rel}: {line_count} Zeilen (Limit: {limit})",
                    files=[rel],
                    fix_prompt=f"Teile {rel} auf ({line_count} Zeilen, Limit: {limit}). Schlage thematische Aufteilung vor.",
                ))
        return issues
