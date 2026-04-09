"""Check: Ungenutzte Python-Imports und verwaiste .py-Dateien (V1).

V1-Scope:
- Ungenutzte Imports (AST-basiert, pro Datei)
- Verwaiste .py-Dateien (nie importiert, kein Entry Point)

V2 (deferred):
- Ungenutzte Funktionen/Klassen (Flask-Decorator-Erkennung noetig)
"""

import ast
import os
import re

from auto_coder.checks import BaseCheck
from auto_coder.checks._dead_code_utils import (
    collect_files,
    load_dead_code_ignore,
    read_file_content,
)
from auto_coder.report import Issue, issue_id

# Verzeichnisse die komplett uebersprungen werden
_SKIP_DIRS = {"tests", "test", "scripts", "migrations", "alembic"}

# Entry Points die nie als verwaist gelten
_ENTRY_POINTS = {
    "app.py", "__main__.py", "cli.py", "wsgi.py", "asgi.py",
    "manage.py", "setup.py", "conftest.py", "celery_app.py",
}

# Side-Effect-Imports (werden importiert fuer Nebeneffekte, nicht fuer Namen)
_SIDE_EFFECT_PACKAGES = {
    "dotenv", "encodings", "codecs", "locale", "warnings",
    "multiprocessing", "logging.config",
}

# Suppress-Kommentare
_NOQA_RE = re.compile(r'#\s*noqa(?:\s*:\s*F401)?', re.IGNORECASE)
_USED_BY_RE = re.compile(r'#\s*used\s+by', re.IGNORECASE)


