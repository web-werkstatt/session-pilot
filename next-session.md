# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-14 (Session 14: Unified Cockpit Phase 6)
> **Status:** Plan-Filter-Dropdown + Sprint-Sections Collapse. Unified Cockpit Phase 1-6 done.
> **Naechste Aufgabe:** Dispatch Sprint 2a Commits 7-9 oder Unified Cockpit Phase 7 (Projekt-Detail bereinigen)

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
- [ ] **ADR-002 Stufe 2a Commits 7-9:** Pull-Adapter, Integration, Doku (offen)
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

## Session 2026-04-14 (Session 14) — Unified Cockpit Phase 6

### Was wurde erledigt
- **Sprint-Sections demoted** (Commit 6): Starten kollapsiert, Toggle-Button (Chevron -90° wenn collapsed)
- **Plan-Filter-Dropdown** im Header: "Alle Plaene (15)" + 6 aktive Plaene mit Marker-Counts
- **Client-side Filtering:** Board + Progress reagieren sofort auf Filter, kein Seiten-Reload
- **Auto-Expand:** Bei aktivem Filter werden Plan-Sections geladen und Sections expanded
- **Partial extrahiert:** `_cockpit_sprint_sections.html` (Template: 300→292 Zeilen)
- **Abwaertskompatibilitaet:** `?plan_id=N` funktioniert unveraendert, Sections dort ebenfalls collapsed

### Git Commits
```
cad2c7d Feature: Unified Cockpit Phase 6 — Sprint-Sections demoten + Plan-Filter-Dropdown
044d583 Docs: Session 14 — Unified Cockpit Phase 6, Sprint-Status aktualisiert
```

### Neue Dateien
| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `templates/_cockpit_sprint_sections.html` | 13 | Sprint-Sections Partial |

---

## Naechste Session

### Primaer: Dispatch Sprint 2a Commits 7-9
- **Commit 7:** Pull-Adapter Scripts + Perplexity-Gate bei Pull
- **Commit 8:** Integration workflow_core + Marker-Binding + Settings-Toggles
- **Commit 9:** Doku + Push

### Sekundaer: Unified Cockpit Phase 7 (DEFERRED)
- Projekt-Detail bereinigen: Workflow-Tab → Zusammenfassung + Cockpit-Link
- Dispatch-Tab entfernen oder durch Link zum Cockpit ersetzen

### Tertiaer (wenn Zeit)
- [ ] Policy-Suggestions bewerten: 4 pending unter /policies
- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung
- [ ] Optional: Trend-Chart, Adaptive Kalibrierung
