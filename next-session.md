# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 12 done, Sprint 9 Nacharbeiten groesstentils done, UI-Fixes
> **Naechste Aufgabe:** Sprint 9 restliche Punkte (9.6-9.8) pruefen, dann Sprint 10

---

## Was wurde in dieser Session gemacht

### Sprint 12: AI Governance & Policies Light (DONE)
- Komplettes Governance-System: Policy-CRUD, Rule-Generator, Feedback-Loop
- Governance-Seite, Dashboard-Widget, Projekt-Detail-Tab, Sidebar-Link
- Hilfe-Center Topic + Sprint-Historie + Seitenuebersicht aktualisiert
- Deployed auf doc.session-pilot.com inkl. Sitemap-Route

### Datenbereinigung (DONE)
- DB: Projektnamen normalisiert (7 Paare Bindestrich->Unterstrich)
- DB: gemini:hash, ~ (Home), <synthetic> bereinigt
- Import: _resolve_dir_name() prueft echte Verzeichnisse
- Filter: model NOT LIKE <%> in allen Sprint 9-11 Queries nachgezogen
- Phantom-Projekte aus allen Dropdowns gefiltert

### Sprint 9 Nacharbeiten (DONE)
- Codex/Gemini Import: AI-Flags (ai_has_writes, ai_has_tool_calls, ai_tools_used)
- Outcome-Dialog: Reason-Dropdown (22 Kategorien) + Severity in Detail + Quick-Rate
- Rework-API: reason_distribution, reason_by_model, reason_by_project, reason_trend
- Default-Filter: project_defaults in /api/sessions/filters per Policy-Level
- Drill-down: Rework by Project + Top Reasons mit Session-Links in Timesheets
- Fehlende Outcome-Reasons ergaenzt: wrong_api, security, style_drift, hallucination, other
- Reason-Labels mit key/label/category in outcome-reasons API
- Validierung: ungueltige reason/severity werden mit 400 abgelehnt
- Backfill-Script: --full und --project Flags, nur unbearbeitete Sessions
- Sessions-Filter: hardcoded Dropdowns -> dynamisch via /api/sessions/filters
- Model-Filter + outcome_reason Filter im Backend
- AI-Scope: Checkbox "AI-relevant only" + Scope-Dropdown statt Buttons
- Quick-Rate Popup direkt in Sessions-Liste (kein Navigieren zur Detail-Seite)

### Session-Detail UI-Fixes (DONE)
- Buttons gestyled: Back, Rate, Export (waren vorher unsichtbar/ungestyled)
- Rate-Button zeigt aktuellen Outcome-Status
- TOC: Texte gekuerzt (40 statt 60 Zeichen), klappbare Turns
- TOC: position fixed rechts, scrollt nicht mehr mit
- Meta-Bar + Export-Bar: sticky unter Topbar
- Leere System-Messages werden nicht mehr gerendert

### Model Comparison Fixes (DONE)
- kpi-row CSS ergaenzt, thead sticky fix, Stack-Toggle CSS/JS Mismatch
- Projekt-Dropdown: nur echte Projekte mit Sessions
- Modelle ohne Ratings zeigen "No ratings" statt F/0.0
- <synthetic> aus Materialized View und allen Queries gefiltert

### Sprint 15 Plan erstellt
- sprints/sprint-15-turn-level-rating.md - Abschnitt-Bewertung innerhalb Sessions

---

## Naechste Session

### Sprint 9 restliche Punkte pruefen

- [ ] 9.6: Filter "Sessions mit Revert/Needs Fix" - Outcome-Dropdown vorhanden, aber outcome_reason als URL-Param testen
- [ ] 9.7: Default-Filter pro Policy-Level - API liefert project_defaults, Frontend setzt sie beim Laden?
- [ ] 9.8: Drill-down Quicklinks - in Rework-Tabelle vorhanden, auch in anderen Tabellen?
- [ ] Alle 14 Akzeptanzkriterien nochmal durchgehen

### Sprint 10 pruefen (File Heatmap)

- Sprint-Plan: sprints/sprint-10-file-heatmap.md
- Gleiche Methodik: Spec Punkt fuer Punkt gegen Code pruefen

### Sprint 11 pruefen (Model Comparison)

- Sprint-Plan: sprints/sprint-11-model-quality-comparison.md

### Offene Bugs / Datenluecken

- [ ] joshko (6 Sessions), llm-test (1 Session) - Projektnamen ohne Verzeichnis
- [ ] 80 Sessions ohne Modell (26x claude, 25x codex, 8x gemini)
- [ ] 0/357 Sessions haben cost_estimate - Backfill-Script
- [ ] TOC top: 188px ist hardcoded - sollte dynamisch berechnet werden

### Docker Image Workflow

- [ ] GitHub Actions Pipeline fuer automatischen Build bei Release/Tag
- [ ] README auf GitHub mit Docker-Pull-Anleitung aktualisieren
- [ ] open-source Branch pflegen

### Hilfe-Center

- [ ] Englische Version: content/de/ und content/en/, Language Toggle, 25 Topics

### Offene Punkte aus vorherigen Sessions

- [ ] Woechentlich/Monatlich-Views in Usage Reports testen
- [ ] Custom Date Range testen
- [ ] Cache-Tokens separat in Tabelle
- [ ] OTel verifizieren
- [ ] Scoring-Tuning: Score-Cap pro Kategorie

### Nicht vergessen

- Codex-Import unterstuetzt ~/.codex/sessions/YYYY/MM/DD/*.jsonl
- Bestehende projects-Tabelle existiert NICHT in DB - Projekte = Verzeichnisse + project.json
- UI komplett Englisch, Mehrsprachigkeit erst Sprint 15
- Design-Tokens aus static/css/design-tokens.css verwenden
- Modals ueber base.js openModal(id)/closeModal(id), API-Calls ueber api.js
- **MODULAR BAUEN:** Eigene Dateien pro Concern
- **Hilfe-Center Deploy:** Content nach docker-vm:/opt/sessionpilot-hilfe/content/, dann docker restart
- **Hilfe-Center App Deploy:** scp app.py nach docker-vm, docker cp + docker restart
- **Bezahl-Module:** Heatmap + Model Analytics + Governance = Starter Pack komplett
- **Docker Image:** ghcr.io/web-werkstatt/session-pilot - nur vom open-source Branch
- **Git Push Safety:** Nur auf Gitea pushen, GitHub nur nach Rueckfrage
- **VERIFY BEFORE SHIPPING:** Spec Punkt fuer Punkt gegen Code pruefen, echte Daten testen, CSS-Klassen verifizieren
