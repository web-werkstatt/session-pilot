"""Check: JS-Funktionsduplikate ueber Dateigrenzen."""

import os
import re

from auto_coder.checks import BaseCheck
from auto_coder.config import IGNORE_DIRS
from auto_coder.report import Issue, issue_id

RE_FUNCTION = re.compile(r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>|\w+\s*=>))")


class JSQualityCheck(BaseCheck):
    name = "js_quality"
    description = "JS/TS Funktionsduplikate ueber Dateigrenzen"

    def is_applicable(self, project_path: str) -> bool:
        return self._has_js_files(project_path)

    def run(self, project_path: str) -> list[Issue]:
        names: dict[str, list[str]] = {}

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".js", ".ts", ".jsx", ".tsx"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, project_path)
                try:
                    with open(fpath, errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue

                for match in RE_FUNCTION.finditer(content):
                    name = match.group(1) or match.group(2)
                    if name and len(name) > 3:
                        names.setdefault(name, []).append(rel)

        issues = []
        idx = 0
        # Ignoriere generische Namen
        generic = {"init", "main", "setup", "render", "update", "handle", "fetch", "load", "save", "create", "delete", "test"}
        for name, files in names.items():
            if name.lower() in generic:
                continue
            unique = list(set(files))
            if len(unique) > 1:
                idx += 1
                issues.append(Issue(
                    id=issue_id("duplication", idx),
                    level="warning",
                    category="duplication",
                    title=f"JS-Funktion '{name}' in {len(unique)} Dateien",
                    files=unique[:5],
                    fix_prompt=f"Funktion '{name}' existiert in {', '.join(unique[:3])}. Verschiebe in ein gemeinsames Modul und importiere.",
                ))

        return issues

    @staticmethod
    def _has_js_files(project_path: str) -> bool:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            if any(f.endswith(ext) for f in files for ext in (".js", ".ts", ".jsx", ".tsx")):
                return True
        return False
