# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-15 (Session 18: Impl-Check Persisting + Task-Sprint-Plan)
> **Status:** Implementierungs-Check DB-Persisting live (4/5 Commits), Sprint-Plan fuer Plan→Section→Task→Marker-Refactor geschrieben.
> **Naechste Aufgabe:** Sprint `sprints/sprint-task-entity-und-drilldown.md` umsetzen (6 Commits, ca. 5 h, 2 Sessions)

---

## Was gilt jetzt

Freeze-Stand **`v1.3-final`** + Unified Cockpit Phase 1-7 + AI-Control-Plane
Stufe 1 + Dispatch Stufe 2a + Implementation-Check mit DB-Persisting. Cockpit ist
Projekt-zentriert mit kontextabhaengiger Fuehrung. Implementation-Check wird
jetzt gecached (markers.implementation_percent|_signals|_checked_at), Cache-Hit
spart ~27 % Request-Zeit bei 16 Markern. Invalidation via updated_at-Vergleich
+ explizite Hooks bei Signal-Feld-Aenderungen und commit_match_mode-Change.

## Naechste Aufgaben

### Primaer: Sprint `sprint-task-entity-und-drilldown.md` (6 Commits)

- **Commit 1:** DB-Schema `plan_tasks` + `markers.task_id` (Surrogate-ID, parse_key, FK ON DELETE SET NULL)
- **Commit 2:** `services/plan_task_service.py` — upsert_tasks_for_plan, list_*, get_markers_for_task, derive_task_status, rename_task
- **Commit 3:** Parser-Integration — `GET /api/plans/<id>` triggert upsert_tasks_for_plan
- **Commit 4:** API-Endpunkte — GET /api/plans/<id>/tasks, PATCH /api/tasks/<id>, POST /api/tasks/<id>/to-marker
- **Commit 5:** UI Drill-Down + Modus-Vereinheitlichung — Section → Task → Marker, einheitlicher Rahmen fuer alle Deep-Links
- **Commit 6:** Marker-Import fuellt `task_id` beim Sprint-Import

Aufwand ca. 5 h. Realistisch 2 Sessions (1-4 in Session 19, 5-6 in Session 20).

### Sekundaer (offen)

- [ ] Commit 5 aus `sprint-impl-check-persisting.md` (optional): UI-Timestamp „Zuletzt geprueft: vor X min" + manueller Recheck-Button
- [ ] Folge-Sprint `sprint-task-backfill.md`: Auto-Zuordnung Bestands-Marker → Task via Titel-Fuzzy-Match mit Review-UI
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung
- [ ] Policy-Suggestions: 4 pending unter `/policies` bewerten
- [ ] `dispatch.js` IIFE → Module-Pattern (aktuell 425 Z., Panel-Code eng gekoppelt)

### GUI/UX (Codex)

- [ ] Dead-Code-Hint im Workflow-Tab mit eigenem Icon und Kategorie-Breakdown (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`)
- [ ] `dead_code_summary` als kompakte Info-Karte im Workflow-Tab (`static/js/workflow-loop.js`)
- [ ] Owner separat editierbar, auch ohne Statuswechsel (`static/js/workflow-loop.js`, `routes/workflow_routes.py`)
- [ ] Microcopy Marker-Gruppen + CTA-Reihenfolge feinjustieren

## Was funktioniert (= Bestand)

| Bereich | Status |
|---|---|
| Basis-Features | DONE — Sessions, Plans, Quality, Governance, Backup |
| Workflow-System | DONE — Loop v1+v2, ADR-001 (Marker-DB, Core, Write-Guard) |
| AI-Control-Plane | DONE — ADR-002 Stufe 1 (Reviewer, Policies, Perplexity, CWO, Metriken) |
| Unified Cockpit Phase 1-7 | DONE — inkl. UI-Konsolidierung, Projekt-Detail bereinigt |
| Dispatch Sprint 2a (7-9) | DONE — Pull-Adapter, Gate, workflow_core, Settings, Doku |
| Guided Flow + Rating-v2 | DONE — Next-Action-Banner, Close-Pflicht-Rating, 48h-Fenster |
| **Implementierungs-Check** | **DONE — 7 Signale, DB-Persisting (Cache + Invalidation), Settings-Toggle** |
| **/rating-unskip API** | **DONE — Gegenstueck zu /rating-skip, schliesst API-Luecke** |

## Wie naechste Session starten

1. Dieses File zuerst lesen
2. `sprints/master-plan-summary.md` als Rahmen lesen
3. **Sprint `sprints/sprint-task-entity-und-drilldown.md` lesen** — enthaelt 6 Commits mit konkretem Scope
4. Bei Bedarf Referenz-Code: `services/plan_structure_service.py`, `services/plan_structure_helpers.py`, `routes/copilot_marker_routes.py:243` (to-markers-Endpoint)

Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich 12:30.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard`
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored)
- **sprints/:** gitignored — lokal, nicht auf GitHub

