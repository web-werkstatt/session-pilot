# Session-Archiv - Project Dashboard

> Archivierte Session-Eintraege aus next-session.md

---

## Session 2026-04-13 (Session 9) — Sprint-Planung Dispatch

### Was wurde erledigt
- **Sprint ADR-002 Stufe 2a freigegeben:** `sprints/sprint-adr002-stufe2a-dispatch.md`
  - Scope: Manuelles Dispatch (A) + Pull-API fuer CLIs (B), Perplexity-Review/Suggest, pro-Tool-Toggles
  - Push/Webhook (C) bewusst nach Stufe 2b verschoben (braucht HMAC+Timestamp+Nonce+Replay-Schutz)
  - State-Machine vereinfacht: kein `dispatched`-Zustand in 2a, nur proposed→approved→claimed→completed
  - Atomic Claim als Pflicht-Akzeptanzkriterium (Race-Condition-Schutz)
  - 9 Commits geplant (DB-Schema → Service → Perplexity → REST → Settings → UI → Pull-Adapter → Integration → Doku)
- **master-plan-summary.md** aktualisiert: Stufe 2a FREIGEGEBEN, 2b Backlog
- **plan-directory.md** aktualisiert: Stufe 2a eingetragen, Backlog auf 2b
- Kein Code geaendert, reine Planungs-Session

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `sprints/sprint-adr002-stufe2a-dispatch.md` | Neu: Sprint-Plan mit 9 Commits |
| `sprints/master-plan-summary.md` | Stufe 2a + 2b in Sprint-Tabelle |
| `sprints/plan-directory.md` | Stufe 2a in Control-Plane-Sektion + Backlog |

---

## Session 2026-04-13 (Session 8) — Metriken-Dashboard + UX-Ueberarbeitung

### Was wurde erledigt
- **Counter-Bugfixes:** `load_review()`/`load_analysis()` in Setup- und CWO-Storage fehlten Counter-Spalten im SELECT. `generated_count`/`shown_count` auch im Orchestrator-Result-Dict ergaenzt.
- **Reviews getriggert + verifiziert:** Setup (2 Projekte), CWO und Policy — alle Counter werden korrekt persistiert und via GET zurueckgegeben.
- **Metriken-Dashboard (`/metrics`):**
  - Service: `services/review_metrics_service.py` — aggregiert Counter aus project_reviews + cwo_analyses + finding_decisions + policy_review_suggestions
  - Route: `routes/review_metrics_routes.py` — GET `/metrics` + GET `/api/review-metrics`
  - UI: KPI-Karten, Stacked-Bar-Chart, Doughnut-Chart, Noisiest-Findings-Tabelle
- **Policies-Badge:** Oranges Badge im Sidebar-Nav-Link zeigt Anzahl pending Suggestions
- **CSS-Block-Fix:** `policies.html` extra_css → head_extra
- **Audits UX komplett ueberarbeitet:** Spec-Cards, Dropdown, Run-Historie, Guidance-Hints
- **LLM Commands UX komplett ueberarbeitet:** Command-Cards, Purpose-Block, bessere Run-Tabelle

### Git Commits
```
8f87a65 Feature: Review-Metriken-Dashboard + Counter-Bugfixes (refs #23)
d9a5d13 Fix: policies.html CSS-Block von extra_css auf head_extra korrigiert
b6441a1 Feature: Pending-Badge im Policies-Nav-Link
bd4c283 Feature: Audits-Seite komplett ueberarbeitet — intelligentere UX/UI
c08b004 Feature: LLM Commands Seite ueberarbeitet — bessere UX/UI
```

---

## Session 2026-04-13 (Session 7) — Rausch-Reduktion: Dismiss-Filter + Confidence-Filter + Metriken

### Was wurde erledigt
- **Analyse:** Perplexity-Rauschen ist kein Modell-Bug, sondern Systemluecke — fehlende Filter zwischen Modell-Ausgabe und Persistierung
- **Gitea Issue #23 angelegt:** Rausch-Reduktion: Dismiss-Filter + Confidence-Filter fuer Reviewer
- **Dismiss-Filter (Schritt 1):**
  - `get_dismissed_fingerprints()` + `is_finding_dismissed()` in `finding_decision_service.py`
  - Setup-Reviewer: Dismisste Fingerprints mit unveraenderter context_signature werden vor Persistierung gefiltert
  - Policy-Reviewer: Rejected Suggestions mit gleichem Payload werden via `_get_rejected_suggestion_keys()` nicht erneut persistiert
  - CWO-Reviewer: Migration-Assessments mit Confidence < 50 gefiltert, `low_confidence_warning` bei overall < 30
- **Confidence-Filter (Schritt 2):**
  - `parse_confidence()` als defensiver Parser (int/float/str/None) in `finding_decision_service.py`
  - Schwelle >= 50 fuer Setup-Findings und Policy-Suggestions
  - Schwelle >= 50 fuer CWO-Migration-Assessments, >= 30 fuer CWO-Overall mit Warning-Flag
  - Thresholds sind vorlaeufig und kalibrierbar — Confidence ist ein Zusatzsignal, kein alleiniges Gate
- **Metriken-Persistierung:**
  - Counter-Spalten (generated_count, shown_count, filtered_dismissed_count, filtered_low_confidence_count) in `project_reviews` + `cwo_analyses`
  - `save_review()` in Setup + CWO berechnet generated_count automatisch und schreibt alle Counter mit

### Git Commits
```
f040047 Feature: Rausch-Reduktion — Dismiss-Filter + Confidence-Filter fuer Reviewer (fixes #23)
60163d6 Feature: Review-Metriken in bestehende Tabellen persistieren (refs #23)
```

---

## Session 2026-04-13 (Session 6) — Policy-Reviewer Live-Test + Finding-Decisions

### Was wurde erledigt
- **CWO Sprint-Plan aktualisiert:** Phase 1a+1b als DONE markiert in `sprints/sprint-cwo-context-window-optimizer.md`
- **Policy-Reviewer Live-Test:** POST `/api/policies/review` erfolgreich gegen Perplexity Sonar getestet
  - Seed-Defaults geladen (6 Rollen, 5 Tool-Profile)
  - Perplexity liefert sinnvolle Policy-Vorschlaege (3 aktive Suggestions pending)
  - Approval/Reject-Flow funktioniert end-to-end
- **Bug gefixt: Multi-Suggestion-Dedup** — `record_suggestion()` in `policy_service.py` deduplizierte nur nach `context_hash`, sodass pro Review-Call nur die erste Suggestion persistiert wurde. Jetzt: `context_hash + suggestion_type + payload`
- **Bug gefixt: Review-Level-Dedup fehlte** — Policy-Reviewer rief Perplexity bei jedem Klick erneut auf. Neu: `_find_cached_review()` in `policy_review_service.py` prueft pending Suggestions vor dem API-Call, `force`-Parameter uebergeht den Cache. Route in `policy_routes.py` angepasst.
- **Feature: Dismiss pro Finding** — Entscheidungs-Flow fuer alle Reviewer-Findings (Setup-Reviewer + CWO):
  - DB: `finding_decisions` Tabelle mit SHA256-Fingerprint, Status, Dismiss-Reason, Context-Signature
  - Service: `finding_decision_service.py` — Fingerprint-Berechnung, Enrichment, Reaktivierung bei Kontext-Aenderung
  - REST: POST `/api/project/<name>/findings/decide`, GET `decisions`, POST `reset`
  - UI: Akzeptieren/Dismiss/Einmal-ignorieren-Buttons pro Finding, Dismiss-Dialog mit 4 Reason-Presets (bewusst so, Runtime-Datei, kein Projektziel, dupliziert) + Freitext
  - Dismissed Findings verschwinden, Counter zeigt "X dismissed", Reaktivierung bei Kontext-Aenderung
  - Browser-verifiziert im Tool-Files-Modal

### Git Commits
```
2d0a7c9 Fix: Policy-Reviewer Dedup — Multi-Suggestion-Persistierung + Review-Level-Cache
567e88b Feature: Dismiss pro Finding — Entscheidungs-Flow fuer Review-Findings
```

---

## Session 2026-04-13 (Nacht 5) — CWO Phase 1b Ticket 1.11 + Guidance

### Was wurde erledigt
- **CWO Ticket 1.11:** Review-Button + Bewertungs-Anzeige
  - `static/js/context-window-optimizer-review.js` (176 Zeilen): Review-UI als eigenes Modul (`window.cwoReview`)
  - Review-Link (lila, `#c084fc`) in CWO-Status-Zeile: "Review anfordern" / "Erneut reviewen"
  - Perplexity-Review Panel: Confidence-Badge (gruen/gelb/rot), Safe/Unsafe-Indikator, Summary-Text
  - Token-Assessment Vorher/Nachher: `10.0K → 8.5K −15%` mit Farb-Rating
  - Migration-Assessments (collapsible): safe=gruen, unsafe=rot, needs_review=gelb mit Begruendung
  - Dedup-Feedback: "Review aktuell — keine Aenderung seit letztem Review"
  - Loading-State + Error-Handling
- **Guidance-Zeile:** Kontextabhaengiger Naechster-Schritt-Hinweis im CWO-Panel
  - 6 Zustaende: Start (blau), Fehler (rot), Veraltet (gelb), Empfehlung (lila), Achtung (rot), Bereit (gruen)
  - `buildGuidance()` + `resolveGuidanceHint()` in `context-window-optimizer.js`
  - Browser-verifiziert: "Bereit" bei project_dashboard, "Start" bei proj_webideas24
- **Architektur:** Review-Logik in eigene Datei ausgelagert (Hauptdatei 428 Z., Review 176 Z.)

### Git Commits
```
e16d24f Feature: CWO Phase 1b Ticket 1.11 - UI Review-Button + Bewertungs-Anzeige + Guidance
```

---

## Session 2026-04-13 (Nacht 4) — CWO Phase 1b Tickets 1.9+1.10

### Was wurde erledigt
- **CWO Ticket 1.9:** Perplexity-Prompt (`prompts/context_window_optimizer.md`, 160 Zeilen)
  - Bewertet Migration-Map auf Sicherheit: safe/unsafe/needs_review pro Sektion
  - Erkennt Verbots-Charakter (muss im Root bleiben), Load-Mode-Angemessenheit, fehlende Zugangswege
  - JSON-Output: migration_assessments, token_assessment, overall_confidence, findings_review
  - Pattern identisch mit setup_reviewer/policy_reviewer: nur JSON, keine Citations
- **CWO Ticket 1.10:** Reviewer-Modul + REST-Endpoints
  - `services/context_window_optimizer/reviewer.py` (170 Zeilen): review_project() mit query_fn-Injection, context_hash-Dedup, Code-Fence-toleranter JSON-Parser, Error-Persistierung
  - `services/context_window_optimizer/storage.py` erweitert: save_review() + load_review()
  - `routes/context_window_optimizer_routes.py` erweitert: POST/GET /api/project/<name>/cwo/review
- **Alle Tests bestanden:** Import, Prompt-Laden, JSON-Parser, Build-Input, Hash-Dedup, DB-Roundtrip, REST-Endpoints

### Git Commits
```
89aedfd Feature: CWO Phase 1b Tickets 1.9+1.10 - Perplexity-Prompt + Reviewer-Modul
```

---

## Session 2026-04-13 (Nacht 3) — CWO Phase 1 Ticket 1.8

### Was wurde erledigt
- **CWO Ticket 1.8:** UI-Analyse-Anzeige im Tool-Files-Modal
  - `static/js/context-window-optimizer.js` (270 Zeilen): Token-Budget-Badge am Topbar-Button, CWO-Panel mit Status-Zeile, Findings, Migration-Map-Tabelle, File-Inventory-Tabelle
  - `static/js/tool-profile-adapter.js` erweitert: `window.cwo.mountPanel()` Aufruf
- **Sprint-Plan aktualisiert:** Navigation-Entscheidung fuer Phase 2 — CWO-Seite unter STEUERN
- **Phase 1a komplett:** Alle 8 Tickets (1.1-1.8) implementiert und im Browser verifiziert

### Git Commits
```
9c29536 Feature: CWO Phase 1 Ticket 1.8 - UI Analyse-Anzeige im Tool-Files-Modal
```

---

## Session 2026-04-13 (Nacht 2) — CWO Phase 1 Tickets 1.6+1.7

### Was wurde erledigt
- **CWO Ticket 1.6:** Orchestrator (`orchestrator.py`) — `analyze_project()` verbindet Context Collector → Checks → Findings-Aggregation → token_budget_rating → DB-Persistierung. `analyze_all_projects()` fuer Batch. context_hash-Dedup (force-Flag). Storage (`storage.py`) mit Upsert auf `cwo_analyses`, `load_analysis()`, `load_all_analyses()`.
- **CWO Ticket 1.7:** REST-Endpoints (`routes/context_window_optimizer_routes.py`) — 4 Endpoints: POST/GET `/api/project/<name>/cwo/analyze`, POST `/api/cwo/analyze-all`, GET `/api/cwo/overview` mit `?rating=` Filter.
- **DB-Migration:** `error`-Spalte in `cwo_analyses` ergaenzt (ALTER TABLE in `db_cwo_schema.py`).
- **Bugfix:** `scan_projects()` gibt Dict (nicht Liste) zurueck — Orchestrator angepasst.

### Statistik (165 Projekte)
| Rating | Anzahl |
|--------|--------|
| ok | 146 |
| info | 19 |
| warning | 0 |
| error | 0 |

---

## Session 2026-04-13 (Nacht) — CWO Phase 1 Tickets 1.3-1.5

### Was wurde erledigt
- **CWO Ticket 1.3:** Check-Framework vervollstaendigt — `run_all_checks()` mit Auto-Discovery via `pkgutil`, Severity-Sortierung (error>warning>info), Fehlerresilienz (Exception → Error-Finding). Token-Budget-Check (Check 8) als erster konkreter Check.
- **CWO Ticket 1.4:** Dateigroessen-Checks 1-4 — `oversize_claude_md.py`, `oversize_tool_files.py`, `focus_file_size.py`, `next_session_growth.py`.
- **CWO Ticket 1.5:** Struktur-Checks 5-7 — `global_rule_duplicates.py` (Jaccard), `missing_subdir_claude.py`, `extractable_sections.py`.
- **Smoke-Test:** 106 Projekte, 202 Findings, alle Severity-Stufen verifiziert.

---

## Session 2026-04-13 (Abend) — CWO Phase 1 Ticket 1.1 + 1.2

### Was wurde erledigt
- **CWO Ticket 1.1:** DB-Schema (`cwo_analyses` + `cwo_action_log`), Constants, Check-Framework, Action-Framework, Facade `__init__.py`
- **CWO Ticket 1.2:** Context Collector (`context_collector.py`) — sammelt Tool-Files, next-session, Fokusauftrag-Dateien, Unterverz.-CLAUDE.md, globale Rules, Sektionsanalyse, Token-Schaetzung. Smoke-Test: 8.798 Tokens fuer project_dashboard.
- **pyrightconfig.json:** Pyright-Config mit `extraPaths`
- **DB live:** `ensure_cwo_schema()` in `db_service.py` registriert

---

## Session 2026-04-13 — Context-Window-Optimierung + CWO Sprint-Plan

### Was wurde erledigt
- **CLAUDE.md modularisiert:** 271 → 102 Zeilen (-63%). Architektur-Listen in Unterverzeichnis-CLAUDE.md ausgelagert, Dateigroessen-Duplikat entfernt, Patterns auf Verbots-Charakter reduziert, Scheduled Tasks/Backup/META in Skill ausgelagert.
- **master-plan-summary.md erstellt:** 48-Zeilen-Summary statt 1.820-Zeilen-Vollversion. Fokusauftrag-Regel geaendert.
- **next-session.md rotiert:** 271 → 95 Zeilen. Session-Historie 2026-04-07 bis 2026-04-11 ins Archiv.
- **5 Unterverzeichnis-CLAUDE.md erstellt:** `routes/`, `services/`, `static/`, `templates/`, `sprints/` — nativer Claude-Code Lazy-Loading-Mechanismus.
- **Skill /project-ops erstellt:** Betriebsbefehle, systemd, Scheduled Tasks, Backup on-demand.
- **Sprint-Plan CWO erstellt:** `sprints/sprint-cwo-context-window-optimizer.md` — 18 Tickets in 3 Phasen.
- **Einsparung:** Startup-Kontext von ~33.600 auf ~5.600 Tokens (-83%).

### CWO Phase 1 Ticket 1.1 + 1.2 implementiert
- `services/db_cwo_schema.py`: DB-Schema (cwo_analyses + cwo_action_log), Lazy-Ensure
- `services/context_window_optimizer/constants.py`: Schwellwerte, Token-Faktoren, Load-Modes, Actions
- `services/context_window_optimizer/__init__.py`: Re-Export-Facade
- `services/context_window_optimizer/checks/__init__.py`: Check-Framework (BaseCWOCheck, CWOFinding, MigrationEntry, Registry)
- `services/context_window_optimizer/actions/__init__.py`: Action-Framework (BaseAction)
- `services/context_window_optimizer/context_collector.py`: Sammelt Analyse-Kontext pro Projekt
- `services/db_service.py`: ensure_cwo_schema() registriert
- `pyrightconfig.json`: Pyright-Config mit extraPaths statt py.typed
- Smoke-Test: DB-Tabellen erstellt, Collector gegen project_dashboard validiert (8.798 Tokens)

### Git Commits
```
bea0131 Feature: Context-Window-Optimierung + CWO Sprint-Plan
```

---

## Session 2026-04-11 (Nachtrag Dispatch/Execute) — ADR-002 erweitert

