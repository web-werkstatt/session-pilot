"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 3, 2026-04-17):
Tests fuer den Append-only-Diff-Check.

Fokus auf Akzeptanzkriterien AC1-AC3 aus §spec-phase3-akzeptanz:
  AC1: Aenderung im generierten Block passiert das Gate
  AC2: Aenderung in manuellem Text (ausserhalb Block, nicht am Ende) wird
       blockiert
  AC3: Anhaengen am Dateiende passiert das Gate

Zusaetzlich abgedeckt:
  * leerer Diff -> pass (Neutralelement)
  * Einfuegung direkt am Block-Ende bleibt im Block
  * Entfernen einer manuellen Zeile ausserhalb Block -> fail
"""
from __future__ import annotations

from services.agent_append_only_diff import check_append_only_diff


FILE_NEXT_SESSION = """\
# Projekt-Dashboard - Naechste Session

<!-- DASHBOARD-GENERATED:START source=session-handoff updated=2026-04-17 -->
> Status: irgendwas
> Naechste Aufgabe: Platzhalter
<!-- DASHBOARD-GENERATED:END -->

## Manuelle Notiz
Hier steht manuell geschriebener Text der geschuetzt ist.
Zweite Zeile manueller Text.

## Update 2026-04-17
- Changed: foo
- Files: bar
"""


def test_ac1_diff_in_generated_block_passes():
    # Aendert zwei Zeilen komplett innerhalb des Generated-Blocks
    diff = (
        "@@ -4,2 +4,2 @@\n"
        "-> Status: irgendwas\n"
        "-> Naechste Aufgabe: Platzhalter\n"
        "+> Status: Phase 3 laeuft\n"
        "+> Naechste Aufgabe: Append-only-Gate\n"
    )
    result = check_append_only_diff(
        "next-session.md", diff, file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "pass", result
    assert result["violations"] == []


def test_ac2_diff_in_manual_text_outside_block_is_blocked():
    # Aendert Zeile 9 (manuelle Notiz) mittendrin — weder im Block noch am EOF
    diff = (
        "@@ -9,1 +9,1 @@\n"
        "-Hier steht manuell geschriebener Text der geschuetzt ist.\n"
        "+Hier steht umformulierter Text.\n"
    )
    result = check_append_only_diff(
        "next-session.md", diff, file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "fail", result
    assert result["violations"], "violations must not be empty"
    assert "outside generated block" in result["violations"][0]["reason"].lower()


def test_ac3_append_at_eof_passes():
    total = len(FILE_NEXT_SESSION.splitlines())
    # Haengt einen neuen Update-Block am Dateiende an (old_count=0 an Position total+1)
    diff = (
        f"@@ -{total},0 +{total + 1},3 @@\n"
        "+## Update 2026-04-17 — Phase 3\n"
        "+- Changed: Append-only-Gate ergaenzt\n"
        "+- Files: services/agent_append_only_diff.py\n"
    )
    result = check_append_only_diff(
        "next-session.md", diff, file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "pass", result


def test_remove_manual_line_outside_block_is_blocked():
    diff = (
        "@@ -9,1 +9,0 @@\n"
        "-Hier steht manuell geschriebener Text der geschuetzt ist.\n"
    )
    result = check_append_only_diff(
        "next-session.md", diff, file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "fail"
    assert "outside generated block" in result["violations"][0]["reason"].lower()


def test_empty_diff_is_pass():
    result = check_append_only_diff(
        "next-session.md", "", file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "pass"
    assert result["reason"] == "empty_diff"


def test_insertion_inside_generated_block_passes():
    # Fuegt eine Zeile zwischen den beiden Generated-Zeilen ein
    diff = (
        "@@ -4,2 +4,3 @@\n"
        " > Status: irgendwas\n"
        "+> Extra: neu\n"
        " > Naechste Aufgabe: Platzhalter\n"
    )
    result = check_append_only_diff(
        "next-session.md", diff, file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "pass", result


def test_insertion_in_middle_of_manual_text_is_blocked():
    # Fuegt eine Zeile zwischen zwei manuellen Zeilen ein — kein EOF, kein Block
    diff = (
        "@@ -9,2 +9,3 @@\n"
        " Hier steht manuell geschriebener Text der geschuetzt ist.\n"
        "+Neue eingeschobene Zeile.\n"
        " Zweite Zeile manueller Text.\n"
    )
    result = check_append_only_diff(
        "next-session.md", diff, file_content_before=FILE_NEXT_SESSION,
    )
    assert result["status"] == "fail"
