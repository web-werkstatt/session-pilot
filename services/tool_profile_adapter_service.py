"""ADR-001 Prio 6: Tool Profile Adapter Service.

Pflegt `DASHBOARD-GENERATED`-Bloecke in `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`
fuer bestehende Projekte. Ersetzt nur markierte Bereiche, manueller Text
bleibt geschuetzt. Nutzt `block_marker_parser` fuer Parsing und
`write_guard.safe_write` fuer spaetere Updates.

Bootstrap-Pfad: Beim ersten Regenerate haengt der Service den
`DASHBOARD-GENERATED`-Block am Ende der Datei an. Da
`write_guard.validate_write` unter `GENERATED_BLOCKS_ONLY`-Policy
Einfuegungen ausserhalb bestehender generated Bloecke ablehnt, wird
fuer diesen Erst-Setup ein Atomic-Write direkt ausgefuehrt (File-Lock,
temp+fsync+rename). Alle Folge-Updates laufen dann zwingend ueber
`safe_write`.
"""
from __future__ import annotations

import difflib
import fcntl
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.block_marker_parser import (
    BlockType,
    GeneratedBlock,
    get_generated_ranges,
    parse_blocks,
)
from services.write_guard import safe_write

log = logging.getLogger(__name__)


WRITER_SOURCE = "tool_profile_adapter"

TOOL_FILES: Dict[str, str] = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "gemini": "GEMINI.md",
}

BLOCK_START_TEMPLATE = (
    "<!-- DASHBOARD-GENERATED:START source={source} updated={updated} -->"
)
BLOCK_END = "<!-- DASHBOARD-GENERATED:END -->"


@dataclass
class ToolUpdateResult:
    """Ergebnis einer Tool-Datei-Aktualisierung."""
    tool: str
    filepath: str
    mode: str  # "bootstrap" | "update" | "noop"
    written: bool
    diff: str = ""
    violations: List[str] = field(default_factory=list)
    error: Optional[str] = None


def build_dashboard_block(
    project_name: str,
    tool: str,
    meta: Optional[Dict[str, Any]] = None,
    *,
    updated: Optional[str] = None,
) -> str:
    """Baut den vollstaendigen DASHBOARD-GENERATED-Block als Markdown.

    Der Block ist deterministisch: bei gleichem project_name, tool, meta
    und updated kommt derselbe Text raus. `updated` wird vom Aufrufer
    kontrolliert, damit Idempotenz-Tests stabil bleiben.
    """
    ts = updated or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = meta or {}

    lines: List[str] = [
        BLOCK_START_TEMPLATE.format(source=WRITER_SOURCE, updated=ts),
        "## Project Dashboard Snapshot",
        "",
        f"Dieser Block wird vom Project Dashboard gepflegt (Quelle: `{WRITER_SOURCE}`).",
        "Manuell geschriebener Text ausserhalb dieser Marker bleibt unveraendert.",
        "",
        f"- Projekt: `{project_name}`",
        f"- Tool: `{tool}`",
    ]

    project_type = meta.get("type")
    if project_type:
        lines.append(f"- Typ: `{project_type}`")

    description = meta.get("description")
    if description:
        lines.append(f"- Beschreibung: {description}")

    marker_count = meta.get("marker_count")
    if marker_count is not None:
        lines.append(f"- Aktive Marker: {marker_count}")

    plan_count = meta.get("plan_count")
    if plan_count is not None:
        lines.append(f"- Plans: {plan_count}")

    quality_score = meta.get("quality_score")
    if quality_score is not None:
        lines.append(f"- Quality Score: {quality_score}")

    lines.extend([
        "",
        f"- Stand: {ts}",
        BLOCK_END,
    ])

    return "\n".join(lines)


