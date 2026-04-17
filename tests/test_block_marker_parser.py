"""
Tests für services/block_marker_parser.py
"""
import os
import tempfile
import pytest

from services.block_marker_parser import (
    Block, BlockType, parse_blocks, get_protected_ranges,
    get_generated_ranges, is_file_protected
)


def test_parse_blocks_empty_file():
    """Test mit leerer Datei."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("")
        f.flush()
        
        blocks = parse_blocks(f.name)
        os.unlink(f.name)
        
        # Leere Datei = ein unmarkierter Block
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.UNMARKED
        assert blocks[0].start_line == 1
        assert blocks[0].end_line == 1  # leer


def test_parse_blocks_unmarked_content():
    """Test mit unmarkiertem Inhalt."""
    content = """# Titel

Hier ist etwas Text.

- Liste
- Zweiter Punkt
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        blocks = parse_blocks(f.name)
        os.unlink(f.name)
        
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.UNMARKED
        assert blocks[0].start_line == 1
        # f.readlines() ohne trailing newline am Ende
        assert blocks[0].end_line == 7  # 7 Zeilen total, end_line ist exklusive


def test_parse_blocks_manual_block():
    """Test mit MANUAL-Block."""
    content = """Vorher Text

<!-- MANUAL:START owner=joseph -->
Hier ist manueller Inhalt
der geschützt sein sollte.
<!-- MANUAL:END -->

Nachher Text
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        blocks = parse_blocks(f.name)
        os.unlink(f.name)
        
        # 3 Blöcke: unmarked, manual, unmarked
        assert len(blocks) == 3
        
        # Erster Block: unmarked (Zeilen 1-2)
        assert blocks[0].block_type == BlockType.UNMARKED
        assert blocks[0].start_line == 1
        assert blocks[0].end_line == 3  # bis zur MANUAL:START Zeile
        
        # Zweiter Block: manual (Zeilen 3-6)
        assert blocks[1].block_type == BlockType.MANUAL
        assert blocks[1].start_line == 3
        assert blocks[1].end_line == 7  # bis zur MANUAL:END Zeile
        assert blocks[1].owner == "joseph"
        
        # Dritter Block: unmarked (Zeilen 7-8)
        assert blocks[2].block_type == BlockType.UNMARKED
        assert blocks[2].start_line == 7
        assert blocks[2].end_line == 9  # bis zum Ende


def test_parse_blocks_dashboard_generated():
    """Test mit DASHBOARD-GENERATED-Block."""
    content = """# Datei mit generiertem Block

<!-- DASHBOARD-GENERATED:START source=tool_profile_adapter updated=2026-04-10 -->
Dieser Inhalt wird vom Dashboard generiert.
Er kann ueberschrieben werden.
<!-- DASHBOARD-GENERATED:END -->

Manueller Text danach.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        blocks = parse_blocks(f.name)
        os.unlink(f.name)
        
        # 3 Blöcke: unmarked, generated, unmarked
        assert len(blocks) == 3
        
        # Generated Block
        assert blocks[1].block_type == BlockType.DASHBOARD_GENERATED
        assert blocks[1].source == "tool_profile_adapter"
        assert blocks[1].updated == "2026-04-10"


def test_parse_blocks_multiple_blocks():
    """Test mit mehreren Blöcken."""
    content = """Vorher

<!-- MANUAL:START owner=team -->
Manuell 1
<!-- MANUAL:END -->

<!-- DASHBOARD-GENERATED:START source=service_a -->
Generiert A
<!-- DASHBOARD-GENERATED:END -->

<!-- MANUAL:START -->
Manuell 2 ohne owner
<!-- MANUAL:END -->

Nachher
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        blocks = parse_blocks(f.name)
        os.unlink(f.name)
        
        # 7 Blöcke wegen Leerzeilen zwischen Blöcken: 
        # unmarked, manual, unmarked (Leerzeile), generated, unmarked (Leerzeile), manual, unmarked
        assert len(blocks) == 7
        
        # Prüfe Reihenfolge und Typen
        types = [b.block_type for b in blocks]
        assert types == [
            BlockType.UNMARKED,           # Vorher + Leerzeile
            BlockType.MANUAL,             # MANUAL Block 1
            BlockType.UNMARKED,           # Leerzeile zwischen Blöcken
            BlockType.DASHBOARD_GENERATED, # GENERATED Block
            BlockType.UNMARKED,           # Leerzeile zwischen Blöcken
            BlockType.MANUAL,             # MANUAL Block 2
            BlockType.UNMARKED            # Nachher
        ]


def test_get_protected_ranges():
    """Test für geschützte Bereiche."""
    content = """Vorher

