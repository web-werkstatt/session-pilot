"""
Plan-Discovery-Scanner (Sprint sprint-plan-discovery, Commit 2).

Reine Discovery-Schicht: iteriert ueber feste Scan-Quellen, wendet Heuristik
+ Negativ-Liste + Exclusions an, liefert Metadaten-Dicts. Kein DB-Schreibpfad
(nur lesend ueber db_service.execute fuer Exclusion-Laden).

Scan-Quellen:
  ~/.claude/plans/                               -> claude_plans
  /mnt/projects/<p>/sprints/*.md                 -> project_sprints
  /mnt/projects/<p>/plans/*.md                   -> project_plans
  /mnt/projects/<p>/docs/{plans,sprints}/*.md    -> project_docs
  /mnt/projects/<p>/{roadmap,ROADMAP,
                     MASTERPLAN,master-plan}.md  -> project_root

Details: siehe sprints/sprint-plan-discovery.md (Basis + Nachtraege 1-5).
"""
import fnmatch
import hashlib
import logging
import os
import re
import threading
import time
from typing import Iterator, Optional

from config import PROJECTS_DIR
from services.db_service import execute, ensure_plan_scan_exclusions_schema

logger = logging.getLogger(__name__)

CLAUDE_PLANS_DIR = os.path.expanduser("~/.claude/plans")

# Harte Blacklist (Nachtrag 1): diese Verzeichnisse werden nie betreten
BLACKLIST_DIRS = frozenset({
    "node_modules", ".venv", "venv", "dist", "build", ".git",
    "archive", "archived", "backups", "_backup", ".cache",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".next",
})

PLAN_FILENAME_RE = re.compile(
    r"^(sprint|spec|plan|roadmap|master-plan|adr)[-_].*\.md$",
    re.IGNORECASE,
)
PLAN_ROOT_FILENAMES = frozenset({
    "roadmap.md", "ROADMAP.md", "MASTERPLAN.md", "master-plan.md",
})
PLAN_TAG_RE = re.compile(r"#(sprint|spec)-[A-Za-z0-9_-]+")
HEADING_RE = re.compile(r"^##\s+\S", re.MULTILINE)

# Negativ-Liste (Nachtrag 1): trotz Plan-Regex-Match ausgeschlossen
NEGATIVE_FILENAME_PATTERNS = (
    "*-retro*.md", "*-notes.md", "*-log.md", "*-changelog.md",
    "CHANGELOG.md", "HISTORY.md", "*-template.md", "README.md",
)

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB (Nachtrag 1)
MAX_DEPTH = 3                     # Tiefenbegrenzung (Nachtrag 1)
PREVIEW_CACHE_TTL_SEC = 10        # In-Memory-Cache fuer Preview (Nachtrag 4)

_preview_cache: dict = {"at": 0.0, "result": None, "key": None}
_preview_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Heuristik
# ---------------------------------------------------------------------------

def _is_plan_filename(name: str) -> bool:
    """Filename-Regex oder Root-Whitelist (Basis-Heuristik 1+2)."""
    if name in PLAN_ROOT_FILENAMES:
        return True
    return bool(PLAN_FILENAME_RE.match(name))


def _is_negative_filename(name: str) -> bool:
    """Negativ-Liste (Nachtrag 1) — schlaegt Plan-Match."""
    for pattern in NEGATIVE_FILENAME_PATTERNS:
        if fnmatch.fnmatchcase(name, pattern):
            return True
    return False


def _has_plan_tag(content: str) -> bool:
    """#sprint-*/#spec-* Tag (Basis-Heuristik 3)."""
    return bool(PLAN_TAG_RE.search(content))


def _has_heading(content: str) -> bool:
    """Content-Signal (Nachtrag 1): mindestens eine ## -Headline."""
    return bool(HEADING_RE.search(content))


def _is_plan_file(name: str, content: str) -> bool:
    """Gesamt-Heuristik: Filename-Match ODER Tag-Match, UND mind. ##-Heading."""
    if _is_negative_filename(name):
        return False
    filename_ok = _is_plan_filename(name)
    tag_ok = _has_plan_tag(content)
    if not (filename_ok or tag_ok):
        return False
    return _has_heading(content)


# ---------------------------------------------------------------------------
# Pfad- und Frontmatter-Helpers
# ---------------------------------------------------------------------------

def _extract_project_name(path: str) -> Optional[str]:
    """Leitet <name> aus /mnt/projects/<name>/... ab."""
    try:
        rel = os.path.relpath(path, PROJECTS_DIR)
    except ValueError:
        return None
    if rel.startswith(".."):
        return None
    first = rel.split(os.sep, 1)[0]
    if not first or first.startswith("."):
        return None
    return first


