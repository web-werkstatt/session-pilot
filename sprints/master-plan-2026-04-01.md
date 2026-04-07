# Master Sprint Plan v0.3

Stand: 2026-04-05 (Session-Update)

## Rollenmodell

| Rolle | Verantwortung |
|-------|---------------|
| Joseph | Produkt, Architektur, Prioritaeten, Abnahme |
| Kontrollsystem (Prompter) | Specs, Pruefregeln, Audit-Logik |
| Claude Code | Executor im Repo (Patches, Refactors, Tests), austauschbar |

---

## Current State

Vier Saeulen sind konzipiert, zwei davon bereits operativ:

```
Messen          Auditieren        Bewerten          Steuern           Copilot
(Observability) (Audit-System)    (Quality+Gov.)    (LLM-Commands)    (Chat+Workflow)
  [DONE]          [DONE v1]         [DONE B+C]        [DONE D]          [DONE]
```

- **Observability** steht komplett (Timesheets, Rework, Context, Scaffolding).
- **Audit** ist als Feature real benutzbar (API + UI + Persistenz + LLM-Evidence).
- **Quality** Scanner MVP laeuft (Score + Issues pro Projekt, API + UI).
- **Governance** Light informative Ampel (green/yellow/red + Reasons, Policy-Stufen).
- **LLM Commands** Hub mit 3 Start-Commands, Persistenz, Markdown-Rendering.
- **Copilot** Chat mit Perplexity, Thread-Historie, Plan-Bindung.
- **Plan-Workflow** Micro-Ebene mit Ist/Soll/Next, Signal-Integration, Copilot-Link.
- **Drag & Drop Board** Kanban-Ansicht fuer Plans mit 8 Workflow-Spalten, HTML5 D&D, API-Sync.
- **Plan-Handoff** Generator fuer standardisierte LLM-Executor-Uebergabe (YAML-Frontmatter + 7 Sektionen).
- **Section-Board** DB-first Level-2-Cards (plan_sections) mit Copilot-Chat pro Section auf /copilot?plan_id=X.
- **Handoff-Service** Zentraler project_handoff_service.py, projektbezogene handoff-<plan_id>.md Dateien, LLM Command handoff-status.
- **AI Governance Analytics (Sprints 9-11)** Fehler-Kategorien + AI-Scope-Filter, Per-File Heatmap + Risk-Radar, Modell-Qualitaetsvergleich + Empfehlungs-Engine (Status-Korrektur 2026-04-07, siehe "AI Governance Analytics"-Block).
- **Marker-Driven Copilot (Sprint 17)** Marker-Block in `handoff.md` als fuehrender Arbeitszustand, `/copilot?plan_id=X` rendert Marker als Cards, Drag&Drop schreibt Status zurueck, `marker-context.md` als expliziter Chat-Kontext (Reality-Check 2026-04-07: faktisch DONE durch P2/P3/P-E3).

---

## Done

### AI Observability (Sprints 1-4)

| Sprint | Feature | Status |
|--------|---------|--------|
| 1 | AI Timesheets & Nutzungsanalyse | DONE |
| 2 | Rework-Tracking fuer AI-Code | DONE |
| 3 | Context Effectiveness / CLAUDE.md | DONE |
| 4 | Self-Service Scaffolding | DONE |

Ergebnis: Mess- und Beobachtungsbasis fuer alle AI-Sessions steht.
277+ Sessions, 5 AI-Tools, Token-/Duration-Tracking, Projekt-Zuordnung.

### Audit-System (ausserhalb der alten Roadmaps)

| Komponente | Was | Status |
|------------|-----|--------|
| Audit Core v0.1 | Spec/Requirement/AuditResult/AuditResponse Modelle, regelbasierte Bewertung | DONE |
| LLM Analyzer | Opt-in Perplexity-Review mit Gating (per-Requirement + global) | DONE |
| Evidence Persistence | evidence.llm_review + evidence.llm_review_error als JSONB | DONE |
| Integration v1 | POST /api/audits/run, GET by run_id, GET latest-by-spec, UI mit Trigger/Header/Requirements/LLM-Badges | DONE |

Ergebnis: Audit ist end-to-end nutzbar. Ein Benutzer kann einen Audit starten,
das Ergebnis inspizieren und persistierte Runs spaeter wieder abrufen.
10 Abnahmetests gruen, keine bestehenden Tests gebrochen.

---

## Open Blocks

### Quality Pipeline (historisch Sprints 5-8)

Code-Qualitaet systematisch messen und verbessern. Scanner, Fixer, Score pro Projekt.
Bisher: Architektur und Checks-Module geplant (auto_coder/), kein Code.

### AI Governance Analytics (historisch Sprints 9-14)

**Status-Korrektur 2026-04-07 (Sprint QT):** Sprint 9, 10 und 11 sind
entgegen der frueheren Einschaetzung substanziell implementiert. Der
Masterplan-Eintrag "Roadmap komplett, kein Code" war nicht mehr korrekt.

| Sprint | Thema | Belegter Code-Stand | Status |
|--------|-------|---------------------|--------|
| 9 | Fehler-Kategorien + AI-Scope-Filter | `services/ai_scope_service.py`, `routes/session_filter_routes.py` (4 Endpoints: outcome-reasons, filters, outcome-detail, scope-stats), `scripts/backfill_ai_flags.py`, AI-Flag-Extraktion in allen Importern unter `services/importers/` | DONE |
| 10 | Per-File Heatmap | `services/file_touch_service.py` (386 Zeilen, heatmap + risk-radar), `routes/analytics_routes.py` (`/api/analytics/file-heatmap/<project>`, `/api/analytics/risk-radar/<project>`), `static/js/file-heatmap.js`, `static/css/file-heatmap.css`, in `templates/project_detail.html` integriert | DONE |
| 11 | Modell-Qualitaetsvergleich | `services/model_recommendation.py` (437 Zeilen, Quality-Score, Stack-Analyse, Empfehlungs-Engine), `routes/model_comparison_routes.py` (Page + 4 API-Endpoints: model-comparison, model-by-stack, model-trend, model-recommendation), `templates/model_comparison.html` | DONE |
| 12 | Governance Feedback-Loop | nur Light-Version als Sprint C abgeschlossen | Voll-Version offen |
| 13 | Bidirektionaler LLM-Control | nur MVP als Sprint D abgeschlossen | Voll-Version offen |
| 14 | Sprint-Flow-Tracking | kein Code gesichtet | offen |
| 17 | Marker-Driven Copilot Orchestration | `services/copilot_marker_format.py` (Parser+Schema), `services/copilot_marker_service.py` (11 Funktionen), `routes/copilot_marker_routes.py` (9 Endpoints), `templates/copilot_board.html` + `static/js/copilot_board.js` + `static/js/copilot-board-panel.js` (Marker-Cards, Drag&Drop-Writeback, Chat-Kontext via marker-context.md) - Reality-Check 2026-04-07 | DONE (Folge: defensive Parser-Fehler-UX, siehe sprint-17-Plan) |

**Nicht geprueft:** vollstaendige Akzeptanzkriterien-Abdeckung pro Sprint
(z.B. alle Default-Filter pro Policy-Level aus Sprint 9.7, Trend-Analyse
aus Sprint 11.6). Die Code-Module und Endpoints entsprechen aber klar
dem Sprint-Scope, die Einordnung als "kein Code" war falsch.

### Audit-Weiterentwicklung

Audit v1 ist funktional, aber isoliert. Offene Verbindungen:
- Audit kennt noch keine Quality-Scores (Scanner-Ergebnisse als input_facts).
- Audit kennt noch keine Governance-Policies (kein Gate-Endpoint).
- Kein automatischer Trigger (nur manuell via UI oder API).

### Data Persistence Consolidation

Das Repo nutzt aktuell parallel DB, Root-JSON-Dateien und Markdown-Artefakte.
Fuer kleine Konfig- und Seed-Faelle ist das akzeptabel, fuer operative Produktdaten aber zunehmend zu teuer.

Neuer geplanter Architekturpfad:
- Sprint `QS` legt die DB-first Zielarchitektur fuer operative Zustandsdaten fest
- Root-JSON-Stores wie Notifications, Favorites, Relations, Ideas und Settings sollen schrittweise in die DB wandern
- Markdown-Artefakte wie `next-session.md`, `handoff.md` und Sprint-Plaene bleiben bewusst dateibasiert, aber nicht als einzige schwer abfragbare Runtime-Wahrheit
- Marker-Runtime-State wird als eigener Migrationspfad nach den einfachen JSON-Stores behandelt

Referenz:
- `sprints/sprint-qs-db-first-state-consolidation.md`

---

## Completed Sprints (diese Session)

### Sprint SB — Session-Marker-Binding hart — DONE (2026-04-07)

**Ziel:** Sessions sollen ihre Marker-Zugehoerigkeit explizit in der DB tragen, statt nur ueber `marker.last_session` aufgeloest zu werden (1:1, nur letzte Session pro Marker findbar).

**Umgesetzt:**
- Schema: `sessions.marker_id VARCHAR(120)`, `sessions.marker_handoff_path TEXT`, Index `idx_sessions_marker_id` via neuer `db_service.ensure_session_marker_schema()` (idempotent, lazy lock).
- Backfill: `scripts/backfill_session_marker_id.py` scannt alle Projektordner unter `PROJECTS_DIR`, liest jede `handoff.md` ueber `parse_markers()` und stempelt fuer jedes nicht-leere `marker.last_session` die `sessions.marker_id` (nur wenn NULL → idempotent). Erster Lauf: 7 Sessions in `project_dashboard` aktualisiert. Zweiter Lauf: 0 Updates, 7 already_set.
- Post-Sync-Hook: `_stamp_marker_context_after_sync()` in `services/session_import.py`. Liest pro Projekt `marker-context.md` (nur `- marker_id:`-Zeile), uebernimmt mtime und stempelt alle Sessions mit `started_at >= mtime` und `marker_id IS NULL`. Aufruf am Ende von `sync_all()`. Fehler je Projekt brechen den Sync nicht ab. Deckt alle 5 Importer (claude/codex/gemini/opencode/kilo) ohne Modifikation ab.
- Read-Path: `routes/session_routes.py:_resolve_session_marker(project_name, session_uuid, stored_marker_id)` bevorzugt den DB-`marker_id` und ruft `get_marker_context()` gezielt; faellt bei NULL auf den bisherigen `get_marker_by_last_session()`-Lookup zurueck. SELECT war bereits `*`, neue Spalten kommen automatisch mit. `ensure_session_marker_schema()` wird in `_api_session_detail_inner` aufgerufen.
- Neue Route: `GET /api/markers/<marker_id>/sessions?project=...` in `routes/copilot_marker_routes.py`, liefert alle verknuepften Sessions sortiert nach `started_at DESC`. Verlauf statt nur "letzte".

**Akzeptanzkriterien (7/7):**
- AC1 Schema-Spalten + Index ✓ (verifiziert ueber Service-Layer)
- AC2 Backfill idempotent ✓ (zweiter Lauf 0 Updates)
- AC3 Post-Sync-Hook funktional ✓ (Code-Pfad identisch zum Backfill, defensiv)
- AC4 Read-Path nutzt DB-marker_id zuerst ✓ (`/api/sessions/032e4f9f-...` liefert `marker_id: 141`, `marker.titel: "Sprint-Plan: Projekt-Metadaten Erweiterung"`)
- AC5 `/api/markers/141/sessions?project=project_dashboard` liefert 1 Session ✓
- AC6 Marker-Lookup gezielt statt Iteration ✓
- AC7 End-to-End auf Live-DB ✓

**Geaenderte Dateien:**
- `services/db_service.py` (+ ensure_session_marker_schema)
- `services/session_import.py` (+ _stamp_marker_context_after_sync, sync_all-Hook)
- `routes/session_routes.py` (+ _resolve_session_marker, neuer Aufruf)
- `routes/copilot_marker_routes.py` (+ /api/markers/<id>/sessions)
- `scripts/backfill_session_marker_id.py` (NEU)
- `sprints/sprint-sb-session-marker-binding.md` (NEU - Sprint-Plan)
- `CLAUDE.md` (Patterns-Eintrag)
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Gitea-Issue:** #20 (refs)

