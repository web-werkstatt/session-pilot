# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-13 (CWO Tickets 1.6+1.7)
> **Status:** CWO Phase 1a komplett (Tickets 1.1-1.7). Orchestrator + Storage + REST-API live. 165 Projekte analysiert, 0 Fehler.
> **Naechste Aufgabe:** CWO Phase 1 Ticket 1.8 (UI: Badge + Panel im Tool-Files-Modal)

---

## Was gilt jetzt

Der Freeze-Stand **`v1.3-final`** bleibt als stabile Basis. Sprint CP (Workflow-Loop v1)
ist abgeschlossen. Jetzt laeuft **Sprint Workflow-v2**: Ausbau des Workflow-Tabs von
reiner Anzeige zu echtem operativem Steuerungssystem. Die GUI/UX-Schicht im Workflow-Tab
ist jetzt sichtbar umgesetzt; offene Arbeit ist nur noch Feintuning nach Live-Feedback.

**Neue Architekturrichtung (ADR-001, 2026-04-10):** Marker-Definitionen und -State werden
DB-first gefuehrt. `handoff.md` wird zum Mirror-/Export-Artefakt degradiert. Ein neuer
`workflow_core_service` buendelt Plan -> Sprint -> Spec -> Marker -> State als zentrale
Domaenenschicht. Ein `tool_profile_adapter_service` pflegt generierte Bloecke in
CLAUDE.md/AGENTS.md/GEMINI.md. Perplexity-Copilot wird Read-Only-Validierungsschicht
(vorschlagsbasiert, Joseph bleibt finale Autoritaet). Siehe `sprints/adr-001-db-first-marker-core-tool-adapter.md`.

## Naechste Aufgaben

### Code (Claude Code)

- [x] Dead-Code-Checks implementiert: `auto_coder/checks/dead_code.py`, `dead_dependencies.py`, `dead_frontend.py`
- [x] Dead-Code-Summary in Governance-Gate integriert (`services/governance_service.py`)
- [x] Dead-Code-Signal im Workflow-Loop (`services/workflow_loop_service.py`)
- [x] **ADR-001 Prio 1:** Marker-DB-Tabelle (`services/db_marker_schema.py`) + `services/workflow_core_service.py` + `services/marker_importer.py`
- [x] **ADR-001 Prio 2:** `services/block_marker_parser.py` + `services/write_guard.py` (Produktfeature: Block-Marker-Schutz fuer alle Projekte)
- [x] **ADR-001 Prio 3:** Idempotenter Importer aus handoff.md in DB (`services/marker_importer.py`, `import_all_projects()` bereit)
- [x] **ADR-001 Prio 4:** `workflow_loop_service` + `copilot_marker_service` + `plan_structure_service` + `copilot_service` auf Core umgebaut
- [x] **ADR-001 Prio 5:** Write-Back: Core -> handoff.md (Mirror, via Write-Guard)
- [x] **ADR-001 Prio 6:** `tool_profile_adapter_service.py` fuer bestehende Projekte (via Write-Guard)
- [x] **ADR-002 Stufe 1a+1b:** Setup-Reviewer, Policy-Schicht, Perplexity-Integration (746 Tests)
- [x] **Context-Window-Optimierung:** CLAUDE.md modularisiert (271→102 Z.), master-plan-summary, Unterverz.-CLAUDE.md, Skill /project-ops
- [x] **CWO Phase 1 Ticket 1.1:** DB-Schema + Constants + Grundgeruest (db_cwo_schema, constants, checks/__init__, actions/__init__)
- [x] **CWO Phase 1 Ticket 1.2:** Context Collector (context_collector.py, Smoke-Test bestanden)
- [x] **CWO Phase 1 Ticket 1.3:** Check-Framework + Token-Budget-Check (run_all_checks, Auto-Discovery, Severity-Sortierung)
- [x] **CWO Phase 1 Ticket 1.4:** Dateigroessen-Checks 1-4 (oversize_claude_md, oversize_tool_files, focus_file_size, next_session_growth)
- [x] **CWO Phase 1 Ticket 1.5:** Struktur-Checks 5-7 (global_rule_duplicates, missing_subdir_claude, extractable_sections)
- [x] **CWO Phase 1 Ticket 1.6:** Orchestrator + Storage (`orchestrator.py`, `storage.py`)
- [x] **CWO Phase 1 Ticket 1.7:** REST-Endpoints (`routes/context_window_optimizer_routes.py`)
- [ ] **CWO Phase 1 Ticket 1.8:** UI: Badge + Panel im Tool-Files-Modal
- [ ] **Policy-Reviewer Live-Test:** POST /api/policies/review gegen Perplexity testen
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung
- [ ] ADR-002 Stufe 2a: Dispatch-Einstieg (work_assignments-Tabelle)

