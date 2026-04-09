"""Shared Helpers fuer Dead-Code-Checks."""

import os
import re

from auto_coder.config import IGNORE_DIRS


def load_dead_code_ignore(project_path: str) -> set[str]:
    """Liest .dead-code-ignore und gibt Set von ignorierten Pfaden/Namen zurueck."""
    ignore_path = os.path.join(project_path, ".dead-code-ignore")
    entries = set()
    if not os.path.isfile(ignore_path):
        return entries
    try:
        with open(ignore_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                entries.add(line)
    except OSError:
        pass
    return entries


def collect_files(project_path: str, extensions: set[str],
                  ignore_dirs: set[str] | None = None,
                  extra_skip_dirs: set[str] | None = None) -> list[str]:
    """Sammelt Dateien mit gegebenen Extensions, IGNORE_DIRS beachten.

    Returns:
        Liste von relativen Pfaden (relativ zu project_path).
    """
    skip = set(ignore_dirs or IGNORE_DIRS)
    if extra_skip_dirs:
        skip |= extra_skip_dirs
    result = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                rel = os.path.relpath(os.path.join(root, fname), project_path)
                result.append(rel)
    return result


_SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']*\.js[^"\']*)["\']', re.IGNORECASE)
_LINK_RE = re.compile(r'<link[^>]+href=["\']([^"\']*\.css[^"\']*)["\']', re.IGNORECASE)
_EXTENDS_RE = re.compile(r'{%[-\s]*extends\s+["\']([^"\']+)["\']', re.IGNORECASE)


def parse_template_assets(project_path: str) -> tuple[set[str], set[str]]:
    """Extrahiert JS- und CSS-Referenzen aus allen Templates (inkl. Vererbung).

    Returns:
        (js_refs, css_refs) — Sets von Dateinamen (nur Basename, normalisiert).
    """
    templates_dir = os.path.join(project_path, "templates")
    if not os.path.isdir(templates_dir):
        return set(), set()

    js_refs: set[str] = set()
    css_refs: set[str] = set()
    parent_templates: set[str] = set()

    # Erst alle Templates einlesen und Parent-Chain aufloesen
    template_contents: dict[str, str] = {}
    for root, dirs, files in os.walk(templates_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            if not fname.endswith(".html"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                rel = os.path.relpath(fpath, templates_dir)
                template_contents[rel] = content
            except OSError:
                continue

    # Parent-Templates identifizieren (die von extends referenziert werden)
    for content in template_contents.values():
        for match in _EXTENDS_RE.finditer(content):
            parent_templates.add(match.group(1))

    # Assets aus ALLEN Templates extrahieren (nicht nur Parents)
    for content in template_contents.values():
        for match in _SCRIPT_RE.finditer(content):
            src = match.group(1)
            if "://" in src:
                continue  # CDN/externe URL
            js_refs.add(_normalize_asset_ref(src))
        for match in _LINK_RE.finditer(content):
            href = match.group(1)
            if "://" in href:
                continue
            css_refs.add(_normalize_asset_ref(href))

    return js_refs, css_refs


def _normalize_asset_ref(ref: str) -> str:
    """Normalisiert Asset-Referenz auf Dateiname.

    '/static/js/foo.js' -> 'foo.js'
    '{{ url_for("static", filename="js/bar.js") }}' -> 'bar.js'
    """
    # Jinja url_for Pattern
    url_for_match = re.search(r'filename=["\']([^"\']+)["\']', ref)
    if url_for_match:
        return os.path.basename(url_for_match.group(1))
    # Normaler Pfad
    return os.path.basename(ref.split("?")[0].split("#")[0])


def read_file_content(filepath: str) -> str:
    """Liest Dateiinhalt sicher, gibt leeren String bei Fehler."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""
