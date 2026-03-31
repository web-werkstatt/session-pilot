"""
AI-Scope-Analyse fuer Sessions (Sprint 9).
Extrahiert AI-Flags aus Messages: Tool-Nutzung, Write-Operationen, Tool-Liste.
"""
import json

# Tools die Dateien schreiben/aendern
WRITE_TOOLS = frozenset({
    "Write", "Edit", "MultiEdit", "NotebookEdit",
    "write", "edit", "multi_edit", "notebook_edit",
    "mcp__serena__create_text_file", "mcp__serena__replace_content",
    "mcp__serena__replace_symbol_body", "mcp__serena__insert_after_symbol",
    "mcp__serena__insert_before_symbol",
})

# Tools die ignoriert werden (kein echtes Tool-Use)
IGNORE_TOOLS = frozenset({
    "thinking", "text",
})


def extract_tool_names(content):
    """Extrahiert Tool-Namen aus Message-Content (tool_use Bloecke)."""
    tools = set()
    if not isinstance(content, list):
        return tools
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            name = block.get("name", "")
            if name and name not in IGNORE_TOOLS:
                tools.add(name)
    return tools


def extract_ai_flags(messages):
    """Analysiert Messages und gibt AI-Scope-Flags zurueck.

    Args:
        messages: Liste von Message-Dicts (mit type, content/content_json)

    Returns:
        dict mit ai_has_writes, ai_has_tool_calls, ai_tools_used
    """
    all_tools = set()

    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        # content_json hat die strukturierten Bloecke
        content_json = msg.get("content_json")
        if content_json:
            try:
                content = json.loads(content_json) if isinstance(content_json, str) else content_json
            except (json.JSONDecodeError, TypeError):
                continue
            all_tools |= extract_tool_names(content)

    tools_list = sorted(all_tools)
    has_writes = bool(all_tools & WRITE_TOOLS)
    has_tool_calls = bool(all_tools)

    return {
        "ai_has_writes": has_writes,
        "ai_has_tool_calls": has_tool_calls,
        "ai_tools_used": tools_list,
    }


def analyze_from_db_messages(rows):
    """Analysiert DB-Message-Rows (mit content_json Spalte).

    Args:
        rows: Liste von DB-Rows (RealDictRow) mit content_json

    Returns:
        dict mit ai_has_writes, ai_has_tool_calls, ai_tools_used
    """
    messages = []
    for row in rows:
        messages.append({
            "type": row.get("type", ""),
            "content_json": row.get("content_json"),
        })
    return extract_ai_flags(messages)
