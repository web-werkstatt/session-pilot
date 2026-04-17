"""
Sprint sprint-agent-orchestrator-phase-2-3-reshaped (Phase 3, 2026-04-17):
Gemeinsamer Append-only-Diff-Check fuer sensitive Markdown-Dateien.

Regel (aus CLAUDE.md "Schreib-Policies pro Datei" + Technical Spec §4):

  * Aenderungen innerhalb eines `<!-- DASHBOARD-GENERATED:START ... -->`
    Blocks duerfen bestehende Zeilen veraendern.
  * Aenderungen ausserhalb eines solchen Blocks sind nur erlaubt, wenn es
    sich um reine Additionen am Dateiende handelt.
  * Alles andere ist eine Verletzung und liefert `status=fail`.

Der Checker ist bewusst ohne DB- oder Subprocess-Zugriff gebaut, damit er
als reiner Parser unit-getestet und von Phase-3-Tests ohne Git- oder
PostgreSQL-Setup genutzt werden kann.
"""
from __future__ import annotations

import os
import re
from typing import Optional


_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_BLOCK_START = re.compile(r"<!--\s*DASHBOARD-GENERATED:START")
_BLOCK_END = re.compile(r"<!--\s*DASHBOARD-GENERATED:END")

STATUS_PASS = "pass"
STATUS_FAIL = "fail"

REASON_OK_INSIDE_BLOCK = "inside_generated_block"
REASON_OK_APPEND_EOF = "append_at_eof"
REASON_OK_MIXED = "inside_generated_block_or_append_at_eof"
REASON_FAIL = "modifies_manual_text"

CLAIM_APPEND_ONLY_RESPECTED = "append_only_respected"

# Status-Konstanten des Verify-Gates, damit dieses Modul nicht rueckwaerts
# aus agent_verify_service importieren muss (vermeidet Zirkular-Import).
_VERIFY_STATUS_PASS = "pass"
_VERIFY_STATUS_FAIL = "fail"
_VERIFY_STATUS_BLOCKED = "blocked"


def check_append_only_diff(
    path: str,
    diff: str,
    *,
    file_content_before: Optional[str] = None,
) -> dict:
    """Prueft, ob ein unified-diff auf `path` die Append-only-Policy einhaelt.

    Parameter:
      path: Pfad der geaenderten Datei (nur fuer Reporting).
      diff: unified-diff-Text (`git diff` Format).
      file_content_before: Originalinhalt der Datei als String. Wenn None,
        wird `path` von der Festplatte gelesen. Tests uebergeben den Inhalt
        direkt, damit kein Dateisystem-Setup noetig ist.

    Rueckgabe:
      {
        "path": str,
        "status": "pass" | "fail",
        "reason": str,
        "violations": [ { "hunk": str, "reason": str } ],
      }

    Leerer diff -> pass (nichts zu pruefen).
    """
    if diff is None or not diff.strip():
        return {
            "path": path,
            "status": STATUS_PASS,
            "reason": "empty_diff",
            "violations": [],
        }

    content = (
        file_content_before
        if file_content_before is not None
        else _read_file_or_empty(path)
    )
    total_lines = len(content.splitlines())
    block_ranges = _find_generated_blocks(content)
    hunks = _parse_hunks(diff)

    violations = []
    for hunk in hunks:
        reason = _hunk_violation(hunk, total_lines, block_ranges)
        if reason:
            violations.append({"hunk": hunk["header"], "reason": reason})

    if violations:
        return {
            "path": path,
            "status": STATUS_FAIL,
            "reason": REASON_FAIL,
            "violations": violations,
        }
    return {
        "path": path,
        "status": STATUS_PASS,
        "reason": REASON_OK_MIXED,
        "violations": [],
    }


def check_append_only_required_verification(req: dict):
    """Verify-Gate-Adapter fuer required_verification-Eintrag vom Typ
    `append_only_diff`.

    Rueckgabe: (check_dict, claim_name)
    check_dict enthaelt `type`, `status`, `claim`, `details`.

    Dieser Helper bleibt bewusst hier, damit agent_verify_service.py schlank
    bleibt und die komplette Append-only-Logik — inklusive ihrer Anbindung
    an den Verify-Gate-Dispatcher — in genau einem Modul liegt.
    """
    claim = req.get("claim") or CLAIM_APPEND_ONLY_RESPECTED

    evidence_list = req.get("evidence")
    if not evidence_list:
        single = {
            "path": req.get("path"),
            "diff": req.get("diff"),
            "file_content_before": req.get("file_content_before"),
        }
        evidence_list = [single] if single.get("path") else []

    if not evidence_list:
        return ({
            "type": "required_verification",
            "status": _VERIFY_STATUS_BLOCKED,
            "claim": claim,
            "details": "append_only_diff missing path/diff evidence",
        }, claim)

    violations = []
    for item in evidence_list:
        path = item.get("path") if isinstance(item, dict) else None
        diff = item.get("diff") if isinstance(item, dict) else None
        file_before = item.get("file_content_before") if isinstance(item, dict) else None
        if not path or diff is None:
            violations.append({"path": path, "reason": "missing_path_or_diff"})
            continue
        result = check_append_only_diff(path, diff, file_content_before=file_before)
        if result["status"] != STATUS_PASS:
            violations.append({
                "path": path,
                "reason": result.get("reason"),
                "violations": result.get("violations") or [],
            })

    if not violations:
        return ({
            "type": "required_verification",
            "status": _VERIFY_STATUS_PASS,
            "claim": claim,
            "details": "append-only diff check passed for all paths",
        }, claim)
    return ({
        "type": "required_verification",
        "status": _VERIFY_STATUS_FAIL,
        "claim": claim,
        "details": f"append-only violations: {violations}",
    }, claim)


