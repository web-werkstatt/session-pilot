# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-15 (Session 17: Phase 7 + Guided Flow + Implementierungs-Check)
> **Status:** Unified Cockpit Phase 7 DONE, kontextabhaengiges Next-Action-Banner live, automatischer Implementierungs-Check pro Marker.
> **Naechste Aufgabe:** Sprint `sprint-impl-check-persisting.md` umsetzen (DB-Persisting Option 2)

---

## Was gilt jetzt

Freeze-Stand **`v1.3-final`** + Unified Cockpit Phase 1-7 + AI-Control-Plane
Stufe 1 + Dispatch Stufe 2a abgeschlossen. Cockpit ist jetzt **Projekt-zentriert**
mit kontextabhaengiger Fuehrung: Next-Action-Banner fuehrt den User durch 5
einheitliche Schritte (Prompt → Checks → Bereit → Session → Abschluss). Rating
passiert zwangslaeufig beim Close, retrospektives Rating ist unterdrueckt.
Automatischer Implementierungs-Check (0-100 %) aggregiert 7 Signale pro Marker.

## Naechste Aufgaben

### Primaer: Sprint `sprint-impl-check-persisting.md` (Option 2)

- **Commit 1:** Schema-Migration `markers.implementation_percent|_signals|_checked_at`
- **Commit 2:** `get_or_calculate_progress()` + `invalidate_implementation_progress()` in `marker_implementation.py` / `workflow_core_service.py`
- **Commit 3:** Integration in `cockpit_routes` + `workflow_loop_service` (Bulk-Load, keine Doppel-Berechnung)
- **Commit 4:** Invalidation-Hooks bei Close, Rating-Skip, Activate, Settings-Change
- **Commit 5 (optional):** UI-Timestamp + manueller Recheck-Button

Aufwand ca. 2 h inkl. Tests.

### Sekundaer (offen)

- [ ] Dead Code V2: Ungenutzte Funktionen/Klassen mit Flask-Decorator-Erkennung
- [ ] Policy-Suggestions: 4 pending unter `/policies` bewerten
- [ ] `dispatch.js` IIFE → Module-Pattern (aktuell 425 Z., Panel-Code eng gekoppelt)

### GUI/UX (Codex)

- [ ] Dead-Code-Hint im Workflow-Tab mit eigenem Icon und Kategorie-Breakdown (`static/js/workflow-loop.js`, `static/css/workflow-loop.css`)
- [ ] `dead_code_summary` als kompakte Info-Karte im Workflow-Tab (`static/js/workflow-loop.js`)
- [ ] Owner separat editierbar, auch ohne Statuswechsel (`static/js/workflow-loop.js`, `routes/workflow_routes.py`)
- [ ] Microcopy Marker-Gruppen + CTA-Reihenfolge feinjustieren

## Was funktioniert (= Bestand)

| Bereich | Status |
|---|---|
| Basis-Features | DONE — Sessions, Plans, Quality, Governance, Backup |
| Workflow-System | DONE — Loop v1+v2, ADR-001 (Marker-DB, Core, Write-Guard) |
| AI-Control-Plane | DONE — ADR-002 Stufe 1 (Reviewer, Policies, Perplexity, CWO, Metriken) |
| **Unified Cockpit Phase 1-7** | **DONE — inkl. UI-Konsolidierung, Projekt-Detail bereinigt** |
| **Dispatch Sprint 2a (7-9)** | **DONE — Pull-Adapter, Gate, workflow_core, Settings, Doku** |
| **Guided Flow + Rating-v2** | **DONE — Next-Action-Banner, Close-Pflicht-Rating, 48h-Fenster, done_since-Kopplung** |
| **Implementierungs-Check** | **DONE — 7 Signale, live-Berechnung, Settings-Toggle fuer Commit-Match** |

## Wie naechste Session starten

