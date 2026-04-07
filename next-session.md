# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-07
> **Status:** Sprint QT (Plan-Reality-Sync) abgeschlossen und gepusht - Master-Plan gegen Code-Realitaet abgeglichen, Sprint 9/10/11 korrekt als DONE eingetragen, alle 5 offenen Gitea-Issues (#13-#18) mit Commit-Referenz geschlossen, Session 2026-04-06 archiviert
> **Naechste Aufgabe:** **Sprint 17 - Marker-Driven Copilot Orchestration** starten (Entscheidung 2026-04-07)

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
- D1/D2 (Session-Kontext-Links im Planning-Panel schaerfen): **verschoben** - aktuelle Bindung laeuft ueber `Marker.last_session` mit Title-Matching. Echte `spec_id`/`task_id`-FK erfordert Schema-Aenderung + Import-Anpassung, ist groesser als ein Follow-up-Task. Soll als eigener kleiner Sprint angelegt werden.
- D3/D4 (Cockpit-Activity-Card anpassen): **obsolet** - es existiert keine separate "Cockpit Activity Card" auf der Projektseite. Die Activity-Summary im Activity-Tab ist bereits das neue Format (Commit `1a1bd3e`). Kein Umbau noetig.
- D5/D6 (Archivierung): **DONE** - Session 2026-04-06 von `next-session.md` nach `next-session-archiv.md` verschoben.

**Arbeitspaket E - Dokumentation:**
- `sprints/audit-2026-04-07.md` erstellt (Prueffbericht)
- `sprints/sprint-qt-plan-reality-sync.md` erstellt (dieser Sprint-Plan mit 2-5-Min-Tasks)
- `sprints/master-plan-2026-04-01.md` aktualisiert (3 Stellen)
- `next-session.md` + `next-session-archiv.md` aktualisiert

### Geaenderte Dateien
| Datei | Aenderung |
|-------|-----------|
| `sprints/audit-2026-04-07.md` | NEU - Prueffbericht mit 8 Sektionen |
| `sprints/sprint-qt-plan-reality-sync.md` | NEU - Sprint-Plan mit 5 Arbeitspaketen, 2-5-Min-Tasks |
| `sprints/master-plan-2026-04-01.md` | Current-State + Open-Blocks + Historische-Referenz korrigiert |
| `next-session.md` | Sprint QT dokumentiert, neue Aufgaben |
| `next-session-archiv.md` | Session 2026-04-06 einsortiert |

### Gitea-Issues
- #13 closed (refs commit 89+ routes/audit_routes.py)
- #14 closed (refs afd218c)
- #15 closed (refs 8f8d08c + 6faf2c8)
- #16 closed (refs 8f8d08c)
- #18 closed (refs 5bcb2af)

---

## Naechste Session - Sprint 17 vorbereiten

### Sprint 17 - Marker-Driven Copilot Orchestration

**Plan-Datei:** `sprints/sprint-17-marker-driven-copilot-orchestration.md` (371 Zeilen, bereits ausgearbeitet)

**Ziel:** Copilot-Board von DB-zentrierten `plan_sections` in Richtung eines Markdown-gefuehrten Marker-Workflows weiterentwickeln. Eine feste Markdown-Datei pro Projekt dient als fuehrender Arbeitszustand, Status-Writeback landet in dieser Datei.

**Plan-Stand:** Inhaltlich vollstaendig (Ziel, Problem, Zielbild, Marker-Schema v1, 3 Phasen, 5 Arbeitspakete A-E, Risiken, Migrationsstrategie, Akzeptanzkriterien).

**Zwei Punkte fehlen vor Start:**

1. **Keine 2-5-Min-Task-Zerlegung** (im Gegensatz zu QT). Arbeitspakete A-E sind noch zu grob fuer direkten Abarbeitungs-Flow.
2. **Plan ist teilweise veraltet:** Er nennt `services/copilot_marker_service.py` als *neu*. Der Service existiert aber bereits aus Sprint P2/P3/P-E3 mit `read_markers`, `list_markers_for_plan`, `update_marker_status`, `update_marker_fields`, `update_execution_rating`. Der Plan wurde vor P2/P3 geschrieben.

### Empfohlener Einstieg: Reality-Check-Paket

Analog zum QT-Arbeitspaket A, bevor die eigentlichen Arbeitspakete beginnen:

- [ ] **R1** (3 Min) `services/copilot_marker_service.py` lesen, vorhandene Funktionen gegen Sprint-17 Paket B pruefen
- [ ] **R2** (3 Min) `routes/copilot_routes.py` Marker-Endpoints identifizieren, gegen Sprint-17 Paket C pruefen
- [ ] **R3** (3 Min) `templates/copilot_board.html` + `static/js/copilot_board.js` pruefen: wie werden Marker aktuell gerendert? Gegen Sprint-17 Paket D abgleichen
- [ ] **R4** (3 Min) `services/project_handoff_service.py` pruefen: aktuelle Struktur von `handoff.md` / `handoff-<plan_id>.md` dokumentieren
- [ ] **R5** (3 Min) `marker-context.md` Format mit Sprint-17 Marker-Schema v1 vergleichen
- [ ] **R6** (5 Min) Befund pro Paket A-E dokumentieren: DONE / PARTIAL / OPEN
- [ ] **R7** (10 Min) Nur noch OPEN/PARTIAL-Anteile in 2-5-Min-Tasks zerlegen, neuen Sprint-Plan `sprints/sprint-17-execution.md` anlegen oder Sprint 17 direkt erweitern

**Danach:** Phase 1 (Read-Only Marker) → Phase 2 (Write-Back) → Phase 3 (Prompt-Orchestrierung) abarbeiten.

### Verschoben aus Sprint QT
- [ ] **Session<->Spec/Task Binding verbessern:** Sessions haengen aktuell nur ueber Marker-Title-Matching an Tasks. Eigener Mini-Sprint fuer explizite `spec_id`/`task_id`-FK in der `sessions`-Tabelle oder in einer Relation-Tabelle, inkl. Import-Anpassung. Nach Sprint 17 sinnvoll, weil Marker dann die primaere Einheit sind.

### Weitere offene Sprints (aus Master-Plan, nach Sprint 17)
- Sprint QS - DB-First State Consolidation (JSON-Stores -> DB)
- Sprint 6 - DeRep Fixer (eigenstaendig)
- Sprint 8 - Automation Tuning
- Sprint 12 - Governance Feedback-Loop (Voll-Version, nur Light als Sprint C DONE)
- Sprint 13 - Bidirektionaler LLM-Control (Voll-Version, nur MVP als Sprint D DONE)
- Sprint 14 - Sprint-Flow-Tracking
- Sprint 15 - Turn-Level-Rating
- Sprint 16 - Workflow-Profiles
- Sprint 20 - Product Launch Bundle
- Audit-Weiterentwicklung: Quality-Score als `input_facts`, Governance-Gate-Integration, automatischer Trigger
