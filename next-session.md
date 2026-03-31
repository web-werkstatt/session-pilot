# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** AI Governance Roadmap Sprint 9-14+15 vollstaendig geplant, inkl. UI/UX
> **Naechste Aufgabe:** Sprint 9 implementieren (Fehler-Kategorien + AI-Scope-Filter)

---

## Naechste Session: Sprint 9 implementieren

### Reihenfolge (Abhaengigkeiten beachten)

1. **DB-Migration:** outcome_reason, outcome_severity, ai_has_writes, ai_has_tool_calls, ai_tools_used
2. **Session-Import erweitern:** AI-Flags beim Parsen setzen (session_import.py + session_import_multi.py)
3. **Backfill-Script:** scripts/backfill_ai_flags.py fuer bestehende Sessions
4. **API:** /api/sessions/filters (dynamisch), /api/sessions/outcome-reasons, Outcome-API erweitern
5. **UI:** sessions2.css + sessions2.js erweitern (Scope-Dropdown, Checkbox, Reason+Severity im Outcome-Dialog)
6. **Drill-down:** URL-Parameter fuer Filter-Deeplinks

### Sprint 9 UI-Dateien (keine neuen, nur aendern)

- `templates/sessions.html` - Filterleiste + Outcome-Modal erweitern
- `static/css/sessions2.css` - Severity-Badges, Scope-Toggle, Drill-down-Links
- `static/js/sessions2.js` - loadFilters(), applyUrlParams(), onOutcomeChange()

### Offene Punkte aus vorherigen Sessions

- [ ] Woechentlich/Monatlich-Views in Usage Reports testen und validieren
- [ ] Custom Date Range testen
- [ ] Cache-Tokens (read/create) separat als Zeile oder Toggle in Tabelle
- [ ] OTel verifizieren (source ~/.bashrc + neue Claude Session)
- [ ] Scoring-Tuning: Score-Cap pro Kategorie

### Nicht vergessen

- Codex-Import (`session_import_multi.py`) unterstuetzt bereits `~/.codex/sessions/YYYY/MM/DD/*.jsonl`
- Bestehende `projects`-Tabelle existiert NICHT in DB - Projekte = Verzeichnisse + project.json
- Sprint-Soll-Werte: Projekt-Policy als Fallback wenn Sprint keine eigenen hat
- UI komplett Englisch, Mehrsprachigkeit erst Sprint 15
- Design-Tokens aus `static/css/design-tokens.css` verwenden, keine hardcoded Farben
- Modals ueber base.js `openModal(id)` / `closeModal(id)`, API-Calls ueber `api.js`
