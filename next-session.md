# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 10 abgeschlossen (Per-File AI-Heatmap + Risk Radar)
> **Naechste Aufgabe:** Sprint 11 planen

---

## Erledigt: Sprint 9 (2026-03-31)

- DB-Migration: outcome_reason, outcome_severity, ai_has_writes, ai_has_tool_calls, ai_tools_used
- Neues Modul `services/ai_scope_service.py` - Tool-Erkennung, Write-Detection
- Neues Modul `routes/session_filter_routes.py` - Filter-API, Outcome-Reasons, Scope-Stats
- Neues Modul `static/js/session-filters.js` + `static/css/session-filters.css`
- Backfill: 264/344 Sessions mit Tool-Calls, 251 mit Writes
- Gitea Issue #9 geschlossen, Commit e1ec0b2

## Erledigt: Sprint 10 (2026-03-31)

- DB-Migration: `ai_file_touches` Tabelle (file_path, touch_type, tool_name, session_id, timestamp)
- Neues Modul `services/file_touch_service.py` - Touch-Extraktion aus tool_use, Heatmap-Aggregation, Risk-Radar
- Neues Modul `routes/analytics_routes.py` - `/api/analytics/file-heatmap/<project>` + `/api/analytics/risk-radar/<project>`
- Neues Modul `static/js/file-heatmap.js` + `static/css/file-heatmap.css` - Heatmap-Tab in Projekt-Detail
- Neues Script `scripts/backfill_file_touches.py` - 29.238 Touches aus 267/351 Sessions extrahiert
- Neuer Tab "AI Heatmap" in project_detail.html mit Risk Radar, Sortierung, Filter, Trend-Chart
- Gitea Issue #10 geschlossen

## Naechste Session: Sprint 11

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