class DeadCodeCheck(BaseCheck):
    name = "dead_code"
    description = "Erkennt ungenutzte Python-Imports und verwaiste .py-Dateien"

    def is_applicable(self, project_path: str) -> bool:
        py_files = collect_files(project_path, {".py"}, extra_skip_dirs=_SKIP_DIRS)
        return len(py_files) >= 2

    def run(self, project_path: str) -> list[Issue]:
        issues: list[Issue] = []
        ignore = load_dead_code_ignore(project_path)
        idx = 0

        py_files = collect_files(project_path, {".py"}, extra_skip_dirs=_SKIP_DIRS)

        # --- Ungenutzte Imports ---
        idx = self._check_unused_imports(project_path, py_files, ignore, issues, idx)

        # --- Verwaiste Dateien ---
        idx = self._check_orphaned_files(project_path, py_files, ignore, issues, idx)

        return issues

    def _check_unused_imports(self, project_path, py_files, ignore, issues, idx):
        for rel in py_files:
            if rel in ignore or os.path.basename(rel) in ignore:
                continue
            # __init__.py Re-Exports immer ueberspringen
            if os.path.basename(rel) == "__init__.py":
                continue

            fpath = os.path.join(project_path, rel)
            content = read_file_content(fpath)
            if not content.strip():
                continue

            try:
                tree = ast.parse(content, filename=rel)
            except SyntaxError:
                continue

            imports = self._extract_imports(tree, content)
            used_names = self._extract_used_names(tree)

            for imp_info in imports:
                name = imp_info["name"]
                if name in used_names:
                    continue
                if name == "_":
                    continue  # Convention fuer Side-Effect-Imports
                if imp_info.get("suppressed"):
                    continue
                if imp_info.get("side_effect"):
                    continue
                if name in ignore:
                    continue
                # In __all__ definiert = gewollter Re-Export
                if self._in_dunder_all(tree, name):
                    continue

                idx += 1
                issues.append(Issue(
                    id=issue_id(self.name, idx),
                    level="warning",
                    category=self.name,
                    title=f"Ungenutzter Import: {imp_info['stmt']} in {rel}",
                    files=[rel],
                    fix_prompt=f"Entferne den ungenutzten Import '{imp_info['stmt']}' in {rel}:{imp_info['line']}.",
                    confidence="high",
                    evidence=f"import {name} in {rel}:{imp_info['line']}, '{name}' never referenced in module",
                ))

        return idx

    def _check_orphaned_files(self, project_path, py_files, ignore, issues, idx):
        # Import-Graph bauen
        import_targets = set()  # Alle Module die irgendwo importiert werden

        # Entry Points sammeln (inkl. routes/ und tests/)
        entry_dirs = {"routes", "tests", "test", "scripts"}
        all_py = collect_files(project_path, {".py"})  # Inkl. tests/scripts fuer Import-Graph

        for rel in all_py:
            fpath = os.path.join(project_path, rel)
            content = read_file_content(fpath)
            if not content.strip():
                continue
            try:
                tree = ast.parse(content, filename=rel)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_targets.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        parts = node.module.split(".")
                        import_targets.add(parts[0])
                        # Auch tiefere Module erfassen
                        if len(parts) > 1:
                            import_targets.add(".".join(parts[:2]))

        # Dateien die weder Entry Point noch importiert sind
        for rel in py_files:
            if rel in ignore or os.path.basename(rel) in ignore:
                continue
            basename = os.path.basename(rel)
            if basename in _ENTRY_POINTS:
                continue
            if basename == "__init__.py":
                continue

            # In Entry-Point-Verzeichnis -> kein Kandidat
            parts = rel.replace("\\", "/").split("/")
            if any(p in entry_dirs for p in parts[:-1]):
                continue

            # Modulname ableiten
            module_name = self._rel_to_module(rel)
            module_parts = module_name.split(".")

            # Pruefen ob irgendein Prefix importiert wird
            is_imported = False
            for i in range(len(module_parts), 0, -1):
                candidate = ".".join(module_parts[:i])
                if candidate in import_targets:
                    is_imported = True
                    break

            if not is_imported:
                idx += 1
                issues.append(Issue(
                    id=issue_id(self.name, idx),
                    level="warning",
                    category=self.name,
                    title=f"Verwaiste Python-Datei: {rel}",
                    files=[rel],
                    fix_prompt=f"Pruefe ob {rel} noch benoetigt wird. "
                               f"Wenn nicht, entferne die Datei.",
                    confidence="medium",
                    evidence=f"{rel} (module: {module_name}) not imported by any file, not an entry point",
                ))

        return idx

    @staticmethod
    def _extract_imports(tree: ast.AST, source: str) -> list[dict]:
        """Extrahiert Import-Informationen aus AST."""
        imports = []
        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    suppressed = bool(_NOQA_RE.search(line_text) or _USED_BY_RE.search(line_text))
                    side_effect = alias.name.split(".")[0] in _SIDE_EFFECT_PACKAGES
                    imports.append({
                        "name": name.split(".")[0],
                        "stmt": f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""),
                        "line": node.lineno,
                        "suppressed": suppressed,
                        "side_effect": side_effect,
                    })
            elif isinstance(node, ast.ImportFrom):
                if not node.names:
                    continue
                module = node.module or ""
                line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                suppressed = bool(_NOQA_RE.search(line_text) or _USED_BY_RE.search(line_text))
                side_effect = module.split(".")[0] in _SIDE_EFFECT_PACKAGES
                for alias in node.names:
                    if alias.name == "*":
                        continue  # Star-Imports ueberspringen
                    name = alias.asname or alias.name
                    imports.append({
                        "name": name,
                        "stmt": f"from {module} import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""),
                        "line": node.lineno,
                        "suppressed": suppressed,
                        "side_effect": side_effect,
                    })

        return imports

    @staticmethod
    def _extract_used_names(tree: ast.AST) -> set[str]:
        """Extrahiert alle verwendeten Namen aus AST (ausser Import-Nodes)."""
        used = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Bei a.b.c nur 'a' ist ein Name-Node, aber auch 'b' als Attribut zaehlt
                if isinstance(node.value, ast.Name):
                    used.add(node.value.id)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Decorator-Argumente
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name):
                        used.add(dec.id)
                    elif isinstance(dec, ast.Attribute) and isinstance(dec.value, ast.Name):
                        used.add(dec.value.id)
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Name):
                            used.add(dec.func.id)
                        elif isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Name):
                            used.add(dec.func.value.id)

        return used

    @staticmethod
    def _in_dunder_all(tree: ast.AST, name: str) -> bool:
        """Prueft ob ein Name in __all__ definiert ist."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and elt.value == name:
                                    return True
        return False

    @staticmethod
    def _rel_to_module(rel: str) -> str:
        """Konvertiert relativen Pfad zu Python-Modulname."""
        module = rel.replace(os.sep, ".").replace("/", ".")
        if module.endswith(".py"):
            module = module[:-3]
        if module.endswith(".__init__"):
            module = module[:-9]
        return module
