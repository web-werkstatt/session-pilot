# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-02
> **Status:** Test-Cleanup abgeschlossen, Handoff-Service sauber, Copilot-Landing-Seite neu. 258/259 Tests gruen.
> **Naechste Aufgabe:** Quality-Scanner Re-Scan, dann Copilot-Board visuell testen

---

## Was in dieser Session fertig wurde (2026-04-02)

### Sprint M: Test-Cleanup fuer Plan-Tests
- pytest-Fixtures in `test_plan_workflow.py` und `test_plan_sections.py` auf `yield` + `DELETE` umgebaut
- Alle Test-Plans tragen jetzt `[TEST]`-Prefix im Titel (eindeutig als Testdaten erkennbar)
- Kaskadierender Teardown: copilot_messages → copilot_threads → plan_sections → project_plans
- Inline-Plan in `test_handoff_missing_signals` mit `try/finally` gesichert
- `test_project_handoff.py`: [TEST]-Prefix fuer Konsistenz, Assertion angepasst
- **68 Tests gruen, 0 Test-Plans verbleiben in der DB nach pytest-Lauf**
- Geaenderte Dateien: `tests/test_plan_workflow.py`, `tests/test_plan_sections.py`, `tests/test_project_handoff.py`

### Sprint K: Copilot-Landing-Seite
- `/copilot` ohne `plan_id` zeigt jetzt eigene Landing-Seite statt Redirect auf `/plans`
- Letzte Projekte als Chips im sticky Header (mit Plan-Count, Active/Done Pills)
- Plan-Cards darunter mit direktem Link zu `/copilot?plan_id=X`
- Neue Dateien: `templates/copilot_landing.html`, `static/css/copilot_landing.css`, `static/js/copilot_landing.js`
- Neue API: `GET /api/copilot/stats` (Plan-Pipeline, Section-Stats, Recent Projects, Active Plans)
- Route `copilot_routes.py` umgebaut: kein Redirect mehr, rendert Landing-Template

### Sprint L: Handoff-Service Cleanup (sauberer Umbau)
- **Altes Modell entfernt:** Keine `handoff-<plan_id>.md` pro Plan mehr, keine `plans/handoff/next-session-*.md`
- **Neues Modell:** Pro Projekt genau eine Datei: `/mnt/projects/<project_id>/handoff.md`
- **Service:** `project_handoff_service.py` hat nur noch 3 Funktionen:
  - `get_handoff_path(project_id)` — Pfad
  - `build_handoff_markdown(project_id)` — Markdown aus DB generieren
  - `write_handoff(project_id)` — Schreiben
- **4 Aufrufer direkt migriert** (keine Kompatibilitaets-Wrapper):
  - `routes/plans_routes.py` — plan_id→project_name Lookup + write_handoff()
  - `services/llm_command_service.py` — plan_id→project_name Lookup + write_handoff()
  - `services/project_memory_service.py` — write_handoff(project_name)
  - `tests/test_project_handoff.py` — komplett neu (9 Tests fuer neue API)
- **Bereinigt:** 656 alte `handoff-*.md` + 12 `next-session-*.md` + Ordner `plans/handoff/` geloescht
- **Alte Funktionen komplett entfernt:** ensure_handoff_for_plan, read_handoff_for_plan, ensure_handoffs_for_project, resolve_project_name_for_plan
- **Tests angepasst:** test_copilot.py, test_plan_sections.py (302→200), test_plan_workflow.py (neues Template)

### DB-Bereinigung
- 673 + 135 Test-Plans entfernt (Test Workflow Plan, Test Section Plan, Handoff Test Plan)
- 15 "Handoff No-Project" Drafts entfernt
- 371 + 60 zugehoerige Sections entfernt
- 13 Copilot-Threads entfernt
- Verbleibend: 36 echte Plans

### Testergebnis
- **258 gruen, 1 rot**
- Roter Test: `test_quality_scanner.py::TestR6IgnoreDirs::test_no_issues_from_ignored_dirs`
  - Ursache: gecachter `.quality/report.json` enthaelt veralteten Eintrag `dup-007` der auf `.claude/backups/` verweist
  - Fix: Re-Scan via `auto_coder.scanner.ProjectQualityScanner` + `auto_coder.report.save_report()`
  - Unabhaengig von Handoff-Aenderungen

---

## Naechste Session

### PRIORITAET 1: Quality-Scanner Re-Scan
- [ ] `auto_coder/scanner.py` API lesen (ProjectQualityScanner.scan())
- [ ] `auto_coder/report.py` API lesen (save_report())
- [ ] Re-Scan fuer project_dashboard ausfuehren, `.quality/report.json` aktualisieren
- [ ] `TestR6IgnoreDirs` muss danach gruen sein (259/259)

### PRIORITAET 2: Copilot-Board visuell testen
- [ ] /copilot?plan_id=X zeigt Section-Board — Board-Spalten und Card-Logik pruefen
  - Spalten: backlog/ready/in_progress/review/done/blocked
  - Cards = plan_sections, NICHT project_plans
  - Drag & Drop aendert plan_sections.status
  - Modal-Chat gebunden an section_id
- [ ] Visueller QA-Test: Sections anlegen, zwischen Spalten verschieben, Chat oeffnen
- [ ] Sicherstellen dass /plans (Level 1) NICHT durch Section-Logik beeinflusst wird

### Prioritaet 3: Copilot-Workflow nutzen
- [ ] Perplexity als Copilot einsetzen: Projekt waehlen, Spec generieren lassen
- [ ] Generierte Spec als .md ins Repo, Claude Code fuehrt aus
- [ ] Review-Loop: Ergebnis an Perplexity, prueft PASS/FAIL

### Prioritaet 4: LLM-agnostischer Connector
- [ ] Spec von Perplexity schreiben lassen (llm_connector.py Abstraktionsschicht)
- [ ] Perplexity nur ein Provider, OpenRouter/lokal spaeter

### Prioritaet 5: Pre-Commit Zeilenlimits fixen
- [ ] services/db_service.py: 516 Zeilen (Limit 500) — ensure_plan_workflow_schema auslagern
- [ ] services/governance_service.py: 519 Zeilen (Limit 500) — Gate-Logik auslagern
- [ ] static/css/governance.css: 413 Zeilen (Limit 400) — Health-Badges auslagern

### ~~Prioritaet 6: Test-Cleanup automatisieren~~ — DONE (Sprint M)
- [x] pytest-Fixtures bereinigen: yield + DELETE in allen Plan-Test-Fixtures
- [x] [TEST]-Prefix, kaskadierender Teardown, 0 DB-Leichen nach pytest

### Offene Bugs / Datenluecken
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
- **Level-Architektur:** /plans = Plan-Board (Level 1), /copilot?plan_id=X = Section-Board + Chat (Level 2), keine dritte Ebene
- **Handoff-Service:** project_handoff_service.py — 3 Funktionen (get_handoff_path, build_handoff_markdown, write_handoff), eine handoff.md pro Projekt, keine plan-spezifischen Dateien
