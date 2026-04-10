"""
Tests für services/write_guard.py
"""
import os
import tempfile
import pytest

from services.write_guard import (
    WritePolicy, ViolationType, WriteResult,
    validate_write, safe_write, get_policy_summary,
    WRITE_POLICIES
)


def test_get_policy_summary():
    """Test für Policy-Zusammenfassung."""
    summary = get_policy_summary()

    assert summary["next-session.md"] == "append-only"
    assert summary["handoff.md"] == "source-allowlist"
    assert summary["sprints/*.md"] == "append-only"
    assert summary["CLAUDE.md"] == "generated-blocks-only"
    assert summary["marker-context.md"] == "explicit-only"


def test_no_policy_file():
    """Test für Datei ohne Policy."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Inhalt")
        f.flush()
        
        result = validate_write(f.name, "Neuer Inhalt", "test_source")
        os.unlink(f.name)
        
        assert result.allowed == True
        assert result.policy_applied is None
        assert len(result.violations) == 0


def test_new_file():
    """Test für neue Datei (existiert nicht)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("")  # Leere Datei erstellen
        temp_path = f.name
    
    # Datei löschen, um neue Datei zu simulieren
    os.unlink(temp_path)
    
    result = validate_write(temp_path, "Neuer Inhalt", "test_source")
    
    # Neue Datei sollte immer erlaubt sein
    assert result.allowed == True
    assert result.file_exists == False


def test_append_only_policy_allowed():
    """Test für append-only Policy (erlaubt)."""
    import tempfile
    import os
    
    # Erstelle temporäres Verzeichnis mit exaktem Dateinamen
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        content = """# Session

Erledigt: X

"""
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Anhängen am Ende
        new_content = content + "Neu: Y\n"
        
        result = validate_write(temp_path, new_content, "test_source")
        
        assert result.allowed == True
        assert result.policy_applied == WritePolicy.APPEND_ONLY
        assert len(result.violations) == 0


def test_append_only_policy_violation():
    """Test für append-only Policy (Verletzung)."""
    content = """# Session

Erster Punkt
Zweiter Punkt
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """# Session

Erster Punkt GEÄNDERT
Zweiter Punkt
"""
        result = validate_write(temp_path, new_content, "test_source")

        assert result.allowed == False
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == ViolationType.NON_APPEND_WRITE


def test_generated_blocks_only_allowed():
    """Test für generated-blocks-only Policy (erlaubt)."""
    content = """Vorher Text

<!-- DASHBOARD-GENERATED:START source=tool_profile_adapter -->
Alter generierter Inhalt
<!-- DASHBOARD-GENERATED:END -->

Nachher Text
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """Vorher Text

<!-- DASHBOARD-GENERATED:START source=tool_profile_adapter -->
NEUER generierter Inhalt
<!-- DASHBOARD-GENERATED:END -->

Nachher Text
"""
        result = validate_write(temp_path, new_content, "tool_profile_adapter")

        assert result.allowed == True
        assert result.policy_applied == WritePolicy.GENERATED_BLOCKS_ONLY
        assert len(result.violations) == 0


def test_generated_blocks_only_wrong_source():
    """Test für generated-blocks-only mit falschem source."""
    content = """Vorher Text

<!-- DASHBOARD-GENERATED:START source=service_a -->
Inhalt
<!-- DASHBOARD-GENERATED:END -->

Nachher Text
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "AGENTS.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """Vorher Text

<!-- DASHBOARD-GENERATED:START source=service_a -->
GEÄNDERTER Inhalt
<!-- DASHBOARD-GENERATED:END -->

Nachher Text
"""
        result = validate_write(temp_path, new_content, "service_b")

        assert result.allowed == False
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == ViolationType.WRONG_SOURCE


def test_generated_blocks_only_protected_violation():
    """Test für generated-blocks-only mit geschütztem Bereich."""
    content = """Vorher Text GESCHÜTZT

<!-- DASHBOARD-GENERATED:START source=service -->
Inhalt
<!-- DASHBOARD-GENERATED:END -->

Nachher Text GESCHÜTZT
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "GEMINI.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """Vorher Text GEÄNDERT

<!-- DASHBOARD-GENERATED:START source=service -->
Inhalt
<!-- DASHBOARD-GENERATED:END -->

