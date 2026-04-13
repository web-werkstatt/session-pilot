"""
CWO Sprint: Context Window Optimizer - oeffentliche API.

Re-Export-Facade. Alle oeffentlichen Funktionen und Konstanten werden
hier exportiert, damit Aufrufer nur `services.context_window_optimizer`
kennen muessen und die interne Modulstruktur irrelevant bleibt.

Hinweis: Imports werden schrittweise ergaenzt wenn die Module
in den folgenden Tickets implementiert werden (1.2-1.8).
"""
from services.context_window_optimizer.constants import (
    ACTION_CREATE_SUBDIR,
    ACTION_CREATE_SUMMARY,
    ACTION_REMOVE_DUPLICATES,
    ACTION_ROTATE_NEXT_SESSION,
    ACTION_UPDATE_FOCUS,
    CLAUDE_MD_ERROR,
    CLAUDE_MD_WARN,
    LOAD_MODE_ALWAYS,
    LOAD_MODE_ARCHIVED,
    LOAD_MODE_AUTO_SUBDIR,
    LOAD_MODE_MANUAL_READ,
    LOAD_MODE_SKILL,
    LOAD_MODE_SUMMARIZED,
    REVIEW_TYPE,
    REVIEWER_TOOL_DEFAULT,
    SCHEMA_VERSION,
    TOKEN_BUDGET_ERROR,
    TOKEN_BUDGET_INFO,
    TOKEN_BUDGET_WARN,
    TOKEN_FACTOR_CODE,
    TOKEN_FACTOR_MARKDOWN,
    TOOL_FILES,
)
from services.context_window_optimizer.context_collector import (
    build_cwo_context,
)
from services.context_window_optimizer.checks import (
    BaseCWOCheck,
    CWOFinding,
    MigrationEntry,
    get_all_checks,
    run_all_checks,
)

__all__ = [
    # Check-Framework
    "BaseCWOCheck",
    "CWOFinding",
    "MigrationEntry",
    "get_all_checks",
    "run_all_checks",
    # Context Collector
    "build_cwo_context",
    # Constants
    "TOKEN_FACTOR_MARKDOWN",
    "TOKEN_FACTOR_CODE",
    "TOKEN_BUDGET_INFO",
    "TOKEN_BUDGET_WARN",
    "TOKEN_BUDGET_ERROR",
    "CLAUDE_MD_WARN",
    "CLAUDE_MD_ERROR",
    "LOAD_MODE_ALWAYS",
    "LOAD_MODE_AUTO_SUBDIR",
    "LOAD_MODE_SKILL",
    "LOAD_MODE_MANUAL_READ",
    "LOAD_MODE_ARCHIVED",
    "LOAD_MODE_SUMMARIZED",
    "TOOL_FILES",
    "REVIEW_TYPE",
    "REVIEWER_TOOL_DEFAULT",
    "SCHEMA_VERSION",
    "ACTION_CREATE_SUBDIR",
    "ACTION_CREATE_SUMMARY",
    "ACTION_ROTATE_NEXT_SESSION",
    "ACTION_REMOVE_DUPLICATES",
    "ACTION_UPDATE_FOCUS",
]
