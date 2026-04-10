# Sprint ADR-001 Welle 1 — DB-First Marker Core + Write-Guard

Stand: 2026-04-10
Status: **FREIGEGEBEN** (Review Joseph)
Grundlage: `sprints/adr-001-db-first-marker-core-tool-adapter.md`

## Ziel

Die 4 freigegebenen Deliverables aus ADR-001 umsetzen:
Marker-DB, workflow_core_service, Write-Guard mit Block-Markern, Update-Pfad fuer Tool-Dateien.

Damit wird das Architektur-Fundament gelegt, auf dem alle weiteren Workflow-Features aufbauen.

## Relation zu bestehenden Plaenen

### `project-dashboard-workflow-v2-system-plan.md` (Workflow-UI, 5 Sprints)

**Beziehung: Dieser Sprint baut das Fundament unter dem Workflow-v2-Plan.**

- Workflow-v2 Sprint 1 (Datenmodell, Transitions, API) ist **DONE** — wird nicht gebrochen,
  sondern erweitert: `marker_workflow_states` bekommt `executor_tool`, Marker-Definitionen
  wandern in eigene DB-Tabelle.
- Workflow-v2 Sprint 2-5 (UI-Aktionen, Grafik, Sync, UX-Haertung) profitieren direkt:
  Sie lesen dann aus einer sauberen DB statt aus handoff.md.
- **Kein Doppelarbeit-Risiko:** Workflow-v2 ist GUI/UX, dieser Sprint ist Datenschicht.

| Workflow-v2 Sprint | Unser Impact |
|---|---|
| Sprint 1 (Datenmodell) | DONE, wird erweitert (Marker-Tabelle + executor_tool) |
| Sprint 2 (Aktionen) | Profitiert: Aktionen schreiben ueber Core-Service |
| Sprint 3 (Grafik) | Profitiert: Grafik liest aus DB statt handoff.md |
| Sprint 4 (Sync) | **Wird teilweise ersetzt:** Session-Rueckkanal laeuft ueber Core |
| Sprint 5 (UX-Haertung) | Profitiert: Stabilere Daten = bessere UX |

### `polished-finding-haven.md` (Dead-Code im Workflow)

**Beziehung: Unabhaengig, kein Konflikt.**

Dead-Code-Findings nutzen die bestehende Workflow-API (`signals.priority_hints`).
Unser Sprint aendert die Datenquelle unter der API, nicht die API selbst.
Dead-Code-Plan kann parallel oder danach umgesetzt werden.

### `sprint-cp-control-plane-loop-closure.md` (Control-Plane Loop)

**Beziehung: Wird teilweise durch diesen Sprint erledigt.**

Sprint CP Arbeitspaket A (Fachliches Workflow-Modell konsolidieren) wird durch den
`workflow_core_service` (Ticket 2) direkt adressiert. Arbeitspakete B-F (Gate, Post-Execution,
Rating, Signale, UX) bleiben als eigenstaendige Folgearbeit bestehen.

### `sprint-qs-db-first-state-consolidation.md` (DB-First Strategie)

**Beziehung: Phase 2 wird durch diesen Sprint implementiert.**

Sprint QS Phase 2 ("Marker-State von Markdown-only zu DB-first") ist exakt das,
was Ticket 1+2 umsetzen. Phase 1 (JSON-Stores migrieren) und Phase 3 (UI entkoppeln)
bleiben als separate Folgearbeit.

### `sprint-17-marker-driven-copilot-orchestration.md` (Marker-Driven Copilot)

**Beziehung: Architekturprinzip wird umgekehrt, Code bleibt.**

Sprint 17 ist DONE. Der Parser (`copilot_marker_format.py`), der Service-Layer
(`copilot_marker_service.py`) und die UI bleiben erhalten. Nur die Datenquelle
aendert sich: DB statt handoff.md. Das Architekturprinzip "Markdown fuehrt" wird
durch ADR-001 umgekehrt (Nachtrag bereits gesetzt).

---

## Freigabe-Matrix (Review Joseph, 2026-04-10)

| Kategorie | Punkt | Freigabe |
|---|---|---|
| **Jetzt** | Marker-DB + Importer | **Go** |
| **Jetzt** | `workflow_core_service` | **Go** |
| **Jetzt** | block_marker_parser + write_guard + Lock | **Go** |
| **Jetzt** | Update-Pfad fuer Tool-Dateien | **Go** |
| Spaeter | Tool-Registry | Backlog |
| Spaeter | Multi-Tool marker-context | Backlog |
| Spaeter | Capability-/Skill-Modell | Backlog |
| Spaeter | Perplexity-Suggestion-Layer | Backlog |
| Vorsicht | DeepSeek/Qwen als native Tools | Nur ueber Wrapper |
| Vorsicht | Grosse DB-Erweiterung in einem Rutsch | Kleine Migrationen |

---

## Architektur-Korrekturen (aus Review)

### Wrapper statt Modell modellieren

Chinesische LLMs haben keine eigenen CLIs. Sie laufen ueber Wrapper (Cline, aider, Continue).
Darum modellieren wir das tatsaechliche Runtime-Werkzeug:

