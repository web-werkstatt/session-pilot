# Projekt-Dashboard - Naechste Session

<!-- DASHBOARD-GENERATED:START source=session-handoff updated=2026-04-17 -->
> **Letzte Aktualisierung:** 2026-04-17
> **Status:** Agent-Orchestrator Phase 3 verschlankt ist im Code. Gemeinsamer Append-only-Diff-Check (`services/agent_append_only_diff.py`), Claim `append_only_respected` als `required_verification`-Typ `append_only_diff` im Verify-Gate, Recovery-Snapshot-Builder + Persistenz (`services/agent_recovery_snapshot.py`), `agent_session_states.recovery_snapshot_json` (ALTER TABLE IF NOT EXISTS), `POST /api/agent-sessions/<id>/recover`. 44 Tests gruen (32 Phase 1+2 + 12 Phase 3).
> **Naechste Aufgabe:** Keine offene Phase aus dem 5-Tage-Plan. Nur bei Bedarf: Scanner-Tuning-Folgepunkte.

---

## Was gilt jetzt

Der aktuelle Critical Path:

- **NOW:** — (alle Tage aus dem 5-Tage-Plan DONE)
- **NEXT:** Scanner-Tuning-Folgepunkte nur bei echtem Bedarf
- **LATER:** —

Referenz dafuer:

- `sprints/NOW-next-critical-path.md`
- `sprints/sprint-agent-orchestrator-phase-2-3-reshaped.md` (Phase 2 + Phase 3 DONE)
- `docs/agent-orchestrator-hardening-technical-spec.md`

## Naechste Aufgaben

### NOW

- [ ] —

### NEXT

- [ ] Scanner-Tuning-Folgepunkte nur bei echtem Bedarf (False-Positive-Haertung, Bulk-Materialize, Auto-Tag-Policy)

### LATER

- [ ] —

### DONE (diese Session)

- [x] Agent-Orchestrator Phase 3 verschlankt (Append-only-Gate + Recovery-Snapshot): `services/agent_append_only_diff.py` (neu), `services/agent_recovery_snapshot.py` (neu), Claim `append_only_respected` via `required_verification`-Typ `append_only_diff` in `services/agent_verify_service.py`, `agent_session_states.recovery_snapshot_json` per ALTER TABLE IF NOT EXISTS in `services/db_agent_orchestrator_schema.py`, `get_session_state` liefert `recovery_snapshot`, neuer Endpoint `POST /api/agent-sessions/<id>/recover`, 12 neue Tests (`test_agent_append_only_diff.py` + `test_agent_recovery.py`) — siehe Sprint-Nachtrag 2026-04-17 in `sprint-agent-orchestrator-phase-2-3-reshaped.md` §spec-phase3-done
<!-- DASHBOARD-GENERATED:END -->

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

## Update 2026-04-17
- Changed: Fehlversuch beim Zusammenfuehren von `github/main` in das interne Repo dokumentiert. Der Commit `7331fda` entfernte versehentlich interne Projektdateien (`AGENTS.md`, `handoff.md`, `next-session.md`, `sprints/`, `tests/`), weil der oeffentliche GitHub-Mirror eine bereinigte Historie ohne diese Dateien hat. Der Fehler wurde sofort mit `280b6f8` revertiert; die fehlenden Repo-Dateien sind lokal und auf `origin/main` wiederhergestellt.
- Files: `AGENTS.md`, `handoff.md`, `next-session.md`, `sprints/master-plan-2026-04-01.md`, `tests/test_session_import.py`, `next-session.md`
- Verify: Nach `git revert -m 1 --no-edit 7331fda` existieren `AGENTS.md`, `next-session.md`, `handoff.md`, `sprints/master-plan-2026-04-01.md` und `tests/test_session_import.py` wieder; Revert-Commit `280b6f8` ist nach `origin/main` gepusht.
- Next: GitHub-Mirror kuenftig nicht mehr in `main` mergen. Falls der oeffentliche Mirror weiter gepflegt werden soll, nur ueber einen separaten Mirror-Branch oder einen expliziten Export-/Cleanup-Workflow arbeiten.

