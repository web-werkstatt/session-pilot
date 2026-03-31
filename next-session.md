# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 9 abgeschlossen (Fehler-Kategorien + AI-Scope-Filter)
> **Naechste Aufgabe:** Sprint 10 implementieren (Per-File AI-Heatmap + File Analysis)

---

## Erledigt: Sprint 9 (2026-03-31)

- DB-Migration: outcome_reason, outcome_severity, ai_has_writes, ai_has_tool_calls, ai_tools_used
- Neues Modul `services/ai_scope_service.py` - Tool-Erkennung, Write-Detection
- Neues Modul `routes/session_filter_routes.py` - Filter-API, Outcome-Reasons, Scope-Stats
- Neues Modul `static/js/session-filters.js` + `static/css/session-filters.css`
- Backfill: 264/344 Sessions mit Tool-Calls, 251 mit Writes
- Gitea Issue #9 geschlossen, Commit e1ec0b2

## Naechste Session: Sprint 10 - Per-File AI-Heatmap

### Reihenfolge (Abhaengigkeiten beachten)

1. **DB-Schema:** Neue `ai_file_touches` Tabelle (file_path, touch_type, ai_written, ai_touched, session_id)
2. **Data Extraction:** Write/Edit Tool-Calls aus JSONL parsen, Datei-Pfade extrahieren
3. **Backfill:** Bestehende Sessions re-analysieren (--with-file-touches)
4. **API:** `/api/analytics/file-heatmap/<project>` + `/api/analytics/risk-radar/<project>`
5. **Heatmap UI:** Treemap/Table in Projekt-Detail-Tab, farbcodiert nach Rework-Rate
6. **Risk Radar:** Top-3-Hotspots, Top-3-Fehlerkategorien, Trend-Visualisierung

### Sprint 10 - Modularer Aufbau (WICHTIG!)

Alle neuen Dateien separat erstellen:
- `services/file_touch_service.py` - Datei-Touch-Extraktion und Analyse
- `routes/analytics_routes.py` - Heatmap + Risk-Radar API
- `static/js/file-heatmap.js` - Heatmap UI-Logik
- `static/css/file-heatmap.css` - Heatmap Styles
- `scripts/backfill_file_touches.py` - Backfill-Script
- `db_service.py` - nur `ensure_file_touch_schema()` hinzufuegen

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
- **MODULAR BAUEN:** Alle Sprints vollstaendig modular - eigene Dateien pro Concern
