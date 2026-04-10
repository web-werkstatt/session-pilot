"""
ADR-001 Prio 2: Write-Guard fuer Block-Marker-Schutz.

Prueft Schreiboperationen basierend auf Block-Map und Write-Policies.
"""
import difflib
import fcntl
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Tuple
import logging

from services.block_marker_parser import (
    GeneratedBlock, get_protected_ranges, get_generated_ranges
)

log = logging.getLogger(__name__)


class WritePolicy(Enum):
    """Schreib-Policy fuer eine Datei."""
    APPEND_ONLY = "append-only"  # Nur Anhaengen am Ende erlaubt
    GENERATED_BLOCKS_ONLY = "generated-blocks-only"  # Nur generierte Bloecke duerfen ueberschrieben werden
    EXPLICIT_ONLY = "explicit-only"  # Nur explizit markierte Bereiche duerfen geaendert werden
    # Uebergangs-Policy: Nur bekannte writer_sources duerfen schreiben.
    # Gilt fuer Dateien deren Block-Marker-Format noch nicht migriert ist.
    SOURCE_ALLOWLIST = "source-allowlist"


class ViolationType(Enum):
    """Art der Policy-Verletzung."""
    PROTECTED_AREA_MODIFIED = "protected_area_modified"
    NON_APPEND_WRITE = "non_append_write"
    WRONG_SOURCE = "wrong_source"
    OUTSIDE_GENERATED_BLOCK = "outside_generated_block"


@dataclass
class Violation:
    """Eine Policy-Verletzung."""
    violation_type: ViolationType
    description: str
    line_range: Optional[Tuple[int, int]] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class WriteResult:
    """Ergebnis einer Schreibpruefung."""
    allowed: bool
    violations: List[Violation]
    protected_diff: Optional[str] = None
    policy_applied: Optional[WritePolicy] = None
    file_exists: bool = False


# Zentrale Write-Policy-Registry
WRITE_POLICIES: Dict[str, WritePolicy] = {
    "next-session.md": WritePolicy.APPEND_ONLY,
    # TODO(ADR-001): handoff.md auf GENERATED_BLOCKS_ONLY umstellen,
    # sobald Block-Marker-Migration abgeschlossen ist.
    # Aktuell nutzt handoff.md <!-- MARKER:XXX {...} --> Format,
    # nicht MANUAL/DASHBOARD-GENERATED. Bis dahin: SOURCE_ALLOWLIST.
    "handoff.md": WritePolicy.SOURCE_ALLOWLIST,
    "CLAUDE.md": WritePolicy.GENERATED_BLOCKS_ONLY,
    "AGENTS.md": WritePolicy.GENERATED_BLOCKS_ONLY,
    "GEMINI.md": WritePolicy.GENERATED_BLOCKS_ONLY,
    "marker-context.md": WritePolicy.EXPLICIT_ONLY,
}

# Erlaubte Quellen fuer SOURCE_ALLOWLIST-Policy (Uebergangsphase handoff.md)
HANDOFF_ALLOWED_SOURCES: Dict[str, set] = {
    "handoff.md": {
        "project_handoff_service",
        "copilot_marker_format",
        "copilot_marker_service",
        "marker_importer",
        "workflow_core_service",
    },
}

# Glob-Patterns für Sprints
SPRINTS_PATTERN = "sprints/*.md"


def _get_policy_for_file(filepath: str) -> Optional[WritePolicy]:
    """Ermittelt die Write-Policy fuer eine Datei.

    Args:
        filepath: Vollstaendiger Pfad zur Datei

    Returns:
        WritePolicy oder None wenn keine Policy definiert ist
    """
    filename = os.path.basename(filepath)
    
    # 1. Exakte Dateinamen pruefen
    if filename in WRITE_POLICIES:
        return WRITE_POLICIES[filename]
    
    # 2. Sprints-Pattern pruefen
    dirname = os.path.basename(os.path.dirname(filepath))
    if dirname == "sprints" and filename.endswith(".md"):
        return WritePolicy.APPEND_ONLY
    
    # 3. Keine Policy gefunden
    return None


def _compare_content(old_lines: List[str], new_lines: List[str]) -> List[Tuple[int, int]]:
    """Vergleicht alte und neue Zeilen, gibt geaenderte Bereiche in der alten Datei zurueck.

    Verwendet SequenceMatcher fuer korrekte Erkennung von insert/delete/replace.

    Args:
        old_lines: Alte Zeilen
        new_lines: Neue Zeilen

    Returns:
        Liste von (start_line, end_line) Tupeln (1-basiert, end exklusive)
    """
    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    changed_ranges = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue

        if tag == 'insert':
            # Insertion an Position i1 in der alten Datei.
            # Markiere den Einfuegepunkt (1 Zeile Kontext), damit
            # Overlap-Checks mit geschuetzten Bereichen greifen.
            pos = max(1, i1 + 1)
            changed_ranges.append((pos, pos + 1))
        else:
            # delete oder replace: betroffene Zeilen in der alten Datei
            start = i1 + 1  # 1-basiert
            end = i2 + 1    # exklusive
            if start < end:
                changed_ranges.append((start, end))

    return changed_ranges


