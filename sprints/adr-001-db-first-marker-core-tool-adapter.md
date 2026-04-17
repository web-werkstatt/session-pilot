# ADR-001: DB-First Marker Core + Tool-Adapter, Compatible Migration #sprint-adr-001-db-first-marker-core-tool-adapter-compatible-migration

Stand: 2026-04-10
Status: **ACCEPTED**
Entscheider: Joseph

## Kontext

Das Projekt hat ueber mehrere Sprints hinweg ein hybrides System aufgebaut:

- **Marker-Definitionen** leben in `handoff.md` als HTML-Kommentare mit JSON-Payload (Sprint 17, DONE).
- **Workflow-States** sind bereits DB-first in `marker_workflow_states` + `workflow_transitions` (Sprint Workflow-v2 Sprint 1, DONE).
- **Session-Marker-Binding** ist DB-backed via `sessions.marker_id` (Sprint SB, DONE).

Das fuehrt zu einem architektonisch inkonsistenten Zustand: Workflow-States und Session-Bindings lesen aus der DB, aber die Marker-Definitionen selbst kommen aus `handoff.md`. Zwei Sprint-Plaene widersprechen sich:

- **Sprint 17** (DONE) postuliert: *"DB kann Cache sein, aber nicht die Wahrheit des Marker-Zustands"*
- **Sprint QS** (GEPLANT) postuliert: *"Marker mittelfristig DB-first"*

Zusaetzlich fehlen:
- Ein zentraler `workflow_core_service` als Domaenenschicht
- Ein Tool-Adapter-Service, der generierte Bloecke in CLAUDE.md/AGENTS.md/GEMINI.md pflegt
- Ein explizites Konfliktmodell bei Divergenz zwischen handoff.md und DB
- Ein abstraktes Capability-/Skill-Modell

## Entscheidung

### 1. Marker und Workflow-State werden DB-first #spec-1-marker-und-workflow-state-werden-db-first

Ab sofort gilt: Marker-Definitionen und -State werden **DB-first** gefuehrt.

- `handoff.md` wird zum Handoff-/Mirror-/Export-Artefakt degradiert, nicht mehr fuehrende Runtime-Quelle.
- Fruehere Aussagen in Sprint 17 und Sprint CP (*"handoff.md bleibt immer fuehrend"*) gelten als ueberholt.
- Sprint QS Phase 2 wird damit zur bindenden Architekturrichtung.

### 2. workflow_core_service als zentrale Domaenenschicht #spec-2-workflow-core-service-als-zentrale-domaenenschicht

Ein neuer `services/workflow_core_service.py` wird eingefuehrt als kanonische Schicht fuer:

```
Plan -> Sprint -> Spec -> Marker -> WorkflowState -> HandoffState -> Zeiger
```

- `workflow_loop_service.py` und `copilot_marker_service.py` werden schrittweise so umgebaut, dass sie nur noch ueber den Core lesen/schreiben.
- Marker werden nie mehr direkt aus `handoff.md` geparst fuer operative Logik.

### 3. Kompatible Migration fuer bestehende Projekte #spec-3-kompatible-migration-fuer-bestehende-projekte

- Bestehende `handoff.md`-Dateien werden beim Lesen importiert, normalisiert und in den DB-Core ueberfuehrt.
- Konflikte (handoff.md sagt X, DB sagt Y) werden **angezeigt**, nicht heimlich ueberschrieben.
- Write-Back-Richtung ist ausschliesslich: `Core (DB) -> handoff.md (Mirror) -> Tool-Bloecke`.
- Manuelle Aenderungen in `handoff.md` ausserhalb der generierten Marker-Bloecke bleiben erhalten.

### 4. Tool-Adapter-Service (nach dem Core) #spec-4-tool-adapter-service-nach-dem-core

Ein neuer `services/tool_profile_adapter_service.py` pflegt pro AI-Tool einen klar markierten Block:

```markdown
<!-- DASHBOARD-GENERATED:START tool=claude updated=2026-04-10 -->
... generierter Inhalt ...
<!-- DASHBOARD-GENERATED:END -->
```

- Ersetzt nur den markierten Bereich, nie manuelle Inhalte davor/danach.
- Erweitert den bestehenden `instruction_generator.py` (der nur bei neuen Projekten greift) um Update-Faehigkeit fuer bestehende Projekte.

### 5. Capability-/Skill-Modell als nachgelagerte Erweiterung #spec-5-capability-skill-modell-als-nachgelagerte-erweiterung

