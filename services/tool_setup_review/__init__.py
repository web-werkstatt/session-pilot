"""
ADR-002 Stufe 1a: Setup-Reviewer - oeffentliche API.

Re-Export-Facade. Alle oeffentlichen Funktionen und Konstanten werden
hier exportiert, damit Aufrufer nur `services.tool_setup_review` kennen
muessen und die interne Modulstruktur irrelevant bleibt.
"""
from services.tool_setup_review.constants import (
    EXCERPT_HEAD_LINES,
    EXCERPT_TAIL_LINES,
    REVIEW_TYPE,
    REVIEWER_TOOL_DEFAULT,
    SCHEMA_VERSION,
    TOOL_FILES,
)
from services.tool_setup_review.context_collector import (
    build_tool_setup_context,
    _inspect_marker_context,
)
from services.tool_setup_review.drift_check import detect_context_drift
from services.tool_setup_review.orchestrator import (
    _compute_context_hash,
    _load_system_prompt,
    _parse_reviewer_response,
    review_tool_setup,
)
from services.tool_setup_review.storage import (
    _default_now,
    _row_to_dict,
    load_review,
    save_review,
)

__all__ = [
    "build_tool_setup_context",
    "detect_context_drift",
    "review_tool_setup",
    "save_review",
    "load_review",
    "TOOL_FILES",
    "REVIEW_TYPE",
    "REVIEWER_TOOL_DEFAULT",
    "SCHEMA_VERSION",
    "EXCERPT_HEAD_LINES",
    "EXCERPT_TAIL_LINES",
]
