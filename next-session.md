# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-14 (Session 15: Dispatch Sprint 2a Commits 7-8)
> **Status:** Dispatch Pull-Adapter + Perplexity-Gate + Integration. Commits 7+8 done, Commit 9 offen.
> **Naechste Aufgabe:** Dispatch Sprint 2a Commit 9 (Doku + Push) oder Unified Cockpit Phase 7

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

- [x] Dead-Code-Checks, Governance-Gate, Workflow-Signal (3 Module)
- [x] ADR-001 komplett (Prio 1-6): Marker-DB, Core, Importer, Write-Guard, Mirror, Tool-Profile
- [x] ADR-002 Stufe 1a+1b: Reviewer, Policies, Perplexity, CWO Phase 1a+1b (11 Tickets)
- [x] Finding-Decisions + Rausch-Reduktion + Metriken-Dashboard + UX-Ueberarbeitung
- [x] ADR-002 Stufe 2a Commit 6: Dispatch-UI in Cockpit-Panel
- [x] Unified Cockpit Phase 1-5: Backend, JS-Param, Route, Workflow-Ring, Board+Badges
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung
- [x] **ADR-002 Stufe 2a Commit 7:** Pull-Adapter + Perplexity-Gate
- [x] **ADR-002 Stufe 2a Commit 8:** Integration workflow_core + Settings-Toggles
- [ ] **ADR-002 Stufe 2a Commit 9:** Doku + Push (offen)
- [x] **Unified Cockpit Phase 6:** Sprint-Sections demoten + Plan-Filter-Dropdown
- [ ] **Unified Cockpit Phase 7:** Projekt-Detail bereinigen (DEFERRED)

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
| Basis-Features | DONE — Sessions, Plans, Quality, Governance, Backup |
| Workflow-System | DONE — Loop v1+v2, ADR-001 (Marker-DB, Core, Write-Guard) |
| AI-Control-Plane | DONE — ADR-002 Stufe 1 (Reviewer, Policies, Perplexity, CWO, Metriken) |
| **Unified Cockpit Phase 1-6** | **DONE — Projekt-API, JS-Param, Route, Workflow-Ring, Board+Badges, Plan-Filter** |
| **Dispatch Sprint 2a (7-8)** | **DONE — Pull-Adapter, Perplexity-Gate, workflow_core Integration, Settings-Toggles** |

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

## Session 2026-04-14 (Session 15) — Dispatch Sprint 2a Commits 7-8

### Was wurde erledigt
- **Commit 7 — Pull-Adapter + Perplexity-Gate:**
  - Pull-API Perplexity-Gate gehaertet: automatischer Review-Trigger bei fehlender Review
  - `scripts/dispatch_pull_adapter.py` (364 Z.) — Referenz-Implementierung mit One-Shot/Daemon
  - `scripts/dispatch_pull_adapter_claude.sh` (106 Z.) — Claude-Code Shell-Wrapper
- **Commit 8 — Integration + Settings-Toggles:**
  - `get_handoff_view()` liefert `active_assignments` Map pro Marker
  - Neues Signal `dispatch_status` + Hint-Typ `dispatch` im Workflow-Loop
  - Settings-Section im Dispatch-Panel (Perplexity-Modus, Tool-Toggles, Suggest-Button)
  - Badge-Counter fuer aktive Assignments im Cockpit-Tab
  - JS aufgeteilt: `dispatch-render.js`, `dispatch-settings.js` (Dateigroessen-Limit)

### Git Commits
```
3d88d24 Feature: ADR-002 Stufe 2a Commit 7 — Pull-Adapter + Perplexity-Gate
3d03c32 Feature: ADR-002 Stufe 2a Commit 8 — Integration workflow_core + Settings-Toggles
```

### Neue Dateien
| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `scripts/dispatch_pull_adapter.py` | 364 | Pull-Adapter Referenz-Implementierung |
| `scripts/dispatch_pull_adapter_claude.sh` | 106 | Claude-Code Shell-Wrapper |
| `static/js/dispatch-render.js` | 118 | Card/Review Render-Funktionen (extrahiert) |
| `static/js/dispatch-settings.js` | 109 | Settings-Panel Logik (extrahiert) |
| `static/css/dispatch-settings.css` | 117 | Settings-Styles + Badge |

---

## Naechste Session

### Primaer: Dispatch Sprint 2a Commit 9 (Doku + Push)
- `services/CLAUDE.md` erweitern: Dispatch-Schicht dokumentieren
- `sprints/master-plan-summary.md` aktualisieren: Stufe 2a als DONE
- Service neustarten + Live-Test der Pull-API + Settings-Toggles
- Push auf Gitea

### Sekundaer: Unified Cockpit Phase 7 (DEFERRED)
- Projekt-Detail bereinigen: Workflow-Tab → Zusammenfassung + Cockpit-Link
- Dispatch-Tab entfernen oder durch Link zum Cockpit ersetzen

### Tertiaer (wenn Zeit)
- [ ] Policy-Suggestions bewerten: 4 pending unter /policies
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung
- [ ] dispatch.js IIFE zu Module-Pattern refactoren (aktuell 425 Z., Panel-Code eng gekoppelt)