- Zuerst nur ein simples DB-Modell + Dashboard-Anzeige, ohne komplexe Logik.
- Spaeter nutzen die Tool-Adapter Capabilities fuer Tool-spezifische Hinweise.
- **Nicht** Voraussetzung fuer den Core-Umbau oder den Tool-Adapter.

### 6. Perplexity-Copilot als Read-Only-Validierungsschicht #spec-6-perplexity-copilot-als-read-only-validierungsschicht

Der bestehende Perplexity-Copilot wird zum **Faktenpruefer / Reviewer** ueber dem Canonical Core:

- **Prueft** generierte `handoff.md` und Tool-Bloecke gegen den DB-Core auf Inkonsistenzen, Luecken und schlechte Beschreibungen.
- **Warnt** bei Divergenz zwischen Mirror-Artefakten und kanonischem State.
- **Hilft** bessere Prompts, Marker-Texte und Tool-Hinweise zu formulieren.
- **Aendert nie direkt** den State in der DB — rein beratend, nie schreibend.
- Der Perplexity-Copilot arbeitet ausschliesslich vorschlagsbasiert: Er liest Core- und Mirror-Artefakte, macht Verbesserungsvorschlaege und Konsistenzhinweise, aber jede Aenderung wird manuell von Joseph als letztem Prueforgan abgenickt oder verworfen.

Architektur-Schnitt: **State in der DB, Textartefakte und Verstaendlichkeit bei LLMs — geprueft und verbessert ueber den Perplexity-Copilot.**

```
                    +-----------------------+
                    |   workflow_core_service |
                    |   (DB = kanonisch)     |
                    +-----------+-----------+
                                |
                 +--------------+--------------+
                 |              |              |
           handoff.md    CLAUDE.md/etc.   Copilot-Board
           (Mirror)      (Tool-Adapter)   (UI)
                 |              |
                 +--------------+
                        |
              +-------------------+
              | Perplexity-Copilot |
              | (Read-Only Review) |
              +-------------------+
```

Damit entsteht ein klarer Dreiklang:
1. **Core** (DB) — besitzt den State
2. **Adapter** (Write-Back) — erzeugt lesbare Artefakte
3. **Reviewer** (Perplexity) — prueft Qualitaet und Konsistenz der Artefakte

## Schreib-Policies und Block-Marker (Governance-Leitplanken)

Executor (Claude, Codex, Gemini, jedes Modell) duerfen nicht auf Modelldisziplin vertrauen muessen.
Das System muss unautorisierte Eingriffe in manuellen Text **technisch und regelbasiert** verhindern.

### Schreib-Policies pro Datei #spec-schreib-policies-pro-datei

| Datei | Policy | Bedeutung |
|---|---|---|
| `next-session.md` | **append-only** | Neue Bloecke/Historie anfuegen, bestehende Zeilen nie aendern/loeschen |
| `handoff.md` | **generated-blocks-only** | Nur markierte Bereiche ueberschreiben |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | **generated-blocks-only** | Nur markierte Bereiche ueberschreiben |
| `sprints/*.md` | **append-only** | Nachtraege anfuegen, bestehenden Text nie aendern |

### Block-Marker-Konvention #spec-block-marker-konvention

- `<!-- MANUAL:START owner=joseph -->` ... `<!-- MANUAL:END -->` — fuer jeden Executor schreibgeschuetzt
- `<!-- DASHBOARD-GENERATED:START source=<service> updated=<datum> -->` ... `<!-- DASHBOARD-GENERATED:END -->` — darf nur vom genannten Service ueberschrieben werden
- Unmarkierter Text gilt als manuell (= geschuetzt)

### Produktfeature: Block-Marker-Parser und Write-Guard #spec-produktfeature-block-marker-parser-und-write-guard

Dies ist kein reines Regelthema, sondern ein **Kernfeature des Produkts**, das auch fuer andere Kunden/Projekte greift.

#### `services/block_marker_parser.py` (neuer Service)

Aufgaben:
- Parst beliebige Markdown-Dateien und erkennt `MANUAL` und `DASHBOARD-GENERATED` Bloecke
- Liefert eine strukturierte Map: welche Zeilen sind manuell, welche generiert, welche unmarkiert
- Unmarkierter Text wird als manuell (= geschuetzt) klassifiziert