**Commit-Hash:** wird beim Commit vergeben

---

### Sprint 17 — Marker-Driven Copilot Orchestration — DONE (Reality-Check 2026-04-07)

**Ziel:** Copilot-Board von DB-zentrierten `plan_sections` auf einen Markdown-gefuehrten Marker-Workflow umstellen.

**Befund:** Alle 5 Arbeitspakete (A-E) und alle 3 Phasen waren bei Pruefung bereits vollstaendig im Code, vermutlich umgesetzt durch die fruehen Sprints P2/P3/P-E3. Sprint-17-Plan war zum Zeitpunkt seiner Erstellung (2026-04-03) bereits ueberholt.

**Belegter Code-Stand:**
- `services/copilot_marker_format.py` - Parser, START/END-Block, Marker-Dataclass mit Validierung, YAML-Frontmatter `state_format: copilot_markers_v1`
- `services/copilot_marker_service.py` (280 Zeilen, 11 Funktionen) - read/list/update/activate/close/execution-rating/backfill
- `services/copilot_marker_import_flow.py` - Sprint→Marker Konverter
- `routes/copilot_marker_routes.py` (219 Zeilen, eigener Blueprint) - 9 Endpoints inkl. PATCH status, PATCH fields, POST activate, POST close, GET/POST execution-rating, POST sprint-to-markers
- `templates/copilot_board.html` (299 Zeilen) - 4-Spalten-Board, Panel mit allen Marker-Feldern (goal, next_step, prompt, checks, risk, last_session, gate, execution_summary)
- `static/js/copilot_board.js` (500 Zeilen) - Marker-Render, Drag&Drop schreibt PATCH /api/copilot/markers/<id>/status, Empty-State
- `static/js/copilot-board-panel.js` - openSectionPanel, Tab-Persistenz via `_activePanelTab`
- `services/project_handoff_service.py` - `build_handoff_markdown` schreibt Marker-Block, behaelt vorhandene Marker-Felder beim Re-Build
- `marker-context.md` - aktiver Marker-Kontext fuer Chat (von `activate_marker` geschrieben, von `/api/copilot/chat` per `context_path` gelesen)

**Akzeptanzkriterien:** Alle 7 erfuellt. Tab-Persistenz verifiziert in `static/js/copilot-board-panel.js:30`.

**Offener Folge-Punkt:** Defensive Parser-Fehler-UX (Risiko 1 aus dem Sprint-17-Plan) - bei JSONDecodeError oder Validation-Fehler in einem Marker liefert die API 500, das Board zeigt nur generisches "Fehler beim Laden". Soll in einen kuenftigen Bugfix-Sprint als Mini-Task wandern.

**Geaenderte Dateien (nur Doku):**
- `sprints/sprint-17-marker-driven-copilot-orchestration.md` (Status auf DONE + Reality-Check-Block)
- `sprints/master-plan-2026-04-01.md` (Sprint 17 aus "Open / Next" entfernt, in AI-Governance-Tabelle und Completed Sprints eingetragen)
- `next-session.md`

**Commit-Hash:** `n/a`

### Sprint QT — Plan-Reality-Sync — DONE (2026-04-07)

**Ziel:** Master-Plan, Gitea-Issues und Repo-Stand in einen konsistenten Zustand bringen, bevor weitere Feature-Sprints gestartet werden.

**Umgesetzt:**
- **Arbeitspaket A - Master-Plan Reality-Check:**
  - Stichprobenhafte Pruefung von Sprint 9/10/11 Artefakten im Code bestaetigt: alle drei Sprints sind substanziell implementiert
  - Sprint 9 (ai_scope_service.py + session_filter_routes.py + backfill_ai_flags.py) als DONE markiert
  - Sprint 10 (file_touch_service.py + analytics_routes.py + file-heatmap.js/css) als DONE markiert
  - Sprint 11 (model_recommendation.py + model_comparison_routes.py + model_comparison.html) als DONE markiert
  - Master-Plan "AI Governance Analytics"-Block mit Status-Tabelle ersetzt
  - Historische-Referenz-Tabelle korrigiert (Sprint 9/10/11 -> DONE)
  - Current-State-Block um neue Saeule ergaenzt
- **Arbeitspaket B - Gitea-Issue-Triage:**
  - 5 offene Issues gepruefte und mit Commit-Referenz geschlossen: #13 (Audit-Integration), #14 (Sprint P3 Prompt-Chain, Commit afd218c), #15 (P2-Branch-Isolierung, Commits 8f8d08c + 6faf2c8), #16 (Sprint P2 marker board, Commit 8f8d08c), #18 (Copilot CSS fix, Commit 5bcb2af)
- **Arbeitspaket C - Marker-Context:** DONE - User-Entscheidung: Testmarker `test-cockpit-2026-04-05` bleibt unveraendert
- **Arbeitspaket D - next-session.md Follow-ups:**
  - Session-Binding-Schaerfung nach Analyse als eigener kuenftiger Mini-Sprint vertagt (erfordert Schema-Aenderung)
  - Cockpit-Activity-Card Anpassung: obsolet, da keine separate Card existiert (Activity-Tab ist bereits das neue Format)
  - Session 2026-04-06 archiviert
- **Arbeitspaket E - Dokumentation:**
  - Neue Dateien `sprints/audit-2026-04-07.md` (Prueffbericht) und `sprints/sprint-qt-plan-reality-sync.md` (dieser Plan)
  - `next-session.md` auf Sprint QT Stand
  - `next-session-archiv.md` ergaenzt

**Geaenderte Dateien:**
- `sprints/audit-2026-04-07.md` (neu)
- `sprints/sprint-qt-plan-reality-sync.md` (neu)
- `sprints/master-plan-2026-04-01.md`
- `next-session.md`
- `next-session-archiv.md`

**Commit-Hash:** `n/a` (wird beim Commit vergeben)

### Hotfix DW — Dashboard Widgets Initial Load

**Ziel:** Den Laufzeitfehler `Uncaught ReferenceError: loadWidgets is not defined` beim direkten Oeffnen des Overview-/Widgets-Tabs beheben.

**Umgesetzt:**
- Script-Reihenfolge in `templates/index.html` korrigiert, sodass `static/js/widgets.js` vor `static/js/dashboard-core.js` geladen wird
- `showTab()` in `static/js/dashboard-core.js` zusaetzlich gegen fehlende `loadWidgets`-Initialisierung abgesichert
- Damit bricht der Initial-Render von `/?tab=widgets` nicht mehr ab, auch wenn die Widgets-Funktion unerwartet nicht verfuegbar waere

**Geaenderte Dateien:**
- `templates/index.html`
- `static/js/dashboard-core.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix DX — Persistente Projekt-Navigation

**Ziel:** Das zuletzt geoeffnete Projekt beim Seitenwechsel ueber globale Navigation erhalten, konkret fuer den Wechsel `Project -> Activity -> Projects`.

**Umgesetzt:**
- Den primären Sidebar-Link `Projects` mit einer expliziten Projekt-Navigation-Markierung versehen
- `static/js/base.js` erweitert, sodass der Link ausserhalb des Root-Dashboards auf `/project/<active-project>` zeigt, wenn ein aktiver Projektkontext in `localStorage` vorhanden ist
- Auf der Root-Seite bleibt das bisherige Verhalten `/?tab=projects` unveraendert

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix DY — Planning Detail Panel Scrollbarkeit

**Ziel:** Lange Task-/Detail-Cards im `Planning`-Tab einer Projektseite beim Scrollen vollstaendig sichtbar halten.

**Umgesetzt:**
- Das sticky Detailpanel in `static/css/project-planning.css` um `max-height` relativ zum Viewport erweitert
- Dem Panel einen eigenen `overflow-y: auto` Scrollbereich gegeben
- Dadurch bleibt die rechte Detailkarte sichtbar, ohne unter dem unteren Viewport-Rand abgeschnitten zu wirken

**Geaenderte Dateien:**
- `static/css/project-planning.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix DZ — Projekt-Detail Script-Reihenfolge

**Ziel:** Den Laufzeitfehler `Uncaught ReferenceError: loadRiskRadarPanel is not defined` auf der Projekt-Detailseite beseitigen.

**Umgesetzt:**
- `static/js/file-heatmap.js` in `templates/project_detail.html` vor `static/js/project-detail.js` verschoben
- Den Initialaufruf in `static/js/project-detail.js` zusaetzlich mit `typeof loadRiskRadarPanel === 'function'` abgesichert
- Damit bricht die Projektseite auch bei spaeteren Script-Aenderungen nicht mehr an dieser Stelle ab

**Geaenderte Dateien:**
- `templates/project_detail.html`
- `static/js/project-detail.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix EA — Direktes Oeffnen verlinkter Planning-Sessions

**Ziel:** Verlinkte Sessions im Projekt-Tab `Planning` nicht nur selektieren, sondern direkt oeffnen koennen.

**Umgesetzt:**
- Session-Zeilen im Planning-Detailbereich um eine explizite `Open`-Aktion erweitert
- Bestehendes Verhalten bleibt erhalten: Klick auf die Zeile selektiert weiter den Session-Knoten fuer das rechte Detailpanel
- `Open` navigiert direkt auf `/sessions/<uuid>`

**Geaenderte Dateien:**
- `static/js/project-planning.js`
- `static/css/project-planning.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix EB — Session-Zeile statt Extra-Button

**Ziel:** Die UX fuer verlinkte Sessions im Projekt-Tab `Planning` vereinfachen und den unnoetigen Extra-Button entfernen.

**Umgesetzt:**
- Den separaten `Open`-Button wieder entfernt
- Die komplette Session-Zeile im Planning-Detailbereich als direkten Link auf `/sessions/<uuid>` umgesetzt
- Damit ist das Session-Verhalten klarer und konsistent mit der Erwartung, dass ein Session-Eintrag direkt oeffnet

**Geaenderte Dateien:**
- `static/js/project-planning.js`
- `static/css/project-planning.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix EC — Session Detail Zurueck-Navigation

**Ziel:** Auf der Session-Detailseite statt eines starren `Activity`-Links eine echte Ruecknavigation bereitstellen.

**Umgesetzt:**
- Breadcrumb und Header-Button auf `Zurueck` umgestellt
- Neue Funktion `goSessionBack()` eingebaut
- Bei passendem internem Referrer wird `history.back()` genutzt, sonst faellt die Navigation auf `/sessions` zurueck

**Geaenderte Dateien:**
- `templates/session_detail.html`
- `static/js/session-detail.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Refactoring ED — Modulare Session-Importer

**Ziel:** Den weiter anwachsenden Multi-Tool-Session-Import von einer Sammeldatei in eine modulare Struktur ueberfuehren, damit neue Tools wie OpenCode und Kilo sauber pro Quelle gepflegt werden koennen.

**Umgesetzt:**
- Neues Paket `services/importers/` eingefuehrt und die Importlogik pro Tool getrennt in `codex_importer.py`, `gemini_importer.py`, `opencode_importer.py` und `kilo_importer.py` abgelegt
- Gemeinsame DB-/Projekt-Helfer in `services/importers/common.py` gebuendelt
- `services/session_import.py` auf die neue Struktur umgestellt, sodass dort nur noch Discovery, Hash-Cache und Sync-Orchestrierung verbleiben
- `services/session_import_multi.py` auf einen schlanken Kompatibilitaets-Wrapper reduziert, damit alte Importe nicht brechen
- Projektnamen-Extraktion fuer `opencode:`- und `kilo:`-Praefixe vervollstaendigt