def _find_our_block(filepath: str) -> Optional[GeneratedBlock]:
    """Sucht den vom Adapter erzeugten DASHBOARD-GENERATED-Block."""
    if not os.path.exists(filepath):
        return None

    for block in get_generated_ranges(filepath):
        if block.source == WRITER_SOURCE:
            return block
    return None


def _read_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        return ""
    with open(filepath, "r", encoding="utf-8") as fh:
        return fh.read()


def _compose_content(old_content: str, new_block: str, existing: Optional[GeneratedBlock]) -> str:
    """Ersetzt einen vorhandenen Block oder haengt ihn am Ende an."""
    new_block = new_block.rstrip("\n")

    if existing is None:
        if not old_content:
            return new_block + "\n"

        if old_content.endswith("\n"):
            sep = "" if old_content.endswith("\n\n") else "\n"
            return old_content + sep + new_block + "\n"
        return old_content + "\n\n" + new_block + "\n"

    lines = old_content.splitlines(keepends=True)
    before = "".join(lines[: existing.start_line - 1])
    after = "".join(lines[existing.end_line - 1:])
    replacement = new_block + ("\n" if not new_block.endswith("\n") else "")

    if before and not before.endswith("\n"):
        before += "\n"

    return before + replacement + after


def _bootstrap_atomic_write(filepath: str, content: str) -> None:
    """Schreibt die Datei ohne Write-Guard-Validierung.

    Nur zulaessig fuer den Erst-Setup, wenn noch kein DASHBOARD-GENERATED-Block
    mit Source `tool_profile_adapter` existiert. Nutzt File-Lock + temp+fsync+
    rename wie `write_guard.safe_write`, damit halbgeschriebene Dateien und
    Races ausgeschlossen sind.
    """
    target_dir = os.path.dirname(filepath) or "."
    os.makedirs(target_dir, exist_ok=True)

    lock_path = filepath + ".lock"
    tmp_fd: Optional[int] = None
    tmp_path: Optional[str] = None

    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # TOCTOU-Schutz: Falls zwischen Pruefung und Lock ein anderer
        # Schreiber einen DASHBOARD-GENERATED-Block mit passender Source
        # eingefuegt hat, darf der Bootstrap-Pfad nicht mehr laufen.
        if _find_our_block(filepath) is not None:
            raise RuntimeError(
                "Bootstrap abgebrochen: DASHBOARD-GENERATED-Block existiert "
                "bereits (wurde zwischen Pruefung und Lock erzeugt). "
                "Bitte Update-Pfad via safe_write verwenden."
            )

        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=target_dir, prefix=".tool_profile_adapter_", suffix=".tmp"
        )
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            tmp_fd = None
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())

        if os.path.exists(filepath):
            st = os.stat(filepath)
            os.chmod(tmp_path, st.st_mode)

        os.replace(tmp_path, filepath)
        tmp_path = None

        log.info(
            "Bootstrap-Write: %s (Source: %s)", filepath, WRITER_SOURCE
        )
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
        try:
            os.unlink(lock_path)
        except OSError:
            pass
        if tmp_fd is not None:
            os.close(tmp_fd)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _compute_diff(old_content: str, new_content: str, filepath: str) -> str:
    """Unified Diff fuer Preview/Logging. Leerer String wenn identisch."""
    if old_content == new_content:
        return ""
    rel = os.path.basename(filepath)
    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{rel}",
        tofile=f"b/{rel}",
        n=3,
    )
    return "".join(diff)


def preview_update(
    project_path: str,
    tool: str,
    project_name: str,
    meta: Optional[Dict[str, Any]] = None,
    *,
    updated: Optional[str] = None,
) -> ToolUpdateResult:
    """Dry-Run: berechnet den geplanten Inhalt und Diff, ohne zu schreiben."""
    if tool not in TOOL_FILES:
        return ToolUpdateResult(
            tool=tool,
            filepath="",
            mode="noop",
            written=False,
            error=f"Unbekanntes Tool: {tool}",
        )

    filepath = os.path.join(project_path, TOOL_FILES[tool])
    old_content = _read_file(filepath)
    existing = _find_our_block(filepath)
    new_block = build_dashboard_block(project_name, tool, meta, updated=updated)
    new_content = _compose_content(old_content, new_block, existing)

    diff = _compute_diff(old_content, new_content, filepath)
    mode = "noop" if not diff else ("update" if existing is not None else "bootstrap")

    return ToolUpdateResult(
        tool=tool,
        filepath=filepath,
        mode=mode,
        written=False,
        diff=diff,
    )


