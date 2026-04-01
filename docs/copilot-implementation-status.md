# Copilot & LLM Integration — Implementierungsstatus

Stand: 2026-04-01

---

## Ueberblick

Das Dashboard hat zwei getrennte LLM-Subsysteme:

1. **LLM Command Hub** (Sprint D) — Strukturierte, vordefinierte Commands als Markdown
2. **Copilot Chat** (SPEC-COPILOT-CHAT-PERPLEXITY-001) — Freier Chat mit Perplexity

Beide nutzen denselben Perplexity-Connector (`services/perplexity_service.py`),
haben aber getrennte Tabellen, Routes, UI und Logik.

---

## 1. LLM Command Hub

### Zweck
Definierte LLM-Aktionen auf Basis vorhandener Projekt-Daten ausfuehren.
Commands liegen versionierbar als Markdown im Repo.

### Dateien

| Typ | Pfad | Beschreibung |
|-----|------|-------------|
| Service | `services/llm_command_service.py` | Command-Loader, Parser, Context-Resolver, Run-Logik, Persistenz |
| Routes | `routes/llm_command_routes.py` | API-Blueprint (4 Endpoints) |
| Template | `templates/llm_commands.html` | Dashboard-Seite |
| JS | `static/js/llm-commands.js` | Frontend: Command-Auswahl, Run, Ergebnis, Recent Runs |
| CSS | `static/css/llm-commands.css` | Styling |
| Tests | `tests/test_llm_commands.py` | 15 Abnahmetests |
| Commands | `prompts/*.md` | Markdown-Command-Definitionen |

### API-Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/api/llm/commands` | Alle verfuegbaren Commands auflisten |
| POST | `/api/llm/commands/run` | Command ausfuehren (command_id + context + optional user_text) |
| GET | `/api/llm/commands/runs` | Letzte Command-Runs (limit Parameter) |
| GET | `/llm-commands` | Dashboard-Seite |

### DB-Tabelle: `command_runs`

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | SERIAL PK | Run-ID |
| command_id | VARCHAR(100) | Referenz auf prompts/<command_id>.md |
| input_context | JSONB | Eingabe-Parameter |
| user_text | TEXT | Optionaler Freitext |
| output_text | TEXT | LLM-Antwort |
| status | VARCHAR(20) | success / failure |
| error_info | TEXT | Fehlerbeschreibung (nullable) |
| model | VARCHAR(100) | Verwendetes LLM-Modell |
| duration_ms | INTEGER | Ausfuehrungsdauer |
| created_at | TIMESTAMPTZ | Zeitstempel |

### Start-Commands (prompts/)

| Datei | command_id | Zweck | Datenquellen |
|-------|-----------|-------|-------------|
| `audit-summary.md` | audit-summary | Audit-Zusammenfassung fuer ein Projekt | Governance-Gate API |
| `risk-files.md` | risk-files | Top-5-Risiko-Dateien aus Quality-Daten | Quality-Report JSON |
| `governance-recommendation.md` | governance-recommendation | Governance-Empfehlung mit Massnahmen | Gate + Quality APIs |

### Command-Dateiformat

```markdown
---
command_id: audit-summary
title: Audit-Zusammenfassung
purpose: Fasst den letzten Audit-Run zusammen.
parameters:
  - name: project
    type: string
    required: true
    description: Projektname
data_sources:
  - GET /api/governance/gate/{project}
---

Prompt-Body mit {{project}} und {{gate_data}} Platzhaltern...
```

### Context-Resolver

Der Service laedt automatisch Daten basierend auf Platzhaltern im Prompt:
- `{{project}}` → Projektname aus context
- `{{gate_data}}` → GET /api/governance/gate/{project} Ergebnis
- `{{quality_data}}` → .quality/report.json (Top-20 Issues + Summary)

---

## 2. Copilot Chat

### Zweck
Freier Chat mit Perplexity als technischer Copilot.
Projektbezogen, mit Thread-Historie und Plan-Bindung.

### Dateien

