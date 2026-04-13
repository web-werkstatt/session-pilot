# Sprint CWO — Context Window Optimizer

Stand: 2026-04-13
Status: PLAN (freigegeben zur Implementierung)
ADR-Bezug: ADR-002 (Observe/Review/Steer), ADR-001 (Write-Guard, Block-Marker-Parser)
Abhaengigkeiten: ADR-001 Welle 1 (DONE), ADR-002 Stufe 1 (DONE)

## Ziel

Automatisierte Analyse und Optimierung der Context-Window-Effizienz fuer alle Projekte unter `/mnt/projects/`. Das Dashboard erkennt uebergrosse Instruktionsdateien, fehlende Modularisierung und Token-Verschwendung — und fuehrt nach Rueckfrage Optimierungen durch, ohne dass Kontext verloren geht.

**Hintergrund:** Manuelle Optimierung am project_dashboard hat den Startup-Kontext von ~33.600 auf ~5.600 Tokens reduziert (-83%). Dieses Feature automatisiert denselben Prozess fuer andere Projekte.

## Architektur

Spiegelt den bestehenden Setup Reviewer (services/tool_setup_review/):

```
Observe (regel-basiert)  →  Review (Perplexity)  →  Steer (Aktionen mit Approval)
     8 Checks                  Migration-Map          5 Aktionen
     kostenlos                 Qualitaetssicherung    nach Joseph-Freigabe
```

### Kernprinzip: Migrations-Plan statt Loeschung

**Nichts wird geloescht — alles wird verschoben.** Jede Optimierung zeigt eine Zuordnungstabelle (Migration-Map) mit Vorher/Nachher pro Sektion. Joseph sieht VOR der Freigabe:
- Wo ist der Inhalt danach verfuegbar?
- Unter welcher Bedingung wird er geladen?
- Welches Risiko besteht?

### 6 Load-Modes

| Mode | Bedeutung | Beispiel |
|------|-----------|---------|
| `always` | Immer geladen (Root-CLAUDE.md, globale Rules) | Verbote, Schreib-Policies |
| `auto_subdir` | Automatisch bei Arbeit im Verzeichnis | routes/CLAUDE.md |
| `skill` | On-demand per /skill-name | /project-ops |
| `manual_read` | Muss explizit gelesen werden | Sprint-Dateien, ADRs |
| `archived` | In Archivdatei verschoben | Alte Session-Historie |
| `summarized` | Summary ersetzt Vollversion, Original bleibt | master-plan-summary.md |

### Sprint-Plan-Schutz

Sprint-Plaene werden NUR zusammengefasst wenn Status DONE ist. Offene/aktive Sprints bleiben vollstaendig erhalten. Der Context Collector erkennt den Status ueber:
1. Dateiname-Pattern (`sprint-*.md`, `adr-*.md`)
2. Inhalt: Status-Marker (`DONE`, `OFFEN`, `IN ARBEIT`)
3. Referenzen im Fokusauftrag oder master-plan-summary
4. Letzte Git-Aenderung

## Dateistruktur

```
services/context_window_optimizer/
    __init__.py                   # Re-Export-Facade
    constants.py                  # Schwellwerte, Token-Faktoren
    context_collector.py          # Sammelt Analyse-Kontext pro Projekt
    checks/
        __init__.py               # BaseCWOCheck Interface + Registry
        oversize_claude_md.py     # Check 1: CLAUDE.md > 150 Zeilen
        oversize_tool_files.py    # Check 2: AGENTS.md / GEMINI.md
        focus_file_size.py        # Check 3: Grosse Dateien im Fokusauftrag
        next_session_growth.py    # Check 4: next-session.md > 150 Zeilen
        global_rule_duplicates.py # Check 5: Duplikate mit ~/.claude/rules/
        missing_subdir_claude.py  # Check 6: Fehlende Unterverzeichnis-CLAUDE.md
        extractable_sections.py   # Check 7: Auslagerbare Listen-Sektionen
        token_budget.py           # Check 8: Gesamt-Token-Budget
    actions/
        __init__.py               # BaseAction Interface
        create_subdir_claude.py   # Aktion A: Unterverz.-CLAUDE.md erstellen
        create_summary.py         # Aktion B: Summary-Datei generieren
        rotate_next_session.py    # Aktion C: next-session.md rotieren
        remove_duplicates.py      # Aktion D: Duplikat-Sektionen (Diff-Preview)
        update_focus_rule.py      # Aktion E: Fokusauftrag anpassen (Diff-Preview)
    orchestrator.py               # Analyse-Flow + Aktions-Approval
    reviewer.py                   # Perplexity-Review der Migration-Map
    storage.py                    # DB-Persistierung

services/db_cwo_schema.py                         # DB-Schema (2 Tabellen)
routes/context_window_optimizer_routes.py          # REST-Endpoints
static/js/context-window-optimizer.js              # UI: Badge + Panel
prompts/context_window_optimizer.md                # Perplexity-Prompt
```

