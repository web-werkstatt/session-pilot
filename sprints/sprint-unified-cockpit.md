# Sprint: Unified Cockpit — Konsolidierung der operativen Oberflaeche

Stand: 2026-04-14
Status: **IN PROGRESS** (Phase 1-3 fertig, Phase 4-7 offen)
Grundlage: ADR-002 Stufe 2a (Dispatch), Unified-Cockpit-Plan (`~/.claude/plans/soft-discovering-horizon.md`)

## Ziel

Drei ueberlappende operative Oberflaechen (Cockpit-Board, Projekt-Detail Workflow-Tab,
Projekt-Detail Dispatch-Tab) zu einer einzigen konsolidierten Cockpit-Seite zusammenfuehren.

Das Cockpit wird **Projekt-zentriert** statt Plan-zentriert. Alle Marker eines Projekts
sind sichtbar, Workflow-Uebersicht und Dispatch sind direkt integriert. Das bestehende
visuelle Design bleibt unveraendert.

## Kontext

### Probleme im Ist-Zustand

1. **Cockpit** (`/copilot?plan_id=N`) ist Plan-zentriert — zeigt oft "Keine AI Tasks"
   weil Marker ueber mehrere Plaene verteilt oder noch nicht importiert sind.
2. **Projekt-Detail → Workflow-Tab** hat die beste Workflow-Visualisierung (SVG-Ring,
   Marker-Gruppen, Aktionen) aber kein Dispatch.
3. **Projekt-Detail → Dispatch-Tab** dupliziert die Cockpit-Panel-Funktionalitaet.

### Design-Prinzip

Das visuelle Design des Cockpit-Boards bleibt exakt wie es ist. Keine neuen Layouts,
keine neuen Card-Styles, keine CSS-Ueberarbeitung. Nur fehlende Funktionalitaet wird
hinzugefuegt und bestehende Features konsolidiert.

## Architektur-Entscheidungen

| Entscheidung | Begruendung |
|---|---|
| Projekt-first, Plan-optional | `/copilot?project=<name>` zeigt alle Marker; loest "Keine AI Tasks"-Problem |
| Bestehendes Board-Layout beibehalten | 4 Kanban-Spalten (Todo/Generating/Done/Blocked) bleiben; Workflow-Status als Badge |
| Workflow-Loop JS wiederverwenden | `PROJECT_NAME` parametrisiert statt neu geschrieben; WL-Komponenten laufen im Cockpit |
| Rechtes Panel unveraendert | Chat/Output/History/Source/Dispatch bleiben exakt wie jetzt |
| Sprint-Sections bleiben | An gleicher Stelle, aber kollapsiert wenn keine Marker zugeordnet |
| Workflow-Uebersicht als Info-Zeile | Zwischen Progress-Bar und Sprint-Sections, kein neues Layout |

## Commits (sequentielle Umsetzung)

### Commit 1 — Backend: Aggregierter Projekt-API-Endpoint [DONE]

**Ziel:** Ein Endpoint liefert alles was das Cockpit fuer ein Projekt braucht.

**Dateien:**
- neu: `routes/cockpit_routes.py`
- erweitert: `routes/__init__.py`

**Scope:**
- `GET /api/cockpit/project/<name>` liefert:
  - `markers[]` — alle Marker des Projekts (via `workflow_core_service.get_markers()`)
  - `workflow{}` — aus `build_workflow_loop_data()` (Steps, Groups, Signals, Current/Next)
  - `plans[]` — aktive Plaene fuer Plan-Filter-Dropdown

**Akzeptanzkriterien:**
- [x] Endpoint liefert 15 Marker, 5 Steps, 6 Plaene fuer `project_dashboard`
- [x] Kein Seiteneffekt auf bestehende Endpoints

---

### Commit 2 — Workflow-Loop JS parametrisieren [DONE]

**Ziel:** `WorkflowLoop` ohne `PROJECT_NAME`-Global nutzbar machen.

**Dateien:**
- erweitert: `static/js/workflow-loop-state.js` (+`WL.projectName`, `WL.getProjectName()`)
- erweitert: `static/js/workflow-loop.js` (`loadWorkflowLoop(projectName?)`)
- erweitert: `static/js/workflow-loop-actions.js` (5x `PROJECT_NAME` → `WL.getProjectName()`)
- erweitert: `static/js/workflow-loop-cards.js` (`WL.onPlanningClick` Callback + Fallback)

**Akzeptanzkriterien:**
- [x] `WL.getProjectName()` faellt auf `PROJECT_NAME` zurueck wenn `WL.projectName` null
- [x] Workflow-Tab auf Projekt-Detail-Seite funktioniert unveraendert
- [x] Keine Regressionen in SVG-Ring, Summary, Actions

