"""
CWO Sprint: Konstanten fuer Context Window Optimizer.

Zentral gehalten, damit alle Submodule aus demselben Ort importieren
und keine Import-Zyklen entstehen.
"""

# --- Token-Schaetzung ---

TOKEN_FACTOR_MARKDOWN = 18   # Tokens pro Zeile (Markdown/Prosa)
TOKEN_FACTOR_CODE = 15       # Tokens pro Zeile (Code-Dateien)

# --- Token-Budget Schwellwerte (Check 8) ---

TOKEN_BUDGET_INFO = 10_000
TOKEN_BUDGET_WARN = 20_000
TOKEN_BUDGET_ERROR = 30_000

# --- Dateigroessen-Schwellwerte (Zeilen) ---

# Check 1: CLAUDE.md
CLAUDE_MD_WARN = 150
CLAUDE_MD_ERROR = 250

# Check 2: AGENTS.md / GEMINI.md
TOOL_FILE_WARN = 150
TOOL_FILE_ERROR = 250

# Check 3: Datei im Fokusauftrag
FOCUS_FILE_WARN = 200
FOCUS_FILE_ERROR = 500

# Check 4: next-session.md
NEXT_SESSION_WARN = 150
NEXT_SESSION_ERROR = 300

# --- Struktur-Checks ---

# Check 5: Duplikat-Erkennung (Jaccard-Aehnlichkeit)
DUPLICATE_JACCARD_WARN = 0.6
DUPLICATE_JACCARD_ERROR = 0.8

# Check 6: Qualifizierte Verzeichnisse fuer Unterverz.-CLAUDE.md
SUBDIR_QUALIFYING_FILES = 3  # Mindestanzahl relevanter Dateien im Verz.

# Check 7: Auslagerbare Listen-Sektionen
EXTRACTABLE_LIST_MIN_ITEMS = 10

# --- Severity-Levels ---

SEVERITY_INFO = "info"
SEVERITY_WARN = "warning"
SEVERITY_ERROR = "error"

# --- Load-Modes ---

LOAD_MODE_ALWAYS = "always"
LOAD_MODE_AUTO_SUBDIR = "auto_subdir"
LOAD_MODE_SKILL = "skill"
LOAD_MODE_MANUAL_READ = "manual_read"
LOAD_MODE_ARCHIVED = "archived"
LOAD_MODE_SUMMARIZED = "summarized"

# --- Content-Loss-Levels ---

CONTENT_LOSS_NONE = "none"
CONTENT_LOSS_SUMMARIZED = "summarized"
CONTENT_LOSS_ARCHIVED = "archived"

# --- Risk-Levels ---

RISK_NONE = "none"
RISK_LOW = "low"
RISK_MEDIUM = "medium"

# --- Action-IDs ---

ACTION_CREATE_SUBDIR = "A"       # Unterverz.-CLAUDE.md erstellen
ACTION_CREATE_SUMMARY = "B"      # Summary-Datei generieren
ACTION_ROTATE_NEXT_SESSION = "C" # next-session.md rotieren
ACTION_REMOVE_DUPLICATES = "D"   # Duplikat-Sektionen (Diff-Preview)
ACTION_UPDATE_FOCUS = "E"        # Fokusauftrag anpassen (Diff-Preview)

# --- Action-Status ---

ACTION_STATUS_PROPOSED = "proposed"
ACTION_STATUS_APPROVED = "approved"
ACTION_STATUS_EXECUTED = "executed"
ACTION_STATUS_FAILED = "failed"
ACTION_STATUS_REJECTED = "rejected"

# --- Tool-Files ---

TOOL_FILES = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "gemini": "GEMINI.md",
}

# --- Globale Rules-Pfade ---

GLOBAL_RULES_DIR = "~/.claude/rules"

# --- Schema-Version ---

SCHEMA_VERSION = 1

# --- Review ---

REVIEW_TYPE = "cwo"
REVIEWER_TOOL_DEFAULT = "perplexity"
