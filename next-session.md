# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-10 (ADR-001 Prio 1+2+3+4 implementiert)
> **Status:** ADR-001 Prio 1-4 komplett. Block-Marker-Schutz (Prio 2) produktiv: Parser, Write-Guard mit Atomic Write + File-Lock, Integration in `project_handoff_service`. 635 Tests gruen.
> **Naechste Aufgabe:** ADR-001 Prio 5: Write-Back Core -> handoff.md (Mirror, via Write-Guard), dann Prio 6: `tool_profile_adapter_service.py`.

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
- [ ] **ADR-001 Prio 5:** Write-Back: Core -> handoff.md (Mirror, via Write-Guard)
- [ ] **ADR-001 Prio 6:** `tool_profile_adapter_service.py` fuer bestehende Projekte (via Write-Guard)
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung (`auto_coder/checks/dead_code.py`)
- [ ] Coverage-Input: `coverage.json` als zusaetzliche Evidenz fuer Dead-Code-Kandidaten

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
| **ADR-001 Prio 1+2+3+4** | **DONE — Marker-DB, Core-Service, Importer, DB-first, Block-Marker-Schutz mit Write-Guard** |
| Backup taeglich | DONE — Cron 12:30, 7-Tage-Rotation |

## Was nicht da ist (= Deferred)

Siehe Master-Plan, Block "Deferred Sprints (post-closeout v1.3-final)".

## Wie naechste Session starten

1. Dieses File zuerst lesen
2. ADR lesen: `sprints/adr-001-db-first-marker-core-tool-adapter.md`
3. Sprint-Plan lesen: `sprints/sprint-adr001-welle1-db-first-core.md` (Ticket 3 DONE, Ticket 4 offen)
4. Mit ADR-001 Prio 5 starten: Write-Back Core -> handoff.md (Mirror, via Write-Guard)

