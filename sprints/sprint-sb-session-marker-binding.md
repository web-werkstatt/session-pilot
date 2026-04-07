# Sprint SB - Session-Marker-Binding hart

Stand: 2026-04-07
Status: DONE 2026-04-07

## Ziel

Sessions sollen ihre Marker-Zugehoerigkeit explizit als persistierte
Spalte in der `sessions`-Tabelle tragen, anstatt nur ueber das einseitige
Feld `marker.last_session` in `handoff.md` aufgeloest zu werden.

## Motivation

Aktueller Stand (Code-Audit 2026-04-07):

1. Sessions kennen ihren Marker nicht. Reverse-Lookup laeuft ausschliesslich
   ueber `routes/session_routes.py:278` -> `get_marker_by_last_session()` in
   `services/copilot_marker_service.py:148`.
2. `marker.last_session` in `handoff.md` ist ein einzelner String. Damit
   findet die Session-Detail-Seite nur die *letzte* Session pro Marker.
   Alle vorherigen Sessions am selben Marker bekommen `marker = null`.
3. Es gibt keine Liste "alle Sessions zu Marker X" im UI/API, weil die
   1:1-Modellierung das nicht hergibt.
4. Der Reverse-Lookup ist O(n_marker) je Aufruf und liest die `handoff.md`
   jedes Mal neu (ueber `_load_markers_with_regeneration`).

Sprint 17 hat Marker zur zentralen Arbeitseinheit gemacht, Sprint 14
(Sprint-Flow-Tracking) und Sprint 15 (Turn-Level-Rating) wuerden auf
einer 1:1-Verknuepfung ohne Verlauf brechen. Bevor diese Sprints
starten, muss das Binding belastbar sein.

## Scope

**In scope:**
- DB-Schema-Migration: `sessions.marker_id`, `sessions.marker_handoff_path`, Index
- Backfill-Script ueber alle vorhandenen `handoff.md`-Dateien (alle Projekte)
- Post-Sync-Hook in `sync_all()`: nach jedem Account-Sync werden Projekte
  mit aktivem `marker-context.md` gestempelt - eine Stelle, alle 5 Importer
  profitieren ohne Modifikation.
- `routes/session_routes.py` Read-Path umstellen: erst `sessions.marker_id`
  aus DB, dann gezielt diesen einen Marker laden.
- Neue Route `GET /api/markers/<marker_id>/sessions` fuer den Verlauf
  aller Sessions zu einem Marker.
- Smoke-Tests, Backfill auf Live-DB, Service-Restart, Doku-Update.

**Out of scope:**
- Schema- oder API-Aenderungen an `marker.last_session` selbst (bleibt
  als denormalisierter Schnellzugriff im Markdown).
- Importer-Module unter `services/importers/*` werden NICHT angefasst -
  der Post-Sync-Hook deckt alle Tools ab.
- UI-Aenderungen an Session-Detail oder Marker-Cards (Folge-Sprint).
- Spec/Task-FK auf Session-Ebene jenseits von Marker (kein eigener
  spec_id-Bezug, weil Marker-Datensatz `spec_tag` schon traegt).

## Abhaengigkeiten

Keine. Reine Backend- und Schema-Aenderung. Marker-Workflow-Logik
bleibt unveraendert.

## Risiken

1. **Post-Sync-Hook stempelt zu viele Sessions:** Wenn `marker-context.md`
   alt ist und seit Tagen nicht aktualisiert wurde, wuerden auch frische
   Sessions auf einen "alten" Marker zeigen. Mitigation: Hook nur Sessions
   mit `started_at >= mtime(marker-context.md)` UND `started_at <= now()`
   stempeln, und nur dann, wenn marker_id noch NULL ist.
2. **Backfill ueberschreibt manuelle Bindings:** Mitigation: Backfill setzt
   nur, wenn `sessions.marker_id IS NULL`. Bestehende Werte werden nie
   ueberschrieben.
3. **handoff.md mit Parser-Fehler:** Bugfix #19 hat den Parser tolerant
   gemacht; das Backfill nutzt `parse_markers()` (jetzt tolerant) und
   ueberspringt fehlerhafte Bloecke automatisch.

## Akzeptanzkriterien

- [x] AC1: `sessions.marker_id` und `sessions.marker_handoff_path` existieren
      in der DB, idempotente Migration in `db_service.py`.