```python
# API-Entwurf
def parse_blocks(filepath: str) -> list[Block]:
    """Erkennt MANUAL und DASHBOARD-GENERATED Bloecke in einer Datei."""

def get_protected_ranges(filepath: str) -> list[tuple[int, int]]:
    """Liefert Zeilenbereiche die geschuetzt sind (manuell + unmarkiert)."""

def get_generated_ranges(filepath: str) -> list[GeneratedBlock]:
    """Liefert generierte Bloecke mit source-Attribut."""
```

#### `services/write_guard.py` (neuer Service)

Aufgaben:
- Wird von jedem Service aufgerufen, der Markdown-Dateien schreibt (tool_profile_adapter, handoff write-back, etc.)
- Vergleicht den geplanten neuen Inhalt gegen die Block-Map der bestehenden Datei
- **Blockiert** Schreiboperationen, die geschuetzte Bereiche veraendern wuerden
- **Erlaubt** nur Aenderungen innerhalb von DASHBOARD-GENERATED Bloecken mit passendem `source`
- **Erlaubt** Anfuegen neuer Bloecke am Ende (append-only Policy)
- Liefert einen strukturierten Diff mit Erklaerung, was blockiert wurde und warum

```python
# API-Entwurf
def validate_write(filepath: str, new_content: str, writer_source: str) -> WriteResult:
    """Prueft ob der Schreibvorgang erlaubt ist.
    
    Returns:
        WriteResult mit .allowed (bool), .violations (list), .protected_diff (str)
    """

def safe_write(filepath: str, new_content: str, writer_source: str) -> WriteResult:
    """Schreibt nur wenn validate_write erlaubt. Sonst Fehler mit Erklaerung."""
```

#### Schreib-Policy-Registry

Dateitypen und ihre Policies werden zentral konfiguriert, nicht hardcoded:

```python
WRITE_POLICIES = {
    "next-session.md":    "append-only",
    "handoff.md":         "generated-blocks-only",
    "CLAUDE.md":          "generated-blocks-only",
    "AGENTS.md":          "generated-blocks-only",
    "GEMINI.md":          "generated-blocks-only",
    "sprints/*.md":       "append-only",
    "marker-context.md":  "explicit-only",
}
```

Neue Projekte bekommen diese Policies automatisch via Scaffolding. Bestehende Projekte koennen sie uebernehmen oder anpassen.

#### Integration in bestehende Services

- `tool_profile_adapter_service` ruft `write_guard.safe_write()` auf, bevor er Tool-Bloecke schreibt
- `project_handoff_service.write_handoff()` ruft `write_guard.safe_write()` auf
- `workflow_core_service` nutzt den Write-Guard fuer jeden Mirror-Write-Back
- API-Endpoints koennen `validate_write()` als Dry-Run anbieten (Vorschau was sich aendern wuerde)

#### Fuer andere Projekte/Kunden

Das Feature ist generisch: Jedes Projekt das ueber das Dashboard verwaltet wird, bekommt automatisch Block-Marker-Schutz. Der Write-Guard ist nicht project_dashboard-spezifisch, sondern schuetzt beliebige Markdown-Dateien in beliebigen Projekten unter `/mnt/projects/`.

### Herkunft #spec-herkunft

Anlassfall: Session 2026-04-10, Claude hat bestehenden manuellen Text in `next-session.md` eigenmaechtig gekuerzt/umformuliert. Problem ist kein Modelldefekt, sondern fehlende Governance-Leitplanken. Executor ohne klare Schreib-Policy wird frueher oder spaeter „optimieren", was nicht optimiert werden soll. Daraus folgt: **technische Durchsetzung im Produkt, nicht Vertrauen auf Modelldisziplin.**

## Umsetzungsreihenfolge

| Prio | Was | Abhaengigkeit |
|------|-----|---------------|
| 1 | `workflow_core_service.py` + Marker-DB-Tabelle | - |
| 2 | `block_marker_parser.py` + `write_guard.py` (Produktfeature) | - |
| 3 | Migration bestehender handoff.md-Marker in DB | Prio 1 |
| 4 | `workflow_loop_service` + `copilot_marker_service` auf Core umbauen | Prio 1+3 |
| 5 | Write-Back: Core -> handoff.md (Mirror, via Write-Guard) | Prio 2+4 |
| 6 | `tool_profile_adapter_service.py` (via Write-Guard) | Prio 2+5 |
| 7 | Capability-/Skill-Modell | unabhaengig, kann parallel |
| 8 | Perplexity-Copilot als Review-Layer ueber Artefakte | Prio 5+6 |

## Betroffene Sprints und Dokumente

