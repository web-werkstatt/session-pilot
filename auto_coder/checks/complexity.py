"""Check: Cyclomatic Complexity via radon."""

import json
import os
import shutil
import subprocess

from auto_coder.checks import BaseCheck
from auto_coder.config import IGNORE_DIRS, RADON_MIN_GRADE
from auto_coder.report import Issue, issue_id


class ComplexityCheck(BaseCheck):
    name = "complexity"
    description = "Cyclomatic Complexity und Maintainability Index (Python)"

    def is_applicable(self, project_path: str) -> bool:
        return self._has_python_files(project_path)

    def run(self, project_path: str) -> list[Issue]:
        if not shutil.which("radon"):
            return []
        issues = []
        issues.extend(self._check_cc(project_path))
        issues.extend(self._check_mi(project_path))
        return issues

    def _check_cc(self, project_path: str) -> list[Issue]:
        """Cyclomatic Complexity - Funktionen mit CC > 10."""
        try:
            result = subprocess.run(
                ["radon", "cc", project_path, "-j", "--min", RADON_MIN_GRADE],
                capture_output=True, text=True, timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

        issues = []
        idx = 0
        for fpath, blocks in data.items():
            if self._should_ignore(fpath, project_path):
                continue
            rel = os.path.relpath(fpath, project_path)
            for block in blocks:
                cc = block.get("complexity", 0)
                if cc <= 10:
                    continue
                idx += 1
                name = block.get("name", "?")
                grade = block.get("rank", "?")
                issues.append(Issue(
                    id=issue_id(self.name, idx),
                    level="error" if cc > 20 else "warning",
                    category=self.name,
                    title=f"{rel}:{name} CC={cc} (Grade {grade})",
                    files=[rel],
                    fix_prompt=f"Refactore {name} in {rel} in kleinere Funktionen. Aktuelle CC={cc}, Ziel: <=10.",
                ))
        return issues

    def _check_mi(self, project_path: str) -> list[Issue]:
        """Maintainability Index - Module mit MI < 20."""
        try:
            result = subprocess.run(
                ["radon", "mi", project_path, "-j"],
                capture_output=True, text=True, timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

        issues = []
        idx = 100  # Offset to avoid ID collision with CC issues
        for fpath, info in data.items():
            if self._should_ignore(fpath, project_path):
                continue
            mi = info.get("mi", 100) if isinstance(info, dict) else 100
            if mi >= 20:
                continue
            idx += 1
            rel = os.path.relpath(fpath, project_path)
            issues.append(Issue(
                id=issue_id(self.name, idx),
                level="warning",
                category=self.name,
                title=f"{rel}: Maintainability Index {mi:.1f} (< 20)",
                files=[rel],
                fix_prompt=f"Verbessere die Wartbarkeit von {rel}. MI={mi:.1f}, Ziel: >=20. Reduziere Komplexitaet und verbessere Struktur.",
            ))
        return issues

    def _should_ignore(self, fpath: str, project_path: str) -> bool:
        rel = os.path.relpath(fpath, project_path)
        parts = rel.split(os.sep)
        return any(p in IGNORE_DIRS for p in parts)

    @staticmethod
    def _has_python_files(project_path: str) -> bool:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            if any(f.endswith(".py") for f in files):
                return True
        return False