1. Dieses File zuerst lesen
2. `sprints/master-plan-summary.md` als Rahmen lesen
3. **Sprint `sprints/sprint-impl-check-persisting.md` lesen** — enthaelt 5 Commits mit konkretem Scope
4. Bei Bedarf Referenz-Code: `services/marker_implementation.py`, `services/db_marker_schema.py`, `routes/cockpit_routes.py`

Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich 12:30.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard`
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored)

---

## Session 2026-04-15 (Session 17) — Phase 7 + Guided Flow + Implementierungs-Check

### Was wurde erledigt

**Phase 7 UI-Konsolidierung:**
- Workflow-Tab + Dispatch-Tab + Planning-Tab im Projekt-Detail ausgeblendet, Links ins Cockpit/Planning
- Cockpit-Board-UI: flex-wrap, flex-shrink:0, Seiten-Scroll statt Column-Scroll, Panel sticky
- Workflow-Ring: Hilfe-Modal, Focus-Row, kontextabhaengige Hints
- Marker-Reihenfolge per `source_line`, Breadcrumb-System, Settings Save/Cancel-Pattern
- **Aufteilung:** `plans.css` (799→3 Dateien), `base.js` (→lightbox.js), `plans.js` (→plans-board.js), `copilot-board-panel.js` (→copilot-board-chat.js), `copilot_board.html` (→_cockpit_panel_tabs.html)

**Breadcrumb-Fixes:**
- Reihenfolge: `Workspace / <projekt> / Cockpit / <Tab>` (vorher verdreht)
- Tab-Segment dynamisch (Chat/Output/Verlauf/Quelle/Dispatch) beim Panel-Oeffnen

**Guided Flow (Next-Action-Banner):**
- Kontextabhaengiges Banner oberhalb der Panel-Tabs mit genau einem Schritt + Primary-CTA
- Step-Modell vereinheitlicht: `gate_prompt → gate_checks → ready → running → close` (Ring + Banner Single Source)
- CTA-Klick oeffnet semantisch passenden Tab mit Fokus (Prompt-Textarea, Rating-Editor)
- Fallback-Navigation bei Cross-Plan-Markern statt silent return

**Rating-v2:**
- Close-Modal erzwingt `execution_score` beim `status=done` (HTTP 400 `rating_required` sonst)
- Klartext-Labels: 5 perfekt ... 0 nicht verwendbar
- 48h-Fenster: `RATING_PENDING_WINDOW` in `workflow_rating.py`, an `completed_at` aus `marker_workflow_states` gekoppelt (nicht `updated_at`)
- Zusaetzliche Bedingungen: `last_session` vorhanden, nicht `rating_skipped`
- Neue Spalte `markers.rating_skipped` + `POST /api/marker/<id>/rating-skip` + "Ignorieren"-Button

**Automatischer Implementierungs-Check:**
- `services/marker_implementation.py`: 7 Signale gewichtet zu 100 % (Prompt, Checks, Aktiviert, Session, Commit, Done, Rating)
- Commit-Match-Modus einstellbar (marker_id | plan_id | both) in Settings → General
- Card: Fortschrittsbalken + Prozent, farbkodiert rot/orange/gruen
- Panel-History-Tab: Box "Implementierungs-Check" mit Prozent + Checkliste aller 7 Signale
- Live-Berechnung bei jedem Request (DB-Persisting folgt in naechster Session)

### Git Commits (12)
```
91959d1 Feature: Automatischer Implementierungs-Check pro Marker (0-100%)
00b5c9b Refactor: Step-Modell vereinheitlichen — Backend als Single Source of Truth
801dcf0 Feature: "Ignorieren"-Button fuer Rating — Marker explizit ueberspringen
48d3c56 Fix: Rating-Pending-Fenster an Done-Zeitpunkt koppeln
0314fc2 Fix: Rating-Pending unterdruecken wenn keine Session vorhanden
9379096 Feature: Rating beim Close erzwingen + 48h-Fenster fuer Pending-Signale
4d0de4e Feature: Cockpit Next-Action-Banner — kontextabhaengige Fuehrung
75ced9e Fix: Cockpit-Breadcrumb-Reihenfolge Workspace / <projekt> / Cockpit
889adc2 Fix: Breadcrumb ergaenzt Tab-Namen wenn Cockpit-Panel offen
bbb9d8f Fix: Cockpit-Workflow-CTA oeffnet semantisch passenden Panel-Tab
d99664a Chore: Dev-Screenshots auf Root-Level per .gitignore ausschliessen
0ea3816 Feature: Unified Cockpit Phase 7 — UI-Konsolidierung + Projekt-Detail bereinigen
```

### Neue Dateien (ausgewaehlt)
| Datei | Zweck |
|-------|-------|
| `services/workflow_rating.py` | 48h-Fenster-Logik, is_rating_pending, get_done_since |
| `services/workflow_loop_signals.py` | Signal-Aggregation (ausgelagert wegen Limit) |
| `services/marker_implementation.py` | 7-Signal-Check mit git-log-grep |
| `static/js/cockpit-next-action.js` | Next-Action-Banner |
| `static/js/cockpit-close-modal.js` | Close-Modal mit Rating-Pflicht |
| `static/css/cockpit-implementation.css` | Card-Balken + Panel-Box |
| `sprints/sprint-impl-check-persisting.md` | Plan fuer naechste Session (Option 2) |