**Geaenderte Dateien:**
- `services/session_import.py`
- `services/session_import_multi.py`
- `services/importers/__init__.py`
- `services/importers/common.py`
- `services/importers/codex_importer.py`
- `services/importers/gemini_importer.py`
- `services/importers/opencode_importer.py`
- `services/importers/kilo_importer.py`
- `tests/test_session_import.py`
- `CLAUDE.md`
- `CONTRIBUTING.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix EE — Session-ID-Validierung und OpenCode-Message-Pfad

**Ziel:** Die neu importierten `kilo`- und `opencode`-Sessions auch in Detailansicht und Export wirklich benutzbar machen und einen gefundenen OpenCode-Importfehler im Live-Test beheben.

**Umgesetzt:**
- Session-UUID-Validierung erweitert, sodass neben klassischen UUIDs auch Formate wie `sess-123` und `ses_...` akzeptiert werden
- Damit funktionieren Detailrouten fuer Kilo/OpenCode-Sessions, die alphanumerische IDs mit Unterstrich verwenden
- Beim OpenCode-Live-Test einen Pfadfehler im Importer gefunden und korrigiert: Messages werden jetzt relativ zum echten `storage/`-Root statt relativ zu `storage/session/` gesucht

**Geaenderte Dateien:**
- `services/session_validation_service.py`
- `services/importers/opencode_importer.py`
- `services/session_import.py`
- `tests/test_session_validation_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix ED — Session Account Badge Contrast

**Ziel:** `Claude` und `Codex` in Session-Tabellen visuell klarer unterscheiden.

**Umgesetzt:**
- Account-Badges in `static/css/sessions-list.css` um explizite Border-Farben erweitert
- `Claude` bleibt blau
- `Codex` auf einen deutlich warmen Orange-/Amber-Ton umgestellt
- Dadurch sind die Accounts sowohl in `Activity` als auch in projektbezogenen Session-Listen schneller erkennbar

**Geaenderte Dateien:**
- `static/css/sessions-list.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Hotfix EE — Konfigurierbare Account-/Tool-Badges

**Ziel:** Neue oder seltene Tools wie `hermes`, `opencode`, `kilo`, `copilot` oder `amazonq` ohne weitere CSS-Patches im Dashboard visuell pflegbar machen.

**Umgesetzt:**
- Persistentes Settings-Feld `account_badge_styles` eingefuehrt
- Default-Styles fuer bestehende und weitere bekannte Tools/Accounts hinterlegt, inklusive `hermes`
- Globale Settings per Context-Processor ins Base-Template injiziert
- Badge-Styling in Session-Listen, Projekt-Sessionliste, Session-Detail und Settings-Accountcards auf Settings-basierte Inline-Styles umgestellt
- In `Settings -> General` eine editierbare Tabelle fuer Key, Background, Text und Border ergaenzt

**Geaenderte Dateien:**
- `services/dashboard_settings_service.py`
- `app.py`
- `templates/base.html`
- `templates/settings.html`
- `static/js/base.js`
- `static/js/settings.js`
- `static/js/sessions2.js`
- `static/js/project-detail.js`
- `static/js/session-detail.js`
- `static/css/settings.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `n/a`

### Sprint QX — Dashboard Self-Discovery konfigurierbar

**Ziel:** `project_dashboard` nicht mehr hart aus der Projekt-Discovery ausfiltern, sondern das Verhalten direkt im Dashboard unter Settings steuerbar machen.

**Umgesetzt:**
- `services/dashboard_settings_service.py` als persistentes Settings-Layer angelegt
- Neue API `GET/POST /api/settings/general` fuer Dashboard-Basisoptionen
- `templates/settings.html`, `static/js/settings.js` und `static/css/settings.css` um einen General-Tab mit Toggle erweitert
- `services/project_scanner.py` und `routes/project_routes.py` lesen die Option jetzt dynamisch aus dem Settings-Layer
- Settings werden in `dashboard_settings.json` gespeichert und nutzen Env-Werte nur noch als Default-Fallback
- Default bleibt sichtbar, damit `project_dashboard` standardmaessig in Scan, Suche und Refresh enthalten ist

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

**Commit-Hash:** `61be781`

### Sprint PX — Hashtag-First Markdown Routine — MODULARER REPO-ABSCHLUSS

**Ziel:** Den verbleibenden Copilot-/Markdown-Block so modularisieren, dass die Repo-Regeln fuer kleine Dateien eingehalten werden und der gesamte PX-Stand sauber commitbar bleibt.

**Umgesetzt:**
- Marker-Endpoints aus `routes/copilot_routes.py` in ein eigenes Blueprint `routes/copilot_marker_routes.py` verschoben und in `routes/__init__.py` registriert
- `services/copilot_marker_service.py` in kleinere Verantwortlichkeiten aufgeteilt: Format/Parser in `services/copilot_marker_format.py`, Import-/Generator-Flow in `services/copilot_marker_import_flow.py`, Runtime-Fassade im bestehenden Service
- Das Copilot-Board-Frontend in `static/js/copilot-board-shared.js`, `static/js/copilot_board.js` und `static/js/copilot-board-panel.js` zerlegt; `templates/copilot_board.html` bindet die neuen Assets jetzt explizit ein
- Die grossen Testmonolithe `tests/test_copilot.py` und `tests/test_copilot_marker_service.py` in mehrere kleinere Suites zerlegt, damit jede geaenderte Datei unter der 500-Zeilen-Grenze bleibt
- Den modularisierten PX-Block lokal geprueft mit Python-Syntaxcheck, JS-Syntaxcheck und einer gebuendelten Pytest-Suite ueber Copilot-, Marker- und Markdown-Routine-Tests

**Geaenderte Dateien:**
- `routes/__init__.py`
- `routes/copilot_routes.py`
- `routes/copilot_marker_routes.py`
- `services/copilot_marker_service.py`
- `services/copilot_marker_format.py`
- `services/copilot_marker_import_flow.py`
- `templates/copilot_board.html`
- `static/js/copilot-board-shared.js`
- `static/js/copilot_board.js`
- `static/js/copilot-board-panel.js`
- `tests/test_copilot_core.py`
- `tests/test_copilot_marker_activation_routes.py`
- `tests/test_copilot_marker_api_routes.py`
- `tests/test_copilot_marker_service_core.py`
- `tests/test_copilot_marker_service_flow.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `bbaf112`

### Sprint QY — Plans-Detail gegen Legacy-DB-Schema gehaertet

**Ziel:** Den HTTP-500 beim Oeffnen von Plan-Details auf Systemen mit aelterer `specs`-Tabelle beheben.

**Umgesetzt:**
- Root Cause im Live-Betrieb identifiziert: `/api/plans/<id>` scheiterte in `ensure_plan_structure_schema()` beim Index auf `specs(sprint_plan_id, updated_at DESC)`
- `services/db_service.py` erweitert die Schema-Sicherung jetzt um idempotente `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`-Schritte fuer `sprint_plans` und `specs`
- Damit wird eine vorhandene Legacy-Tabelle nicht mehr stillschweigend als voll kompatibel angenommen
- Produktionsdienst neu gestartet und die Migration im Live-Kontext erfolgreich ausgefuehrt
- Der zuvor fehlerhafte Endpunkt `/api/plans/145` antwortet wieder mit HTTP `200`

**Geaenderte Dateien:**
- `services/db_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `61be781`

### Sprint QZ — Plan-Detailseite mit Tabs

**Ziel:** Plan-Cards nicht mehr ueber ein Auto-Modal auf `/plans?plan=...` oeffnen, sondern ueber eine eigene Detailseite mit klaren Tabs.

**Umgesetzt:**
- Neue Route `GET /plans/<id>` angelegt
- Legacy-Links `?plan=<id>` werden auf die neue Detailseite umgeleitet
- Neues Template `templates/plan_detail.html`
- Neue Assets `static/js/plan-detail.js` und `static/css/plan-detail.css`
- Die neue Seite zeigt Tabs fuer `Overview`, `Content`, `Workflow` und `Handoff`
- Die Seite nutzt bestehende APIs fuer Plan, Workflow und Handoff weiter
- Plan-Cards aus Projektdetail und Plans-Uebersicht navigieren jetzt auf die echte Detailseite statt auf ein Modal

**Geaenderte Dateien:**
- `routes/plans_routes.py`
- `templates/plan_detail.html`
- `static/js/plan-detail.js`
- `static/css/plan-detail.css`
- `static/js/plans.js`
- `static/js/project-detail.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `04f96b7`

### Sprint QR — Projektzentrierter Planning Workspace geplant

**Ziel:** Die GUI fachlich klar auf `Project -> Master Plan -> Sprint Plan -> Task/Spec -> Session` ausrichten.

**Umgesetzt:**
- Neuer Sprint-Plan `sprints/sprint-qr-project-planning-workspace.md` angelegt
- Projekt als primaere Homebase fuer Planung und operative Arbeit festgelegt
- `/plans` im Zielbild als globaler Index statt als konkurrierender Arbeitsraum definiert
- `Planning` im Projekt als neue zentrale Hierarchieansicht beschrieben
- Sessions fachlich der operativen Task-/Spec-Ebene zugeordnet
- zusaetzliche Architekturleitplanken dokumentiert: Glossar, Parent-Child-Regeln, Deep-Link-Prinzipien, normierte UI-Begriffe und erlaubte UI-Aktionen pro Ebene
- der Sprint ist jetzt in 5 sequentielle Umsetzungs-Sessions mit klaren Voraussetzungen und Ergebnissen aufgeteilt

**Geaenderte Dateien:**
- `sprints/sprint-qr-project-planning-workspace.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `04f96b7`

### Sprint QR — Session 1 Navigation und Begriffssystem festgezogen

**Ziel:** Den Einstiegspunkt fachlich korrekt machen, sichtbare Begriffe normieren und `/plans` als globalen Index statt als konkurrierende Arbeitsflaeche rahmen.

**Umgesetzt:**
- Projekt-Tab `Plans` zu `Planning` umbenannt und `Sessions` als spaetere `Session History` sekundarisiert
- Sidebar-Navigation auf `Plan Index` umgestellt
- `/plans` mit einem expliziten Global-Index-Hinweis versehen
- Plan-Cards im Index verlinken jetzt zusaetzlich sauber in den jeweiligen Projekt-Workspace
- Plan-Detailseiten fuehren ueber Query-Kontext wieder zur passenden Projektansicht bzw. zum gefilterten Index zurueck

**Geaenderte Dateien:**
- `templates/base.html`
- `templates/project_detail.html`
- `static/js/project-detail.js`
- `templates/plans.html`
- `static/js/plans.js`
- `templates/plan_detail.html`
- `static/js/plan-detail.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `04f96b7`

### Sprint QR — Session 2 Projekt-Hierarchie sichtbar gemacht

**Ziel:** Die Planungsstruktur im Projekt erstmals als echte Hierarchie `Plan -> Sprint -> Task/Spec` rendern.

**Umgesetzt:**
- neuen Read-Endpoint `GET /api/projects/<project_id>/planning` fuer den Projekt-Planning-Workspace angelegt
- `services/plan_structure_service.py` um einen read-only Hierarchie-Aggregator erweitert, der Projekt-Plans mit getaggter Sprint-/Spec-Struktur zusammenfuehrt
- den Projekt-Tab `Planning` von flachen Plan-Cards auf eine sichtbare Hierarchie umgestellt
- Sprints, Specs, direkte Sprint-Tasks und markerbasierte Tasks werden jetzt getrennt und in der fachlichen Reihenfolge gerendert
- leichter Test fuer den neuen Service-Pfad ergaenzt

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `routes/plans_routes.py`
- `static/js/project-detail.js`
- `static/css/project-detail.css`
- `tests/test_plan_structure_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `04f96b7`

### Sprint QR — Session 3 Detailpanel fuer operative Arbeit angebunden

**Ziel:** Aus der neuen Hierarchie direkt in konkrete operative Arbeit fuer `Spec` und `Task` wechseln koennen.

