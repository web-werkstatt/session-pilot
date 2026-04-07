# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-07 (Sprint SB DONE)
> **Status:** Sessions↔Marker-Bindung jetzt hart in der DB. Backfill 7 Sessions, Hook fuer kuenftige Sessions aktiv, Read-Path und neue Verlauf-Route deployed.
> **Naechste Aufgabe:** Naechster Sprint waehlen (siehe Optionen unten)

---

## Session 2026-04-07 (dritter Block) - Sprint SB Session-Marker-Binding

### Befund vor dem Sprint

- `sessions` kannte ihren Marker nicht. Reverse-Lookup ueber `routes/session_routes.py:278` -> `get_marker_by_last_session()` (services/copilot_marker_service.py:148).
- `marker.last_session` in `handoff.md` ist 1:1 - nur die *letzte* Session pro Marker findbar, alle vorherigen bekamen `marker = null`.
- `next-session.md` hatte das urspruenglich als "Title-Matching" beschrieben - das war ungenau.

### Umgesetzt

**Schema (`services/db_service.py`):**
- `ensure_session_marker_schema()`: `sessions.marker_id VARCHAR(120)`, `sessions.marker_handoff_path TEXT`, Index `idx_sessions_marker_id`. Lazy + Lock-Pattern wie `ensure_ai_scope_schema`.

**Backfill (`scripts/backfill_session_marker_id.py`):**
- Scannt alle Projektordner unter `PROJECTS_DIR`, parst jede `handoff.md` mit `parse_markers()`.
- Fuer jeden Marker mit `last_session != ''`: `UPDATE sessions SET marker_id, marker_handoff_path WHERE session_uuid=? AND marker_id IS NULL`.
- Idempotent durch `marker_id IS NULL`-Guard.
- Erster Lauf: 7/7 Sessions in `project_dashboard` aktualisiert.
- Zweiter Lauf: 0 Updates, 7 already_set.

**Post-Sync-Hook (`services/session_import.py`):**
- `_stamp_marker_context_after_sync()` iteriert nach jedem `sync_all()` ueber alle Projekte mit `marker-context.md`.
- Liest `- marker_id:` und mtime, stempelt alle Sessions mit `started_at >= mtime` und `marker_id IS NULL`.
- Fehler je Projekt brechen den Sync nicht ab (defensiv, nur Print).
- **Single point of change**: deckt alle 5 Importer (claude/codex/gemini/opencode/kilo) ohne Modifikation ab.

**Read-Path (`routes/session_routes.py`):**
- Neuer Helper `_resolve_session_marker(project_name, session_uuid, stored_marker_id)`.
- Bevorzugt DB-`marker_id` -> gezielter `get_marker_context()`-Lookup. Fallback auf `get_marker_by_last_session()` fuer Sessions ohne DB-Stempel.
- `ensure_session_marker_schema()` in `_api_session_detail_inner` aufgerufen.
- SELECT war bereits `*` -> neue Spalten kommen automatisch im Response mit.

**Neue Route (`routes/copilot_marker_routes.py`):**
- `GET /api/markers/<marker_id>/sessions?project=...` - liefert Verlauf aller verknuepften Sessions sortiert nach `started_at DESC`.

### Verifikation auf Live-System

```bash
# Schema (ueber Service-Layer)
ensure_session_marker_schema()  # ok

# Backfill
python3 scripts/backfill_session_marker_id.py
# {"sessions_updated": 7, "sessions_already_set": 0, ...}
python3 scripts/backfill_session_marker_id.py
# {"sessions_updated": 0, "sessions_already_set": 7, ...}  -> idempotent

# Service-Restart
sudo systemctl restart project-dashboard  # active

# Read-Path Test
curl /api/sessions/032e4f9f-7ff4-4980-94cc-10a8e13b04c4
# marker_id: 141, marker_handoff_path: /mnt/projects/.../handoff.md
# marker.titel: "Sprint-Plan: Projekt-Metadaten Erweiterung"

# Verlauf-Route
curl /api/markers/141/sessions?project=project_dashboard
# ok: True, count: 1
```

### Akzeptanzkriterien (7/7)

- AC1 Schema-Spalten + Index ✓
- AC2 Backfill idempotent ✓
- AC3 Post-Sync-Hook funktional ✓ (Code-Pfad identisch zum Backfill)
- AC4 Read-Path nutzt DB-marker_id zuerst ✓
- AC5 Verlauf-Route liefert Sessions ✓
- AC6 Marker-Lookup gezielt statt O(n_marker)-Iteration ✓
- AC7 End-to-End auf Live-DB ✓

### Geaenderte Dateien

| Datei | Aenderung |
|-------|-----------|
| `services/db_service.py` | + `ensure_session_marker_schema` |
| `services/session_import.py` | + `_stamp_marker_context_after_sync`, sync_all-Hook |
| `routes/session_routes.py` | + `_resolve_session_marker`, neuer Read-Path |
| `routes/copilot_marker_routes.py` | + `GET /api/markers/<id>/sessions` |
| `scripts/backfill_session_marker_id.py` | NEU |
| `sprints/sprint-sb-session-marker-binding.md` | NEU - Sprint-Plan |
| `CLAUDE.md` | Patterns-Eintrag "Session-Marker-Binding" |
| `sprints/master-plan-2026-04-01.md` | Sprint SB Completed-Block |
| `next-session.md` | dieses Update |

### Gitea-Issues

- #20 wird beim Commit per `fixes #20` geschlossen

---

## Naechste Session - Optionen

Aus Master-Plan offenen Sprints (Sprint A/B/C/D sind alle DONE - ist in der alten Optionsliste falsch gelistet gewesen):

- **Sprint QS** - DB-First State Consolidation (JSON-Stores → DB). Logischer Anschluss an Sprint SB, weil das Schema-Pattern jetzt etabliert ist.
- **Sprint 14** - Sprint-Flow-Tracking. Profitiert direkt vom Session-Marker-Binding (Verlauf pro Marker jetzt verfuegbar).
- **Sprint 15** - Turn-Level-Rating. Setzt auf 14 auf.
- **Sprint 12** - Governance Feedback-Loop (Voll-Version, nur Light als Sprint C DONE).
- **Sprint 13** - Bidirektionaler LLM-Control (Voll-Version, nur MVP als Sprint D DONE).
- **Sprint 16** - Workflow-Profiles.
- **Sprint 6** - DeRep Fixer.
- **Sprint 8** - Automation Tuning.
- **Sprint 20** - Product Launch Bundle.
- **Audit-Weiterentwicklung** - Quality-Score als `input_facts`, Governance-Gate-Integration, automatischer Trigger.

**Empfehlung naechstes Mal:** **Sprint 14 (Sprint-Flow-Tracking)** - direkter Nutzwert des frischen Session-Marker-Bindings, baut darauf auf.
