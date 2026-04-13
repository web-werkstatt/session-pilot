# Routes — Architektur-Kontext

Jedes Route-Modul ist ein Flask Blueprint, registriert in `routes/__init__.py`.

## Module

| Modul | Zweck |
|-------|-------|
| `project_routes.py` | Projekt-Info, Detail, Save, Export, Assets, Tool-Profile-Endpoints |
| `data_routes.py` | /api/data, /api/containers (Haupt-Daten-Aggregation) |
| `document_routes.py` | Dokumenten-Browser, Viewer, Editor, Upload, Export |
| `session_routes.py` | Claude Sessions (PostgreSQL) |
| `search_routes.py` | Volltextsuche via ripgrep, `_parse_search_output()` gemeinsam fuer rg/grep |
| `widget_routes.py` | Dashboard-Widgets (Heatmap, Charts, Statistiken) |
| `notification_routes.py` | Benachrichtigungs-API |
| `relation_routes.py` | Projekt-Beziehungen |
| `group_routes.py` | Gruppen-Verwaltung |
| `idea_routes.py` | Ideen/Notizen |
| `news_routes.py` | News + Vorlagen |
| `scheduled_tasks_routes.py` | Scheduled Tasks (CRUD, JSON-Store) |
| `plans_routes.py` | Plans Import, Uebersicht, Detail, Status (PostgreSQL) |
| `session_filter_routes.py` | Filter-API, Outcome-Reasons, AI-Scope-Stats |
| `analytics_routes.py` | File-Heatmap + Risk-Radar API |
| `model_comparison_routes.py` | Modell-Vergleich, Stack-Metriken, Trends, Empfehlungen |
| `workflow_routes.py` | Workflow-State REST-API (Transitionen, Audit-Trail) |
| `policy_routes.py` | Policy-CRUD, Review-Trigger, Suggestions |
| `tool_setup_review_routes.py` | Setup-Review POST/GET pro Projekt |

## Konventionen

- **Error-Handling:** `@api_route` Decorator aus `routes/api_utils.py` statt try/except. Nur bei speziellen Fehler-Responses manuelles try/except.
- **Timesheet-Filter:** `_build_timesheet_filter()` in `timesheet_routes.py` fuer WHERE-Klausel-Bau.
- **Pfad-Aufloesung:** Immer `services/path_resolver.py:resolve_project_path()` nutzen, nie manuell.