**Umgesetzt:**
- Marker-Daten im Struktur-Service fuer das Projekt-Planning um operative Felder wie `ziel`, `naechster_schritt`, `prompt`, `checks` und `risiko` erweitert
- im Projekt-Workspace ein selektierbares Detailpanel fuer `Sprint`, `Spec`, Markdown-Tasks und markerbasierte Tasks angebunden
- fuer markerbasierte Tasks werden jetzt Ziel, Next Step, Prompt, Checks und Risiko direkt im Panel gezeigt
- fuer plain Markdown-Tasks und Specs werden passende Fallback-Informationen bzw. Strukturzusammenfassungen gerendert
- die neue Planning-Logik modular in `static/js/project-planning.js` und `static/css/project-planning.css` ausgelagert, damit bestehende Dateien unter 500 Zeilen bleiben

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `templates/project_detail.html`
- `static/js/project-planning.js`
- `static/css/project-planning.css`
- `static/js/project-detail.js`
- `static/css/project-detail.css`
- `tests/test_plan_structure_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `04f96b7`

### Sprint QR — Session 4 Session-Historie an Task und Spec gehaengt

**Ziel:** Sessions fachlich korrekt als Ausfuehrungshistorie der operativen Ebene sichtbar machen.

**Umgesetzt:**
- `services/plan_structure_service.py` erweitert die Projekt-Planning-Hierarchie jetzt um Session-Summaries aus `last_session`, inklusive Startzeit, Dauer, Modell und Outcome
- Marker tragen ihre verknuepfte Session jetzt direkt im Hierarchie-Read-Model; `Spec` und `Sprint` aggregieren diese Session-Historie read-only nach oben
- plain Markdown-Tasks werden best-effort ueber gleichnamige Marker an Sessions angebunden, damit operative Eintraege im Planning nicht leer bleiben
- `static/js/project-planning.js` kennt jetzt zusaetzlich den Knotentyp `session`, zeigt Session-Historie im Detailpanel fuer `Task`, `Spec`, `Sprint` und Marker und verlinkt auf die Session-Detailseite
- `static/css/project-planning.css` um Session-Badges und eine kleine History-Darstellung im Detailpanel erweitert
- `tests/test_plan_structure_service.py` deckt die Session-Anreicherung im Planning-Service jetzt mit ab

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `static/js/project-planning.js`
- `static/css/project-planning.css`
- `tests/test_plan_structure_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `noch nicht committed`

### Sprint QR — Session 4 Follow-up: last_session Preservation und Backfill

**Ziel:** Die neue Session-Historie nicht nur im Code, sondern auch im echten Bestand wirksam machen.

**Umgesetzt:**
- `services/project_handoff_service.py` bewahrt bei Handoff-Regeneration jetzt bestehende Runtime-Felder wie `last_session`, Status und Execution-Metadaten pro Marker, statt sie wieder auf Default zurueckzusetzen
- `services/copilot_marker_service.py` um einen idempotenten Backfill fuer leere `last_session`-Felder erweitert
- neues Script `scripts/backfill_marker_last_sessions.py` angelegt
- den Backfill fuer `project_dashboard` direkt ausgefuehrt; dabei wurden 7 von 8 Markern mit echter `session_uuid` aus `project_plans.session_uuid` angereichert
- Tests fuer Handoff-Preservation und Marker-Backfill ergaenzt

**Geaenderte Dateien:**
- `services/project_handoff_service.py`
- `services/copilot_marker_service.py`
- `scripts/backfill_marker_last_sessions.py`
- `tests/test_project_handoff.py`
- `tests/test_copilot_marker_service_flow.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `noch nicht committed`

### Sprint PX — Hashtag-First Markdown Routine — MODUL 1 START

**Ziel:** Den Sprint modular beginnen: erst einen projektuebergreifenden Markdown-Kernservice bauen und den ersten produktiven Marker-Flow daran anbinden.

**Umgesetzt:**
- `services/markdown_routine_service.py` neu angelegt
- Der Service liefert bereits:
  - Encoding-Fallback fuer Markdown-Dateien
  - Content-Hash ohne technische Steuer-Marker
  - heuristische Klassifikation fuer Sprint-/Spec-/Technical-/Legacy-Faelle
  - Tag-Erkennung fuer `#sprint-*` und `#spec-*`
  - Sprint-/Spec-Struktur-Extraktion
  - semantische Split-Point-Erkennung fuer Legacy-Fallbacks
- Die lokal verfuegbaren Altdateien unter `upload/hash/` dienen jetzt als reale Referenz fuer die Generalisierung
- `services/copilot_marker_service.py` erweitert Marker um `sprint_tag` und `spec_tag`
- Der bestehende Sprint->Marker-Import nutzt fuer getaggte Inhalte bereits den neuen Markdown-Service und schreibt Tags an Marker zurueck
- `marker-context.md` enthaelt beim Aktivieren jetzt ebenfalls `sprint_tag` und `spec_tag`
- Tests fuer Service und Marker-Integration ergaenzt; `pytest tests/test_markdown_routine_service.py tests/test_copilot_marker_service.py -q` laeuft mit `26 passed`

**Geaenderte Dateien:**
- `services/markdown_routine_service.py`
- `services/copilot_marker_service.py`
- `tests/test_markdown_routine_service.py`
- `tests/test_copilot_marker_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `bbaf112`

### Sprint PX — Hashtag-First Markdown Routine — MODUL 2 CHECK/APPLY

**Ziel:** Die neue Tag-Architektur operativ machen, indem fehlende Sprint-/Spec-Tags projektweit erkannt und idempotent geschrieben werden koennen.

**Umgesetzt:**
- `services/markdown_routine_service.py` um Tag-Setter-Funktionen erweitert:
  - `build_tag_update_plan()`
  - `apply_tag_update_plan()`
- Der Service erkennt jetzt fehlende `#sprint-*`-Tags bei Sprint-Headings und fehlende `#spec-*`-Tags bei Unterabschnitten innerhalb eines Sprints
- Neues CLI-Script `scripts/markdown_tag_migration.py` angelegt
- Das Script unterstuetzt bereits:
  - `--check`
  - `--apply`
  - optional `--project`
  - optional `--handoff`
- Die erste Migration-Stufe schreibt bewusst nur Markdown-Tags; Marker-Backfill bleibt als separater naechster Modulschritt offen
- Tests fuer Tag-Setter und Check/Apply-Routine ergaenzt; `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py -q` laeuft mit `30 passed`

**Geaenderte Dateien:**
- `services/markdown_routine_service.py`
- `scripts/markdown_tag_migration.py`
- `tests/test_markdown_routine_service.py`
- `tests/test_markdown_tag_migration.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `bbaf112`

### Sprint PX — Hashtag-First Markdown Routine — MODUL 3 MARKER-BACKFILL

**Ziel:** Bestehende Marker in `handoff.md` konservativ auf `sprint_tag` und optional `spec_tag` nachziehen, ohne unklare Volltext-Zuordnungen.

**Umgesetzt:**
- `scripts/markdown_tag_migration.py` baut jetzt einen Markdown-Struktur-Index aus getaggten Sprint-/Spec-Dateien
- Marker-Mapping bevorzugt eine eindeutige `plan_id`-Zuordnung
- `spec_tag` wird nur gesetzt, wenn im eindeutig gemappten Sprint ein eindeutiger Treffer ueber Task-Titel oder Spec-Titel existiert
- Marker mit bereits vorhandenem `sprint_tag` werden nicht blind ueberschrieben
- `--check` zeigt fuer ungetaggte Marker Vorschlaege inkl. Grund (`plan_id_unique_match`, `plan_id_plus_task_match`, `plan_id_plus_spec_title_match`)
- `--apply` schreibt die gemappten Marker-Felder idempotent in `handoff.md`
- Tests fuer Vorschlag, Writeback und Idempotenz ergaenzt; `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py -q` laeuft mit `32 passed`

**Geaenderte Dateien:**
- `scripts/markdown_tag_migration.py`
- `tests/test_markdown_tag_migration.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `bbaf112`

### Sprint PX — Hashtag-First Markdown Routine — MODUL 4 PARSER/UI-INTEGRATION

**Ziel:** Den ersten sichtbaren Produktpfad von lokaler Frontend-Heuristik auf serverseitige Tag-Hierarchie umstellen.

**Umgesetzt:**
- `services/plan_structure_service.py` nutzt fuer Sprint-/Spec-Erkennung jetzt bevorzugt `scan_markdown_structure()`
- `sync_sprint_plans_from_master()` und `sync_specs_from_sprint_plan()` priorisieren `sprint_tag`, `spec_tag` und `plan_id` aus Markdown
- `get_plan_structure()` und `get_sprint_plan_detail()` matchen Marker bevorzugt ueber `sprint_tag` und `spec_tag`, mit Legacy-Fallback auf `plan_id` bzw. DB-IDs
- Neuer serverseitiger Helper `derive_tagged_plan_sections()` erzeugt eine direkte `Plan -> Sprint -> Spec -> Marker`-Struktur aus Markdown plus Marker-Bestand
- `routes/plans_routes.py` liefert in `/api/plans/<id>` jetzt zusaetzlich `tagged_sections`
- `static/js/copilot_board.js` nutzt fuer `Sprint Sections` bevorzugt diese serverseitige Struktur statt reines Titel-/Task-Matching aus lokal geparsten `##`-Headings
- Das Source-Panel zeigt Tasks inkl. Spec-Kontext und Marker inkl. Tag-Hierarchie an
- Tests fuer den neuen Service-Pfad ergaenzt; `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py tests/test_plan_structure_service.py -q` laeuft mit `34 passed`
- JS-Syntaxcheck fuer das Board laeuft: `node --check static/js/copilot_board.js`

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `routes/plans_routes.py`
- `static/js/copilot_board.js`
- `tests/test_plan_structure_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `bbaf112`

### Sprint PX — Hashtag-First Markdown Routine — REPO-ABSCHLUSS

**Ziel:** Die letzten sinnvollen Legacy-Pfade im Repo schliessen, damit fuer Sprint PX nur noch Live-Validierung gegen reale Plaene offen bleibt.

**Umgesetzt:**
- `services/plan_structure_service.py` priorisiert bei Spec-Referenzaufloesung jetzt `spec_tag` vor `spec_title`
- `services/copilot_marker_service.py` reicht `spec_tag` in die Struktur-Referenzaufloesung durch
- `services/copilot_service.py` fuehrt `sprint_tag` und `spec_tag` explizit im kompakten Marker-Kontext fuer Copilot-Calls mit
- Die verbleibenden naheliegenden Parser-/Struktur-Altpfade im Code sind damit auf Tag-Hierarchie reduziert oder klar als Legacy-Fallback stehen geblieben
- Relevante Sprint-Pfade lokal verifiziert:
  - `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py tests/test_plan_structure_service.py tests/test_copilot.py -q`
  - Ergebnis: `75 passed`
  - `python3 -m py_compile ...`
  - `node --check static/js/copilot_board.js`

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `services/copilot_marker_service.py`
- `services/copilot_service.py`
- `tests/test_plan_structure_service.py`
- `tests/test_copilot.py`
- `next-session.md`
- `sprints/sprint-px-hashtag-first-markdown-routine.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** `bbaf112`

### Session-Status 2026-04-03

**Konsolidiert live:**
- Copilot Sprint P3 auf `main` inkl. Marker-Aktivierung, `marker-context.md` und OK-Flow ohne Auto-Session-Start
- Sidebar task-basiert neu gruppiert, responsive gemacht, mehrfach gestrafft und mit Accordions fuer seltene Bereiche versehen
- `/quality` und `/governance` auf "aktive Projekte der letzten 90 Tage" begrenzt

**Rest-Risiko / offen:**
- Copilot-Workspace braucht weiter gezielten UI-Feinschliff; die globale Navigation und die Filterlogik sind dagegen fuer den Moment stabil

### Sprint PX — Hashtag-First Markdown Routine — PLAN ERSTELLT

**Ziel:** Die Kette `Plan -> Sprint -> Spec -> Marker` explizit als Markdown-first Architektur planen, inklusive projektuebergreifender Parser-Routine fuer alte und neue Projekte.

**Umgesetzt:**
- Neuer Gesamt-Sprint-Plan `sprints/sprint-px-hashtag-first-markdown-routine.md` angelegt
- Architekturentscheidung auf Hashtag-first festgezogen: `#sprint-*` und `#spec-*` als stabile Keys
- Marker-Zukunftsmodell im Plan dokumentiert: `sprint_tag` und optional `spec_tag`
- Die gefundene Altlogik unter `proj_irtours/archive/ALT/tools/scripts` ist als Quelle fuer eine generische Markdown-Routine festgehalten
- Der Sprint-Plan enthaelt jetzt auch eine explizite projektuebergreifende Tag-Migration mit Scanner, Tag-Setter, Marker-Updater sowie `--check`/`--apply` fuer Altprojekte
- DB-first fuer `sprint_plans/specs` ist in diesem Plan nicht mehr primaere Richtung, sondern hoechstens Cache-/Uebergangsmodell