### GUI/UX (Codex)

- [x] Workflow-Cards reduziert: Cards zeigen nur Status, Titel, `Naechster Schritt`, wenige Meta-Chips und Workflow-Aktionen; Rating, Write-Back-Checkliste und Blocker-Begruendung liegen im Modal, Owner/Flags/Inline-Editoren sind aus den Cards entfernt, Grid-Cards sind wieder gleich hoch (`services/workflow_loop_service.py`, `static/js/workflow-loop.js`, `static/css/workflow-loop.css`)
- [x] Sprachregel ergänzt: `AGENTS.md` verlangt bei deutscher Prosa echte Umlaute und `ß`, außer in Code, Dateinamen, technischen IDs oder bestehendem ASCII-Text.
- [ ] Dead-Code-Hint im Workflow-Tab mit eigenem Icon und Kategorie-Breakdown rendern: bei `hint.label === "Dead Code"` Unterliste mit Imports/Dateien/Deps anzeigen (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`)
- [ ] `dead_code_summary` aus `signals` als kompakte Info-Karte im Workflow-Tab anzeigen: "38 Imports · 9 Dateien · 2 Deps" mit Link zu `/quality?project=<name>` (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`)
- [ ] Owner separat editierbar machen, auch ohne Statuswechsel (`static/js/workflow-loop.js`, `routes/workflow_routes.py`)
- [ ] Microcopy der Marker-Gruppen und CTA-Reihenfolge feinjustieren (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`)

## Was funktioniert (= Bestand)

| Bereich | Status |
|---|---|
| Session-Verwaltung | DONE — Multi-Account, Live-Viewer, Reviews, Export |
| Plans-Import + Detail | DONE — `/plans` mit Tabs, Sprint-Plans-Liste |
| Cockpit / Copilot-Board | DONE — Marker-Cards, Drag&Drop, Chat-Kontext, Session-Marker-Binding |
| Quality Scanner | DONE — `/quality` mit 10 Checks (+ Dead Code, Dead Deps, Dead Frontend) |
| Governance Light | DONE — `/governance` mit Policy-Levels, Gate-Ampel |
| Workflow Loop v1 | DONE — Visualisierung, Deep-Links, Signale |
| **Workflow-v2 Sprint 1** | **DONE — Persistentes Datenmodell, Transition-Regeln, REST-API, Sync** |
| **ADR-001 Welle 1 (Prio 1-6)** | **DONE — Marker-DB, Core, Importer, Write-Guard, Mirror, Tool-Profile-Adapter** |
| **ADR-002 Stufe 1a+1b** | **DONE — Setup-Reviewer, Policy-Schicht, Perplexity, /policies** |
| **Context-Window-Optimierung** | **DONE — CLAUDE.md modularisiert, master-plan-summary, Unterverz.-CLAUDE.md** |
| Backup taeglich | DONE — Cron 12:30, 7-Tage-Rotation |

## Was nicht da ist (= Deferred)

Siehe Master-Plan, Block "Deferred Sprints (post-closeout v1.3-final)".

## Wie naechste Session starten

1. Dieses File zuerst lesen
2. `sprints/master-plan-summary.md` als Rahmen lesen (statt des vollstaendigen Master-Plans)
3. Status-Uebersicht lesen: `sprints/status-adr002-stufe1-abschluss.md`
4. Bei Bedarf ADRs nachlesen: `sprints/adr-001-*.md`, `sprints/adr-002-*.md`

Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich 12:30.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard` (active expected)
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **Backup manuell ausloesen:** `/mnt/projects/project_dashboard/scripts/backup.sh daily`
- **Cron-Zeiten:** daily 12:30, weekly Sonntag 13:30 (mittags weil Workstation nachts aus)
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored), CLAUDE.md-Regel: nie eigenmaechtig veraendern

## Session 2026-04-13 (Nacht 2) — CWO Phase 1 Tickets 1.6+1.7