| Typ | Pfad | Beschreibung |
|-----|------|-------------|
| Service | `services/copilot_service.py` | Chat-Logik, Thread-Historie, Persistenz |
| Routes | `routes/copilot_routes.py` | API-Blueprint (3 Endpoints) |
| Template | `templates/copilot.html` | Chat-UI mit Sidebar |
| JS | `static/js/copilot.js` | Frontend: Chat-Verlauf, Senden, Markdown-Rendering |
| CSS | `static/css/copilot.css` | Chat-Layout, Bubbles, Dark-Theme |
| Tests | `tests/test_copilot.py` | 12 Abnahmetests |

### API-Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| POST | `/api/copilot/chat` | Nachricht senden (message + project_id + thread_id + context + plan_id) |
| GET | `/api/copilot/runs` | Verlauf laden (Filter: project_id, thread_id, limit) |
| GET | `/copilot` | Chat-UI-Seite |

### DB-Tabelle: `copilot_runs`

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| id | SERIAL PK | Run-ID |
| project_id | VARCHAR(200) | Projekt-Zuordnung (nullable) |
| thread_id | VARCHAR(100) | Thread-Identifikator (auto-generiert wenn leer) |
| user_message | TEXT | User-Nachricht |
| assistant_reply | TEXT | Copilot-Antwort (nullable bei Fehler) |
| model | VARCHAR(100) | Verwendetes Modell |
| status | VARCHAR(20) | success / failure |
| error_info | TEXT | Fehlerbeschreibung (nullable) |
| created_at | TIMESTAMPTZ | Zeitstempel |
| plan_id | INTEGER | Plan-Zuordnung fuer Sprint E (nullable) |

### Indizes

- `idx_copilot_runs_project` auf project_id
- `idx_copilot_runs_thread` auf thread_id
- `idx_copilot_runs_created` auf created_at DESC
- `idx_copilot_runs_plan` auf plan_id

### Verhalten

- **System-Prompt:** "Du bist Perplexity, ein technischer Copilot, der bei Architektur, Spezifikationen und Code-Reviews hilft."
- **Thread-Historie:** Letzte 20 Nachrichten des Threads werden als Konversationskontext mitgesendet
- **Context-Injection:** Optionales JSON-Objekt wird als "Aktueller Projektkontext" eingefuegt
- **Plan-Bindung:** plan_id wird gespeichert, Plan-Modal hat "Copilot fuer diesen Plan"-Link
- **Fehlerbehandlung:** Config-Fehler (kein API-Key), Request-Fehler, API-Fehler werden persistiert mit status=failure

### UI-Features

- Projekt-Eingabefeld (optional)
- Thread-ID-Anzeige (auto-generiert, readonly)
- "Neuer Thread"-Button
- Chat-Verlauf mit User/Copilot-Bubbles
- Markdown-Rendering (marked.js) fuer Copilot-Antworten
- Enter-to-Send (Shift+Enter fuer Zeilenumbruch)
- Loading-State waehrend LLM-Aufruf
- Inline-Fehleranzeige

---

## 3. Gemeinsamer LLM-Connector

### Datei: `services/perplexity_service.py`

Synchroner HTTP-Client fuer die Perplexity Chat Completions API.

| Funktion | Beschreibung |
|----------|-------------|
| `query_perplexity(messages, model, temperature, max_tokens)` | Hauptfunktion: sendet Messages, gibt normalisiertes Ergebnis zurueck |
| `_get_api_key()` | Laedt PERPLEXITY_API_KEY aus Config |
| `_build_request_body(...)` | Baut JSON-Request |
| `_send_request(...)` | HTTP-Call via urllib |
| `_parse_response(...)` | Normalisiert API-Antwort |

### Konfiguration (.env)

```
PERPLEXITY_API_KEY=pplx-...
PERPLEXITY_BASE_URL=https://api.perplexity.ai/chat/completions  (Default)
PERPLEXITY_MODEL=sonar  (Default)
PERPLEXITY_TIMEOUT=30  (Default, Sekunden)
```

### Exceptions