## Update 2026-04-17 — Handoff-/Marker-Resolver (Tag 3) umgesetzt
- Changed: Resolver + Bootstrap fuer den Agent-Orchestrator gebaut. `resolve_context(project_id, plan_id?, marker_id?)` liefert `handoff_path`, aktiven Marker, relevanten Plan und `start_scope`; `bootstrap_task(...)` kombiniert Resolver + `create_task` und setzt `allowed_files` per Default auf den Start-Scope.
- Files: `services/agent_orchestrator_resolver.py` (neu), `services/agent_orchestrator_service.py`, `routes/agent_orchestrator_routes.py`, `tests/test_agent_orchestrator.py`, `next-session.md`, `sprints/NOW-next-critical-path.md`, `sprints/sprint-agent-orchestrator-5-day-execution-plan.md`
- Verify: `python3 -m py_compile services/*.py routes/*.py` -> ALL_OK; `pytest tests/test_agent_orchestrator.py -v` -> 19 passed; `from app import app` zeigt `/api/agent-tasks/resolve-context` und `/api/agent-tasks/bootstrap` als POST registriert.
- Next: Verify-Gate MVP gemaess `sprints/sprint-agent-orchestrator-phase-2-3-reshaped.md` (Phase 2 verschlankt) anfangen.

## Update 2026-04-17 — Agent-Orchestrator Phase 1 (Foundation) umgesetzt
- Changed: Fundament fuer den Agent-Orchestrator gebaut. Das Programm hat jetzt erstmals einen maschinenlesbaren `agent_task_contract`, einen expliziten `agent_session_state` und einen `preflight_result`-Check vor Executor-Start. Scope strikt auf Phase 1 begrenzt (kein Verify-Gate, keine Recovery, keine Doku-Gates).
- Files:
  - `services/db_agent_orchestrator_schema.py` (neu) — Tabellen `agent_task_contracts` + `agent_session_states`, lazy idempotent nach Muster der anderen `ensure_*_schema_impl`.
  - `services/agent_orchestrator_service.py` (neu) — `create_task`, `get_task`, `get_session_state`, `set_session_state` (upsert mit automatischem `previous_state`), `run_preflight` mit injizierbarem `git_runner` fuer Tests, Scope-Diff gegen `allowed_files` und Sensitive-File-Flag fuer `next-session.md` / `handoff.md` / `sprints/master-plan-2026-04-01.md`.
  - `services/db_service.py` — `ensure_agent_orchestrator_schema()` als Delegator ergaenzt.
  - `routes/agent_orchestrator_routes.py` (neu) — `POST /api/agent-tasks`, `GET /api/agent-tasks/<id>`, `POST /api/agent-tasks/<id>/preflight`, `GET/POST /api/agent-sessions/<session_id>/state`. Fehler-Handling ueber `@api_route`.
  - `routes/__init__.py` — Blueprint importiert und registriert.
  - `tests/test_agent_orchestrator.py` (neu) — In-Memory-Fake fuer `execute`, 9 Tests fuer Task-CRUD, Session-State-Transitionen und alle Preflight-Pfade (Scope-Hit, Scope-Miss, Sensitive-File, Untracked, unbekannter Task).
- Verify:
  - `python3 -m py_compile services/*.py routes/*.py` → `ALL OK`.
  - `pytest tests/test_agent_orchestrator.py -v` → `9 passed in 0.06s`.
  - `from app import app` + `url_map` listet alle vier neuen Routes: `/api/agent-tasks`, `/api/agent-tasks/<int:task_id>`, `/api/agent-tasks/<int:task_id>/preflight`, `/api/agent-sessions/<session_id>/state` (GET + POST).
  - Akzeptanzkriterien AC1-AC5 aus `sprints/sprint-agent-orchestrator-phase-1-foundation.md` durch Tests belegt.
- Next: Gemaess `sprints/NOW-next-critical-path.md` als naechstes den Handoff-/Marker-Resolver bauen (`project_id` / `plan_id` / `marker_id` → `handoff_path`, aktiver Marker, relevanter Plan, Start-Scope). Verify-Gates, Claim-Modell, Close-Gate und Recovery-/Doku-Gates bleiben bewusst NEXT/LATER und werden erst nach dem Resolver angefasst.

