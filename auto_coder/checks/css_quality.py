"""Check: CSS-Variablen-Konsistenz und Duplikate."""

import os
import re

from auto_coder.checks import BaseCheck
from auto_coder.config import IGNORE_DIRS
from auto_coder.report import Issue, issue_id

RE_VAR_DEF = re.compile(r"(--[\w-]+)\s*:")
RE_VAR_REF = re.compile(r"var\((--[\w-]+)\)")
RE_SELECTOR = re.compile(r"^\s*(\.[\w-]+)\s*\{", re.MULTILINE)


class CSSQualityCheck(BaseCheck):
    name = "css_quality"
    description = "CSS-Variablen-Konsistenz und duplizierte Selektoren"

    def is_applicable(self, project_path: str) -> bool:
        return self._has_css_files(project_path)

    def run(self, project_path: str) -> list[Issue]:
        definitions: dict[str, list[str]] = {}
        references: dict[str, list[str]] = {}
        selectors: dict[str, list[str]] = {}

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fname in files:
                if not fname.endswith(".css"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, project_path)
                try:
                    with open(fpath, errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue

                for match in RE_VAR_DEF.finditer(content):
                    definitions.setdefault(match.group(1), []).append(rel)
                for match in RE_VAR_REF.finditer(content):
                    references.setdefault(match.group(1), []).append(rel)
                for match in RE_SELECTOR.finditer(content):
                    selectors.setdefault(match.group(1), []).append(rel)

        issues = []
        idx = 0

        # Undefinierte Variablen
        for var, ref_files in references.items():
            if var not in definitions:
                idx += 1
                unique_files = list(set(ref_files))
                issues.append(Issue(
                    id=issue_id("css_undefined", idx),
                    level="warning",
                    category="css_undefined",
                    title=f"Undefinierte CSS-Variable: {var}",
                    files=unique_files[:5],
                    fix_prompt=f"Variable {var} ist undefiniert. Definiere sie in design-tokens.css oder ersetze die Referenz.",
                ))

        # Ungenutzte Variablen
        for var, def_files in definitions.items():
            if var not in references:
                idx += 1
                issues.append(Issue(
                    id=issue_id("css_tokens", idx),
                    level="info",
                    category="css_tokens",
                    title=f"Ungenutzte CSS-Variable: {var}",
                    files=list(set(def_files))[:5],
                    fix_prompt=f"Variable {var} wird nirgends referenziert. Entfernen oder verwenden.",
                ))

        # Duplizierte Selektoren
        for selector, sel_files in selectors.items():
            unique = list(set(sel_files))
            if len(unique) > 1:
                idx += 1
                issues.append(Issue(
                    id=issue_id("css_tokens", idx),
                    level="warning",
                    category="css_tokens",
                    title=f"Selektor '{selector}' in {len(unique)} Dateien",
                    files=unique[:5],
                    fix_prompt=f"Selektor '{selector}' ist in {', '.join(unique[:3])} definiert. Konsolidiere an einem Ort.",
                ))

        return issues

    @staticmethod
    def _has_css_files(project_path: str) -> bool:
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            if any(f.endswith(".css") for f in files):
                return True
        return False