---

### Commit 3 — Cockpit-Route: project= Parameter [DONE]

**Ziel:** `/copilot?project=<name>` als neuer Einstieg ins Cockpit.

**Dateien:**
- erweitert: `routes/copilot_routes.py` (Projekt-Modus + Projekt-aus-Plan-Ableitung)
- erweitert: `templates/copilot_board.html` (`COCKPIT_PROJECT` + `PLAN_ID` nullable)

**Scope:**
- `/copilot?project=<name>` → Projekt-Modus (neu, primaer)
- `/copilot?plan_id=N` → loest Projekt aus Plan auf (abwaertskompatibel)
- `/copilot` ohne Parameter → Redirect zum letzten aktiven Plan (unveraendert)

**Akzeptanzkriterien:**
- [x] `/copilot?project=project_dashboard` → HTTP 200, `COCKPIT_PROJECT = "project_dashboard"`
- [x] `/copilot?plan_id=1853` → HTTP 200, `PLAN_ID = 1853`, `COCKPIT_PROJECT = "project_dashboard"`
- [x] Bestehende Cockpit-Funktionalitaet (Board, Panel, Drag&Drop) unveraendert

---

### Commit 4 — Workflow-Uebersicht im Cockpit

**Ziel:** Kompakte Workflow-Info zwischen Progress-Bar und Sprint-Sections.

**Dateien:**
- neu: `templates/_cockpit_workflow_overview.html` (~30 Zeilen)
- neu: `static/css/cockpit-workflow.css` (~60 Zeilen)
- erweitert: `templates/copilot_board.html` (Partial einbinden + CSS/JS laden)
- erweitert: `static/js/copilot_board.js` (Workflow-Daten laden + rendern)

**Scope:**
- Kompakter SVG-Ring (~200px) inline neben Summary-Text
- Current-Marker + Next-Marker als Pill-Badges
- Workflow-Signale (Governance, Quality, Audit) als farbige Dots
- Kollapsibel via Toggle-Button
- Daten aus `/api/cockpit/project/<name>` (bereits vorhanden)

**Akzeptanzkriterien:**
- [ ] Workflow-Uebersicht sichtbar unter Progress-Bar
- [ ] SVG-Ring zeigt 5 Steps mit korrektem Current-Step
- [ ] Current/Next-Marker anklickbar (oeffnet Panel)
- [ ] Kollaps-Toggle funktioniert
- [ ] Kein visueller Bruch mit bestehendem Design

---

### Commit 5 — Board: Projekt-Datenquelle + Workflow-Badges

**Ziel:** Board zeigt alle Marker des Projekts (nicht nur eines Plans).

**Dateien:**
- erweitert: `static/js/copilot_board.js` (`_loadSections` auf Cockpit-API umstellen)
- erweitert: `static/js/copilot-board-panel.js` (Workflow-Status im Panel-Header)

**Scope:**
- Wenn `COCKPIT_PROJECT` gesetzt und `PLAN_ID` null: Marker via `/api/cockpit/project/<name>`
- Wenn `PLAN_ID` gesetzt: bisheriges Verhalten (Plan-scoped, abwaertskompatibel)
- Workflow-Status als Badge auf bestehenden Cards ("Rating offen", "Write Back", "Bereit")
- Assignment-Badge auf Cards wenn Dispatch-Assignment aktiv
- Plan-Herkunft als Label auf Cards (wenn Marker aus verschiedenen Plaenen)

**Akzeptanzkriterien:**
- [ ] `/copilot?project=project_dashboard` zeigt alle 15 Marker auf dem Board
- [ ] `/copilot?plan_id=1853` zeigt nur Marker dieses Plans (unveraendert)
- [ ] Workflow-Status-Badges sichtbar auf Cards
- [ ] Panel oeffnet sich bei Klick auf Card, Dispatch-Tab funktioniert
- [ ] Drag&Drop aendert Marker-Status wie bisher

---

### Commit 6 — Sprint-Sections demoten + Plan-Filter

**Ziel:** Sprint-Sections werden sekundaer, Plan-Filter im Header.

**Dateien:**
- erweitert: `static/js/copilot_board.js` (`_renderSprintSections` + Plan-Filter)
- erweitert: `templates/copilot_board.html` (Plan-Filter-Dropdown im Header)

**Scope:**
- Sprint-Sections starten kollapsiert wenn keine Marker zugeordnet
- Toggle-Button zum Ein-/Ausklappen
- Plan-Filter-Dropdown im Header: "Alle Plaene" (Default) + Liste aktiver Plaene
- Bei Plan-Filter: nur Marker dieses Plans anzeigen + Sprint-Sections aufklappen

