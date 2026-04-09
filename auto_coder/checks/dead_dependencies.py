"""Check: Ungenutzte Dependencies (requirements.txt, package.json)."""

import json
import os
import re

from auto_coder.checks import BaseCheck
from auto_coder.checks._dead_code_utils import (
    collect_files,
    load_dead_code_ignore,
    read_file_content,
)
from auto_coder.report import Issue, issue_id

# PyPI-Name -> Import-Name Mapping (bekannte Abweichungen)
PYPI_IMPORT_MAP = {
    "psycopg2-binary": "psycopg2",
    "python-dotenv": "dotenv",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "python-dateutil": "dateutil",
    "pyyaml": "yaml",
    "beautifulsoup4": "bs4",
    "opencv-python": "cv2",
    "opencv-python-headless": "cv2",
    "python-magic": "magic",
    "python-jose": "jose",
    "python-multipart": "multipart",
    "markupsafe": "markupsafe",
    "werkzeug": "werkzeug",
    "jinja2": "jinja2",
    "itsdangerous": "itsdangerous",
    "click": "click",
}

# Packages die nie als "unused" gemeldet werden
PYTHON_WHITELIST = {
    # Runtime-Starters (CLI, nicht importiert)
    "gunicorn", "uvicorn", "waitress", "celery", "daphne", "hypercorn",
    # Build/Dev-Tools
    "setuptools", "wheel", "pip", "build", "twine", "flit",
    "black", "flake8", "mypy", "pylint", "pytest", "ruff", "isort",
    "autopep8", "bandit", "pre-commit", "tox", "nox",
    # Pytest-Plugins (werden implizit geladen)
    "pytest-cov", "pytest-asyncio", "pytest-mock", "pytest-xdist",
    "pytest-env", "pytest-timeout",
}

NPM_WHITELIST = {
    # Build-Tools
    "webpack", "webpack-cli", "webpack-dev-server",
    "vite", "rollup", "esbuild", "parcel",
    "eslint", "prettier", "stylelint",
    "typescript", "ts-node", "tsx",
    "tailwindcss", "postcss", "autoprefixer", "cssnano",
    "sass", "less", "stylus",
    # Test-Frameworks
    "jest", "mocha", "vitest", "cypress", "playwright",
    # Type-Packages (werden ueber tsconfig referenziert)
    # @types/* Pattern wird separat behandelt
}

_REQ_LINE_RE = re.compile(r'^([a-zA-Z0-9_][a-zA-Z0-9._-]*)')
_PY_IMPORT_RE = re.compile(r'(?:^|\n)\s*(?:import|from)\s+([a-zA-Z_]\w*)')
_JS_REQUIRE_RE = re.compile(r'''require\s*\(\s*['"]([^'"./][^'"]*)['"]\s*\)''')
_JS_IMPORT_RE = re.compile(r'''(?:import|from)\s+['"]([^'"./][^'"]*)['"]\s*;?''')
_JS_IMPORT_FROM_RE = re.compile(r'''import\s+.*?\s+from\s+['"]([^'"./][^'"]*)['"]\s*;?''')