## 8 Checks (regel-basiert)

| # | Check | Schwellwert | Severity | Aktion |
|---|-------|-------------|----------|--------|
| 1 | CLAUDE.md Uebergroesse | >150 Z. warn, >250 Z. error | warn/error | A, D |
| 2 | AGENTS.md/GEMINI.md Uebergroesse | analog | warn/error | — |
| 3 | Grosse Datei im Fokusauftrag | >200 Z. warn, >500 Z. error | warn/error | B, E |
| 4 | next-session.md Wachstum | >150 Z. warn, >300 Z. error | warn/error | C |
| 5 | Duplikate mit globalen Rules | Jaccard >0.6 warn, >0.8 error | warn/error | D |
| 6 | Fehlende Unterverz.-CLAUDE.md | Qualifiz. Verz. ohne CLAUDE.md | info/warn | A |
| 7 | Auslagerbare Listen-Sektionen | >10 Listenelemente reine Aufz. | info | A |
| 8 | Token-Budget Gesamt | >10k info, >20k warn, >30k error | info-error | diagnostisch |

Token-Schaetzung: Zeilen * 18 (Markdown) bzw. * 15 (Code).

## 5 Aktionen (nach User-Approval)

| ID | Aktion | Schreibt | Write-Guard |
|----|--------|----------|-------------|
| A | Unterverz.-CLAUDE.md erstellen | Neue Dateien | Kein Conflict |
| B | Summary-Datei erstellen | Neue Datei | Kein Conflict |
| C | next-session.md rotieren | next-session.md + Archiv | Policy-Ausnahme oder Diff-Preview |
| D | Duplikat-Sektionen entfernen | CLAUDE.md | Diff-Preview (UNMARKED = geschuetzt) |
| E | Fokusauftrag-Regel anpassen | CLAUDE.md | Diff-Preview (UNMARKED = geschuetzt) |

Aktionen D+E generieren nur Diff-Previews. Joseph bestaetigt manuell.

## Perplexity-Review (Qualitaetssicherung)

Perplexity bewertet die Migration-Map NACH der regelbasierten Analyse:
- Ist die vorgeschlagene Migration sicher?
- Welche Sektionen haben Verbots-Charakter und muessen im Root bleiben?
- Sind Sprint-Status-Einschaetzungen korrekt?
- Fehlt ein Zugangsweg?

Aufruf nur auf Knopfdruck ("Review anfordern"), context_hash-Dedup verhindert Mehrfach-Calls.

**Prompt:** `prompts/context_window_optimizer.md`
**Eingabe:** Projekt-Kontext + regel-basierte Findings + vorgeschlagene Migrations
**Ausgabe:** Migration-Assessment mit safe_to_move, risk, reason pro Sektion + overall_confidence

## Datenmodell

```python
@dataclass
class MigrationEntry:
    section_title: str        # "Route-Module (58 Zeilen)"
    source: str               # "CLAUDE.md Zeile 39-96"
    target: str               # "routes/CLAUDE.md"
    load_mode: str            # always | auto_subdir | skill | manual_read | archived | summarized
    load_condition: str       # "Automatisch wenn in routes/ gearbeitet wird"
    tokens_saved: int
    content_loss: str         # none | summarized | archived
    risk: str                 # none | low | medium

@dataclass
class CWOFinding:
    check_id: str
    severity: str             # error | warning | info
    title: str
    detail: str
    current_value: Any
    threshold: Any
    estimated_tokens: int
    actionable: bool
    action_id: str | None
    migration_map: list[MigrationEntry]
    recommendation: str
```

## DB-Schema

**`cwo_analyses`** — Eine Zeile pro Projekt:
- project_name (PK), total_tokens, token_budget_rating, findings (JSONB), migration_map (JSONB), file_inventory (JSONB), context_hash, perplexity_review (JSONB), perplexity_confidence (INTEGER), review_context_hash, created_at, updated_at

**`cwo_action_log`** — Aktions-Protokoll:
- id (SERIAL PK), project_name, action_id, status (proposed/approved/executed/failed/rejected), parameters (JSONB), result (JSONB), proposed_at, executed_at

