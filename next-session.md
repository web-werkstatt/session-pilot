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
