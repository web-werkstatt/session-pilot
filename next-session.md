# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-13 (Context-Window-Optimierung)
> **Status:** ADR-001 Welle 1 komplett (Prio 1-6). ADR-002 Stufe 1a+1b komplett (Observe/Review/Steer live). 746 Tests gruen.
> **Naechste Aufgabe:** CWO Phase 1 (Context Window Optimizer) implementieren, oder Policy-Reviewer Live-Test.

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
- [ ] **CWO Phase 1:** Context Window Optimizer als Dashboard-Feature (`sprints/sprint-cwo-context-window-optimizer.md`)
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

## Session 2026-04-13 — Context-Window-Optimierung + CWO Sprint-Plan

### Was wurde erledigt
- **CLAUDE.md modularisiert:** 271 → 102 Zeilen (-63%). Architektur-Listen in Unterverzeichnis-CLAUDE.md ausgelagert, Dateigroessen-Duplikat entfernt, Patterns auf Verbots-Charakter reduziert, Scheduled Tasks/Backup/META in Skill ausgelagert.
- **master-plan-summary.md erstellt:** 48-Zeilen-Summary statt 1.820-Zeilen-Vollversion. Fokusauftrag-Regel geaendert.
- **next-session.md rotiert:** 271 → 95 Zeilen. Session-Historie 2026-04-07 bis 2026-04-11 ins Archiv.
- **5 Unterverzeichnis-CLAUDE.md erstellt:** `routes/`, `services/`, `static/`, `templates/`, `sprints/` — nativer Claude-Code Lazy-Loading-Mechanismus.
- **Skill /project-ops erstellt:** Betriebsbefehle, systemd, Scheduled Tasks, Backup on-demand.
- **Session-End Skill ergaenzt:** Limit-Regel (max 130 Zeilen) + master-plan-summary-Check.
- **Globale Rule ergaenzt:** Pre-Commit-Hook-Verhalten + Praevention fuer neue Dateien.
- **Sprint-Plan CWO erstellt:** `sprints/sprint-cwo-context-window-optimizer.md` — 18 Tickets in 3 Phasen (Analyse, Perplexity-Review, Aktionen). Migrations-Map-Konzept: nichts wird geloescht, alles wird verschoben mit vollstaendiger Zuordnungstabelle.
- **plan-directory.md aktualisiert:** ADR-002, CWO-Sprint, Backlog-Eintraege.
- **master-plan-summary.md aktualisiert:** CWO als aktiver Sprint.
- **Einsparung:** Startup-Kontext von ~33.600 auf ~5.600 Tokens (-83%).

### Geaenderte/neue Dateien
| Datei | Aenderung |
|-------|-----------|
| `CLAUDE.md` | Modularisiert: 271 → 102 Zeilen |
| `next-session.md` | Rotiert + aktualisiert |
| `next-session-archiv.md` | Sessions 2026-04-07 bis 2026-04-11 archiviert |
| `routes/CLAUDE.md` | Neu: Route-Module-Index (33 Z.) |
| `services/CLAUDE.md` | Neu: Service-Schicht-Index (56 Z.) |
| `static/CLAUDE.md` | Neu: JS/CSS-Patterns (34 Z.) |
| `templates/CLAUDE.md` | Neu: Template-Konventionen (16 Z.) |
| `sprints/CLAUDE.md` | Neu: Sprint-Doku-Index (24 Z.) |
| `sprints/master-plan-summary.md` | Neu: Kompakter Master-Plan (48 Z.) |
| `sprints/sprint-cwo-context-window-optimizer.md` | Neu: CWO Sprint-Plan (18 Tickets) |
| `sprints/plan-directory.md` | Aktualisiert: ADR-002 + CWO |
| `~/.claude/skills/project-ops/SKILL.md` | Neu: Betriebsbefehle-Skill |
| `~/.claude/skills/session-end/SKILL.md` | Ergaenzt: Limit-Regel + Summary-Check |
| `~/.claude/rules/file-size-limits.md` | Ergaenzt: Hook-Verhalten + Praevention |

### Naechste Session
- [ ] **CWO Phase 1 starten:** `sprints/sprint-cwo-context-window-optimizer.md` Ticket 1.1 (DB-Schema + Constants)
- [ ] **Oder:** Policy-Reviewer Live-Test (POST /api/policies/review gegen Perplexity)
- [ ] Sprint-Plan CWO lesen, dann mit Ticket 1.1 beginnen