**Akzeptanzkriterien:**
- [ ] Sprint-Sections kollapsiert bei `/copilot?project=...` ohne Plan-Filter
- [ ] Plan-Filter wechselt Board-Inhalt ohne Seiten-Reload
- [ ] Sprint-Sections expandieren bei aktivem Plan-Filter
- [ ] "Alle Plaene" setzt Filter zurueck

---

### Commit 7 — Projekt-Detail bereinigen (Deferred)

**Ziel:** Keine duplizierten operativen UIs.

**Dateien:**
- erweitert: `templates/project_detail.html`
- erweitert: `static/js/project-detail.js`

**Scope:**
- Workflow-Tab → kompakte Zusammenfassung + "Im Cockpit oeffnen" Button
- Dispatch-Tab → entfernen oder durch Link zum Cockpit ersetzen
- Workflow-Loop JS/CSS bleibt geladen (fuer Zusammenfassung)

**DEFERRED** — erst nach stabilem Cockpit (fruehestens uebernachste Session).

**Akzeptanzkriterien:**
- [ ] Workflow-Tab zeigt Zusammenfassung + Cockpit-Link
- [ ] Kein dupliziertes Dispatch-UI mehr
- [ ] Alle Deep-Links zum Cockpit funktionieren

---

## Was dieser Sprint NICHT anfasst

- **Push/Webhook (Variante C)** — eigener Sprint 2b
- **Neues Board-Layout** — bestehende 4 Spalten bleiben
- **Neue Card-Styles** — bestehende Marker-Card-Optik bleibt
- **Cross-Projekt-Cockpit** — nur ein Projekt gleichzeitig
- **Automatischer Marker-Import** — "Sprint → Marker" Button bleibt manuell

## Bekannte Risiken + Gegenmassnahmen

| Risiko | Gegenmassnahme |
|--------|---------------|
| `copilot_board.js` ist bei 495 Zeilen (Limit 500) | Commit 5 muss Code umstrukturieren, ggf. Helper extrahieren |
| Board-Rendering fuer 15+ Marker aus verschiedenen Plaenen | Plan-Label pro Card zeigt Herkunft; Plan-Filter reduziert Komplexitaet |
| Workflow-Loop-Daten und Copilot-Marker-Daten haben leicht unterschiedliche Felder | Normalisierung im Frontend; `/api/cockpit/project` liefert beides |

## Neue Dateien (Uebersicht)

| Datei | Typ | Commit |
|-------|-----|--------|
| `routes/cockpit_routes.py` | Backend | 1 |
| `templates/_cockpit_workflow_overview.html` | Template-Partial | 4 |
| `static/css/cockpit-workflow.css` | Styles | 4 |

## Verifizierung

1. Nach Commit 3: Beide URL-Modi funktionieren (`?project=` und `?plan_id=`)
2. Nach Commit 4: Workflow-Ring + Summary im Cockpit sichtbar
3. Nach Commit 5: Alle Projekt-Marker auf dem Board, Dispatch im Panel funktioniert
4. Nach Commit 6: Plan-Filter wechselt Board-Inhalt, Sprint-Sections kollapsierbar
5. Durchgehend: `/copilot?plan_id=N` funktioniert wie zuvor (abwaertskompatibel)
6. Durchgehend: Projekt-Detail Workflow-Tab zeigt unveraenderte Visualisierung

## Status-Nachtraege

### Session 2026-04-14 (Commits 1-3)

- Commit 1 (Backend): `routes/cockpit_routes.py` mit aggregiertem Endpoint, getestet
- Commit 2 (JS-Parametrisierung): 4 Workflow-Loop-Dateien, `WL.getProjectName()` mit Fallback
- Commit 3 (Route): `/copilot?project=` akzeptiert, Projekt aus Plan abgeleitet
- Git-Commit: `a514bcb` (alle 3 Phasen zusammen)
- Abwaertskompatibilitaet verifiziert: Workflow-Tab auf Projekt-Detail-Seite unveraendert

### Session 2026-04-14 (Commit 4)

- Commit 4 (Workflow-Uebersicht): SVG-Ring 240px, Current/Next-Pills, Signal-Dots, Kollaps-Toggle
- Neue Dateien: `_cockpit_workflow_overview.html`, `cockpit-workflow.css`, `cockpit-workflow.js`
- Projekt-Modus-Fix: `_loadPlanInfo`/`_loadSections` nutzen Cockpit-API wenn PLAN_ID null
- Plan-Switcher nach `copilot-board-shared.js` extrahiert (copilot_board.js: 495→477 Zeilen)
- `workflow-loop-summary.css` im Cockpit geladen (SVG-Farben fehlten initial)
- Git-Commit: `3e6b696`
- Alle 5 Akzeptanzkriterien verifiziert im Browser
