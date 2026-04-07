# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-07
> **Status:** Sprint QT (Plan-Reality-Sync) abgeschlossen - Master-Plan gegen Code-Realitaet abgeglichen, Sprint 9/10/11 korrekt als DONE eingetragen, alle 5 offenen Gitea-Issues (#13-#18) mit Commit-Referenz geschlossen, Session 2026-04-06 archiviert
> **Naechste Aufgabe:** Sprint QS Phase 1 (JSON-Stores -> DB) ODER Sprint 17 (Marker-Driven Copilot Orchestration) starten

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
- **OFFEN:** `marker-context.md` enthaelt Testmarker `test-cockpit-2026-04-05`, Plan 142
- Laut CLAUDE.md-Regel nicht eigenmaechtig aenderbar - User-Rueckfrage erforderlich

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

## Naechste Session

### Offene Entscheidung
- [ ] **Marker-Context:** Testmarker `test-cockpit-2026-04-05` behalten oder `marker-context.md` leeren? (User-Freigabe noetig)
- [ ] **Naechster Sprint:** Sprint QS Phase 1 (DB-First State Consolidation, JSON-Stores -> DB) ODER Sprint 17 (Marker-Driven Copilot Orchestration)?

### Verschoben aus Sprint QT
- [ ] **Session<->Spec/Task Binding verbessern:** Sessions haengen aktuell nur ueber Marker-Title-Matching an Tasks. Eigener Mini-Sprint fuer explizite `spec_id`/`task_id`-FK in der `sessions`-Tabelle oder in einer Relation-Tabelle, inkl. Import-Anpassung.

### Weitere offene Sprints (aus Master-Plan)
- Sprint 6 - DeRep Fixer (eigenstaendig)
- Sprint 8 - Automation Tuning
- Sprint 12 - Governance Feedback-Loop (Voll-Version, nur Light als Sprint C DONE)
- Sprint 13 - Bidirektionaler LLM-Control (Voll-Version, nur MVP als Sprint D DONE)
- Sprint 14 - Sprint-Flow-Tracking
- Sprint 15 - Turn-Level-Rating
- Sprint 16 - Workflow-Profiles
- Sprint 20 - Product Launch Bundle
- Audit-Weiterentwicklung: Quality-Score als `input_facts`, Governance-Gate-Integration, automatischer Trigger