### Was wurde erledigt
- ADR-002 Nachtrag: Dispatch/Execute als vierte Schicht, work_assignments-Entitaet, Autonomie-Stufen L0-L3. Commit `04d0f7c`.
- Status-Uebersicht ADR-002 Stufe 1 als Markdown (`8796fdd`).
- Status-HTML-Variante lokal (1024 Zeilen, nicht committet).

---

## Session 2026-04-10 (Abend) - ADR-001 Prio 1+3+4: DB-First Marker Core

### Was wurde erledigt
- `services/db_marker_schema.py` (neu): `markers`-Tabelle + `executor_tool` in `marker_workflow_states`
- `services/marker_importer.py` (neu): Idempotenter Import aus handoff.md (9 Marker importiert, Re-Run: 0 neue)
- `services/workflow_core_service.py` (neu): `get_markers()`, `get_marker()`, `update_marker_field()`, `update_marker_state()`, `get_handoff_view()`
- `services/db_service.py`: `ensure_marker_schema()` Delegate
- `services/copilot_marker_service.py`: Komplett auf DB-first umgestellt
- `services/workflow_loop_service.py`: Marker via `core_get_markers()`
- 598 Tests gruen, 0 Failures

### Architektur-Muster
- **DB-first mit Fallback:** `_resolve_marker()` / `_resolve_markers()` lesen aus DB, fallen auf handoff.md zurueck
- **Dual-Write:** Schreib-Operationen aktualisieren handoff.md (Mirror) UND DB
- **Auto-Import:** Core importiert automatisch aus handoff.md wenn DB leer

## Historie (2026-04-07 bis 2026-04-10)

- **2026-04-10 (Nacht):** ADR-001 Prio 2 implementiert: Block-Marker-Parser + Write-Guard. Code-Review + Refactor. 37 neue Tests, 635 gesamt. Commit `44f52f6`.
- **2026-04-10:** ADR-001 Prio 1+3+4 implementiert. 598 Tests gruen.
- **2026-04-10:** ADR-001 erstellt + Sprint-Nachtraege. Perplexity-Copilot als Read-Only-Validierungsschicht.
- **2026-04-10:** Workflow-Cards entmischt, Sprachregel in AGENTS.md.
- **2026-04-09:** Workflow-Tab operativ ausgebaut, Session-Detail Back-Navigation, Quality/Governance UX.
- **2026-04-08:** Sprint CP abgeschlossen, Workflow-Loop v1, 3 Haupttabs.
- **2026-04-07:** Sprint SB DONE, Closeout (M1-M14), Tag `v1.3-final`

---

## Session 2026-04-11 - ADR-001 Prio 5 DONE

### Was wurde erledigt
- **ADR-001 Prio 5:** `write_handoff_mirror(project_name)` in `services/workflow_core_service.py`
- 10 neue Tests, 645/645 gruen. Issue #21, Commit `24a19b3`

---

## Session 2026-04-11 (Nachmittag) - Workflow-v2 UX Follow-up + Asset-Split + ADR-001 Prio 6 DONE

### Was wurde erledigt
- Asset-Split: workflow-loop CSS (4 Dateien) und JS (6 Module). Template entlastet.
- ADR-001 Prio 6: `tool_profile_adapter_service.py`, REST-Endpoints, UI-Modal. 659/659 Tests.
- 4 Commits nach Gitea gepusht.

---

## Session 2026-04-11 (Abend) — ADR-002 + Sprint-Plan Stufe 1 (Doku-Rahmen)

### Was wurde erledigt
- ADR-002 angelegt: AI-Control-Plane fuer Multi-LLM-Systeme
- Sprint-Plan Stufe 1 angelegt (10 Commits)
- Nachtraege an ADR-001, Master-Plan

---

## Session 2026-04-11 (Spaet-Abend) — ADR-002 Stufe 1a + 1b vollstaendig

### Alle Commits
| # | Commit | Hash | Inhalt |
|---|---|---|---|
| 1 | Doku-Rahmen | `04fb9d2` | ADR-002 + Sprint-Plan |
| 2 | Setup-Reviewer Core | `92c8f49` | services/tool_setup_review/, 22 Tests |
| 3 | Setup-Reviewer REST + UI | `887031c` | POST/GET, UI im Modal |
| 3b | UX Fix | `a09f415` | Badge + Banner |
| — | Prompt-Schaerfung | `e59f978` | setup_reviewer.md |
| 3c | UX Fix Refresh-Link | `1b66445` | Refresh-Link dauerhaft sichtbar |
| 4 | Policy-Schema | `7c42773` | 4 DB-Tabellen, 14 Tests |
| 5 | Seed-Defaults | `c16f1be` | 6 Rollen + 5 Tool-Profile |
| 6 | Policy-Reviewer | `bdd31d5` | Perplexity-Reviewer, 13 Tests |
| 7 | Policy-REST | `dcef99a` | 8 Endpoints |
| 8 | Policy-UI | `733289b` | /policies Seite |
| 9 | workflow_core | `9923d82` | get_handoff_view + policies |

### Tests
746/746 gruen (+65 neue ueber den Tag)

### Parkzettel fuer Stufe 2+
- context_hash ohne Prompt-Version (force=True als Workaround)
- policy_stats aggregiert account statt tool_id (Stufe 3)
- Marker-Schema ohne role_id/assigned_tool (Stufe 3)
- Tool-Profile-Strengths/Weaknesses leer (Stufe 3)
- Policy-Reviewer ohne Session-Evidence (Stufe 3)

---

## Session 2026-04-09 (Nachmittag) - Dead Code Detection + Workflow-Integration

### Was wurde erledigt
- Workflow-v2 Sprint 1 Code: Persistentes Datenmodell (`marker_workflow_states`, `workflow_transitions`), Transition-Regeln, REST-API, Auto-Sync
- Dead-Code-Erkennung: 3 neue Quality-Checks (`dead_code.py`, `dead_dependencies.py`, `dead_frontend.py`) mit Confidence/Evidence, AST-basiert
- Workflow-Integration: Dead-Code-Summary fliesst von Quality-Report ueber Governance-Gate in Workflow-Signale
- Sprint-Plan `sprint-workflow-v2-full-system.md` um GUI/UX-Specs fuer Sprint 2-5 ergaenzt
- next-session.md auf Code/GUI-Split umgestellt (Claude Code vs. Codex)

### Neue Dateien
- `services/db_workflow_state_schema.py` — DB-Schema fuer Workflow-States
- `services/workflow_state_service.py` — Transition-Logik (7 Statuses, ALLOWED_TRANSITIONS)
- `routes/workflow_routes.py` — 5 REST-Endpoints
- `auto_coder/checks/_dead_code_utils.py` — Shared Helpers
- `auto_coder/checks/dead_code.py` — Ungenutzte Imports + verwaiste .py-Dateien
- `auto_coder/checks/dead_dependencies.py` — Ungenutzte Python/npm Deps
- `auto_coder/checks/dead_frontend.py` — Verwaiste JS/CSS + CSS-Klassen

### Geaenderte Dateien
- `services/db_service.py` — `ensure_workflow_state_schema()` hinzugefuegt
- `services/workflow_loop_service.py` — Auto-Sync, marker_groups, Dead-Code-Signal
- `services/governance_service.py` — `dead_code_summary` in Quality-Summary
- `routes/__init__.py` — `workflow_bp` registriert
- `auto_coder/scanner.py` — 3 neue Checks registriert
- `auto_coder/report.py` — Issue: +confidence, +evidence
- `auto_coder/config.py` — Score-Weights fuer dead_code, dead_deps, dead_frontend
- `CLAUDE.md` — Workflow-State-System + Dead-Code-Erkennung dokumentiert

### Ergebnisse Dead-Code-Scan (project_dashboard)
- 38 ungenutzte Imports, 9 verwaiste .py-Dateien, 2 ungenutzte Dependencies, 2 verwaiste Assets, 28 CSS-Klassen-Kandidaten
- 42 davon mit confidence=high

---

---

## Session 2026-04-07 - Sprint QT Plan-Reality-Sync

### Ziel
Master-Plan, Gitea-Issues und Repo-Stand in einen konsistenten Zustand bringen, bevor weitere Feature-Sprints gestartet werden.

### Was wurde erledigt

**Arbeitspaket A - Master-Plan Reality-Check:**
- Stichprobenhafte Pruefung von Sprint 9/10/11 Artefakten im Code
- Sprint 9 (Fehler-Kategorien + AI-Scope-Filter) als DONE bestaetigt:
  - `services/ai_scope_service.py` (86 Zeilen)
  - `routes/session_filter_routes.py` (187 Zeilen, 4 Endpoints)
  - `scripts/backfill_ai_flags.py`
  - AI-Flag-Extraktion in allen Importern unter `services/importers/`
- Sprint 10 (Per-File Heatmap) als DONE bestaetigt:
  - `services/file_touch_service.py` (386 Zeilen)
  - `routes/analytics_routes.py` (2 Endpoints)
  - `static/js/file-heatmap.js`, in `project_detail.html` integriert
- Sprint 11 (Modell-Qualitaetsvergleich) als DONE bestaetigt:
  - `services/model_recommendation.py` (437 Zeilen)
  - `routes/model_comparison_routes.py` (Page + 4 API-Endpoints)
  - `templates/model_comparison.html`
- Master-Plan-Block "AI Governance Analytics (historisch Sprints 9-14)" mit Status-Tabelle korrigiert
- Historische-Referenz-Tabelle angepasst (Sprint 9/10/11 -> DONE)
- Current-State-Block um neue Saeule erweitert

**Arbeitspaket B - Gitea-Issue-Triage:**
- Alle 5 offenen Issues #13, #14, #15, #16, #18 gepruefte und mit Commit-Referenz geschlossen:
  - #13 (Audit-Integration) - `routes/audit_routes.py` + `templates/audit.html` vorhanden
  - #14 (Sprint P3 Prompt-Chain) - Commit `afd218c` auf main
  - #15 (P2-Branch-Isolierung) - Commits `8f8d08c` + `6faf2c8` (PR #17)
  - #16 (Sprint P2 marker board) - Commit `8f8d08c`
  - #18 (Copilot CSS + handoff regeneration) - Commit `5bcb2af`

**Arbeitspaket C - Marker-Context:**
- **DONE:** `marker-context.md` bleibt unveraendert (User-Entscheidung: Testmarker `test-cockpit-2026-04-05` behalten)

**Arbeitspaket D - next-session.md Follow-ups:**
- D1/D2 (Session-Kontext-Links im Planning-Panel schaerfen): **verschoben**
- D3/D4 (Cockpit-Activity-Card anpassen): **obsolet**
- D5/D6 (Archivierung): **DONE**

**Arbeitspaket E - Dokumentation:**
- `sprints/audit-2026-04-07.md` erstellt (Prueffbericht)
- `sprints/sprint-qt-plan-reality-sync.md` erstellt
- `sprints/master-plan-2026-04-01.md` aktualisiert (3 Stellen)
- `next-session.md` + `next-session-archiv.md` aktualisiert

### Gitea-Issues
- #13, #14, #15, #16, #18 alle closed mit Commit-Referenz

**Commits:** `e39d97c`, `25009fb`, `26797fa`, `85adbcf`

---

## Session 2026-04-06 - QR-Validierung + Session-Tab Reduktion

### Was wurde erledigt
- Sprint QR vollstaendig im Browser gegen echte Daten validiert:
  - Planning-Tab: Hierarchie Plan -> Sprint -> Spec -> Task rendert korrekt (8 Plans, 3 Sprints, 15 Specs)
  - Detailpanel reagiert auf Klick (Sprint, Spec, Task) und zeigt Status/Goal/Next Step/Sessions
  - Session-Zeilen im Planning-Panel navigieren korrekt zur Session-Detailseite
  - Zurueck-Button auf Session-Detail fuehrt zurueck zur Projektseite
  - Widgets-Tab laedt ohne Console-Fehler (`loadWidgets` Fix bestaetigt)
  - Account-Badges (claude/codex/kilo) farblich korrekt unterscheidbar
- Session-Tab zu Activity-Summary reduziert:
  - Stats-Kacheln: Sessions, Total Time, Tokens, Tools
  - Account-Breakdown-Badges mit Anzahl
  - Kompakte Recent-Sessions-Liste (max 10) statt Volltabelle
  - "View all sessions" Link zur globalen Activity-Seite
- Planning-Detailpanel Sessions erweitert:
  - Account-Badges mit tool-spezifischen Farben (claude=blau, codex=orange, kilo=lila, gemini=gruen, opencode=rot)
  - Token-Anzeige (input/output formatiert)
  - Modellnamen-Kurzform (Opus, Sonnet statt claude-opus-4-6)
  - "View all in Activity" Link
- Backend: SQL-Queries fuer Sessions um account, total_input_tokens, total_output_tokens erweitert; Limit von 6 auf 10 erhoeht