| Dokument | Aenderung |
|----------|-----------|
| `sprint-17-marker-driven-copilot-orchestration.md` | Nachtrag: Architekturprinzip "DB nicht Wahrheit" gilt als ueberholt durch ADR-001 |
| `sprint-cp-control-plane-loop-closure.md` | Nachtrag: "handoff.md bleibt immer fuehrend" gilt als ueberholt durch ADR-001 |
| `sprint-qs-db-first-state-consolidation.md` | Phase 2 wird bindend; Referenz auf ADR-001 |
| `sprint-workflow-v2-full-system.md` | Sprint 4 (Session-Sync) muss DB-first-Modell beruecksichtigen |
| `master-plan-2026-04-01.md` | Data Persistence Consolidation-Block aktualisieren |
| `CLAUDE.md` | Neues Pattern: workflow_core_service + Tool-Adapter |

## Konsequenzen

### Positiv #spec-positiv

- Genau eine primaere Wahrheit pro Datentyp (Marker -> DB)
- Saubere Domaenenschicht statt verteilter Koordination
- Bestehende Projekte bleiben lauffaehig (kompatible Migration)
- Tool-Instruktionsdateien werden automatisch aktuell gehalten
- Konflikte werden sichtbar statt versteckt
- Perplexity-Copilot kann als unabhaengiger Reviewer die Qualitaet der generierten Artefakte pruefen, ohne den State zu gefaehrden

### Negativ / Risiken #spec-negativ-risiken

- Umfangreicher Umbau der Marker-Lese-/Schreibpfade
- Uebergangsphase mit zwei Marker-Quellen (handoff.md + DB) bis Migration abgeschlossen
- Write-Back-Logik muss manuelle handoff.md-Abschnitte zuverlaessig erkennen und bewahren
- Tool-Adapter muss mit unterschiedlichen bestehenden CLAUDE.md-Formaten umgehen koennen

### Leitregeln fuer die Umsetzung #spec-leitregeln-fuer-die-umsetzung

- Kein Big-Bang: schrittweise Migration, jeder Schritt einzeln testbar
- Importer-Phase (handoff.md -> DB) muss idempotent und re-runnable sein
- UI zeigt Konflikte explizit an, statt sie aufzuloesen
- Bestehende Tests muessen bei jedem Schritt gruen bleiben
- `handoff.md` wird nie geloescht, nur zum Mirror degradiert

## Alternativen (verworfen)

### A: handoff.md-first beibehalten (Status quo) #spec-a-handoff-md-first-beibehalten-status-quo

Verworfen, weil: wachsende Inkonsistenz zwischen DB-States und Markdown-Definitionen, kein sauberes Konfliktmodell moeglich, kein Tool-Adapter ohne kanonische DB-Quelle.

### B: Kompletter Neubau ohne Migration #spec-b-kompletter-neubau-ohne-migration

Verworfen, weil: bestehende Projekte mit handoff.md wuerden brechen, zu hohes Risiko fuer ein produktives System.

### C: Zwei gleichrangige Quellen mit Sync #spec-c-zwei-gleichrangige-quellen-mit-sync

Verworfen, weil: Sprint QS explizit als Anti-Pattern identifiziert ("dieselbe fachliche Information gleichrangig in JSON, Markdown und DB").

## Nachtrag 2026-04-11 — Folge-ADR 002

Prio 7 (Capability-/Skill-Modell) wird bis auf Weiteres zurueckgestellt.
Begruendung: Nutzen nicht nachgewiesen. Die Policy-Schicht aus ADR-002 Stufe 1b
loest dasselbe Problem minimal-invasiver und DB-gestuetzt.

Prio 8 (Perplexity-Copilot als Review-Layer) wird erweitert und vorgezogen
durch **ADR-002: AI-Control-Plane fuer kooperierende Multi-LLM-Systeme**.
Die Reviewer-Rolle aus Abschnitt 6 dieses ADRs bleibt verbindlich, wird aber
auf den Multi-Tool-Kontext erweitert (context_drift, Policy-Reviewer, spaeter
Tool-Routing, Uebergabe-Pruefung, Trendwaechter).

Alle anderen Prioritaeten (1-6) bleiben DONE und sind Fundament von ADR-002.
Der Write-Guard und der Block-Marker-Parser aus Prio 2 bleiben die einzige
erlaubte Schreibschicht fuer generierte Markdown-Bloecke.

Verweis: `sprints/adr-002-ai-control-plane-multi-llm-reviewer.md` (bindend).
Sprint-Plan: `sprints/sprint-adr002-stufe1-control-plane.md`.
