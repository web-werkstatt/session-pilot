"""Check: Code-Duplikation via jscpd."""

import json
import os
import shutil
import subprocess

from auto_coder.checks import BaseCheck
from auto_coder.config import IGNORE_DIRS, QUALITY_DIR
from auto_coder.report import Issue, issue_id


class DuplicationCheck(BaseCheck):
    name = "duplication"
    description = "Code-Duplikation via jscpd"

    def run(self, project_path: str) -> list[Issue]:
        if shutil.which("npx"):
            return self._run_jscpd(project_path)
        return self._run_fallback(project_path)

    def _run_jscpd(self, project_path: str) -> list[Issue]:
        output_dir = os.path.join(project_path, QUALITY_DIR, "jscpd")
        os.makedirs(output_dir, exist_ok=True)
        ignore_pattern = ",".join(sorted(IGNORE_DIRS))
        try:
            subprocess.run(
                [
                    "npx", "jscpd", project_path,
                    "--min-tokens", "30",
                    "--min-lines", "5",
                    "--reporters", "json",
                    "--output", output_dir,
                    "--ignore", ignore_pattern,
                ],
                capture_output=True, text=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._run_fallback(project_path)

        report_path = os.path.join(output_dir, "jscpd-report.json")
        if not os.path.exists(report_path):
            return []

        try:
            with open(report_path) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return []

        issues = []
        duplicates = data.get("duplicates", [])
        for idx, dup in enumerate(duplicates, 1):
            first = dup.get("firstFile", {})
            second = dup.get("secondFile", {})
            f1 = first.get("name", "?")
            f2 = second.get("name", "?")
            lines = dup.get("lines", 0)
            issues.append(Issue(
                id=issue_id(self.name, idx),
                level="warning",
                category=self.name,
                title=f"{lines} duplizierte Zeilen: {f1} <-> {f2}",
                files=[f1, f2],
                fix_prompt=f"Extrahiere den duplizierten Code ({lines} Zeilen) aus {f1} und {f2} in ein gemeinsames Modul.",
            ))
        return issues

    def _run_fallback(self, project_path: str) -> list[Issue]:
        """Einfacher Fallback: Funktionsnamen-Duplikation via grep."""
        try:
            result = subprocess.run(
                ["rg", r"^(def |function |const \w+ = )", "--type", "py",
                 "--type", "js", "-n", "--no-heading", project_path],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        names: dict[str, list[str]] = {}
        for line in result.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            fpath = os.path.relpath(parts[0], project_path)
            text = parts[2].strip()
            name = self._extract_name(text)
            if name and len(name) > 3:
                names.setdefault(name, []).append(fpath)

        issues = []
        idx = 0
        for name, files in names.items():
            unique = list(set(files))
            if len(unique) > 1:
                idx += 1
                issues.append(Issue(
                    id=issue_id(self.name, idx),
                    level="warning",
                    category=self.name,
                    title=f"'{name}' in {len(unique)} Dateien definiert",
                    files=unique[:5],
                    fix_prompt=f"Funktion '{name}' existiert in {', '.join(unique[:3])}. Konsolidiere in ein Modul.",
                ))
        return issues

    @staticmethod
    def _extract_name(text: str) -> str:
        for prefix in ("def ", "function "):
            if text.startswith(prefix):
                rest = text[len(prefix):]
                name = rest.split("(")[0].strip()
                return name
        if text.startswith("const "):
            rest = text[6:]
            name = rest.split("=")[0].strip()
            return name
        return ""