## REST-API

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/project/<name>/cwo/analyze` | Analyse durchfuehren (context_hash-Dedup) |
| GET | `/api/project/<name>/cwo/analyze` | Letzte Analyse laden |
| POST | `/api/cwo/analyze-all` | Alle Projekte analysieren |
| GET | `/api/cwo/overview` | Uebersicht: Projekte nach Token-Budget |
| POST | `/api/project/<name>/cwo/review` | Perplexity-Review anfordern |
| GET | `/api/project/<name>/cwo/review` | Letztes Review laden |
| GET | `/api/project/<name>/cwo/actions` | Vorgeschlagene Aktionen |
| POST | `/api/project/<name>/cwo/actions/<id>/approve` | Aktion freigeben |
| POST | `/api/project/<name>/cwo/actions/<id>/execute` | Freigegebene Aktion ausfuehren |

## UI-Integration

**Phase 1:** Badge + Banner im Tool-Files-Modal (analog Setup-Reviewer):
- Token-Budget-Badge (gruen/gelb/rot) am Tool-Files-Button
- CWO-Banner im Modal mit Findings + Migrations-Map + Aktions-Vorschlaegen
- "Review anfordern"-Button fuer Perplexity-Qualitaetssicherung
- Approve/Execute-Buttons pro Aktion

**Phase 2:** Eigene `/cwo`-Uebersichtsseite mit allen Projekten, sortiert nach Token-Budget.

### Navigation (Phase 2)

Die CWO-Seite gehoert in die Sidebar unter **STEUERN**, direkt nach Quality:

```
STEUERN
  Quality        — Code-Qualitaet
  Context Window — AI-Kontext-Qualitaet (CWO)
  Governance
  Policies
  Audits
  Commands
```

Begruendung: CWO ist ein Quality-Check fuer Context-Windows (automatisierte Checks, Severity-Bewertung, Empfehlungen) — nicht Planning (plant nichts) und nicht Workflow (steuert keine Marker-Transitionen). Gleiches UX-Pattern wie `/quality`: alle Projekte mit Score-Uebersicht, sortierbar.

## Wiederverwendbare Services

- `path_resolver.resolve_project_path()`, `project_scanner.scan_projects()`
- `block_marker_parser.parse_blocks()`, `write_guard.safe_write()`
- `perplexity_service.query_perplexity()`, `db_service.execute()`
- Setup-Reviewer Patterns: context_hash-Dedup, Lazy Schema, Upsert, query_fn-Injection

## Tickets

### Phase 1a — Analyse (Read-Only)

| # | Ticket | Dateien |
|---|--------|---------|
| 1.1 | DB-Schema + Constants + Grundgeruest | `db_cwo_schema.py`, `constants.py`, `__init__.py` |
| 1.2 | Context Collector | `context_collector.py` |
| 1.3 | Check-Framework + Token-Budget | `checks/__init__.py`, `checks/token_budget.py` |
| 1.4 | Dateigroessen-Checks (1-4) | 4 Check-Module |
| 1.5 | Struktur-Checks (5-7) | 3 Check-Module |
| 1.6 | Orchestrator + Storage | `orchestrator.py`, `storage.py` |
| 1.7 | REST-Endpoints (Analyse) | `routes/context_window_optimizer_routes.py` |
| 1.8 | UI (Analyse-Anzeige) | `context-window-optimizer.js`, Template |

### Phase 1b — Perplexity-Review

| # | Ticket | Dateien |
|---|--------|---------|
| 1.9 | Perplexity-Prompt erstellen | `prompts/context_window_optimizer.md` |
| 1.10 | Reviewer-Modul (Perplexity-Call + Dedup) | `reviewer.py`, Tests |
| 1.11 | UI: Review-Button + Bewertungs-Anzeige | JS-Erweiterung |

### Phase 2 — Aktionen mit Approval

| # | Ticket | Dateien |
|---|--------|---------|
| 2.1 | Action-Framework + Action-Log | `actions/__init__.py`, DB-Erweiterung |
| 2.2 | Aktion C: next-session.md Rotation | `actions/rotate_next_session.py` |
| 2.3 | Aktion A: Unterverz.-CLAUDE.md | `actions/create_subdir_claude.py` |
| 2.4 | Aktion B: Summary erstellen | `actions/create_summary.py` |
| 2.5 | Aktionen D+E: Duplikate + Fokus (Diff-Preview) | 2 Action-Module |
| 2.6 | REST-Endpoints (Aktionen) | Route-Erweiterung |
| 2.7 | UI (Aktions-Panel) | JS-Erweiterung |

### Phase 3 — Perplexity-generierte Inhalte (Optional)

- Perplexity generiert Unterverz.-CLAUDE.md Inhalte (statt regelbasierte Kopie)
- LLM-gestuetzte Summary-Generierung (statt H2-Extraktion)
- Perplexity-gestuetzte Sektions-Klassifikation (Verbots-Charakter vs. selbst-entdeckbar)

## Status-Nachtrag

- **2026-04-13:** Phase 1a (Tickets 1.1-1.8) DONE — Analyse, Orchestrator, REST-API, UI (Badge+Panel) live
- **2026-04-13:** Phase 1b (Tickets 1.9-1.11) DONE — Perplexity-Prompt, Reviewer-Modul, Review-UI + Guidance live

## Verifikation

1. CWO auf `project_dashboard` laufen lassen — sollte niedrigen Score zeigen (bereits optimiert)
2. CWO auf ein nicht-optimiertes Projekt laufen lassen — sollte Findings und Aktionen vorschlagen
3. Aktionen einzeln freigeben und ausfuehren
4. Token-Budget vorher/nachher vergleichen
5. Neue Claude-Code-Session im optimierten Projekt starten — Funktionalitaet pruefen