---

## Session 2026-04-15 (Session 18) — Impl-Check Persisting + Task-Sprint-Plan

### Was wurde erledigt

**Sprint `sprint-impl-check-persisting.md` — 4/5 Commits (Commit 5 optional):**
- **Commit 1 (Schema):** `markers.implementation_percent SMALLINT`, `_signals JSONB`, `_checked_at TIMESTAMPTZ` in `services/db_marker_schema.py`, idempotent via duplicate_column-Pattern
- **Commit 2 (Service):** `services/marker_implementation.py` erweitert um `get_or_calculate_progress()`, `load_cached_progress_map()`, `invalidate_implementation_progress()`. TTL 5 min + `updated_at > checked_at` triggert Neuberechnung. DB-Fehler werden geloggt, nicht gethrown (Graceful-Degradation)
- **Commit 3 (Integration):** `routes/cockpit_routes.py` + `services/workflow_loop_service.py` umgestellt auf Wrapper + Bulk-Load. Progress-Cache wird einmalig geladen und durchgereicht (kein N+1). Cockpit-Request ~27 % schneller bei warmem Cache (97 → 71 ms bei 16 Markern)
- **Commit 4 (Invalidation-Hooks):** `workflow_core_service.update_marker_field` setzt `implementation_checked_at = NULL` wenn Signal-Feld (prompt, checks, status, execution_score, last_session, rating_skipped) geaendert wird. `dashboard_settings_service.save_dashboard_settings` invalidiert alle Marker aller Projekte bei commit_match_mode-Change

**Bonus: API-Luecke geschlossen:**
- **`POST /api/marker/<id>/rating-unskip`** als Gegenstueck zu `/rating-skip`. Bisher gab es keinen Weg, rating_skipped zurueckzusetzen — der `fields`-PATCH-Endpoint erlaubte das Feld nicht. Entdeckt waehrend Smoke-Test, sofort gefixt. Marker 115 war durch Test versehentlich auf true gesetzt, jetzt zurueckgesetzt

**Neuer Sprint-Plan fuer naechste Session:**
- **`sprints/sprint-task-entity-und-drilldown.md`** — Einfuehrung von `plan_tasks` als DB-Entitaet mit Surrogate-ID, `markers.task_id` FK, Cockpit-UI-Vereinheitlichung (ein Layout fuer alle Deep-Links), Drill-Down Section → Task → Marker. 6 Commits, ca. 5 h.
- **Design-Entscheidungen dokumentiert:** Surrogate-ID + `parse_key`-Match (nicht Titel als Identitaet), Task-Status abgeleitet (open/in_progress/done), Bestands-Marker bleiben `task_id=NULL`, ON DELETE SET NULL, Fuzzy-Backfill als separater Sprint

### Git Commits (5)
```
5cb984d API: /rating-unskip Endpoint als Gegenstueck zu /rating-skip
8b8061b Invalidation-Hooks: Signal-Felder + Settings-Change
a65b76b Integration: cockpit_routes + workflow_loop_service nutzen Cache-Wrapper
ec42220 Service: get_or_calculate_progress + Invalidation + Bulk-Load
a86b02a Schema: markers.implementation_percent|_signals|_checked_at
```