```
tool_type = "cline"    backend_model = "deepseek"
tool_type = "aider"    backend_model = "qwen"
tool_type = "claude"   backend_model = "claude-opus-4-6"
```

### Atomic Write Pattern

Nicht nur Locking, sondern: `temp -> fsync/close -> rename`.
Damit bleiben Dateien bei Crash nicht halbgeschrieben.

### Idempotente Re-Generierung

Derselbe Core-State muss bei erneutem Schreiben denselben generierten Block erzeugen.
- Keine Timestamps im generierten Content (nur im Marker-Attribut `updated=`)
- Deterministische Sortierung der Marker
- Stabile Formatierung (kein Trailing-Whitespace-Jitter)

---

## Ticket 1: Marker-DB-Tabelle + Importer aus handoff.md

**Ziel:** Marker-Definitionen in eigene DB-Tabelle heben.

**Scope:**
- Neue Tabelle `markers` mit Schema-Migration in `services/db_marker_schema.py` (lazy, idempotent)
- Importer-Funktion die bestehende `handoff.md` parst und Marker in DB ueberfuehrt
- Idempotent: Re-Run aktualisiert bestehende, legt neue an, loescht nichts
- Legacy-Marker (`in_progress`/`done` ohne Rating) als `review_needed` markieren
- Minimal `executor_tool` VARCHAR(30) in `marker_workflow_states`

**Akzeptanzkriterien:**
- [ ] Tabelle `markers` existiert mit allen Pflichtfeldern aus Marker-Dataclass
- [ ] Importer liest handoff.md und schreibt korrekt in DB
- [ ] Zweiter Importer-Lauf: 0 neue Eintraege, nur Updates wo noetig
- [ ] Bestehende `marker_workflow_states` und `workflow_transitions` bleiben intakt

**Dateien:**
- `services/db_marker_schema.py` (neu)
- `services/marker_importer.py` (neu)
- `services/db_service.py` (ensure_marker_schema aufrufen)
- `services/copilot_marker_format.py` (Parser wiederverwenden)

---

## Ticket 2: workflow_core_service als Domaenenschicht

**Ziel:** Duenne Lese-/Schreibschicht die Marker-Zugriff zentralisiert.

**Scope:**
- `services/workflow_core_service.py` (neu) mit:
  - `get_markers(project_name, plan_id=None)` — liest aus DB
  - `get_marker(project_name, marker_id)` — einzelner Marker
  - `update_marker_state(project_name, marker_id, new_state, executor_tool=None)`
  - `get_handoff_view(project_name)` — Read-Model fuer handoff.md-Regenerierung
- `workflow_loop_service.py` Zeile 37: auf Core umleiten
- `copilot_marker_service.py`: Lesen/Schreiben via Core

**Akzeptanzkriterien:**
- [ ] `workflow_loop_service` liest Marker aus DB via Core
- [ ] `copilot_marker_service` delegiert an Core
- [ ] Bestehende API-Endpoints liefern identische Responses (Regression)
- [ ] Bestehende Tests gruen

**Dateien:**
- `services/workflow_core_service.py` (neu)
- `services/workflow_loop_service.py` (Zeile 37-41 umbauen)
- `services/copilot_marker_service.py` (auf Core umleiten)

**Relation:** Adressiert Sprint CP Arbeitspaket A ("Fachliches Workflow-Modell konsolidieren").
Adressiert Sprint QS Phase 2 ("Marker-State DB-first").

---

## Ticket 3: block_marker_parser + write_guard + Atomic Write

**Ziel:** Produktfeature das manuelle Inhalte in Markdown-Dateien technisch schuetzt.

**Scope:**
- `services/block_marker_parser.py` (neu):
  - Erkennt MANUAL und DASHBOARD-GENERATED Bloecke
  - Unmarkierter Text gilt als manuell (= geschuetzt)
  - `parse_blocks(filepath)` → Liste von Block-Objekten
  - `get_protected_ranges(filepath)` → geschuetzte Zeilenbereiche
- `services/write_guard.py` (neu):
  - `validate_write(filepath, new_content, writer_source)` → Dry-Run
  - `safe_write(filepath, new_content, writer_source)` → Schreibt nur wenn erlaubt
  - Atomic Write: temp → fsync → rename
  - File-Lock: `fcntl.flock()` waehrend Write
  - Blockiert wenn geschuetzte Bereiche veraendert wuerden
  - Idempotent: Selber Core-State erzeugt selben generierten Block
- `project_handoff_service.write_handoff()` muss durch write_guard gehen

**Akzeptanzkriterien:**
- [ ] Parser erkennt MANUAL und DASHBOARD-GENERATED Bloecke korrekt
- [ ] Unmarkierter Text wird als geschuetzt klassifiziert
- [ ] write_guard blockiert Schreibvorgang der geschuetzte Bereiche aendert
- [ ] write_guard erlaubt Aenderungen nur in GENERATED-Bloecken mit passendem source
- [ ] Atomic Write: Bei Abbruch keine halbgeschriebenen Dateien
- [ ] Dry-Run zeigt geplante Aenderungen ohne zu schreiben
- [ ] Idempotent: Re-Write ohne State-Aenderung erzeugt keinen Diff

