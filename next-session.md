# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 11 abgeschlossen + Hilfe-Center deployed
> **Naechste Aufgabe:** Sprint 12 (Governance Light) planen

---

## Erledigt: Sprint 10 (2026-03-31)

- DB-Migration: `ai_file_touches` Tabelle (file_path, touch_type, tool_name, session_id, timestamp)
- Neues Modul `services/file_touch_service.py` - Touch-Extraktion aus tool_use, Heatmap-Aggregation, Risk-Radar
- Neues Modul `routes/analytics_routes.py` - `/api/analytics/file-heatmap/<project>` + `/api/analytics/risk-radar/<project>`
- Neues Modul `static/js/file-heatmap.js` + `static/css/file-heatmap.css` - Heatmap-Tab in Projekt-Detail
- Neues Script `scripts/backfill_file_touches.py` - 29.238 Touches aus 267/351 Sessions extrahiert
- Neuer Tab "AI Heatmap" in project_detail.html mit Risk Radar, Sortierung, Filter, Trend-Chart
- Gitea Issue #10 geschlossen

## Erledigt: Sprint 11 (2026-03-31)

- DB-Migration: Materialized View `mv_model_quality` + `cost_estimate`/`duration_minutes` Spalten
- Neues Modul `services/model_recommendation.py` - Quality-Score (0-100, A-F), Stack-Erkennung, Empfehlungs-Engine, Trend-Analyse
- Neues Modul `routes/model_comparison_routes.py` - 4 API-Endpoints: model-comparison, model-by-stack, model-trend, model-recommendation
- Neue Seite `/model-comparison` mit Vergleichstabelle, Radar-Chart (Quality/Cost/Speed), Stack-Chart, Sparklines
- Backend/Frontend Stack-Toggle fuer Stack-spezifische Analyse
- Empfehlungs-Badge im Projekt-Detail Header
- Navigation erweitert (nach AI Timesheets)
- Gitea Issue #11

## Erledigt: Hilfe-Center (2026-03-31)

- Hilfe-Center aus Contypio-Vorlage kopiert und fuer SessionPilot angepasst
- 22 Doku-Seiten mit YAML-Frontmatter (Markdown + Flask + Gunicorn)
- 13 Screenshots automatisch erstellt und eingebettet
- SessionPilot Logo + Favicon integriert
- PRO-Badges fuer bezahlte Module (Heatmap, Model Analytics, Empfehlungen, Quality Score)
- Deployed als Docker-Container auf SaaS-Server (168.119.35.184)
- Live unter https://doc.session-pilot.com (Caddy Reverse Proxy + Let's Encrypt SSL)
- Help-Button in Dashboard GUI (Topbar + Sidebar-Footer)
- Doku: `dokumentenaustausch/SESSIONPILOT-PAID-MODULES.md` + `SESSIONPILOT-PRICING.md`

## Naechste Session: Sprint 12

### Sprint 12: Governance & Policies Light

- [ ] `ai_policy` pro Projekt (sandbox/controlled/critical + allowed_models)
- [ ] Governance-Uebersichtsseite (Policy-Level, Rework-Rate, einfache Badges)
- [ ] Exportierbare Snippets fuer CLAUDE.md / AGENTS.md / Hooks (noch ohne Auto-Write)
- [ ] Sprint-Plan in `sprints/sprint-12-governance-feedback-loop.md` vorhanden

### Hilfe-Center Verbesserungen

- [ ] **Englische Version:** content/de/ und content/en/ Verzeichnisse, Language Toggle (DE|EN), URL-Schema /de/topic/X vs /en/topic/X, 22 Topics uebersetzen
- [ ] **Mobile Responsive:** Hilfe-Center Texte brechen auf Mobilgeraeten nicht korrekt um, Layout-Fix noetig (Sidebar, Content-Bereich, Tabellen)
- [ ] Governance-Topics ergaenzen sobald Sprint 12 fertig

### Offene Punkte aus vorherigen Sessions

- [ ] Woechentlich/Monatlich-Views in Usage Reports testen und validieren
- [ ] Custom Date Range testen
- [ ] Cache-Tokens (read/create) separat als Zeile oder Toggle in Tabelle
- [ ] OTel verifizieren (source ~/.bashrc + neue Claude Session)
- [ ] Scoring-Tuning: Score-Cap pro Kategorie
- [ ] cost_estimate Backfill: Sessions haben noch keine Kostenschaetzung in DB

### Nicht vergessen

- Codex-Import (`session_import_multi.py`) unterstuetzt bereits `~/.codex/sessions/YYYY/MM/DD/*.jsonl`
- Bestehende `projects`-Tabelle existiert NICHT in DB - Projekte = Verzeichnisse + project.json
- Sprint-Soll-Werte: Projekt-Policy als Fallback wenn Sprint keine eigenen hat
- UI komplett Englisch, Mehrsprachigkeit erst Sprint 15
- Design-Tokens aus `static/css/design-tokens.css` verwenden, keine hardcoded Farben
- Modals ueber base.js `openModal(id)` / `closeModal(id)`, API-Calls ueber `api.js`
- **MODULAR BAUEN:** Alle Sprints vollstaendig modular - eigene Dateien pro Concern
- Materialized View `mv_model_quality` taeglich refreshen (RemoteTrigger oder Background-Thread)
- **Hilfe-Center Deploy:** `rsync` Content/Templates auf SaaS-Server, dann `docker build + restart`
- **Bezahl-Module:** Heatmap (Sprint 10), Model Analytics (Sprint 11), Governance (Sprint 12) = "Starter Pack"
- **Pricing:** Indie 9-12€/Monat, Team 29-39€/Monat - Details in `dokumentenaustausch/SESSIONPILOT-PRICING.md`
