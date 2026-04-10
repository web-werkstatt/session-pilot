"""
ADR-001 Prio 2: Block-Marker-Parser fuer MANUAL und DASHBOARD-GENERATED Bloecke.

Erkennt geschuetzte und generierte Bereiche in Markdown-Dateien.
"""
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

log = logging.getLogger(__name__)


class BlockType(Enum):
    """Typ eines erkannten Blocks."""
    MANUAL = "manual"
    DASHBOARD_GENERATED = "dashboard_generated"
    UNMARKED = "unmarked"


@dataclass
class Block:
    """Ein erkanntes Block-Segment."""
    start_line: int  # 1-basiert inklusive
    end_line: int    # 1-basiert exklusive (wie Python slice)
    block_type: BlockType
    source: Optional[str] = None  # nur bei DASHBOARD_GENERATED
    updated: Optional[str] = None  # nur bei DASHBOARD_GENERATED
    owner: Optional[str] = None   # nur bei MANUAL


@dataclass
class GeneratedBlock(Block):
    """Ein generierter Block mit Metadaten."""
    pass


# Regex für MANUAL-Blöcke
MANUAL_START_RE = re.compile(
    r"^<!--\s*MANUAL:START\s+(owner\s*=\s*(?P<owner>[^\s>]+)\s*)?-->$",
    re.IGNORECASE
)
MANUAL_END_RE = re.compile(r"^<!--\s*MANUAL:END\s*-->$", re.IGNORECASE)

# Regex für DASHBOARD-GENERATED-Blöcke
DASHBOARD_START_RE = re.compile(
    r"^<!--\s*DASHBOARD-GENERATED:START\s+"
    r"(source\s*=\s*(?P<source>[^\s>]+)\s+)?"
    r"(updated\s*=\s*(?P<updated>[^\s>]+)\s*)?"
    r"-->$",
    re.IGNORECASE
)
DASHBOARD_END_RE = re.compile(r"^<!--\s*DASHBOARD-GENERATED:END\s*-->$", re.IGNORECASE)


