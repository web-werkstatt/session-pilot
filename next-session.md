# Projekt-Dashboard - Naechste Session

<!-- DASHBOARD-GENERATED:START source=session-handoff updated=2026-04-18 -->
> **Letzte Aktualisierung:** 2026-04-18
> **Status:** Sprint 1 DONE; Sprint 2 Commit 1 (Prompt-Export) + Commit 2 (CLI-Helper) DONE. 87 Agent-Orchestrator-Tests gruen. NOW: Sprint 2 Commit 3 — UI-Minimum.
> **Naechste Aufgabe:** Sprint 2 Commit 3 — UI-Minimum (Copy-Prompt-Button + Execution-Result-Textarea) implementieren.

---

## Was gilt jetzt

Der aktuelle Critical Path:

- **NOW:** Sprint 2 Commit 3 — UI-Minimum (`sprints/sprint-agent-orchestrator-executor-handoff.md §spec-commit-3-ui`)
- **NEXT:** Sprint 2 Commit 4 — Doku + Smoke-Test (`sprints/sprint-agent-orchestrator-executor-handoff.md §spec-commit-4-doku`)
- **LATER:** Sprint 3 Copilot-Chat; Modell A bei Bedarf; Scanner-Tuning nur bei Bedarf

Referenz: `sprints/NOW-next-critical-path.md`

## Naechste Aufgaben

### NOW

- [ ] Sprint 2 Commit 3: `templates/agent_task_detail.html` + `static/js/agent_task_detail.js` — Copy-Prompt-Button + Execution-Result-Textarea (AC3)

### NEXT

- [ ] Sprint 2 Commit 4: `docs/agent-orchestrator-executor-handoff.md` + manueller Smoke-Test (AC4)

### LATER

- [ ] Sprint 3 Copilot-Chat (10 Commits, `sprints/sprint-agent-orchestrator-copilot-chat.md`)
- [ ] Modell A (Executor-Adapter) bei echtem Bedarf reaktivieren
- [ ] Scanner-Tuning nur bei echtem Bedarf

### DONE (diese Session)

- [x] Sprint 2 Commit 2: `scripts/claude_task.py` (`pull|finish|verify|close`), `tests/test_claude_task_cli.py` (24 Tests), `scripts/README-claude-task.md` — 87 Tests gruen. Commit `1a36388`.
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

## Update 2026-04-17 — Drei neue Sprint-Plaene fuer Multi-Projekt-Einsatz
- Changed: Drei neue Sprints angelegt (Project-Config, Executor-Handoff Modell B, Copilot-Chat mit Nachtrag `during_task` + versionierbare Prompts); Executor-Adapter-Sprint (Modell A) zurueckgestellt mit Begruendung (Max-Policy, synchroner HTTP-Block). `NOW-next-critical-path.md`, `plan-directory.md` und Kopfblock dieses Files auf neuen Pfad ausgerichtet.
- Files: `sprints/sprint-agent-orchestrator-project-config.md` (neu), `sprints/sprint-agent-orchestrator-executor-handoff.md` (neu), `sprints/sprint-agent-orchestrator-copilot-chat.md` (neu), `sprints/sprint-agent-orchestrator-executor-adapter.md` (Status + Nachtrag), `sprints/NOW-next-critical-path.md`, `sprints/plan-directory.md`, `next-session.md`
- Verify: Kein Code veraendert. 44 Orchestrator-Tests unveraendert gruen. Alle vier Sprint-Dateien Status "Proposed" bzw. "Proposed — zurueckgestellt". Reihenfolge: Sprint 1 NOW, Sprint 2 NEXT, Sprint 3 LATER.
- Next: Sprint 1 Project-Config implementieren — Schema + Service-Grundlagen, Preflight auf Project-Config umstellen, Append-only-Diff parametrisieren, Resolver-Registry, Claim `docs_updated`, Admin-API.

## Update 2026-04-17 — Sprint 1 Project-Config umgesetzt
- Changed: Agent-Orchestrator ist nicht mehr dashboard-hardcoded. Neue Tabelle `agent_project_configs` (lazy), Service `agent_project_config_service` (get/set/delete mit Default-Fallback je Feld), `agent_task_contracts.project_id` als optionaler Bezug, `run_preflight` liest `sensitive_files` pro Task-Projekt, `agent_append_only_diff` nimmt Block-Regex-Paar projektspezifisch, Verify-Gate reicht Block-Regex und neuen Claim `docs_updated` (Diff via command_runner oder execution.changed_files; Match gegen `docs_paths`) durch, Resolver hat jetzt `register_project_lookups` / `unregister_project_lookups`, Admin-API GET/PUT `/api/agent-projects/<id>/config`.
- Files: `services/db_agent_project_config_schema.py` (neu), `services/agent_project_config_service.py` (neu), `services/db_service.py`, `services/db_agent_orchestrator_schema.py`, `services/agent_orchestrator_service.py`, `services/agent_append_only_diff.py`, `services/agent_verify_service.py`, `services/agent_orchestrator_resolver.py`, `routes/agent_orchestrator_routes.py`, `tests/test_agent_project_config.py` (neu), `tests/test_agent_orchestrator.py`, `tests/test_agent_verify.py`, `tests/test_agent_append_only_diff.py`, `next-session.md`, `sprints/sprint-agent-orchestrator-project-config.md`
- Verify: `python3 -m py_compile services/agent_project_config_service.py services/db_agent_project_config_schema.py services/agent_orchestrator_service.py services/agent_orchestrator_resolver.py services/agent_append_only_diff.py services/agent_verify_service.py services/db_agent_orchestrator_schema.py services/db_service.py routes/agent_orchestrator_routes.py` -> `ALL OK`; `pytest tests/test_agent_orchestrator.py tests/test_agent_verify.py tests/test_agent_append_only_diff.py tests/test_agent_recovery.py tests/test_agent_project_config.py -v` -> `69 passed in 1.63s` (44 Bestands-Tests gruen + 25 neue: 10 Project-Config-Tests inkl. Admin-API, 2 Preflight-mit-Project-Config, 3 Custom-Block-Regex Append-only, 6 Claim-`docs_updated`, 4 Resolver-Registry); `from app import app` listet `/api/agent-projects/<int:project_id>/config` (GET+PUT). Akzeptanzkriterien AC1-AC5 aus `sprint-agent-orchestrator-project-config.md §spec-akzeptanz` belegt: AC1 Lazy-Schema via `ensure_agent_project_config_schema`; AC2 Default-Fallback je Feld (`test_get_config_without_row_returns_defaults`, `test_set_config_overrides_only_given_field`); AC3 Preflight/Append-only/docs_updated ueber Config (`test_agent_orchestrator.py::test_preflight_uses_project_specific_sensitive_files`, `test_agent_verify.py::test_append_only_uses_project_specific_block_regex`, `test_docs_updated_*`); AC4 44 Bestandstests gruen; AC5 Dashboard laeuft ohne Eintrag dank Default-Fallback (`test_preflight_defaults_for_task_without_project`).
- Next: Sprint 2 Executor-Handoff Modell B angehen (`sprints/sprint-agent-orchestrator-executor-handoff.md`).

