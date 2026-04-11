"""
ADR-002 Stufe 1a: Konstanten fuer Setup-Reviewer.

Zentral gehalten, damit alle Submodule aus demselben Ort importieren
und keine Import-Zyklen entstehen.
"""

TOOL_FILES = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "gemini": "GEMINI.md",
}

REVIEWER_TOOL_DEFAULT = "perplexity"
REVIEW_TYPE = "setup"
SCHEMA_VERSION = 1

# Excerpt-Groessen fuer Tool-Files: Kopf + Ende, damit der Reviewer
# Struktur und Signatur sieht, ohne das Kontextfenster zu sprengen.
EXCERPT_HEAD_LINES = 40
EXCERPT_TAIL_LINES = 20
