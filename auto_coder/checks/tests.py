"""Check: Test-Erkennung und optionale Ausfuehrung."""

import json
import os
import subprocess

from auto_coder.checks import BaseCheck
from auto_coder.config import IGNORE_DIRS, QUALITY_DIR
from auto_coder.report import Issue, issue_id


class TestCheck(BaseCheck):
    name = "tests"
    description = "Erkennt Test-Framework und prueft Test-Status"

    def run(self, project_path: str) -> list[Issue]:
        issues = []
        framework = self._detect_framework(project_path)

        if not framework:
            issues.append(Issue(
                id=issue_id("test_failure", 1),
                level="info",
                category="test_failure",
                title="Kein Test-Framework erkannt",
                files=[],
                fix_prompt="Richte ein Test-Framework ein (pytest fuer Python, vitest/jest fuer JS/TS).",
            ))
            return issues

        # Tests nur ausfuehren wenn explizit konfiguriert
        config_path = os.path.join(project_path, QUALITY_DIR, "config.json")
        run_tests = False
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                run_tests = cfg.get("run_tests", False)
            except (json.JSONDecodeError, OSError):
                pass

        if not run_tests:
            return []  # Tests erkannt, aber nicht ausfuehren

        return self._run_tests(project_path, framework)

    def _detect_framework(self, project_path: str) -> str | None:
        # Python: pytest
        tests_dir = os.path.join(project_path, "tests")
        if os.path.isdir(tests_dir):
            return "pytest"
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            if any(f.startswith("test_") and f.endswith(".py") for f in files):
                return "pytest"
            break  # Nur Top-Level

        # Node: npm test
        pkg = os.path.join(project_path, "package.json")
        if os.path.exists(pkg):
            try:
                with open(pkg) as f:
                    data = json.load(f)
                scripts = data.get("scripts", {})
                if "test" in scripts and scripts["test"] != 'echo "Error: no test specified" && exit 1':
                    return "npm"
            except (json.JSONDecodeError, OSError):
                pass

        return None

    def _run_tests(self, project_path: str, framework: str) -> list[Issue]:
        issues = []
        try:
            if framework == "pytest":
                result = subprocess.run(
                    ["python", "-m", "pytest", "--tb=short", "-q"],
                    capture_output=True, text=True, timeout=60,
                    cwd=project_path,
                )
            elif framework == "npm":
                result = subprocess.run(
                    ["npm", "test", "--", "--reporter=json"],
                    capture_output=True, text=True, timeout=60,
                    cwd=project_path,
                )
            else:
                return []

            if result.returncode != 0:
                issues.append(Issue(
                    id=issue_id("test_failure", 1),
                    level="error",
                    category="test_failure",
                    title=f"Tests fehlgeschlagen ({framework})",
                    files=[],
                    fix_prompt=f"Tests schlagen fehl. Output:\n{result.stdout[-500:] if result.stdout else result.stderr[-500:]}",
                ))
        except subprocess.TimeoutExpired:
            issues.append(Issue(
                id=issue_id("test_failure", 1),
                level="warning",
                category="test_failure",
                title="Test-Timeout (>60s)",
                files=[],
                fix_prompt="Tests brauchen laenger als 60 Sekunden. Optimiere oder parallelisiere.",
            ))

        return issues