### Was wurde erledigt
- **CWO Ticket 1.6:** Orchestrator (`orchestrator.py`) — `analyze_project()` verbindet Context Collector → Checks → Findings-Aggregation → token_budget_rating → DB-Persistierung. `analyze_all_projects()` fuer Batch. context_hash-Dedup (force-Flag). Storage (`storage.py`) mit Upsert auf `cwo_analyses`, `load_analysis()`, `load_all_analyses()`.
- **CWO Ticket 1.7:** REST-Endpoints (`routes/context_window_optimizer_routes.py`) — 4 Endpoints: POST/GET `/api/project/<name>/cwo/analyze`, POST `/api/cwo/analyze-all`, GET `/api/cwo/overview` mit `?rating=` Filter.
- **DB-Migration:** `error`-Spalte in `cwo_analyses` ergaenzt (ALTER TABLE in `db_cwo_schema.py`).
- **Bugfix:** `scan_projects()` gibt Dict (nicht Liste) zurueck — Orchestrator angepasst.

### Geaenderte/neue Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/context_window_optimizer/orchestrator.py` | Neu: analyze_project(), analyze_all_projects() |
| `services/context_window_optimizer/storage.py` | Neu: save_analysis(), load_analysis(), load_all_analyses() |
| `services/context_window_optimizer/__init__.py` | Erweitert: 5 neue Exports (Orchestrator + Storage) |
| `services/db_cwo_schema.py` | Migration: error-Spalte in cwo_analyses |
| `routes/context_window_optimizer_routes.py` | Neu: 4 REST-Endpoints (cwo_bp Blueprint) |
| `routes/__init__.py` | cwo_bp registriert |

### Statistik (165 Projekte)
| Rating | Anzahl |
|--------|--------|
| ok | 146 |
| info | 19 |
| warning | 0 |
| error | 0 |

Top Token-Verbraucher: visual-editor (19.008), proj_progrKI (18.576), irtours-claude-branch (17.514).

### Naechste Session
- [ ] **CWO Ticket 1.8:** UI: Token-Budget-Badge am Tool-Files-Button + CWO-Panel im Modal (Findings, Migration-Map, File-Inventory)
- [ ] Sprint-Plan: `sprints/sprint-cwo-context-window-optimizer.md`
- [ ] Danach: Phase 1b (Tickets 1.9-1.11: Perplexity-Review)

## Session 2026-04-13 (Nacht) — CWO Phase 1 Tickets 1.3-1.5

### Was wurde erledigt
- **CWO Ticket 1.3:** Check-Framework vervollstaendigt — `run_all_checks()` mit Auto-Discovery via `pkgutil`, Severity-Sortierung (error>warning>info), Fehlerresilienz (Exception → Error-Finding). Token-Budget-Check (Check 8) als erster konkreter Check.
- **CWO Ticket 1.4:** Dateigroessen-Checks 1-4 — `oversize_claude_md.py` (mit Migration-Map-Heuristik fuer Sektions-Auslagerung), `oversize_tool_files.py` (AGENTS.md/GEMINI.md), `focus_file_size.py` (Fokusauftrag-Dateien mit Summary-Vorschlag), `next_session_growth.py` (Rotations-Vorschlag).
- **CWO Ticket 1.5:** Struktur-Checks 5-7 — `global_rule_duplicates.py` (Jaccard 3-Wort-Shingles), `missing_subdir_claude.py` (Verzeichnisse mit >=3 Code-Dateien ohne CLAUDE.md), `extractable_sections.py` (Listen-lastige Sektionen mit >10 Items).
- **Bugfix:** `get_all_checks()` triggert jetzt auch Auto-Discovery (vorher nur `run_all_checks`).
- **Smoke-Test:** 106 Projekte, 202 Findings, alle Severity-Stufen verifiziert. project_dashboard: 0 Findings (korrekt).

