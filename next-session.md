# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-28
> **Status:** auto_coder als eigenstaendiges Projekt extrahiert, Quality-Workflow komplett
> **Naechste Aufgabe:** Scoring-Tuning oder Sprint 6 (DeRep + Fixer)

---

## Session 2026-03-28 (Abend) - Quality Pipeline + Duplikat-Sprint

### Was wurde erledigt

**1. Tag-Erkennung konsolidiert (Issue #5):**
- Zentrale `detect_tags()` in `project_detector.py`, 3 Duplikate entfernt

**2. Scanner-Rauschen + Code-Duplikate bereinigt (Issue #6):**
- IGNORE_DIRS erweitert (.claude/, backups/, _archive/), Same-File -> info
- `escapeHtml()` (5x) und `formatTimeAgo()` (2x) nach base.js konsolidiert
- `create_session_meta()` und `update_time_range()` in session_import_utils.py
- **Warnings 347 -> 189 (-46%)**

**3. Quality Baseline + Diff-Workflow (Issue #7):**
- CLI-Befehle: `auto_coder diff` (Delta zur Baseline), `auto_coder baseline`
- Pre-commit Hook erweitert: Architektur-Guards, Utility-Duplikat-Guard
- Baseline bei 189 Warnings eingefroren

**4. auto_coder als eigenstaendiges Projekt:**
- Extrahiert nach `/mnt/projects/auto_coder/` mit eigener Package-Struktur
- `quality-template/` Bundle: pre-commit, Makefile, CLAUDE-Vorlage
- Validiert ueber 3 Projekte (A/93, F/33, F/0)

### Commits
| Commit | Beschreibung |
|--------|-------------|
| 59ee90a | refactor: detect_tags() konsolidiert (fixes #5) |
| 16a729a | refactor: Scanner-Rauschen + Duplikate (fixes #6) |
| b902488 | docs: CLAUDE.md House-Style-Regeln |
| eedd1ed | feat: Baseline + Diff + Pre-commit (fixes #7) |

---

## Naechste Session

### Aufgaben
- [ ] auto_coder README: Architektur-Skizze + Roadmap-Kapitel ergaenzen
- [ ] Scoring-Tuning: Score-Cap pro Kategorie (aktuell F bei 189 Warnings)
- [ ] Sprint 6: DeRep + Fixer (abhaengig von Sprint 5)
- [ ] Langfristziel: Warnings < 100 (Scout Rule bei jeder Aenderung)

### Offene Punkte
- CSS-Duplikate (12x): Warten auf Design-Refactor
- Gleichnamige JS-Funktionen: Kein echtes DRY-Problem, seitenspezifische Logik
- auto_coder: Weitere Checks (Security, Dependencies), HTML-Reports, CI-Integration

### Referenz
- auto_coder Projekt: `/mnt/projects/auto_coder/`
- Quality Roadmap: `sprints/05-roadmap-quality-pipeline.md`
- Baseline: `.quality/baseline.json` (189 Warnings, 13 Errors)
- Report: `.quality/report.json`