## Update 2026-04-17 — Agent-Orchestrator Phase 2 (Verify-Gate MVP) umgesetzt
- Changed: Verify-Gate MVP verschlankt implementiert. Neue Schemata `agent_execution_results` + `agent_verify_results`, Service mit `record_execution`, `run_verify_gate` (Command-Runner per DI), `evaluate_close` + `close_task`, fuenf neue Endpunkte (`POST/GET /api/agent-tasks/<id>/execution`, `POST/GET /api/agent-tasks/<id>/verify`, `POST /api/agent-tasks/<id>/close`). Claim-Typen in Scope: `tests_passed`, `syntax_check_passed`, `smoke_test_done`, `feature_complete`. `append_only_respected` und `docs_updated` bewusst nicht dabei (Phase 3).
- Files: `services/db_agent_verify_schema.py` (neu), `services/agent_verify_service.py` (neu), `services/db_service.py`, `routes/agent_orchestrator_routes.py`, `tests/test_agent_verify.py` (neu), `next-session.md`, `sprints/NOW-next-critical-path.md`, `sprints/sprint-agent-orchestrator-phase-2-3-reshaped.md`
- Verify: `python3 -m py_compile services/agent_verify_service.py services/db_agent_verify_schema.py routes/agent_orchestrator_routes.py services/db_service.py tests/test_agent_verify.py` → `ALL_OK`; `pytest tests/test_agent_verify.py tests/test_agent_orchestrator.py -v` → `32 passed in 1.34s`; `from app import app` listet `/api/agent-tasks/<int:task_id>/execution`, `/verify` (GET+POST) und `/close` (POST). AC1-AC4 aus `sprint-agent-orchestrator-phase-2-3-reshaped.md §spec-phase2-akzeptanz` belegt durch dedizierte Tests (AC1 `test_ac1_tests_passed_without_runner_is_blocked`, AC2 `test_ac2_tests_passed_with_exit_zero_is_pass`, AC3 `test_ac3_close_rejected_without_verify` + `test_ac3_close_rejected_when_verify_not_pass` + `test_ac3_close_ok_when_verify_pass_sets_session_done`, AC4 `test_ac4_execution_and_verify_readable_after_write`).
- Next: Phase 3 verschlankt angehen (Append-only-Diff-Check fuer sensitive Dateien + Recovery-Snapshot ohne Restore). Zielschnitt steht in `sprints/sprint-agent-orchestrator-phase-2-3-reshaped.md §spec-phase3-*`.

## Update 2026-04-17 — Agent-Orchestrator Phase 3 (Append-only-Gate + Recovery-Snapshot) umgesetzt
- Changed: Phase 3 verschlankt implementiert. Gemeinsamer Append-only-Diff-Check mit DASHBOARD-GENERATED-Block-Awareness, Claim `append_only_respected` via `required_verification`-Typ `append_only_diff` im Verify-Gate, Recovery-Snapshot-Builder (git status + diff-stat + risk_flags) + Persistenz auf `agent_session_states.recovery_snapshot_json` (ALTER TABLE IF NOT EXISTS), neuer Endpoint `POST /api/agent-sessions/<id>/recover`. Kein Auto-Trigger, kein Restore — nur Snapshot, wie im Sprint festgelegt.
- Files: `services/agent_append_only_diff.py` (neu), `services/agent_recovery_snapshot.py` (neu), `services/agent_verify_service.py`, `services/agent_orchestrator_service.py`, `services/db_agent_orchestrator_schema.py`, `routes/agent_orchestrator_routes.py`, `tests/test_agent_append_only_diff.py` (neu), `tests/test_agent_recovery.py` (neu), `next-session.md`, `sprints/NOW-next-critical-path.md`, `sprints/sprint-agent-orchestrator-5-day-execution-plan.md`, `sprints/sprint-agent-orchestrator-phase-2-3-reshaped.md`
- Verify: `python3 -m py_compile services/agent_append_only_diff.py services/agent_recovery_snapshot.py services/agent_orchestrator_service.py services/agent_verify_service.py services/db_agent_orchestrator_schema.py routes/agent_orchestrator_routes.py tests/test_agent_append_only_diff.py tests/test_agent_recovery.py` → `ALL_OK`; `pytest tests/test_agent_verify.py tests/test_agent_orchestrator.py tests/test_agent_append_only_diff.py tests/test_agent_recovery.py -v` → `44 passed in 0.68s` (32 Phase 1+2 + 7 Append-only-Diff + 5 Recovery); `from app import app` + `url_map` listet `/api/agent-sessions/<session_id>/recover` zusaetzlich zu allen vorherigen Agent-Routen. AC1-AC4 aus `sprint-agent-orchestrator-phase-2-3-reshaped.md §spec-phase3-akzeptanz` belegt durch dedizierte Tests (AC1 `test_ac1_diff_in_generated_block_passes`, AC2 `test_ac2_diff_in_manual_text_outside_block_is_blocked`, AC3 `test_ac3_append_at_eof_passes`, AC4 `test_ac4_recovery_api_persists_snapshot_and_sets_state` + `test_ac4_recovery_api_accepts_explicit_snapshot`).
- Next: 5-Tage-Plan ist damit komplett umgesetzt. Offen bleibt nur (nicht beauftragt): Auto-Trigger von `recover` durch Preflight-Ergebnisse, Restore-Logik, Claim `docs_updated` — alle bewusst ausserhalb Scope.
