"""
Tests fuer write_guard.py: Edge Cases, Fehlermodi, Atomic Write, File-Lock.

Ergaenzt test_write_guard.py um Haertungstests (ADR-001 Prio 2).
"""
import os
import tempfile
import pytest

from services.write_guard import (
    WritePolicy, ViolationType, validate_write, safe_write
)


# --- Edge Cases: Insert / Delete / Prefix-Check ---


def test_append_only_prefix_check_insert_in_middle():
    """Test: APPEND_ONLY erkennt Einfuegung in der Mitte als Verletzung."""
    content = """# Session

Erster Eintrag
Zweiter Eintrag
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """# Session

Erster Eintrag
EINGEFUEGT IN DER MITTE
Zweiter Eintrag
"""
        result = validate_write(temp_path, new_content, "test_source")

        assert result.allowed == False
        assert result.violations[0].violation_type == ViolationType.NON_APPEND_WRITE


def test_append_only_prefix_check_deletion():
    """Test: APPEND_ONLY erkennt Loeschung als Verletzung."""
    content = """# Session

Erster Eintrag
Zweiter Eintrag
Dritter Eintrag
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """# Session

Erster Eintrag
Dritter Eintrag
"""
        result = validate_write(temp_path, new_content, "test_source")

        assert result.allowed == False
        assert result.violations[0].violation_type == ViolationType.NON_APPEND_WRITE


def test_generated_blocks_insert_in_protected_area():
    """Test: Insert in geschuetztem Bereich bei GENERATED_BLOCKS_ONLY wird erkannt."""
    content = """Geschuetzter Text Zeile 1
Geschuetzter Text Zeile 2

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """Geschuetzter Text Zeile 1
EINGEFUEGT
Geschuetzter Text Zeile 2

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->
"""
        result = validate_write(temp_path, new_content, "service")

        assert result.allowed == False
        assert any(v.violation_type == ViolationType.PROTECTED_AREA_MODIFIED
                   for v in result.violations)


def test_generated_blocks_delete_in_protected_area():
    """Test: Delete in geschuetztem Bereich bei GENERATED_BLOCKS_ONLY wird erkannt."""
    content = """Geschuetzter Text Zeile 1
Geschuetzter Text Zeile 2
Geschuetzter Text Zeile 3

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """Geschuetzter Text Zeile 1
Geschuetzter Text Zeile 3

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->
"""
        result = validate_write(temp_path, new_content, "service")

        assert result.allowed == False
        assert any(v.violation_type == ViolationType.PROTECTED_AREA_MODIFIED
                   for v in result.violations)


# --- SOURCE_ALLOWLIST + echtes handoff.md-Format ---


def test_real_handoff_format_with_source_allowlist():
    """Test: Echtes handoff.md-Format mit Copilot-Markern + SOURCE_ALLOWLIST."""
    old_content = """---
handoff:
  project_id: "test_project"
---

# Handoff fuer Projekt test_project

<!-- MARKER:42
{
  "marker_id": "42",
  "titel": "Alter Marker",
  "status": "todo"
}
-->

## Alter Marker · todo
"""
    new_content = """---
handoff:
  project_id: "test_project"
---

# Handoff fuer Projekt test_project

<!-- MARKER:42
{
  "marker_id": "42",
  "titel": "Aktualisierter Marker",
  "status": "in_progress"
}
-->

## Aktualisierter Marker · in_progress
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "handoff.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(old_content)

        # project_handoff_service darf schreiben
        result = validate_write(temp_path, new_content, "project_handoff_service")
        assert result.allowed == True

        # Unbekanntes Script darf nicht
        result2 = validate_write(temp_path, new_content, "random_script")
        assert result2.allowed == False


def test_explicit_only_blocks_all_changes():
    """Test: EXPLICIT_ONLY blockiert jede Aenderung (marker-context.md)."""
    content = "# Marker Context\nAktueller Fokus\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "marker-context.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = validate_write(temp_path, content + "Neu\n", "test_source")
        assert result.allowed == False
        assert result.violations[0].violation_type == ViolationType.PROTECTED_AREA_MODIFIED


# --- Atomic Write + File-Lock ---


def test_atomic_write_no_partial_file():
    """Test: Atomic Write hinterlaesst keine halbgeschriebenen Dateien."""
    content = """# Test

<!-- DASHBOARD-GENERATED:START source=svc -->
Alt
<!-- DASHBOARD-GENERATED:END -->
"""
    new_content = """# Test

<!-- DASHBOARD-GENERATED:START source=svc -->
Neu mit mehr Inhalt
Zweite Zeile
Dritte Zeile
<!-- DASHBOARD-GENERATED:END -->
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = safe_write(temp_path, new_content, "svc")
        assert result.allowed == True

        with open(temp_path, 'r', encoding='utf-8') as f:
            actual = f.read()

        assert actual == new_content

        remaining = [f for f in os.listdir(tmpdir) if f.startswith(".write_guard_")]
        assert remaining == [], f"Temp-Dateien zurueckgeblieben: {remaining}"

        lock_files = [f for f in os.listdir(tmpdir) if f.endswith(".lock")]
        assert lock_files == [], f"Lock-Dateien zurueckgeblieben: {lock_files}"


def test_atomic_write_preserves_permissions():
    """Test: Atomic Write uebernimmt Dateiberechtigungen vom Original."""
    content = "Original\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        no_policy_path = os.path.join(tmpdir, "readme.md")
        with open(no_policy_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(no_policy_path, 0o644)
        original_mode = os.stat(no_policy_path).st_mode

        result = safe_write(no_policy_path, "Neuer Inhalt\n", "test")
        assert result.allowed == True

        new_mode = os.stat(no_policy_path).st_mode
        assert new_mode == original_mode, (
            f"Berechtigungen geaendert: {oct(original_mode)} -> {oct(new_mode)}"
        )


def test_file_lock_serializes_writes():
    """Test: File-Lock serialisiert sequentielle Schreibzugriffe korrekt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        content = "# Session\n\nErste Zeile\n"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        append1 = content + "Zweite Zeile\n"
        result1 = safe_write(temp_path, append1, "writer_1")
        assert result1.allowed == True

        append2 = append1 + "Dritte Zeile\n"
        result2 = safe_write(temp_path, append2, "writer_2")
        assert result2.allowed == True

        with open(temp_path, 'r', encoding='utf-8') as f:
            final = f.read()
        assert final == append2


def test_revalidation_after_lock():
    """Test: Re-Validierung nach Lock-Akquise erkennt zwischenzeitliche Aenderung."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        original = "# Session\n\nOriginal\n"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(original)

        new_content = original + "Neu\n"

        # Aendere die Datei (simuliert zwischenzeitliche Aenderung)
        modified = "# Session\n\nOriginal\nZwischenzeitlich eingefuegt\n"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(modified)

        result = safe_write(temp_path, new_content, "test")

        assert result.allowed == False
        assert any(v.violation_type == ViolationType.NON_APPEND_WRITE
                   for v in result.violations)

        with open(temp_path, 'r', encoding='utf-8') as f:
            actual = f.read()
        assert actual == modified


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
