# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-28
> **Status:** Auto-Coder Quality Pipeline geplant (Sprint 5-8)
> **Naechste Aufgabe:** Sprint 5 - Package + Scanner implementieren

---

## Session 2026-03-28 - Codebasis-Analyse + Quality Pipeline Planung

### Was wurde erledigt
- **Codebasis-Analyse** mit Serena: Alle Module, Schichten, Duplikationen identifiziert
  - Services: 25 Module, 5.086 Zeilen -- HTTP/Cache-Pattern 7x dupliziert
  - Routes: 21 Blueprints, 4.628 Zeilen -- JSON-Persistierung 5x dupliziert
  - Frontend: 29 CSS (5.247Z), 30+ JS (8.800Z) -- escapeHtml() 6x, .stat 7x dupliziert
- **Auto-Coder Quality Pipeline** konzipiert:
  - DeRep Middleware (Post-Processing fuer Claude-Output)
  - Automatischer Scanner mit modularen Checks
  - Claude Code Fix-Loop (headless Issues beheben)
  - Dashboard-Integration (Score-Badge, Detail-Tab, Verlaufs-Chart)
- **4 Sprint-Plaene erstellt:**
  - `sprints/05-roadmap-quality-pipeline.md` (Roadmap + Architektur)
  - `sprints/sprint-5-scanner.md` (Package + 7 Checks + CLI)
  - `sprints/sprint-6-derep-fixer.md` (DeRep + Fix-Loop)
  - `sprints/sprint-7-ui-integration.md` (API + UI)
  - `sprints/sprint-8-automation.md` (Scheduler + Tuning)
- **Serena** fuer project_dashboard aktiviert (.serena/ Config)

### Neue Dateien
| Datei | Zweck |
|-------|-------|
| sprints/05-roadmap-quality-pipeline.md | Roadmap Quality Pipeline |
| sprints/sprint-5-scanner.md | Sprint 5: Package + Scanner |
| sprints/sprint-6-derep-fixer.md | Sprint 6: DeRep + Fixer |
| sprints/sprint-7-ui-integration.md | Sprint 7: API + UI |
| sprints/sprint-8-automation.md | Sprint 8: Automation |
| docs/plan-auto-coder.md | Detailplan (Referenz) |
| .serena/project.yml | Serena-Konfiguration |

---

## Naechste Session: Sprint 5 starten

### Aufgaben
- [ ] `auto_coder/__init__.py` + `__main__.py` + `config.py` erstellen
- [ ] `auto_coder/report.py` -- Datenklassen (Issue, QualityReport)
- [ ] `auto_coder/checks/__init__.py` -- BaseCheck Interface
- [ ] `auto_coder/checks/file_sizes.py` -- Dateigroessen-Limits
- [ ] `auto_coder/checks/duplication.py` -- DRYwall/jscpd
- [ ] `auto_coder/checks/complexity.py` -- Radon (Python)
- [ ] `auto_coder/checks/css_quality.py` -- CSS-Token-Pruefung
- [ ] `auto_coder/checks/js_quality.py` -- JS-Funktionsduplikate
- [ ] `auto_coder/checks/architecture.py` -- Schicht-Regeln
- [ ] `auto_coder/checks/tests.py` -- Test-Erkennung
- [ ] `auto_coder/scanner.py` -- Orchestrator
- [ ] `auto_coder/cli.py` -- CLI (scan, report)
- [ ] Erster Scan auf project_dashboard ausfuehren

### Referenz
- Sprint-Plan: `sprints/sprint-5-scanner.md`
- Architektur: `sprints/05-roadmap-quality-pipeline.md`

### Hinweise
- radon bereits installiert: `/home/joshko/.local/bin/radon`
- jscpd via npx verfuegbar (v4.0.8)
- DRYwall Plugin aktiv in Claude Code settings
- Serena MCP Server konfiguriert
- Alle Module unter 500 Zeilen halten!