def apply_update(
    project_path: str,
    tool: str,
    project_name: str,
    meta: Optional[Dict[str, Any]] = None,
    *,
    updated: Optional[str] = None,
) -> ToolUpdateResult:
    """Schreibt den DASHBOARD-GENERATED-Block (Bootstrap oder Update).

    Bootstrap-Pfad (Atomic-Write ohne Guard-Validierung) kommt nur zum
    Einsatz, wenn noch kein Block mit passender Source existiert. Alle
    weiteren Updates laufen ueber `write_guard.safe_write`.
    """
    result = preview_update(project_path, tool, project_name, meta, updated=updated)
    if result.error or result.mode == "noop":
        return result

    old_content = _read_file(result.filepath)
    existing = _find_our_block(result.filepath)
    new_block = build_dashboard_block(project_name, tool, meta, updated=updated)
    new_content = _compose_content(old_content, new_block, existing)

    _guard_protected_unchanged(result.filepath, old_content, new_content)

    if existing is None:
        try:
            _bootstrap_atomic_write(result.filepath, new_content)
            result.written = True
            result.mode = "bootstrap"
        except Exception as exc:  # pragma: no cover - nur fuer Logging
            result.error = str(exc)
            result.written = False
        return result

    write_result = safe_write(result.filepath, new_content, WRITER_SOURCE)
    result.written = write_result.allowed
    result.violations = [v.description for v in write_result.violations]
    if not write_result.allowed:
        result.error = write_result.protected_diff or "Write-Guard hat abgelehnt"
    return result


def _guard_protected_unchanged(
    filepath: str, old_content: str, new_content: str
) -> None:
    """Stellt sicher, dass kein MANUAL/UNMARKED-Block veraendert wurde.

    Bootstrap umgeht `write_guard`, also fangen wir den Fall hier selbst.
    """
    if not old_content:
        return

    old_blocks = parse_blocks(filepath)
    protected_line_count = 0
    for block in old_blocks:
        if block.block_type in (BlockType.MANUAL, BlockType.UNMARKED):
            protected_line_count += block.end_line - block.start_line

    if protected_line_count == 0:
        return

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    # Alle geschuetzten Zeilen muessen unveraendert im neuen Inhalt erscheinen.
    protected_ranges: List[Tuple[int, int]] = []
    for block in old_blocks:
        if block.block_type in (BlockType.MANUAL, BlockType.UNMARKED):
            protected_ranges.append((block.start_line, block.end_line))

    for start, end in protected_ranges:
        original = "".join(old_lines[start - 1: end - 1])
        if original and original not in "".join(new_lines):
            raise RuntimeError(
                "Adapter-Bootstrap haette manuellen Inhalt angefasst "
                f"(Zeilen {start}-{end - 1} in {os.path.basename(filepath)})."
            )


def regenerate_all(
    project_path: str,
    project_name: str,
    meta: Optional[Dict[str, Any]] = None,
    *,
    updated: Optional[str] = None,
    dry_run: bool = False,
) -> List[ToolUpdateResult]:
    """Pflegt DASHBOARD-GENERATED-Bloecke in allen drei Tool-Dateien."""
    runner = preview_update if dry_run else apply_update
    results: List[ToolUpdateResult] = []
    for tool in TOOL_FILES:
        results.append(
            runner(project_path, tool, project_name, meta, updated=updated)
        )
    return results
