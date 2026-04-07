# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-07 (Sprint 17 Reality-Check + Bugfix #19 verifiziert)
> **Status:** Sprint 17 als DONE bestaetigt + defensiver Marker-Parser-UX-Bugfix umgesetzt, getestet und auf prod verifiziert (Service neu gestartet, End-to-End-Test mit kaputter handoff.md erfolgreich).
> **Naechste Aufgabe:** Naechster Feature-Sprint waehlen (siehe Optionen unten)

---

## Session 2026-04-07 (zweiter Block) - Sprint 17 Reality-Check + Bugfix #19

### Sprint 17 Reality-Check

Pruefung der 5 Sprint-17-Arbeitspakete A-E gegen den Code (analog zu Sprint QT bei Sprint 9/10/11):

| Paket | Befund |
|---|---|
| A Marker-Dateiformat | DONE - `services/copilot_marker_format.py` (Parser, START/END, Validierung), YAML-Frontmatter `state_format: copilot_markers_v1` in `handoff.md` |
| B Service-Layer | DONE (uebererfuellt) - `services/copilot_marker_service.py` 11 Funktionen inkl. activate_marker, close_marker, execution_rating, backfill |
| C Routes/API | DONE (uebererfuellt) - `routes/copilot_marker_routes.py` 9 Endpoints in eigenem Blueprint |
| D UI-Integration | DONE - `copilot_board.html`+`copilot_board.js` rendern ausschliesslich Marker, Drag&Drop schreibt zurueck |
| E Chat-Kontext | DONE - `activate_marker` schreibt `marker-context.md`, `/api/copilot/chat` liest via `context_path` |

**Phasen 1-3** alle DONE. **Akzeptanzkriterien:** 6 von 7 erfuellt, 1 PARTIAL → in Bugfix #19 behoben.

**Befund-Fazit:** Sprint 17 ist faktisch DONE. Der Sprint-17-Plan vom 2026-04-03 war zum Zeitpunkt seiner Erstellung bereits ueberholt - der Service `copilot_marker_service.py` und die Routes existierten schon aus P2/P3/P-E3.

### Bugfix #19 - Defensive Marker-Parser-UX

Einziger PARTIAL-Punkt aus Sprint 17 Reality-Check (Risiko 1: defensive Parser-Fehler-UX) wurde umgesetzt:

**Backend:**
- `services/copilot_marker_format.py`: neue `parse_markers_with_errors(path) -> (markers, errors)`, `parse_markers` ist jetzt tolerant. Errors enthalten `marker_id`, `error`, `error_type` (`json_decode` / `validation` / `unexpected`), `handoff_path`.
- `services/copilot_marker_service.py`: neue `list_markers_for_plan_with_errors`.
- `routes/copilot_marker_routes.py`: `GET /api/copilot/markers` liefert zusaetzlich `parse_errors`-Feld.

**Frontend:**
- `static/js/copilot-marker-errors.js` (neu): `_renderMarkerParseErrors(errors)` zeichnet roten Banner ueber dem Board.
- `static/js/copilot_board.js`: `_loadSections` liest `parse_errors`, `.catch` zeigt echte Fehlermeldung.
- `static/css/copilot-marker-errors.css` (neu): Banner-Styling.

### Folge-Refactor (file-size-limits.md)

Pre-Commit-Hook lehnte zunaechst ab: `copilot.css` (1150), `copilot_board.js` (539), `copilot_board.html` (306) ueber Limit. Statt nur den Bugfix auszulagern, wurde die Altlast aufgeteilt:

| Datei | Vorher | Nachher |
|---|---|---|
| `copilot.css` | 1150 | 320 |
| `copilot_board.js` | 539 | 474 |
| `copilot_board.html` | 306 | 277 |

8 neue Dateien:
- 5 thematische CSS: `copilot-header.css` (138), `copilot-cards.css` (235), `copilot-panel.css` (249), `copilot-chat.css` (173), `copilot-marker-errors.css` (49)
- 2 JS: `copilot-marker-errors.js` (41), `copilot-section-modal.js` (36)
- 1 HTML-Include: `_copilot_add_section_modal.html` (30)

Alle Dateien jetzt unter Limit (CSS 400 / JS 500 / HTML 300).

### Verifikation

- **Smoke-Tests** (Python): 4/4 gruen (missing file, 1 valid + 1 broken JSON, validation error, parse_markers tolerant)
- **Service-Restart:** `sudo systemctl restart project-dashboard` → laeuft seit 14:15
- **End-to-End-Test:** handoff.md temporaer mit broken JSON-Block verfaelscht, `curl /api/copilot/markers?project_id=project_dashboard&plan_id=142` lieferte `markers: [142]` + `parse_errors: [{marker_id: broken-test, error_type: json_decode, error: "JSON kaputt: Expecting property name enclosed in double quotes (Zeile 1, Spalte 3)", handoff_path: "/mnt/projects/project_dashboard/handoff.md"}]`. handoff.md sauber wiederhergestellt.

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/copilot_marker_format.py` | parse_markers_with_errors + tolerantes parse_markers |
| `services/copilot_marker_service.py` | list_markers_for_plan_with_errors |
| `routes/copilot_marker_routes.py` | parse_errors-Feld in /api/copilot/markers |
| `static/js/copilot_board.js` | parse_errors-Handling, ausgelagerte Helpers |
| `static/js/copilot-marker-errors.js` | NEU - Banner-Renderer |
| `static/js/copilot-section-modal.js` | NEU - Add-Section-Modal-Logik |
| `static/css/copilot.css` | auf 320 Z reduziert |
| `static/css/copilot-{header,cards,panel,chat,marker-errors}.css` | NEU |
| `templates/copilot_board.html` | 5 neue link + 2 neue script + Modal-Include |
| `templates/_copilot_add_section_modal.html` | NEU - Modal-Include |
| `sprints/sprint-17-marker-driven-copilot-orchestration.md` | Status auf DONE + Reality-Check |
| `sprints/master-plan-2026-04-01.md` | Sprint 17 in Done eingetragen |

### Gitea-Issues
- #19 closed (refs `250c0d7`)

**Commit:** `250c0d7`

---

## Naechste Session - Optionen

### Option 1: Verschoben aus Sprint QT
- [ ] **Session↔Spec/Task Binding verbessern:** Sessions haengen aktuell nur ueber Marker-Title-Matching an Tasks. Eigener Mini-Sprint fuer explizite `spec_id`/`task_id`-FK in der `sessions`-Tabelle oder in einer Relation-Tabelle, inkl. Import-Anpassung. Jetzt nach Sprint 17 DONE besonders sinnvoll.

### Option 2: Naechster echter Feature-Sprint
Aus Master-Plan "Open / Next":
- Sprint A - Quality Scanner Spec & Scope Lock
- Sprint QS - DB-First State Consolidation (JSON-Stores → DB)
- Sprint 6 - DeRep Fixer (eigenstaendig)
- Sprint 8 - Automation Tuning
- Sprint 12 - Governance Feedback-Loop (Voll-Version, nur Light als Sprint C DONE)
- Sprint 13 - Bidirektionaler LLM-Control (Voll-Version, nur MVP als Sprint D DONE)
- Sprint 14 - Sprint-Flow-Tracking
- Sprint 15 - Turn-Level-Rating
- Sprint 16 - Workflow-Profiles
- Sprint 20 - Product Launch Bundle
- Audit-Weiterentwicklung: Quality-Score als `input_facts`, Governance-Gate-Integration, automatischer Trigger
