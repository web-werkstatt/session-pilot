# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-09 (Dead-Code-Erkennung + Workflow-Integration)
> **Status:** Quality Scanner auf 10 Checks erweitert (+ Dead Code, Dead Deps, Dead Frontend). Dead-Code-Findings fliessen jetzt als eigenes Signal in den Workflow-Tab. Workflow-v2 Sprint 1 (Datenmodell, Transitions, API) ist DONE.
> **Naechste Aufgabe:** Dead Code V2 (Funktions-Analyse), Workflow-Card-Design vereinfachen, Dead-Code-Signal im Frontend rendern.

---

## Was gilt jetzt

Der Freeze-Stand **`v1.3-final`** bleibt als stabile Basis. Sprint CP (Workflow-Loop v1)
ist abgeschlossen. Jetzt laeuft **Sprint Workflow-v2**: Ausbau des Workflow-Tabs von
reiner Anzeige zu echtem operativem Steuerungssystem. Die GUI/UX-Schicht im Workflow-Tab
ist jetzt sichtbar umgesetzt; offene Arbeit ist nur noch Feintuning nach Live-Feedback.

## Naechste Aufgaben

### Code (Claude Code)

- [x] Dead-Code-Checks implementiert: `auto_coder/checks/dead_code.py`, `dead_dependencies.py`, `dead_frontend.py`
- [x] Dead-Code-Summary in Governance-Gate integriert (`services/governance_service.py`)
- [x] Dead-Code-Signal im Workflow-Loop (`services/workflow_loop_service.py`)
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung (`auto_coder/checks/dead_code.py`)
- [ ] Coverage-Input: `coverage.json` als zusaetzliche Evidenz fuer Dead-Code-Kandidaten
- [ ] Im Live-Betrieb pruefen, ob Workflow-Automatik zwischen Handoff-Status und Workflow-State ausreicht (`services/workflow_state_service.py`)

### GUI/UX (Codex)

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
| Backup taeglich | DONE — Cron 12:30, 7-Tage-Rotation |

## Was nicht da ist (= Deferred)

Siehe Master-Plan, Block "Deferred Sprints (post-closeout v1.3-final)".

## Wie naechste Session starten

1. Dieses File zuerst lesen
2. Sprint-Plan lesen: `sprints/sprint-workflow-v2-full-system.md`
3. Workflow-Tab eines echten Projekts mit Markern oeffnen
4. Pruefen, ob Starten, Blockieren, Reaktivieren, Write Back und Rating in der Praxis so stimmig wirken

Vollstaendiger Sprint-Plan mit GUI/UX-Specs pro Sprint:
- `sprints/sprint-workflow-v2-full-system.md`

Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich 12:30.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard` (active expected)
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **Backup manuell ausloesen:** `/mnt/projects/project_dashboard/scripts/backup.sh daily`
- **Cron-Zeiten:** daily 12:30, weekly Sonntag 13:30 (mittags weil Workstation nachts aus)
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored), CLAUDE.md-Regel: nie eigenmaechtig veraendern

## Session 2026-04-09 (Nachmittag) - Dead Code Detection + Workflow-Integration

### Was wurde erledigt
- 3 neue Quality-Checks: Dead Code (AST-basiert), Dead Dependencies, Dead Frontend
- Issue-Dataclass um `confidence` + `evidence` erweitert
- Governance-Gate: `dead_code_summary` mit Kategorie-Counts
- Workflow-Signal: Dead-Code-Findings als eigener Priority-Hint
- Workflow-v2 Sprint 1: Persistentes Datenmodell, Transition-Regeln, REST-API
- Sprint-Plan um GUI/UX-Specs erweitert, next-session.md Code/GUI-Split

### Scan-Ergebnis (project_dashboard)
38 ungenutzte Imports, 9 verwaiste Dateien, 2 Deps, 2 Assets, 28 CSS-Klassen

### Offene UX-Punkte (aus Codex-Session)
- Workflow-Cards: Informationshierarchie vereinfachen (Kopf/Mitte/Fuss-Struktur)
- Leerer Workflow: Marker-Erstellungspfad klaren (CTA aus Planning oder manuell)

### Vorherige Sessions
Siehe `next-session-archiv.md`
