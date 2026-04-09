"""Check: Verwaiste Frontend-Assets (JS/CSS-Dateien + ungenutzte CSS-Klassen)."""

import os
import re

from auto_coder.checks import BaseCheck
from auto_coder.checks._dead_code_utils import (
    collect_files,
    load_dead_code_ignore,
    parse_template_assets,
    read_file_content,
)
from auto_coder.report import Issue, issue_id

# CSS-Klassen-Definition: .class-name { ... }
# Ignoriert Pseudo-Klassen (:hover etc.) und CSS-Variablen (--var)
_CSS_CLASS_DEF_RE = re.compile(r'\.([a-zA-Z_][\w-]*)\s*[{,:\[]')

# CSS-Klassen-Referenzen in HTML/JS
_HTML_CLASS_RE = re.compile(r'class=["\']([^"\']*)["\']')
_CLASSLIST_RE = re.compile(
    r'classList\.(?:add|remove|toggle|replace|contains)\s*\(\s*["\']([^"\']+)["\']'
)
_CLASSNAME_RE = re.compile(r'className\s*[+=]\s*["\']([^"\']+)["\']')

# CSS @import/@use als Referenz
_CSS_IMPORT_RE = re.compile(r'@(?:import|use)\s+(?:url\s*\(\s*)?["\']([^"\']+)["\']')

# Dynamische Klassen in Templates ({{ var }})
_DYNAMIC_CLASS_RE = re.compile(r'\{\{[^}]*\}\}')

# Pseudo-Klassen und At-Rules die keine echten CSS-Klassen sind
_PSEUDO_PREFIXES = {"hover", "focus", "active", "visited", "first", "last", "nth", "not",
                    "before", "after", "root", "checked", "disabled", "empty", "target",
                    "placeholder", "selection", "webkit", "moz", "ms"}