Architektur-Referenz:
- `sprints/adr-001-db-first-marker-core-tool-adapter.md` (bindende Architekturentscheidung)
- `sprints/sprint-qs-db-first-state-consolidation.md` (Migrationsstrategie)
- `sprints/sprint-workflow-v2-full-system.md` (GUI/UX-Specs)

Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich 12:30.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard` (active expected)
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **Backup manuell ausloesen:** `/mnt/projects/project_dashboard/scripts/backup.sh daily`
- **Cron-Zeiten:** daily 12:30, weekly Sonntag 13:30 (mittags weil Workstation nachts aus)
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored), CLAUDE.md-Regel: nie eigenmaechtig veraendern

## Session 2026-04-10 (Abend) - ADR-001 Prio 1+3+4: DB-First Marker Core

### Was wurde erledigt
- `services/db_marker_schema.py` (neu): `markers`-Tabelle + `executor_tool` in `marker_workflow_states`
- `services/marker_importer.py` (neu): Idempotenter Import aus handoff.md (9 Marker importiert, Re-Run: 0 neue)
- `services/workflow_core_service.py` (neu): `get_markers()`, `get_marker()`, `update_marker_field()`, `update_marker_state()`, `get_handoff_view()`
- `services/db_service.py`: `ensure_marker_schema()` Delegate
- `services/copilot_marker_service.py`: Komplett auf DB-first umgestellt — `_resolve_marker()` und `_resolve_markers()` als zentrale Resolver, alle 12 Funktionen umgebaut, Inline-Imports konsolidiert
- `services/workflow_loop_service.py`: Marker via `core_get_markers()`
- `services/plan_structure_service.py`: `_get_markers_with_fallback()` Helper
- `services/copilot_service.py`: `core_get_marker()` fuer Chat-Kontext
- `services/copilot_marker_import_flow.py`: DB-Sync nach Sprint-zu-Marker-Konversion
- Quality-Scanner: `IGNORE_DIRS` um `.kilo`, `.codex`, `.aider`, `.serena`, `.playwright-mcp` erweitert, jscpd-Globs + Post-Filter
- Smoke-Test: `/copilot` 302-Redirect als erlaubt
- 598 Tests gruen, 0 Failures

### Architektur-Muster
- **DB-first mit Fallback:** `_resolve_marker()` / `_resolve_markers()` lesen aus DB, fallen auf handoff.md zurueck (Tests ohne DB, Uebergangsphase)
- **Dual-Write:** Schreib-Operationen aktualisieren handoff.md (Mirror) UND DB
- **Auto-Import:** Core importiert automatisch aus handoff.md wenn DB leer

## Historie

- **2026-04-10 (Nacht):** ADR-001 Prio 2 implementiert: Block-Marker-Parser + Write-Guard als Produktfeature. Code-Review durchgefuehrt (Korrektheit=2, Architektur-Fit=1 im Ausgangszustand), daraufhin gezielter Refactor: `_compare_content()` auf SequenceMatcher umgestellt, APPEND_ONLY auf Prefix-Check vereinfacht, Parser fail-closed bei defekten Markern, SOURCE_ALLOWLIST als Uebergangs-Policy fuer handoff.md, Atomic Write (temp+fsync+rename), File-Lock (fcntl.flock) mit TOCTOU-Schutz. Integration in `project_handoff_service.write_handoff()`. 37 neue Tests, 635 gesamt. Alle 7 Akzeptanzkriterien erfuellt. Commit `44f52f6` (`services/block_marker_parser.py`, `services/write_guard.py`, `services/project_handoff_service.py`, `tests/test_block_marker_parser.py`, `tests/test_write_guard.py`, `tests/test_write_guard_hardening.py`).
- **2026-04-10:** ADR-001 Prio 1+3+4 implementiert: `markers`-DB-Tabelle, `workflow_core_service`, `marker_importer`. Alle Marker-Lese-/Schreibpfade in `copilot_marker_service`, `workflow_loop_service`, `plan_structure_service`, `copilot_service` auf DB-first mit handoff.md-Fallback umgestellt. Zentrale Resolver `_resolve_marker()` / `_resolve_markers()` eingefuehrt. Quality-Scanner `IGNORE_DIRS` fuer Multi-CLI-Setups (.kilo, .codex, .aider, .serena) erweitert, jscpd-Globs + Post-Filter. 598 Tests gruen (`services/db_marker_schema.py`, `services/marker_importer.py`, `services/workflow_core_service.py`, `services/copilot_marker_service.py`, `services/workflow_loop_service.py`, `auto_coder/config.py`, `auto_coder/checks/duplication.py`).
- **2026-04-10:** Szenarien-Analyse (4 Szenarien: Neues Projekt, Bestehendes Projekt, Multi-LLM, China-LLMs) durchgefuehrt. Freigabe-Matrix erstellt. 4 Coding-Tickets definiert (Marker-DB, Core-Service, Write-Guard, Tool-Update). Sprint-Plan `sprints/sprint-adr001-welle1-db-first-core.md` und Planverzeichnis `sprints/plan-directory.md` erstellt. Korrekturen aus Review: Wrapper statt Modell fuer China-LLMs, Atomic Write Pattern, Idempotente Re-Generierung.
- **2026-04-10:** ADR-001 erstellt: DB-First Marker Core + Tool-Adapter + Perplexity-Review-Layer. Sprint-Nachtraege in Sprint 17 (Architekturprinzip ueberholt), Sprint CP (AC5 + Risiko 3 ueberholt), Sprint QS (Status auf Bindend), Master-Plan (Data Persistence Block aktualisiert). Perplexity-Copilot als vorschlagsbasierte Read-Only-Validierungsschicht verankert, Joseph bleibt finale Autoritaet (`sprints/adr-001-db-first-marker-core-tool-adapter.md`, `sprints/sprint-17-*.md`, `sprints/sprint-cp-*.md`, `sprints/sprint-qs-*.md`, `sprints/master-plan-*.md`).
- **2026-04-10:** Workflow-Cards im Workflow-Tab auf User-Feedback hin entmischt: `rating` und `write_back` werden backendseitig jetzt unter `Wartet` gruppiert, damit unter `AKTIV` nur echte Execution-Marker stehen. Cards zeigen nur noch Status, Titel, `Naechster Schritt`, wenige Meta-Chips und Workflow-Aktionen; Rating, Write-Back-Checkliste und Blocker-Begruendung oeffnen im Marker-Modal. Owner-Badge, Status-Flags und Inline-Editoren wurden aus den Cards entfernt; Grid-Cards sind wieder gleich hoch, die Aktionsleiste sitzt unten (`services/workflow_loop_service.py`, `static/js/workflow-loop.js`, `static/css/workflow-loop.css`).
- **2026-04-10:** Sprachregel in `AGENTS.md` ergänzt: Deutsche Prosa soll echte Umlaute und `ß` verwenden; ASCII bleibt für Code, Dateinamen, technische IDs, Shell-Befehle und bestehende ASCII-only-Texte erlaubt.
- **2026-04-09:** Weiterer offener UX-Punkt fuer die naechste Session festgehalten: Die Workflow-Cards sind funktional deutlich weiter, aber visuell noch zu unruhig. Das Problem ist weniger fehlende Daten als fehlende Informationshierarchie. Zu viele gleich starke Elemente konkurrieren in einer Card gleichzeitig (`Status`, `Flags`, `Owner`, `Meta`, `Text`, `Actions`). Fuer die naechste Session sollte deshalb ein reiner Design-Schnitt geplant werden: Kopf nur mit Status + Titel, Mitte nur mit einem klaren `Naechster Schritt`, Fuss nur mit 1 Primaeraktion + 1 Sekundaeraktion; Zusatzinfos wie Owner, Session oder Execution nur noch leise und kritisch nur bei echten Sonderfaellen wie `Blockiert` oder `Rating offen` (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`).
- **2026-04-09:** Offener UX-Punkt im Workflow-Tab explizit festgehalten: Wenn ein Projekt noch keine Marker hat, bleibt der Workflow derzeit leer und der Nutzer muss gedanklich sowie navigationstechnisch zurueck nach `Planning` oder Copilot springen. Das System ist technisch konsistent, aber als Arbeitsfluss noch nicht geschlossen. Fuer die naechste Denk-/Bauphase sollte deshalb sauber entschieden werden, wie Marker initial entstehen sollen: CTA `Marker aus Planning erzeugen`, manueller `Ersten Marker anlegen`-Pfad oder ein halbautomatischer Bruecken-Flow direkt aus dem leeren Workflow-State. Nichts loeschen, sondern diese Luecke als eigenstaendigen Produktpunkt weiterdenken (`static/js/workflow-loop.js`, `services/workflow_loop_service.py`, `routes/copilot_marker_routes.py`).
- **2026-04-09:** Workflow-Tab von reiner Anzeige zu operativem Arbeitsbereich ausgebaut: Ringgrafik blieb erhalten, darunter gibt es jetzt gruppierte Marker-Boards (`Aktiv`, `Wartet`, `Blockiert`) mit Owner-Badges, Blocker-Textarea, Write-Back-Checkliste, kompaktem Rating-Widget und echten Inline-Aktionen fuer Starten, Blockieren, Reaktivieren, Write Back und Rating. Das Backend liefert dafuer Marker-Gruppen inklusive erlaubter Transitionen; der Workflow-Sync bewahrt feinere Stati wie `ready`, `write_back` und `rating` jetzt stabiler gegen Handoff-Sync (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`, `services/workflow_loop_service.py`, `services/workflow_state_service.py`).
- **2026-04-09:** Session-Detailseite entkoppelt den Breadcrumb vom Rueck-CTA (`templates/session_detail.html`, `static/js/session-detail.js`, `static/js/project-planning.js`).
- **2026-04-09:** Session-Detail-TOC lesbarer gemacht (`static/css/session-detail.css`, `static/js/session-toc.js`).
- **2026-04-09:** `Projects` im Sidebar-Menue staerkerer aktiver Hintergrund (`static/css/sidebar-submenu.css`).
- **2026-04-09:** `Quality` auf der Projektseite signalisiert Report-Status direkt im Sekundaerlink (`templates/project_detail.html`, `static/js/project-detail.js`, `static/css/project-detail.css`).
- **2026-04-09:** Governance-Uebersicht auf Entscheidungslogik vereinfacht (`templates/governance.html`, `static/js/governance.js`, `static/css/governance.css`).
- **2026-04-09:** `/quality` GUI/UX nachgeschaerft: risikoorientierte Projektliste, Quality Briefing (`templates/quality.html`, `static/js/quality.js`, `static/css/quality.css`).
- **2026-04-09:** Monorepo-Detailseiten verbessert + `Was kann ich verbessern?` Block (`routes/project_info_routes.py`).
- **2026-04-09:** Planning fuer Subprojekte + Fortschrittsblock (`services/plan_structure_service.py`, `routes/plans_routes.py`, `static/js/project-planning.js`).
- **2026-04-09:** Workflow-Loop Intro-Block und Leerzustand gestrafft (`static/js/workflow-loop.js`, `static/js/workflow-loop-svg.js`, `static/css/workflow-loop.css`).
- **2026-04-08:** Sprint CP fachlich abgeschlossen + deployt. Workflow-Loop v1, Thread-Fortsetzung, Abschluss-Flow.
- **2026-04-08:** Projektseite auf 3 Haupttabs reduziert (Details, Planning, Workflow). Planning-Tab entmischt.
- **2026-04-08:** Read-only-GETs gehaertet, Workflow-Loop v1 implementiert und getestet.
- **2026-04-07:** Sprint SB DONE, Closeout (M1-M14), Tag `v1.3-final`
- **Davor:** siehe `next-session-archiv.md` und `master-plan-2026-04-01.md`

## Session 2026-04-11 - ADR-001 Prio 5 DONE

### Was wurde erledigt
- **ADR-001 Prio 5:** `write_handoff_mirror(project_name)` in `services/workflow_core_service.py` — regeneriert handoff.md aus DB-Markern via `write_guard.safe_write` mit Source `workflow_core_service`
- `_read_preamble` bewahrt YAML-Frontmatter + Text oberhalb von `## Copilot Markers` (kein Flip von `stage`/`scope` zwischen `project_handoff_service` und Mirror)
- `_build_marker_section` sortiert deterministisch nach `(plan_id, marker_id)`, idempotent bei gleichem DB-State
- Pre-Import via `import_markers_from_handoff` schuetzt manuell angelegte Marker (z.B. `test-cockpit-2026-04-05`) vor Drop bei Regenerierung
- `_trigger_mirror_write` laeuft best-effort am Ende von `update_marker_field` (und transitiv `update_marker_state`), Mirror-Fehler propagieren nicht (DB bleibt Source of Truth)
- 10 neue Tests in `tests/test_workflow_core_mirror.py`: Empty-Projekt, DB-Marker, Preamble-Preservation, Idempotenz, Deterministic-Ordering, unknown-Projekt, beide Trigger-Pfade, Mirror-Fehler-Isolation, write_guard-Source-Check
- 645/645 Tests gruen, null Regressionen
- Issue #21, Commit `24a19b3`

### Naechste Aufgabe
**ADR-001 Prio 6:** `services/tool_profile_adapter_service.py` fuer bestehende Projekte (via Write-Guard). Pflegt `DASHBOARD-GENERATED`-Bloecke in `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`, ersetzt nur markierte Bereiche, nutzt `block_marker_parser` + `write_guard.safe_write`. Abhaengigkeit Prio 2+5 erfuellt. Akzeptanzkriterien siehe `sprints/sprint-adr001-welle1-db-first-core.md` Ticket 4.

### Nicht im Scope (Prio 5b / Follow-up)
- `copilot_marker_service._write_marker` behaelt vorerst Direct-Write-Path (bypasst write_guard). Core-Mirror ueberschreibt nachgelagert, Content-kompatibel. Vollstaendiger Umbau auf Core-Single-Writer erfordert `last_execution_at` in `update_marker_field.allowed`-Set + Refactoring der Tests in `test_copilot_marker_service_core.py` / `test_copilot_marker_service_flow.py`, die `_write_marker` direkt nutzen.

## Session 2026-04-11 (Nachmittag) - Workflow-v2 UX Follow-up + Asset-Split + ADR-001 Prio 6 DONE

### Was wurde erledigt
- **Uncommitted-Aufraeumen:** vier logische Commits aus dem Working-Tree geloest (Sprint Workflow-v2 UX Follow-up war als DONE dokumentiert, aber nie committet; handoff.md wurde automatisch durch Prio-5 Mirror erweitert; CLAUDE.md META-Block + Gap-Analyse waren unkommittet).
- **Asset-Split wegen Dateigroessen-Limits:** `static/css/workflow-loop.css` (773 Zeilen) in vier thematische Dateien aufgeteilt (`workflow-loop-shell.css` 188, `workflow-loop-cards.css` 108, `workflow-loop-forms.css` 190, `workflow-loop-summary.css` 284). `static/js/workflow-loop.js` (767 Zeilen) auf `window.WorkflowLoop`-Namespace verteilt: `state.js` (67), `cards.js` (191), `board.js` (156), `modal.js` (98), `actions.js` (203), Orchestrator `workflow-loop.js` (68). Template `templates/project_detail.html` (339 Zeilen) um Documents-Tab als `templates/_project_documents_tab.html` entlastet, jetzt 246 Zeilen. Live-verifiziert via Chrome-DevTools MCP: Workflow-Tab rendert Intro/Ring/Summary/Card-Gruppen/Board korrekt, null Console-Errors.
- **ADR-001 Prio 6 Core:** `services/tool_profile_adapter_service.py` (374 Zeilen). Zwei Schreibpfade: Bootstrap (Atomic-Write mit File-Lock + TOCTOU-Re-Check, fuer Erst-Setup ohne bestehenden Block) und Update (ueber `write_guard.safe_write`). `_guard_protected_unchanged` verifiziert im Bootstrap-Pfad, dass MANUAL/UNMARKED-Zeilen 1:1 erhalten bleiben. `build_dashboard_block` deterministisch mit festem `updated`-Parameter fuer Idempotenz-Tests.
- **ADR-001 Prio 6 REST:** In `routes/project_routes.py` zwei Endpoints ergaenzt: `GET /api/project/<name>/tool-profile/preview` (Dry-Run mit Unified-Diff pro Tool) und `POST /api/project/<name>/tool-profile/regenerate` (schreibt, liefert 409 bei Write-Guard-Verletzung). `_tool_profile_meta` liest `project.json` fuer Typ/Description.
- **ADR-001 Prio 6 UI:** Topbar-Button "Tool Files" in `project_detail.html`. `static/js/tool-profile-adapter.js` (123 Zeilen) erzeugt den Modal dynamisch per `document.body.appendChild`, laedt die Preview beim Oeffnen, zeigt Diff + Mode-Badge (`Erst-Setup` / `Update` / `Keine Aenderungen`) pro Tool-Datei, "Regenerate schreiben"-Button fuehrt den POST-Call aus. Live getestet: Modal zeigt korrekt die drei Diffs fuer CLAUDE.md/AGENTS.md/GEMINI.md mit Bootstrap-Badge.
- **14 neue Tests** in `tests/test_tool_profile_adapter.py`: 11 fuer den Core-Service (Deterministik, Bootstrap mit 200 manuellen Zeilen intakt, Idempotenz, Update-Replacement, Preview-Dry-Run, regenerate_all ueber alle Tools, unknown-Tool, fremder generated Block) + 3 fuer die REST-Endpoints (Preview-Diffs, idempotenter Regenerate-Flow, 404 fuer unbekanntes Projekt).
- **659/659 Tests gruen** (+14 neue), null Regressionen.
- **4 Commits**, nach Gitea gepusht:
  - `526f5cd` Sprint: Workflow-v2 UX Follow-up + Asset-Split + ADR-001 Nachtraege
  - `6e977e3` Docs: META-Transparenz-Anforderungen + Managed Agents Gap Analysis
  - `7ab334a` Feature: ADR-001 Prio 6 — tool_profile_adapter_service (Core)
  - `4a326d6` Feature: ADR-001 Prio 6 — Tool-Profile Adapter REST + UI

### Akzeptanzkriterien Ticket 4 (Sprint ADR-001 Welle 1)
- Bestehende CLAUDE.md mit 200 manuellen Zeilen nach Update intakt: erfuellt (`test_bootstrap_preserves_200_manual_lines`)
- DASHBOARD-GENERATED-Block korrekt eingefuegt/aktualisiert: erfuellt (Bootstrap- und Update-Pfad)
- Dry-Run zeigt Diff ohne zu schreiben: erfuellt (`preview_update` + GET-Endpoint, live verifiziert)
- UI-Button funktional mit Preview-Dialog: erfuellt (Topbar-Button "Tool Files", Modal mit Diff-Anzeige, live verifiziert)
- Idempotent (zweites Regenerate erzeugt keinen Diff): erfuellt (`test_second_regenerate_is_idempotent`, REST-idempotent-Test)

### Naechste Aufgabe
**ADR-001 Welle 1 abgeschlossen.** ADR-001 Prio 7 (Capability-/Skill-Modell, unabhaengig) und Prio 8 (Perplexity-Review-Layer ueber generierte Artefakte, Abhaengigkeit Prio 5+6) sind die logischen Folgen. Alternativ offene GUI/UX-Punkte aus dem Workflow-v2-Follow-up:
- Dead-Code-Hint im Workflow-Tab mit eigenem Icon und Kategorie-Breakdown rendern (`static/js/workflow-loop-cards.js` oder `board.js`, `static/css/workflow-loop-forms.css`)
- `dead_code_summary` aus `signals` als kompakte Info-Karte im Workflow-Tab
- Owner separat editierbar machen, auch ohne Statuswechsel
- Microcopy der Marker-Gruppen und CTA-Reihenfolge feinjustieren

### Nicht im Scope (Follow-up)
- Block-Inhalt der `DASHBOARD-GENERATED`-Section ist aktuell minimal (Projekt-Name, Tool, Typ, Description, Stand). Marker-Count, Plan-Count, Quality-Score koennten ergaenzt werden, brauchen aber DB-Queries aus `_tool_profile_meta` und sind in `build_dashboard_block` vorbereitet (`meta["marker_count"]`, `meta["plan_count"]`, `meta["quality_score"]` werden bereits gerendert, wenn gesetzt).
- GitHub-Mirror nicht gepusht (Verkaufsschutz laut Memory-Regel).

## Session 2026-04-11 (Abend) — ADR-002 + Sprint-Plan Stufe 1 (Doku-Rahmen)

### Was wurde erledigt
- **ADR-002** angelegt: *AI-Control-Plane fuer kooperierende Multi-LLM-Systeme* (`sprints/adr-002-ai-control-plane-multi-llm-reviewer.md`, Status ACCEPTED). Produktdefinition als modellagnostische Control-Plane ueber mehreren LLMs, Fuenf-Ebenen-Architektur (Steuerung/Planung/Umsetzung/Pruefung/Freigabe), Observe-Review-Steer-Schichten, Perplexity als Reviewer-Rolle (provider-agnostisch), DB-first Policy-Schicht fuer Rollen und Tool-Zuweisungen, 10 Kernregeln. Prio 7 aus ADR-001 zurueckgestellt, Prio 8 erweitert und vorgezogen.
- **Sprint-Plan Stufe 1** angelegt (`sprints/sprint-adr002-stufe1-control-plane.md`): 10 Commits in Stufe 1a (Setup-Reviewer als kleinste funktionierende Control-Plane) + Stufe 1b (Policy-Schicht mit 4 DB-Tabellen, Seed-Defaults, Perplexity-Policy-Reviewer, REST, /policies-UI, workflow_core_service-Integration).
- **Nachtraege (append-only)** an:
  - `sprints/adr-001-db-first-marker-core-tool-adapter.md` (Prio 7 zurueckgestellt, Prio 8 durch ADR-002 abgeloest)
  - `sprints/master-plan-2026-04-01.md` (Produktdefinition als AI-Control-Plane bindend)
  - diese Datei

### Offene Arbeit (Commits 2-10)
- **Commit 2 (Stufe 1a):** Setup-Reviewer Core + `project_reviews`-Schema + `context_drift`-Check
- **Commit 3 (Stufe 1a):** Setup-Reviewer REST + minimale UI-Anzeige im Tool-Files-Modal — Stufe 1a vollstaendig
- **Commit 4-9 (Stufe 1b):** Policy-Schema, Seed-Defaults (6 Rollen), Perplexity-Policy-Reviewer, REST, `/policies`-UI, `workflow_core_service`-Integration
- **Commit 10:** Session-Close + Push

### Leitlinien aus den Planungsgespraechen
- Kein Auto-Write, auch bei hohem Confidence. Joseph entscheidet.
- Policies sind Daten, keine Konstanten. Keine hart kodierten Best-Practices.
- Reviewer ist Rolle, nicht Provider. Perplexity = erste Backend-Implementierung.
- Ein Writer pro Marker, mehrere Reviewer moeglich.
- Reviewer nie derselbe Provider wie Executor.
- Stufe 1a ist Proof-of-Concept vor Stufe 1b — nach Commit 3 kann Joseph pausieren und testen.
