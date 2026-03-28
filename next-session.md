# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-29
> **Status:** Quality-Pipeline komplett, UI massiv verbessert
> **Naechste Aufgabe:** Komplette Umstellung auf Englisch

---

## Session 2026-03-28/29 (Abend/Nacht) - Quality + UI Sprint

### Was wurde erledigt

**Quality Pipeline (Issues #5-#7):**
- detect_tags() konsolidiert, Scanner-Rauschen -46%, Warnings 347->189
- Baseline + Diff CLI, Pre-commit Hook, auto_coder als eigenstaendiges Projekt
- AI Quality Templates (AI_QUALITY.md, AI_TASKS.md) mit Init-Script

**Quality Dashboard (Issue #8):**
- /quality Seite mit Projekt-Tabelle, Score, Scan/Baseline Buttons
- Quality-Tab in Projekt-Detail-Seite mit Issues nach Kategorie
- Scan-Fortschrittsanzeige (progress.json Polling)
- Timeout 120s->300s, jscpd 120s->60s

**Projekt-Detail Verbesserungen:**
- Uebersicht zweispaltig (Grid) mit sticky TOC rechts
- Sessions-Tab als richtige Tabelle (wie Sessions-Hauptseite)
- Plans-Tab: verschachtelte Links behoben, 404 gefixt
- Git-Panel unter Sessions-Tabelle mit Legende (M/A/D/?) auf Englisch
- Session-Filter matcht jetzt auch Bindestrich/Unterstrich-Varianten

**UI/Design:**
- Akzentfarbe von Cyan #4fc3f7 auf Stahlblau #5b9bd5
- Lila Card-Hintergrund #1e1e2e durch neutrales #222
- Lila Code-Statistik-Balken #1a1a2e durch #222
- Prio-Icons: Leerer Kreis -> Pfeile (arrow-up/minus/arrow-down)
- Account-Badge Styling fuer account1 und codex
- Zeilennummern in Code-Bloecken der Session-Ansicht
- Plans: Manuelle Status-Buttons entfernt (Auto-Status reicht)

**README + GitHub:**
- Code Quality Feature dokumentiert mit Screenshot
- API-Endpoints, Roadmap aktualisiert

---

## Naechste Session

### Aufgaben (Prioritaet)
- [ ] **Komplette Umstellung auf Englisch** - Templates, JS, Python-Routes
  - Templates (15+): Tab-Labels, Buttons, Ueberschriften, Platzhalter
  - JS-Dateien (10+): UI-Texte, Fehlermeldungen, Tooltips
  - Python-Routes (5+): Server-generierte h3 (Beschreibung, Details, Letzte Commits etc.)
  - Systematisch mit Agents parallelisieren

### Weitere Aufgaben
- [ ] Scoring-Tuning: Score-Cap pro Kategorie (aktuell F bei 189 Warnings)
- [ ] Sprint 6: DeRep + Fixer
- [ ] auto_coder README: Architektur-Skizze + Roadmap

### Offene Punkte
- CSS-Duplikate (12x): Warten auf Design-Refactor
- auto_coder: Weitere Checks (Security, Dependencies), HTML-Reports, CI-Integration

### Referenz
- auto_coder Projekt: `/mnt/projects/auto_coder/`
- Quality Roadmap: `sprints/05-roadmap-quality-pipeline.md`
- Baseline: `.quality/baseline.json` (189 Warnings, 13 Errors)
