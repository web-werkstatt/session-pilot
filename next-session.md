# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-28
> **Status:** Quality Pipeline Sprint 5 komplett, Duplikat-Bereinigung abgeschlossen
> **Naechste Aufgabe:** Sprint 6 (DeRep + Fixer) oder Scoring-Tuning

---

## Session 2026-03-28 (Abend) - Duplikat-Bereinigung + Scanner-Tuning

### Was wurde erledigt

**Tag-Erkennung konsolidiert (Issue #5):**
- Zentrale `detect_tags()` Funktion in `project_detector.py`
- 3 duplizierte Stellen in scanner/detector zusammengefuehrt

**Scanner-Rauschen reduziert + Code-Duplikate bereinigt (Issue #6):**
- `.claude/`, `backups/`, `_archive/` zu IGNORE_DIRS hinzugefuegt (62 false positives eliminiert)
- Same-File-Duplikate als info statt warning eingestuft (58 Warnings reduziert)
- `escapeHtml()` (5x) und `formatTimeAgo()` (2x) nach base.js konsolidiert
- `create_session_meta()` und `update_time_range()` in session_import_utils.py extrahiert
- CLAUDE.md House-Style-Regeln fuer Utilities und Shared Helpers dokumentiert

**Ergebnis:** Warnings 347 -> 188 (-46%), -45 Zeilen netto

### Betroffene Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/project_detector.py` | detect_tags() hinzugefuegt |
| `services/project_scanner.py` | Tag-Duplizierung entfernt |
| `auto_coder/config.py` | IGNORE_DIRS erweitert |
| `auto_coder/checks/duplication.py` | Same-File info statt warning |
| `static/js/base.js` | escapeHtml, formatTimeAgo hinzugefuegt |
| `static/js/*.js` (6 Dateien) | Duplikate entfernt |
| `services/session_import_utils.py` | create_session_meta, update_time_range |
| `services/session_import.py` | Nutzt Shared Helpers |
| `services/session_import_multi.py` | Nutzt Shared Helpers |

---

## Naechste Session

### Aufgaben
- [ ] Scoring-Tuning: Score-Cap pro Kategorie oder Gewichtung anpassen (aktuell F bei 188 Warnings)
- [ ] Sprint 6: DeRep + Fixer (abhaengig von Sprint 5)
- [ ] Langfristziel: Warnings < 100

### Offene Punkte
- CSS-Duplikate (12x): Warten auf Design-Refactor
- Gleichnamige JS-Funktionen (loadProjects, loadData etc.): Kein echtes DRY-Problem, seitenspezifische Logik

### Referenz
- Sprint-Plan Quality: `sprints/sprint-5-scanner.md` (komplett)
- Quality Roadmap: `sprints/05-roadmap-quality-pipeline.md`
- Aktueller Report: `.quality/report.json`
