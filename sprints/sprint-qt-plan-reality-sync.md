# Sprint QT - Plan-Reality-Sync #sprint-sprint-qt-plan-reality-sync

Stand: 2026-04-07
Status: DONE 2026-04-07
Grundlage: `sprints/audit-2026-04-07.md`

## Ziel

Den Master-Plan, die Sprint-Einzeldateien, Gitea-Issues und den tatsaechlichen Code-Stand in einen konsistenten Zustand bringen, bevor weitere Feature-Sprints (QS, 17) gestartet werden.

Danach: Kleinen, sofort greifbaren Nutzwert liefern durch Aufraeumen der offenen Hotfix-Follow-ups aus `next-session.md`.

## Motivation

Das Audit 2026-04-07 hat drei konkrete Drift-Punkte gefunden:

1. Sprint 9/10/11 haben Code im Repo, sind aber im Master-Plan als "kein Code" gelistet.
2. Gitea-Issues #13-#18 referenzieren Sprints, die laut Master-Plan DONE sind.
3. Commit-Hashes in mehreren Sprint-Eintraegen stehen auf `n/a`, die Git-History-Rueckverfolgung ist unvollstaendig.

Ein weiterer Feature-Sprint auf dieser Basis verstaerkt die Drift.

## Scope

- **In scope:** Master-Plan-Status korrigieren, Gitea-Issues triagieren, Marker-Context klaeren, 3 konkrete Follow-ups aus `next-session.md` umsetzen.
- **Out of scope:** Neue Features, Architektur-Umbauten, Sprint QS, Sprint 17.

## Abhaengigkeiten

Keine. Reiner Bestandsaufnahme- und Aufraeum-Sprint.

---

## Arbeitspakete

Jedes Arbeitspaket ist in 2-5-Minuten-Tasks zerlegt. Reihenfolge: A vor B vor C.

### Arbeitspaket A - Master-Plan Reality-Check (~20 Min) - DONE 2026-04-07 #spec-arbeitspaket-a-master-plan-reality-check-20-min-done-2026-04-07

- [x] **A1** `services/ai_scope_service.py` (86 Zeilen): `extract_tool_names`, `extract_ai_flags`, `analyze_from_db_messages`
- [x] **A2** `routes/session_filter_routes.py` (187 Zeilen): `/api/sessions/outcome-reasons`, `/filters`, `/<uuid>/outcome-detail`, `/scope-stats`
- [x] **A3** `services/file_touch_service.py` (386 Zeilen): `extract_file_touches`, `extract_file_touches_git`, `save_file_touches`, `_build_heatmap_where`, `get_file_heatmap`, `get_risk_radar`
- [x] **A4** `routes/analytics_routes.py` (96 Zeilen): `/api/analytics/file-heatmap/<project>`, `/api/analytics/risk-radar/<project>`
- [x] **A5** `services/model_recommendation.py` (437 Zeilen) + `routes/model_comparison_routes.py`: Page `/model-comparison`, Endpoints `/model-comparison`, `/model-by-stack`, `/model-trend`, `/model-recommendation`. UI: `templates/model_comparison.html`.
- [x] **A6** Sprint 9 Status: **DONE**. Alle Kernartefakte vorhanden (AI-Scope-Flags in allen Importern, Backfill-Script, Outcome-API, Filter-API). Vollstaendige Akzeptanzkriterien-Abdeckung nicht bis ins letzte Detail verifiziert.
- [x] **A7** Sprint 10 Status: **DONE**. Heatmap + Risk-Radar Backend und Frontend vollstaendig, in `project_detail.html` integriert (`loadFileHeatmap`, `loadRiskRadarPanel`).
- [x] **A8** Sprint 11 Status: **DONE**. Modell-Vergleich Seite + 4 API-Endpoints + Empfehlungs-Engine.
- [x] **A9** Master-Plan-Block "AI Governance Analytics" sowie Historische-Referenz-Tabelle mit Status-Korrektur 2026-04-07 aktualisiert. Current-State-Block ergaenzt.

### Arbeitspaket B - Gitea-Issue-Triage (~15 Min) - DONE 2026-04-07 #spec-arbeitspaket-b-gitea-issue-triage-15-min-done-2026-04-07

- [x] **B1** Issue #13 Body gelesen: Audit-Integration (POST /api/audits/run, /audits-Seite, Sidebar). Verifiziert: `routes/audit_routes.py` Zeile 89 hat `/api/audits/run`, `templates/audit.html` + Sidebar-Link in `base.html` Zeile 88 vorhanden.
- [x] **B2** Issue #14 Body gelesen: Sprint P3 Prompt-Chain, Body nennt selbst Commit `afd218c`. `git log` bestaetigt: `afd218c Feature: Sprint P3 Prompt-Chain activation` auf main.
- [x] **B3** Issue #15 Body gelesen: P2-Branch-Isolierung. `git log --grep="refs #15"` findet `8f8d08c Feature: Sprint P2 marker board from handoff refs #15` und `6faf2c8 Feature: integrate P2 handoff board onto main refs #15` (via PR #17).
- [x] **B4** Issue #16 Body gelesen: Sprint P2 marker board. Dieselben Commits wie #15 (8f8d08c).
- [x] **B5** Issue #18 Body gelesen: Copilot CSS + handoff regeneration. Verifiziert: `templates/copilot_board.html` Zeilen 6-7 laden `design-tokens.css` + `components.css`, `static/css/components.css` hat `ui-panel`, `ui-button`, `ui-badge`. Commit `5bcb2af fix: Copilot CSS and handoff regeneration refs #18` auf main.
- [x] **B6** Alle 5 Issues mit Schliess-Kommentar + Commit-Referenz geschlossen (Gitea API).

