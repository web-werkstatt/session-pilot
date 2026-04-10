# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-10 (ADR-001 Prio 1+3+4 implementiert)
> **Status:** ADR-001 Kern implementiert: `markers`-DB-Tabelle, `workflow_core_service`, `marker_importer`, alle Lese-/Schreibpfade in `copilot_marker_service` und `workflow_loop_service` auf DB-first umgestellt. 598 Tests gruen. Quality-Scanner IGNORE_DIRS fuer Multi-CLI gefixt.
> **Naechste Aufgabe:** ADR-001 Prio 2: `block_marker_parser.py` + `write_guard.py` (Produktfeature: Block-Marker-Schutz), dann Prio 3: Migration aller Projekte via `import_all_projects()`.

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
- [ ] **ADR-001 Prio 2:** `services/block_marker_parser.py` + `services/write_guard.py` (Produktfeature: Block-Marker-Schutz fuer alle Projekte)
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
| **ADR-001 Prio 1+3+4** | **DONE — Marker-DB, Core-Service, Importer, alle Lese-/Schreibpfade auf DB-first** |
| Backup taeglich | DONE — Cron 12:30, 7-Tage-Rotation |

## Was nicht da ist (= Deferred)

Siehe Master-Plan, Block "Deferred Sprints (post-closeout v1.3-final)".

## Wie naechste Session starten

1. Dieses File zuerst lesen
2. ADR lesen: `sprints/adr-001-db-first-marker-core-tool-adapter.md`
3. Sprint-Plan lesen: `sprints/sprint-adr001-welle1-db-first-core.md` (Ticket 3)
4. Mit ADR-001 Prio 2 starten: `block_marker_parser.py` + `write_guard.py`

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