def _read_file_or_empty(path: str) -> str:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
    except Exception:
        return ""
    return ""


def _find_generated_blocks(content: str):
    """Liefert Liste von (start_line, end_line) 1-indexiert, inklusive beide.

    Ein Block erstreckt sich von der START-Marker-Zeile bis zur END-Marker-Zeile
    (beide Marker-Zeilen selbst gelten als zum Block gehoerig, damit ein Diff
    auf der START- oder END-Zeile den Block intakt halten kann).
    """
    ranges = []
    open_start: Optional[int] = None
    for idx, line in enumerate(content.splitlines(), start=1):
        if _BLOCK_START.search(line):
            if open_start is None:
                open_start = idx
        elif _BLOCK_END.search(line):
            if open_start is not None:
                ranges.append((open_start, idx))
                open_start = None
    # Offen gebliebener Block: defensiv bis Dateiende weiten, damit ein
    # kaputtes / halbes Generated-Fragment nicht faelschlich als "manueller
    # Text" blockiert wird. Der Verify-Gate soll Append-only-Verstoesse
    # erkennen, nicht Block-Parsing-Fehler.
    if open_start is not None:
        ranges.append((open_start, max(open_start, len(content.splitlines()))))
    return ranges


def _parse_hunks(diff: str):
    hunks = []
    current = None
    for raw in diff.splitlines():
        m = _HUNK_HEADER.match(raw)
        if m:
            if current is not None:
                hunks.append(current)
            current = {
                "header": raw,
                "old_start": int(m.group(1)),
                "old_count": int(m.group(2)) if m.group(2) is not None else 1,
                "new_start": int(m.group(3)),
                "new_count": int(m.group(4)) if m.group(4) is not None else 1,
                "lines": [],
            }
        elif current is not None:
            if raw.startswith("+++") or raw.startswith("---"):
                # File headers gehoeren nicht in Hunk-Lines.
                continue
            if raw and raw[0] in ("+", "-", " ", "\\"):
                current["lines"].append(raw)
            # andere Zeilen (leer, diff --git, index ...) ignorieren
    if current is not None:
        hunks.append(current)
    return hunks


def _hunk_violation(hunk, total_lines, block_ranges):
    """Gibt Grund als String zurueck, wenn der Hunk die Policy verletzt.

    None heisst: Hunk ist ok.
    """
    affected_old = []       # original-Zeilennummern, die entfernt/geaendert werden
    added_anchor = []       # alte-Datei-Koordinaten, an denen Zeilen eingefuegt werden
    # Bei `@@ -N,0 +M,K @@` ist die Einfuegung in git-Konvention "nach Zeile N",
    # also vor Zeile N+1 der alten Datei. Wir starten cur_old deshalb bei N+1,
    # damit die Anchor-Pruefung "anchor > total_lines" auch den EOF-Fall
    # sauber abdeckt (N = total_lines -> anchor = total_lines + 1 > total_lines).
    if hunk["old_count"] == 0:
        cur_old = hunk["old_start"] + 1
    else:
        cur_old = hunk["old_start"]

    for raw in hunk["lines"]:
        if raw.startswith("\\"):
            # "\ No newline at end of file" — ignorieren
            continue
        if raw.startswith("-"):
            affected_old.append(cur_old)
            cur_old += 1
        elif raw.startswith("+"):
            # Einfuegung vor cur_old (bzw. am Ende, wenn cur_old > total_lines)
            added_anchor.append(cur_old)
        elif raw.startswith(" "):
            cur_old += 1

    def _in_block(line_no: int) -> bool:
        for start, end in block_ranges:
            if start <= line_no <= end:
                return True
        return False

    # Entfernte/geaenderte Original-Zeilen, die NICHT in einem Generated-Block
    # liegen, sind grundsaetzlich Verletzungen.
    bad_removals = [p for p in affected_old if not _in_block(p)]

    # Einfuegungen sind ok wenn:
    #   - Ankerposition liegt in einem Generated-Block, ODER
    #   - die Zeile davor (Anker-1) liegt in einem Generated-Block
    #     (Einfuegung direkt hinter einer Block-Zeile ist Teil des Blocks), ODER
    #   - Anker liegt hinter dem Dateiende (reine EOF-Addition).
    bad_insertions = [
        p for p in added_anchor
        if not (_in_block(p) or _in_block(p - 1) or p > total_lines)
    ]

    if bad_removals and bad_insertions:
        return (
            f"removes lines {sorted(set(bad_removals))} and inserts at "
            f"{sorted(set(bad_insertions))} outside generated block / EOF"
        )
    if bad_removals:
        return (
            f"removes or modifies manual lines outside generated block: "
            f"{sorted(set(bad_removals))}"
        )
    if bad_insertions:
        return (
            f"inserts lines outside generated block and not at EOF: "
            f"{sorted(set(bad_insertions))}"
        )
    return None