### Geaenderte/neue Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/context_window_optimizer/checks/__init__.py` | Erweitert: run_all_checks(), Auto-Discovery, Severity-Sortierung |
| `services/context_window_optimizer/checks/token_budget.py` | Neu: Check 8 — Token-Budget Gesamt |
| `services/context_window_optimizer/checks/oversize_claude_md.py` | Neu: Check 1 — CLAUDE.md Uebergroesse + Migration-Map |
| `services/context_window_optimizer/checks/oversize_tool_files.py` | Neu: Check 2 — AGENTS.md/GEMINI.md |
| `services/context_window_optimizer/checks/focus_file_size.py` | Neu: Check 3 — Fokusauftrag-Dateien |
| `services/context_window_optimizer/checks/next_session_growth.py` | Neu: Check 4 — next-session.md Wachstum |
| `services/context_window_optimizer/checks/global_rule_duplicates.py` | Neu: Check 5 — Duplikate mit globalen Rules |
| `services/context_window_optimizer/checks/missing_subdir_claude.py` | Neu: Check 6 — Fehlende Unterverz.-CLAUDE.md |
| `services/context_window_optimizer/checks/extractable_sections.py` | Neu: Check 7 — Auslagerbare Listen-Sektionen |
| `services/context_window_optimizer/__init__.py` | Erweitert: Check-Exports (run_all_checks, get_all_checks, CWOFinding etc.) |

### Statistik (106 Projekte)
| Check | Findings |
|-------|----------|
| missing_subdir_claude | 102 |
| extractable_sections | 46 |
| oversize_claude_md | 30 |
| token_budget | 18 |
| next_session_growth | 5 |
| oversize_tool_files | 1 |
| global_rule_duplicates | 0 |
| focus_file_size | 0 |

### Naechste Session
- [ ] **CWO Ticket 1.6:** Orchestrator (`orchestrator.py`) — Analyse-Flow: Context Collector → Checks → Findings aggregieren → Storage (DB-Persistierung)
- [ ] **CWO Ticket 1.7:** REST-Endpoints (`routes/context_window_optimizer_routes.py`) — POST/GET /api/project/<name>/cwo/analyze, POST /api/cwo/analyze-all, GET /api/cwo/overview
- [ ] Danach: Ticket 1.8 (UI: Badge + Panel im Tool-Files-Modal)
- [ ] Sprint-Plan: `sprints/sprint-cwo-context-window-optimizer.md`

## Session 2026-04-13 (Abend) — CWO Phase 1 Ticket 1.1 + 1.2

### Was wurde erledigt
- **CWO Ticket 1.1:** DB-Schema (`cwo_analyses` + `cwo_action_log`), Constants (Schwellwerte, Token-Faktoren, Load-Modes, Actions), Check-Framework (`BaseCWOCheck`, `CWOFinding`, `MigrationEntry`, Registry), Action-Framework (`BaseAction`), Facade `__init__.py`
- **CWO Ticket 1.2:** Context Collector (`context_collector.py`) — sammelt Tool-Files, next-session, Fokusauftrag-Dateien, Unterverz.-CLAUDE.md, globale Rules, Sektionsanalyse, Token-Schaetzung. Smoke-Test: 8.798 Tokens fuer project_dashboard.
- **pyrightconfig.json:** Pyright-Config mit `extraPaths` statt `py.typed` (interne Flask-App, kein PyPI-Package)
- **DB live:** `ensure_cwo_schema()` in `db_service.py` registriert, Tabellen in PostgreSQL erstellt

### Geaenderte/neue Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/db_cwo_schema.py` | Neu: CWO DB-Schema (2 Tabellen) |
| `services/context_window_optimizer/__init__.py` | Neu: Re-Export-Facade |
| `services/context_window_optimizer/constants.py` | Neu: Schwellwerte, Actions, Load-Modes |
| `services/context_window_optimizer/checks/__init__.py` | Neu: Check-Framework + Datenklassen |
| `services/context_window_optimizer/actions/__init__.py` | Neu: Action-Framework |
| `services/context_window_optimizer/context_collector.py` | Neu: Analyse-Kontext-Sammler |
| `services/db_service.py` | `ensure_cwo_schema()` hinzugefuegt |
| `pyrightconfig.json` | Neu: Pyright extraPaths Config |

### Naechste Session
- [ ] **CWO Ticket 1.6:** Orchestrator (`orchestrator.py`) — Analyse-Flow: Context Collector → Checks → Findings aggregieren → Storage
- [ ] **CWO Ticket 1.7:** REST-Endpoints (`routes/context_window_optimizer_routes.py`) — POST/GET /api/project/<name>/cwo/analyze, POST /api/cwo/analyze-all, GET /api/cwo/overview
- [ ] Sprint-Plan: `sprints/sprint-cwo-context-window-optimizer.md`
