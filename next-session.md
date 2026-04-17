# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-17
> **Status:** Task-Entity, Task-Backfill, Multi-Source-Plan-Discovery und der neue `project_recursive`-Pfad sind im Code und live quergeprueft; offene Punkte sind jetzt Agent-Orchestrator Phase 1 und der Handoff-/Marker-Resolver.
> **Naechste Aufgabe:** 1. Agent-Orchestrator Phase 1 bauen, 2. Handoff-/Marker-Resolver umsetzen, 3. spaetere Scanner-Tuning-Themen nur bei echtem Bedarf anfassen.

---

## Was gilt jetzt

Der relevante Arbeitsstand fuer die naechste Session ist nicht mehr
`sprint-task-entity-und-drilldown`, sondern der aktuelle Critical Path:

- **NOW:** Agent-Orchestrator Phase 1 (`task_contract`, `session_state`, `preflight`)
- **NEXT:** automatischen Handoff-/Marker-Resolver bauen
- **LATER:** Scanner-Tuning nur fuer echte Folgeprobleme

Referenz dafuer:

- `sprints/NOW-next-critical-path.md`
- `sprints/sprint-agent-orchestrator-5-day-execution-plan.md`

## Naechste Aufgaben

### NOW

- [ ] Agent-Orchestrator Phase 1 bauen:
  `task_contract`, `session_state`, `preflight`

### NEXT

- [ ] automatischen Handoff-/Marker-Resolver fuer `project_id` / `plan_id` / `marker_id` bauen
- [ ] Scanner-Tuning-Folgepunkte nur bei echtem Bedarf aufnehmen (nicht sofort: False-Positive-Haertung, Bulk-Materialize, Auto-Tag-Policy)

### LATER

- [ ] Verify-Gates (`execution_result`, Claims, `verify_gate_result`, Close-Gate)
- [ ] Recovery + Doku-Gates (`recovery`, Append-only-/Sensitive-File-Regeln)

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
2. `sprints/NOW-next-critical-path.md` lesen
3. fuer Orchestrator-Arbeit: `sprints/sprint-agent-orchestrator-phase-1-foundation.md`
4. fuer Scanner-Abnahme: `sprints/sprint-full-project-recursive-plan-scanner.md`
5. fuer historische Sprint-Chronik: `sprints/master-plan-2026-04-01.md` (siehe Lesehinweis 2026-04-17)
6. bei Bedarf Referenz-Code: `services/plan_structure_service.py`, `services/markdown_routine_service.py`, `services/copilot_marker_import_flow.py`, `routes/copilot_marker_routes.py`
7. fuer Quellenhierarchie und Sofortkontext: `codex-skills/project-dashboard-context-routing/SKILL.md` und `codex-skills/project-dashboard-context-routing/references/session-2026-04-17.md`

Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich 12:30.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard`
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored)
- **sprints/:** gitignored — lokal, nicht auf GitHub

## Update 2026-04-17
- Changed: `project_recursive` live quergeprueft und danach bereinigt. Smoke-Datei und Alt-Records entfernt, Discovery fuer `handoff.md`/`next-session.md` gehaertet, `skipped`-Doppelzaehlung behoben.
- Files: `services/plan_discovery_service.py`, `services/plans_sync_service.py`, `tests/test_plan_discovery.py`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `pytest tests/test_plan_discovery.py::TestRecursiveScannerReal::test_md_ausserhalb_standardpfade_wird_gefunden_und_fuer_import_vorbereitet -v` → `1 passed`; rekursiver Smoke-Fall als `project_recursive` ohne Dublette belegt; grosser Sprintplan-Crosscheck auf `sprints/sprint-plan-discovery.md` zeigte saubere `project_sprints`-Zuordnung und 124 `plan_tasks` nach Lazy-Parse; Sync-Metrik stabil (`total=1020 unchanged=904 skipped=116 inserted=0 duration_ms=2360`).
- Next: Scanner als funktional abgenommen behandeln und nur noch echte Folgeprobleme separat anfassen; operativer Fokus jetzt auf Agent-Orchestrator Phase 1 und Handoff-/Marker-Resolver.

## Update 2026-04-17
- Changed: Repo-lokales Kontext-Skill fuer Codex/Agenten angelegt, damit die neue Quellenhierarchie und der bereinigte Stand dieser Session nicht erneut aus alten Chroniken rekonstruiert werden muessen.
- Files: `codex-skills/project-dashboard-context-routing/SKILL.md`, `codex-skills/project-dashboard-context-routing/references/session-2026-04-17.md`, `next-session.md`
- Verify: Skill definiert die gueltige Reihenfolge `next-session.md` -> `sprints/NOW-next-critical-path.md` -> passende Sprint-Datei; Session-Referenz fasst Scanner-Abschluss, Archivschnitt und aktuellen Critical Path kompakt zusammen.
- Next: Bei neuen Sessions zuerst das neue Kontext-Skill und die Session-Referenz heranziehen, bevor Archiv- oder Master-Plan-Bloecke gelesen werden.

## Update 2026-04-17
- Changed: `AGENTS.md` um eine harte Repo-Regel fuer Context Routing / Handoff Priority erweitert, damit die neue Quellenhierarchie nicht nur im Skill, sondern direkt in den Repo-Anweisungen fuer alle Agents steht.
- Files: `AGENTS.md`, `next-session.md`
- Verify: `AGENTS.md` priorisiert jetzt explizit `next-session.md` -> `sprints/NOW-next-critical-path.md` -> passende Sprint-Datei und stuft Master-Plan/Archiv als historische Quellen ein.
- Next: Neue Sessions sollen die operative Prioritaet nicht mehr aus Archiv- oder Chronikdateien ableiten.

## Update 2026-04-17
- Changed: Session-Sync gegen Cache-/DB-Drift gehaertet. JSONL-Dateien werden nicht mehr allein wegen `.sync_hashes.json` als `unchanged` uebersprungen, wenn der zugehoerige DB-Row fehlt. Damit koennen auch vorhandene Codex-Sessiondateien, inklusive `codex resume`-Runs, nach DB-Reset oder Teilverlust wieder sauber in `/sessions` auftauchen.
- Files: `services/session_import.py`, `tests/test_session_import.py`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `parse_codex_jsonl()` liest die echte `019d99fa-e6f3-70a1-8035-f9c947483a8e`-Datei korrekt (`session_uuid`, `cwd`, Zeitfenster, Messages); `pytest tests/test_session_import.py -q` -> `25 passed`.
- Next: Auf der laufenden Instanz einen Session-Sync anstossen, damit ggf. bisher nur gecachte, aber nicht persistierte Codex-Sessions neu eingelesen werden.

## Update 2026-04-17
- Changed: `README.md` auf den aktuellen Produktstand gezogen. SessionPilot beschreibt jetzt explizit Multi-Tool-Sessionimport (Claude, Codex, Gemini, OpenCode, Kilo), den robusteren Session-Sync und die allgemeineren `/api/sessions`-Beschreibungen.
- Files: `README.md`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: README-Abschnitte fuer Intro, Features, API und deutsche Produktbeschreibung spiegeln den aktuellen Import-/Sync-Stand wider.
- Next: Bei weiteren Session-Import-Aenderungen die Produktbeschreibung in README synchron halten, damit GitHub/Gitea-Stand nicht wieder hinter dem Code liegt.
