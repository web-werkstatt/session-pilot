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

---

## Session 2026-04-15 (Session 20) — Sprint Task-Backfill umgesetzt

### Was wurde erledigt

**Sprint `sprint-task-backfill.md` — Commits 1-4 DONE, Commit 5 via Sprint-Nachtrag:**

- **Commit 1 (Schema):** `services/db_plan_task_match_schema.py` — Tabelle `plan_task_match_suggestions` (SERIAL id, marker_id + task_id FK ON DELETE CASCADE, score NUMERIC(4,3), method VARCHAR(30), status VARCHAR(20) 'pending', decided_at/by, UNIQUE(marker_id, task_id)). 3 Indizes (marker, task, status). Idempotent via `ensure_plan_task_match_schema()`.
- **Commit 2 (Service):** `services/plan_task_match_service.py` (295 Z.) — Mehrstufiger Match: `normalized_exact` (1.0), `jaccard_tokens` (Set-Intersection mit Stopword-Filter), `seq_ratio` (difflib-Fallback). Konstanten `PERSIST_MIN_SCORE=0.5`, `AUTO_APPLY_MIN_SCORE=0.9`. Scope: `markers.sprint_plan_id = plan_id AND task_id IS NULL`. Best-per-Marker-Filter gegen Review-Noise.
- **Commit 3 (API):** `routes/plan_task_match_routes.py` — 5 Endpunkte, alle mit `@api_route`:
  - `POST /api/plans/<id>/task-matches/recompute`
  - `GET  /api/plans/<id>/task-matches?status=pending|approved|rejected`
  - `POST /api/task-matches/<id>/approve` (setzt `markers.task_id`, auto-rejected andere pending desselben Markers)
  - `POST /api/task-matches/<id>/reject`
  - `POST /api/plans/<id>/task-matches/auto-apply` (Body: `min_score`, Default 0.9)
- **Commit 4 (UI):** Cockpit-Toolbar-Button "Backfill" (nur im Plan-Modus sichtbar, analog `importSprintMarkersBtn`) oeffnet Modal. Modal zeigt Suggestions sortiert nach Score:
  - Marker-Titel -> Task-Titel (plus section/spec-Kontext)
  - Score-Value + Farbverlauf-Bar (orange -> gruen) + Method-Label
  - Approve/Reject pro Item, "Alle >= 0.9 anwenden" global
  - Eigene Dateien (`task-backfill-panel.js`, `task-backfill.css`, `_task_backfill_modal.html`) — `copilot-board-panel.js` ist bei 500 Z.-Limit.

### Abweichungen vom Plan

- **Match-Methode erweitert:** Plan nannte nur `normalized_jaccard`. Implementierung nutzt zusaetzlich `seq_ratio` als Fallback fuer sehr kurze Titel, wo Jaccard-Tokens zu schwach sind.
- **Best-per-Marker statt alle Paare:** Nur der beste Task-Kandidat pro Orphan-Marker wird persistiert. Haelt die Review-Liste fokussiert.
- **approve() auto-rejected Konkurrenten:** Bei mehreren pending Suggestions pro Marker wird nach Approve der Rest verworfen — Ein Marker = ein Task.

### Git Commits (4) — alle auf Gitea, GitHub unangetastet

```
0bc111e UI: Task-Backfill-Modal im Cockpit mit Approve/Reject/Auto-Apply
4d18b32 API: plan_task_match_routes (recompute/list/approve/reject/auto-apply)
9d6da5a Service: plan_task_match_service mit compute/approve/reject/auto_apply
2d30fae Schema: plan_task_match_suggestions (Fuzzy-Match Backfill)
```

### Neue/erweiterte Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/db_plan_task_match_schema.py` | NEU — Schema + 3 Indizes |
| `services/db_service.py` | `ensure_plan_task_match_schema()` registriert |
| `services/plan_task_match_service.py` | NEU — Match-Algorithmus, CRUD, auto_apply |
| `routes/plan_task_match_routes.py` | NEU — 5 API-Endpunkte |
| `routes/__init__.py` | plan_task_match_bp registriert |
| `templates/copilot_board.html` | Button + Modal-Include + JS/CSS-Link |
| `templates/_task_backfill_modal.html` | NEU — Modal-Partial |
| `static/js/task-backfill-panel.js` | NEU — Modul mit openModal/api.js |
| `static/js/copilot_board.js` | taskBackfillBtn-Sichtbarkeit an Plan-Modus gekoppelt |
| `static/css/task-backfill.css` | NEU — 161 Z. Styles |

### Verifikation

- Service aktiv, Schema idempotent — kein Fehler beim Restart
- `POST /api/plans/1853/task-matches/recompute` -> `{"created":0, "orphans":0, "tasks":50}`. Plan 1853 hat nach Sprint-19-Backfill keine Orphans mehr — erwartetes Verhalten.
- UI-Modal oeffnet korrekt, Empty-State bei leerer Pending-Liste.

### Gitea-Issue
- **Issue #25:** https://git.webideas24.com/webideas24/project_dashboard/issues/25 (offen, soll mit Commit-Batch geschlossen werden)

### Offen / Naechste Schritte