### Git Commits
```
1a1bd3e Feature: reduce Session tab to compact Activity summary, enrich Planning sessions
```

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/plan_structure_helpers.py` | SQL um account + tokens erweitert, Serializer ergaenzt |
| `services/plan_structure_service.py` | Recent-Sessions-Limit 6 -> 10 |
| `static/js/project-planning.js` | Session-Rendering mit Account-Badges, Tokens, Activity-Link |
| `static/css/project-planning.css` | Account-Badge-Farben, Activity-Link CSS |
| `static/js/project-detail.js` | Session-Tab -> kompakte Activity-Summary |
| `static/css/activity-summary.css` | Neues CSS fuer Activity-Summary (aus project-detail.css extrahiert) |
| `templates/project_detail.html` | Tab-Label "Session History" -> "Activity", CSS-Link |

---

## Session 2026-04-05 - Sprint QR Validierung + Diverse Hotfixes

## Update 2026-04-05
- Changed: Dashboard-Hotfix fuer den Widgets-Tab eingebaut; `loadWidgets` ist beim Initial-Render nicht mehr vorzeitig undefiniert, weil `widgets.js` jetzt vor `dashboard-core.js` geladen wird und `showTab()` den Aufruf zusaetzlich absichert.
- Files: `templates/index.html`, `static/js/dashboard-core.js`
- Verify: `node --check static/js/dashboard-core.js`, `node --check static/js/widgets.js`; Browser-Fehler `Uncaught ReferenceError: loadWidgets is not defined` sollte beim Tab `Overview` nicht mehr auftreten.
- Next: Im Browser hart neu laden und pruefen, dass `/?tab=widgets` direkt ohne Console-Fehler rendert.

## Update 2026-04-05
- Changed: Der Sidebar-Link `Projects` nutzt ausserhalb des Dashboards jetzt das gespeicherte aktive Projekt aus `localStorage`, sodass der Wechsel `Projekt -> Activity -> Projects` wieder in das zuletzt geoeffnete Projekt fuehrt statt zur nackten Projektliste.
- Files: `templates/base.html`, `static/js/base.js`
- Verify: `node --check static/js/base.js`; im Browser `project_dashboard -> Activity -> Projects` klicken und pruefen, dass `/project/project_dashboard` geoeffnet wird.
- Next: Weitere globale Navigationen auf dasselbe Projekt-Kontext-Verhalten pruefen, falls der gleiche Erwartungswert auch fuer Command Palette oder Breadcrumbs gelten soll.

## Update 2026-04-05
- Changed: Das sticky `Planning`-Detailpanel auf der Projektseite hat jetzt eine maximale Viewport-Hoehe und einen eigenen Vertikal-Scrollbereich, damit lange Task-Cards beim Herunterscrollen vollstaendig sichtbar bleiben.
- Files: `static/css/project-planning.css`
- Verify: Seite `/project/project_dashboard` im Tab `Planning` oeffnen, lange Task-/Detail-Card waehlen und pruefen, dass der komplette Inhalt im rechten Panel per internem Scroll sichtbar ist.
- Next: Falls das Problem eher die linke Kartenliste betrifft, den konkreten betroffenen Kartentyp und Scrollpfad im Browser nachziehen.

## Update 2026-04-05
- Changed: Projekt-Detail-Hotfix fuer `loadRiskRadarPanel`; `file-heatmap.js` wird jetzt vor `project-detail.js` geladen und der Init-Aufruf ist zusaetzlich gegen fehlende Definition abgesichert.
- Files: `templates/project_detail.html`, `static/js/project-detail.js`
- Verify: `node --check static/js/project-detail.js`; Browser-Fehler `Uncaught ReferenceError: loadRiskRadarPanel is not defined` auf `/project/<name>` sollte nicht mehr auftreten.
- Next: Weitere Projekt-Detail-Skripte auf implizite Abhaengigkeiten pruefen, falls noch weitere Globals ueber Script-Reihenfolge gekoppelt sind.

## Update 2026-04-05
- Changed: Session-Eintraege im `Planning`-Detailbereich haben jetzt neben der Auswahlflaeche eine echte `Open`-Aktion, damit verlinkte Sessions direkt auf `/sessions/<uuid>` geoeffnet werden koennen.
- Files: `static/js/project-planning.js`, `static/css/project-planning.css`
- Verify: Im Projekt-Tab `Planning` bei einer Session-Zeile auf `Open` klicken und pruefen, dass die Session-Detailseite geladen wird.
- Next: Optional spaeter die gesamte Session-Zeile direkt navigierbar machen, falls die separate Auswahl im rechten Panel nicht mehr benoetigt wird.

## Update 2026-04-05
- Changed: Session-Eintraege im `Planning`-Detailbereich navigieren jetzt direkt beim Klick auf die gesamte Zeile zur Session-Detailseite; der separate `Open`-Button wurde wieder entfernt.
- Files: `static/js/project-planning.js`, `static/css/project-planning.css`
- Verify: Im Projekt-Tab `Planning` auf eine Session-Zeile klicken und pruefen, dass direkt `/sessions/<uuid>` geladen wird.
- Next: Falls die Session-Auswahl im rechten Panel doch wieder benoetigt wird, ein separates Icon fuer Vorschau statt Vollklick einfuehren.

## Update 2026-04-05
- Changed: Die Session-Detailseite hat jetzt einen echten `Zurueck`-Button statt nur des statischen Links `Activity`; bei internem Verlauf geht er per Browser-History zur vorherigen Seite zurueck, sonst faellt er auf `/sessions` zurueck.
- Files: `templates/session_detail.html`, `static/js/session-detail.js`
- Verify: Session-Detail aus `Planning` oder `Activity` oeffnen und `Zurueck` pruefen; direkte URL-Oeffnung sollte auf `/sessions` fallen.
- Next: Optional gleiche History-Back-Logik auch fuer weitere Detailseiten wie Plan-Detail vereinheitlichen.

## Update 2026-04-05
- Changed: Account-Badges in der Session-Tabelle farblich geschaerft; `Codex` ist jetzt deutlich warm/orange statt nah am `Claude`-Blau und damit in `Activity` und Projekt-Sessionlisten schneller unterscheidbar.
- Files: `static/css/sessions-list.css`
- Verify: `Activity` oder Projekt-Tab `Session History` oeffnen und `claude` gegen `codex` visuell vergleichen.
- Next: Falls gewuenscht, die gleiche Farbsemantik auch in Session-Detail-Metabars und anderen toolbezogenen Badges vereinheitlichen.

## Update 2026-04-05
- Changed: Badge-Styling fuer AI-Accounts/Tools ist jetzt als persistente Settings-Konfiguration implementiert; `hermes`, `copilot`, `amazonq`, `opencode` und `kilo` sind als editierbare Defaults hinterlegt und koennen in `Settings -> General` ohne Codeaenderung angepasst oder erweitert werden.
- Files: `services/dashboard_settings_service.py`, `app.py`, `templates/base.html`, `templates/settings.html`, `static/js/base.js`, `static/js/settings.js`, `static/js/sessions2.js`, `static/js/project-detail.js`, `static/js/session-detail.js`, `static/css/settings.css`
- Verify: In `Settings -> General` einen Badge-Key wie `hermes` oder `codex` aendern, speichern und danach `Activity`, Projekt-Sessionliste und Session-Detail neu laden.
- Next: Falls gewuenscht, dieselbe Settings-Mechanik spaeter auch fuer Provider- und Modell-Badges ausrollen.

## Update 2026-04-05
- Changed: Die wachsende Datei `services/session_import_multi.py` wurde in eine modulare Importer-Struktur unter `services/importers/` zerlegt; Codex, Gemini, OpenCode und Kilo haben jetzt jeweils eigene Module, waehrend `session_import.py` nur noch den Sync orchestriert und `session_import_multi.py` als Kompatibilitaets-Wrapper bestehen bleibt. Zusaetzlich wurde die Projektnamen-Extraktion fuer `opencode:`- und `kilo:`-Hashes vervollstaendigt.
- Files: `services/session_import.py`, `services/session_import_multi.py`, `services/importers/__init__.py`, `services/importers/common.py`, `services/importers/codex_importer.py`, `services/importers/gemini_importer.py`, `services/importers/opencode_importer.py`, `services/importers/kilo_importer.py`, `tests/test_session_import.py`, `CLAUDE.md`, `CONTRIBUTING.md`
- Verify: `python3 -m py_compile services/session_import.py services/session_import_multi.py services/importers/*.py` und `pytest tests/test_session_import.py -q`
- Next: Live-Sync fuer `opencode` und `kilo` im laufenden Service ausloesen und pruefen, wie aussagekraeftig Kilo-Message-Inhalte aus den vorhandenen SQLite-Daten im UI erscheinen.

## Update 2026-04-05
- Changed: End-to-End-Validierung fuer die neuen `kilo`-/`opencode`-Importer abgeschlossen; Session-IDs wie `ses_...` werden jetzt von der Validierung akzeptiert, sodass Detailseiten und Exporte fuer diese Tools funktionieren. Dabei fiel ein echter OpenCode-Pfadfehler auf: der Importer suchte Messages relativ zu `storage/session/...` statt zu `storage/...`; der Pfad wurde korrigiert.
- Files: `services/session_validation_service.py`, `services/importers/opencode_importer.py`, `tests/test_session_validation_service.py`
- Verify: `pytest tests/test_session_import.py tests/test_session_validation_service.py -q`; danach `/api/sessions?account=kilo`, `/api/sessions?account=opencode` sowie Detail-APIs fuer `ses_...` gegen den laufenden Service pruefen.
- Next: OpenCode nach dem Pfadfix erneut synchronisieren und bestaetigen, dass die bislang leere Session jetzt ihre Messages und Tokenwerte traegt.

## Update 2026-04-05
- Changed: Der Session-Hash-Cache ist jetzt importer-versioniert. Wenn sich ein Parser aendert, werden dessen Quelldateien beim naechsten Sync automatisch einmal neu importiert, statt am alten Hash-Cache haengenzubleiben. Fuer den OpenCode-Fix ist damit gezielt `opencode:v2` aktiv.
- Files: `services/session_import.py`
- Verify: Manuellen Sync ausloesen und pruefen, dass geaenderte Importer dieselben Quelldateien trotz unveraenderter Dateimtime erneut verarbeiten.
- Next: Falls noetig das gleiche Muster spaeter auch fuer einzelne Parser-Migrationspfade oder DB-Backfills feiner granulieren.

## Was in dieser Session passiert ist (2026-04-04)

### Sprint QX: Dashboard-Self-Discovery konfigurierbar gemacht

**Ziel:** Das Repo `project_dashboard` nicht mehr hart aus der Projektliste ausschliessen, sondern ueber Settings im Dashboard selbst steuerbar machen.

**Umgesetzt:**
- Neues Persistenz-Layer `services/dashboard_settings_service.py` angelegt
- Settings werden jetzt in `dashboard_settings.json` gespeichert und fallen nur initial auf Env-Defaults zurueck
- Neue API `GET/POST /api/settings/general` angelegt
- `templates/settings.html`, `static/js/settings.js` und `static/css/settings.css` um einen General-Tab mit Toggle fuer `project_dashboard`-Self-Discovery erweitert
- `services/project_scanner.py` und `routes/project_routes.py` lesen die Einstellung jetzt dynamisch aus dem Settings-Service statt aus einer statischen Config-Konstante
- Default bleibt sichtbar; die Option kann jetzt direkt im UI gespeichert werden

**Geaenderte Dateien:**
- `config.py`
- `services/dashboard_settings_service.py`
- `services/project_scanner.py`
- `routes/settings_routes.py`
- `routes/project_routes.py`
- `templates/settings.html`
- `static/js/settings.js`
- `static/css/settings.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Im laufenden Dashboard pruefen, dass `project_dashboard` in Listen und Suchtreffern erscheint
- pruefen, ob nach Toggle-Wechsel ein manueller Refresh/Rescan im UI noch klarer gefuehrt werden sollte

### Sprint QY: Plans-Detail gegen Legacy-DB-Schema gehaertet

**Ziel:** Den HTTP-500 beim Oeffnen einer Plan-Card beheben, wenn die produktive DB bereits eine aeltere `specs`-Tabelle ohne neue Strukturspalten besitzt.

**Umgesetzt:**
- Root Cause im Live-Log identifiziert: `GET /api/plans/145` scheiterte in `ensure_plan_structure_schema()` beim Index auf `specs(sprint_plan_id, updated_at DESC)`
- `services/db_service.py` haertet die Schema-Sicherung jetzt ueber `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` fuer `sprint_plans` und `specs`
- Damit funktionieren bestehende Installationen auch dann, wenn `CREATE TABLE IF NOT EXISTS` wegen einer Alt-Tabelle keine neuen Spalten mehr anlegt
- Service neu gestartet und Migration im Live-Kontext erfolgreich ausgefuehrt
- Der zuvor betroffene Endpoint liefert nach dem Fix wieder `200`

**Geaenderte Dateien:**
- `services/db_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Optional noch Legacy-Constraints/Foreign-Keys fuer `specs` nachziehen, falls spaeter echte Datenintegritaet fuer Altbestandsdaten benoetigt wird

### Sprint QZ: Plan-Detailseite mit Tabs statt Auto-Modal

**Ziel:** Beim Klick auf Plan-Cards eine echte Detailseite bereitstellen, statt die Plans-Seite nur mit `?plan=` zu oeffnen und sofort ein Modal zu zeigen.

**Umgesetzt:**
- Neue Route `GET /plans/<id>` in `routes/plans_routes.py`
- Bestehende Legacy-Links `/plans?plan=<id>` werden serverseitig auf die neue Detailroute umgeleitet
- Neues Template `templates/plan_detail.html` angelegt
- Neue Assets `static/js/plan-detail.js` und `static/css/plan-detail.css` fuer die Detailseite mit Tabs `Overview`, `Content`, `Workflow`, `Handoff`
- Die Detailseite nutzt bestehende APIs `/api/plans/<id>`, `/api/plans/<id>/workflow` und `/api/plans/<id>/handoff`
- Die Projektdetailseite verlinkt Plan-Cards jetzt direkt auf `/plans/<id>`
- Die Plans-Uebersicht navigiert bei Card-Klick jetzt ebenfalls auf die Detailseite statt ein Modal zu oeffnen

**Geaenderte Dateien:**
- `routes/plans_routes.py`
- `templates/plan_detail.html`
- `static/js/plan-detail.js`
- `static/css/plan-detail.css`
- `static/js/plans.js`
- `static/js/project-detail.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Im Browser pruefen, ob auf der neuen Detailseite noch Inline-Editing oder weitere Tabs wie `Sections` / `Markers` benoetigt werden

### Sprint QR: Projektzentrierter Planning Workspace geplant

**Ziel:** Die UI fachlich sauber auf die Hierarchie `Project -> Master Plan -> Sprint Plan -> Task/Spec -> Session` ausrichten.

**Umgesetzt:**
- Neuer Sprint-Plan `sprints/sprint-qr-project-planning-workspace.md` angelegt
- Der Plan definiert das Projekt als primaeren Einstieg
- `/plans` wird im Zielbild als globaler Index statt als konkurrierende Arbeitsflaeche beschrieben
- `Planning` im Projekt wird als neue zentrale Hierarchieansicht spezifiziert
- Sessions werden fachlich der operativen Task-/Spec-Ebene untergeordnet
- zusaetzlich sind jetzt Architekturleitplanken dokumentiert: Glossar, Parent-Child-Regeln, Deep-Link-Prinzipien, normierte UI-Begriffe und erlaubte UI-Aktionen pro Ebene
- der Sprint ist jetzt in 5 aufeinander aufbauende Umsetzungs-Sessions heruntergebrochen

**Geaenderte Dateien:**
- `sprints/sprint-qr-project-planning-workspace.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Den neuen Sprint QR schrittweise in Project-Detail, Plans-Index und Copilot-Navigation umsetzen

## Update 2026-04-05
- Changed: Self-Discovery fuer `project_dashboard` als persistente Settings-Option mit API und UI eingebaut
- Files: `config.py`, `services/dashboard_settings_service.py`, `services/project_scanner.py`, `routes/settings_routes.py`, `routes/project_routes.py`, `templates/settings.html`, `static/js/settings.js`, `static/css/settings.css`
- Verify: `python3 -m py_compile config.py services/dashboard_settings_service.py services/project_scanner.py routes/settings_routes.py routes/project_routes.py` und `node --check static/js/settings.js`
- Next: Im Browser Toggle speichern und pruefen, wie sich Suche, Scan und Refresh direkt verhalten

## Update 2026-04-05
- Changed: Plan-Detail-500 gegen Legacy-DB-Schema behoben, indem `ensure_plan_structure_schema()` fehlende Spalten in `sprint_plans` und `specs` idempotent nachzieht
- Files: `services/db_service.py`
- Verify: `python3 -m py_compile services/db_service.py routes/plans_routes.py`, `sudo python3 -c "from services.db_service import ensure_plan_structure_schema; ensure_plan_structure_schema(); print('ok')"` und `sudo curl http://127.0.0.1:5055/api/plans/145`
- Next: Im Browser denselben Plan erneut oeffnen und auf weitere Legacy-Schema-Abweichungen achten

## Update 2026-04-05
- Changed: Echte Plan-Detailseite mit Tabs gebaut und alte `?plan=`-Links auf `/plans/<id>` umgestellt
- Files: `routes/plans_routes.py`, `templates/plan_detail.html`, `static/js/plan-detail.js`, `static/css/plan-detail.css`, `static/js/plans.js`, `static/js/project-detail.js`
- Verify: `python3 -m py_compile routes/plans_routes.py`, `node --check static/js/plan-detail.js`, `node --check static/js/plans.js`, `node --check static/js/project-detail.js`
- Next: Live im Browser auf Inhalt, Workflow und Handoff-Tabs gegen echte Plaene pruefen

## Update 2026-04-05
- Changed: Neuen Sprint-Plan fuer den projektzentrierten Planning Workspace erstellt
- Files: `sprints/sprint-qr-project-planning-workspace.md`
- Verify: Inhaltlich gegen Zielbild `Project -> Master Plan -> Sprint Plan -> Task/Spec -> Session` geprueft
- Next: Sprint QR operativ in die Projekt-UI ueberfuehren

## Update 2026-04-05
- Changed: Sprint QR um Architekturleitplanken und Navigationsregeln geschaerft
- Files: `sprints/sprint-qr-project-planning-workspace.md`
- Verify: Glossar, Parent-Child-Regeln, Deep-Link-Prinzipien und UI-Aktionsgrenzen sind jetzt explizit dokumentiert
- Next: Bei der Umsetzung alle sichtbaren Begriffe auf `Plan`, `Sprint`, `Spec`, `Task`, `Session` normieren

## Update 2026-04-05
- Changed: Sprint QR in 5 aufeinander aufbauende Umsetzungs-Sessions heruntergebrochen
- Files: `sprints/sprint-qr-project-planning-workspace.md`
- Verify: Jede Session baut jetzt explizit auf der vorherigen auf und hat ein klares Ergebnis
- Next: Umsetzung mit Session 1 beginnen: Navigation und Begriffssystem festziehen

## Update 2026-04-05
- Changed: Sprint QR Session 1 im UI gestartet; Projekt-Tabs und globale Navigation auf `Planning`, `Session History` und `Plan Index` geschoben, `/plans` als read-first Index gerahmt und Plan-Deep-Links mit Ruecksprung in den Projektkontext versehen
- Files: `templates/base.html`, `templates/project_detail.html`, `static/js/project-detail.js`, `templates/plans.html`, `static/js/plans.js`, `templates/plan_detail.html`, `static/js/plan-detail.js`
- Verify: `node --check static/js/project-detail.js`, `node --check static/js/plans.js`, `node --check static/js/plan-detail.js`
- Next: Session 2 umsetzen und im Projekt die echte Hierarchie `Plan -> Sprint -> Task/Spec` statt flacher Plan-Cards rendern

## Update 2026-04-05
- Changed: Sprint QR Session 2 umgesetzt; neuer Read-Endpoint fuer die Projekt-Planning-Hierarchie gebaut und den Projekt-Tab `Planning` von flachen Plan-Cards auf eine sichtbare Hierarchie `Plan -> Sprint -> Spec/Task` umgestellt
- Files: `services/plan_structure_service.py`, `routes/plans_routes.py`, `static/js/project-detail.js`, `static/css/project-detail.css`, `tests/test_plan_structure_service.py`
- Verify: `python3 -m py_compile services/plan_structure_service.py routes/plans_routes.py`, `node --check static/js/project-detail.js`, `pytest tests/test_plan_structure_service.py -q`
- Next: Session 3 umsetzen und fuer `Spec` bzw. `Task` ein operatives Detailpanel mit Ziel, Next Step, Prompt, Checks, Status und Risiko anbinden

## Update 2026-04-05
- Changed: Sprint QR Session 3 umgesetzt; im Projekt-Workspace gibt es jetzt ein selektierbares Detailpanel fuer `Sprint`, `Spec` und operative `Task`-Eintraege, Marker liefern dort Ziel, Next Step, Prompt, Checks und Risiko; zusaetzlich wurde die neue Planning-Logik bewusst in eigene JS/CSS-Assets ausgelagert, damit die 500-Zeilen-Grenze pro Datei eingehalten bleibt
- Files: `services/plan_structure_service.py`, `static/js/project-planning.js`, `static/css/project-planning.css`, `static/js/project-detail.js`, `static/css/project-detail.css`, `templates/project_detail.html`, `tests/test_plan_structure_service.py`
- Verify: `node --check static/js/project-detail.js`, `node --check static/js/project-planning.js`, `pytest tests/test_plan_structure_service.py -q`
- Next: Session 4 umsetzen und echte Sessions ueber `last_session` bzw. Session-Daten sichtbar an Task/Spec haengen

### Sprint PX: Modularer Start der Hashtag-First Markdown-Routine

**Ziel:** Die neue Markdown-first Architektur nicht als Monolith, sondern mit einem wiederverwendbaren Kernservice starten und den ersten produktiven Integrationspfad direkt daran anbinden.

**Umgesetzt:**
- Neuer generischer Service `services/markdown_routine_service.py` angelegt
- Der Service kapselt jetzt Encoding-Fallback, Content-Hash ohne Steuer-Marker, heuristische Markdown-Klassifikation, Tag-Erkennung fuer `#sprint-*`/`#spec-*`, semantische Split-Points und Sprint-/Spec-Struktur-Extraktion
- Die Altdateien unter `upload/hash/` wurden als konkrete Referenz benutzt, aber nicht 1:1 portiert; die Logik wurde auf generische Pattern-Sets und projektuebergreifende Funktionen reduziert
- `services/copilot_marker_service.py` erweitert Marker jetzt um `sprint_tag` und `spec_tag`
- `sprinttomarkers_from_content()` und der bestehende Sprint-Import ziehen bei getaggten Sprint-Dateien Tags direkt aus der neuen Struktur-Extraktion und schreiben sie an Marker
- Marker-Kontext schreibt `sprint_tag` und `spec_tag` jetzt ebenfalls in `marker-context.md`
- Neue Tests fuer den Markdown-Service und die Marker-Tag-Integration laufen lokal gruen: `pytest tests/test_markdown_routine_service.py tests/test_copilot_marker_service.py -q` mit `26 passed`

**Geaenderte Dateien:**
- `services/markdown_routine_service.py`
- `services/copilot_marker_service.py`
- `tests/test_markdown_routine_service.py`
- `tests/test_copilot_marker_service.py`
- `sprints/sprint-px-hashtag-first-markdown-routine.md`

**Naechste Session:**
- `scripts/markdown_tag_migration.py` mit `--check` / `--apply` auf Basis des neuen Services anlegen
- Tag-Setter fuer fehlende `#sprint-*` / `#spec-*` entwerfen
- Marker-Backfill fuer bestehende `handoff.md`-Marker modular auf die neue Struktur-Extraktion setzen
- danach Sprint-/Spec-Parsing und UI-Mapping schrittweise von Titel-Heuristiken auf Tag-Hierarchie umstellen

### Sprint PX: Modul 2 - Check/Apply-Routine fuer fehlende Markdown-Tags

**Ziel:** Den neuen Service sofort operativ machen: fehlende Sprint-/Spec-Tags projektweit erkennen und idempotent direkt in Markdown-Dateien schreiben koennen.

**Umgesetzt:**
- `services/markdown_routine_service.py` um `build_tag_update_plan()` und `apply_tag_update_plan()` erweitert
- Fehlende `#sprint-*`-Tags werden fuer Sprint-Headings und fehlende `#spec-*`-Tags fuer Unterabschnitte innerhalb eines Sprints als Update-Plan vorgeschlagen
- `scripts/markdown_tag_migration.py` neu angelegt
- Das Script unterstuetzt jetzt:
  - `--check` fuer reine Analyse
  - `--apply` fuer idempotentes Schreiben fehlender Tags
  - optional `--project`
  - optional `--handoff` fuer Marker-Pruefung
- Die erste Version schreibt bewusst nur Markdown-Tags; Marker-Backfill bleibt als naechster modularer Schritt separat
- Lokale Tests fuer Tag-Setter, Check/Apply und Marker-Integration laufen gruen: `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py -q` mit `30 passed`

**Geaenderte Dateien:**
- `services/markdown_routine_service.py`
- `scripts/markdown_tag_migration.py`
- `tests/test_markdown_routine_service.py`
- `tests/test_markdown_tag_migration.py`
- `next-session.md`

**Naechste Session:**
- Marker-Backfill fuer bestehende `handoff.md`-Marker in `scripts/markdown_tag_migration.py` bzw. Service-Layer ergaenzen
- Mapping bevorzugt ueber `plan_id`, Sprint-Struktur und Spec-Titel statt loser Volltextsuche
- danach Copilot-/Plan-UI schrittweise auf `Plan -> Sprint -> Spec -> Marker` umstellen

### Sprint PX: Modul 3 - Marker-Backfill fuer bestehende handoff.md Marker

**Ziel:** Bestehende Marker konservativ an die neue Tag-Hierarchie anbinden, ohne freie Volltext-Magie oder blindes Ueberschreiben.

**Umgesetzt:**
- `scripts/markdown_tag_migration.py` baut jetzt einen Struktur-Index aus den gescannten Markdown-Dateien
- Der Marker-Backfill mappt bevorzugt ueber eindeutige `plan_id`
- `spec_tag` wird nur gesetzt, wenn innerhalb des eindeutig gemappten Sprints ein eindeutiger Treffer ueber Task-Titel oder Spec-Titel existiert
- Marker mit bereits gesetztem `sprint_tag` bleiben unangetastet
- `--check` zeigt fuer ungetaggte Marker jetzt vorgeschlagene `sprint_tag`/`spec_tag`-Werte samt Mapping-Grund an
- `--apply` schreibt diese Marker-Felder idempotent in `handoff.md`
- Neue Tests decken Vorschlag, Writeback und zweiten idempotenten Lauf ab; `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py -q` laeuft jetzt mit `32 passed`

**Geaenderte Dateien:**
- `scripts/markdown_tag_migration.py`
- `tests/test_markdown_tag_migration.py`
- `next-session.md`

**Naechste Session:**
- Copilot-/Plan-UI und Parser-Pfade von Titel-Aehnlichkeit auf `sprint_tag`/`spec_tag` umstellen
- bestehende Sprint-Sections- und Source-Mappings gegen getaggte Inhalte pruefen
- optional spaeter Mapping-Heuristiken erweitern, aber nur mit klaren Prioritaetsregeln

### Sprint PX: Modul 4 - Tag-basierter Parser/UI-Pfad fuer Plan Sections

**Ziel:** Den ersten sichtbaren Produktpfad von Frontend-Heuristik auf serverseitige Tag-Hierarchie umstellen.

**Umgesetzt:**
- `services/plan_structure_service.py` nutzt fuer Sprint-/Spec-Struktur jetzt bevorzugt `scan_markdown_structure()` statt nur Heading-RegEx
- `sync_sprint_plans_from_master()` und `sync_specs_from_sprint_plan()` priorisieren `sprint_tag`, `spec_tag` und `plan_id` aus Markdown
- `get_plan_structure()` und `get_sprint_plan_detail()` matchen Marker bevorzugt ueber `sprint_tag` und `spec_tag`, mit Legacy-Fallback auf `plan_id` bzw. bestehende DB-IDs
- Neuer serverseitiger Helper `derive_tagged_plan_sections()` erzeugt direkt die Hierarchie `Plan -> Sprint -> Spec -> Marker`
- `routes/plans_routes.py` liefert in `/api/plans/<id>` jetzt zusaetzlich `tagged_sections`
- `static/js/copilot_board.js` nutzt fuer `Sprint Sections` bevorzugt `plan.tagged_sections` statt die Quellstruktur komplett lokal aus `##`-Headings zu erraten
- Das Board mappt Marker fuer diese Sections jetzt bevorzugt ueber `sprint_tag`; Titel-Aehnlichkeit bleibt nur noch Legacy-Fallback fuer ungetaggte Inhalte
- Das Source-Panel zeigt Tasks jetzt inklusive Spec-Kontext und Marker inkl. Tag-Hierarchie an
- Neue Service-Tests und Syntaxchecks laufen gruen: `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py tests/test_plan_structure_service.py -q` mit `34 passed`, plus `node --check static/js/copilot_board.js`

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `routes/plans_routes.py`
- `static/js/copilot_board.js`
- `tests/test_plan_structure_service.py`
- `next-session.md`

**Naechste Session:**
- Das Copilot-Board gegen echte getaggte Plaene im Browser pruefen
- weitere Altpfade auf `sprint_tag` / `spec_tag` umziehen, insbesondere dort, wo noch numerische `sprint_plan_id` / `spec_id` als Hauptpfad dienen
- optional API-Responses fuer Marker- und Plan-Detailansichten noch expliziter um Hierarchie-Metadaten erweitern

### Sprint PX: Abschlussstand im Repo

**Ziel:** Die restlichen naheliegenden Legacy-Pfade im Code schliessen, damit ausser Live-Validierung keine groessere Sprint-Arbeit mehr offen bleibt.

**Umgesetzt:**
- `services/plan_structure_service.py` priorisiert bei DB-Referenzaufloesung fuer Specs jetzt `spec_tag` vor `spec_title`
- `services/copilot_marker_service.py` reicht `spec_tag` in die Struktur-Referenzaufloesung durch
- `services/copilot_service.py` fuehrt `sprint_tag` und `spec_tag` jetzt explizit im kompakten Marker-Kontext fuer Copilot-Calls mit
- Tests fuer diese Restpfade ergaenzt; die relevanten Sprint-Pfade laufen lokal mit `75 passed`
- Python-Syntaxcheck und `node --check static/js/copilot_board.js` laufen ebenfalls gruen

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `services/copilot_marker_service.py`
- `services/copilot_service.py`
- `tests/test_plan_structure_service.py`
- `tests/test_copilot.py`
- `next-session.md`
- `sprints/sprint-px-hashtag-first-markdown-routine.md`

**Naechste Session:**
- echte getaggte Plaene im Browser pruefen
- nur noch reale Mapping-Abweichungen nachschaerfen, falls sie in Live-Daten auftauchen

### Neuer Gesamt-Sprint-Plan fuer Hashtag-First Markdown-Routine

**Ziel:** Die fachliche Kette `Plan -> Sprint -> Spec -> Marker` als Markdown-first und projektuebergreifend planbar machen, inklusive Wiederverwendung der alten Hash-/Parser-Logik aus IR-Tours.

**Umgesetzt:**
- Neue Sprint-Datei `sprints/sprint-px-hashtag-first-markdown-routine.md` angelegt
- Der Plan definiert `#sprint-*` und `#spec-*` als stabile Tags fuer Sprint und Spec
- Marker sollen kuenftig `sprint_tag` und optional `spec_tag` tragen
- Der Plan ersetzt die DB-first-Richtung als primaere Architektur und beschreibt stattdessen eine generische Python-Routine fuer alte und neue Projekte
- Als Altquellen fuer die neue Routine sind `hash_manager.py`, `md_classifier.py` und `split_fragenkatalog_v4_safe.py` aus `proj_irtours/archive/ALT/tools/scripts` festgehalten
- Der Plan enthaelt jetzt explizit eine projektuebergreifende Tag-Migration mit `--check`/`--apply`, Tag-Setter fuer Sprint/Spec und einen Marker-Updater fuer `handoff.md`

**Geaenderte Dateien:**
- `sprints/sprint-px-hashtag-first-markdown-routine.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- `services/markdown_routine_service.py` als generischen Parser-/Klassifikations-Service anlegen
- `scripts/markdown_tag_migration.py` fuer projektweiten `check/apply`-Lauf entwerfen
- Marker-Schema um `sprint_tag/spec_tag` erweitern
- Sprint-/Spec-Parsing und UI-Mapping schrittweise auf Tags umstellen

### Copilot Sprint P-E3: Execution-Rating & Feedback fuer Marker

**Ziel:** Nach markerbezogenen Sessions eine leichte manuelle Ausfuehrungsbewertung erfassen, die am Marker und optional an der Session haengt.

**Umgesetzt:**
- `services/copilot_marker_service.py` um optionale Marker-Felder `execution_score`, `execution_comment`, `last_execution_at` erweitert; `update_execution_rating()` validiert `0..5`, schreibt die Marker-Felder und aktualisiert bei Bedarf auch `sessions.execution_score` / `sessions.execution_comment`
- `services/db_service.py` erweitert `ensure_session_review_schema()` idempotent um die neuen Session-Spalten fuer Execution-Ratings
- `routes/copilot_routes.py` enthaelt jetzt `GET/POST /api/marker/<marker_id>/execution-rating`
- `routes/session_routes.py` liefert in `/api/sessions/<uuid>` zusaetzlich `session.marker`, wenn ein Marker denselben `last_session`-Wert traegt
- `templates/session_detail.html`, `static/js/session-detail.js` und `static/css/session-detail.css` haben ein kleines Rating-Panel fuer den zugeordneten Marker; Speichern sendet den Score zusammen mit `sessionid`
- `templates/copilot_board.html`, `static/js/copilot_board.js` und `static/css/copilot.css` zeigen Execution-Score und Kommentar direkt im Board bzw. Marker-Panel an und erlauben dort schnelles Ueberschreiben
- Tests decken Marker-Rating, Session-Update und den API-Flow ab; `pytest tests/test_copilot_marker_service.py tests/test_copilot.py -q` laeuft lokal mit `55 passed`

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/db_service.py`
- `routes/copilot_routes.py`
- `routes/session_routes.py`
- `templates/copilot_board.html`
- `templates/session_detail.html`
- `static/js/copilot_board.js`
- `static/js/session-detail.js`
- `static/css/copilot.css`
- `static/css/session-detail.css`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`

**Naechste Session:**
- Den Flow einmal mit einer echten Session pruefen, bei der `last_session` auf einen Marker zurueckgeschrieben wurde
- P-E4 kann auf Basis der neuen Marker-/Session-Felder Monitoring und Vergleiche aufbauen

### Copilot Sprint P5: Sprint->Marker Fallback fuer DB-Plan-Content

**Ziel:** Der Button `Sprint -> Marker` soll nicht nur mit einer separaten Sprint-Datei funktionieren, sondern auch dann, wenn der aktuelle Plan bereits als `project_plans.content` vorliegt.

**Umgesetzt:**
- `static/js/copilot_board.js` schickt fuer den Import jetzt nur noch `filename` bzw. die semantische Plan-ID statt eines hart verdrahteten `upload/Sprints/...`-Pfads
- `routes/copilot_routes.py` faellt in `POST /api/sprint/<plan_id>/to-markers` bei `sprint_missing` auf den DB-Planinhalt (`project_plans.content`) zurueck
- `services/copilot_marker_service.py` enthaelt dafuer jetzt `sprinttomarkers_from_content()`
- Tests decken den Fallback-Flow ohne externe Sprint-Datei ab; `pytest tests/test_copilot_marker_service.py tests/test_copilot.py -q` laeuft mit `57 passed`

**Naechste Session:**
- Im Live-Board einmal den Button `Sprint -> Marker` gegen einen echten DB-Plan ohne separate Sprint-Datei pruefen

### Copilot Board: Sprint Sections ueber dem Marker-Board

**Ziel:** Die Quelle `Plan/Sprint -> Marker` dauerhaft sichtbar machen statt nur ueber einen Import-Button.

**Umgesetzt:**
- `templates/copilot_board.html`, `static/js/copilot_board.js` und `static/css/copilot.css` zeigen jetzt oberhalb des Marker-Boards einen `Sprint Sections`-Bereich
- Die Cards werden direkt aus `project_plans.content` ueber `##`-Abschnitte abgeleitet und gegen vorhandene Marker gemappt
- Jede Section-Card zeigt Abschnittstitel, Kurzsummary, Task-Anzahl, Mapping-Status und die ersten zugeordneten Marker
- Das rechte Panel hat zusaetzlich einen `Source`-Tab mit Abschnitt, erkannten Tasks, zugeordneten Markern und Rohinhalt
- JS-Syntaxcheck und Copilot-Tests laufen lokal weiter gruen: `node --check static/js/copilot_board.js`, `pytest tests/test_copilot.py tests/test_copilot_marker_service.py -q`

**Naechste Session:**
- Live im Browser pruefen, ob die Section-Erkennung fuer verschiedene Planformate fein genug ist oder noch mehr Heading-/Task-Heuristiken braucht

### Copilot Sprint P4: Session Write-back geschlossen

**Ziel:** Den Session-Ende-Stand explizit in den zugehoerigen Marker in `handoff.md` zurueckschreiben, ohne neue Auto-Start-Logik einzufuehren.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `close_marker()` erweitert; schreibt gezielt `status`, `naechster_schritt`, `last_session` und `updated_at` in den betroffenen Marker zurueck
- `routes/copilot_routes.py` um `POST /api/copilot/markers/<id>/close` erweitert; liefert definierte Fehler fuer `handoff_missing` und `marker_not_found` und kann `project_id` bei Bedarf aus `marker-context.md` ableiten
- `marker-context.md` enthaelt beim Aktivieren jetzt zusaetzlich `project_id`, damit die Session-Zuordnung stabiler bleibt und der Close-Flow ohne explizites `project_id` arbeiten kann
- `static/js/copilot_board.js` hat eine kleine `closeMarkerSession()`-Hilfsfunktion; nach erfolgreichem Close wird das Board neu geladen und zeigt den Statuswechsel spaetestens beim Refresh
- Tests decken den Service-Roundtrip und den neuen Close-Endpunkt ab; ein manueller Test-Flow `activate -> close -> parse_markers()` liefert `done`, `last_session` und aktualisierten Next Step
- `tests/test_copilot.py` laeuft jetzt lokal ohne Postgres: In-Memory-Copilot-DB-Fake in `tests/conftest.py`, Redirect-Erwartung fuer `/copilot` aktualisiert und Bild-Persistenz im Copilot-Service an die bestehende API-Spec angeglichen
- Copilot-/Plan-Testinfrastruktur teilweise vereinheitlicht: `tests/test_copilot.py`, `tests/test_plan_sections.py` und der Copilot-Binding-Test in `tests/test_plan_workflow.py` nutzen jetzt denselben Mock-/Shared-Fixture-Pfad; reine UI-Render-Tests erzeugen keinen DB-Plan mehr
- `tests/test_plan_workflow.py` Handoff-Drift behoben: Legacy-Import auf den aktuellen `project_handoff_service` umgestellt, Erwartungen auf das Marker-Format aktualisiert und Handoff-Tests mit kleinem In-Memory-Plan-Store von Postgres entkoppelt

### Copilot Sprint P5: Sprint -> Marker Import

**Ziel:** Aufgaben aus einem Sprint-Plan per Klick in Marker in `handoff.md` ueberfuehren, ohne Duplikate zu erzeugen.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `sprinttomarkers()` und `buildsuggestion()` erweitert; Sprint-Sektion wird ueber `Plan-ID` gelesen, Aufgaben-Bullets werden als Marker geschrieben oder aktualisiert
- Marker-IDs sind deterministisch aus `plan_id + titel`, so dass wiederholte Aufrufe keine doppelten Marker erzeugen
- `routes/copilot_routes.py` enthaelt jetzt `POST /api/sprint/<plan_id>/to-markers`
- `templates/copilot_board.html` und `static/js/copilot_board.js` haben den Button `Sprint -> Marker`; nach erfolgreichem Import wird das Marker-Board neu geladen
- Das Board erkennt fuer Marker bei Bedarf eine semantische `Plan-ID` aus dem Plan-Inhalt und faellt sonst auf die bisherige numerische Plan-ID zurueck
- `static/css/copilot.css` zeigt Marker-Titel jetzt ueber bis zu vier Zeilen und den Vorschau-/Prompt-Text ueber bis zu drei Zeilen statt nur als Einzeiler; ausserdem sind die Board-Spalten fuer Marker-Cards breiter, damit TODO/GENERATING/DONE/BLOCKED mehr Inhalt aufnehmen
- `static/js/copilot_board.js` rendert den Vorschau-Block direkt unter dem Marker-Titel statt erst unter Gate/Status-Hinweisen, damit der eigentliche Inhalt in der Card frueher lesbar ist
- `static/css/copilot.css` haertet die Chat-Nachrichten im rechten Panel gegen Overflow ab; lange Antworten, Markdown-Code und Tabellen umbrechen bzw. bleiben innerhalb der Chat-Card
- `static/css/copilot.css` haertet die Scroll-Container im rechten Chat-Panel mit `min-height: 0` ab, damit Chat-Boxen beim Scrollen nicht abgeschnitten werden
- `services/copilot_service.py` persistiert fuer `copilot_runs` jetzt auch `input_tokens`, `output_tokens`, `total_tokens` und `cost_usd`; `static/js/copilot_board.js` zeigt diese API-Kosten als Meta-Zeile unter Assistant-Nachrichten im Chat-Panel an
- `services/copilot_service.py` baut vor dem Perplexity-Call jetzt serverseitig einen kompakten Marker-Kontext aus `marker-context.md` und `handoff.md`; `handoff.md` bleibt fuehrende Wahrheit, Frontend-Kontext ist nur noch Fallback
- `services/copilot_service.py` loest fuer den serverseitigen Marker-Kontext jetzt auch den lesbaren `plan_title` aus `project_plans` auf; `static/js/copilot_board.js`, `static/js/plans.js` und `templates/copilot_landing.html` zeigen bzw. verwenden den Plan-Namen in Panel und Copilot-URL zusaetzlich zur `plan_id`

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `routes/copilot_routes.py`
- `templates/copilot_board.html`
- `static/js/copilot_board.js`
- `static/css/copilot.css`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`

**Naechste Session:**
- Den Import einmal gegen reale Sprint-Dateien im laufenden Board pruefen
- Optional spaeter die Sprint-Pfad-Ableitung weiter haerten, falls Plans aus anderen Verzeichnissen kommen

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/copilot_service.py`
- `routes/copilot_routes.py`
- `static/js/copilot_board.js`
- `tests/conftest.py`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `tests/test_plan_sections.py`
- `tests/test_plan_workflow.py`

**Naechste Session:**
- Optional den Close-Endpunkt aus einer Session-Detailansicht oder einem Import-Flow explizit aufrufen
- Copilot-Workspace weiter optisch nachschaerfen; P4 selbst fuehrt keine neue Session-Start-Logik ein

---

## Was in dieser Session passiert ist (2026-04-03)

### Session-Abschluss: Live-Stand konsolidiert

**Ziel:** Den aktuellen Produktstand fuer die naechste Session realistisch zusammenfassen.

**Stand jetzt:**
- Sidebar ist task-basiert gruppiert, verdichtet, responsiv und mit Accordions fuer seltenere Bereiche live
- Copilot Sprint P3 ist live: Marker-Aktivierung schreibt `marker-context.md`, setzt Marker auf `in_progress`, startet aber keine Session automatisch
- `Quality` und `Governance` zeigen nur noch Projekte mit relevanten Datei-Aenderungen in den letzten 90 Tagen
- Mehrere UI-/Service-Fixes der Session sind bereits auf `main` gepusht und auf dem Server deployed

**Naechster sinnvoller Fokus:**
- Copilot-Workspace visuell und funktional fertigziehen, statt weitere globale Navigation umzubauen

### Responsive Sidebar fuer Mobile

**Ziel:** Die linke Navigationsleiste soll auf Tablet/Mobile nicht mehr fix den Content einengen, sondern als sauberer Drawer funktionieren.

**Umgesetzt:**
- `templates/base.html` um einen Sidebar-Backdrop erweitert
- `static/js/base.js` um Mobile-Drawer-Logik, `Esc`-Close, Focus-Restore und Auto-Close bei Navigation erweitert
- `static/css/layout.css` fuer Off-Canvas-Sidebar, Backdrop und responsive Topbar angepasst
- `static/css/base.css` sperrt Body-Scroll, solange die mobile Sidebar offen ist
- Auf Mobile scrollt jetzt die gesamte Sidebar inklusive `Help Center` und `Settings`, statt den Footer separat stehen zu lassen

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `static/css/layout.css`
- `static/css/base.css`

### Sidebar-Navigation logisch gestrafft

**Ziel:** Die globale Navigation soll weniger verstreut wirken und in der Reihenfolge schneller erfassbar sein.

**Umgesetzt:**
- `templates/base.html` gruppiert die Sidebar jetzt in `Core`, `AI Ops`, `Engineering` und `Content`
- `Plans`, `Copilot` und `New Project` sind in den Kernbereich gezogen
- Lange Labels wurden gekuerzt, z.B. `Claude Sessions` -> `Sessions`, `Model Comparison` -> `Models`, `LLM Commands` -> `Commands`

**Geaenderte Dateien:**
- `templates/base.html`

### Sidebar visuell verdichtet

**Ziel:** Die linke Navigation soll auf Desktop weniger schwer und gross wirken, ohne an Lesbarkeit zu verlieren.

**Umgesetzt:**
- `static/css/layout.css` auf dichtere Sidebar-Typografie und flachere Nav-Zeilen umgestellt
- Section-Labels feiner und ruhiger gemacht
- Active-/Hover-State weniger breit und eher als kompakte Surface statt als schwere Vollflaeche umgesetzt
- Footer-Links visuell als Utility-Layer abgeschwaecht

**Geaenderte Dateien:**
- `static/css/layout.css`

### Sidebar auf Task-Mentalmodell umgestellt

**Ziel:** Die globale Navigation soll sich an echten Nutzeraufgaben statt an internen Systemkategorien orientieren.

**Umgesetzt:**
- `templates/base.html` gruppiert die Sidebar jetzt in `Arbeiten`, `Auswerten`, `System`, `Inhalte`, `Integrationen`
- `Copilot`, `Dashboard` und `Sessions` sind als primaere Ziele hervorgehoben
- `System` ist als einklappbarer Block umgesetzt und standardmaessig reduziert
- `External` wurde zu `Integrationen` umbenannt
- `static/js/base.js` speichert den Collapse-Zustand des `System`-Blocks in `localStorage`
- `static/css/layout.css` staerkt Section-Header und gibt `Copilot` einen klareren Fokuszustand

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `static/css/layout.css`

### Startseite nur noch als ein Sidebar-Ziel

**Ziel:** `/` soll in der Navigation nicht mehr doppelt als `Dashboard` und `Projects` auftauchen.

**Umgesetzt:**
- `templates/base.html` fuehrt die Startseite jetzt nur noch als `Projects`
- der aktive Zustand greift fuer `dashboard` und `projects` auf demselben Sidebar-Eintrag
- der separate `Dashboard`-Eintrag ist entfernt

**Geaenderte Dateien:**
- `templates/base.html`

### Models nach Auswerten verschoben

**Ziel:** `Models` soll fachlich als Analyse-/Vergleichsbereich statt als Systempunkt eingeordnet sein.

**Umgesetzt:**
- `templates/base.html` verschiebt `Models` aus `System` nach `Auswerten`
- der `System`-Block bleibt dadurch klarer auf operative und infrastrukturelle Punkte fokussiert

**Geaenderte Dateien:**
- `templates/base.html`

### Seitenaktionen vor globalem Hilfe-Icon

**Ziel:** Kontextbezogene Header-Aktionen wie `Guide` sollen vor dem globalen Hilfe-Icon stehen.

**Umgesetzt:**
- `templates/base.html` rendert `topbar_actions` jetzt vor dem globalen `?`-Hilfe-Icon
- auf `/quality` steht der `Guide`-Button damit vor dem Help-Center-Shortcut

**Geaenderte Dateien:**
- `templates/base.html`

### Quality/Governance/Audits/Commands als eigener Block

**Ziel:** Bewertungs- und Steuerungsfunktionen sollen nicht im Infrastruktur-Block `System` untergehen.

**Umgesetzt:**
- `templates/base.html` fuehrt jetzt einen eigenen Bereich `Steuern`
- `Quality`, `Governance`, `Audits` und `Commands` liegen nicht mehr unter `System`
- `System` bleibt damit auf operative Themen wie `Containers`, `Dependencies` und `Schedules` fokussiert

**Geaenderte Dateien:**
- `templates/base.html`

### Governance nur fuer kuerzlich geaenderte Projekte

**Ziel:** Die Governance-Uebersicht soll wie `Quality` nur aktive Projekte zeigen, die in den letzten 90 Tagen relevante Datei-Aenderungen hatten.

**Umgesetzt:**
- `services/governance_service.py` filtert `get_governance_overview()` jetzt auf Projektdateien mit relevanter Aenderung in den letzten 90 Tagen
- `project.json` allein zaehlt bewusst nicht als Aktivitaet, damit keine reinen Metadaten-Leichen in `/governance` erscheinen
- Tests decken den Fall "recent code" sowie "nur frisches project.json, aber alter Code" explizit ab

**Geaenderte Dateien:**
- `services/governance_service.py`
- `tests/test_governance_gate.py`

### Inhalte und Integrationen als Accordion

**Ziel:** Seltenere Sidebar-Bereiche sollen Platz sparen und dieselbe Collapse-Logik wie `System` nutzen.

**Umgesetzt:**
- `templates/base.html` fuehrt `Inhalte` und `Integrationen` jetzt als einklappbare Sidebar-Bloecke
- `static/js/base.js` speichert deren Collapse-Zustand ebenfalls in `localStorage`
- beide Bereiche starten standardmaessig eingeklappt

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`

### Auswerten als Accordion hinter Steuern

**Ziel:** `Auswerten` soll dieselbe Accordion-Logik wie `System`, `Inhalte` und `Integrationen` nutzen und in der Reihenfolge hinter `Steuern` stehen.

**Umgesetzt:**
- `templates/base.html` fuehrt `Auswerten` jetzt als einklappbaren Block
- `Auswerten` steht jetzt nach `Steuern`
- `static/js/base.js` erweitert die Default-Collapse-Zustaende um `analysis`

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`

### Handoff-Fallback fuer neue Projektordner

**Ziel:** `handoff.md` auch dann robust erzeugen, wenn ein Projektordner schon existiert, aber in `project_plans` noch keine Plaene vorhanden sind.

**Umgesetzt:**
- `services/project_handoff_service.py` erzeugt in `write_handoff()` jetzt einen minimalen `copilot_markers_v1`-Handoff statt mit `None` abzubrechen
- Neuer Minimal-Handoff bleibt marker-kompatibel, enthaelt aber bewusst keine Marker-Bloecke
- Tests decken jetzt den Fall "Projektordner existiert, aber keine Plans" explizit ab

**Geaenderte Dateien:**
- `services/project_handoff_service.py`
- `tests/test_project_handoff.py`

### Copilot Chat-Verlauf fuer Marker wiederhergestellt

**Ziel:** Panel-Chat im Copilot-Board soll Marker-Threads wieder laden koennen, ohne auf `/api/copilot/runs` mit 500 zu scheitern.

**Umgesetzt:**
- `services/copilot_service.py` akzeptiert in `list_copilot_runs()` jetzt wieder `plan_id` als Filter
- Verlauf-Response liefert `plan_id` wieder mit aus
- Damit funktioniert der Marker-Chat-Load aus `static/js/copilot_board.js` wieder gegen den Live-Endpunkt

**Geaenderte Dateien:**
- `services/copilot_service.py`

### Copilot Workspace Redesign (teilweise umgesetzt)

**Ziel:** /copilot?plan_id=X als AI-native Work OS umbauen (Referenzbild vorhanden).

**Umgesetzt:**
- `/copilot` ohne plan_id → Redirect zum letzten aktiven Plan (oder /plans)
- Landing-Page wird umgangen (kein doppeltes Plan-Dashboard mehr)
- Workspace Header mit Plan-Switcher Dropdown
- Progress-Bar (done/total, Prozent, Task/Done/Review Counts)
- Board-Spalten: Backlog, Ready, Generating (statt in_progress), Review, Done, Blocked
- Emoji-Icons, Beschreibungszeilen, Empty-States pro Spalte
- Cards: Typ-Badge, Message-Count, Generating-Indikator, Zeitinfo, Hover-Actions
- Detail-Panel rechts: oeffnet/schliesst bei Karte-Klick, Tabs (Chat/Output/History)
- Panel-Close gibt Board volle Breite zurueck
- Lila-Farbe entfernt, Landing-Page auf var(--accent) umgestellt
- shadcn/ui Zinc-Palette als CSS-Design-Tokens eingefuehrt

**Geaenderte Dateien:**
- `routes/copilot_routes.py` — Redirect-Logik (redirect import, /copilot Fallback)
- `templates/copilot_board.html` — Komplett neu: Header, Progress, Split-View, Panel mit Tabs
- `templates/copilot_landing.html` — Lila entfernt, Zentrierung entfernt (wird nicht mehr direkt aufgerufen)
- `static/css/copilot.css` — Komplett neu: shadcn/ui Zinc-Tokens, alle Komponenten
- `static/css/copilot_landing.css` — Lila-Farbwerte durch var(--accent) ersetzt
- `static/js/copilot_board.js` — Komplett neu: Generating-Column, Progress, Plan-Switcher, Tabs, Panel-Logik

**Bekannte Probleme / User-Feedback:**
- Qualitaet entspricht NICHT dem Referenzbild (Linear/Vercel-Niveau nicht erreicht)
- Zu viele Iterationen fuer selbst eingefuehrte Bugs (Panel-Close, Farben, Icons)
- Zeitanzeige in Cards bricht auf 3 Zeilen um ("24 min ago" → 3 Zeilen)
- shadcn-Tokens kollidieren teilweise mit base.html Design-System
- Output-Tab und History-Tab sind leer (nur Empty-States)
- User ist enttaeuscht vom Ergebnis

### Copilot Design-System Refresh (gezielte Nachschaerfung)

**Ziel:** Kein weiterer Komplettumbau, sondern ein kleines, sauberes Dark-SaaS-Design-System auf bestehender Struktur.

**Umgesetzt:**
- Zentrale Dark-SaaS-Tokens in `static/css/design-tokens.css` auf konsistente Werte vereinheitlicht
- Neue Basis-Klassen in `static/css/components.css`: `ui-card`, `ui-panel`, `ui-button`, `ui-badge`, `ui-tabs`, `ui-input`
- Board-Card-Pattern im Copilot-Board auf die neuen Primitives gezogen (`ui-card`, `ui-badge`, `ui-button`)
- Rechtes Detail-Panel auf `ui-panel` plus neue Tabs-/Input-Primitive umgestellt
- Keine neue Seite, keine Frameworks, keine Backend- oder Architektur-Aenderung

**Geaenderte Dateien:**
- `static/css/design-tokens.css`
- `static/css/components.css`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `templates/copilot_board.html`

**Offen / naechster sinnvoller Schritt:**
- Im Browser pruefen, ob das Panel visuell sauber mit bestehendem `base.html` harmoniert
- Bei Bedarf als naechsten kleinen Schritt weitere Copilot-Elemente selektiv auf `ui-*` Klassen umstellen

### Copilot Header + Progress Refactor

**Ziel:** Nur den oberen Workspace-Bereich hochwertiger machen, ohne Board, Cards oder Panel weiter anzufassen.

**Umgesetzt:**
- Workspace-Header als eigener `ui-panel` Block mit klarer Hierarchie aufgebaut
- Linke Seite trennt jetzt Brand, Plan-Switcher und aktiven Plan
- Rechte Actions (`AI Task`, `Ask Copilot`) aus der engen Topbar in den Workspace-Header verschoben
- Progress-Leiste als kompakter Info-Block mit staerkerer visueller Gewichtung umgesetzt
- Stats (`Tasks`, `Done`, `Review`) als kleine `ui-card` KPI-Elemente dargestellt
- Bestehende Logik fuer Plan-Laden, Switcher und Progress-Berechnung unveraendert gelassen

**Geaenderte Dateien:**
- `templates/copilot_board.html`
- `static/css/copilot.css`
- `static/js/copilot_board.js`

### Marker-/Zeiger-Orchestrierung geplant

**Ziel:** Copilot fachlich von einem reinen Section-Board zu einem Markdown-gefuehrten Marker-Workflow weiterdenken.

**Erarbeitet:**
- `handoff.md` gegen aktuelle Copilot-UI geprueft: passt fachlich nicht, weil `handoff.md` projektweit aggregiert ist, Copilot-Cards aber plan-spezifisch sind
- Neue Detail-Planung erstellt: `sprints/sprint-17-marker-driven-copilot-orchestration.md`
- Master-Plan um Verweis auf Sprint 17 erweitert

**Kernidee Sprint 17:**
- feste Markdown-Datei als fuehrender Projektzustand
- Marker/Zeiger darin als adressierbare Arbeitseinheiten
- Anzeige der Marker als Copilot-Cards
- Card-Klick -> Chat/Perplexity fuer genau diesen Marker-Kontext
- spaeterer Status-Write-Back in dieselbe Datei

### Sprint P1 umgesetzt: Marker-Schema & handoff.md Generator

**Ziel:** `handoff.md` von einer aggregierten Textdatei auf ein maschinenlesbares Marker-Dual-Format umstellen.

**Umgesetzt:**
- `services/copilot_marker_service.py` neu: `Marker`-Dataclass, `_serialize_marker()`, `_write_marker()`, `parse_markers()`
- Wahrheitsquelle beim Einlesen ist jetzt der JSON-Block im HTML-Kommentar; Markdown-Teil wird immer neu aus dem Objekt erzeugt
- `services/project_handoff_service.py` schreibt jetzt Marker-Bloecke statt aggregiertem Prosatext
- Gezielte Tests fuer Parser/Writer-Roundtrip und Generator erstellt

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/project_handoff_service.py`
- `tests/test_copilot_marker_service.py`
- `tests/test_project_handoff.py`

### Sprint P2 umgesetzt: Cards aus Markdown + Status Write-back

**Ziel:** Copilot-Board auf Marker aus `handoff.md` umstellen und Status-/Prompt-Write-back direkt in die Datei schreiben.

**Umgesetzt:**
- `services/copilot_marker_service.py` um Marker-Read-/Update-Funktionen erweitert: `list_markers_for_plan()`, `get_marker_context()`, `update_marker_status()`, `update_marker_fields()`
- `routes/copilot_routes.py` um Marker-API erweitert: `GET /api/copilot/markers`, `GET /api/copilot/markers/<id>`, `PATCH /status`, `PATCH /fields`
- `static/js/copilot_board.js` laedt Board-Cards jetzt aus der Marker-API statt aus `plan_sections`
- Drag & Drop schreibt Marker-Status direkt nach `handoff.md` zurueck
- Gate-Logik im Board sichtbar gemacht (`is_activatable`, `gate_reason`)
- Detail-Panel zeigt Marker-Felder und bietet `Vorschlag uebernehmen` fuer `prompt_suggestion -> prompt`
- Chat im Panel auf markerbasierte Copilot-Threads via `thread_id=marker:<plan_id>:<marker_id>` umgelegt
- `services/project_handoff_service.py` erzeugt Default-Checks, damit Prompt-Uebernahme Marker sinnvoll aktivierbar machen kann
- Gezielte Marker-/API-Tests fuer P2 ergaenzt

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/project_handoff_service.py`
- `routes/copilot_routes.py`
- `templates/copilot_board.html`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`

### Sprint P3 umgesetzt: Prompt-Chain & Execution

**Ziel:** Aktivierbare Marker direkt aus dem Copilot-Board in einen fokussierten Ausfuehrungskontext ueberfuehren, ohne Sessions automatisch zu starten.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `is_activatable()` und `activate_marker()` erweitert; die Aktivierung nutzt dieselbe Gate-Logik wie P2, schreibt `marker-context.md` fuer genau einen Marker und setzt den Marker in `handoff.md` auf `in_progress`
- Neue API `POST /api/copilot/markers/<id>/activate` in `routes/copilot_routes.py` liefert bei Erfolg `{ ok: true, status: "in_progress" }` und bei Gate-Block sauber `{ ok: false, error: "gate_blocked", reason: ... }`
- `static/js/copilot_board.js` zeigt pro freigegebener Card einen `OK`-Button, ruft die Aktivierung auf und aktualisiert Status/UI lokal ohne Session-Autostart
- `CLAUDE.md` minimal um die Regel erweitert, dass `marker-context.md` als aktueller Fokusauftrag gilt
- Tests fuer Service- und API-Roundtrip der Marker-Aktivierung ergaenzt

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `routes/copilot_routes.py`
- `static/js/copilot_board.js`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `CLAUDE.md`

### Testdaten angelegt
- 5 Sections in Plan #5 erstellt (IDs 796-800)
- Verschiedene Status: backlog, ready, in_progress, review, done
- Diese koennen geloescht werden wenn nicht gewuenscht

### Copilot Landing-Page Aenderungen (vor dem Redesign)
- Lila Gradient-Farbe durch var(--accent) blau ersetzt
- Zentrierung entfernt (Karten linksbuendig)
- continue-card, quickstart-btn Farben angepasst

---

## Naechste Session
- Live-Validierung des modularisierten Copilot-Flows gegen echte Plaene: Plan-Switcher, `Sprint -> Marker`, Panel-Tabs, Execution-Rating, Marker-Aktivierung, Close-/Write-back
- Die neue QR-Session-Historie im Projekt-Planning gegen echte Daten pruefen: Marker, gleichnamige Markdown-Tasks, Spec-Aggregation, Session-Detail-Link
- Alternativ oder direkt danach Phase 1 von Sprint QS beginnen: DB-Zielstruktur fuer `notifications`, `favorites`, `relations`, `ideas` und `dashboard_settings` anlegen und Root-JSON-Stores schrittweise DB-first machen
- Optional danach den separaten Projekt-Tab `Session History` im Sinne von Sprint QR weiter reduzieren oder sekundarer rahmen

## Kontext
- letzter Feature-Commit: `bbaf112` `Feature: modularize copilot markdown workflow and session detail`
- letzter Doku-Commit: `372720d` `Dokumentation: update sprint commit hashes`
- `origin/main` ist aktuell, `project-dashboard` lief beim Abschluss sauber

## Lokal offen
- `handoff.md`
- `.codex`
- `static/uploads/`

## Update 2026-04-05
- Changed: Neuen Architektur-Sprint fuer DB-first Konsolidierung verteilter JSON-Zustandsdaten geplant und im Master-Plan verankert
- Files: `sprints/sprint-qs-db-first-state-consolidation.md`, `sprints/master-plan-2026-04-01.md`, `next-session.md`
- Verify: Inhaltlich gegen aktuelle Repo-Aufteilung `DB + Root-JSON + Markdown` geprueft und Migrationsreihenfolge fuer einfache JSON-Stores vor Marker-Runtime-State festgelegt
- Next: Entscheiden, ob zuerst QR Session 4 oder QS Phase 1 umgesetzt wird

## Update 2026-04-05
- Changed: Sprint QR Session 4 umgesetzt; der Planning-Service liefert jetzt Session-Summaries aus `last_session`, Marker/Tasks/Specs/Sprints zeigen ihre Session-Historie im Detailpanel, und Sessions koennen direkt aus dem Projekt-Planning geoeffnet werden
- Files: `services/plan_structure_service.py`, `static/js/project-planning.js`, `static/css/project-planning.css`, `tests/test_plan_structure_service.py`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `python3 -m py_compile services/plan_structure_service.py`, `node --check static/js/project-planning.js`, `pytest tests/test_plan_structure_service.py -q`
- Next: Im Browser mit echten Projekt-/Marker-Daten pruefen, ob die best-effort Task-Zuordnung ueber Markertitel robust genug ist oder spaeter eine explizitere Task-ID braucht

## Update 2026-04-05
- Changed: Live-Validierung fuer QR Session 4 nachgezogen und den Planning-Read-Pfad um einen klar gekennzeichneten Fallback auf echte Projektsessions erweitert, damit das Detailpanel auch bei leeren `last_session`-Feldern im aktuellen `handoff.md` nutzbaren Session-Kontext zeigt
- Files: `services/plan_structure_service.py`, `static/js/project-planning.js`, `tests/test_plan_structure_service.py`, `next-session.md`
- Verify: lokaler Restart `sudo systemctl restart project-dashboard`; Live-API `GET /api/projects/project_dashboard/planning` liefert jetzt `recent_sessions`; Bestand geprueft: `handoff.md` hat aktuell 8 Marker und 0 gesetzte `last_session`
- Next: Entweder Marker-Write-back kuenftig konsequent mit `last_session` fuellen oder einen expliziten Backfill fuer bestehende Marker planen, damit die Session-Historie von Fallback auf echte Task-Verknuepfung wechselt

## Update 2026-04-05
- Changed: `last_session`-Kontinuitaet umgesetzt; Handoff-Regeneration bewahrt jetzt bestehende Marker-Runtime-Felder, und ein neuer Backfill zieht leere `last_session`-Felder aus `project_plans.session_uuid` nach
- Files: `services/project_handoff_service.py`, `services/copilot_marker_service.py`, `scripts/backfill_marker_last_sessions.py`, `tests/test_project_handoff.py`, `tests/test_copilot_marker_service_flow.py`, `handoff.md`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `python3 -m py_compile services/copilot_marker_service.py services/project_handoff_service.py scripts/backfill_marker_last_sessions.py`, `pytest tests/test_copilot_marker_service_flow.py tests/test_project_handoff.py -q`; echter Backfill `python3 scripts/backfill_marker_last_sessions.py --project project_dashboard` ergab `updated: 7` bei `8` Markern
- Next: Den verbleibenden Marker ohne `last_session` pruefen und entscheiden, ob dafuer bewusst kein Session-Link existiert oder ein spezieller Fallback gebraucht wird

## Update 2026-04-05
- Changed: Hauptnavigation fachlogisch weiter vereinheitlicht; `Plan Index` heisst jetzt `Planning`, `Copilot` wird in der primaeren Navigation als `AI Workspace` gefuehrt, und `Sessions` wurde auf `Activity` umbenannt
- Files: `templates/base.html`, `templates/plans.html`, `templates/plan_detail.html`, `templates/copilot_landing.html`, `templates/copilot_board.html`, `templates/copilot.html`, `templates/sessions.html`, `templates/session_detail.html`, `templates/partials/index_modals.html`, `static/js/base.js`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/base.js`; Sichttexte in Sidebar, Breadcrumbs, Plan-Backlink und Command Palette vereinheitlicht; technische Routen wie `/copilot`, `/sessions` und `?tab=gitea` bleiben unveraendert
- Next: Restliche sichtbare Fachbegriffe rund um `Claude Sessions` und `Copilot` in Widgets, Landing-Texte und Detailmodule angleichen, falls die neue Navigationssprache durchgaengig ueber alle Screens gelten soll

## Update 2026-04-05
- Changed: Den redundanten Unterpunkt `Projects` entfernt; der Bereichsheader `Projects` oeffnet jetzt direkt die Hauptansicht, waehrend der Chevron separat nur das Submenue fuer `New Project`, `Overview` und `Repository Sources` schaltet
- Files: `templates/base.html`, `static/css/layout.css`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: Sidebar-Markup und CSS gegen bestehende `showTab('projects')`-Logik geprueft; keine Routen- oder JS-Logik fuer Tabs geaendert
- Next: Im Browser kurz pruefen, ob sich Klick auf `Projects` und Klick auf den Chevron im Desktop- und Mobile-Sidebar-Verhalten klar getrennt anfuehlen

## Update 2026-04-05
- Changed: Projektseite fachlich geschaerft; der Projekt-Tab `Overview` heisst jetzt `Details`, und oberhalb der Tabs rendert die Seite jetzt eine kartenbasierte Projektuebersicht fuer Plan-Fortschritt, Sprint-Plans, Quality-Issues und aktuelle Activity
- Files: `templates/project_detail.html`, `static/js/project-detail.js`, `static/css/project-detail.css`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/project-detail.js`; die neuen Cards lesen vorhandene Daten nur aus bestehenden APIs fuer Planning, Quality und Sessions, ohne neue Backend-Endpunkte
- Next: Im Browser auf echten Projekten pruefen, ob die Kartenreihenfolge und die Auswahl der Kennzahlen fachlich passen oder ob statt Quality-Issues eher Repo-Issues/GitHub-Issues prominenter gezeigt werden sollen

## Update 2026-04-05
- Changed: Die neue Projektuebersicht von reiner Statistik auf handlungsfuehrende `What Now`-Karten umgebaut; jede Karte formuliert jetzt eine Empfehlung und fuehrt direkt nach `Details`, `Planning`, `Quality` oder `Activity`
- Files: `static/js/project-detail.js`, `static/css/project-detail.css`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/project-detail.js`; die Karten nutzen weiter nur bestehende APIs, aber priorisieren jetzt naechste Aktionen statt nackter KPI-Ansammlung
- Next: Im laufenden UI pruefen, ob die Hauptkarte fachlich die richtige Prioritaet waehlt oder ob `Planning` immer der Default-Einstieg bleiben soll

## Update 2026-04-05
- Changed: Den primaeren KI-Arbeitsbereich sprachlich wieder auf `Cockpit` zurueckgezogen; Sidebar, Breadcrumbs und Seitentitel zeigen jetzt wieder denselben Fachbegriff statt `AI Workspace`
- Files: `templates/base.html`, `templates/copilot_landing.html`, `templates/copilot_board.html`, `templates/copilot.html`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: Reststellen auf sichtbares `AI Workspace` in Templates und ausgelieferten UI-Texten geprueft; technische Route `/copilot` bleibt unveraendert
- Next: Nach dem Restart kurz live pruefen, ob `Cockpit` in Sidebar und auf allen Copilot-Seiten konsistent erscheint

## Update 2026-04-05
- Changed: Projektkontext im Browser persistierbar gemacht; Projektseiten und projektbezogene Plan-/Cockpit-Einstiege speichern jetzt das aktive Projekt, und das `Cockpit` befuellt das Projektfeld beim Oeffnen automatisch wieder
- Files: `static/js/base.js`, `static/js/copilot.js`, `static/js/project-detail.js`, `static/js/project-planning.js`, `static/js/plan-detail.js`, `static/js/plans.js`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/base.js static/js/copilot.js static/js/project-detail.js static/js/project-planning.js static/js/plan-detail.js static/js/plans.js`; projektbezogene `Cockpit`-Links tragen jetzt zusaetzlich `project=` im Query-String mit
- Next: Live pruefen, ob das Projektfeld im `Cockpit` nach Wechseln zwischen Projektseite, Plan-Detail und globalem Plans-Index stabil auf dem letzten aktiven Projekt bleibt

## Update 2026-04-05
- Changed: Bewussten Testmarker fuer die Cockpit-Kontrolle in `project_dashboard` gesetzt
- Files: `handoff.md`, `next-session.md`
- Verify: Marker `test-cockpit-2026-04-05` mit Titel `TESTMARKER: Copilot-Kontrolle` auf `plan_id=142` angelegt; Gate ist offen (`is_activatable: true`)
- Next: Im Cockpit Plan `142` oeffnen und pruefen, wie Sichtbarkeit, Aktivierung, Marker-Kontext und Statuswechsel auf diesem Testmarker reagieren

## Update 2026-04-05
- Changed: Den aktiven Projektkontext jetzt auch auf globalen Filterseiten als Default eingezogen; `Planning`, `Sessions`, `Timesheets` und `Model Comparison` uebernehmen jetzt das zuletzt aktive Projekt, solange kein expliziter URL-Parameter gesetzt ist
- Files: `static/js/plans.js`, `static/js/sessions2.js`, `static/js/timesheets.js`, `static/js/model-comparison.js`, `next-session.md`
- Verify: `node --check static/js/plans.js static/js/sessions2.js static/js/timesheets.js static/js/model-comparison.js`; `Planning` liest jetzt `filters.project` aus dem aktiven Projektkontext, die anderen Seiten setzen bzw. lesen ihre Projektfilter entsprechend
- Next: Live pruefen, ob sich die Default-Filter fachlich richtig anfuehlen oder ob einzelne globale Seiten bewusst immer ungefiltert starten sollen

## Update 2026-04-05
- Changed: Rest-Audit fuer projektbezogenen Kontext nachgezogen; `Session Detail` setzt jetzt das Session-Projekt als aktiven Kontext, `Model Eval` uebernimmt und speichert den Projektkontext, und die `Cockpit`-Landing fuehrt aktive Plans projektbezogen ins Cockpit
- Files: `static/js/session-detail.js`, `static/js/model_eval.js`, `templates/copilot_landing.html`, `next-session.md`
- Verify: `node --check static/js/session-detail.js static/js/model_eval.js`; die `Cockpit`-Landing baut `project=` jetzt in aktive Plan-Links ein
- Next: Live einmal quer pruefen, ob der Projektkontext nach `Project -> Planning -> Plan Detail -> Cockpit -> Sessions -> Model Eval` stabil gleich bleibt

## Update 2026-04-05
- Changed: Vollbackup des aktuellen Repo-Stands und ein echter Live-PostgreSQL-Dump wurden erstellt, nach `backups/` kopiert und mit SHA256 sowie Restore-Hinweisen versehen. Zusaetzlich gibt es jetzt ein kleines Restore-Script fuer Verify/Extract/DB-Restore.
- Files: `next-session.md`, `backups/restore-project-dashboard-backup-20260405-220935.md`, `backups/restore-project-dashboard-backup-20260405-220935.sh`
- Verify: Backup-Dateien liegen unter `backups/`; Checksummen in `backups/project-dashboard-backup-20260405-220935.sha256`; Vollbackup `project-dashboard-full-backup-20260405-220935.tar.gz` und echter DB-Dump `project-dashboard-db-real-20260405-220935.sql` wurden lokal erstellt und abgelegt.
- Next: Falls noetig die Backup-Artefakte extern wegkopieren und den noch offenen OpenCode-Reimportpfad abschliessen, damit die bereits korrekt geparsten Messages auch im API-Datensatz sichtbar werden.


## Session 2026-04-01 - Control-Plane & RAG Foundation + Sprints A-E + Copilot

### Was wurde erledigt

**Erste Haelfte: 6 SPECs (Control-Plane Foundation)**
- SPEC-REPO-ASSESS-001: Repository Assessment (docs/repo-assessment-control-plane-rag.md)
- SPEC-PROJECT-MEMORY-001: Project Identity + Memory Foundation (9 Tests)
- SPEC-PERPLEXITY-CONNECTOR-001: Perplexity Connector via urllib (19 Tests)
- SPEC-AUDIT-ANALYZER-LLM-001: LLM Audit-Analyzer (16 Tests)
- SPEC-AUDIT-ANALYZER-GATING-001: Gating Rules (24 Tests)
- SPEC-AUDIT-PERSISTENCE-LLM-001: Evidence Persistence (13 Tests)

**Zweite Haelfte: Sprints A-E + Copilot (Masterplan-Ausfuehrung)**

Sprint A — Quality Scanner Spec:
- SPEC-QUALITY-SCANNER-MVP-001 erstellt (sprints/)

Sprint B — Quality Scanner MVP:
- Scanner validiert, Pfadaufloesung gefixt, History-Felder spec-konform, 20 Tests

Sprint C — Governance Light:
- GET /api/governance/gate/<project> (green/yellow/red + Reasons)
- Health-Ampel in Governance-Tabelle, 11 Tests

Sprint D — LLM Command Hub:
- 3 Markdown-Commands (audit-summary, risk-files, governance-recommendation)
- POST /api/llm/commands/run, Perplexity-Connector, Persistenz, UI, 15 Tests

Copilot Chat:
- POST /api/copilot/chat mit Thread-Historie und Plan-Bindung
- Chat-UI mit Markdown-Rendering, 12 Tests

Sprint E — Plan-Workflow Micro-Ebene:
- 14 Workflow-Spalten auf project_plans (ALTER TABLE)
- GET/PUT /api/plans/<id>/workflow mit Ist/Soll/Next
- Signal-Integration (Quality/Audit/Governance live), 16 Tests

### Git Commits
```
7040d27 feat: Session 2026-04-01 — Sprints A-E + Copilot Chat
91ffa58 docs: Session 2026-04-01 dokumentiert - 6 SPECs implementiert
340a03e feat: SPEC-AUDIT-PERSISTENCE-LLM-001
684e2eb feat: SPEC-AUDIT-ANALYZER-GATING-001
52476b0 feat: SPEC-AUDIT-ANALYZER-LLM-001
7416c14 feat: SPEC-PERPLEXITY-CONNECTOR-001
bc66152 feat: SPEC-AUDIT-001 - Audit-Core
1f38ea7 feat: Sprint 12 - Governance JS-Refactoring
1ea60ce feat: SPEC-PROJECT-MEMORY-001
```

### Test-Status
- **197 Tests gruen** (113 vorherige + 84 neue: 10 Audit-Integration + 20 Quality + 11 Governance + 15 LLM Commands + 12 Copilot + 16 Plan-Workflow)

### Architektur-Kette komplett
```
Messen → Auditieren → Bewerten → Steuern → Copilot
(1-4)    (Audit v1)   (B+C)      (D)       (Chat+E)
```

### Wichtige Entscheidungen
- Perplexity als strategischer Copilot (plant, reviewt, generiert Prompts)
- Claude Code als reiner Executor (fuehrt .md-Prompts aus)
- Joseph: Produkt, Architektur, Abnahme
- LLM-agnostischer Connector geplant (Perplexity nur ein Provider)

---

## Session 2026-03-31 - Sprint 11 Model Quality Comparison

### Was wurde erledigt
- Sprint 11: Model Quality Comparison komplett (Provider aus DB, top_reasons, Security-Malus, Scatter-Chart, Stack-Drilldown)
- Audit-Core (SPEC-AUDIT-001): T0-T8 komplett, 32 Tests gruen

### Offene Punkte (uebernommen)
- joshko/llm-test Projektnamen ohne Verzeichnis
- 80 Sessions ohne Modell, 0/357 mit cost_estimate
- Docker Image Workflow, Hilfe-Center EN

---

## Session 2026-03-31 (Abend) - Mobile Fixes + Hilfe-Center Responsive + Docker Image

### Was wurde erledigt

**Landingpage Mobile Fixes:**
- Problem-Panel ("Before SessionPilot") auf mobil sichtbar gemacht (war `display: none`)
- Solution-Section: Bild unter Headline verschoben auf mobil (HTML in 3 Grid-Kinder aufgeteilt)
- Abstände angeglichen, "No more guessing" margin reduziert
- Datenschutz + Impressum: Sprach-Bug gefixt (beide Sprachen wurden gleichzeitig angezeigt wegen Inline-Style Override)
- Datenschutz: h1 "Datenschutzerklärung" bricht jetzt auf mobil um
- Back-Button von Datenschutz + Impressum entfernt
- "Docs" Link in Desktop-Nav + Mobile-Menu hinzugefuegt (-> doc.session-pilot.com)

**Hilfe-Center komplett mobil-ready:**
- Fixer Mobile-Header mit Burger + Logo + Webseite-Link
- Sidebar: Brand-Bereich auf mobil ausgeblendet (redundant zum Header)
- Sidebar: Suche bleibt oben fixiert, Nav scrollt unabhaengig
- Sidebar: Backdrop-Overlay bei offenem Menue, Klick ausserhalb schliesst
- Sidebar: Nav-Link-Klick schliesst automatisch
- Bilder responsive (max-width: 100%)
- Tabellen horizontal scrollbar
- Lightbox fuer Bilder (Klick oeffnet gross, Escape/Klick schliesst)
- Farben von Blau auf Tuerkis (#00c8f0) umgestellt (passend zum Logo)
- Bootstrap text-primary/bg-primary/btn-primary ueberschrieben
- Breadcrumb-Links tuerkis
- Footer: cms.ir-tours.de -> session-pilot.com, Info-Icon entfernt
- session-pilot.com Link am Ende der Sidebar-Navigation

**Docker Image:**
- `ghcr.io/web-werkstatt/session-pilot:latest` + `:1.0.0` gepusht
- Gebaut vom sauberen `open-source` Branch (GitHub main) - KEIN PRO-Code
- OCI-Labels fuer GitHub-Repo-Verknuepfung
- Package auf GitHub public gesetzt
- Landingpage aktualisiert: "1 command. 30 seconds." statt "3 commands. 2 minutes."

**Sprint-Plaene:**
- Sprint 13: Neuer Abschnitt 13.1b "Plattform-Incident-Erkennung aus eigenen Metriken"
- Roadmap: Neue Feature-Zeile "Plattform-Incident-Erkennung"

**Dokumentation:**
- Hilfecenter-Vorlage in /mnt/projects/dokumentenaustausch/Hilfecenter-Vorlage/ kopiert
- FARBEN-ANPASSEN.md erstellt (CSS-Variablen Referenz + Schnell-Anleitung)

### Betroffene Dateien
| Datei | Aenderung |
|-------|-----------|
| session-pilot-landing/index.html | Mobile fixes, Docker install, Docs link |
| session-pilot-landing/assets/css/style.css | Problem-panel, solution-grid mobile |
| session-pilot-landing/datenschutz.html | Sprach-Bug, h1 Umbruch, Back entfernt |
| session-pilot-landing/impressum.html | Sprach-Bug, Back entfernt |
| hilfe-center/static/css/style.css | Komplett mobile-ready, Tuerkis-Farben |
| hilfe-center/templates/base.html | Mobile-Header, Backdrop, Lightbox, Sidebar-Footer |
| hilfe-center/templates/index.html | Footer cms.ir-tours -> session-pilot.com |
| Dockerfile | OCI-Labels fuer GHCR |
| sprints/sprint-13-bidirectional-llm-control.md | 13.1b Incident-Erkennung |
| sprints/10-roadmap-ai-governance.md | Neue Feature-Zeile |

---

## Session 2026-03-31 - Sprint 10: Per-File AI-Heatmap + Risk Radar

### Was wurde erledigt

**Sprint 10 komplett modular implementiert:**
- DB-Migration: `ai_file_touches` Tabelle (file_path, touch_type, tool_name, session_id, timestamp)
- `services/file_touch_service.py` - Touch-Extraktion aus tool_use Bloecken, Pfad-Normalisierung, Heatmap-Aggregation, Risk-Radar-Berechnung
- `routes/analytics_routes.py` - `/api/analytics/file-heatmap/<project>` + `/api/analytics/risk-radar/<project>`
- `static/js/file-heatmap.js` - Heatmap-Tab UI mit Risk Radar Cards, sortierbare Tabelle, Filter, Trend-Chart
- `static/css/file-heatmap.css` - Styles mit Design-Tokens
- `scripts/backfill_file_touches.py` - Backfill: 29.238 Touches aus 267/351 Sessions extrahiert
- Neuer Tab "AI Heatmap" in project_detail.html
- `db_service.py` erweitert: `ensure_file_touch_schema()`
- Blueprint in `routes/__init__.py` registriert

### Sprint 10 - Urspruenglicher Plan

**Reihenfolge (Abhaengigkeiten beachten):**
1. DB-Schema: Neue `ai_file_touches` Tabelle (file_path, touch_type, ai_written, ai_touched, session_id)
2. Data Extraction: Write/Edit Tool-Calls aus JSONL parsen, Datei-Pfade extrahieren
3. Backfill: Bestehende Sessions re-analysieren (--with-file-touches)
4. API: `/api/analytics/file-heatmap/<project>` + `/api/analytics/risk-radar/<project>`
5. Heatmap UI: Treemap/Table in Projekt-Detail-Tab, farbcodiert nach Rework-Rate
6. Risk Radar: Top-3-Hotspots, Top-3-Fehlerkategorien, Trend-Visualisierung

**Modularer Aufbau (WICHTIG!):**
- `services/file_touch_service.py` - Datei-Touch-Extraktion und Analyse
- `routes/analytics_routes.py` - Heatmap + Risk-Radar API
- `static/js/file-heatmap.js` - Heatmap UI-Logik
- `static/css/file-heatmap.css` - Heatmap Styles
- `scripts/backfill_file_touches.py` - Backfill-Script
- `db_service.py` - nur `ensure_file_touch_schema()` hinzufuegen

---

## Session 2026-03-31 - AI Governance Roadmap (Sprint 9-15)

### Was wurde erledigt

**Komplette AI Governance Roadmap erstellt (7 Sprints, ~2700 Zeilen):**
- Sprint 9: Fehler-Kategorien + AI-Scope-Filter (outcome_reason, severity, ai_has_writes)
- Sprint 10: Per-File AI-Heatmap + Risiko-Radar (ai_file_touches, Hotspot-Warnungen)
- Sprint 11: Modell-Qualitaetsvergleich (mv_model_quality, Stack-Analyse, Empfehlungs-Engine)
- Sprint 12: Governance + Feedback-Loop (3-Stufen Policy, Regel-Generator, Wirkungs-Tracking)
- Sprint 13: Bidirektionaler LLM-Control (Recommendations, Tool-Control, Safe-Mode, Audit-Trail)
- Sprint 14: Sprint/Flow-Tracking + Soll/Ist (Sprint-Tasks, planned_value JSONB, Controlling)
- Sprint 15: Mehrsprachigkeit DE/EN (JSON+JS Ansatz, nach Governance-Sprints)

**Architektur-Analyse durchgefuehrt:**
- Bestehende Features auf Vollstaendigkeit geprueft (Quality Scoring 100%, Usage 95%, etc.)
- Bidirektionale Kommunikation analysiert (Ergebnis: Dashboard ist passiver Beobachter)
- Kompatibilitaet neue/bestehende Projekte geprueft (Backfill-Script noetig)
- Codex-Import bereits implementiert in session_import_multi.py

**UI/UX-Implementierungsdetails ergaenzt:**
- Alle 6 Sprints mit konkreten Template/CSS/JS Dateien
- 5 neue Templates, 5 neue CSS, 5 neue JS Dateien geplant
- 4 neue Sidebar-Eintraege (Sprints, Model Comparison, AI Governance, Recommendations)
- Design-Token-Konsistenz sichergestellt (CSS Custom Properties)

**Zusaetzliche Features eingearbeitet (aus Feedback-Schleifen):**
- Default-Filter pro Policy-Level
- Drill-down-Quicklinks in allen Tabellen
- Risiko-Radar Panel im Projekt-Detail
- Trend-Analyse (Sparklines)
- Wirkungs-Tracking fuer angewandte Regeln
- Recommendation-Objects mit Lebenszyklus
- Safe-Mode pro Policy (sandbox/controlled/critical)
- Sprint-Tasks mit planned_value JSONB + Task-Session-Verknuepfung
- Soll/Ist-Vergleich mit Ampel (gruen/gelb/rot)
- "Aktion ableiten"-Block bei roten Metriken
- sprint_task_notes fuer Plan-Aenderungshistorie
- Markdown-Backup-Strategie (DB + .md bleiben parallel)
- Optionale Erweiterungen: CI/CD-Gate, Issue-Sync, Webhooks, Prompt-Snippets

### Erstellte Dateien

| Datei | Zeilen |
|-------|--------|
| `sprints/10-roadmap-ai-governance.md` | 75 |
| `sprints/sprint-9-error-categories-ai-filter.md` | 324 |
| `sprints/sprint-10-file-heatmap.md` | 302 |
| `sprints/sprint-11-model-quality-comparison.md` | 289 |
| `sprints/sprint-12-governance-feedback-loop.md` | 388 |
| `sprints/sprint-13-bidirectional-llm-control.md` | 675 |
| `sprints/sprint-14-sprint-flow-tracking.md` | 720 |

### Architektur-Kette

```
Messen (9-10) → Bewerten (11) → Steuern (12-13) → Kontrollieren (14) → i18n (15)
```

---

## Session 2026-03-30 - Live Usage Monitor Rewrite + Usage Reports

### Was wurde erledigt

**Usage Monitor komplett neu gebaut:**
- Alter DB-basierter Monitor ersetzt durch Live-JSONL-Reader (`services/usage_live_service.py`)
- Terminal-Style UI inspiriert von Claude-Code-Usage-Monitor (github.com/Maciek-roboblog)
- Liest `~/.claude/projects/**/*.jsonl` direkt, kein DB-Sync noetig
- Progress Bars mit Emoji-Icons und Farbwechsel (gruen/gelb/rot bei 60%/85%)
- Billable Tokens korrekt getrennt (input+output, ohne cache)

**P90 Dynamic Limits (`services/usage_limits.py`):**
- Analysiert 8 Tage Historie in 5h-Bloecken, berechnet P90-Perzentil
- Plan-Dropdown entfernt, Limits passen sich automatisch an

**OpenTelemetry Receiver:**
- `services/otel_store.py` + `routes/otel_routes.py`
- Empfaengt OTLP protobuf+JSON auf `/v1/metrics`
- OTel-first, P90-fallback Architektur

**Usage Reports Seite (NEU):**
- Neue Seite `/usage-reports` mit Tages-/Wochen-/Monatsberichten
- 4 Chart.js Charts: Kosten-Verlauf, Token-Verteilung, Modell-Doughnut, Stunden-Aktivitaet
- 6 KPI-Cards: Gesamtkosten, Tokens, Messages, Sessions, Kosten/Tag, API Calls
- Detail-Tabelle mit allen Metriken pro Periode
- Preset-Filter: Heute, Diese Woche, 7 Tage, 30 Tage, Monat, Benutzerdefiniert

**Irrefuehrende Week-Daten entfernt:**
- "$1097 Current Week" aus Usage Monitor entfernt (war lokale Kostensumme ohne echtes Limit)
- Durch Link zu Usage Reports ersetzt

**README komplett ueberarbeitet:**
- "The Problem" Section oben mit Fokus auf Session-Management
- Usage Monitor Feature-Sektion, Screenshot, OTel-Anleitung

### Git Commits
```
e944593 feat: add usage reports page with daily/weekly/monthly charts, remove misleading week data from monitor
1b48da8 docs: rewrite problem section - focus on session management as core value
c52fd7d docs: add problem/solution section to README for immediate value proposition
8470b77 docs: remove 'coming soon' from session-pilot.com link
967f6d1 docs: clarify configurable port in README quick start sections
eec63f2 feat: live usage monitor with real-time JSONL parsing, P90 limits, and OpenTelemetry support
```

---

## Session 2026-03-29 - English UI, Usage Monitor, GitHub Launch, X Marketing

### Was wurde erledigt
- Komplette Englisch-Umstellung (17 Templates, 30+ JS, 16 Python Routes)
- Usage Monitor v1 (DB-basiert, per-Account Cards, Plan-Dropdown, Auto-Polling)
- Configurable External Links (Sidebar dynamisch)
- Cross-Platform Support (setup.sh Wizard, setup.ps1, Windows APPDATA)
- GitHub Launch: v1.0.0 Release, CONTRIBUTING.md, LICENSE, SECURITY.md, Dependabot
- session-pilot.com Website Update (Multi-LLM, WAVE a11y fixes)
- X/Twitter Launch-Thread (@joverdi)

### Git Commits
```
24bea7f docs: add SECURITY.md with vulnerability reporting policy
fe166c2 chore: enable Dependabot for pip dependency updates
af3dde7 chore: remove internal files from git tracking
390d28d docs: add MIT license
67dc94e docs: add CONTRIBUTING.md with development setup and PR guidelines
9c71923 feat: English UI, usage monitor, configurable external links, cross-platform setup
```

---

## Session 2026-03-28/29 (Abend/Nacht) - Quality + UI Sprint

### Was wurde erledigt
- Quality Pipeline (Issues #5-#7): detect_tags() konsolidiert, Pre-commit Hook
- Quality Dashboard (Issue #8): /quality Seite, Scan/Baseline Buttons
- Projekt-Detail: zweispaltig, Sessions-Tab, Git-Panel, Plans-Tab fixes
- UI: Stahlblau statt Cyan, neutrales Grau statt Lila, Prio-Icons
- README + GitHub: Code Quality Feature dokumentiert

---

## Session 2026-03-28 (Nacht) - Zentraler Fetch-Wrapper + CSS-Fix

### Was wurde erledigt

**Fetch-Wrapper `api.js`:**
- Neues Modul `static/js/api.js` als zentrale HTTP-Schicht
- ~85 rohe fetch()-Aufrufe in 24 JS-Dateien auf api.get/post/put/del umgestellt
- Automatisches JSON-Parsing, Content-Type-Header, Status-Check
- ApiError-Klasse mit status, body, message
- Convenience-Methoden: get, post, put, patch, del, request (raw fuer Downloads)
- Eingebunden in base.html vor base.js

**CSS-Fix:**
- `sessions-list.css` und `session-reviews.css` aus Git-History wiederhergestellt
- Waren in b0a5cd7 faelschlicherweise als "verwaist" geloescht worden
- Werden per @import in sessions2.css eingebunden

### Git Commits
```
(dieser Commit)
```

---

## Session 2026-03-28 (Abend) - Modal-Refactoring + Performance

### Was wurde erledigt

**Modal-Handling vereinheitlicht:**
- Generisches openModal(id)/closeModal(id) mit Modal-Stack in base.js
- Globaler Escape-Handler, delegierter Overlay-Click
- 5x gleichnamige closeModal() aufgeloest, 5 Escape-Handler entfernt
- ideasModal von style.display auf classList/modal-overlay umgestellt
- Duplizierte Lightbox aus index-ui.js entfernt

**Performance Projekt-Detail (60s -> 20ms):**
- /api/info aufgeteilt: Basis (4ms) sofort, teure Sections async via /api/info/slow
- git fetch nur on-demand (Refresh-Button), nicht beim Seitenaufruf
- count_lines_of_code: Weiche kleine/grosse Projekte (os.walk vs find+wc)
- Security-Scan Timeouts von 30-60s auf 10s reduziert

**Performance Dashboard (8-11s -> 5ms):**
- Background-Scan: Projekt-Scan laeuft async im Thread
- /api/data liefert sofort cached Daten, Scan startet beim App-Start
- scan_projects() parallelisiert via ThreadPoolExecutor (8 Workers)
- GitHub-API/Health-Checks aus Dashboard-Scan entfernt (nur Projekt-Detail)
- Flask threaded=True aktiviert

### Git Commits
```
24d61b0 perf: Dashboard /api/data von 8-11s auf 5ms optimiert
2271eb6 perf: Projekt-Detail von 60s auf 20ms optimiert
09a5914 refactor: Generisches Modal-System in base.js, Duplikate bereinigt
```

---

## Session 2026-03-28 (Nachmittag) - System Cleanup + Code Quality

### Was wurde erledigt

**Performance & Sync:**
- Session-Sync Timer deaktiviert (lief alle 20 Min, 485s pro Lauf)
- Hash-basierter Cache (.sync_hashes.json) - Sync jetzt <1s statt 485s
- Auto-Sync bei Sessions-Seitenaufruf mit 1h Cooldown
- JSONL-Import Escape-Fehler behoben (\u0000, \x00 in content_json)

**DB-Bereinigung:**
- messages-Tabelle von 11 GB auf 713 MB reduziert
- 4.4 Mio duplizierte Messages entfernt (Bug: DELETE vor INSERT fehlte)
- NoneType-Absicherung bei Session-INSERT

**System-Bereinigung:**
- 20 Docker Container gestoppt, ~300 GB Docker-Muell freigegeben
- Ollama, PCP, docker-mec-autostart deaktiviert

**Code Cleanup:**
- 4 verwaiste Dateien geloescht (context_tracker.py, dashboard.js, 2x CSS)
- 2 ungenutzte Funktionen entfernt
- session_import_utils.py: Shared Helpers extrahiert (parse_ts, sanitize_content_json)
- Python-Duplikate: _build_timesheet_filter(), _parse_search_output()
- JS-Duplikate: formatTokens/formatDate/formatDateTime nach base.js
- CSS-Duplikate: .empty-state nur noch in components.css
- @api_route Decorator: 22x try/except in 6 Route-Dateien ersetzt
- CLAUDE.md mit allen neuen Patterns aktualisiert

### Git Commits
```
7a7b473 refactor: Zentrales Error-Handling via @api_route Decorator
3d5cf9c refactor: Doppelte Funktionen konsolidiert
b0a5cd7 refactor: Verwaisten Code entfernt, Duplikate bereinigt
3692454 fix: NoneType-Absicherung bei Session-INSERT mit ON CONFLICT
81a39fd fix: Message-Duplikat-Bug und \u0000 Escape-Fehler behoben
1b866d8 fix: JSONL-Import Escape-Fehler bei content_json behoben
5db605e fix: Auto-Sync bei Sessions-Seitenaufruf statt manueller Trigger
13a78eb fix: Session-Sync durch Hash-Cache optimiert, Timer entfernt, fixes #5
```

---

## Session 2026-03-28 (Morgen) - Codebasis-Analyse + Quality Pipeline Planung

### Was wurde erledigt
- **Codebasis-Analyse** mit Serena: Alle Module, Schichten, Duplikationen identifiziert
- **Auto-Coder Quality Pipeline** konzipiert (DeRep, Scanner, Fix-Loop, Dashboard)
- **4 Sprint-Plaene erstellt** (Sprint 5-8)
- **Auto-Coder Sprint 5** implementiert: Package + 7 Quality Checks + CLI + Scanner
- **Serena** fuer project_dashboard aktiviert

### Git Commits
```
79df878 feat: Auto-Coder Quality Scanner implementiert (Sprint 5), fixes #4
abb3eb8 docs: Workflow fuer Gitea-Issues bei Aenderungen in CLAUDE.md
332759e docs: Session 2026-03-28 - Auto-Coder Quality Pipeline geplant
```

---

## Session 2026-03-27 (Nacht) - UI-Verbesserungen

### Was wurde erledigt
- **CSS-Variablen:** ~30 neue Design-Tokens definiert (Brand, Syntax, Status, Actions) + ~129 hardcoded Hex-Farben in 22 CSS-Dateien durch var(--...) ersetzt
- **Emoji → Lucide:** 12 JS-Dateien migriert (dashboard-table, -modals, -groups, -news, -actions, -ideas, documents, news, vorlagen, project-detail, sessions2, notifications). Python-Routen waren bereits umgestellt. `renderIcon()` Dual-Mode (Emoji+Lucide) vorhanden
- **Plans zugeordnet:** 3 unassigned Plans → proj_irtours. 0 unassigned verbleibend
- dashboard-misc.js Emojis bewusst beibehalten (dekorative Zitate)

---

## Session 2026-03-27 (Abend) - Sprint 2+3 + Tech-Debt Cleanup

### Was wurde erledigt

**Sprint 2 - Git-erweiterte Features:**
- Aktivitaets-Score (Commits 7d/30d, gewichteter Score, farbiger Dot)
- Branch-Zaehler + Branch-Liste in Detail
- Top 3 Contributors in Detail
- Env-Variablen aus .env.example als Badges
- Port-Konflikt-Erkennung mit Warn-Badge

**Sprint 3 - GitHub-Integration & Security:**
- GitHub-Service (Stars, Forks, Issues, PRs, Sprache via API, 5min Cache)
- CI/CD-Status (GitHub Actions letzter Workflow-Run)
- Health-Check-Service (HTTP-Checks auf Ports/URLs, 2min Cache)
- Security-Scanner (npm audit / pip-audit, On-Demand API)
- 5 GitHub-Repos erkannt (serena 22k, open-lovable 24k, Archon 13k)
- 27 Health-Checks aktiv
- Badges in Dashboard-Tabelle: GH, CI, Health
- Detail-Sections: GitHub, Health-Check, Security

**Tech-Debt Cleanup:**
- session_routes.py aufgeteilt (583→350 Zeilen, Reviews nach session_review_routes.py)
- sessions2.css aufgeteilt (823→7 Zeilen Import-Hub, 3 thematische Dateien)

### Git Commits
```
9f6e14e refactor: session_routes.py und sessions2.css aufgeteilt (Dateigroessen-Limits)
7568784 feat: Sprint 3 - GitHub-Integration, CI/CD-Status, Health-Checks, Security-Scanner
4156492 docs: next-session.md fuer Sprint 3 aktualisiert
69d552e feat: Sprint 2 - Activity-Score, Branches, Contributors, Env-Infos, Port-Konflikte
e308a5a docs: Session 2026-03-27 dokumentiert
```

### Neue Dateien
- `services/github_service.py` - GitHub API Service
- `services/health_check_service.py` - Health-Check Service
- `services/security_scanner.py` - Security Scanner
- `routes/session_review_routes.py` - Review-Routes (extrahiert)
- `routes/project_info_sections_s3.py` - Sprint 3 Detail-Sections
- `static/css/sessions-list.css` - Sessions-Liste CSS
- `static/css/session-reviews.css` - Reviews CSS

---

## Session 2026-03-27 (Nachmittag) - README Update + Sprint 1 Metadaten

### Was wurde erledigt
- README.md aktualisiert: Plans, Scheduled Tasks, Projekt-Tabs dokumentiert
- 3 neue Screenshots erstellt (06-project-detail, 07-plans, 08-scheduled-tasks)
- 13 neue API-Endpoints in README dokumentiert
- Auf GitHub gepusht (Remote `github` war bereits eingerichtet)
- Sprint-Plan erstellt fuer 14 neue Metadaten-Features (3 Sprints)
- **Sprint 1 implementiert:** Version, Lizenz, Repo-Size, LOC, Changelog
  - `metadata_extractor.py` (neue Datei): extract_version, detect_license, get_repo_size, count_lines_of_code, parse_changelog
  - Schema v2 -> v3 (project_detector.py)
  - Version-Badge in Dashboard-Tabelle (gruen, neben Projektname)
  - LOC/Lizenz/Size als Meta-Info in Beschreibungs-Spalte
  - Farbige Code-Statistik-Balken in Projekt-Detail (pro Sprache)
  - Performance-Fix: LOC/Size/Changelog nur on-demand in Detail-Ansicht (nicht bei /api/data)

### Git Commits
```
ea34b6f feat: Sprint 1 - Version, Lizenz, LOC, Repo-Size, Changelog Erkennung
d1f1450 docs: README mit Plans, Scheduled Tasks, Projekt-Tabs aktualisiert + Screenshots
```

---

## Session 2026-03-27 - Scheduled Tasks + Plans + Projekt-Tabs

### Was wurde erledigt
- Scheduled Tasks Seite (`/scheduled-tasks`) mit CRUD, Vorlagen, Cron-Vorschau
- 2 RemoteTrigger erstellt (Health Check 8:23, Backup Verification 2:17)
- Plans Seite (`/plans`) mit PostgreSQL-Import aus `~/.claude/plans/`
- Automatische Projekt-Erkennung (89% Trefferquote, 5-Pass-Strategie)
- Auto-Status aus Session-Abgleich (completed/active/draft)
- KPI-Cards: Umsetzung, Pipeline, Aktivitaet, Abdeckung
- Plan-Cards mit Status-Farben (blau=aktiv, gruen=erledigt, grau=draft)
- Projekt-Detail-Seite in Tabs umgebaut (Uebersicht, Sessions, Plans, Dokumente)
- Projekte-Menuepunkt in Sidebar
- Background Plans-Sync alle 10 Minuten
- Namens-Mapping Sessions<->Plans (project_dashboard vs project-dashboard)

### Git Commits
```
1184687 feat: Projekt-Detail Tabs + Projekte-Menuepunkt + CLAUDE.md
29a0d77 feat: Plans-Seite mit DB-Import, Session-Abgleich und Auto-Status
c944250 feat: Scheduled Tasks Seite + RemoteTrigger
```

### Issues
- Gitea: #1, #2, #3 (Closed)
- GitHub: web-werkstatt/session-pilot#1, #2, #3 (Closed)

---

## Session 2026-03-22 - Session-Detail UI + Review-System + Volltextsuche

### Was wurde erledigt
- AGENTS.md als Contributor Guide
- Session-Detail Redesign (Summary-Header, Sidebar, Timeline)
- Review-System mit Threads und Modal
- Session-Volltextsuche mit pg_trgm Index
- Ctrl+K Palette mit Session-Treffern
- marked.js Markdown-Rendering
- Cache-Busting fuer statische Dateien
- Diverse Session-Detail UI-Iterationen und Cleanup

---

## Session 2026-03-20 (Abend) - Enterprise SaaS Dashboard Redesign

### Was wurde erledigt
- Design-Token-System (100+ CSS Custom Properties) + Component Library
- Tailwind CSS CDN + Inter Font + Lucide SVG-Icons
- Alle 13 CSS-Dateien tokenisiert
- 6 neue CSS-Dateien
- index.html + dependencies.html von standalone zu base.html migriert
- 6 Templates: Inline-Styles extrahiert

---

## Session 2026-03-20 - AI Observability Suite

### Was wurde erledigt

**Bugfixes & Infrastruktur:**
- Sessions JSON.parse SyntaxError gefixt (HTML statt JSON bei DB-Fehler)
- DB Connection-Pool stabilisiert (thread-safe, 3 init / 10 max)
- claude-session-sync.service gefixt (EnvironmentFile + docker.service Dependency)
- Loading-Spinner auf allen Seiten ergaenzt (sessions, containers, analyse, vorlagen)
- Inline-JS aus 3 Templates extrahiert (session_detail, sessions, vorlagen)

**Auto-Discovery (5 AI-Tools):**
- Claude Code, OpenAI Codex CLI, Google Gemini CLI, GitHub Copilot CLI, Amazon Q
- 277 Sessions importiert (claude, claude1, minimax, account1, codex, gemini)

**Sprint 1-4:** AI Timesheets, Rework-Tracking, Context Effectiveness, Self-Service Scaffolding
**Kosten-System:** Cache-Tokens, 31 Modelle in DB, Admin-UI
**Settings-Seite:** SaaS-Pattern mit 3 Tabs

### Git Commits
```
8d88c5a Feature: AI Observability Suite (4 Sprints)
```

---

## Session 2026-03-20 (Abend) - Enterprise SaaS Dashboard Redesign

### Was wurde erledigt

**Phase 0-1: Foundation + Layout**
- design-tokens.css (100+ CSS Custom Properties, shadcn/ui-inspiriert)
- components.css (Buttons, Stats, Filter, Badges, Status, Toast, Dropdown, Cards)
- Tailwind CSS CDN + Inter Font + Lucide SVG-Icons (alle Emojis ersetzt)
- layout.css, base.css komplett tokenisiert
- Focus-visible Ringe auf alle interaktiven Elemente

**Phase 2-3: Table, Modals, Container**
- table.css, modals.css tokenisiert
- Container-Seite: Inline-CSS extrahiert, Stat-Cards, Filter-Pills, Status-Dots

**Phase 4: Dashboard Index (Hoch-Risiko)**
- index.html von standalone zu extends base.html migriert
- Duplizierte Sidebar/Topbar entfernt, alle 12+ JS-Dateien laden korrekt

**Phase 5-7: Sessions, News, Vorlagen, Rest**
- sessions.css neu (3 Templates), news.css, vorlagen.css, containers.css
- timesheets.css, project-detail.css, documents.css, settings.css, scaffold.css, widgets.css tokenisiert

**Phase 8: Dependencies (Hoch-Risiko)**
- dependencies.html von standalone (1429 Zeilen) zu extends base.html migriert
- CSS + JS in separate Dateien extrahiert

**Phase 9: Polish + UX**
- Tailwind .container Konflikt gefixt (corePlugins: container: false)
- Projekt-Zeilen klickbar (navigiert zu Projekt-Detail)
- Info-Icon nach rechts in Aktionen-Spalte verschoben
- Filter-Bar: 10+ Buttons durch Gruppen-Dropdown ersetzt
- Button/Dropdown Umbruch-Bug gefixt (display: inline-flex)
- Sessions-Tabelle: Spaltenbreiten optimiert
- Modal: max-width 700px -> 900px + 90vw
- Beziehungen-Tab im Edit-Modal: Formular-Styling gefixt

### Git Commits
```
(noch nicht committed)
```

---

## Session 2026-03-17 (Abend) - Technische Schulden + 4 Features

### Technische Schulden (alle erledigt)
- **dashboard.css** (1012 Zeilen) in 5 thematische Dateien aufgeteilt: base.css, layout.css, table.css, modals.css, features.css
- **project_routes.py** (534 Zeilen) aufgeteilt: /api/info -> project_info_routes.py (281 Zeilen)
- **base.html** (391 Zeilen) -> 132 Zeilen (JS nach static/js/base.js extrahiert)
- **project_detail.html** (384 Zeilen) -> 286 Zeilen (CSS nach project-detail.css)
- **dashboard.js** (1627 Zeilen) in 10 Module aufgeteilt (max 316 Zeilen pro Datei)
- **index.html** (575 Zeilen) -> 256 Zeilen (Modals in partials/, JS in index-ui.js)
- **Pre-Commit Hook** installiert: Dateigroessen-Limits + Secrets-Erkennung
- **Docker-Compose** end-to-end getestet (PostgreSQL + Dashboard)

### Neue Features
1. Container-Aktionen - Start/Stop/Restart + Logs-Modal
2. Session-Analyse (/sessions/analysis) - Token-Kosten, Stunden/Wochentag-Verteilung
3. Git-Aktionen - Commit/Push/Pull Panel in Projekt-Detailseite
4. Projekt-Archivierung - Archivieren/Wiederherstellen via Kontextmenue

### Git Commits
```
112455c Refactoring: dashboard.js + index.html aufgeteilt (Pre-Commit clean)
ab5170f Feature: Projekt-Archivierung mit Filter-Toggle
feb078f Feature: Git-Aktionen (Commit/Push/Pull) aus Projekt-Detail
13760c1 Features: Container-Aktionen + Session-Analyse + base.js Extraktion
59510ff Technische Schulden: CSS + Routes aufgeteilt, Pre-Commit Hook
```