Nachher Text GESCHÜTZT
"""
        result = validate_write(temp_path, new_content, "service")

        assert result.allowed == False
        assert len(result.violations) >= 1
        assert any(v.violation_type == ViolationType.PROTECTED_AREA_MODIFIED
                   for v in result.violations)


def test_manual_block_protection():
    """Test für MANUAL-Block Schutz."""
    content = """Vorher

<!-- MANUAL:START owner=joseph -->
Manueller Inhalt
<!-- MANUAL:END -->

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """Vorher

<!-- MANUAL:START owner=joseph -->
MANUELL GEÄNDERT
<!-- MANUAL:END -->

<!-- DASHBOARD-GENERATED:START source=service -->
Generiert
<!-- DASHBOARD-GENERATED:END -->
"""
        result = validate_write(temp_path, new_content, "service")

        assert result.allowed == False
        assert any(v.violation_type == ViolationType.PROTECTED_AREA_MODIFIED
                   for v in result.violations)


def test_safe_write_allowed():
    """Test für safe_write (erlaubt)."""
    content = """# Test

<!-- DASHBOARD-GENERATED:START source=test_service -->
Alt
<!-- DASHBOARD-GENERATED:END -->
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """# Test

<!-- DASHBOARD-GENERATED:START source=test_service -->
Neu
<!-- DASHBOARD-GENERATED:END -->
"""
        result = safe_write(temp_path, new_content, "test_service")

        with open(temp_path, 'r', encoding='utf-8') as f:
            written_content = f.read()

        assert result.allowed == True
        assert written_content == new_content


def test_safe_write_blocked():
    """Test für safe_write (blockiert)."""
    content = """# Geschützt

Manueller Text
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "next-session.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """# Geschützt GEÄNDERT

Manueller Text
"""
        result = safe_write(temp_path, new_content, "test_service")

        with open(temp_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        assert result.allowed == False
        assert original_content == content


def test_sprints_pattern():
    """Test für sprints/*.md Pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sprints_dir = os.path.join(tmpdir, "sprints")
        os.makedirs(sprints_dir)
        
        file_path = os.path.join(sprints_dir, "test-sprint.md")
        
        # Schreibe initialen Inhalt
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("""# Sprint Test

## Erledigt
- Punkt 1
""")
        
        # Versuche zu ändern (nicht erlaubt bei append-only)
        new_content = """# Sprint Test GEÄNDERT

## Erledigt
- Punkt 1
"""
        
        result = validate_write(file_path, new_content, "test_source")
        
        assert result.allowed == False
        assert result.policy_applied == WritePolicy.APPEND_ONLY
        assert len(result.violations) == 1


def test_no_changes():
    """Test ohne Änderungen (immer erlaubt)."""
    content = """Beliebiger Inhalt"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    # Gleicher Inhalt
    result = validate_write(temp_path, content, "test_source")
    os.unlink(temp_path)
    
    assert result.allowed == True
    assert len(result.violations) == 0


def test_file_unreadable():
    """Test für nicht lesbare Datei mit Policy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "CLAUDE.md")
        # Erstelle Verzeichnis mit dem Dateinamen (nicht lesbar als Datei)
        os.makedirs(temp_path, exist_ok=True)

        result = validate_write(temp_path, "Neuer Inhalt", "test_source")

        assert result.allowed == False
        assert len(result.violations) == 1


def test_source_allowlist_allowed():
    """Test: SOURCE_ALLOWLIST erlaubt bekannte Quellen."""
    content = """# Handoff
<!-- MARKER:42 {...} -->
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "handoff.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        new_content = """# Handoff KOMPLETT NEU
Voellig anderer Inhalt
"""
        result = validate_write(temp_path, new_content, "project_handoff_service")

        assert result.allowed == True
        assert result.policy_applied == WritePolicy.SOURCE_ALLOWLIST


def test_source_allowlist_blocked():
    """Test: SOURCE_ALLOWLIST blockiert unbekannte Quellen."""
    content = """# Handoff
Inhalt
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "handoff.md")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = validate_write(temp_path, "Neuer Inhalt", "unknown_script")

        assert result.allowed == False
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == ViolationType.WRONG_SOURCE
        assert "unknown_script" in result.violations[0].description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])