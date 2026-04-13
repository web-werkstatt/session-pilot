"""
CWO Sprint Ticket 1.5: Check 5 — Duplikate mit globalen Rules.

Vergleicht CLAUDE.md-Sektionen mit ~/.claude/rules/ Dateien via
Jaccard-Aehnlichkeit auf Token-Ebene (Wort-Shingles). Hohe
Aehnlichkeit deutet auf redundante Inhalte hin, die in der
globalen Rule bereits vorhanden sind.
"""
from __future__ import annotations

from typing import Dict, List, Set

from services.context_window_optimizer.checks import (
    BaseCWOCheck,
    CWOFinding,
    MigrationEntry,
    register_check,
)
from services.context_window_optimizer.constants import (
    ACTION_REMOVE_DUPLICATES,
    DUPLICATE_JACCARD_ERROR,
    DUPLICATE_JACCARD_WARN,
    LOAD_MODE_ALWAYS,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    TOKEN_FACTOR_MARKDOWN,
)


def _tokenize(text: str) -> Set[str]:
    """Erzeugt Wort-Shingle-Set aus Text (lowercase, Satzzeichen entfernt)."""
    words = []
    for line in text.splitlines():
        stripped = line.strip()
        # Ueberschriften, Leerzeilen und reine Markdown-Marker ignorieren
        if not stripped or stripped.startswith("#") or stripped in ("---", "```"):
            continue
        for word in stripped.split():
            cleaned = word.strip("*`_|#-:,;.!?()[]{}\"'<>")
            if cleaned and len(cleaned) > 2:
                words.append(cleaned.lower())

    # 3-Wort-Shingles fuer robusteren Vergleich
    if len(words) < 3:
        return set(words)
    return {f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)}


def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard-Aehnlichkeit zwischen zwei Sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


@register_check
class GlobalRuleDuplicatesCheck(BaseCWOCheck):
    """Check 5: Duplikate zwischen CLAUDE.md-Sektionen und globalen Rules."""

    check_id = "global_rule_duplicates"
    title = "Duplikate mit globalen Rules"

    def run(self, context: dict) -> List[CWOFinding]:
        sections = context.get("claude_md_sections", [])
        global_rules = context.get("global_rules", [])
        claude_content = (
            context.get("tool_files", {})
            .get("claude", {})
            .get("content", "")
        )

        if not sections or not global_rules or not claude_content:
            return []

        claude_lines = claude_content.splitlines()

        # Rules tokenisieren
        rule_tokens: Dict[str, Set[str]] = {}
        for rule in global_rules:
            content = rule.get("content", "")
            tokens = _tokenize(content)
            if tokens:
                rule_tokens[rule["filename"]] = tokens

        if not rule_tokens:
            return []

        findings = []
        for sec in sections:
            sec_text = _extract_section_text(claude_lines, sec)
            if not sec_text:
                continue
            sec_tokens = _tokenize(sec_text)
            if not sec_tokens:
                continue

            best_match = _find_best_match(sec_tokens, rule_tokens)
            if not best_match:
                continue

            rule_name, similarity = best_match

            if similarity < DUPLICATE_JACCARD_WARN:
                continue

            severity = (
                SEVERITY_ERROR if similarity >= DUPLICATE_JACCARD_ERROR
                else SEVERITY_WARN
            )
            threshold = (
                DUPLICATE_JACCARD_ERROR if severity == SEVERITY_ERROR
                else DUPLICATE_JACCARD_WARN
            )

            sec_lines = sec.get("lines", 0)
            tokens_saved = sec_lines * TOKEN_FACTOR_MARKDOWN

            migrations = [MigrationEntry(
                section_title=f"{sec['title']} ({sec_lines} Zeilen)",
                source=f"CLAUDE.md Zeile {sec['start_line']}-{sec['end_line']}",
                target=f"~/.claude/rules/{rule_name}",
                load_mode=LOAD_MODE_ALWAYS,
                load_condition=(
                    f"Bereits global geladen via {rule_name} "
                    f"(Jaccard {similarity:.0%})"
                ),
                tokens_saved=tokens_saved,
                risk="low",
            )]

            findings.append(CWOFinding(
                check_id=self.check_id,
                severity=severity,
                title=self.title,
                detail=(
                    f"Sektion '{sec['title']}' aehnelt "
                    f"globaler Rule '{rule_name}' "
                    f"(Jaccard: {similarity:.0%}, "
                    f"Schwelle: {threshold:.0%}). "
                    f"~{tokens_saved:,} Tokens redundant."
                ),
                current_value=round(similarity, 3),
                threshold=threshold,
                estimated_tokens=tokens_saved,
                actionable=True,
                action_id=ACTION_REMOVE_DUPLICATES,
                migration_map=migrations,
                recommendation=(
                    f"Sektion entfernen oder kuerzen — Inhalt ist "
                    f"bereits in '{rule_name}' vorhanden."
                ),
            ))

        return findings


def _extract_section_text(
    claude_lines: List[str], section: dict
) -> str:
    """Extrahiert den Text einer Sektion aus CLAUDE.md-Zeilen."""
    start = section.get("start_line", 0)
    end = section.get("end_line", 0)
    if start >= end or start >= len(claude_lines):
        return ""
    return "\n".join(claude_lines[start:end])


def _find_best_match(
    sec_tokens: Set[str],
    rule_tokens: Dict[str, Set[str]],
) -> tuple[str, float] | None:
    """Findet die Rule mit der hoechsten Jaccard-Aehnlichkeit."""
    best_name = ""
    best_sim = 0.0

    for name, tokens in rule_tokens.items():
        sim = _jaccard(sec_tokens, tokens)
        if sim > best_sim:
            best_sim = sim
            best_name = name

    if best_sim <= 0.0:
        return None
    return best_name, best_sim
