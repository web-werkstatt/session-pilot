# Repository Assessment: Control-Plane & RAG Integration

**SPEC:** SPEC-REPO-ASSESS-001 v0.1
**Datum:** 2026-04-01
**Status:** Befund (read-only, keine Implementierung)

---

## Inhaltsverzeichnis

1. [Project Structure](#1-project-structure)
2. [Backend Entrypoints](#2-backend-entrypoints)
3. [DB and ORM Patterns](#3-db-and-orm-patterns)
4. [Migrations Pattern](#4-migrations-pattern)
5. [Existing Models (Tabellen)](#5-existing-models-tabellen)
6. [Existing Routes and Blueprints](#6-existing-routes-and-blueprints)
7. [Session and Outcome Data Flow](#7-session-and-outcome-data-flow)
8. [Project and Repo Metadata Sources](#8-project-and-repo-metadata-sources)
9. [Search, Index, Import Capabilities](#9-search-index-import-capabilities)
10. [Audit-Core Integration Points](#10-audit-core-integration-points)
11. [Quality Pipeline Integration Points](#11-quality-pipeline-integration-points)
12. [Governance Integration Points](#12-governance-integration-points)
13. [External API Integration Points](#13-external-api-integration-points)
14. [Gaps for Control-Plane](#14-gaps-for-control-plane)
15. [Recommended Extension Points](#15-recommended-extension-points)
16. [Unknowns and Risks](#16-unknowns-and-risks)
17. [Top 3 Integration Points (priorisiert)](#17-top-3-integrationspunkte-priorisiert)
18. [3 Folgesprints](#18-3-folgesprints)

---

## 1. Project Structure

```
project_dashboard/
  app.py                      # Flask-Entrypoint (95 Zeilen)
  config.py                   # Env-basierte Konfiguration
  requirements.txt            # flask, psycopg2-binary, markdown, openpyxl, opentelemetry-proto
  routes/                     # 30 Blueprint-Module (je 1 Datei pro Concern)
    __init__.py               # register_blueprints() - 29 Blueprints
    api_utils.py              # @api_route Decorator
    session_routes.py         # Sessions CRUD + Sync
    session_filter_routes.py  # Outcome-Reasons, Scope-Stats
    governance_routes.py      # Governance API
    quality_routes.py         # Quality-Metriken
    analytics_routes.py       # File-Heatmap, Risk-Radar
    model_comparison_routes.py # Modell-Vergleich
    plans_routes.py           # Plans CRUD + Sync
    search_routes.py          # Volltextsuche (ripgrep)
    ...                       # 20 weitere Route-Module
  services/                   # 35 Service-Module
    db_service.py             # PostgreSQL raw SQL, Connection Pool, Schema-Init
    project_scanner.py        # Projekt-Discovery + Cache
    project_detector.py       # Typ-/Tag-Erkennung
    description_extractor.py  # README/package.json Parsing
    session_import.py         # Claude JSONL Import
    session_import_multi.py   # Codex/Gemini Import
    governance_service.py     # 3-Tier Policy System
    model_recommendation.py   # Quality-Score, Empfehlungen
    file_touch_service.py     # Per-File AI-Activity Tracking
    cost_service.py           # Token-Kosten-Berechnung
    plans_import.py           # ~/.claude/plans/ Scanner
    account_discovery.py      # Multi-Tool Account Discovery
    ...                       # 22 weitere Services
  audit/                      # Spec-basiertes Audit-System
    models.py                 # Pydantic: Spec, Requirement, AuditResult
    rules.py                  # Coverage-basierte Evaluation
    service.py                # run_audit() Orchestrierung
    repository.py             # DB-Operationen (specs, audit_runs)
    analyzers/                # Hook fuer kuenftige Analyzer (leer)
  templates/                  # Jinja2 HTML Templates
  static/                     # CSS, JS, Assets
  api/                        # LEER - nicht genutzt
```

**Bestaetigt:** Monolithische Flask-App, Blueprint-basiert, kein Build-Step, kein ORM.

---

## 2. Backend Entrypoints

| Entrypoint | Datei | Zeile | Zweck |
|---|---|---|---|
| Flask App Init | `app.py:27` | `app = Flask(__name__)` | Hauptanwendung |
| Blueprint-Registrierung | `app.py:32` | `register_blueprints(app)` | Alle 29 Blueprints |
| Notification Checker | `app.py:35-36` | `start_checker()` | Background-Thread (60s) |
| Background Scan | `app.py:39-40` | `init_background_scan()` | Projekt-Scan beim Start |
| HTTP Server | `app.py:95` | `app.run(host, port, threaded=True)` | Port 5055 |

**Middleware:** Keine (kein `before_request`/`after_request` in app.py).
**Threading:** `threaded=True` + Daemon-Threads fuer Checker/Scan.

---

## 3. DB and ORM Patterns

**Befund: Raw SQL mit psycopg2. Kein ORM.**

| Aspekt | Detail |
|---|---|
| **Adapter** | `psycopg2-binary` (requirements.txt) |
| **Connection Pool** | `ThreadedConnectionPool(3, 10)` (`db_service.py:20`) |
| **Pool-Schutz** | `threading.Lock` (`db_service.py:13`) |
| **Cursor** | `RealDictCursor` - Ergebnisse als dict |
| **Haupt-Executor** | `execute(sql, params, fetch, fetchone)` (`db_service.py:37-55`) |
| **Batch-Executor** | `execute_many(sql, params_list)` (`db_service.py:58-69`) |
| **Auto-Commit** | Ja, nach jedem execute (mit Rollback bei Fehler) |
| **Transaktionen** | Keine expliziten Transaktionen ausser in execute_many |

**Kein SQLAlchemy, kein SQLModel, kein Alembic.** Alle Queries sind handgeschriebenes SQL.

---

## 4. Migrations Pattern

**Befund: Kein Migrationssystem. Schema-Evolution via `ensure_*_schema()`-Funktionen.**

| Funktion | Datei:Zeile | Tabellen |
|---|---|---|
| `ensure_database()` | `db_service.py:72-145` | sessions, messages |
| `ensure_session_review_schema()` | `db_service.py:153-189` | review_threads, session_reviews + ALTER sessions |
| `ensure_plans_schema()` | `db_service.py:192-221` | project_plans |
| `ensure_ai_scope_schema()` | `db_service.py:228-241` | ALTER sessions (ai_*-Spalten) |
| `ensure_model_quality_view()` | `db_service.py:248-281` | MATERIALIZED VIEW mv_model_quality |
| `ensure_file_touch_schema()` | `db_service.py:296-353` | ai_file_touches |
| `ensure_audit_schema()` | `db_service.py:360-433` | specs, spec_requirements, audit_runs, audit_results |

**Pattern:** `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS`. Thread-safe via individuelle Locks. Nur additive Aenderungen, keine destruktiven Migrationen.

---

## 5. Existing Models (Tabellen)

### 5.1 Core: sessions (`db_service.py:97-122`)

| Spalte | Typ | Zweck |
|---|---|---|
| id | SERIAL PK | |
| session_uuid | VARCHAR(64) UNIQUE | Externe Session-ID |
| account | VARCHAR(20) | Account-Name |
| project_hash, project_name | VARCHAR | Projekt-Zuordnung |
| cwd, git_branch | VARCHAR | Arbeitsverzeichnis, Branch |
| model, claude_version, slug | VARCHAR | Modell-Info |
| started_at, ended_at | TIMESTAMPTZ | Zeitraum |
| duration_ms | INTEGER | Dauer |
| user_message_count, assistant_message_count | INTEGER | Nachrichtenzaehler |
| total_input_tokens, total_output_tokens | INTEGER | Token-Verbrauch |
| jsonl_path, jsonl_size, jsonl_mtime | | Quelldatei-Tracking |
| outcome | VARCHAR(20) | ok / needs_fix / reverted |
| outcome_note | TEXT | Review-Notiz |
| outcome_reason | VARCHAR(50) | Fehler-Kategorie (syntax_error, wrong_file, ...) |
| outcome_severity | VARCHAR(20) | low / medium / high / critical |
| ai_has_writes, ai_has_tool_calls | BOOLEAN | AI-Scope |
| ai_tools_used | JSONB | Tool-Liste |
| cost_estimate | NUMERIC(10,4) | Geschaetzte Kosten |

### 5.2 messages (`db_service.py:123-139`)

| Spalte | Typ | Zweck |
|---|---|---|
| id | SERIAL PK | |
| session_id | INT FK sessions | |
| uuid, parent_uuid | VARCHAR(64) | Thread-Struktur |
| type | VARCHAR(20) | user / assistant |
| content | TEXT | Klartext |
| content_json | JSONB | Strukturierter Inhalt (tool_use etc.) |
| model | VARCHAR(100) | Modell pro Nachricht |
| input_tokens, output_tokens, duration_ms | INTEGER | |
| timestamp | TIMESTAMPTZ | |
| is_tool_result | BOOLEAN | |

### 5.3 review_threads / session_reviews (`db_service.py:165-184`)

Projekt-bezogene Review-Threads mit individuellen Session-Reviews.

### 5.4 project_plans (`db_service.py:200-221`)

Plans aus `~/.claude/plans/`, verknuepft mit Sessions via `session_uuid` und Zeitstempel-Korrelation.

### 5.5 ai_file_touches (`db_service.py:304-353`)

Per-File AI-Aktivitaet: file_path, touch_type (write/edit/read), tool_name, model, issue_category. Unique Constraint auf (session_id, file_path, touch_type).

### 5.6 Audit-Tabellen (`db_service.py:370-433`)

- **specs** - Spezifikationsdokumente (spec_id, title, status, risk_level)
- **spec_requirements** - Anforderungs-Atome (key, priority, affected_areas als JSONB)
- **audit_runs** - Audit-Durchlaeufe (spec_id, overall_status, input_facts als JSONB)
- **audit_results** - Einzelergebnisse (requirement_key, status, evidence als JSONB)

### 5.7 Materialized View: mv_model_quality (`db_service.py:259-281`)

Aggregiert: model, total_sessions, ok/needs_fix/reverted counts, rework_rate, total_tokens, total_cost.

### 5.8 Nicht in DB (JSON-Dateien)

| Datei | Zweck |
|---|---|
| `groups.json` | Projekt-Gruppen |
| `relations.json` | Projekt-Beziehungen |
| `ideas.json` | Ideen/Notizen |
| `scheduled_tasks.json` | Geplante Tasks |
| `favorites.json` | Favoriten |
| `notifications.json` | Benachrichtigungen (max 200, FIFO) |

---

## 6. Existing Routes and Blueprints

**29 Blueprints registriert in `routes/__init__.py`:**

| Blueprint | Datei | Kern-Endpoints |
|---|---|---|
| sessions_bp | session_routes.py | /api/sessions, /api/sessions/sync, /api/sessions/search |
| session_filter_bp | session_filter_routes.py | /api/sessions/filters, /api/sessions/outcome-reasons, /api/sessions/scope-stats |
| session_review_bp | session_review_routes.py | Session-Review CRUD |
| session_analysis_bp | session_analysis_routes.py | Session-Analyse |
| plans_bp | plans_routes.py | /api/plans, /api/plans/sync, /api/plans/stats |
| analytics_bp | analytics_routes.py | /api/analytics/file-heatmap, /api/analytics/risk-radar |
| model_comparison_bp | model_comparison_routes.py | /api/analytics/model-comparison, model-trend, model-recommendation |
| governance_bp | governance_routes.py | Governance-API |
| quality_bp | quality_routes.py | Quality-Metriken |
| search_bp | search_routes.py | /api/search (ripgrep) |
| data_bp | data_routes.py | /api/data (Haupt-Aggregation), /api/containers |
| notification_bp | notification_routes.py | Benachrichtigungs-API |
| project_bp | project_routes.py | Projekt CRUD |
| project_info_bp | project_info_routes.py | Projekt-Detail |
| documents_bp | document_routes.py | Dokument-Browser/Editor |
| timesheets_bp | timesheet_routes.py | Timesheet-Tracking |
| otel_bp | otel_routes.py | OpenTelemetry |
| usage_monitor_bp | usage_monitor_routes.py | Usage-Monitoring |
| usage_reports_bp | usage_reports_routes.py | Usage-Reports |
| settings_bp | settings_routes.py | Einstellungen |
| scaffold_bp | scaffold_routes.py | Code-Scaffolding |
| context_bp | context_routes.py | Kontext-Verwaltung |
| scheduled_tasks_bp | scheduled_tasks_routes.py | Scheduled Tasks CRUD |
| git_bp | git_routes.py | Git-Operationen |
| widget_bp | widget_routes.py | Dashboard-Widgets |
| relation_bp | relation_routes.py | Projekt-Relationen |
| group_bp | group_routes.py | Gruppen |
| idea_bp | idea_routes.py | Ideen |
| news_bp | news_routes.py | News + Vorlagen |

---

## 7. Session and Outcome Data Flow

```
Quelldateien (JSONL/JSON)
  ~/.claude*/projects/**/*.jsonl    (Claude Code)
  ~/.codex/sessions/**/*.jsonl      (Codex CLI)
  ~/.gemini/tmp/*/logs.json         (Gemini CLI)
        |
        v
account_discovery.py:discover_all_accounts()
        |
        v
session_import.py:sync_all()  /  session_import_multi.py
  -> parse_jsonl() / parse_codex_jsonl() / parse_gemini_json()
  -> ai_scope_service.extract_ai_flags(messages)
  -> file_touch_service.extract_file_touches(messages)
        |
        v
INSERT INTO sessions + messages + ai_file_touches
        |
        v
session_routes.py: /api/sessions (Filter, Pagination, Sort)
session_filter_routes.py: /api/sessions/outcome-reasons
  -> OUTCOME_REASONS dict (needs_fix: 12 Kategorien, reverted: 5, partial: 5)
  -> Severity: low / medium / high / critical
        |
        v
analytics_routes.py: /api/analytics/file-heatmap, risk-radar
model_comparison_routes.py: /api/analytics/model-comparison
cost_service.py: calculate_cost()
session_export.py: JSON/MD/HTML/XLSX/TXT Export
```

**Outcome-Taxonomie** (`session_filter_routes.py:12-26`):
- `needs_fix`: syntax_error, wrong_file, incomplete, wrong_approach, missing_import, test_failure, type_error, logic_error, wrong_api, security, style_drift, hallucination
- `reverted`: broke_existing, wrong_scope, not_requested, regression, performance_issue
- `partial`: needs_followup, incomplete_refactor, manual_fix_needed, missing_tests, other

---

## 8. Project and Repo Metadata Sources

### 8.1 Projekt-Identitaet

**Kein dediziertes Projekt-Modell in der DB.** Projekte existieren als:

1. **Verzeichnisse** unter `/mnt/projects/` (physisch)
2. **project.json** pro Projekt (Schema v3, `project_detector.py:11`)
3. **project_name STRING** in sessions, plans, file_touches (kein FK, kein Enum)

**project.json Felder** (`project_detector.py:14-27`):
name, description, category, topic, tags, group, priority, status, project_type, version, license, schema_version, ai_policy, deadline, progress, milestones, container_patterns, port, auto_generated, archived

### 8.2 Metadata-Extraction Pipeline

| Service | Funktion | Quelle |
|---|---|---|
| `project_scanner.py:scan_projects()` | Haupt-Scanner (ThreadPoolExecutor, 8 Workers) | Filesystem |
| `project_detector.py:detect_tags()` | Technologie-Tags aus Dateien | package.json, pyproject.toml, etc. |
| `project_detector.py:detect_project_type()` | monorepo/fork/tool/documentation/archive | Verzeichnisstruktur |
| `description_extractor.py:extract_description()` | Beschreibung (10 Quellen, Prioritaet) | README, package.json, pyproject.toml, ... |
| `description_extractor.py:detect_topic()` | Topic-Klassifikation | Keywords |
| `description_extractor.py:extract_dependencies()` | Abhaengigkeiten (internal/external/dev/frameworks) | Lock-Files, package.json |
| `git_service.py` | SHA, Branch, Commit-History | git CLI |
| `gitea_service.py` | Remote-Repos, Stars, Issues | Gitea API |
| `path_resolver.py:resolve_project_path()` | Name -> Pfad Aufloesung | Filesystem |

### 8.3 Bestaetigt: Kein Projekt-Identity-Modell

Projekte sind **nur Strings** (project_name). Keine Tabelle `projects` in der DB. Keine ID, kein FK. Verknuepfung zwischen Sessions, Plans, File-Touches, Governance erfolgt ueber String-Match auf project_name.

---

## 9. Search, Index, Import Capabilities

### 9.1 Volltextsuche (`search_routes.py`)

- **Technologie:** ripgrep (rg), Fallback grep
- **Scope:** Alle Projekte unter `/mnt/projects/`
- **Filter:** Projekt, Typ (docs/code/config), Limit
- **Einschraenkungen:** Max 500KB Dateien, Tiefe 5, ignoriert node_modules/.git/etc.
- **Ergebnis:** Datei + Zeile + Kontext (max 3 Matches pro Datei)
- **Kein Index** - jede Suche ist ein Live-Scan

### 9.2 Session-Volltext (`session_routes.py:335`)

- **Endpoint:** `/api/sessions/search`
- **Methode:** SQL `ILIKE` auf messages.content
- **Snippets:** 200 Zeichen Kontext um Match

### 9.3 Import-Systeme

| System | Service | Trigger |
|---|---|---|
| Sessions (Claude) | `session_import.py:sync_all()` | Manuell via /api/sessions/sync, Cooldown 1h |
| Sessions (Codex/Gemini) | `session_import_multi.py` | Teil von sync_all() |
| Plans | `plans_import.py:sync_plans()` | Background-Checker alle 600s + manuell |
| Projekte | `project_scanner.py:scan_projects()` | Bei /api/data Aufruf |

### 9.4 Bestaetigt: Kein Embedding/Vector/RAG

Grep ueber alle Python-Dateien nach "embedding", "vector", "rag", "perplexity", "openai" ergab **keine Treffer** ausser Display-Strings fuer Provider-Namen. Kein Vector-Store, kein Embedding-Modell, keine Retrieval-Logik vorhanden.

---

## 10. Audit-Core Integration Points

### 10.1 Standort

```
audit/
  __init__.py
  models.py       # Pydantic: Spec, Requirement, AuditResult, AuditResponse
  rules.py        # evaluate_requirement(), _match_areas()
  service.py      # run_audit(spec_id, changed_files) -> AuditResponse
  repository.py   # get_spec(), save_spec() (DB CRUD)
  analyzers/
    __init__.py   # _run_analyzers() Hook - LEER, vorbereitet fuer Erweiterung
```

### 10.2 Ablauf

```python
# audit/service.py:run_audit()
spec = repository.get_spec(spec_id)          # Spec + Requirements aus DB
for req in spec.requirements:
    result = rules.evaluate_requirement(req, changed_files)  # Coverage-Check
overall = _compute_overall_status(results)   # PASS/FAIL/PARTIAL/UNSICHER
# Ergebnis in audit_runs + audit_results gespeichert
```

### 10.3 Evaluation-Logik (`rules.py:9-75`)

- Matching: `affected_areas` (aus Spec) gegen `changed_files` (Input)
- Coverage = matched / total areas
- 100% -> ERFUELLT, >0% -> TEILWEISE, 0% -> FEHLT
- Keine Code-Analyse, nur Pfad-Matching

### 10.4 Erweiterungs-Hook

`audit/analyzers/__init__.py` enthaelt `_run_analyzers()` - aktuell leer, vorgesehen fuer:
- LLM-basierte Analyzer
- Statische Code-Analyse
- **Hier koennte ein RAG-basierter Analyzer andocken**

---

## 11. Quality Pipeline Integration Points

### 11.1 Model Quality Score (`model_recommendation.py:69-94`)

```
score = 100
  - (rework_rate * 0.5)
  - (reverted_rate * 1.5)
  - (incomplete_rate * 0.3)
  + 5 (wenn rated_sessions > 20)
  - 10 (wenn security_issues > 3)
  - (avg_severity * 2)
Clamped: [0, 100], Grade: A(90+) B(75+) C(60+) D(40+) F(<40)
```

### 11.2 Rework-Tracking

- **Quelle:** `outcome` + `outcome_reason` Spalten in sessions
- **Aggregation:** `mv_model_quality` Materialized View
- **API:** `/api/analytics/model-comparison`, `/api/analytics/model-trend`

### 11.3 File Risk Radar (`file_touch_service.py:285-386`)

- Hotspot-Erkennung: >10 Touches in 7 Tagen ODER Rework-Rate >25%
- Notification bei Hotspots: `notification_checker.py:143-196` (alle 600s)

### 11.4 Stack-Analyse (`model_recommendation.py:269-367`)

Bestimmt dominanten Stack pro Session (>50% der File-Touches) und vergleicht Modell-Performance pro Stack.

---

## 12. Governance Integration Points

### 12.1 3-Tier Policy System (`governance_service.py:14-57`)

| Level | Name | Writes | Review | Deploy | Sprints |
|---|---|---|---|---|---|
| 1 | sandbox | ja | nein | ja | nein |
| 2 | controlled | ja | ja | nein | ja |
| 3 | critical | nein | ja | nein | ja |

### 12.2 Workflow-Einstellungen (`governance_service.py:142-146`)

- uses_sprints, require_session_review, session_end_mode
- governance_mode: relaxed / balanced / strict
- primary_models: Liste bevorzugter Modelle

### 12.3 Policy-Speicherung

Policies werden in `project.json` unter `ai_policy` gespeichert (nicht in DB).

### 12.4 Policy-Export (`governance_service.py:362-403`)

`generate_policy_snippets()` erzeugt exportierbare Konfiguration fuer:
- CLAUDE.md
- AGENTS.md
- Pre-Commit Hooks

### 12.5 Unreviewed Critical Count (`governance_service.py:242-265`)

Zaehlt Sessions in critical-Projekten ohne Review - direkter Andockpunkt fuer Benachrichtigungen/Eskalation.

---

## 13. External API Integration Points

### 13.1 Vorhandene Integrationen

| Integration | Service | Auth | Protokoll |
|---|---|---|---|
| Gitea | `gitea_service.py` | Token (Bearer) | REST via urllib |
| Docker | `docker_service.py` | Local Socket | `docker ps` CLI |
| Git | `git_service.py` | Local | git CLI Subprocess |
| OpenTelemetry | `otel_routes.py` + `otel_store.py` | - | OTLP/Protobuf |

### 13.2 Bestaetigt: Keine externen AI-APIs

- Kein OpenAI SDK
- Kein Perplexity SDK
- Kein Anthropic SDK (ausser indirekt via Claude Code Sessions)
- Keine HTTP-Client-Library (kein requests, kein httpx) - nur `urllib.request`

### 13.3 Andockpunkt fuer Perplexity

Die App nutzt `urllib.request` fuer HTTP (Gitea). Ein Perplexity-Connector koennte:
1. Als neuer Service `services/perplexity_service.py` analog zu `gitea_service.py` gebaut werden
2. `urllib.request` oder besser `requests` (muesste in requirements.txt) nutzen
3. In `audit/analyzers/` als LLM-Analyzer integriert werden
4. Ueber `notification_checker.py` periodisch aufgerufen werden

---

## 14. Gaps for Control-Plane

| Gap | Beschreibung | Schwere |
|---|---|---|
| **Kein Projekt-Identity-Modell** | Projekte sind nur Strings, keine DB-Tabelle, kein FK | Hoch |
| **Kein Embedding/Vector-Store** | Keine Retrieval-Infrastruktur vorhanden | Hoch |
| **Kein Migration-System** | Schema-Aenderungen nur via ensure_*-Pattern | Mittel |
| **Keine externe HTTP-Library** | Nur urllib, kein requests/httpx fuer API-Calls | Niedrig |
| **Kein LLM-Analyzer** | audit/analyzers/ Hook existiert, aber leer | Mittel |
| **Session-Suche nur ILIKE** | Keine semantische Suche, kein Ranking | Mittel |
| **Kein Project-Memory** | Kein persistenter Wissens-Store pro Projekt | Hoch |
| **JSON-Dateien ohne Backup-Strategie** | groups, relations, ideas ohne DB-Backend | Niedrig |

---

## 15. Recommended Extension Points

### 15.1 Project-Memory / RAG

| Rang | Andockpunkt | Datei | Begruendung |
|---|---|---|---|
| **1** | `audit/analyzers/` | `audit/analyzers/__init__.py` | Existierender Hook, saubere Abstraktion, Spec-Kontext verfuegbar |
| **2** | Neuer Service `services/project_memory_service.py` | (neu) | Analog zu bestehenden Services, Blueprint-Pattern nutzen |
| **3** | `services/description_extractor.py` erweitern | `services/description_extractor.py` | Bereits 10+ Metadata-Quellen, RAG als weitere Quelle |

### 15.2 Perplexity-Connector

| Rang | Andockpunkt | Datei | Begruendung |
|---|---|---|---|
| **1** | Neuer Service analog `gitea_service.py` | (neu) `services/perplexity_service.py` | Bewaehrtes Pattern, In-Memory-Cache, Token-Auth |
| **2** | `audit/analyzers/` als LLM-Analyzer | `audit/service.py:132-140` | _run_analyzers() Hook existiert |
| **3** | `notification_checker.py` fuer periodische Enrichment | `services/notification_checker.py` | Background-Thread Pattern vorhanden |

### 15.3 Reuse-Kandidaten (reduzieren neuen Code)

| Bestehendes Utility | Datei | Wiederverwendbar fuer |
|---|---|---|
| `db_service.execute()` | `db_service.py:37` | Alle neuen DB-Queries |
| `ensure_*_schema()` Pattern | `db_service.py` | Neue Tabellen (project_memory, embeddings) |
| `@api_route` Decorator | `routes/api_utils.py` | Neue API-Endpoints |
| `account_discovery.discover_all_accounts()` | `services/account_discovery.py:164` | Multi-Source Kontext-Sammlung |
| `search_routes._search_rg()` | `routes/search_routes.py:112` | Content-Extraktion fuer Embeddings |
| `session_import_utils.sanitize_content_json()` | `services/session_import_utils.py:48` | JSON-Bereinigung fuer JSONB |
| `path_resolver.resolve_project_path()` | `services/path_resolver.py:14` | Pfad-Aufloesung in neuen Services |
| `notification_service.add_notification()` | `services/notification_service.py:45` | Benachrichtigungen bei RAG-Events |
| `cost_service.calculate_cost()` | `services/cost_service.py:70` | Kosten-Tracking fuer LLM-Calls |

---

## 16. Unknowns and Risks

### Offene Fragen

| # | Frage | Warum relevant |
|---|---|---|
| U1 | Wie gross ist die messages-Tabelle aktuell? | Bestimmt ob Embedding-Batch machbar oder inkrementell sein muss |
| U2 | Gibt es Performance-Probleme bei ILIKE-Suche? | Wuerde Prioritaet fuer Vector-Suche beeinflussen |
| U3 | Wird `ensure_*_schema()` bei jedem Request aufgerufen? | Koennte neue Schema-Funktionen verlangsamen |
| U4 | Wie viele Projekte existieren unter /mnt/projects/? | Bestimmt Skalierung des Project-Identity-Modells |
| U5 | Wird model_pricing Tabelle manuell gepflegt? | Relevant fuer Perplexity-Kosten-Tracking |
| U6 | Wie werden project.json ai_policy und DB-Daten synchron gehalten? | Governance haengt an JSON, Sessions an DB |
| U7 | Gibt es Rate-Limits oder Budget-Constraints fuer externe APIs? | Perplexity-Connector muesste Limits respektieren |
| U8 | Ist der `api/`-Ordner fuer etwas geplant? | Leer, aber im Repo |

### Risiken

| Risiko | Auswirkung | Mitigation |
|---|---|---|
| String-basierte Projekt-Zuordnung | Inkonsistenzen bei Umbenennung | Project-Identity-Tabelle einfuehren |
| Kein Alembic | Schema-Rollbacks nicht moeglich | Vor groesseren Aenderungen evaluieren |
| urllib als einziger HTTP-Client | Kein Retry, kein Timeout-Handling | requests hinzufuegen oder urllib-Wrapper |
| ThreadedConnectionPool(3,10) | Bei vielen RAG-Queries Pool-Exhaustion | Pool-Groesse erhoehen oder async evaluieren |

---

## 17. Top 3 Integrationspunkte (priorisiert)

### Platz 1: `audit/analyzers/` — LLM/RAG Analyzer Hook

- **Datei:** `audit/analyzers/__init__.py` + `audit/service.py:132-140`
- **Warum:** Sauberer, vorbereiteter Extension-Point. Specs liefern Kontext (affected_areas, acceptance_criteria). Aktuell nur Pfad-Matching, LLM-Analyzer wuerde semantische Evaluation ergaenzen.
- **Aufwand:** Gering (Interface steht, nur Implementierung).
- **Abhaengigkeit:** Perplexity- oder LLM-Service muss existieren.

### Platz 2: Neuer Service `services/project_memory_service.py`

- **Warum:** Projekt-Kontext ist aktuell verstreut (project.json, sessions, plans, governance). Ein zentraler Memory-Service koennte all das aggregieren und als RAG-Kontext bereitstellen.
- **Pattern:** Analog zu `model_recommendation.py` - aggregiert aus DB, cached, stellt API bereit.
- **Aufwand:** Mittel (neuer Service + neue Route + ggf. neue Tabelle).

### Platz 3: `services/perplexity_service.py` — Externer Connector

- **Warum:** Bewaehrtes Pattern (`gitea_service.py`: urllib + Cache + Token). Kann unabhaengig entwickelt und dann in Audit-Analyzer oder Project-Memory eingebunden werden.
- **Pattern:** Service mit In-Memory-Cache (TTL), Token aus .env.
- **Aufwand:** Gering (isolierter Service, keine Abhaengigkeiten).

---

## 18. 3 Folgesprints

### Sprint A: Project Identity + Memory Foundation

**Ziel:** Projekt-Identity-Tabelle in DB, zentraler Memory-Service.

**Tasks:**
1. `ensure_project_identity_schema()` in `db_service.py` — Tabelle `projects` (id, name, path, tags, policy_level, created_at)
2. Migration bestehender project_name-Strings zu FK (oder View-basiert)
3. `services/project_memory_service.py` — aggregiert Projekt-Kontext aus sessions, plans, file_touches, governance
4. Route `/api/projects/<name>/memory` — liefert aggregierten Kontext

**Risiko:** Niedrig (additiv, keine Aenderungen an bestehenden Queries noetig wenn View-basiert).

### Sprint B: Perplexity Connector + Audit Analyzer

**Ziel:** Externer LLM-Zugang, erster semantischer Audit-Analyzer.

**Tasks:**
1. `services/perplexity_service.py` — HTTP-Client, Auth, Rate-Limiting, Cache
2. `audit/analyzers/llm_analyzer.py` — nutzt Perplexity fuer semantische Requirement-Evaluation
3. `audit/service.py:_run_analyzers()` mit LLM-Analyzer verbinden
4. Kosten-Tracking via `cost_service.py` erweitern

**Risiko:** Mittel (externer API-Zugang, Kosten, Latenz).

### Sprint C: Embedding Pipeline + Semantische Suche

**Ziel:** Vector-basierte Suche ueber Session-Inhalte und Projekt-Dokumentation.

**Tasks:**
1. Embedding-Modell evaluieren (lokal vs. API)
2. `ensure_embeddings_schema()` — Tabelle oder pgvector Extension
3. Batch-Embedding fuer bestehende messages.content
4. `/api/search/semantic` Endpoint
5. Integration in Project-Memory als Retrieval-Quelle

**Risiko:** Hoch (groesste Architektur-Aenderung, pgvector-Abhaengigkeit, Batch-Laufzeit).

---

## Anhang: Evidenz-Zusammenfassung

| Behauptung | Typ | Quelle |
|---|---|---|
| Raw SQL, kein ORM | Bestaetigt | `requirements.txt`, `db_service.py` |
| 29 Blueprints | Bestaetigt | `routes/__init__.py` |
| Kein Migrationssystem | Bestaetigt | Keine migrations/, kein Alembic in requirements |
| Kein Embedding/RAG | Bestaetigt | Grep ueber alle .py Dateien |
| Audit-Analyzer-Hook leer | Bestaetigt | `audit/analyzers/__init__.py` |
| Projekte nur als Strings | Bestaetigt | Kein CREATE TABLE projects in db_service.py |
| project.json Schema v3 | Bestaetigt | `project_detector.py:11` |
| ThreadedConnectionPool(3,10) | Bestaetigt | `db_service.py:20` |
| Perplexity nicht integriert | Bestaetigt | Keine Imports/Referenzen |
| model_pricing Tabelle existiert | Inferiert | Referenziert in cost_service.py:27, aber CREATE nicht in db_service.py gefunden |