def _lines_overlap(range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
    """Prueft ob zwei Zeilenbereiche ueberlappen.

    Args:
        range1: (start, end) exklusive
        range2: (start, end) exklusive

    Returns:
        True wenn die Bereiche ueberlappen
    """
    start1, end1 = range1
    start2, end2 = range2
    return not (end1 <= start2 or end2 <= start1)


def validate_write(filepath: str, new_content: str, writer_source: str) -> WriteResult:
    """Prueft ob der Schreibvorgang erlaubt ist.

    Args:
        filepath: Pfad zur Datei
        new_content: Neuer Inhalt der geschrieben werden soll
        writer_source: Quelle des Schreibvorgangs (z.B. 'tool_profile_adapter')

    Returns:
        WriteResult mit .allowed (bool), .violations (list), .protected_diff (str)
    """
    violations: List[Violation] = []
    
    # 1. Policy ermitteln
    policy = _get_policy_for_file(filepath)
    if policy is None:
        # Keine Policy definiert = Schreiben erlaubt
        return WriteResult(
            allowed=True,
            violations=[],
            policy_applied=None,
            file_exists=os.path.exists(filepath)
        )
    
    # 2. Existiert die Datei?
    file_exists = os.path.exists(filepath)
    if not file_exists:
        # Neue Datei = Schreiben erlaubt
        return WriteResult(
            allowed=True,
            violations=[],
            policy_applied=policy,
            file_exists=False
        )
    
    # 3. Alten Inhalt lesen
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            old_content = f.read()
            old_lines = old_content.splitlines(keepends=True)
    except (IOError, UnicodeDecodeError) as e:
        log.warning(f"Konnte Datei {filepath} nicht lesen: {e}")
        # Wenn Datei nicht lesbar, erlauben wir Schreiben nicht
        return WriteResult(
            allowed=False,
            violations=[Violation(
                ViolationType.PROTECTED_AREA_MODIFIED,
                f"Datei kann nicht gelesen werden: {e}"
            )],
            policy_applied=policy,
            file_exists=True
        )
    
    # 4. Policy-spezifische Pruefungen
    protected_ranges: List[Tuple[int, int]] = []
    generated_blocks: List[GeneratedBlock] = []

    if policy == WritePolicy.APPEND_ONLY:
        # Robuster Prefix-Check: Neuer Inhalt muss mit altem beginnen.
        # Kein Diff noetig — ein einfacher String-Vergleich genuegt.
        if not new_content.startswith(old_content):
            violations.append(Violation(
                ViolationType.NON_APPEND_WRITE,
                "Bestehender Inhalt wurde veraendert (nur Anhaengen am Ende erlaubt)"
            ))

    elif policy == WritePolicy.SOURCE_ALLOWLIST:
        # Uebergangs-Policy: Nur bekannte writer_sources duerfen schreiben.
        # Gilt fuer Dateien deren Block-Marker-Format noch nicht migriert ist
        # (z.B. handoff.md mit <!-- MARKER:XXX --> statt DASHBOARD-GENERATED).
        filename = os.path.basename(filepath)
        allowed_sources = HANDOFF_ALLOWED_SOURCES.get(filename, set())
        if writer_source not in allowed_sources:
            violations.append(Violation(
                ViolationType.WRONG_SOURCE,
                f"Quelle '{writer_source}' nicht in Allowlist fuer {filename}. "
                f"Erlaubt: {', '.join(sorted(allowed_sources))}"
            ))
    
    elif policy == WritePolicy.GENERATED_BLOCKS_ONLY:
        # Veraenderungen berechnen (nur fuer block-basierte Policies)
        new_lines = new_content.splitlines(keepends=True)
        changed_ranges = _compare_content(old_lines, new_lines)

        if not changed_ranges:
            return WriteResult(
                allowed=True, violations=[], policy_applied=policy, file_exists=True
            )

        # Pruefe ob Aenderungen nur in generierten Bloecken sind
        protected_ranges = get_protected_ranges(filepath)
        generated_blocks = get_generated_ranges(filepath)

        for start, end in changed_ranges:
            # Pruefe ob Bereich in geschuetzten Bereichen liegt
            is_protected = any(
                _lines_overlap((start, end), (prot_start, prot_end))
                for prot_start, prot_end in protected_ranges
            )

            if is_protected:
                for prot_start, prot_end in protected_ranges:
                    if _lines_overlap((start, end), (prot_start, prot_end)):
                        violations.append(Violation(
                            ViolationType.PROTECTED_AREA_MODIFIED,
                            f"Aenderung in geschuetzten Zeilen {max(start, prot_start)}-{min(end, prot_end)}",
                            line_range=(max(start, prot_start), min(end, prot_end))
                        ))
                        break

            # Pruefe ob Aenderung in generiertem Block mit passendem source
            in_generated_block = False
            correct_source = False

            for block in generated_blocks:
                if _lines_overlap((start, end), (block.start_line, block.end_line)):
                    in_generated_block = True
                    if block.source == writer_source:
                        correct_source = True
                    break

            if in_generated_block and not correct_source:
                violations.append(Violation(
                    ViolationType.WRONG_SOURCE,
                    f"Aenderung in generiertem Block, aber writer_source='{writer_source}' passt nicht",
                    line_range=(start, end)
                ))
            elif not in_generated_block and not is_protected:
                violations.append(Violation(
                    ViolationType.OUTSIDE_GENERATED_BLOCK,
                    f"Aenderung in nicht-klassifiziertem Bereich {start}-{end}",
                    line_range=(start, end)
                ))

    elif policy == WritePolicy.EXPLICIT_ONLY:
        # Keine Aenderungen erlaubt (marker-context.md)
        if new_content != old_content:
            violations.append(Violation(
                ViolationType.PROTECTED_AREA_MODIFIED,
                "Datei hat explicit-only Policy, Aenderungen nicht erlaubt"
            ))
    
    # 5. Ergebnis zusammenstellen
    allowed = len(violations) == 0

    # Violation-Beschreibungen als Zusammenfassung
    protected_diff = None
    if violations:
        protected_diff = "\n".join(v.description for v in violations)

    return WriteResult(
        allowed=allowed,
        violations=violations,
        protected_diff=protected_diff,
        policy_applied=policy,
        file_exists=True
    )


def safe_write(filepath: str, new_content: str, writer_source: str) -> WriteResult:
    """Schreibt nur wenn validate_write erlaubt. Sonst Fehler mit Erklaerung.

    Verwendet Atomic Write (temp -> fsync -> rename) und File-Lock
    (fcntl.flock), um halbgeschriebene Dateien und Race Conditions
    zu verhindern.

    Args:
        filepath: Pfad zur Datei
        new_content: Neuer Inhalt der geschrieben werden soll
        writer_source: Quelle des Schreibvorgangs

    Returns:
        WriteResult mit dem Ergebnis der Operation
    """
    result = validate_write(filepath, new_content, writer_source)

    if not result.allowed:
        return result

    target_dir = os.path.dirname(filepath) or "."
    lock_path = filepath + ".lock"
    tmp_fd = None
    tmp_path = None

    try:
        os.makedirs(target_dir, exist_ok=True)

        # --- File-Lock: exklusiv, blockierend ---
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Re-Validierung nach Lock-Akquise (TOCTOU-Schutz):
            # Datei koennte sich zwischen validate_write und Lock
            # geaendert haben.
            re_result = validate_write(filepath, new_content, writer_source)
            if not re_result.allowed:
                return re_result

            # --- Atomic Write: temp -> fsync -> rename ---
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=target_dir, prefix=".write_guard_", suffix=".tmp"
            )
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                tmp_fd = None  # fdopen uebernimmt Ownership
                f.write(new_content)
                f.flush()
                os.fsync(f.fileno())

            # Berechtigungen vom Original uebernehmen
            if os.path.exists(filepath):
                st = os.stat(filepath)
                os.chmod(tmp_path, st.st_mode)

            # Atomarer Rename (POSIX-Garantie auf gleichem Filesystem)
            os.replace(tmp_path, filepath)
            tmp_path = None  # Rename war erfolgreich, kein Cleanup noetig

            log.info("Datei geschrieben: %s (Source: %s)", filepath, writer_source)

        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            # Lock-Datei aufräumen (best-effort)
            try:
                os.unlink(lock_path)
            except OSError:
                pass

    except Exception as e:
        log.error("Fehler beim Schreiben von %s: %s", filepath, e)
        result.violations.append(Violation(
            ViolationType.PROTECTED_AREA_MODIFIED,
            f"Schreibfehler: {e}"
        ))
        result.allowed = False
    finally:
        # Aufräumen: Temp-Datei entfernen falls Rename nicht stattfand
        if tmp_fd is not None:
            os.close(tmp_fd)
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return result


def get_policy_summary() -> Dict[str, str]:
    """Gibt eine Zusammenfassung aller definierten Policies zurueck.
    
    Returns:
        Dictionary mit Dateiname -> Policy
    """
    summary = {k: v.value for k, v in WRITE_POLICIES.items()}
    summary[SPRINTS_PATTERN] = WritePolicy.APPEND_ONLY.value
    return summary