class DeadDependenciesCheck(BaseCheck):
    name = "dead_deps"
    description = "Erkennt ungenutzte Dependencies in requirements.txt und package.json"

    def is_applicable(self, project_path: str) -> bool:
        return (os.path.isfile(os.path.join(project_path, "requirements.txt")) or
                os.path.isfile(os.path.join(project_path, "package.json")))

    def run(self, project_path: str) -> list[Issue]:
        issues: list[Issue] = []
        ignore = load_dead_code_ignore(project_path)
        idx = 0

        # Python
        req_path = os.path.join(project_path, "requirements.txt")
        if os.path.isfile(req_path):
            idx = self._check_python_deps(project_path, req_path, ignore, issues, idx)

        # npm
        pkg_path = os.path.join(project_path, "package.json")
        if os.path.isfile(pkg_path):
            idx = self._check_npm_deps(project_path, pkg_path, ignore, issues, idx)

        return issues

    def _check_python_deps(self, project_path, req_path, ignore, issues, idx):
        # Requirements parsen
        packages = self._parse_requirements(req_path)
        if not packages:
            return idx

        # Alle Python-Imports im Projekt sammeln
        py_files = collect_files(project_path, {".py"})
        all_imports = set()
        for rel in py_files:
            content = read_file_content(os.path.join(project_path, rel))
            for match in _PY_IMPORT_RE.finditer(content):
                all_imports.add(match.group(1).lower())

        file_count = len(py_files)

        for pkg_name in sorted(packages):
            pkg_lower = pkg_name.lower()
            if pkg_lower in ignore or pkg_name in ignore:
                continue
            if pkg_lower in PYTHON_WHITELIST:
                continue

            import_name = self._resolve_python_import(pkg_lower)
            if import_name.lower() in all_imports:
                continue

            idx += 1
            issues.append(Issue(
                id=issue_id(self.name, idx),
                level="info",
                category=self.name,
                title=f"Potentiell ungenutzte Python-Dependency: {pkg_name}",
                files=["requirements.txt"],
                fix_prompt=f"Pruefe ob {pkg_name} (import: {import_name}) noch benoetigt wird. "
                           f"Wenn nicht, entferne es aus requirements.txt.",
                confidence="high",
                evidence=f"{pkg_name} in requirements.txt, import '{import_name}' not found in {file_count} .py files",
            ))

        return idx

    def _check_npm_deps(self, project_path, pkg_path, ignore, issues, idx):
        try:
            with open(pkg_path, encoding="utf-8") as f:
                pkg_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return idx

        deps = {}
        deps.update(pkg_data.get("dependencies", {}))
        deps.update(pkg_data.get("devDependencies", {}))
        if not deps:
            return idx

        # Alle JS/TS Imports sammeln
        js_files = collect_files(project_path, {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"})
        all_imports = set()
        for rel in js_files:
            content = read_file_content(os.path.join(project_path, rel))
            for match in _JS_REQUIRE_RE.finditer(content):
                all_imports.add(self._normalize_npm_import(match.group(1)))
            for match in _JS_IMPORT_RE.finditer(content):
                all_imports.add(self._normalize_npm_import(match.group(1)))
            for match in _JS_IMPORT_FROM_RE.finditer(content):
                all_imports.add(self._normalize_npm_import(match.group(1)))

        file_count = len(js_files)

        for dep_name in sorted(deps.keys()):
            if dep_name in ignore:
                continue
            if dep_name in NPM_WHITELIST:
                continue
            if dep_name.startswith("@types/"):
                continue

            normalized = self._normalize_npm_import(dep_name)
            if normalized in all_imports:
                continue

            idx += 1
            issues.append(Issue(
                id=issue_id(self.name, idx),
                level="info",
                category=self.name,
                title=f"Potentiell ungenutzte npm-Dependency: {dep_name}",
                files=["package.json"],
                fix_prompt=f"Pruefe ob {dep_name} noch benoetigt wird. "
                           f"Wenn nicht, entferne es mit 'npm uninstall {dep_name}'.",
                confidence="high",
                evidence=f"{dep_name} in package.json, no require/import found in {file_count} JS/TS files",
            ))

        return idx

    @staticmethod
    def _parse_requirements(req_path: str) -> list[str]:
        """Parst requirements.txt und gibt Package-Namen zurueck."""
        packages = []
        try:
            with open(req_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    match = _REQ_LINE_RE.match(line)
                    if match:
                        packages.append(match.group(1))
        except OSError:
            pass
        return packages

    @staticmethod
    def _resolve_python_import(pkg_name: str) -> str:
        """Loest PyPI-Name zu Import-Name auf."""
        if pkg_name in PYPI_IMPORT_MAP:
            return PYPI_IMPORT_MAP[pkg_name]
        return pkg_name.replace("-", "_")

    @staticmethod
    def _normalize_npm_import(name: str) -> str:
        """Normalisiert npm-Import auf Package-Root (z.B. '@scope/pkg/sub' -> '@scope/pkg')."""
        if name.startswith("@"):
            parts = name.split("/")
            return "/".join(parts[:2]) if len(parts) >= 2 else name
        return name.split("/")[0]
