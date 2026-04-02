# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-02
> **Status:** Sprint N Copilot UX Redesign abgeschlossen
> **Naechste Aufgabe:** -

---

## Was in dieser Session fertig wurde (2026-04-02)

### Sprint N: Copilot UX Redesign — AI-native Work OS
**Vision:** Von "Kanban + Chat" zu "AI-native Work OS"

**Features:**
- **Split View Layout:** Board links, Slide-in Panel rechts (CSS Grid + Animation)
- **Side Panel:** Zeigt Section-Info, AI-Preview, Live-Chat
- **Rich Cards:** AI-Message-Count + Preview der letzten Antwort
- **Column Microcopy:** Emoji + Beschreibung pro Spalte (💡 Backlog: "Noch zu klären", etc.)
- **Flow Guidance Header:** 4-Schritt-Hinweis oben im Board
- **Landing Page Redesign:** Stats, Continue-Card, Quick-Start
- **Drag & Drop:** Card-Hintergrund ändert sich mit Status
- **KI-Farbe:** Lila → Blau (#1f79f0)

**Dateien:**
- `templates/copilot_board.html` — Split View, Side Panel
- `static/js/copilot_board.js` — Panel-Toggle, AI-Previews, Click/Drag Handler
- `static/css/copilot.css` — Panel-Styles, Glows, Microcopy, Farben
- `templates/copilot_landing.html` — Stats, Continue, Quick-Start
- `services/plan_section_service.py` — `get_section_ai_preview()`
- `routes/section_routes.py` — `/api/copilot/ai-previews`
- `sprints/sprint-n-copilot-ux-redesign.md` — Sprint-Dokumentation

**Tests:** 28/28 bestanden

### Sprint M2.8: Quality-Scanner Re-Scan
- Fix: `duplication.py` — jscpd `--ignore` Pattern `node_modules` → `**/node_modules/**`
- Ergebnis: 259/259 Tests grün

---

## Naechste Session

### Offene Aufgaben

- [ ] Copilot-Workflow: Perplexity als Copilot einsetzen
- [ ] LLM-agnostischer Connector (llm_connector.py)
- [ ] Pre-Commit Zeilenlimits fixen (db_service.py, governance_service.py)

### Nicht vergessen
- **Rollenmodell:** Perplexity = Copilot (plant/reviewt), Claude Code = Executor (.md), Joseph = Abnahme
- **Level-Architektur:** /plans = Plan-Board (Level 1), /copilot?plan_id=X = Section-Board + Chat (Level 2)
- **Handoff-Service:** project_handoff_service.py — 3 Funktionen, eine handoff.md pro Projekt
