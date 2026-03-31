# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 11 + Hilfe-Center + Docker Image + Mobile Fixes
> **Naechste Aufgabe:** Sprint 12 (Governance Light) planen

---

## Naechste Session: Sprint 12

### Sprint 12: Governance & Policies Light

- [ ] `ai_policy` pro Projekt (sandbox/controlled/critical + allowed_models)
- [ ] Governance-Uebersichtsseite (Policy-Level, Rework-Rate, einfache Badges)
- [ ] Exportierbare Snippets fuer CLAUDE.md / AGENTS.md / Hooks (noch ohne Auto-Write)
- [ ] Sprint-Plan in `sprints/sprint-12-governance-feedback-loop.md` vorhanden

### Docker Image Workflow

- [ ] GitHub Actions Pipeline fuer automatischen Build bei Release/Tag
- [ ] README auf GitHub mit Docker-Pull-Anleitung aktualisieren
- [ ] `open-source` Branch pflegen: bei neuen Open-Source-Features Branch updaten, PRO-Code nie mergen

### Hilfe-Center Verbesserungen

- [ ] Englische Version: content/de/ und content/en/, Language Toggle, 22 Topics uebersetzen
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
- **Hilfe-Center Deploy:** `scp` CSS/Templates auf docker-vm, dann `docker cp` + `docker restart sessionpilot-hilfe`
- **Bezahl-Module:** Heatmap (Sprint 10), Model Analytics (Sprint 11), Governance (Sprint 12) = "Starter Pack"
- **Pricing:** Indie 9-12 EUR/Monat, Team 29-39 EUR/Monat - Details in `dokumentenaustausch/SESSIONPILOT-PRICING.md`
- **Docker Image:** `ghcr.io/web-werkstatt/session-pilot` - nur vom `open-source` Branch bauen, nie PRO-Code
- **Git Push Safety:** Nur auf Gitea pushen, GitHub nur nach Rueckfrage
