# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-13 (Session 8: Metriken-Dashboard + UX-Ueberarbeitung)
> **Status:** Counter-Bugfixes, /metrics Seite live, Audits + LLM Commands UX komplett ueberarbeitet, Policies-Badge im Nav.
> **Naechste Aufgabe:** Policy-Suggestions im UI bewerten, optional weitere UX-Seiten verbessern

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
- [x] **CWO Phase 1 Ticket 1.8:** UI: Badge + Panel im Tool-Files-Modal
- [x] **CWO Phase 1b Ticket 1.9:** Perplexity-Prompt erstellen (`prompts/context_window_optimizer.md`)
- [x] **CWO Phase 1b Ticket 1.10:** Reviewer-Modul (Perplexity-Call + Dedup) (`reviewer.py`)
- [x] **CWO Phase 1b Ticket 1.11:** UI: Review-Button + Bewertungs-Anzeige + Guidance-Zeile
- [x] **Policy-Reviewer Live-Test:** POST /api/policies/review gegen Perplexity getestet + 2 Dedup-Bugs gefixt
- [x] **Finding-Decisions:** Approve/Dismiss/Ignore pro Finding (Setup-Reviewer + CWO), DB + Service + REST + UI
- [x] **Rausch-Reduktion (Issue #23):** Dismiss-Filter + Confidence-Filter + Reject-Dedup in allen 3 Reviewern
- [x] **Metriken-Persistierung:** Counter-Spalten in project_reviews + cwo_analyses (generated/shown/filtered)
- [x] **Metriken-Dashboard:** /metrics Seite mit KPI-Karten, Charts, Noisiest-Findings-Tabelle (refs #23)
- [x] **Counter-Bugfixes:** load-Funktionen + Orchestrator-Result-Dicts um Counter-Spalten ergaenzt
- [x] **Policies-Badge:** Pending-Count als oranges Badge im Nav-Link, pollt alle 15s
- [x] **Audits UX:** Spec-Cards, Dropdown statt Freitext, Run-Historie, Guidance-Hints
- [x] **LLM Commands UX:** Command-Cards mit Icons, Purpose-Block, bessere Run-Tabelle
- [x] **CSS-Block-Fix:** policies.html extra_css → head_extra (CSS wurde nicht geladen)
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
| **CWO Phase 1a (Analyse)** | **DONE — 8 Checks, Orchestrator, REST-API, UI (Badge+Panel)** |
| **CWO Phase 1b (Review)** | **DONE — Perplexity-Prompt, Reviewer-Modul, Review-UI + Guidance** |
| **Finding-Decisions** | **DONE — Approve/Dismiss/Ignore pro Finding (Setup-Reviewer + CWO)** |
| **Rausch-Reduktion** | **DONE — Dismiss-Filter, Confidence-Filter, Reject-Dedup, Metriken-Counter** |
| **Metriken-Dashboard** | **DONE — /metrics mit KPI-Karten, Charts, Noisiest-Findings, Stats-Boxen** |
| **UX-Ueberarbeitung** | **DONE — Audits + LLM Commands: Kontext, Cards, Guidance, Historie** |
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

## Session 2026-04-13 (Session 8) — Metriken-Dashboard + UX-Ueberarbeitung

### Was wurde erledigt
- **Counter-Bugfixes:** `load_review()`/`load_analysis()` in Setup- und CWO-Storage fehlten Counter-Spalten im SELECT. `generated_count`/`shown_count` auch im Orchestrator-Result-Dict ergaenzt.
- **Reviews getriggert + verifiziert:** Setup (2 Projekte), CWO und Policy — alle Counter werden korrekt persistiert und via GET zurueckgegeben.
- **Metriken-Dashboard (`/metrics`):**
  - Service: `services/review_metrics_service.py` — aggregiert Counter aus project_reviews + cwo_analyses + finding_decisions + policy_review_suggestions
  - Route: `routes/review_metrics_routes.py` — GET `/metrics` + GET `/api/review-metrics`
  - UI: KPI-Karten (Signal-Ratio, Noise-Rate, Dismiss-Filter, Decision Dismiss/Approve, Policy Reject), Stacked-Bar-Chart (Setup per Projekt), Doughnut-Chart (Entscheidungen), Noisiest-Findings-Tabelle, Policy- und CWO-Stats-Boxen
- **Policies-Badge:** Oranges Badge im Sidebar-Nav-Link zeigt Anzahl pending Suggestions, pollt alle 15s zusammen mit Notifications
- **CSS-Block-Fix:** `policies.html` nutzte `extra_css`-Block der in `base.html` nicht existiert — korrigiert auf `head_extra`
- **Audits UX komplett ueberarbeitet:**
  - Erklaerungstext, Spec-Cards mit letztem Run-Status, Dropdown statt Freitext, Dateien eine-pro-Zeile statt JSON, Run-Historie-Tabelle, Guidance-Hints
  - Neue API-Endpoints: `GET /api/audits/specs`, `GET /api/audits/recent`
- **LLM Commands UX komplett ueberarbeitet:**
  - Command-Cards mit Icons, Titel, Purpose und Parameter-Info, Purpose-Block mit Seitenleiste, bessere Run-Tabelle

### Git Commits
```
8f87a65 Feature: Review-Metriken-Dashboard + Counter-Bugfixes (refs #23)
d9a5d13 Fix: policies.html CSS-Block von extra_css auf head_extra korrigiert
b6441a1 Feature: Pending-Badge im Policies-Nav-Link
bd4c283 Feature: Audits-Seite komplett ueberarbeitet — intelligentere UX/UI
c08b004 Feature: LLM Commands Seite ueberarbeitet — bessere UX/UI
```

### Geaenderte/neue Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/review_metrics_service.py` | Neu: Aggregiert Counter-Daten aus allen Reviewern |
| `routes/review_metrics_routes.py` | Neu: GET /metrics + GET /api/review-metrics |
| `templates/metrics.html` | Neu: KPI-Karten, Charts, Tabellen |
| `static/js/metrics.js` | Neu: Chart.js-Integration, KPI-Rendering |
| `static/css/metrics.css` | Neu: Metrics-Dashboard Styles |
| `services/tool_setup_review/storage.py` | Fix: Counter-Spalten im SELECT ergaenzt |
| `services/tool_setup_review/orchestrator.py` | Fix: generated_count/shown_count im Result |
| `services/context_window_optimizer/storage.py` | Fix: Counter-Spalten in allen 3 load-Funktionen |
| `services/context_window_optimizer/reviewer.py` | Fix: generated_count/shown_count im Result |
| `templates/base.html` | Metriken-Nav-Link + Policies-Badge |
| `static/js/notifications.js` | Policy-Pending-Badge Polling |
| `static/css/notifications.css` | Nav-Badge Style |
| `templates/policies.html` | Fix: extra_css → head_extra |
| `templates/audit.html` | Komplett ueberarbeitet: Spec-Cards, Dropdown, Historie |
| `routes/audit_routes.py` | Neu: GET /api/audits/specs, GET /api/audits/recent |
| `static/js/audit.js` | Komplett ueberarbeitet: Cards, Run-Historie, besseres Formular |
| `static/css/audit.css` + `audit-results.css` | Aufgeteilt (Limit 400 Zeilen) |
| `templates/llm_commands.html` | Komplett ueberarbeitet: Command-Cards, Guidance |
| `static/js/llm-commands.js` | Komplett ueberarbeitet: Cards, bessere Struktur |
| `static/css/llm-commands.css` | Komplett ueberarbeitet: Page-Layout, Cards |

---

## Naechste Session

### Aufgaben
- [ ] **Policy-Suggestions bewerten:** 4 pending Suggestions unter /policies (Badge zeigt es an)
- [ ] Optional: Weitere Seiten mit gleicher UX-Behandlung (Governance, Quality)
- [ ] Optional: Mehrstufiger Filter (Policy-Filter: nur Findings mit Handlung + Severity)
- [ ] Optional: Adaptive Kalibrierung (Schwellen aus Dismiss-/Accept-Daten je Reviewer)
- [ ] Optional: Dead Code V2 (Funktionen/Klassen mit Flask-Decorator-Erkennung)
- [ ] Optional: Trend-Chart mit historischen Metriken (erfordert Snapshot-Tabelle)