### Erweiterte Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/db_marker_schema.py` | 3 neue Spalten in `markers` (idempotent) |
| `services/marker_implementation.py` | +198 Z. — Cache-Wrapper, Bulk-Load, Invalidation |
| `routes/cockpit_routes.py` | Bulk-Load + Wrapper-Aufruf |
| `services/workflow_loop_service.py` | progress_cache durchgereicht an 3 Serialisierungs-Funktionen |
| `services/workflow_core_service.py` | `SIGNAL_RELEVANT_FIELDS` + Auto-Invalidation bei signal-Touch |
| `services/dashboard_settings_service.py` | Bulk-Invalidation bei commit_match_mode-Change |
| `routes/copilot_marker_routes.py` | `api_marker_rating_unskip` (+19 Z.) |
| `sprints/sprint-task-entity-und-drilldown.md` | neu, lokal (gitignored) |

### Architekur-Notizen fuer naechste Session

- **Server-Parser fuer Plan-Sections existiert:** `services/plan_structure_service.py:derive_tagged_plan_sections()` + `services/markdown_routine_service.py:scan_markdown_structure()` erkennen `#sprint-*` und `#spec-*` Tags. `GET /api/plans/<id>` triggert Lazy-Parse.
- **Marker-Bulk-Import:** `POST /api/sprint/<plan_id>/to-markers` in `routes/copilot_marker_routes.py:243` — erzeugt deterministische `marker_id = slug(plan_id) + '-' + slug(title)`, schreibt in handoff.md und synct zur DB.
- **Tasks aktuell nur Text-Strings:** `services/plan_structure_helpers.py:build_task_items()` liefert `{title, sessions[], marker_id, status}` via Titel-Match (fragil). Ziel: stabile FK.
- **ADR-001-Regel weiterhin gueltig:** DB ist kanonische Quelle, handoff.md ist Mirror.

---

## Session 2026-04-15 (Session 19) — Sprint Task-Entity + Drill-Down umgesetzt

### Was wurde erledigt

**Sprint `sprint-task-entity-und-drilldown.md` — alle 6 Commits + Bugfix:**

- **Commit 1 (Schema):** `services/db_plan_task_schema.py` — Tabelle `plan_tasks` (SERIAL id, plan_id, section_key, spec_key, title, normalized_title, parse_key UNIQUE, order_index, body, last_parsed_at). `markers.task_id INTEGER REFERENCES plan_tasks(id) ON DELETE SET NULL` + Index. Idempotent via duplicate_column-Pattern. Lazy-Init via `db_service.ensure_plan_task_schema()`.
- **Commit 2 (Service):** `services/plan_task_service.py` (291 Z.) — `upsert_tasks_for_plan` (UPSERT via parse_key ON CONFLICT), `list_tasks_for_plan|section`, `get_task`, `get_markers_for_task`, `rename_task` (laesst parse_key stabil), `find_task_by_parse_key`, `derive_task_status` (open|in_progress|done). Verwaiste Tasks bleiben erhalten.
- **Commit 3 (Parser-Integration):** `routes/plans_routes.py` — `GET /api/plans/<id>` triggert nach `get_tagged_plan_structure` einen `upsert_tasks_for_plan(plan_id, tagged_sections)`-Call. Fehler werden geloggt, Plan-Detail funktioniert auch ohne Task-Persisting.
- **Commit 4 (API):** `routes/plan_task_routes.py` (neu) — `GET /api/plans/<id>/tasks`, `GET /api/plans/<id>/sections/<key>/tasks`, `GET /api/tasks/<id>`, `GET /api/tasks/<id>/markers`, `PATCH /api/tasks/<id>` (Inline-Rename), `POST /api/tasks/<id>/to-marker` (erzeugt Marker via `_write_marker`/`_sync_to_db` + setzt `markers.task_id`-Backlink). Alle mit `@api_route` (ausser to-marker).
- **Commit 5 (UI):** `static/js/copilot-board-panel.js` (+109 Z.) + `static/css/copilot-board.css` (+76 Z.) — Drill-Down im Source-Tab: `_renderSectionTasks` rendert DB-Tasks als klickbare Cards mit Status-Dot + Marker-Count. Klick laedt `/api/tasks/<id>/markers` in den "Zugeordnete Marker"-Bucket. Section-Marker mit `task_id=NULL` landen im Orphan-Bucket "Ohne Task". Fallback auf rohe Markdown-Strings, wenn DB noch leer. **Modus-Vereinheitlichung:** Bei `?project=&marker_id=` wird der Plan-Header analog zum Plan-Modus geladen, sobald der Marker `sprint_plan_id` traegt.
- **Commit 6 (Marker-Import-Backlink):** `services/copilot_marker_import_flow.py` — `sprinttomarkers*` nehmen optionalen `db_plan_id` (project_plans.id). Neue Helper-Funktion `_backfill_task_ids` setzt `markers.task_id` via `find_task_by_parse_key(plan_id, section_key, spec_key, titel)` mit Fallback auf spec_key="". `routes/copilot_marker_routes.py` reicht db_plan_id aus dem Body weiter.

