# Services — Architektur-Kontext

## Kern-Services

| Service | Zweck |
|---------|-------|
| `project_scanner.py` | Scannt Projekte, verwaltet project.json, Cache-Logik |
| `project_detector.py` | Typ-Erkennung, Sub-Projekt-Erkennung. `detect_tags()` ist zentral fuer Tech-Tags — NICHT duplizieren |
| `description_extractor.py` | Beschreibung aus README/package.json/etc., Topic-Erkennung |
| `path_resolver.py` | Zentralisierte Projektpfad-Aufloesung (inkl. Sub-Projekte) |
| `db_service.py` | PostgreSQL Connection-Pool (psycopg2) |
| `cache_service.py` | JSON-Datei-basierter Cache (120s TTL) |
| `config.py` | Alle Werte via `os.environ` mit Defaults |

## Session-Import

| Service | Zweck |
|---------|-------|
| `session_import.py` | JSONL-Parser, zentraler Sync-Orchestrator, Hash-basierter Cache |
| `session_import_utils.py` | **Shared Helpers:** `parse_ts()`, `sanitize_content_json()`, `create_session_meta()`, `update_time_range()` |
| `importers/` | Modulare Importer: Claude, Codex, Gemini, OpenCode, Kilo |
| `session_export.py` | Export: JSON, MD, HTML, XLSX, TXT |
| `account_discovery.py` | Erkennt AI-Assistenten-Accounts |

**WICHTIG:** Neue Session-Meta-Felder oder Timestamp-Logik IMMER in `session_import_utils.py` aendern, nicht in den Import-Modulen.

## Marker / Workflow (ADR-001)

| Service | Zweck |
|---------|-------|
| `db_marker_schema.py` | `markers`-Tabelle + `executor_tool` in `marker_workflow_states` |
| `marker_importer.py` | Idempotenter Import aus handoff.md in DB |
| `workflow_core_service.py` | Zentrale Domaenenschicht: `get_markers()`, `get_marker()`, `update_marker_field()`, `get_handoff_view()` |
| `workflow_state_service.py` | Transition-Regeln (`ALLOWED_TRANSITIONS`), Audit-Trail |
| `workflow_loop_service.py` | Marker-Gruppen + Signale fuer Workflow-Tab |
| `copilot_marker_service.py` | `_resolve_marker()` / `_resolve_markers()` (DB-first mit Fallback) |
| `block_marker_parser.py` | Parst MANUAL/DASHBOARD-GENERATED/UNMARKED Bloecke |
| `write_guard.py` | Policy-Enforcement: Atomic Write, File-Lock, TOCTOU-Schutz |
| `tool_profile_adapter_service.py` | Generiert DASHBOARD-GENERATED-Bloecke in Tool-Files |

## Policy-Schicht (ADR-002)

| Service | Zweck |
|---------|-------|
| `db_policy_schema.py` | 4 DB-Tabellen: roles, tool_profiles, role_tool_policies, policy_review_suggestions |
| `policy_service.py` | CRUD fuer Policies, Apply-Pfad fuer Suggestions |
| `policy_seed.py` | Idempotente Seed-Defaults (6 Rollen, 5 Tool-Profile) |
| `policy_review_service.py` | Perplexity-Policy-Reviewer mit context_hash-Dedup |
| `tool_setup_review/` | Modularer Setup-Reviewer (Collector, Drift-Check, Orchestrator, Storage) |

## Patterns

- **DB-first mit Fallback:** Lese-Pfade nutzen DB, fallen auf handoff.md zurueck
- **Dual-Write:** Schreib-Operationen aktualisieren handoff.md (Mirror) UND DB
- **Schema lazy:** Alle `ensure_*_schema()` Funktionen sind idempotent
- **Keine externen HTTP-Libraries:** Gitea-API nutzt `urllib.request` direkt