## Update 2026-04-17 — Sprint 2 Executor-Handoff Commit 1 umgesetzt (Prompt-Export)
- Changed: Commit 1 (Prompt-Export-Endpunkt) aus `sprint-agent-orchestrator-executor-handoff.md` umgesetzt. Neuer Service `agent_prompt_export_service.build_prompt_markdown()` rendert 8 Abschnitte (Titel, Ziel, erlaubte Dateien, verbotene Aktionen, Nachweise, Stop-Bedingungen, Handoff-Kontext mit Pfad + letzten 50 Zeilen + Marker-ID/Titel + Plan, Abschluss-Protokoll mit 3 Shell-Zeilen + UI-Fallback-Hinweis). Neue Route `GET /api/agent-tasks/<int:task_id>/prompt` liefert `text/markdown; charset=utf-8`. Auth ueber neuen Helper `services/agent_task_auth.py` mit Pflicht-Header `X-Agent-Task-Token` gegen `~/.agent-task-token` (v1-Default Plaintext); fehlt Datei oder Header -> 401. Auth-Check ist explizit NUR am neuen /prompt-Endpunkt, damit AC5 (bestehende Tests unveraendert) eingehalten bleibt. Query-Params `?project=&plan=&marker=` reichen durch den Resolver; ohne Params bleibt der Handoff-Abschnitt als "kein Handoff konfiguriert" stehen.
- Files: `services/agent_prompt_export_service.py` (neu), `services/agent_task_auth.py` (neu), `routes/agent_orchestrator_routes.py`, `tests/test_agent_prompt_export.py` (neu)
- Verify: `python3 -m py_compile services/agent_prompt_export_service.py services/agent_task_auth.py routes/agent_orchestrator_routes.py tests/test_agent_prompt_export.py` -> `ALL_OK`; `pytest tests/test_agent_prompt_export.py tests/test_agent_orchestrator.py tests/test_agent_orchestrator_resolver.py tests/test_agent_verify.py tests/test_agent_verify_project_config.py tests/test_agent_append_only_diff.py tests/test_agent_recovery.py tests/test_agent_project_config.py` -> `83 passed in 2.09s` (69 Bestands-Tests unveraendert gruen + 14 neue Prompt-Export-Tests: 8 Service-Tests fuer alle Kombinationen [mit/ohne Handoff, mit/ohne Marker, mit/ohne Plan, leere Listen, 50-Zeilen-Default, ValueError bei leerem Task] + 6 Route-Tests [401 ohne Token, 401 bei falschem Token, 401 wenn Token-Datei fehlt, 200 mit korrektem Token, 404 fuer unbekannten Task, Query-Param-Durchreichung an Resolver]); `from app import app` listet `/api/agent-tasks/<int:task_id>/prompt` (GET). AC1 aus `sprint-agent-orchestrator-executor-handoff.md §spec-akzeptanz` belegt durch `test_prompt_has_all_eight_sections_with_full_context` + Varianten-Tests. AC5 belegt: 69 Bestands-Tests unveraendert gruen.
- Next: Commit 2 (CLI-Helper `scripts/claude_task.py` mit `pull|finish|verify|close`) angehen.

## Update 2026-04-18 — Sprint 2 Commit 2 (CLI-Helper claude-task) umgesetzt
- Changed: `scripts/claude_task.py` mit Subcommands `pull|finish|verify|close`. Config-Prioritaet: env > `~/.agent-task.toml` > `~/.agent-task-token`. `finish` sammelt `git status --porcelain` + `git diff --stat HEAD`, berechnet Out-of-Scope clientseitig. `README-claude-task.md` als Kurzanleitung. 24 neue Tests (Config-Prioritaet, alle 4 Subcommands, echtes Git-Repo fuer finish, Out-of-Scope-Units).
- Files: `scripts/claude_task.py` (neu), `scripts/README-claude-task.md` (neu), `tests/test_claude_task_cli.py` (neu)
- Verify: `python3 -m py_compile scripts/claude_task.py tests/test_claude_task_cli.py` -> `ALL_OK`; `pytest tests/test_claude_task_cli.py ...` -> `87 passed in 1.20s` (83 Bestand + 24 neu). Commit `1a36388`.
- Next: Sprint 2 Commit 3 — UI-Minimum (`templates/agent_task_detail.html`, Copy-Prompt-Button + Execution-Result-Textarea).