**Bugfix + Cleanup (Commit 7):**
- `derive_tagged_plan_sections` liefert Tasks via `build_task_items` als dict ({title, sessions, marker_id, status}), nicht als Strings. `upsert_tasks_for_plan` stringifizierte das fehlerhaft (`"{'title': '...'}"` wurde als title gespeichert). `_task_title()`-Helper extrahiert den title-Key korrekt.
- `scripts/cleanup_dirty_plan_tasks.py` raeumt einmalig 50 kaputte plan_tasks-Zeilen auf (Filter `title LIKE "%'title':%"`). Idempotent.

### Verifikation

- `POST /api/plans/1853` -> 50 saubere Tasks in DB, parse_key korrekt
- `GET /api/tasks/65` -> dict mit body, normalized_title, parse_key, status='open'
- `GET /api/plans/1853/sections/sprint-workflow-actions/tasks` -> 9 Tasks
- Service `project-dashboard` aktiv, Schema idempotent

### Git Commits (7) — alle auf Gitea (origin), GitHub unangetastet
```
313f1b6 Fix: dict-Items aus build_task_items als String behandeln (+ Cleanup)
26aee19 Marker-Import: backfill markers.task_id via parse_key-Match
b099bf9 UI: Drill-Down Section -> Task -> Marker + Modus-Vereinheitlichung
82a254c API: plan_task_routes mit Tasks-CRUD und to-marker
ec95855 Parser-Integration: GET /api/plans/<id> triggert upsert_tasks_for_plan
70d48a4 Service: plan_task_service mit upsert/rename/derive_status
1e93f1d Schema: plan_tasks + markers.task_id (FK ON DELETE SET NULL)
```

### Erweiterte/neue Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/db_plan_task_schema.py` | NEU — plan_tasks-Schema + markers.task_id |
| `services/plan_task_service.py` | NEU — Service-Schicht (291 Z.) |
| `services/db_service.py` | `ensure_plan_task_schema()` registriert |
| `services/copilot_marker_import_flow.py` | `_backfill_task_ids` + db_plan_id-Param |
| `routes/plan_task_routes.py` | NEU — 6 API-Endpunkte |
| `routes/plans_routes.py` | upsert_tasks_for_plan-Trigger im GET |
| `routes/copilot_marker_routes.py` | db_plan_id durchgereicht |
| `routes/__init__.py` | plan_task_bp registriert |
| `static/js/copilot-board-panel.js` | Drill-Down + Modus-Vereinheitlichung |
| `static/css/copilot-board.css` | .panel-task-item + Marker-Status-Badges |
| `scripts/cleanup_dirty_plan_tasks.py` | NEU — Einmal-Cleanup |

### Gitea-Issue
- **Issue #24** geschlossen: https://git.webideas24.com/webideas24/project_dashboard/issues/24

### Naechste Session

Folge-Sprint-Kandidaten (Reihenfolge nach Wert):

1. **`sprints/sprint-task-backfill.md`** (zu erstellen) — Bestands-Marker `task_id=NULL` per Titel-Fuzzy-Match an Tasks zuordnen, mit Review-UI (Opt-In pro Marker). Aktuell sind alle Bestands-Marker im Orphan-Bucket sichtbar.
2. **Commit 5 aus `sprint-impl-check-persisting.md`** (optional): UI-Timestamp „Zuletzt geprueft: vor X min" + manueller Recheck-Button.
3. **Task-UX-Erweiterungen:** Inline-Rename via PATCH-Endpunkt im UI, Task-Status-Override (`blocked`, `wont_do`) via neue Spalte `manual_status_override`.