- **Live-Test mit echten Orphans:** Aktuell 0 Orphans in allen Plaenen (`markers.sprint_plan_id IS NOT NULL AND task_id IS NULL`). Algorithmus noch nicht unter Realbedingungen geprueft — erst wenn neue Marker importiert werden oder alte Marker ohne task_id auftauchen, greift der Backfill.
- **Commit 5 aus `sprint-impl-check-persisting.md`** (optional): UI-Timestamp „Zuletzt geprueft: vor X min" + manueller Recheck-Button.
- **Task-UX-Erweiterungen:** Inline-Rename, manual_status_override, Task-spezifische Close-Rule-Overrides.

---

## Session 2026-04-15 (Session 21 — Planning Only) — Sprint Plan-Discovery vorbereitet

### Ausgangspunkt

Beim Live-Test-Versuch des Task-Backfills (Sprint 20) entdeckt: Plan-Scanner liest nur `~/.claude/plans/`. Eigene Sprint-/Spec-/ADR-Dateien unter `/mnt/projects/project_dashboard/sprints/` sind fuer das Dashboard unsichtbar. Damit fehlt die Basis fuer realistische Orphan-Tests — Scanner-Luecke blockiert alle nachgelagerten Sprints.

### Was entstanden ist

**Sprint-Plan `sprints/sprint-plan-discovery.md`** (gitignored, lokal) — Basis + 5 Nachtraege, append-only.

Kern-Design:
- **Scan-Quellen (fest):** `~/.claude/plans/`, `<project>/sprints/`, `<project>/plans/`, `<project>/docs/{plans,sprints}/`, Projekt-Root-Roadmaps
- **Heuristik:** Filename-Regex + Plan-Tag + `## `-Headline; Negativ-Liste (`-retro`, `CHANGELOG` etc.)
- **Schema-Delta:** `source_path`, `source_kind`, `content_hash` + Tabelle `plan_scan_exclusions`
- **Duplikat-Erkennung:** 6 Quellen adressiert (source_path-UNIQUE, Symlinks via realpath, Scan-seen-Set, Content-Hash-Migration, Modul-Lock, Quarantaene `source_kind='unclassified'`)
- **Preview-UI:** Route `/plans/scan` mit Baum-Ansicht + Checkbox-Exclusions + Badge-System
- **Observability:** Strukturiertes Metrik-Log (`plan_scan metrics ...`), Circuit-Breaker (`plan_scan_circuit_open`), Lock-Log (`plan_scan_lock_skipped`)
- **Test-Strategie:** Option A verbindlich — nur Stubs in `tests/test_plan_discovery.py`, voller pytest-Setup in Folge-Sprint `sprint-test-infrastructure.md`

**5 Commits geplant (5.5-6.5 h, 2 Sessions):**
1. Schema: Spalten + Tabelle + Indizes
2. Scanner: `plan_discovery_service.py` (~200 Z., realpath, seen-Set, MD5, Heuristik, Exclusion-Filter)
3. Import: `plans_import.py` erweitert (4-stufige Upsert-Reihenfolge, Cooldown, Bulk-Tx, Notification-Suppression)
4. API: `plan_scan_routes.py` (scan-preview, sync-now, scan-exclusions CRUD)
5. UI: `/plans/scan` (Baum, Badges, Exclusion-Tab)

### Gitea-Issue

- **Issue #26** angelegt: https://git.webideas24.com/webideas24/project_dashboard/issues/26
- Referenz in jedem der 5 Commits (`refs #26`), Schluss mit Commit 5 (`closes #26`)

### Code-Status

**Keine Implementierung.** Nur Planungs-Session. Keine Commits auf Gitea/GitHub. `sprints/sprint-plan-discovery.md` ist gitignored (nicht in Repo).

### Naechste Session — Start-Reihenfolge

1. `next-session.md` lesen (diese Datei)
2. `sprints/sprint-plan-discovery.md` vollstaendig lesen — Basis + 5 Nachtraege, Reihenfolge:
   - Basis → Nachtrag (5) Navigation → Nachtraege (1-4) in Reihenfolge
3. Commit 1 (Schema) starten:
   - Datei `services/db_plan_schema.py` neu anlegen ODER Erweiterung in `services/plans_import.py:ensure_plans_schema`
   - Spalten: `source_path TEXT`, `source_kind VARCHAR(32)`, `content_hash VARCHAR(32)`
   - Tabelle: `plan_scan_exclusions` (siehe Nachtrag 3)
   - Indizes: `UNIQUE(source_path) WHERE NOT NULL`, `ix_project_plans_content_hash`, `ix_plan_scan_exclusions_project`
   - `db_service.ensure_plan_source_schema()` + `ensure_plan_scan_exclusions_schema()` registrieren
   - Akzeptanz: Service-Neustart ohne Fehler
4. Commit-Message: `Schema: source_path, source_kind, content_hash + plan_scan_exclusions (refs #26)`

### Verbindliche Festlegungen aus Planung

- **Test-Strategie:** Option A (Stubs only)
- **UI-Kopplung:** Preview + Exclusions BLEIBEN im selben Sprint (Nachtrag 3 + Nachtrag 5)
- **Rollback-SQL-Form:** `UPDATE project_plans SET source_path = NULL, source_kind = NULL WHERE source_kind != 'claude_plans'` via `db_service.execute()` (siehe Nachtrag 5, Klarstellung 2)
- **Sprint-Datei ist append-only** — keine Korrekturen im bestehenden Text, nur weitere Nachtraege
- **Issue-Referenzierung:** `refs #26` in Commits 1-4, `closes #26` in Commit 5
