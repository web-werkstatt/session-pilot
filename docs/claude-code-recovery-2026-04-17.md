# Claude Code Recovery Brief (2026-04-17)

## Ziel

Diese Datei ist ein konkreter Wiederherstellungsauftrag fuer Claude Code.
Hintergrund: Ein spaeter Git-Befehl hat bereits umgesetzte Arbeit ganz oder
teilweise rueckgaengig gemacht. Claude soll die verlorenen Aenderungen
wiederherstellen, ohne weitere Daten zu zerstoeren.

## Wichtige Sicherheitsregeln

1. Vor jeder Wiederherstellung zuerst `git status` und `git branch --show-current`
   pruefen.
2. Vor destruktiven Git-Befehlen den aktuellen Stand sichern:
   `git diff > /tmp/project-dashboard-before-recovery.patch`
3. Keine Befehle wie `git reset --hard`, `git checkout -- .`, `git clean -fd`
   oder aehnliche Ruecksetz-Kommandos ausfuehren, solange nicht explizit
   bestaetigt wurde, dass keine ungesicherten Aenderungen mehr existieren.
4. Schnellster Restore-Pfad ist immer:
   vorhandene Commits finden -> gezielt cherry-picken oder Inhalte daraus
   wiederherstellen.
5. Erst wenn die Commits wirklich nicht mehr verfuegbar sind, aus den Sprint-
   Dokumenten und `next-session.md` neu implementieren.

## Beobachteter Stand in diesem Repo

- Branch: `main`
- `next-session.md` enthaelt eine sehr detaillierte Handoff-Historie fuer die
  Sessions 18, 19, 20, 21 und 22.
- Ein grosser Teil der angeblich "zerstoerten" Arbeit ist weiterhin ueber
  Commit-Hashes, Sprint-Dokumente und Dateilisten rekonstruierbar.
- `git log --oneline` zeigt insbesondere die komplette Kette fuer:
  - Task-Entity + Drill-Down
  - Task-Backfill
  - Plan-Discovery / Multi-Source-Scanner
  - Recovery-Follow-up
  - UI-Fixes auf `/plans`

## Restore-Reihenfolge

Claude soll in genau dieser Reihenfolge vorgehen.

### Block 1 - Task-Entity / Drill-Down wiederherstellen

Quelle:
- `next-session.md`, Abschnitt `Session 2026-04-15 (Session 19)`
- `sprints/sprint-task-entity-und-drilldown.md`

Commit-Kette:
1. `1e93f1d` Schema: `plan_tasks` + `markers.task_id`
2. `70d48a4` Service: `plan_task_service`
3. `ec95855` Parser-Integration in `GET /api/plans/<id>`
4. `82a254c` API: `routes/plan_task_routes.py`
5. `b099bf9` UI: Section -> Task -> Marker + Modus-Vereinheitlichung
6. `26aee19` Marker-Import: `task_id` via parse_key-Match
7. `313f1b6` Fix: dict-Items korrekt behandeln + Cleanup

Betroffene Dateien:
- `services/db_plan_task_schema.py`
- `services/plan_task_service.py`
- `services/db_service.py`
- `services/copilot_marker_import_flow.py`
- `routes/plan_task_routes.py`
- `routes/plans_routes.py`
- `routes/copilot_marker_routes.py`
- `routes/__init__.py`
- `static/js/copilot-board-panel.js`
- `static/css/copilot-board.css`
- `scripts/cleanup_dirty_plan_tasks.py`

### Block 2 - Task-Backfill wiederherstellen

Quelle:
- `next-session.md`, Abschnitt `Session 2026-04-15 (Session 20)`
- `sprints/sprint-task-backfill.md`

Commit-Kette:
1. `2d30fae` Schema: `plan_task_match_suggestions`
2. `9d6da5a` Service: `plan_task_match_service`
3. `4d18b32` API: `plan_task_match_routes`
4. `0bc111e` UI: Backfill-Modal

Betroffene Dateien:
- `services/db_plan_task_match_schema.py`
- `services/plan_task_match_service.py`
- `services/db_service.py`
- `routes/plan_task_match_routes.py`
- `routes/__init__.py`
- `templates/copilot_board.html`
- `templates/_task_backfill_modal.html`
- `static/js/task-backfill-panel.js`
- `static/js/copilot_board.js`
- `static/css/task-backfill.css`

### Block 3 - Plan-Discovery / Multi-Source-Import wiederherstellen

Quelle:
- `next-session.md`, Sessions 21 und 22
- `sprints/sprint-plan-discovery.md`
- `sprints/sprint-plan-discovery-followup.md`
- `sprints/recovery-plan-discovery-followup-2026-04-16.md`

