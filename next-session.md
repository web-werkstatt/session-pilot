# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-06
> **Status:** Sprint QR gegen echte Projektdaten im Browser validiert; Session-Tab zu kompakter Activity-Summary reduziert mit Stats-Kacheln, Account-Breakdown und Link zur globalen Activity-Seite; Planning-Detailpanel zeigt jetzt Account-Badges, Modell, Tokens und "View all" Link bei Sessions
> **Naechste Aufgabe:** Entscheiden ob Phase 1 von Sprint QS (DB-first Abloesung JSON-Zustandsdaten) oder weitere UI-Verbesserungen am Planning-Workspace als naechstes folgen

---

## Session 2026-04-06 - QR-Validierung + Session-Tab Reduktion

### Was wurde erledigt
- Sprint QR vollstaendig im Browser gegen echte Daten validiert:
  - Planning-Tab: Hierarchie Plan -> Sprint -> Spec -> Task rendert korrekt (8 Plans, 3 Sprints, 15 Specs)
  - Detailpanel reagiert auf Klick (Sprint, Spec, Task) und zeigt Status/Goal/Next Step/Sessions
  - Session-Zeilen im Planning-Panel navigieren korrekt zur Session-Detailseite
  - Zurueck-Button auf Session-Detail fuehrt zurueck zur Projektseite
  - Widgets-Tab laedt ohne Console-Fehler (`loadWidgets` Fix bestaetigt)
  - Account-Badges (claude/codex/kilo) farblich korrekt unterscheidbar
- Session-Tab zu Activity-Summary reduziert:
  - Stats-Kacheln: Sessions, Total Time, Tokens, Tools
  - Account-Breakdown-Badges mit Anzahl
  - Kompakte Recent-Sessions-Liste (max 10) statt Volltabelle
  - "View all sessions" Link zur globalen Activity-Seite
- Planning-Detailpanel Sessions erweitert:
  - Account-Badges mit tool-spezifischen Farben (claude=blau, codex=orange, kilo=lila, gemini=gruen, opencode=rot)
  - Token-Anzeige (input/output formatiert)
  - Modellnamen-Kurzform (Opus, Sonnet statt claude-opus-4-6)
  - "View all in Activity" Link
- Backend: SQL-Queries fuer Sessions um account, total_input_tokens, total_output_tokens erweitert; Limit von 6 auf 10 erhoeht

### Git Commits
```
1a1bd3e Feature: reduce Session tab to compact Activity summary, enrich Planning sessions
```

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/plan_structure_helpers.py` | SQL um account + tokens erweitert, Serializer ergaenzt |
| `services/plan_structure_service.py` | Recent-Sessions-Limit 6 -> 10 |
| `static/js/project-planning.js` | Session-Rendering mit Account-Badges, Tokens, Activity-Link |
| `static/css/project-planning.css` | Account-Badge-Farben, Activity-Link CSS |
| `static/js/project-detail.js` | Session-Tab -> kompakte Activity-Summary |
| `static/css/activity-summary.css` | Neues CSS fuer Activity-Summary (aus project-detail.css extrahiert) |
| `templates/project_detail.html` | Tab-Label "Session History" -> "Activity", CSS-Link |

---

## Naechste Session

### Aufgaben
- [ ] Entscheiden: Sprint QS Phase 1 (JSON -> DB) oder weitere Planning-UX
- [ ] Optional: Session-Kontext-Links im Planning-Panel schaerfen (Sessions direkt an Specs/Tasks binden statt nur Fallback)
- [ ] Optional: Cockpit-Card "Activity" auf der Projektseite an die neue Summary-Darstellung anpassen
- [ ] next-session-archiv.md pruefen ob sauber archiviert