### Arbeitspaket C - Marker-Context klaeren (~5 Min) - DONE 2026-04-07 #spec-arbeitspaket-c-marker-context-klaeren-5-min-done-2026-04-07

- [x] **C1** User-Rueckfrage: "Ist `marker-context.md` noch relevant?" -> Antwort: **behalten**.
- [x] **C2** entfaellt (keine Aktion noetig)
- [x] **C3** entfaellt (Marker bleibt wie er ist)

### Arbeitspaket D - next-session.md Follow-ups (~25 Min) - TEILWEISE DONE #spec-arbeitspaket-d-next-session-md-follow-ups-25-min-teilweise-done

- [x] **D1** `services/plan_structure_helpers.py` geprueft: Session-Bindung laeuft ueber `Marker.last_session` (einzelne Session-ID pro Marker) und `build_task_items` matcht Tasks an Marker ueber **Titel-Lowercase**. Sessions bubble up Spec->Sprint->Plan via `collect_session_summaries`.
- [x] **D2** **verschoben**: Echte Session <-> Spec/Task Bindung erfordert Schema-Aenderung (FK `spec_id`/`task_id` in `sessions` oder Relation-Tabelle) + Anpassung aller Importer. Groesser als ein 5-Min-Task. Als eigener Mini-Sprint in `next-session.md` eingetragen.
- [x] **D3** `templates/project_detail.html` + `static/js/project-detail.js` gepruefte: es existiert **keine** separate "Cockpit Activity Card" auf der Overview-Seite. Der Activity-Tab (`ptab_sessions`, Zeile 209-211) rendert bereits die neue Activity-Summary via `project-detail.js` Zeilen 277-316.
- [x] **D4** **obsolet**: kein Card zum Umbauen vorhanden. D3 zeigt, dass die Summary-Komponente bereits ueberall verwendet wird wo sie soll.
- [x] **D5** `next-session-archiv.md` geprueft: juengster Eintrag war `Session 2026-04-05`, Session 2026-04-06 fehlte.
- [x] **D6** Session 2026-04-06 Block aus `next-session.md` nach `next-session-archiv.md` verschoben.

### Arbeitspaket E - Master-Plan & next-session.md updaten (~10 Min) - DONE 2026-04-07 #spec-arbeitspaket-e-master-plan-next-session-md-updaten-10-min-done-2026-04-07

- [x] **E1** Master-Plan: neuer Abschnitt "Sprint QT - Plan-Reality-Sync - DONE (2026-04-07)" mit Ergebnissen aller Arbeitspakete in "Completed Sprints (diese Session)" ergaenzt.
- [x] **E2** Master-Plan-Prioritaeten: Sprint QS und Sprint 17 als naechste Kandidaten im `next-session.md` benannt.
- [x] **E3** `next-session.md` vollstaendig neu geschrieben: Sprint QT dokumentiert, offene Entscheidungen, verschobene Tasks, Sprint-Roadmap.
- [ ] **E4** Commit steht noch aus (wird vom User / in naechstem Schritt ausgeloest).

---

## Definition of Done

- Master-Plan listet Sprint 9/10/11 mit realistischem Status (DONE / PARTIAL, mit kurzer Beschreibung des tatsaechlichen Umfangs)
- Alle Gitea-Issues #13-#18 sind entweder geschlossen oder mit einem aktuellen Kommentar versehen, der den tatsaechlichen Zustand beschreibt
- `marker-context.md` ist entweder geleert/geloescht oder enthaelt einen real verfolgten Auftrag (nach User-Freigabe)
- Die drei Follow-ups aus `next-session.md` (Session-Binding, Cockpit-Activity-Card, Archivierung) sind umgesetzt oder bewusst verschoben
- `next-session.md` beschreibt den neuen Ausgangspunkt mit klarem naechsten Sprint

## Nicht-Ziele

- Keine Code-Aenderungen an Sprint 9/10/11 Substance (reines Dokumentations-Sync)
- Kein Beginn von Sprint QS oder Sprint 17
- Keine Master-Plan-Umstrukturierung, nur Status-Korrektur

## Risiken

- **A6-A8 koennten zeigen, dass Sprint 9/10/11 nur teilweise implementiert sind.** In diesem Fall: Status als PARTIAL dokumentieren, konkrete Rest-Luecken als eigene kleine Folge-Sprints anlegen, NICHT in diesem Sprint mit-implementieren.
- **C1 kann ergeben, dass der Marker aktiv ist.** Dann nur Beschreibung schaerfen, nicht loeschen.
- **D2 kann groesser werden als geplant**, wenn die SQL-Join-Struktur komplex ist. In diesem Fall: D2 herausloesen und als eigenen kleinen UI-Sprint anlegen.

## Geschaetzte Dauer

~75 Min fokussierte Arbeit. Bei jedem Block sind die Tasks so geschnitten, dass sich nach jedem Arbeitspaket ein sauberer Abbruch-/Commit-Punkt ergibt.