**Geaenderte Dateien:**
- `sprints/sprint-px-hashtag-first-markdown-routine.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** noch nicht committed

### Sprint P4 — Session Write-back — DONE

**Ziel:** Den Status eines aktiv bearbeiteten Markers am Session-Ende explizit in `handoff.md` zurueckschreiben, ohne P3 um Auto-Start oder neue Aktivierungslogik zu erweitern.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `close_marker(handoff_path, marker_id, ...)` erweitert; aktualisiert `status`, `naechster_schritt`, `last_session` und `updated_at` im bestehenden Dual-Format
- `routes/copilot_routes.py` um `POST /api/copilot/markers/<id>/close` erweitert; Fehlerfaelle `handoff_missing` und `marker_not_found` sind explizit abgebildet, und `project_id` kann optional aus `marker-context.md` gelesen werden
- `marker-context.md` schreibt beim Aktivieren jetzt auch `project_id`, neben `marker_id` und `plan_id`
- `static/js/copilot_board.js` enthaelt eine kleine Refresh-Hilfe fuer den expliziten Close-Call
- Service- und API-Tests fuer den Write-back-Roundtrip ergaenzt, plus manueller `activate -> close -> parse_markers()`-Check
- Copilot-Testsuite lokal stabilisiert: `tests/test_copilot.py` nutzt jetzt einen In-Memory-DB-Fake statt Live-Postgres, `/copilot`-Redirect-Tests spiegeln den aktuellen UI-Flow, und `services/copilot_service.py` persistiert optional `images`
- Copilot-/Plan-Tests teilweise vereinheitlicht: gemeinsames `client`-Fixture aus `tests/conftest.py`, derselbe `mock_copilot_db`-Pfad fuer Copilot-Binding, und UI-Render-Tests vermeiden unnoetige DB-Fixures
- `tests/test_plan_workflow.py` auf die aktuelle Handoff-Architektur gezogen: Handoff-Tests nutzen `project_handoff_service`, pruefen das Marker-Format und laufen fuer diesen Teilbereich ohne Postgres ueber einen kleinen In-Memory-Plan-Store

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
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** noch nicht committed

### Sprint P5 — Sprint to Markers — DONE

**Ziel:** Sprint-Aufgaben aus einem Sprint-Plan per Klick als Marker in `handoff.md` erzeugen oder aktualisieren, ohne Duplikate.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `sprinttomarkers()` und `buildsuggestion()` erweitert; Sprint-Sektion wird ueber `Plan-ID` gefunden und Aufgaben-Bullets werden als Marker in `handoff.md` geschrieben
- Marker werden ueber deterministische IDs aus `plan_id + titel` idempotent erzeugt oder aktualisiert
- `routes/copilot_routes.py` um `POST /api/sprint/<plan_id>/to-markers` erweitert
- `templates/copilot_board.html` und `static/js/copilot_board.js` um den Header-Button `Sprint -> Marker` erweitert; nach Erfolg laedt das Board die Marker neu
- Marker-Board nutzt bei Bedarf eine semantische `Plan-ID` aus dem Plan-Inhalt und faellt sonst auf das bisherige Verhalten zurueck
- Service- und API-Tests fuer Sprint->Marker und Duplikat-Schutz ergaenzt
- `static/css/copilot.css` zeigt laengere Marker-Titel und Vorschau-Texte jetzt mehrzeilig, und die Board-Spalten wurden breiter gesetzt, damit Marker-Text in den Cards nicht vorzeitig abgeschnitten wird
- `static/js/copilot_board.js` rendert den Vorschau-Block jetzt direkt unter dem Marker-Titel statt erst unter Gate/Status-Hinweisen
- `static/css/copilot.css` haertet die Chat-Nachrichten im Panel gegen Overflow ab; lange Antworten und Markdown-Code bleiben innerhalb der Chat-Card
- `static/css/copilot.css` setzt die relevanten Flex-/Scroll-Container im Chat-Panel auf `min-height: 0`, damit Chat-Boxen beim Scrollen nicht abgeschnitten werden
- `services/copilot_service.py` persistiert fuer `copilot_runs` jetzt auch Token- und Kostenfelder; `static/js/copilot_board.js` zeigt Modell, Tokens und USD-Kosten unter Assistant-Nachrichten im Chat-Panel an
- `services/copilot_service.py` baut vor dem LLM-Call serverseitig einen kompakten Marker-Kontext aus `marker-context.md` und `handoff.md`; `handoff.md` bleibt fuehrende Wahrheit, Frontend-Kontext dient nur als Fallback
- `services/copilot_service.py` loest fuer diesen Marker-Kontext jetzt auch den lesbaren Plan-Titel auf; `static/js/copilot_board.js`, `static/js/plans.js` und `templates/copilot_landing.html` zeigen bzw. verwenden den Plan-Namen im Panel und als lesbaren URL-Slug zusaetzlich zur `plan_id`

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `routes/copilot_routes.py`
- `templates/copilot_board.html`
- `static/js/copilot_board.js`
- `static/css/copilot.css`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** noch nicht committed

### Sprint P-E3 — Execution-Rating & Feedback fuer Marker — DONE

**Ziel:** Nach jeder markerbezogenen Session eine leichte Execution-Bewertung erfassen, die am Marker und optional an der Session haengt.

**Umgesetzt:**
- `services/copilot_marker_service.py` um optionale Marker-Felder `execution_score`, `execution_comment`, `last_execution_at` sowie `update_execution_rating()`, `get_marker_execution_rating()` und `get_marker_by_last_session()` erweitert
- `handoff.md` Dual-Format rendert die neuen Execution-Felder rueckwaertskompatibel mit; aeltere Marker bleiben gueltig
- `services/db_service.py` erweitert `sessions` idempotent um `execution_score` und `execution_comment`
- `routes/copilot_routes.py` enthaelt jetzt `GET/POST /api/marker/<marker_id>/execution-rating`
- `routes/session_routes.py` haengt in der Session-Detail-API bei Treffern den zuletzt auf die Session geschriebenen Marker (`last_session == session_uuid`) als `session.marker` an
- `templates/copilot_board.html`, `static/js/copilot_board.js` und `static/css/copilot.css` zeigen die aktuelle Execution-Bewertung im Board/Marker-Panel an und erlauben dort direkte Aenderungen
- `templates/session_detail.html`, `static/js/session-detail.js` und `static/css/session-detail.css` enthalten ein leichtes Rating-Panel fuer den zugeordneten Marker; Speichern schreibt Marker und Session gemeinsam
- Service- und API-Tests decken Marker-Writeback, Session-Update, Score-Validierung und GET/POST-Flow ab

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
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit-Hash:** 338fd8c

### Sprint M2.11a — Governance auf aktive Projekte begrenzen — DONE

**Ziel:** Die Governance-Seite soll wie die Quality-Seite nur Projekte mit relevanten Datei-Aenderungen in den letzten 90 Tagen anzeigen.

**Umgesetzt:**
- `services/governance_service.py` filtert `get_governance_overview()` jetzt auf relevante Projektdateien mit `mtime >= 90 Tage`
- `project.json` allein zaehlt nicht als Aktivitaet, damit reine Metadaten-Aenderungen keine Governance-Kacheln mehr sichtbar halten
- Service-Tests decken sowohl den Positivfall als auch den Fall "nur frisches project.json, aber alter Code" ab

**Geaenderte Dateien:**
- `services/governance_service.py`
- `tests/test_governance_gate.py`

### Sprint A — Quality Scanner Spec & Scope Lock — DONE
Spec erstellt: `sprints/spec-quality-scanner-mvp-001.md`

### Sprint B — Quality Scanner MVP — DONE
Scanner validiert, 2 Fixes (Pfadaufloesung, History-Felder), 20 Abnahmetests.

### Sprint C — Governance Light — DONE
GET /api/governance/gate/<project>, green/yellow/red Logik, Health-Ampel in UI, 11 Tests.

### Sprint D — LLM Command Hub MVP — DONE
3 Markdown-Commands, POST /api/llm/commands/run, Perplexity-Connector, Persistenz, UI, 15 Tests.

### Copilot Chat — DONE
POST /api/copilot/chat, Thread-Historie, Plan-Bindung, Chat-UI, 12 Tests.

### Sprint E — Plan-Workflow Micro-Ebene — DONE
14 Workflow-Spalten auf project_plans, GET/PUT /api/plans/<id>/workflow, Ist/Soll/Next,
Signal-Integration (Quality+Audit+Governance), Copilot plan_id-Binding, 16 Tests.

### Sprint F — Drag & Drop Board — DONE
Kanban-Board-Ansicht fuer Plans-Seite. Plan-Cards per Drag & Drop zwischen 8 Workflow-Spalten
verschiebbar (idea → spec_ready → prompt_ready → executing → review_pending → fixed → done → blocked).
HTML5 native D&D, optimistisches Move mit API-Rollback bei Fehler, View-Toggle Grid/Board.
Geaendert: plans.html, plans.js, plans.css. 6 neue Tests (22 total).

### Sprint G — Plan-Handoff Generator — DONE
Standardisierte Markdown-Zusammenfassung pro Plan fuer LLM-Executor-Uebergabe.
YAML-Frontmatter (type/stage/scope/expected_output/priority) + 7 Sektionen (Projektkontext,
Ist, Soll, Ergebnisse, Blocker, Auftrag, Output-Format). build_plan_handoff_markdown() in
plan_workflow_service.py, GET /api/plans/<id>/handoff (text/markdown), Handoff-Button im
Plan-Modal mit Kopieren+Download. 9 neue Tests (31 total).

### Sprint H — DB-first Copilot-Architektur — DONE
Neue DB-Tabellen: plan_sections (Level-2-Cards), copilot_threads (Thread pro Section),
copilot_messages (Messages mit Usage/Kosten). Service-Layer: plan_section_service.py
(CRUD + Chat), section_routes.py (API). Board-Spalten: backlog/ready/in_progress/review/done/blocked.
/copilot?plan_id=X zeigt Section-Board + Modal-Chat. 27 neue Tests (94 total).

### Sprint I — Zentraler Handoff-Service — DONE
project_handoff_service.py: get_handoff_path(), ensure_handoff_for_plan(), read_handoff_for_plan(),
ensure_handoffs_for_project(). Alle Aufrufer (API, Memory, LLM Commands) umverdrahtet.
Handoff-Erkennung im Projekt-Scanner. LLM Command handoff-status.md mit {{handoff_data}}/
{{sections_data}} Platzhaltern. CLAUDE.md aktualisiert. 13 neue Tests.

### Sprint J — Level-Trennung Korrektur — DONE
/plans = einziges Plan-Board (Level 1). /copilot?plan_id=X = Section-Board + Chat (Level 2).
/copilot ohne plan_id = Redirect (1 aktiver Plan → direkt, sonst → /plans).
Copilot-Tab/Chat/Upload aus Plan-Modal entfernt. Copilot-Link auf Plan-Cards + Modal-Toolbar.
Keine dritte Board-Ebene.

### Sprint M — Test-Cleanup fuer Plan-Tests — DONE
pytest-Fixtures in test_plan_workflow.py und test_plan_sections.py auf yield+DELETE umgebaut.
Alle Test-Plans tragen jetzt [TEST]-Prefix. Kaskadierender Teardown (Messages→Threads→Sections→Plans).
Inline-Plan in test_handoff_missing_signals mit try/finally gesichert. 68 Tests gruen, 0 DB-Leichen.

### Sprint M2.7 — Plans-Cards & Modal Redesign — DONE
**Ziel:** Plans-Cards aufgeräumt, Modal auf Linear/Notion Level.

**Änderungen:**
- Cards im Grid: Ist/Soll/Next/exec von Cards entfernt, nur noch Header (Typ-Badge + Titel + Stage-Badge) + Body (Kurzbeschreibung, 2 Zeilen) + Footer (Projekt-Tag)
- Card-Design: Dezente Background-Tints nach Status (Draft=grau, Active=blau, Completed=grün), einheitliche Höhe (140px), Ellipsis bei langem Text
- Modal komplett neu: Linear/Notion Style
  - Header: Kategorie-Badge + Titel + Meta (Projekt/Datum)
  - Body links: Ist/Soll nebeneinander (2-Spalten), dann Details
  - Body rechts: Sidebar mit Status, Workflow, Metadaten, Aktionen (Copilot, Handoff)
  - Footer: Schließen-Button
- Sticky Filter-Bar: KPI-Header + Filter-Leiste sticky (kpi-wrapper)

**Dateien:** templates/plans.html, static/js/plans.js, static/css/plans.css
**Commit:** 54b521c

### Sprint M2.8 — Quality-Scanner Re-Scan — DONE
**Ziel:** Test `TestR6IgnoreDirs` reparieren, 259/259 Tests gruen.

**Problem:** jscpd `--ignore` Pattern `node_modules` ignoriert nur direct node_modules/, 
aber nicht verschachteltes `.kilo/node_modules/`.

**Fix:**
- `auto_coder/checks/duplication.py` — `_run_jscpd()` geaendert
- Pattern von `node_modules` auf `**/node_modules/**` fuer jscpd
- Re-Scan mit `ProjectQualityScanner.scan()` + `save_report()` ausgefuehrt

**Ergebnis:** Test gruen, keine node_modules-Issues mehr im Report.

### Sprint M2.9 — Copilot-Board QA — DONE
**Ziel:** Copilot-Board funktional testen, Level-Trennung verifizieren.

**Tests:**
- API-Workflow: Plan → Section erstellen → Status verschieben (backlog→done) ✓
- Board-Spalten: backlog/ready/in_progress/review/done/blocked ✓
- Cards = plan_sections (nicht project_plans) ✓
- Thread pro Section (chat_with_section) ✓
- Level-Trennung: /plans ohne Section-Logik ✓
- Copilot-Landing-Page (/copilot ohne plan_id) mit Stats ✓
- 28 Tests in test_plan_sections.py alle gruen

### Sprint N — Copilot UX Redesign: AI-native Work OS — DONE
**Ziel:** Von "Kanban + Chat" zu "AI-native Work OS" — Split View, Rich Cards, Side Panel.

**Änderungen:**
1. **Split View Layout:** Board links, Slide-in Panel rechts (CSS Grid + Animation)
2. **Side Panel:** Zeigt Section-Info, AI-Preview, Live-Chat
3. **Rich Cards:** AI-Message-Count + Preview der letzten Antwort
4. **Column Microcopy:** Emoji + Beschreibung pro Spalte (💡 Backlog: "Noch zu klären", etc.)
5. **Flow Guidance:** Header mit 4-Schritt-Hinweis
6. **Landing Page Redesign:** Stats, Continue-Card, Quick-Start Buttons

**Dateien:**
- `copilot_board.html` — Split View, Side Panel
- `copilot_board.js` — Panel-Toggle, AI-Previews
- `copilot.css` — Panel-Styles, Glows, Microcopy
- `copilot_landing.html` — Redesign mit Stats/Continue
- `plan_section_service.py` — `get_section_ai_preview()`
- `section_routes.py` — `/api/copilot/ai-previews`

**Hinweis:** Server-Restart erforderlich für Template-Aktualisierung.

### Sprint O — Release v1.2.0 + Test-Suite Komplett — DONE (2026-04-02)
**Ziel:** Release-Prozess etablieren, Test-Abdeckung von 20% auf 75%+ bringen, Produktions-Bugs fixen.

**Release v1.2.0:**
- CHANGELOG.md erstellt (68 Commits: 27 feat, 22 fix, 19 docs)
- Git-Tag v1.2.0 + Docker-Image sessionpilot:v1.2.0
- Release-Skill `sessionpilot-release` als wiederverwendbarer 7-Schritt-Prozess

**Test-Infrastruktur (3 Stufen):**
- Stufe 1: `tests/conftest.py` — Shared Fixtures (client, 4 Mock-Fixtures fuer externe Services)
- Stufe 2: `tests/test_routes_smoke.py` — 110 Smoke-Tests (20 Seiten, 66 APIs, 13 Struktur-Checks)
- Stufe 3: 5 neue Unit-Test-Dateien — cost_service, notification_service, session_import, session_import_utils, project_detector (82 Tests)
- **Vorher:** 258 Tests, 37 failed, 54 errors → **Nachher:** 451 Tests, 0 failed, 0 errors

**Bugs gefixt:**
1. `config.py` — load_dotenv() fehlte (91 Test-Failures behoben)
2. `routes/timesheet_routes.py` — SQL `'<%>'` psycopg2 Format-Bug (Produktion kaputt)
3. `services/db_service.py` — ai_file_touches Schema-Reihenfolge (Widget kaputt)
4. `tests/test_copilot.py` — Template-IDs an Sprint N angepasst

**Commits:** e42ed29, ab65270, 5c752de, 3142cc2, 83e5774, 94d2e18, d430d51

### Sprint P — Copilot Dark Design-System Seed — DONE (2026-04-03)
**Ziel:** Ohne Architekturumbau ein konsistentes Dark-SaaS-Design-System fuer den bestehenden Copilot-Workspace anlegen.

**Aenderungen:**
- `static/css/design-tokens.css` um zentrale Dark-SaaS-Tokens erweitert (`--bg-main`, `--bg-panel`, `--bg-card`, `--border`, `--text-*`, `--accent`, Statusfarben, Radien)
- `static/css/components.css` um neue UI-Primitives erweitert: `ui-card`, `ui-panel`, `ui-button`, `ui-badge`, `ui-tabs`, `ui-input`
- `static/css/copilot.css` auf die neuen Tokens gemappt und gezielt fuer Board-Card + rechtes Panel nachgeschaerft
- `static/js/copilot_board.js` erzeugt Board-Cards jetzt mit `ui-*` Klassen; Status-Badge im rechten Panel ebenfalls angeglichen
- `templates/copilot_board.html` nutzt `ui-panel`, `ui-tabs` und `ui-input` im bestehenden Layout

**Dateien:**
- `static/css/design-tokens.css`
- `static/css/components.css`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `templates/copilot_board.html`
- `next-session.md`

**Commit:** uncommitted

### Sprint P1 — Copilot Workspace Header + Progress Refactor — DONE (2026-04-03)
**Ziel:** Den oberen Bereich von `/copilot?plan_id=X` wie einen echten AI-Workspace wirken lassen, ohne weitere UI-Bereiche anzufassen.

**Aenderungen:**
- Header in `templates/copilot_board.html` neu strukturiert: Brand, Plan-Switcher, aktiver Plan, Actions
- Progress-Bereich als eigener kompakter Info-Block mit staerkerer Typohierarchie und KPI-Karten umgesetzt
- `static/css/copilot.css` um wiederverwendbare Header-/Progress-Klassen erweitert
- `static/js/copilot_board.js` so angepasst, dass Plan-Switcher und aktueller Planname getrennt befuellt werden

**Dateien:**

### Sprint P3.1 — Leerer Handoff fuer neue Projektordner — DONE (2026-04-03)
**Ziel:** `handoff.md` auch fuer existierende Projektordner ohne `project_plans` robust anlegen, damit Copilot-/Handoff-Flows nicht an `None` scheitern.

**Aenderungen:**
- `services/project_handoff_service.py` um `build_empty_handoff_markdown()` erweitert
- `write_handoff()` schreibt jetzt fuer existierende Projektordner ohne Plans einen minimalen `copilot_markers_v1`-Handoff statt `(None, None)` zurueckzugeben
- `tests/test_project_handoff.py` um Abdeckung fuer den Empty-Handoff-Fall erweitert

**Dateien:**
- `services/project_handoff_service.py`
- `tests/test_project_handoff.py`

**Commit:** uncommitted

### Sprint P3.2 — Marker-Chat-Verlauf Fix — DONE (2026-04-03)
**Ziel:** Das Copilot-Panel soll Marker-Threads wieder laden koennen, ohne dass `/api/copilot/runs` bei `plan_id`-Filtern mit 500 scheitert.

**Aenderungen:**
- `services/copilot_service.py` um `plan_id`-Filter in `list_copilot_runs()` erweitert
- Verlaufseintraege liefern `plan_id` wieder mit an die Route und das Board
- Live-Fehler `list_copilot_runs() got an unexpected keyword argument 'plan_id'` damit beseitigt

**Dateien:**
- `services/copilot_service.py`

**Commit:** uncommitted

### Sprint P3.3 — Responsive Sidebar Layout — DONE (2026-04-03)
**Ziel:** Die globale linke Navigation soll auf kleineren Viewports als sauberer Off-Canvas-Drawer funktionieren, ohne den Content zu quetschen.

**Aenderungen:**
- `templates/base.html` um mobilen Backdrop fuer die Sidebar erweitert
- `static/js/base.js` um Mobile-Drawer-Logik, `Esc`-Close, Focus-Restore und Auto-Close nach Navigation erweitert
- `static/css/layout.css` fuer Off-Canvas-Sidebar, Backdrop und responsive Topbar aufbereitet
- `static/css/base.css` sperrt den Body-Scroll bei offener mobiler Sidebar
- Mobile scrollt jetzt die gesamte Sidebar inklusive Footer-Links statt nur den mittleren Nav-Bereich

**Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `static/css/layout.css`
- `static/css/base.css`

**Commit:** uncommitted

### Sprint P3.4 — Sidebar-Navigation gestrafft — DONE (2026-04-03)
**Ziel:** Die globale Navigation soll fachlich klarer gruppiert und textlich kompakter werden.

**Aenderungen:**
- `templates/base.html` gruppiert die Sidebar jetzt in `Core`, `AI Ops`, `Engineering` und `Content`
- `Plans`, `Copilot` und `New Project` stehen jetzt im Kernbereich statt verteilt zwischen DevOps- und Workspace-Links
- Mehrere lange Labels wurden gekuerzt, damit die Navigation schneller scanbar ist

**Dateien:**
- `templates/base.html`

**Commit:** uncommitted

### Sprint P3.5 — Sidebar Density Tuning — DONE (2026-04-03)
**Ziel:** Die globale Sidebar soll visuell kompakter und ruhiger wirken, ohne Funktion oder Struktur weiter zu aendern.

**Aenderungen:**
- `static/css/layout.css` auf dichtere Typografie, kleinere Icons und flachere Nav-Zeilen umgestellt
- Section-Labels feiner gewichtet und Utility-Footer visuell abgeschwaecht
- Active- und Hover-States auf kompaktere, weniger schwere Flaechen reduziert

**Dateien:**
- `static/css/layout.css`

**Commit:** uncommitted

### Sprint P3.6 — Sidebar auf Task-Navigation umgestellt — DONE (2026-04-03)
**Ziel:** Die globale Navigation soll sich an Nutzeraufgaben statt an technischen Systemkategorien orientieren.

**Aenderungen:**
- `templates/base.html` auf die Gruppen `Arbeiten`, `Auswerten`, `System`, `Inhalte`, `Integrationen` umgebaut
- `Copilot`, `Dashboard` und `Sessions` als primaere Ziele hervorgehoben
- `System` als standardmaessig eingeklappter Block umgesetzt
- `static/js/base.js` speichert den Collapse-Zustand des System-Blocks in `localStorage`
- `static/css/layout.css` staerkt die Section-Hierarchie und hebt den Copilot-Einstieg deutlicher hervor

**Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `static/css/layout.css`

**Commit:** uncommitted

### Sprint P3.7 — Startseite in Sidebar entdoppelt — DONE (2026-04-03)
**Ziel:** Die Startseite `/` soll in der Sidebar nicht mehr doppelt als `Dashboard` und `Projects` erscheinen.

**Aenderungen:**
- `templates/base.html` fuehrt `/` jetzt nur noch als `Projects`
- aktiver Zustand deckt `dashboard` und `projects` gemeinsam ueber denselben Menüpunkt ab
- separater `Dashboard`-Eintrag aus der Sidebar entfernt

**Dateien:**
- `templates/base.html`

**Commit:** uncommitted

### Sprint P3.8 — Models nach Auswerten verschoben — DONE (2026-04-03)
**Ziel:** Der Menüpunkt `Models` soll fachlich im Analyse-/Auswertungsbereich statt im Systemblock liegen.

**Aenderungen:**
- `templates/base.html` verschiebt `Models` von `System` nach `Auswerten`
- `System` bleibt dadurch klarer auf operative und infrastrukturelle Punkte fokussiert

**Dateien:**
- `templates/base.html`

**Commit:** uncommitted

### Sprint P3.9 — Steuerungsfunktionen aus System herausgezogen — DONE (2026-04-03)
**Ziel:** `Quality`, `Governance`, `Audits` und `Commands` sollen als eigener Steuerungsblock statt als Teil von `System` erscheinen.

**Aenderungen:**
- `templates/base.html` fuehrt einen eigenen Bereich `Steuern`
- `Quality`, `Governance`, `Audits` und `Commands` aus dem `System`-Block herausgezogen
- `System` bleibt dadurch klarer auf operative und infrastrukturelle Themen fokussiert

**Dateien:**
- `templates/base.html`

**Commit:** uncommitted

### Sprint P3.10 — Inhalte und Integrationen als Accordion — DONE (2026-04-03)
**Ziel:** Seltenere Sidebar-Bereiche sollen Platz sparen und dieselbe Collapse-Logik wie der Systemblock nutzen.

**Aenderungen:**
- `templates/base.html` fuehrt `Inhalte` und `Integrationen` als einklappbare Bereiche
- `static/js/base.js` erweitert die gespeicherten Sidebar-Collapse-Zustaende um `content` und `integrations`
- beide Bereiche starten standardmaessig eingeklappt

**Dateien:**
- `templates/base.html`
- `static/js/base.js`

**Commit:** uncommitted

### Sprint P3.11 — Auswerten als Accordion nach Steuern — DONE (2026-04-03)
**Ziel:** Der Bereich `Auswerten` soll dieselbe Accordion-Logik wie die restlichen Nebenbereiche nutzen und in der Reihenfolge hinter `Steuern` liegen.

**Aenderungen:**
- `templates/base.html` fuehrt `Auswerten` jetzt als einklappbaren Block
- Reihenfolge der Sidebar angepasst: `Steuern` vor `Auswerten`
- `static/js/base.js` erweitert die Default-Collapse-Zustaende um `analysis`

**Dateien:**
- `templates/base.html`
- `static/js/base.js`

**Commit:** uncommitted

### Sprint P3.12 — Kontextaktionen vor globaler Hilfe — DONE (2026-04-03)
**Ziel:** Seitenspezifische Header-Aktionen sollen vor dem globalen Help-Center-Shortcut stehen.

**Aenderungen:**
- `templates/base.html` rendert `topbar_actions` jetzt vor dem globalen `?`-Icon
- kontextbezogene Aktionen wie `Guide` auf der Quality-Seite erscheinen dadurch vor der globalen Hilfe

**Dateien:**
- `templates/base.html`

**Commit:** uncommitted

### Sprint P3.13 — Hauptnavigation fachlogisch vereinheitlicht — DONE (2026-04-05)
**Ziel:** Die primaeren Menuepunkte sprachlich von technischen Systembegriffen auf fachlich lesbare Arbeitsbegriffe umstellen.

**Aenderungen:**
- `templates/base.html` benennt die Hauptnavigation auf `Planning`, `AI Workspace` und `Activity` um
- Breadcrumbs und Seitentitel fuer Planning-, Copilot-/Workspace- und Sessions-Seiten an die neue Navigationssprache angepasst
- `templates/plan_detail.html` Backlink von `Back to Plan Index` auf `Back to Planning` umgestellt
- `static/js/base.js` Command-Palette-Eintraege auf `Activity` angeglichen
- Technische Pfade und Query-Parameter wie `/copilot`, `/sessions` und `?tab=gitea` bewusst unveraendert gelassen

**Dateien:**
- `templates/base.html`
- `templates/plans.html`
- `templates/plan_detail.html`
- `templates/copilot_landing.html`
- `templates/copilot_board.html`
- `templates/copilot.html`
- `templates/sessions.html`
- `templates/session_detail.html`
- `templates/partials/index_modals.html`
- `static/js/base.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit:** uncommitted

### Sprint P3.14 — Projects-Header als direkter Einstieg — DONE (2026-04-05)
**Ziel:** Den redundanten Unterpunkt `Projects` aus der Sidebar entfernen, ohne den direkten Rueckweg zur Hauptansicht zu verlieren.

**Aenderungen:**
- `templates/base.html` trennt den Bereich `Projects` in einen klickbaren Header-Link und einen separaten Chevron-Button fuer das Submenue
- Der Unterpunkt `Projects` entfällt; sichtbar bleiben nur `New Project`, `Overview` und `Repository Sources`
- `static/css/layout.css` ergaenzt die minimale Layout-Unterstuetzung fuer Link + Toggle innerhalb desselben Sidebar-Headers
- Bestehende Tab-Logik fuer `showTab('projects')` und die technischen URLs bleiben unveraendert

**Dateien:**
- `templates/base.html`
- `static/css/layout.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit:** uncommitted

### Sprint P3.15 — Projektseite von Overview zu Details geschaerft — DONE (2026-04-05)
**Ziel:** Die Projektseite sprachlich und visuell klarer strukturieren: Detailinformationen als eigener Tab, die eigentliche Uebersicht als Karten-Summary im Seitenkopf.

**Aenderungen:**
- `templates/project_detail.html` benennt den Tab `Overview` in `Details` um
- Oberhalb der Tabs wurde eine neue kartenbasierte Projektuebersicht eingefuegt
- `static/js/project-detail.js` laedt dafuer bestehende Planning-, Quality- und Session-Daten parallel und verdichtet sie zu Karten fuer Fortschritt, Sprint-Plans, Issues und Activity
- `static/css/project-detail.css` ergaenzt das responsive Kartenlayout fuer die neue Projektuebersicht
- Bestehende Detailinhalte im bisherigen Overview-Bereich bleiben als `Details` erhalten

**Dateien:**
- `templates/project_detail.html`
- `static/js/project-detail.js`
- `static/css/project-detail.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit:** uncommitted

### Sprint P3.16 — Projektuebersicht als handlungsfuehrende Karten — DONE (2026-04-05)
**Ziel:** Die neue Projektuebersicht nicht als reine KPI-Flaeche, sondern als fachliche `Was jetzt?`-Navigation nutzbar machen.

**Aenderungen:**
- `static/js/project-detail.js` leitet aus Planning-, Quality- und Activity-Signalen jetzt konkrete Empfehlungen und CTA-Ziele ab
- Die primaere Karte formuliert eine priorisierte naechste Aktion statt nur einen Zustandswert
- Die Fachkarten fuer `Planning`, `Delivery`, `Issues` und `Activity` fuehren direkt in die passende Arbeitsflaeche
- `static/css/project-detail.css` ergaenzt CTA-Styling fuer die neue handlungsfuehrende Kartenlogik

**Dateien:**
- `static/js/project-detail.js`
- `static/css/project-detail.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit:** uncommitted

### Sprint P3.17 — AI Workspace wieder zu Cockpit vereinheitlicht — DONE (2026-04-05)
**Ziel:** Den primaeren KI-Arbeitsbereich wieder mit dem etablierten Fachbegriff `Cockpit` fuehren statt mit dem generischen Begriff `AI Workspace`.

**Aenderungen:**
- Sidebar-Eintrag in `templates/base.html` von `AI Workspace` auf `Cockpit` umgestellt
- Seitentitel und Breadcrumbs der Copilot-/Cockpit-Seiten in `templates/copilot_landing.html`, `templates/copilot_board.html` und `templates/copilot.html` auf `Cockpit` vereinheitlicht
- Technische Route `/copilot` bewusst unveraendert gelassen

**Dateien:**
- `templates/base.html`
- `templates/copilot_landing.html`
- `templates/copilot_board.html`
- `templates/copilot.html`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit:** uncommitted

### Sprint P3.18 — Projektkontext zwischen Screens persistent gemacht — DONE (2026-04-05)
**Ziel:** Das aktuell bearbeitete Projekt nicht bei jedem Wechsel in das `Cockpit` oder zwischen Plan-/Projektansichten neu auswaehlen muessen.

**Aenderungen:**
- `static/js/base.js` fuehrt einen kleinen globalen Browser-Speicher fuer den aktiven Projektkontext ein
- `static/js/project-detail.js` und `static/js/plan-detail.js` setzen das aktuelle Projekt beim Oeffnen der jeweiligen Arbeitsflaeche
- `static/js/project-planning.js` und `static/js/plans.js` geben den Projektkontext zusaetzlich in `Cockpit`-Links als `project=` weiter
- `static/js/copilot.js` liest zuerst `project`/`project_id` aus der URL und faellt dann auf den zuletzt gespeicherten Projektkontext zurueck

**Dateien:**
- `static/js/base.js`
- `static/js/copilot.js`
- `static/js/project-detail.js`
- `static/js/project-planning.js`
- `static/js/plan-detail.js`
- `static/js/plans.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Commit:** uncommitted
- `templates/copilot_board.html`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `next-session.md`

**Commit:** uncommitted

### Sprint P1.1 — Marker-Schema & handoff.md Generator — DONE (2026-04-03)
**Ziel:** `handoff.md` als fuehrende State-Datei auf ein maschinenlesbares Marker-Format umstellen.

**Aenderungen:**
- Neuer Kernservice `services/copilot_marker_service.py` mit `Marker`-Dataclass, `_serialize_marker()`, `_write_marker()` und `parse_markers()`
- Dual-Format eingefuehrt: JSON im HTML-Kommentar + lesbarer Markdown-Teil
- `services/project_handoff_service.py` erzeugt jetzt Marker-Bloecke statt aggregiertem Prosatext
- Gezielte Tests fuer Marker-Roundtrip und Generator ergaenzt

**Dateien:**
- `services/copilot_marker_service.py`
- `services/project_handoff_service.py`
- `tests/test_copilot_marker_service.py`
- `tests/test_project_handoff.py`
- `next-session.md`

**Commit:** uncommitted

### Sprint P2 — Cards aus Markdown + Status Write-back — DONE (2026-04-03)
**Ziel:** Copilot-Board auf Marker aus `handoff.md` umstellen und Status-/Prompt-Aenderungen direkt in die Marker-Datei zurueckschreiben.

**Aenderungen:**
- `services/copilot_marker_service.py` um plan-gefilterte Read-/Update-Funktionen erweitert: `list_markers_for_plan()`, `get_marker_context()`, `update_marker_status()`, `update_marker_fields()`
- `routes/copilot_routes.py` um Marker-Endpunkte erweitert: `GET /api/copilot/markers`, `GET /api/copilot/markers/<id>`, `PATCH /status`, `PATCH /fields`
- `static/js/copilot_board.js` von DB-`plan_sections` auf Marker-API umgestellt; Board rendert jetzt `titel`, `ziel`, `naechster_schritt`, Gate-Status und schreibt Drag-&-Drop-Status per PATCH zurueck
- Detail-Panel in `templates/copilot_board.html`/`static/js/copilot_board.js` zeigt Marker-Kontext, Checks, Risiko, last_session, updated_at und den Button `Vorschlag uebernehmen`
- Panel-Chat auf markerbasierte Copilot-Runs mit stabiler `thread_id` umgestellt, damit Chat weiter pro Card funktioniert
- `services/project_handoff_service.py` erzeugt Default-Checks fuer neue Marker, damit Prompt-Uebernahme den Gate-Status sinnvoll beeinflussen kann
- Gezielte Tests fuer Marker-Service und Marker-API ergaenzt

**Dateien:**
- `services/copilot_marker_service.py`
- `services/project_handoff_service.py`
- `routes/copilot_routes.py`
- `templates/copilot_board.html`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `next-session.md`

**Commit:** uncommitted

### Sprint P3 — Prompt-Chain & Execution — DONE (2026-04-03)
**Ziel:** Aktivierbare Marker im Copilot-Board kontrolliert starten, indem nur fokussierter Marker-Kontext vorbereitet und der Marker-Status auf `in_progress` gesetzt wird.

**Aenderungen:**
- `services/copilot_marker_service.py` um die oeffentlichen Aktivierungshelfer `is_activatable()` und `activate_marker()` erweitert; dabei wird `marker-context.md` aus exakt einem Marker erzeugt und `handoff.md` per `_write_marker()` auf `in_progress` aktualisiert
- `routes/copilot_routes.py` um `POST /api/copilot/markers/<id>/activate` erweitert, inklusive Gate-Blocked-Response ohne Nebenlogik fuer Sessions
- `static/js/copilot_board.js` zeigt nur fuer freigegebene Cards einen `OK`-Button und aktualisiert nach erfolgreicher Aktivierung den lokalen Card-Status auf `in_progress`
- `CLAUDE.md` um die Minimalregel ergaenzt, `marker-context.md` beim Start als Fokusauftrag zu behandeln
- Gezielte Tests fuer Aktivierungsservice und API hinzugefuegt

**Dateien:**
- `services/copilot_marker_service.py`
- `routes/copilot_routes.py`
- `static/js/copilot_board.js`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `CLAUDE.md`
- `next-session.md`

**Commit:** uncommitted

---

## Deferred Sprints (post-closeout v1.3-final)

> **Status 2026-04-07:** Dashboard ist mit Tag `v1.3-final` auf Feature-Freeze gesetzt.
> Die unten gelisteten Sprints sind **bewusst verschoben** ("Bezahl-Features"), nicht
> vergessen. Reaktivierung jederzeit moeglich: einen der Sprint-Plan-Files in `sprints/`
> oeffnen, neuen Arbeitssprint starten, `v1.3-final` als Ausgangspunkt nutzen.
>
> **Aktuell deferred (geschaetzter Restaufwand laut Audit 2026-04-07: ~275-355h):**
>
> - **Sprint QS** — DB-First State Consolidation (notifications/favorites/relations/ideas/settings → DB, Marker-State DB-first)
> - **Sprint 12 Voll** — preferred_workflow UI + Effectiveness-Display (Light-Version ist DONE als Sprint C)
> - **Sprint 13 Voll** — Recommendations-Tabelle + Decide-API + Tool-Control + Generatoren (MVP-Version ist DONE als Sprint D)
> - **Sprint 14** — Sprint-Flow-Tracking (DB-Tabellen `sprints` + `sprint_sessions`, Soll/Ist-Ampel, `/sprints` Page)
> - **Sprint 15** — Turn-Level Rating (Segment-Heuristik + Per-Segment-Outcome im Session-Detail)
> - **Sprint 16** — Workflow-Profile (Multi-Profil-DB-Tabelle + `/workflow` Settings-Page)
> - **Sprint 6** — DeRep Fixer (`auto_coder/derep.py` + CLI)
> - **Sprint 8** — Automation Tuning (Quality-Scan-Scheduler + neue Notification-Typen)
> - **Audit-Weiterentwicklung** — Quality-Score als `input_facts`, automatischer Trigger
> - **Sprint 20** — Product Launch Bundle (Release-Notes-Page, Changelog-Automation)
>
> Die folgenden alten Sprint-Beschreibungen (A/B/C/D) sind **historische Referenz** —
> sie wurden alle bereits abgeschlossen (siehe DONE-Bloecke weiter oben in diesem Plan).

### Sprint A — Quality Scanner Spec & Scope Lock

**Ziel:** Eine maschinenlesbare, repo-nahe Spec fuer den Quality Scanner MVP erstellen
und Scope/Abgrenzung fixieren — als direkte Vorbereitung auf die Implementierung.

**Abhaengigkeiten:** Keine. Dieser Masterplan ist bereits der Rebase; Sprint A baut
direkt darauf auf.

**Inhalte:**
- Scanner-Ziel definieren: ein Score (0-100) + Level (A-F) + Issues-Liste pro Projekt,
  rein lesend, kein automatisches Fixen.
- Klarer Scope fuer v0.1:
  - Nur Lesen/Scannen, kein automatischer Fixer.
  - Kein CI-Autotrigger, kein DeRep-Post-Processing.
  - Keine neuen Dependencies.
- Geplante Check-Module als Anforderungen auflisten (kein Code):
  - Duplication (jscpd via npx).
  - Complexity (radon, bereits installiert).
  - File Sizes (Zeilen-Limits).
  - CSS Quality (Tokens, Variablen).
  - JS Quality (Funktionsduplikate).
  - Architecture (Schicht-Regeln).
- Report-Struktur (.quality/report.json) definieren:
  - Felder: score, level, issues[], scanned_at, checks_run[].
  - Jedes Issue: check, severity, file, message.
- Abhaengigkeiten und Nicht-Ziele explizit dokumentieren:
  - Kein DeRep/Fixer (spaeter, eigenstaendig).
  - Kein UI in diesem Sprint (kommt in Sprint B).
  - Scanner funktioniert standalone via CLI, Dashboard-Integration separat.

**Ergebnis:** Am Ende von Sprint A liegt eine SPEC-QUALITY-SCANNER-MVP-001 vor,
die als Grundlage fuer die Implementierung in Sprint B dient.

---

### Sprint B — Quality Scanner MVP

**Ziel:** Erster messbarer Code-Qualitaets-Score pro Projekt. Nur Scanner, kein Fixer.

**Abhaengigkeiten:** Sprint A (Spec muss vorliegen).

**Historische Referenz:** Entspricht Sprint 5 (Package Scanner) + Teile von Sprint 7 (API/UI).

**Inhalte:**
- Scanner-Package (auto_coder/scanner.py) mit modularen Check-Modulen:
  - Duplikation, Komplexitaet, Dateigroessen, CSS-/JS-Qualitaet, Architektur-Regeln.
  - Jeder Check als eigenes Modul mit einheitlichem Interface.
- Report-Ausgabe als JSON pro Projekt (.quality/report.json).
  - Score (0-100), Level (A-F), Issues mit Severity und Kategorie.
- Einfache API im Dashboard:
  - GET /api/quality/<project> liefert aktuellen Report.
  - Score-Badge und Issue-Liste pro Projekt in der UI.
- Keine neuen Dependencies (jscpd via npx, radon bereits vorhanden).

**Ergebnis:** Jedes Projekt hat einen messbaren Quality-Score. Dieser Score kann spaeter
als input_fact in Audits einfliessen und als Signal fuer Governance dienen.

---

### Sprint C — Governance Light (informative Ampel)

**Ziel:** Audit- und Quality-Signale in eine verstaendliche, NICHT-blockierende
Projektampel uebersetzen. Informativ, nicht enforcing.

**Abhaengigkeiten:** Sprint B (Quality-Score als Eingabe). Audit v1 (Audit-Ergebnisse als Eingabe).

**Historische Referenz:** Entspricht Sprint 12 (Governance Light), angereichert mit Audit-Daten.

**Inhalte:**
- Governance-Gate-Endpoint:
  - GET /api/governance/gate/<project> gibt gruen/gelb/rot zurueck.
  - Leitet Status aus vorhandenen Daten ab: Quality-Score, letzte Audit-Ergebnisse, Outcome-Daten.
  - Regeln konfigurierbar (Schwellwerte), aber einfach gehalten.
- UI-Integration:
  - Ampel-Badge pro Projekt auf der Dashboard-Uebersicht.
  - Kurze Begruendung (z.B. "Quality Score unter 60", "Letzter Audit FAIL").
  - Drill-down auf bestehende Quality- und Audit-Detailseiten.
- Policy-Stufen (sandbox/controlled/critical) als Metadatum pro Projekt.
  - Konfig in project.json, Toggle in Projekt-Detail-UI.
  - Exportierbare Snippets fuer CLAUDE.md (Copy-to-Clipboard, kein Auto-Write).

**Ergebnis:** Aus Metriken wird erstmals Produktlogik "Wie gesund ist dieses Projekt?".
Die Ampel ist informativ und bildet die Basis fuer spaeteres Enforcement.

---

### Sprint D — LLM Command Hub MVP

**Ziel:** Markdown-basierter Command-Hub, ueber den das Dashboard definierte LLM-Aktionen
ausfuehrt. Strukturierte Commands statt Freiform-Chat.

**Abhaengigkeiten:** Sprint C (Governance-Daten als Context). Audit v1 (Audit-Ergebnisse als Context).
LLM-/Perplexity-Connector: vorhandene Integrationsmuster (z.B. gitea_service) wiederverwenden;
falls noch kein produktiver Connector existiert, in diesem Sprint einen minimalen,
wiederverwendbaren Connector ergaenzen.

**Historische Referenz:** Grundstein fuer Sprint 13 (Bidirektionaler LLM-Feedback-Loop).

**Inhalte:**
- Command-Verzeichnis (prompts/*.md) mit klarer Struktur:
  - Titel, Zweck, Parameter-Schema, Prompt-Body.
  - Commands sind versionierbar und reviewbar (Markdown im Repo).
- API-Endpoint:
  - POST /api/llm/commands/run mit command_id, context-Objekt, optionalem user_text.
  - LLM-Anbindung ueber minimalen Connector (Pattern analog gitea_service: urllib, kein SDK).
  - Ergebnis wird persistiert (Command-Run-Log).
- 2-3 konkrete Start-Commands, die ausschliesslich vorhandene Daten nutzen:
  - "Zusammenfassung des letzten Audits fuer Projekt X" (liest Audit-API).
  - "Top-5-Risiko-Dateien basierend auf vorhandenen Metriken" (liest Quality + Heatmap).
  - "Governance-Empfehlung fuer Projekt X" (liest Gate-Endpoint).
- Minimale UI:
  - Command-Auswahl (Dropdown/Liste), Parameter-Eingabe, Run-Button.
  - Ergebnis-Anzeige inline (Markdown-Rendering).
  - Kein Chat-Interface, kein Streaming, kein Framework.

**Ergebnis:** Grundstein fuer den bidirektionalen LLM-Feedback-Loop. Das Dashboard steuert
LLM-Aufgaben ueber klar definierte Commands, nicht ueber Freitext.

---

## Sprint-Abfolge

```
Sprint A       Sprint B         Sprint C          Sprint D          Copilot    Sprint E        Sprint F      Sprint G
Scanner Spec   Quality MVP      Gov Light         LLM Commands      Chat       Plan-Workflow   D&D Board     Handoff
  [DONE]         [DONE]           [DONE]            [DONE]          [DONE]       [DONE]         [DONE]       [DONE]
    │                │                │                 │              │            │              │            │
    ▼                ▼                ▼                 ▼              ▼            ▼              ▼            ▼
  Spec           Score/Issues     Gate-Ampel       3 Commands      Perplexity   Ist/Soll/Next   Kanban       YAML+MD
  erstellt       pro Projekt      green/y/red      + Persistenz    Chat+Thread  + Signale       8 Spalten    7 Sektionen
```

Die Kette **Messen → Auditieren → Bewerten → Steuern → Copilot** steht durchgaengig
mit echtem Code. Alle weiteren Sprints (Heatmap, Model-Vergleich, Sprint-Tracking,
LLM-agnostischer Connector) sind Vertiefungen innerhalb dieser Kette.

---

## Historische Referenz

Die alten Sprint-Nummern bleiben in den Einzeldateien erhalten.
Zuordnung zu den neuen Sprints:

| Alt | Thema | Neuer Sprint |
|-----|-------|-------------|
| 1-4 | Observability | DONE |
| — | Audit Core + Integration | DONE |
| 5 | Package Scanner | B |
| 6 | DeRep Fixer | nach D (eigenstaendig) |
| 7 | API/UI Integration | B (Teile), C (Teile) |
| 8 | Automation Tuning | nach D (eigenstaendig) |
| 9 | Fehler-Kategorien + AI-Scope | DONE (Status-Korrektur 2026-04-07) |
| 10 | Per-File Heatmap | DONE (Status-Korrektur 2026-04-07) |
| 11 | Model-Vergleich | DONE (Status-Korrektur 2026-04-07) |
| 12 | Governance + Feedback-Loop | C (Light-Version) |
| 13 | Bidirektionaler LLM-Control | D (MVP-Version) |
| 14 | Sprint-Flow-Tracking | nach D (eigenstaendig) |
