# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 12 fertig + Hilfe-Center aktualisiert
> **Naechste Aufgabe:** Sprint 13 planen / Docker Image Workflow

---

## Was wurde in dieser Session gemacht

### Sprint 12: AI Governance & Policies Light (DONE)

**16 Dateien, 1712 Zeilen, 2 Commits:**

- `services/governance_service.py` - Policy-CRUD, Governance-Overview, Rework-Rates, Wirkungs-Tracking, Snippet-Generator
- `services/rule_generator.py` - 17 Rule-Templates, Top-Fehlergrund-Analyse, Feedback-Loop
- `routes/governance_routes.py` - 8 API-Endpoints (Overview, Policy GET/PUT, Rules, Apply, Effectiveness, Feedback-Loop, Snippets)
- `templates/governance.html` - Governance-Seite mit 4 Tabs (Overview, Rules, Feedback, Snippets)
- `static/css/governance.css` - Policy-Badges, Rule-Cards, Snippet-Boxes, responsive
- `static/js/governance.js` - Alle Interaktionen, Modals, Copy-to-Clipboard
- Sidebar-Link, Dashboard-Widget, Governance-Tab in Projekt-Detail
- Gitea Issue #12 erstellt und via Commit geschlossen

### Hilfe-Center Update (DONE)

- `hilfe-center/content/governance.md` - Neues Topic mit NEW-Badge
- Sprint-Historie + Seitenuebersicht aktualisiert
- Deployed auf doc.session-pilot.com via docker-vm

---

## Naechste Session

### Sprint 13 planen

- Sprint-Plan erstellen in `sprints/sprint-13-*.md`
- Moegliche Themen:
  - Team-Dashboard / Multi-User
  - Compliance-Report Export
  - Cross-Projekt Fehler-Analyse
  - LLM-basierte Regel-Generierung statt Templates

### Docker Image Workflow

- [ ] GitHub Actions Pipeline fuer automatischen Build bei Release/Tag
- [ ] README auf GitHub mit Docker-Pull-Anleitung aktualisieren
- [ ] `open-source` Branch pflegen: bei neuen Open-Source-Features Branch updaten, PRO-Code nie mergen

### Hilfe-Center Verbesserungen

- [x] Governance-Topic ergaenzt (Sprint 12 fertig)
- [ ] Englische Version: content/de/ und content/en/, Language Toggle, 25 Topics uebersetzen

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
- **Hilfe-Center Deploy:** Content nach docker-vm:/opt/sessionpilot-hilfe/content/ kopieren, dann `docker restart sessionpilot-hilfe` (Volume ist read-only gemounted, Host-Pfad beschreiben)
- **Bezahl-Module:** Heatmap (Sprint 10), Model Analytics (Sprint 11), Governance (Sprint 12) = "Starter Pack" komplett
- **Pricing:** Indie 9-12 EUR/Monat, Team 29-39 EUR/Monat - Details in `dokumentenaustausch/SESSIONPILOT-PRICING.md`
- **Docker Image:** `ghcr.io/web-werkstatt/session-pilot` - nur vom `open-source` Branch bauen, nie PRO-Code
- **Git Push Safety:** Nur auf Gitea pushen, GitHub nur nach Rueckfrage