<!-- MANUAL:START -->
Geschützt
<!-- MANUAL:END -->

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->

Nachher unmarkiert
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        protected = get_protected_ranges(f.name)
        os.unlink(f.name)
        
        # Geschützte Bereiche: Vorher (Zeilen 1-3), Manual (Zeilen 3-6), Leerzeile (6-7), Nachher (10-12)
        assert len(protected) == 4
        
        # Vorher: Zeilen 1-3
        assert protected[0] == (1, 3)
        # Manual: Zeilen 3-6
        assert protected[1] == (3, 6)
        # Leerzeile: Zeilen 6-7
        assert protected[2] == (6, 7)
        # Nachher: Zeilen 10-12
        assert protected[3] == (10, 12)


def test_get_generated_ranges():
    """Test für generierte Bereiche."""
    content = """Vorher

<!-- DASHBOARD-GENERATED:START source=service_a updated=2026-04-10 -->
Generiert A
<!-- DASHBOARD-GENERATED:END -->

Mitte

<!-- DASHBOARD-GENERATED:START source=service_b -->
Generiert B
<!-- DASHBOARD-GENERATED:END -->

Nachher
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()
        
        generated = get_generated_ranges(f.name)
        os.unlink(f.name)
        
        assert len(generated) == 2
        
        # Erster Block
        assert generated[0].source == "service_a"
        assert generated[0].updated == "2026-04-10"
        
        # Zweiter Block
        assert generated[1].source == "service_b"
        assert generated[1].updated is None  # kein updated Attribut


def test_is_file_protected():
    """Test für Dateischutz-Prüfung."""
    # Datei mit geschützten Bereichen
    content1 = """Manueller Inhalt
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content1)
        f.flush()
        assert is_file_protected(f.name) == True
        os.unlink(f.name)
    
    # Datei nur mit generiertem Block
    content2 = """<!-- DASHBOARD-GENERATED:START source=service -->
Inhalt
<!-- DASHBOARD-GENERATED:END -->
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content2)
        f.flush()
        # Keine geschützten Bereiche, nur generierter Block
        assert is_file_protected(f.name) == False
        os.unlink(f.name)


def test_malformed_blocks_fail_closed():
    """Test: Ungeschlossener Block fuehrt zu fail-closed (gesamte Datei geschuetzt)."""
    content = """Vorher

<!-- MANUAL:START -->
Nicht geschlossen
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        blocks = parse_blocks(f.name)
        os.unlink(f.name)

        # Fail-closed: Gesamte Datei als ein MANUAL-Block
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.MANUAL
        assert blocks[0].owner == "__malformed__"
        assert blocks[0].start_line == 1


def test_malformed_dashboard_block_fail_closed():
    """Test: Ungeschlossener DASHBOARD-GENERATED-Block ist auch fail-closed."""
    content = """# Header

<!-- DASHBOARD-GENERATED:START source=service -->
Offen geblieben
Noch mehr Text
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        blocks = parse_blocks(f.name)
        os.unlink(f.name)

        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.MANUAL
        assert blocks[0].owner == "__malformed__"


def test_copilot_marker_format_treated_as_unmarked():
    """Test: Echtes handoff.md-Format (<!-- MARKER:XXX -->) wird als UNMARKED erkannt.

    Das Copilot-Marker-Format ist kein MANUAL/DASHBOARD-GENERATED Block,
    daher wird der gesamte Inhalt als ein grosser UNMARKED-Block behandelt.
    """
    content = """---
handoff:
  project_id: "test_project"
---

# Handoff fuer Projekt test_project

## Copilot Markers

<!-- MARKER:42
{
  "marker_id": "42",
  "titel": "Test Marker",
  "status": "in_progress"
}
-->

## Test Marker · in_progress

Nächster Schritt: Testing
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        f.flush()

        blocks = parse_blocks(f.name)
        os.unlink(f.name)

        # Keine MANUAL/DASHBOARD-GENERATED Marker erkannt
        # -> gesamte Datei ist ein UNMARKED-Block
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.UNMARKED
        assert blocks[0].start_line == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])