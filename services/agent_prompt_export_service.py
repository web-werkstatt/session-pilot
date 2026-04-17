"""
Sprint sprint-agent-orchestrator-executor-handoff Commit 1 (2026-04-17):
Baut einen Markdown-Prompt-Block aus Task-Contract + Resolver-Kontext.

Der erzeugte Text ist so formatiert, dass der User ihn unveraendert in eine
interaktive Claude-Session pasten kann (Modell B: Dashboard als Empfaenger).
Struktur gemaess `sprints/sprint-agent-orchestrator-executor-handoff.md
§spec-prompt-export` — acht feste Abschnitte:

  1. Titel
  2. Ziel-Absatz
  3. Erlaubte Dateien
  4. Verbotene Aktionen
  5. Geforderte Nachweise beim Abschluss
  6. Stop-Bedingungen
  7. Handoff-Kontext (Pfad, letzte N Zeilen, aktiver Marker, relevanter Plan)
  8. Abschluss-Protokoll (3 Shell-Zeilen + UI-Fallback-Hinweis)

Defaults:
  * `HANDOFF_TAIL_LINES = 50` — genug Kontext fuer kontinuierliche Sessions,
    ohne den Prompt unnoetig aufzublaehen.
  * Aktiver Marker wird kompakt als `marker_id + titel` dargestellt, nicht mit
    vollem Text-Inhalt, damit der Export stabil und uebersichtlich bleibt.
"""

HANDOFF_TAIL_LINES = 50


def build_prompt_markdown(task, context=None, handoff_tail_lines=HANDOFF_TAIL_LINES,
                          read_handoff_fn=None):
    """Baut den Markdown-Prompt-Block.

    Parameter:
      * task: dict aus `agent_orchestrator_service.get_task(...)`.
      * context: optional Ergebnis von `resolve_context(...)`. None -> der
        Handoff-Abschnitt zeigt "kein Handoff konfiguriert".
      * handoff_tail_lines: Anzahl der Tail-Zeilen aus `handoff_path`.
      * read_handoff_fn: Injection fuer Tests (callable(path) -> str). None ->
        Datei wird direkt via open() gelesen.

    Rueckgabe: Markdown-String, endet mit genau einem "\n".
    """
    if not task:
        raise ValueError("task darf nicht leer sein")

    lines = []
    task_id = task.get("task_id")
    title = task.get("title") or "(ohne Titel)"
    lines.append(f"# Agent-Task {task_id}: {title}")
    lines.append("")

    goal = (task.get("goal") or "").strip()
    lines.append(goal if goal else "_Kein Ziel-Text hinterlegt._")
    lines.append("")

    lines.append("## Erlaubte Dateien")
    lines.extend(_render_list(task.get("allowed_files"),
                              empty="_Kein Scope gesetzt._"))
    lines.append("")

    lines.append("## Verbotene Aktionen")
    lines.extend(_render_list(task.get("forbidden_actions"),
                              empty="_Keine Einschraenkungen gesetzt._"))
    lines.append("")

    lines.append("## Geforderte Nachweise beim Abschluss")
    lines.extend(_render_verification(task.get("required_verification")))
    lines.append("")

    lines.append("## Stop-Bedingungen")
    lines.extend(_render_list(task.get("stop_conditions"),
                              empty="_Keine Stop-Bedingungen definiert._"))
    lines.append("")

    lines.append("## Handoff-Kontext")
    lines.extend(_render_handoff_section(context, handoff_tail_lines,
                                         read_handoff_fn=read_handoff_fn))
    lines.append("")

    lines.append("## Abschluss-Protokoll")
    lines.append("```")
    lines.append(f"claude-task finish {task_id}")
    lines.append(f"claude-task verify {task_id}")
    lines.append(f"claude-task close {task_id}")
    lines.append("```")
    lines.append(
        "Ohne CLI-Helper: Execution-Result ueber das Textfeld "
        '"Execution-Result pasten" auf der Task-Detail-Seite einreichen.'
    )

    return "\n".join(lines).rstrip() + "\n"


def _render_list(items, *, empty):
    if not items:
        return [empty]
    return [f"- {_as_line(item)}" for item in items]


def _render_verification(items):
    if not items:
        return ["_Keine Nachweise konfiguriert._"]
    rendered = []
    for item in items:
        if isinstance(item, dict):
            claim_type = item.get("type") or item.get("claim") or "claim"
            extras = []
            for key in ("command", "path", "match"):
                value = item.get(key)
                if value:
                    extras.append(f"{key}=`{value}`")
            if extras:
                rendered.append(f"- {claim_type} ({', '.join(extras)})")
            else:
                rendered.append(f"- {claim_type}")
        else:
            rendered.append(f"- {_as_line(item)}")
    return rendered


def _render_handoff_section(context, handoff_tail_lines, *, read_handoff_fn=None):
    if not context:
        return ["_Kein Handoff konfiguriert._"]

    lines = []
    handoff_path = context.get("handoff_path")
    handoff_exists = bool(context.get("handoff_exists"))

    if handoff_path:
        lines.append(f"Handoff: `{handoff_path}`")
        if handoff_exists:
            tail = _read_handoff_tail(handoff_path, handoff_tail_lines,
                                      read_handoff_fn=read_handoff_fn)
            if tail:
                lines.append("")
                lines.append(f"Letzte {handoff_tail_lines} Zeilen:")
                lines.append("```")
                lines.extend(tail.splitlines())
                lines.append("```")
            else:
                lines.append("_Handoff-Datei existiert, ist aber leer._")
        else:
            lines.append("_Handoff-Datei existiert nicht._")
    else:
        lines.append("_Kein Handoff konfiguriert._")

    lines.append("")
    marker = context.get("active_marker") or None
    if marker and marker.get("marker_id"):
        marker_id = marker.get("marker_id")
        marker_title = marker.get("titel") or "(ohne Titel)"
        lines.append(f"Aktiver Marker: `{marker_id}` — {marker_title}")
    else:
        lines.append("Aktiver Marker: _keiner_")

    plan = context.get("relevant_plan") or None
    if plan and plan.get("id"):
        plan_id = plan.get("id")
        plan_title = plan.get("title") or "(ohne Titel)"
        plan_source = plan.get("source_path") or ""
        if plan_source:
            lines.append(
                f"Relevanter Plan: `{plan_id}` — {plan_title} (`{plan_source}`)"
            )
        else:
            lines.append(f"Relevanter Plan: `{plan_id}` — {plan_title}")
    else:
        lines.append("Relevanter Plan: _keiner_")

    return lines


def _read_handoff_tail(path, n_lines, *, read_handoff_fn=None):
    if read_handoff_fn is not None:
        try:
            text = read_handoff_fn(path)
        except Exception:
            return ""
    else:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return ""
    if not text:
        return ""
    split = text.splitlines()
    if n_lines <= 0:
        return "\n".join(split)
    return "\n".join(split[-n_lines:])


def _as_line(value):
    if isinstance(value, str):
        return value
    return str(value)