**Dateien:**
- `services/block_marker_parser.py` (neu)
- `services/write_guard.py` (neu)
- `services/project_handoff_service.py` (write_handoff via Guard)

**Relation:** Ist Kernfeature fuer alle Projekte, nicht nur project_dashboard.
Schuetzt bestehende manuelle Inhalte bei jedem kuenftigen Mirror-Write oder Tool-Update.

---

## Ticket 4: Update-Pfad fuer bestehende Tool-Instruktionsdateien

**Ziel:** Bestehende CLAUDE.md/AGENTS.md/GEMINI.md sicher aktualisieren.

**Scope:**
- `instruction_generator.py` erweitern:
  - Bestehende Datei lesen
  - MANUAL-Bereich erkennen und schuetzen (via block_marker_parser)
  - Nur DASHBOARD-GENERATED Block anhaengen/aktualisieren
- UI: Button "Regenerate tool instructions (safe)" mit Dry-Run/Preview
- Alle Schreibvorgaenge via `write_guard.safe_write()`

**Akzeptanzkriterien:**
- [ ] Bestehende CLAUDE.md mit 200 manuellen Zeilen: nach Update intakt
- [ ] DASHBOARD-GENERATED Block korrekt eingefuegt/aktualisiert
- [ ] Dry-Run zeigt Diff ohne zu schreiben
- [ ] UI-Button funktional mit Preview-Dialog
- [ ] Idempotent: Zweites Regenerate erzeugt keinen Diff

**Dateien:**
- `services/instruction_generator.py` (erweitern)
- `services/scaffolding_service.py:214-226` (Update-Pfad)
- `routes/project_routes.py` (neuer Endpoint)
- `templates/project_detail.html` (Button + Preview-Dialog)
- Nutzt: `services/block_marker_parser.py`, `services/write_guard.py`

---

## Abhaengigkeiten

```
Ticket 1 (Marker-DB)  ──→  Ticket 2 (Core-Service)
                                ↓
Ticket 3 (Write-Guard)  ──→  Ticket 4 (Tool-Update)
```

Tickets 1+3 koennen **parallel** gestartet werden.
Ticket 2 braucht Ticket 1. Ticket 4 braucht Ticket 3.

## Verifikation

1. Marker aus bestehender handoff.md in DB importiert? Idempotent bei Re-Run?
2. `workflow_core_service` liest Marker aus DB, nicht aus handoff.md?
3. Bestehendes Projekt mit manueller CLAUDE.md → manueller Text nach Update intakt?
4. write_guard blockiert Schreibvorgang der geschuetzte Bereiche aendert?
5. Dry-Run zeigt geplante Aenderungen ohne zu schreiben?
6. Atomic Write: Bei Abbruch keine halbgeschriebenen Dateien?
7. Bestehende API-Responses identisch (Regression)?

## Was dieser Sprint NICHT anfasst

- Workflow-v2 Sprints 2-5 (GUI/UX) — bleiben als Folgearbeit
- Tool-Registry — Backlog
- Multi-Tool marker-context — Backlog
- DeepSeek/Qwen-Integration — erst nach Core
- Capability-/Skill-Modell — nachgelagert
- Perplexity-Review-Layer — nachgelagert
- JSON-Store-Migration (Sprint QS Phase 1) — unabhaengig

---

## Status-Nachtraege

### Ticket 3 — DONE (2026-04-10)

**Commit:** `44f52f6` Feature: ADR-001 Prio 2 — Block-Marker-Parser + Write-Guard (7/7 Akzeptanzkriterien)

Alle 7 Akzeptanzkriterien erfuellt:
- [x] Parser erkennt MANUAL und DASHBOARD-GENERATED Bloecke korrekt
- [x] Unmarkierter Text wird als geschuetzt klassifiziert
- [x] write_guard blockiert Schreibvorgang der geschuetzte Bereiche aendert
- [x] write_guard erlaubt Aenderungen nur in GENERATED-Bloecken mit passendem source
- [x] Atomic Write: temp -> fsync -> rename (keine halbgeschriebenen Dateien)
- [x] Dry-Run: validate_write() prueft ohne zu schreiben
- [x] Idempotent: Re-Write ohne State-Aenderung erzeugt keinen Diff

Zusaetzlich umgesetzt:
- Fail-closed Parser bei defekten/ungeschlossenen Block-Markern
- File-Lock (fcntl.flock) mit Re-Validierung nach Lock-Akquise (TOCTOU-Schutz)
- SOURCE_ALLOWLIST Policy als Uebergang fuer handoff.md (Copilot-Marker-Format)
- 37 neue Tests, 635 gesamt, null Regressionen
- Integration in project_handoff_service.write_handoff()

Dateien: `services/block_marker_parser.py`, `services/write_guard.py`, `services/project_handoff_service.py`, `tests/test_block_marker_parser.py`, `tests/test_write_guard.py`, `tests/test_write_guard_hardening.py`
