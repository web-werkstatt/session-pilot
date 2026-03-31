# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 9 done, Sprint 10 done, Sprint 11 pruefen
> **Naechste Aufgabe:** Sprint 11 Spec gegen Code pruefen

---

## Was wurde in dieser Session gemacht

### Sprint 9: Akzeptanzkriterien geprueft (15/15 DONE)
- Alle 15 Kriterien gegen Implementierung verifiziert
- Uncommitted Changes committed: Multi-Value Outcome Filter, Project Policy Defaults, Deeplink-Support

### Sprint 10: Per-File AI-Heatmap komplett ueberarbeitet (13/13 DONE)
- **10.1 Schema:** 5 fehlende Spalten nachgeruestet (project, ai_written, ai_touched, model, issue_category), UNIQUE Constraint, Partial Index, ALTER TABLE fuer bestehende DB
- **10.2 Extraktion:** Import-Integration in session_import.py (fehlte komplett), Git-Diff-Fallback fuer Sessions ohne Tool-Calls, ON CONFLICT statt DELETE+INSERT, --with-file-touches in backfill_ai_flags.py
- **10.3 Heatmap-API:** Spec-Parameter (period/depth/model/category/only_written), SQL-seitige Verzeichnis-Aggregation via split_part, outcome_stats mit reverted getrennt, models pro Datei via Subquery, top_reason via MODE()
- **10.4 Heatmap-UI:** Period/Model/Category Filter-Dropdowns (fehlten alle), Rework-Rate Spalte mit Farbcodierung gruen/gelb/rot, Category-Spalte mit top_reason, Verzeichnisbaum (Dir fett, Children eingerueckt)
- **10.5 Risk-Radar:** Panel VOR den Tabs (war nur im Heatmap-Tab), laedt beim Seitenstart, drill_down URL pro Hotspot, LIMIT 3, outcome Filter in SQL
- **10.6 Hotspot-Warnungen:** _check_ai_hotspots() im Notification-Checker, >10 Touches/7d und >25% Rework-Rate, AI Hotspot Badge + Tooltip
- **10.7 Dashboard-Widget:** /api/widgets/ai-hotspots Endpoint, renderAiHotspots() in widgets.js, Widget in index.html, optionaler ?project= Filter
- **10.8 Drill-down:** Arrow-Links in jeder Heatmap-Zeile, file/file_prefix Filter in Session-API via Join mit ai_file_touches
- **10.9 UI:** risk-radar-panel CSS, Responsive Media Query, Dashboard-Widget HTML

---

## Naechste Session

### Sprint 11 pruefen (Model Comparison)

- Sprint-Plan: sprints/sprint-11-model-quality-comparison.md
- Gleiche Methodik: Spec Punkt fuer Punkt gegen Code pruefen

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