class DeadFrontendCheck(BaseCheck):
    name = "dead_frontend"
    description = "Erkennt verwaiste JS/CSS-Dateien und ungenutzte CSS-Klassen"

    def is_applicable(self, project_path: str) -> bool:
        return (os.path.isdir(os.path.join(project_path, "static")) and
                os.path.isdir(os.path.join(project_path, "templates")))

    def run(self, project_path: str) -> list[Issue]:
        issues: list[Issue] = []
        ignore = load_dead_code_ignore(project_path)
        idx = 0

        # --- Verwaiste JS/CSS-Dateien ---
        idx = self._check_orphaned_assets(project_path, ignore, issues, idx)

        # --- Ungenutzte CSS-Klassen ---
        idx = self._check_unused_css_classes(project_path, ignore, issues, idx)

        return issues

    def _check_orphaned_assets(self, project_path, ignore, issues, idx):
        js_refs, css_refs = parse_template_assets(project_path)

        # CSS @import Referenzen auch einsammeln
        css_import_refs = self._collect_css_imports(project_path)
        css_refs |= css_import_refs

        # JS-Dateien pruefen
        js_dir = os.path.join(project_path, "static", "js")
        if os.path.isdir(js_dir):
            for fname in sorted(os.listdir(js_dir)):
                if not fname.endswith(".js"):
                    continue
                rel = f"static/js/{fname}"
                if rel in ignore or fname in ignore:
                    continue
                if fname not in js_refs:
                    idx += 1
                    issues.append(Issue(
                        id=issue_id(self.name, idx),
                        level="warning",
                        category=self.name,
                        title=f"Verwaiste JS-Datei: {rel}",
                        files=[rel],
                        fix_prompt=f"Pruefe ob {rel} noch benoetigt wird. Wenn nicht, entferne die Datei.",
                        confidence="high",
                        evidence=f"{rel} not referenced via <script src> in any template",
                    ))

        # CSS-Dateien pruefen
        css_dir = os.path.join(project_path, "static", "css")
        if os.path.isdir(css_dir):
            for fname in sorted(os.listdir(css_dir)):
                if not fname.endswith(".css"):
                    continue
                rel = f"static/css/{fname}"
                if rel in ignore or fname in ignore:
                    continue
                if fname not in css_refs:
                    idx += 1
                    issues.append(Issue(
                        id=issue_id(self.name, idx),
                        level="warning",
                        category=self.name,
                        title=f"Verwaiste CSS-Datei: {rel}",
                        files=[rel],
                        fix_prompt=f"Pruefe ob {rel} noch benoetigt wird. Wenn nicht, entferne die Datei.",
                        confidence="high",
                        evidence=f"{rel} not referenced via <link href> or @import in any template/CSS",
                    ))

        return idx

    def _collect_css_imports(self, project_path):
        """Sammelt Dateinamen die per @import/@use in CSS referenziert werden."""
        refs = set()
        css_dir = os.path.join(project_path, "static", "css")
        if not os.path.isdir(css_dir):
            return refs
        for fname in os.listdir(css_dir):
            if not fname.endswith(".css"):
                continue
            content = read_file_content(os.path.join(css_dir, fname))
            for match in _CSS_IMPORT_RE.finditer(content):
                imported = os.path.basename(match.group(1))
                refs.add(imported)
        return refs

    def _check_unused_css_classes(self, project_path, ignore, issues, idx):
        # Alle CSS-Klassen-Definitionen sammeln
        css_classes: dict[str, list[str]] = {}  # class_name -> [defining files]
        css_files = collect_files(project_path, {".css"},
                                 extra_skip_dirs={"node_modules", ".git", "venv"})
        for rel in css_files:
            if not rel.startswith("static/"):
                continue
            content = read_file_content(os.path.join(project_path, rel))
            for match in _CSS_CLASS_DEF_RE.finditer(content):
                cls_name = match.group(1)
                if cls_name.lower() in _PSEUDO_PREFIXES:
                    continue
                if cls_name.startswith("-"):
                    continue  # CSS Custom Property Fallback
                css_classes.setdefault(cls_name, []).append(rel)

        if not css_classes:
            return idx

        # Alle Referenzen aus Templates und JS sammeln
        used_classes = self._collect_class_references(project_path)

        # Dateien mit dynamischen Klassen markieren
        dynamic_files = self._find_dynamic_class_files(project_path)

        for cls_name, defining_files in sorted(css_classes.items()):
            if cls_name in used_classes:
                continue
            if cls_name in ignore:
                continue
            # Sehr kurze Klassennamen (1-2 Zeichen) ueberspringen — zu viele false positives
            if len(cls_name) <= 2:
                continue

            # Confidence bestimmen
            any_dynamic = any(f in dynamic_files for f in defining_files)
            confidence = "low" if any_dynamic else "medium"

            idx += 1
            issues.append(Issue(
                id=issue_id(self.name, idx),
                level="info",
                category=self.name,
                title=f"Potentiell ungenutzte CSS-Klasse: .{cls_name}",
                files=defining_files,
                fix_prompt=f"Pruefe ob die CSS-Klasse .{cls_name} in {', '.join(defining_files)} noch verwendet wird.",
                confidence=confidence,
                evidence=f".{cls_name} defined in {', '.join(defining_files)}, no reference in templates or JS",
            ))

            # Max 30 CSS-Klassen-Issues um Report nicht zu ueberladen
            if idx >= 30:
                break

        return idx

    def _collect_class_references(self, project_path) -> set[str]:
        """Sammelt alle CSS-Klassen-Referenzen aus Templates und JS."""
        used = set()

        # Templates
        templates_dir = os.path.join(project_path, "templates")
        if os.path.isdir(templates_dir):
            for rel in collect_files(templates_dir, {".html"}):
                content = read_file_content(os.path.join(templates_dir, rel))
                self._extract_classes_from_content(content, used)

        # JS-Dateien
        js_dir = os.path.join(project_path, "static", "js")
        if os.path.isdir(js_dir):
            for fname in os.listdir(js_dir):
                if not fname.endswith(".js"):
                    continue
                content = read_file_content(os.path.join(js_dir, fname))
                self._extract_classes_from_content(content, used)

        return used

    def _extract_classes_from_content(self, content: str, used: set[str]):
        """Extrahiert CSS-Klassen-Referenzen aus einem Textinhalt."""
        for match in _HTML_CLASS_RE.finditer(content):
            for cls in match.group(1).split():
                cls = cls.strip()
                if cls and not cls.startswith("{"):
                    used.add(cls)
        for match in _CLASSLIST_RE.finditer(content):
            for cls in match.group(1).split():
                used.add(cls.strip())
        for match in _CLASSNAME_RE.finditer(content):
            for cls in match.group(1).split():
                used.add(cls.strip())
        # String-Literale die wie Klassennamen aussehen (z.B. in Template-Strings)
        for match in re.finditer(r'["\']([a-zA-Z_][\w-]*(?:\s+[a-zA-Z_][\w-]*)*)["\']', content):
            candidate = match.group(1)
            if " " in candidate:
                for cls in candidate.split():
                    used.add(cls.strip())

    def _find_dynamic_class_files(self, project_path) -> set[str]:
        """Findet CSS-Dateien deren Klassen dynamisch gesetzt werden koennten."""
        dynamic = set()
        templates_dir = os.path.join(project_path, "templates")
        if not os.path.isdir(templates_dir):
            return dynamic
        for rel in collect_files(templates_dir, {".html"}):
            content = read_file_content(os.path.join(templates_dir, rel))
            if _DYNAMIC_CLASS_RE.search(content):
                # Markiere alle CSS-Dateien die in diesem Template geladen werden
                for match in re.finditer(r'href=["\']([^"\']*\.css)["\']', content):
                    dynamic.add(os.path.basename(match.group(1)))
        return dynamic