- [x] AC2: Backfill-Script setzt fuer jedes `marker.last_session != ''`
      genau eine `sessions.marker_id`-Zelle. Idempotent (zweiter Lauf =
      0 neue Updates).
- [x] AC3: Post-Sync-Hook stempelt eine neue Session, die nach Aktivierung
      eines Markers laeuft, automatisch mit der `marker_id`.
- [x] AC4: `routes/session_routes.py:278` liest `sessions.marker_id` zuerst,
      faellt nur bei NULL auf den Reverse-Lookup zurueck.
- [x] AC5: `GET /api/markers/<marker_id>/sessions?project=...` liefert
      alle Sessions sortiert nach `started_at DESC`.
- [x] AC6: `routes/session_routes.py` Marker-Lookup ist nicht mehr O(n_marker)
      pro Session-Detail-Aufruf - der gezielte Marker-Lookup ist
      O(n_marker) nur in der `parse_markers()`-Iteration der einen
      betroffenen handoff.md.
- [x] AC7: Smoke-Test: Schema-Migration, Backfill, Hook und neue Route
      laufen ohne Fehler auf der Live-DB.

## Arbeitspakete

### A - Schema-Migration

- [x] A1 `services/db_service.py`: neue Funktion `ensure_session_marker_schema()`
      mit `ALTER TABLE sessions ADD COLUMN IF NOT EXISTS marker_id VARCHAR(120)`,
      `marker_handoff_path TEXT`, Index `idx_sessions_marker_id`.
- [x] A2 Lazy-Init-Aufruf in `_api_session_detail_inner` und im Backfill-Script (Pattern wie `ensure_ai_scope_schema`, kein expliziter Startup-Call in `app.py` noetig).

### B - Backfill-Script

- [x] B1 `scripts/backfill_session_marker_id.py`: scannt alle Projekte,
      lockerer Aufbau wie `backfill_marker_last_sessions.py`.
- [x] B2 Pro Projekt: `parse_markers(handoff_path)`, fuer jeden Marker
      mit `last_session != ''` -> `UPDATE sessions SET marker_id=?, marker_handoff_path=? WHERE session_uuid=? AND marker_id IS NULL`.
- [x] B3 Logging: pro Projekt {markers_with_session, sessions_updated, sessions_already_set}.

### C - Post-Sync-Hook

- [x] C1 `services/session_import.py`: neue Funktion
      `_stamp_marker_context_after_sync()` - iteriert ueber alle Projekte
      mit `marker-context.md`, liest marker_id + mtime, stempelt Sessions
      seit mtime ohne `marker_id`.
- [x] C2 Aufruf am Ende von `sync_all()` nach `_save_hash_cache()`.
- [x] C3 Defensive: Fehler im Hook brechen den Sync nicht ab, nur Warning-Print.

### D - Read-Path

- [x] D1 `routes/session_routes.py`: neuer Helfer `_resolve_session_marker(s)`
      der erst `s["marker_id"]` aus DB nutzt, dann Fallback auf
      `get_marker_by_last_session`.
- [x] D2 SELECT-Statement der Session-Detail-Route um `marker_id`,
      `marker_handoff_path` ergaenzen.
- [x] D3 Neue Route `GET /api/markers/<marker_id>/sessions` mit
      optionalem `project`-Query-Param.

### E - Tests + Deploy

- [x] E1 Smoke-Test-Script (Python): Schema da, Backfill idempotent,
      Hook stempelt korrekt, Read-Path liefert Marker fuer historische Session.
- [x] E2 Backfill auf Live-DB ausfuehren, Counts protokollieren.
- [x] E3 `sudo systemctl restart project-dashboard`.
- [x] E4 End-to-End-Verifikation: `curl /api/sessions/<uuid>` zeigt Marker,
      `curl /api/markers/<id>/sessions?project=...` zeigt Verlauf.

### F - Doku

- [x] F1 `CLAUDE.md`: neuer Patterns-Eintrag "Session-Marker-Binding" unter
      "Wichtige Patterns".
- [x] F2 `sprints/master-plan-2026-04-01.md`: Sprint SB in Completed Sprints.
- [x] F3 `next-session.md`: Sprint SB DONE-Block, Folge-Optionen aufraeumen
      (Sprint A/C/D Liste korrigieren).
- [x] F4 Gitea-Issue schliessen via `fixes #N` im Commit.
