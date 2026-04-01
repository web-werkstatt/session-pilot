# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-01
> **Status:** Kette Messen→Auditieren→Bewerten→Steuern→Copilot komplett. Masterplan v0.3.
> **Naechste Aufgabe:** Perplexity Copilot-Workflow aktivieren — Specs generieren lassen, Claude Code ausfuehrt

---

## Was in dieser Session fertig wurde

Sprints A-E + Copilot Chat in einer Session implementiert:
- **Sprint A:** Quality Scanner Spec (SPEC-QUALITY-SCANNER-MVP-001)
- **Sprint B:** Quality Scanner validiert + 2 Fixes + 20 Tests
- **Sprint C:** Governance Light (Ampel green/yellow/red) + 11 Tests
- **Sprint D:** LLM Command Hub (3 Commands, Perplexity) + 15 Tests
- **Copilot:** Chat mit Perplexity, Thread-Historie, Plan-Bindung + 12 Tests
- **Sprint E:** Plan-Workflow Micro-Ebene (Ist/Soll/Next, Signale) + 16 Tests
- **Commit:** `7040d27` — 40 Dateien, 4230 Zeilen, 84 neue Tests

---

## Naechste Session

### Prioritaet 1: Copilot-Workflow nutzen
- [ ] Perplexity als Copilot einsetzen: Projekt waehlen, Spec generieren lassen
- [ ] Generierte Spec als .md ins Repo, Claude Code fuehrt aus
- [ ] Review-Loop: Ergebnis an Perplexity, prueft PASS/FAIL

### Prioritaet 2: LLM-agnostischer Connector
- [ ] Spec von Perplexity schreiben lassen (llm_connector.py Abstraktionsschicht)
- [ ] Perplexity nur ein Provider, OpenRouter/lokal spaeter

### Prioritaet 3: Pre-Commit Zeilenlimits fixen
- [ ] services/db_service.py: 516 Zeilen (Limit 500) — ensure_plan_workflow_schema auslagern
- [ ] services/governance_service.py: 519 Zeilen (Limit 500) — Gate-Logik auslagern
- [ ] static/css/governance.css: 413 Zeilen (Limit 400) — Health-Badges auslagern

### Offene Bugs / Datenluecken (unveraendert)
- [ ] joshko (6 Sessions), llm-test (1 Session) - Projektnamen ohne Verzeichnis
- [ ] 80 Sessions ohne Modell (26x claude, 25x codex, 8x gemini)
- [ ] 0/357 Sessions haben cost_estimate - Backfill-Script
- [ ] TOC top: 188px ist hardcoded

### Nicht vergessen
- **Rollenmodell:** Perplexity = Copilot (plant/reviewt), Claude Code = Executor (.md), Joseph = Abnahme
- **PERPLEXITY_API_KEY** ist in .env gesetzt und funktioniert
- **Masterplan:** sprints/master-plan-2026-04-01.md (v0.3, in .gitignore)
- **Copilot-Doku:** docs/copilot-implementation-status.md (komplett)
- **Git Push Safety:** Nur auf Gitea pushen, GitHub nur nach Rueckfrage
- **Keine Hintergrund-Scanner:** jscpd/auto_coder nur on-demand, nie automatisch