def parse_blocks(filepath: str) -> List[Block]:
    """Erkennt MANUAL und DASHBOARD-GENERATED Bloecke in einer Datei.

    Args:
        filepath: Pfad zur Markdown-Datei

    Returns:
        Liste von Bloecken in der Reihenfolge ihres Auftretens
    """
    blocks = []
    current_block = None
    current_start_line = None
    current_type = None
    current_attrs = {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (IOError, UnicodeDecodeError) as e:
        # Datei existiert nicht oder kann nicht gelesen werden
        return []

    for i, line in enumerate(lines, start=1):
        line = line.rstrip('\n')

        # Prüfe auf MANUAL:START
        manual_start_match = MANUAL_START_RE.match(line)
        if manual_start_match and current_block is None:
            current_block = BlockType.MANUAL
            current_start_line = i
            current_attrs = {"owner": manual_start_match.group("owner")}
            continue

        # Prüfe auf DASHBOARD-GENERATED:START
        dashboard_start_match = DASHBOARD_START_RE.match(line)
        if dashboard_start_match and current_block is None:
            current_block = BlockType.DASHBOARD_GENERATED
            current_start_line = i
            current_attrs = {
                "source": dashboard_start_match.group("source"),
                "updated": dashboard_start_match.group("updated")
            }
            continue

        # Prüfe auf MANUAL:END
        if MANUAL_END_RE.match(line) and current_block == BlockType.MANUAL and current_start_line is not None:
            blocks.append(Block(
                start_line=current_start_line,
                end_line=i + 1,  # End-Line exklusive
                block_type=BlockType.MANUAL,
                owner=current_attrs.get("owner")
            ))
            current_block = None
            current_start_line = None
            current_attrs = {}
            continue

        # Prüfe auf DASHBOARD-GENERATED:END
        if DASHBOARD_END_RE.match(line) and current_block == BlockType.DASHBOARD_GENERATED and current_start_line is not None:
            blocks.append(Block(
                start_line=current_start_line,
                end_line=i + 1,
                block_type=BlockType.DASHBOARD_GENERATED,
                source=current_attrs.get("source"),
                updated=current_attrs.get("updated")
            ))
            current_block = None
            current_start_line = None
            current_attrs = {}
            continue

    # Fail-closed: Ungeschlossener Block = gesamte Datei ist geschuetzt.
    # Ein MANUAL:START oder DASHBOARD-GENERATED:START ohne END bedeutet,
    # dass die Datei-Struktur defekt ist. Statt stillschweigend zu ignorieren
    # (fail-open), behandeln wir die gesamte Datei als einen geschuetzten
    # MANUAL-Block, damit kein Schreibzugriff durchrutscht.
    if current_block is not None:
        log.warning(
            "Ungeschlossener %s-Block ab Zeile %d in %s — "
            "Datei wird als vollstaendig geschuetzt behandelt (fail-closed)",
            current_block.value, current_start_line, filepath
        )
        return [Block(
            start_line=1,
            end_line=len(lines) + 1,
            block_type=BlockType.MANUAL,
            owner="__malformed__"
        )]

    # Unmarkierten Text als UNMARKED-Bloecke hinzufuegen
    if not blocks:
        # Ganze Datei ist unmarkiert = ein großer MANUAL-Block
        blocks.append(Block(
            start_line=1,
            end_line=len(lines) + 1,
            block_type=BlockType.UNMARKED
        ))
    else:
        # Lücken zwischen Blöcken als MANUAL-Blöcke ergänzen
        sorted_blocks = sorted(blocks, key=lambda b: b.start_line)
        final_blocks = []
        last_end = 1

        for block in sorted_blocks:
            if block.start_line > last_end:
                # Lücke gefunden = unmarkierter Text
                final_blocks.append(Block(
                    start_line=last_end,
                    end_line=block.start_line,
                    block_type=BlockType.UNMARKED
                ))
            final_blocks.append(block)
            last_end = block.end_line

        # Rest nach dem letzten Block
        if last_end <= len(lines):
            final_blocks.append(Block(
                start_line=last_end,
                end_line=len(lines) + 1,
                block_type=BlockType.UNMARKED
            ))

        blocks = final_blocks

    return blocks


def get_protected_ranges(filepath: str) -> List[Tuple[int, int]]:
    """Liefert Zeilenbereiche die geschuetzt sind (manuell + unmarkiert).

    Args:
        filepath: Pfad zur Markdown-Datei

    Returns:
        Liste von (start_line, end_line) Tupeln (end_line exklusive)
    """
    blocks = parse_blocks(filepath)
    protected = []

    for block in blocks:
        if block.block_type in (BlockType.MANUAL, BlockType.UNMARKED):
            protected.append((block.start_line, block.end_line))

    return protected


def get_generated_ranges(filepath: str) -> List[GeneratedBlock]:
    """Liefert generierte Bloecke mit source-Attribut.

    Args:
        filepath: Pfad zur Markdown-Datei

    Returns:
        Liste von GeneratedBlock-Objekten
    """
    blocks = parse_blocks(filepath)
    generated = []

    for block in blocks:
        if block.block_type == BlockType.DASHBOARD_GENERATED:
            generated.append(GeneratedBlock(
                start_line=block.start_line,
                end_line=block.end_line,
                block_type=block.block_type,
                source=block.source,
                updated=block.updated
            ))

    return generated


def is_file_protected(filepath: str) -> bool:
    """Prüft ob eine Datei überhaupt geschützte Bereiche hat.

    Args:
        filepath: Pfad zur Datei

    Returns:
        True wenn die Datei existiert und geschützte Bereiche hat
    """
    protected = get_protected_ranges(filepath)
    return len(protected) > 0