# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-07 (Sprint 17 Reality-Check + Bugfix #19)
> **Status:** Sprint 17 als DONE bestaetigt + defensiver Marker-Parser-UX-Bugfix umgesetzt (Issue #19, F1-F5 Tasks abgeschlossen). `parse_markers_with_errors` sammelt fehlerhafte Bloecke statt zu propagieren, API liefert `parse_errors`-Feld, Board zeigt Fehler-Banner mit marker_id + Fehlertyp + Pfad.
> **Naechste Aufgabe:** Service neu starten (`sudo systemctl restart project-dashboard`), Bugfix in der UI manuell verifizieren, dann naechster Feature-Sprint (siehe Optionen unten)

---

## Session 2026-04-07 - Sprint QT Plan-Reality-Sync

### Ziel
Master-Plan, Gitea-Issues und Repo-Stand in einen konsistenten Zustand bringen, bevor weitere Feature-Sprints gestartet werden.

### Was wurde erledigt

**Arbeitspaket A - Master-Plan Reality-Check:**
- Stichprobenhafte Pruefung von Sprint 9/10/11 Artefakten im Code
- Sprint 9 (Fehler-Kategorien + AI-Scope-Filter) als DONE bestaetigt:
  - `services/ai_scope_service.py` (86 Zeilen)
  - `routes/session_filter_routes.py` (187 Zeilen, 4 Endpoints)
  - `scripts/backfill_ai_flags.py`
  - AI-Flag-Extraktion in allen Importern unter `services/importers/`
- Sprint 10 (Per-File Heatmap) als DONE bestaetigt:
  - `services/file_touch_service.py` (386 Zeilen)
  - `routes/analytics_routes.py` (2 Endpoints)
  - `static/js/file-heatmap.js`, in `project_detail.html` integriert
- Sprint 11 (Modell-Qualitaetsvergleich) als DONE bestaetigt:
  - `services/model_recommendation.py` (437 Zeilen)
  - `routes/model_comparison_routes.py` (Page + 4 API-Endpoints)
  - `templates/model_comparison.html`
- Master-Plan-Block "AI Governance Analytics (historisch Sprints 9-14)" mit Status-Tabelle korrigiert
- Historische-Referenz-Tabelle angepasst (Sprint 9/10/11 -> DONE)
- Current-State-Block um neue Saeule erweitert

**Arbeitspaket B - Gitea-Issue-Triage:**
- Alle 5 offenen Issues #13, #14, #15, #16, #18 gepruefte und mit Commit-Referenz geschlossen:
  - #13 (Audit-Integration) - `routes/audit_routes.py` + `templates/audit.html` vorhanden
  - #14 (Sprint P3 Prompt-Chain) - Commit `afd218c` auf main
  - #15 (P2-Branch-Isolierung) - Commits `8f8d08c` + `6faf2c8` (PR #17)
  - #16 (Sprint P2 marker board) - Commit `8f8d08c`
  - #18 (Copilot CSS + handoff regeneration) - Commit `5bcb2af`

**Arbeitspaket C - Marker-Context:**
- **DONE:** `marker-context.md` bleibt unveraendert (User-Entscheidung: Testmarker `test-cockpit-2026-04-05` behalten)

**Arbeitspaket D - next-session.md Follow-ups:**
- D1/D2 (Session-Kontext-Links im Planning-Panel schaerfen): **verschoben** - aktuelle Bindung laeuft ueber `Marker.last_session` mit Title-Matching. Echte `spec_id`/`task_id`-FK erfordert Schema-Aenderung + Import-Anpassung, ist groesser als ein Follow-up-Task. Soll als eigener kleiner Sprint angelegt werden.
- D3/D4 (Cockpit-Activity-Card anpassen): **obsolet** - es existiert keine separate "Cockpit Activity Card" auf der Projektseite. Die Activity-Summary im Activity-Tab ist bereits das neue Format (Commit `1a1bd3e`). Kein Umbau noetig.
- D5/D6 (Archivierung): **DONE** - Session 2026-04-06 von `next-session.md` nach `next-session-archiv.md` verschoben.

**Arbeitspaket E - Dokumentation:**
- `sprints/audit-2026-04-07.md` erstellt (Prueffbericht)
- `sprints/sprint-qt-plan-reality-sync.md` erstellt (dieser Sprint-Plan mit 2-5-Min-Tasks)
- `sprints/master-plan-2026-04-01.md` aktualisiert (3 Stellen)
- `next-session.md` + `next-session-archiv.md` aktualisiert

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `sprints/audit-2026-04-07.md` | NEU - Prueffbericht mit 8 Sektionen |
| `sprints/sprint-qt-plan-reality-sync.md` | NEU - Sprint-Plan mit 5 Arbeitspaketen, 2-5-Min-Tasks |
| `sprints/master-plan-2026-04-01.md` | Current-State + Open-Blocks + Historische-Referenz korrigiert |
| `next-session.md` | Sprint QT dokumentiert, neue Aufgaben |
| `next-session-archiv.md` | Session 2026-04-06 einsortiert |

### Gitea-Issues
- #13 closed (refs commit 89+ routes/audit_routes.py)
- #14 closed (refs afd218c)
- #15 closed (refs 8f8d08c + 6faf2c8)
- #16 closed (refs 8f8d08c)
- #18 closed (refs 5bcb2af)

---

## Session 2026-04-07 (zweiter Block) - Sprint 17 Reality-Check

### Ziel
Pruefen ob Sprint 17 (Marker-Driven Copilot Orchestration) wirklich ein Sprint-Vorhaben ist oder ob der Plan bereits durch fruehere Arbeit (P2/P3/P-E3) ueberholt wurde. Analog zu Sprint QT bei Sprint 9/10/11.

### Was wurde erledigt

**R1-R7 Reality-Check** der 5 Sprint-17-Arbeitspakete A-E gegen den Code:

| Paket | Befund |
|---|---|
| A Marker-Dateiformat | DONE - `services/copilot_marker_format.py` (Parser, START/END, Validierung), YAML-Frontmatter `state_format: copilot_markers_v1` in `handoff.md` |
| B Service-Layer | DONE (uebererfuellt) - `services/copilot_marker_service.py` 11 Funktionen inkl. activate_marker, close_marker, execution_rating, backfill |
| C Routes/API | DONE (uebererfuellt) - `routes/copilot_marker_routes.py` 9 Endpoints in eigenem Blueprint |
| D UI-Integration | DONE - `copilot_board.html`+`copilot_board.js` rendern ausschliesslich Marker, Drag&Drop schreibt zurueck |
| E Chat-Kontext | DONE - `activate_marker` schreibt `marker-context.md`, `/api/copilot/chat` liest via `context_path` |

**Phasen 1-3** alle DONE. **Akzeptanzkriterien:** alle 7 erfuellt.

**Verifikation der 3 unklaren Akzeptanzpunkte:**
- **V1 Empty-State bei kaputtem Marker-Block: PARTIAL.** `parse_markers` faengt nur `FileNotFoundError`. JSONDecodeError oder ValueError aus `Marker.__post_init__` propagieren als 500. `copilot_board.js:111` zeigt nur generisches "Fehler beim Laden", verwirft den API-Fehlertext.
- **V2 Card-Oeffnung behaelt letzten aktiven Tab bei: DONE.** `copilot-board-panel.js:30` `switchPanelTab(tab || _activePanelTab || 'chat')`.
- **V3 Doku-Update: DONE** (siehe geaenderte Dateien).

**Befund-Fazit:** Sprint 17 ist faktisch DONE und wurde als solches eingetragen. Der Sprint-17-Plan vom 2026-04-03 war zum Zeitpunkt seiner Erstellung bereits ueberholt - der Service `copilot_marker_service.py` und die Routes existierten schon aus P2/P3/P-E3.

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `sprints/sprint-17-marker-driven-copilot-orchestration.md` | Status auf DONE, Reality-Check-Block mit Soll/Ist-Tabelle und offenem Folge-Punkt |
| `sprints/master-plan-2026-04-01.md` | Sprint 17 aus "Open / Next" entfernt, in AI-Governance-Analytics-Tabelle und "Completed Sprints (diese Session)" eingetragen, Current-State-Block ergaenzt |
| `next-session.md` | Sprint 17 Reality-Check dokumentiert |

---

## Bugfix Defensive Marker-Parser-UX (Issue #19) - DONE

**Backend-Aenderungen:**
- `services/copilot_marker_format.py`: neue `parse_markers_with_errors(path) -> (markers, errors)`, `parse_markers` ist jetzt tolerant (skipt fehlerhafte Bloecke). Errors enthalten `marker_id`, `error`, `error_type` (`json_decode` / `validation` / `unexpected`), `handoff_path`.
- `services/copilot_marker_service.py`: neue `list_markers_for_plan_with_errors(project_id, plan_id) -> (markers, errors)`.
- `routes/copilot_marker_routes.py`: `GET /api/copilot/markers` liefert jetzt zusaetzlich `parse_errors`-Feld.

**Frontend-Aenderungen:**
- `static/js/copilot_board.js`: `_loadSections` liest `parse_errors`, ruft `_renderMarkerParseErrors`. `.catch` zeigt jetzt die echte Fehlermeldung statt generisch "Fehler beim Laden".
- `static/js/copilot-marker-errors.js` (neu): `_renderMarkerParseErrors(errors)` zeichnet Hinweis-Banner ueber dem Board mit marker_id, Fehlertyp, Fehlertext und Datei-Pfad.
- `static/css/copilot-marker-errors.css` (neu): Styling `.marker-parse-errors-banner` (rot, links Border, Liste).

**CSS+JS-Aufteilung (Folge-Refactor wegen file-size-limits.md):**
Pre-Commit-Hook lehnte zunaechst ab: `copilot.css` (1150) und `copilot_board.js` (539) ueber Limit. Statt nur den Bugfix auszulagern, wurde die Altlast aufgeteilt:

- `copilot.css` 1150 → 320 Zeilen (nur noch Tokens, Progress, Split, Board Columns, Drag&Drop, Toast, Attachments, Responsive)
- Neue thematische CSS-Dateien:
  - `copilot-header.css` (138 Z) - Workspace-Header + Plan Switcher
  - `copilot-cards.css` (235 Z) - Card-Layout + Status Badges
  - `copilot-panel.css` (249 Z) - Side Panel + Tabs
  - `copilot-chat.css` (173 Z) - Chat Messages + Input
  - `copilot-marker-errors.css` (49 Z) - Marker-Parser-Banner (siehe oben)
- `copilot_board.js` 539 → 474 Zeilen (openAddSectionModal+createSection in `copilot-section-modal.js` 36 Z, Marker-Errors-Renderer in `copilot-marker-errors.js` 41 Z)
- `templates/copilot_board.html`: 5 neue `<link>` und 2 neue `<script>` in fester Reihenfolge

Alle Dateien jetzt unter Limit (CSS 400 / JS 500).

**Smoke-Tests (alle gruen):**
1. Datei nicht da -> `([], [])`
2. 1 kaputter JSON + 1 gueltiger Marker -> `([good], [json_decode error])`
3. Gueltiger JSON aber leeres `titel`-Feld -> `([], [validation error "titel ist erforderlich"])`
4. Alte API `parse_markers()` wirft nicht mehr, liefert nur die gueltigen Marker.

**Noch offen:** Service-Restart + manueller UI-Smoke-Test mit kaputter handoff.md.

---

## Naechste Session - Optionen

### Option 1: Verschoben aus Sprint QT
- [ ] **Session↔Spec/Task Binding verbessern:** Sessions haengen aktuell nur ueber Marker-Title-Matching an Tasks. Eigener Mini-Sprint fuer explizite `spec_id`/`task_id`-FK in der `sessions`-Tabelle oder in einer Relation-Tabelle, inkl. Import-Anpassung. Jetzt nach Sprint 17 DONE besonders sinnvoll, weil Marker dann die primaere Einheit sind.

### Option 2: Naechster echter Feature-Sprint
Aus Master-Plan "Open / Next":
- Sprint A - Quality Scanner Spec & Scope Lock
- Sprint QS - DB-First State Consolidation
- Sprint 6 - DeRep Fixer
- Sprint 8 - Automation Tuning
- Sprint 12 - Governance Feedback-Loop (Voll-Version)
- Sprint 13 - Bidirektionaler LLM-Control (Voll-Version)
- Sprint 14 - Sprint-Flow-Tracking
- Sprint 15 - Turn-Level-Rating
- Sprint 16 - Workflow-Profiles
- Sprint 20 - Product Launch Bundle

### Weitere offene Sprints (aus Master-Plan, nach Sprint 17)
- Sprint QS - DB-First State Consolidation (JSON-Stores -> DB)
- Sprint 6 - DeRep Fixer (eigenstaendig)
- Sprint 8 - Automation Tuning
- Sprint 12 - Governance Feedback-Loop (Voll-Version, nur Light als Sprint C DONE)
- Sprint 13 - Bidirektionaler LLM-Control (Voll-Version, nur MVP als Sprint D DONE)
- Sprint 14 - Sprint-Flow-Tracking
- Sprint 15 - Turn-Level-Rating
- Sprint 16 - Workflow-Profiles
- Sprint 20 - Product Launch Bundle
- Audit-Weiterentwicklung: Quality-Score als `input_facts`, Governance-Gate-Integration, automatischer Trigger