Commit-Kette:
1. `ec339c5` Scanner: `plan_discovery_service` mit Multi-Source-Discovery
2. `a212ec2` API: `plan_scan_routes`
3. `5f5fbce` UI: `/plans/scan`
4. `750ea1b` Tool: `scripts/plan_tag_migrator.py`
5. `c65abfb` Heuristik: 100% Plan-Coverage
6. `4476791` Rueckbau + Cleanup auf Sprint/Spec-Fokus
7. `803c2d9` Auto-Tagging in `sync_all_plans()`
8. `c2d8f32` Recovery Block D: Specs als Karten unter Sprint-Sections
9. `c9de4ca` Recovery Block B: Source-Metadaten + Badges auf `/plans`
10. `f1e289d` Recovery Block A+C: Circuit-Guard + Notification-Suppression
11. `fcfca66` Recovery Commit 4: `UNIQUE(filename, project_name)`
12. `fbad6d1` UI: IDEA-Badge raus, Sprintplan-Label rein
13. `0bcd2b5` UI: Source-Badge nicht doppelt rendern
14. `c33f13b` UI: einheitliche Sprintplan-Optik
15. `8e25411` UI: zweiter Category-Badge
16. `607b2df` UI: `/plans` filtert auf lokale Plaene/Sprintplaene
17. `c8374d4` Plans: Status aus Markdown-Header + Card-Date aus `file_mtime`
18. `380495b` Doku/Handoff fuer Session 22

Besonders wichtige Dateien in diesem Block:
- `services/plan_discovery_service.py`
- `routes/plan_scan_routes.py`
- `services/plan_scan_exclusion_service.py`
- `templates/plan_scan.html`
- `static/js/plan_scan_panel.js`
- `static/css/plan_scan.css`
- `services/plans_sync_service.py`
- `services/plans_import.py`
- `services/markdown_routine_service.py`
- `services/notification_service.py`
- `services/db_plan_source_schema.py`
- `services/db_service.py`
- `routes/plans_routes.py`
- `static/js/plans.js`
- `static/css/plans.css`
- `static/css/plans-board.css`
- `static/js/copilot_board.js`
- `static/css/copilot-board.css`
- `scripts/plan_tag_migrator.py`
- `scripts/restore_auto_tag_mtimes.py`

## Praktischer Restore-Plan fuer Claude Code

1. `git log --oneline --all` auf die oben genannten Hashes pruefen.
2. Falls die Commits noch existieren:
   - nicht blind alles cherry-picken
   - zuerst aktuellen Arbeitsbaum gegen die betroffenen Dateien pruefen
   - dann die fehlenden Aenderungen blockweise uebernehmen
   - bei Konflikten immer den in `next-session.md` beschriebenen Zielzustand
     bevorzugen
3. Falls einzelne Commits fehlen:
   - Zielzustand aus den genannten Sprint-Dateien und `next-session.md`
     rekonstruieren
   - betroffene Dateien neu anlegen oder gezielt patchen
4. Nach jedem Block verifizieren, bevor der naechste Block kommt.

## Verifikation nach Restore

### Minimal

- `python3 -m py_compile services/*.py routes/*.py`
- `node --check static/js/plans.js`
- `node --check static/js/plan_scan_panel.js`
- `node --check static/js/copilot_board.js`
- `node --check static/js/task-backfill-panel.js`

### Funktional

- `/plans` oeffnen:
  - nur lokale Plaene/Sprintplaene sichtbar
  - Source-/Category-Badges korrekt
  - Status aus Markdown-Header plausibel
- `/plans/scan` oeffnen:
  - Baumansicht, Exclusions, Sync-Button vorhanden
- Plan-Detail / Copilot-Board pruefen:
  - Section -> Task -> Marker Drill-Down vorhanden
  - Orphan-Bucket vorhanden
  - Task-Backfill-Modal vorhanden
  - Specs als Karten unter Sprint-Sections sichtbar

### Datenmodell

- `plan_tasks` existiert
- `markers.task_id` existiert
- `plan_task_match_suggestions` existiert
- Plan-Source-Constraint ist `UNIQUE(filename, project_name)`, nicht mehr nur
  `UNIQUE(filename)`

## Kanonische Quellen

Wenn Claude Code unsicher ist, gelten diese Dateien als Wahrheit:

1. `next-session.md`
2. `sprints/sprint-task-entity-und-drilldown.md`
3. `sprints/sprint-task-backfill.md`
4. `sprints/sprint-plan-discovery.md`
5. `sprints/sprint-plan-discovery-followup.md`
6. `sprints/recovery-plan-discovery-followup-2026-04-16.md`

## Arbeitsauftrag an Claude Code

Stelle die oben genannten drei Bloecke wieder her. Nutze zuerst die vorhandenen
Commit-Hashes als Restore-Quelle. Wenn Commits fehlen oder nur teilweise
anwendbar sind, implementiere den Zielzustand aus `next-session.md` und den
Sprint-Dokumenten neu. Arbeite blockweise, verifiziere nach jedem Block und
fuehre keine destruktiven Git-Befehle aus, solange ungesicherte Aenderungen im
Arbeitsbaum liegen.
