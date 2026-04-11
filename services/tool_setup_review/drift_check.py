"""
ADR-002 Stufe 1a: Context-Drift-Check zwischen Tool-Files.

Prueft, ob die DASHBOARD-GENERATED-Bloecke in CLAUDE.md, AGENTS.md und
GEMINI.md konsistent sind. Drift ist ein hartes Risiko im Multi-LLM-Setup,
weil die Tools dann mit unterschiedlichem Kontext arbeiten, ohne dass es
jemandem auffaellt.
"""
from typing import Any, Dict


def detect_context_drift(tool_files: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Prueft, ob die DASHBOARD-GENERATED-Bloecke der Tool-Files konsistent sind.

    Szenarien:
    - Keine Tool-Datei existiert → kein Drift, has_drift=False
    - Nur einige Tool-Dateien haben einen Block → Drift
    - Alle Blocks sind identisch → kein Drift
    - Blocks unterscheiden sich → Drift
    """
    existing = {f: info for f, info in tool_files.items() if info.get("exists")}

    if not existing:
        return {
            "has_drift": False,
            "reason": "Keine Tool-Datei existiert, noch nichts zu vergleichen.",
        }

    with_block = {
        f: info for f, info in existing.items() if info.get("has_generated_block")
    }
    without_block = sorted(
        f for f, info in existing.items() if not info.get("has_generated_block")
    )

    if not with_block:
        return {
            "has_drift": False,
            "reason": "Keine Tool-Datei hat bisher einen DASHBOARD-GENERATED-Block.",
        }

    contents = {f: info.get("generated_block_content") for f, info in with_block.items()}
    unique_contents = set(contents.values())

    # Drift, wenn es Tool-Files ohne Block gibt und auch Tool-Files mit Block
    if without_block:
        drifted = sorted(list(with_block.keys()) + without_block)
        reason_parts = []
        if without_block:
            reason_parts.append(
                "Ohne generated Block: " + ", ".join(without_block)
            )
        if len(unique_contents) > 1:
            for f, info in with_block.items():
                reason_parts.append(
                    f"{f}: updated={info.get('generated_block_updated') or '?'}"
                )
        return {
            "has_drift": True,
            "drifted_files": drifted,
            "reason": "; ".join(reason_parts),
        }

    # Alle haben einen Block — sind sie identisch?
    if len(unique_contents) == 1:
        return {"has_drift": False}

    drifted = sorted(with_block.keys())
    reason_parts = [
        f"{f}: updated={info.get('generated_block_updated') or '?'}"
        for f, info in with_block.items()
    ]
    return {
        "has_drift": True,
        "drifted_files": drifted,
        "reason": "; ".join(reason_parts),
    }