def _read_frontmatter(content: str) -> dict:
    """Minimaler YAML-Frontmatter-Parser (nur draft/archived/project/kind)."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    block = content[3:end]
    result: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip().strip("\"'")
        if not key:
            continue
        if value.lower() in ("true", "false"):
            result[key] = value.lower() == "true"
        else:
            result[key] = value
    return result


def _read_file_safe(path: str) -> Optional[tuple[str, str, float]]:
    """Liest Datei sicher; (content, md5_hex, mtime) oder None bei Fehler/zu gross."""
    try:
        st = os.stat(path)
    except OSError as exc:
        logger.warning("plan_scan_file_error path=%s error=%s", path, exc)
        return None
    if st.st_size > MAX_FILE_SIZE:
        logger.info(
            "plan_scan_skipped_large path=%s size=%d limit=%d",
            path, st.st_size, MAX_FILE_SIZE,
        )
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as exc:
        logger.warning("plan_scan_file_error path=%s error=%s", path, exc)
        return None
    md5 = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()
    return content, md5, st.st_mtime


# ---------------------------------------------------------------------------
# Exclusion-Laden und -Matching
# ---------------------------------------------------------------------------

def load_exclusions() -> list[dict]:
    """Lädt alle plan_scan_exclusions aus DB."""
    try:
        ensure_plan_scan_exclusions_schema()
        rows = execute(
            "SELECT id, project_name, path_pattern, scope FROM plan_scan_exclusions",
            fetch=True,
        )
        return [dict(r) for r in (rows or [])]
    except Exception as exc:  # noqa: BLE001 — defensiver Read, Scan geht weiter
        logger.warning("plan_scan_exclusions_load_error error=%s", exc)
        return []


def is_excluded(
    relative_path: str, project_name: Optional[str], exclusions: list[dict]
) -> Optional[str]:
    """Prueft, ob relative_path gegen eine Exclusion matcht.

    - Globale Exclusion (project_name IS NULL) greift fuer alle Projekte
    - Projekt-spezifische Exclusion greift nur beim gleichen project_name
    Rueckgabe: path_pattern des ersten Treffers oder None.
    """
    norm = relative_path.replace(os.sep, "/")
    for exc in exclusions:
        exc_project = exc.get("project_name")
        if exc_project and exc_project != project_name:
            continue
        pattern = exc.get("path_pattern")
        if not pattern:
            continue
        if fnmatch.fnmatchcase(norm, pattern):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Scan-Iteratoren pro Quelle
# ---------------------------------------------------------------------------

def _known_projects() -> list[str]:
    """Liefert sichtbare Nicht-Dotfile-Ordner unter PROJECTS_DIR."""
    try:
        names = []
        for entry in os.scandir(PROJECTS_DIR):
            if not entry.is_dir(follow_symlinks=False):
                continue
            if entry.name.startswith("."):
                continue
            if entry.name in BLACKLIST_DIRS:
                continue
            # Nachtrag 1: Projekt-Whitelist per project.json ODER
            # sichtbarer Nicht-Dotfile-Ordner. Wir akzeptieren beide.
            names.append(entry.name)
        return sorted(names)
    except OSError as exc:
        logger.warning("plan_scan_projects_dir_error error=%s", exc)
        return []


def _iter_dir_markdown(root: str, max_depth: int) -> Iterator[str]:
    """Yieldt *.md-Pfade unter root bis max_depth. scandir + Blacklist."""
    if not os.path.isdir(root):
        return
    stack: list[tuple[str, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            logger.warning("plan_scan_dir_error path=%s error=%s", current, exc)
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    # Symlinks lassen wir zu; realpath wird in _make_entry kanonisiert.
                    pass
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in BLACKLIST_DIRS:
                        continue
                    if entry.name.startswith("."):
                        continue
                    if depth + 1 > max_depth:
                        continue
                    stack.append((entry.path, depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    if entry.name.lower().endswith(".md"):
                        yield entry.path
            except OSError as exc:
                logger.warning("plan_scan_entry_error path=%s error=%s", entry.path, exc)


def _iter_claude_plans() -> Iterator[tuple[str, str, Optional[str]]]:
    """Yieldt (path, source_kind, project_name) fuer ~/.claude/plans/*.md."""
    for path in _iter_dir_markdown(CLAUDE_PLANS_DIR, max_depth=1):
        yield path, "claude_plans", None


def _iter_project_source(project: str, subdir: str, kind: str,
                         max_depth: int) -> Iterator[tuple[str, str, Optional[str]]]:
    root = os.path.join(PROJECTS_DIR, project, subdir)
    for path in _iter_dir_markdown(root, max_depth=max_depth):
        yield path, kind, project


def _iter_project_root(project: str) -> Iterator[tuple[str, str, Optional[str]]]:
    root = os.path.join(PROJECTS_DIR, project)
    for name in PLAN_ROOT_FILENAMES:
        candidate = os.path.join(root, name)
        if os.path.isfile(candidate):
            yield candidate, "project_root", project


def _iter_all_sources() -> Iterator[tuple[str, str, Optional[str]]]:
    yield from _iter_claude_plans()
    for project in _known_projects():
        yield from _iter_project_source(project, "sprints", "project_sprints", MAX_DEPTH)
        yield from _iter_project_source(project, "plans", "project_plans", MAX_DEPTH)
        yield from _iter_project_source(project, "docs/plans", "project_docs", MAX_DEPTH)
        yield from _iter_project_source(project, "docs/sprints", "project_docs", MAX_DEPTH)
        yield from _iter_project_root(project)


# ---------------------------------------------------------------------------
# Ergebnis-Builder + Public API
# ---------------------------------------------------------------------------

def _make_entry(path: str, source_kind: str, project_name: Optional[str],
                exclusions: list[dict], seen: set[str]) -> Optional[dict]:
    """Baut Ergebnis-Dict fuer eine Datei. Gibt None zurueck, wenn keine
    Plan-Datei, nicht lesbar, zu gross oder als draft/archived markiert."""
    try:
        real_path = os.path.realpath(path)
    except OSError as exc:
        logger.warning("plan_scan_realpath_error path=%s error=%s", path, exc)
        return None
    if real_path in seen:
        return None

    # Symlink-Sanity: realpath kann in ein anderes Projekt zeigen als der
    # ursprueng­liche Iterator-Pfad. In dem Fall gilt die Zuordnung aus realpath.
    real_project = _extract_project_name(real_path)
    if real_project is not None:
        project_name = real_project

    data = _read_file_safe(real_path)
    if data is None:
        seen.add(real_path)
        return None
    content, content_hash, mtime = data

    filename = os.path.basename(real_path)
    if not _is_plan_file(filename, content):
        seen.add(real_path)
        return None

    frontmatter = _read_frontmatter(content)
    if frontmatter.get("draft") is True or frontmatter.get("archived") is True:
        seen.add(real_path)
        return None

    # Relative Pfad-Berechnung fuer Exclusion-Matching
    if project_name:
        project_root = os.path.join(PROJECTS_DIR, project_name)
        try:
            rel_for_exclusion = os.path.relpath(real_path, project_root)
        except ValueError:
            rel_for_exclusion = real_path
    else:
        # Globale Plaene (claude_plans): Pattern matcht gegen Filename
        rel_for_exclusion = filename

    excluded_by = is_excluded(rel_for_exclusion, project_name, exclusions)

    seen.add(real_path)
    return {
        "source_path": real_path,
        "source_kind": source_kind,
        "filename": filename,
        "project_name": project_name,
        "frontmatter": frontmatter,
        "content": content,
        "content_hash": content_hash,
        "mtime": mtime,
        "excluded_by": excluded_by,
    }


def discover_plans(
    exclusions: Optional[list[dict]] = None,
    use_cache: bool = False,
) -> list[dict]:
    """Iteriert ueber alle Scan-Quellen und liefert Plan-Metadaten.

    - `exclusions`: wenn None, werden Exclusions einmalig aus DB geladen
    - `use_cache`: wenn True, liefert gecachtes Ergebnis innerhalb
      PREVIEW_CACHE_TTL_SEC zurueck (fuer Scan-Preview-UI)

    Rueckgabe-Dicts: source_path, source_kind, filename, project_name,
    frontmatter, content, content_hash, mtime, excluded_by.
    Excluded-Dateien erscheinen mit `excluded_by != None` fuer UI-Transparenz.
    """
    if use_cache:
        with _preview_lock:
            now = time.monotonic()
            if (_preview_cache["result"] is not None
                    and now - _preview_cache["at"] < PREVIEW_CACHE_TTL_SEC):
                return list(_preview_cache["result"])

    if exclusions is None:
        exclusions = load_exclusions()

    results: list[dict] = []
    seen: set[str] = set()
    started = time.monotonic()

    for path, kind, project in _iter_all_sources():
        try:
            entry = _make_entry(path, kind, project, exclusions, seen)
            if entry is not None:
                results.append(entry)
        except Exception as exc:  # noqa: BLE001
            logger.warning("plan_scan_file_error path=%s error=%s", path, exc)

    duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "plan_scan discover files=%d seen=%d excluded=%d duration_ms=%d",
        len(results), len(seen),
        sum(1 for r in results if r.get("excluded_by")),
        duration_ms,
    )

    if use_cache:
        with _preview_lock:
            _preview_cache["at"] = time.monotonic()
            _preview_cache["result"] = list(results)

    return results
