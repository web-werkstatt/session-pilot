# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-31
> **Status:** Sprint 9 done, Sprint 10 done, Sprint 11 done
> **Naechste Aufgabe:** Sprint 12 planen oder offene Bugs/Datenluecken angehen

---

## Was wurde in dieser Session gemacht

### Sprint 11: Model Quality Comparison - Spec-Abgleich + Nachruesten

**11.1 Backend: Modell-Qualitaets-Aggregation**
- `provider`-Feld nachgeruestet: dynamisch aus `model_pricing`-DB-Tabelle (kein Hardcoding)
- `top_reasons` pro Modell nachgeruestet: `_fetch_top_reasons()` mit Security-Count-Extraktion
- `outcome_severity::int` Cast-Bug gefixt (Spalte enthaelt Strings wie 'high', nicht Zahlen) - betrifft MV und direkten Query

**11.2 Stack-spezifische Fehlerraten**
- `cost_per_success` pro Model/Stack nachgeruestet
- Dominanter-Stack-Logik (>50% Touches) statt Mehrfachzaehlung pro File-Touch
- Cross-Stack-Insight ("2x hoehere Rework-Rate bei TS vs Python")
- Response-Format auf verschachtelte Struktur umgestellt (gruppiert nach Stack)

**11.3 Quality-Score**
- Security-Malus (-10 bei >3 Security-Issues) nachgeruestet
- Security-Count aus outcome_reasons extrahiert (unabhaengig vom Top-3-Limit)

**11.4 UI: Modell-Vergleichsseite**
- Scatter-Plot (Bubble-Chart: $/Success vs Rework-Rate, Bubble=Sessions) nachgeruestet
- Provider-Tags und Reason-Tags im CSS ergaenzt

**11.5 Empfehlungs-Engine**
- Alternative-Begruendung mit Kostenverhaeltnis ("8x more expensive") nachgeruestet
- Badge im Projekt-Detail war bereits implementiert

**11.6 Trend-Analyse**
- Sparkline-Tooltip ("Rework: X% -> Y% over N periods") nachgeruestet
- Period-Format auf ISO-Wochen (2026-W09) umgestellt

**11.7 Drill-down-Quicklinks**
- Stack-Filter in Sessions-Endpoint nachgeruestet (`?stack=python`)
- Stack-Chart onClick-Handler: Klick auf Bar navigiert zu `/sessions?model=X&stack=Y`

**11.8 UI-Implementierung**
- "Model Comparison →" Link in Session-Analysis nachgeruestet
- Sidebar-Navigation, Template, CSS, JS waren bereits vollstaendig

---

## Naechste Session

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