| Exception | Wann |
|-----------|------|
| `PerplexityConfigError` | API-Key fehlt |
| `PerplexityRequestError` | Timeout, Transport, Parsing |
| `PerplexityAPIError` | non-2xx Response (hat status_code, body) |

### Normalisiertes Response-Format

```json
{
    "provider": "perplexity",
    "model": "sonar",
    "content": "Antworttext...",
    "usage": {
        "prompt_tokens": 123,
        "completion_tokens": 456,
        "total_tokens": 579
    },
    "raw": { ... }
}
```

---

## 4. Plan-Workflow-Integration (Sprint E)

### Copilot-Anbindung an Plans

- `copilot_runs.plan_id` verknuepft Chat-Nachrichten mit einem Plan
- POST /api/copilot/chat akzeptiert `plan_id` im Request-Body
- Plan-Detail-Modal hat "Copilot fuer diesen Plan"-Button
- URL-Schema: `/copilot?project=X&plan_id=Y`

### Workflow-Felder auf project_plans

Diese Felder wurden in Sprint E auf die bestehende `project_plans` Tabelle ergaenzt:

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| workflow_stage | VARCHAR(30) | idea, spec_ready, prompt_ready, executing, review_pending, fixed, done, blocked |
| current_state | TEXT | Ist-Zustand |
| target_state | TEXT | Soll-Zustand |
| next_action | TEXT | Naechster Schritt |
| latest_executor_status | VARCHAR(30) | pending, running, done, failed |
| latest_review_status | VARCHAR(30) | pending, pass, fail, partial |
| open_items_count | INTEGER | Anzahl offener Punkte |
| latest_audit_status | VARCHAR(30) | Live-Signal aus Audit |
| latest_quality_score | INTEGER | Live-Signal aus Quality |
| governance_status | VARCHAR(20) | Live-Signal aus Governance (green/yellow/red) |
| spec_ref | VARCHAR(500) | Referenz auf Spec-Datei |
| prompt_ref | VARCHAR(500) | Referenz auf Prompt-Datei |
| last_run_at | TIMESTAMPTZ | Letzter Executor-Lauf |
| plan_type | VARCHAR(50) | Typ des Plans |

---

## 5. Sidebar-Navigation

| Pfad | Label | Icon |
|------|-------|------|
| `/llm-commands` | LLM Commands | terminal |
| `/copilot` | Copilot | message-circle |

---

## 6. Tests

| Datei | Anzahl | Abdeckung |
|-------|--------|-----------|
| `tests/test_llm_commands.py` | 15 | Command-Parsing, API, Connector-Mock, Persistenz, UI |
| `tests/test_copilot.py` | 12 | Chat-API, Verlauf, Filter, Fehler, UI, Abgrenzung |
| `tests/test_plan_workflow.py` | 16 | DB-Schema, Workflow-API, Logik, Copilot-Binding, Signale |

---

## 7. Bekannte Einschraenkungen

- Kein Streaming (Antwort kommt komplett)
- Kein Multi-Provider (nur Perplexity, agnostischer Connector geplant)
- Thread-Historie: max 20 letzte Runs als Kontext (Token-Limit)
- Kein automatischer Projektstatus-Dump (manuell oder spaeterer Spec)
- Command-Context-Resolver kennt nur {{project}}, {{gate_data}}, {{quality_data}}
- Copilot hat keinen "Projektstatus anhaengen"-Button (geplant)

---

## 8. Geplante Erweiterungen

| Feature | Status | Beschreibung |
|---------|--------|-------------|
| LLM-agnostischer Connector | Geplant | Perplexity nur ein Provider, OpenRouter/lokal spaeter |
| Projektstatus-Aggregation | Geplant | GET /api/project-status/<project> als Kontext-Quelle |
| "Status anhaengen"-Button | Geplant | Injiziert Projektkontext in Copilot-Chat |
| Modell-Auswahl in UI | Geplant | Dropdown fuer sonar/sonar-pro/andere |
| Prompt-Generierung | Vision | Copilot generiert Executor-Prompts fuer Claude Code |
