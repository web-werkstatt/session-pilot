"""
CWO Sprint Ticket 1.2: Context Collector.

Sammelt Analyse-Kontext pro Projekt zu einem rein beschreibenden Snapshot.
Der Collector urteilt nicht — die Checks (Ticket 1.3-1.5) urteilen.

Gesammelte Daten:
- Tool-Files (CLAUDE.md, AGENTS.md, GEMINI.md): Zeilen, Sektionen, Tokens
- next-session.md: Zeilen, Tokens
- marker-context.md: Fokusauftrag-Dateien
- Unterverzeichnis-CLAUDE.md: vorhandene + qualifizierte Verzeichnisse
- Globale Rules (~/.claude/rules/): Dateiliste + Inhalt fuer Duplikat-Check
- Token-Gesamtschaetzung
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from services.context_window_optimizer.constants import (
    GLOBAL_RULES_DIR,
    SCHEMA_VERSION,
    SUBDIR_QUALIFYING_FILES,
    TOKEN_FACTOR_MARKDOWN,
    TOOL_FILES,
)

log = logging.getLogger(__name__)

# Dateierweiterungen die als "relevant" fuer ein Verzeichnis zaehlen
_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".scss",
    ".html", ".astro", ".vue", ".svelte",
}

# Verzeichnisse die bei Unterverz.-CLAUDE.md-Suche uebersprungen werden
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", ".cache", ".mypy_cache",
}


def build_cwo_context(project_name: str) -> Optional[Dict[str, Any]]:
    """Sammelt CWO-Analyse-Kontext fuer ein Projekt.

    Returns:
        Context-Dict oder None wenn Projekt nicht existiert.
    """
    from services.path_resolver import resolve_project_path

    project_path = resolve_project_path(project_name)
    if not project_path:
        return None

    tool_files = _collect_tool_files(project_path)
    next_session = _collect_file_info(
        os.path.join(project_path, "next-session.md")
    )
    focus_files = _collect_focus_files(project_path)
    subdir_claude = _collect_subdir_claude_md(project_path)
    global_rules = _collect_global_rules()
    sections = _collect_claude_md_sections(project_path)

    total_tokens = _estimate_total_tokens(
        tool_files, next_session, subdir_claude, global_rules
    )

    context = {
        "schema_version": SCHEMA_VERSION,
        "project_name": project_name,
        "project_path": project_path,
        "tool_files": tool_files,
        "next_session": next_session,
        "focus_files": focus_files,
        "subdir_claude_md": subdir_claude,
        "global_rules": global_rules,
        "claude_md_sections": sections,
        "total_tokens": total_tokens,
    }
    context["context_hash"] = _compute_context_hash(context)
    return context


# --- Tool-Files ---

def _collect_tool_files(project_path: str) -> Dict[str, Dict[str, Any]]:
    """Sammelt Infos zu CLAUDE.md, AGENTS.md, GEMINI.md."""
    result = {}
    for key, filename in TOOL_FILES.items():
        filepath = os.path.join(project_path, filename)
        result[key] = _collect_file_info(filepath)
    return result


def _collect_file_info(filepath: str) -> Dict[str, Any]:
    """Liest eine Datei und gibt Basis-Infos zurueck."""
    if not os.path.exists(filepath):
        return {"exists": False, "path": filepath, "lines": 0, "tokens": 0}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        log.warning("Konnte Datei nicht lesen: %s (%s)", filepath, e)
        return {
            "exists": True, "path": filepath,
            "lines": 0, "tokens": 0, "read_error": str(e),
        }

    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    tokens = lines * TOKEN_FACTOR_MARKDOWN
    return {
        "exists": True,
        "path": filepath,
        "lines": lines,
        "tokens": tokens,
        "content": content,
    }


# --- Fokusauftrag-Dateien ---

def _collect_focus_files(project_path: str) -> List[Dict[str, Any]]:
    """Erkennt Dateien die im marker-context.md referenziert werden."""
    mc_path = os.path.join(project_path, "marker-context.md")
    if not os.path.exists(mc_path):
        return []

    try:
        with open(mc_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return []

    # Einfache Heuristik: Dateipfade in Backticks oder nach Doppelpunkt
    referenced = []
    for line in content.splitlines():
        # Suche nach relativen Pfaden wie `sprints/foo.md` oder `services/bar.py`
        for token in line.split():
            cleaned = token.strip("`'\",()[]")
            if ("/" in cleaned or cleaned.endswith(".md")) and not cleaned.startswith("http"):
                full_path = os.path.join(project_path, cleaned)
                if os.path.isfile(full_path):
                    info = _collect_file_info(full_path)
                    info["reference"] = cleaned
                    referenced.append(info)

    return referenced


# --- Unterverzeichnis-CLAUDE.md ---

def _collect_subdir_claude_md(project_path: str) -> Dict[str, Any]:
    """Findet vorhandene und fehlende Unterverzeichnis-CLAUDE.md Dateien."""
    existing = []
    qualifying_without = []

    try:
        entries = sorted(os.listdir(project_path))
    except OSError:
        return {"existing": [], "qualifying_without": []}

    for entry in entries:
        if entry.startswith(".") or entry in _SKIP_DIRS:
            continue
        subdir = os.path.join(project_path, entry)
        if not os.path.isdir(subdir):
            continue

        claude_md = os.path.join(subdir, "CLAUDE.md")
        relevant_count = _count_relevant_files(subdir)

        if os.path.isfile(claude_md):
            info = _collect_file_info(claude_md)
            info["dir_name"] = entry
            info["relevant_files"] = relevant_count
            existing.append(info)
        elif relevant_count >= SUBDIR_QUALIFYING_FILES:
            qualifying_without.append({
                "dir_name": entry,
                "relevant_files": relevant_count,
                "path": claude_md,
            })

    return {"existing": existing, "qualifying_without": qualifying_without}


def _count_relevant_files(directory: str) -> int:
    """Zaehlt relevante Code-/Config-Dateien in einem Verzeichnis (flach)."""
    count = 0
    try:
        for entry in os.listdir(directory):
            if entry.startswith("."):
                continue
            _, ext = os.path.splitext(entry)
            if ext.lower() in _CODE_EXTENSIONS:
                count += 1
    except OSError:
        pass
    return count


# --- Globale Rules ---

def _collect_global_rules() -> List[Dict[str, Any]]:
    """Sammelt ~/.claude/rules/ Dateien fuer Duplikat-Check."""
    rules_dir = os.path.expanduser(GLOBAL_RULES_DIR)
    if not os.path.isdir(rules_dir):
        return []

    rules = []
    try:
        for entry in sorted(os.listdir(rules_dir)):
            if not entry.endswith(".md"):
                continue
            filepath = os.path.join(rules_dir, entry)
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                rules.append({
                    "filename": entry,
                    "path": filepath,
                    "lines": content.count("\n") + 1,
                    "content": content,
                })
            except OSError:
                continue
    except OSError:
        pass

    return rules


# --- CLAUDE.md Sektions-Analyse ---

def _collect_claude_md_sections(project_path: str) -> List[Dict[str, Any]]:
    """Parst H2-Sektionen aus CLAUDE.md fuer Auslagerbarkeits-Analyse."""
    claude_md = os.path.join(project_path, "CLAUDE.md")
    if not os.path.isfile(claude_md):
        return []

    try:
        with open(claude_md, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    sections: List[Dict[str, Any]] = []
    current_title = None
    current_start = 0
    current_lines: List[str] = []

    for i, line in enumerate(lines):
        if line.startswith("## "):
            if current_title is not None:
                sections.append(_build_section(
                    current_title, current_start, i, current_lines
                ))
            current_title = line.strip("# \n")
            current_start = i + 1
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    # Letzte Sektion
    if current_title is not None:
        sections.append(_build_section(
            current_title, current_start, len(lines), current_lines
        ))

    return sections


def _build_section(
    title: str, start: int, end: int, lines: List[str]
) -> Dict[str, Any]:
    """Erstellt Sektions-Info mit Listen-Element-Zaehlung."""
    list_items = sum(1 for l in lines if l.strip().startswith(("- ", "* ", "| ")))
    line_count = end - start
    return {
        "title": title,
        "start_line": start,
        "end_line": end,
        "lines": line_count,
        "tokens": line_count * TOKEN_FACTOR_MARKDOWN,
        "list_items": list_items,
        "is_list_heavy": list_items > (line_count * 0.6) if line_count > 0 else False,
    }


# --- Token-Schaetzung ---

def _estimate_total_tokens(
    tool_files: Dict[str, Dict[str, Any]],
    next_session: Dict[str, Any],
    subdir_claude: Dict[str, Any],
    global_rules: List[Dict[str, Any]],
) -> int:
    """Schaetzt den Gesamt-Token-Verbrauch beim Session-Start."""
    total = 0

    # Tool-Files (always loaded)
    for info in tool_files.values():
        total += info.get("tokens", 0)

    # next-session.md (always loaded, falls referenziert)
    total += next_session.get("tokens", 0)

    # Unterverz.-CLAUDE.md (auto_subdir, anteilig schaetzen: ~30% werden geladen)
    for info in subdir_claude.get("existing", []):
        total += int(info.get("tokens", 0) * 0.3)

    # Globale Rules (always loaded)
    for rule in global_rules:
        total += rule.get("lines", 0) * TOKEN_FACTOR_MARKDOWN

    return total


# --- Context-Hash ---

def _compute_context_hash(context: Dict[str, Any]) -> str:
    """Berechnet einen Hash ueber die wesentlichen Context-Daten fuer Dedup."""
    parts = []
    for key in ("claude", "codex", "gemini"):
        info = context.get("tool_files", {}).get(key, {})
        parts.append(f"{key}:{info.get('lines', 0)}")
    parts.append(f"ns:{context.get('next_session', {}).get('lines', 0)}")
    parts.append(f"tokens:{context.get('total_tokens', 0)}")
    parts.append(f"subdir:{len(context.get('subdir_claude_md', {}).get('existing', []))}")
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
