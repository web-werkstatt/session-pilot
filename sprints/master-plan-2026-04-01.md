# Master Sprint Plan v0.3

Stand: 2026-04-01 (Session-Update)

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

AI-Scope-Filter, Fehler-Kategorien, Per-File Heatmap, Model-Vergleich,
Projekt-Governance, LLM-Steuerung, Sprint-Tracking.
Bisher: Roadmap komplett, kein Code.

### Audit-Weiterentwicklung

Audit v1 ist funktional, aber isoliert. Offene Verbindungen:
- Audit kennt noch keine Quality-Scores (Scanner-Ergebnisse als input_facts).
- Audit kennt noch keine Governance-Policies (kein Gate-Endpoint).
- Kein automatischer Trigger (nur manuell via UI oder API).

---

## Completed Sprints (diese Session)

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

---

## Open / Next Sprints

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
| 9 | Fehler-Kategorien + AI-Scope | nach D (Daten-Infrastruktur) |
| 10 | Per-File Heatmap | nach D (nutzt Quality-Score) |
| 11 | Model-Vergleich | nach D (nutzt Quality-Score) |
| 12 | Governance + Feedback-Loop | C (Light-Version) |
| 13 | Bidirektionaler LLM-Control | D (MVP-Version) |
| 14 | Sprint-Flow-Tracking | nach D (eigenstaendig) |
