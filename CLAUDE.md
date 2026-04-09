# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Fokusauftrag

1. Lies beim Start immer zuerst `sprints/master-plan-*.md` als Rahmen.
2. Wenn `marker-context.md` existiert und nicht leer ist, behandle ihn als aktuellen Fokusauftrag.
3. Wenn kein `marker-context.md` existiert, frag nach, bevor du an einem Marker arbeitest.
4. Veraendere `marker-context.md` nie eigenmaechtig, ausser auf ausdruecklichen Auftrag.

## Projekt

Flask-basiertes Web-Dashboard zur Verwaltung und Uebersicht aller Projekte unter `/mnt/projects/` sowie Docker-Container und Claude Code Sessions. Laeuft als systemd-Service (`project-dashboard`) auf Port 5055. Installierbar via Docker oder setup.sh.

## Befehle

```bash
# Entwicklung: App manuell starten
python3 app.py

# Produktion: systemd-Service
sudo systemctl restart project-dashboard
sudo systemctl status project-dashboard

# Logs
tail -f /mnt/projects/project_dashboard/dashboard.log

# Docker (Alternative)
docker compose up -d
```

Kein Build-Schritt, keine Tests, kein Linting konfiguriert. Abhaengigkeiten in `requirements.txt` (Flask, markdown, psycopg2-binary, openpyxl).

## Architektur

**Einstiegspunkt:** `app.py` (104 Zeilen) - Flask-App, registriert Blueprints, startet Notification-Checker, laedt .env.

**Route-Module (`routes/`):**
- `project_routes.py` - Projekt-Info, Detail, Save, Export, Assets
- `data_routes.py` - /api/data, /api/containers (Haupt-Daten-Aggregation)
- `document_routes.py` - Dokumenten-Browser, Viewer, Editor, Upload, Export
- `session_routes.py` - Claude Sessions (PostgreSQL)
- `search_routes.py` - Volltextsuche via ripgrep ueber alle Projekte
- `widget_routes.py` - Dashboard-Widgets (Heatmap, Charts, Statistiken)
- `notification_routes.py` - Benachrichtigungs-API
- `relation_routes.py` - Projekt-Beziehungen
- `group_routes.py` - Gruppen-Verwaltung
- `idea_routes.py` - Ideen/Notizen
- `news_routes.py` - News + Vorlagen
- `scheduled_tasks_routes.py` - Scheduled Tasks Verwaltung (CRUD, JSON-Store)
- `plans_routes.py` - Plans Import, Uebersicht, Detail, Status-Verwaltung (PostgreSQL)
- `session_filter_routes.py` - Sprint 9: Filter-API, Outcome-Reasons, AI-Scope-Stats
- `analytics_routes.py` - Sprint 10: File-Heatmap + Risk-Radar API
- `model_comparison_routes.py` - Sprint 11: Modell-Vergleich, Stack-Metriken, Trends, Empfehlungen

**Service-Schicht (`services/`):**
- `project_scanner.py` - Scannt Projekte, verwaltet project.json, Cache-Logik
- `project_detector.py` - Typ-Erkennung (monorepo, fork, tool etc.), Sub-Projekt-Erkennung
- `description_extractor.py` - Beschreibung aus README/package.json/etc., Topic-Erkennung, Dependencies
- `path_resolver.py` - Zentralisierte Projektpfad-Aufloesung (inkl. Sub-Projekte)
- `notification_service.py` - Thread-safe JSON-Store fuer Notifications
- `notification_checker.py` - Background-Thread (60s): Container, Sync, neue Projekte
- `gitea_service.py` - Gitea-API (urllib, In-Memory-Cache 60s TTL)
- `docker_service.py` - Docker-Container-Status via `docker ps`
- `git_service.py` - Lokale Git-Infos via Subprocess
- `cache_service.py` - JSON-Datei-basierter Cache (120s TTL)
- `db_service.py` - PostgreSQL Connection-Pool (psycopg2)
- `session_import.py` - JSONL-Parser fuer Claude Sessions und zentraler Sync-Orchestrator (Hash-basierter Cache)
- `services/importers/` - Modulare Tool-Importer fuer Codex, Gemini, OpenCode und Kilo
- `session_import_multi.py` - Kompatibilitaetsmodul, re-exportiert die modularen Importer
- `session_import_utils.py` - Shared Helpers: `parse_ts()`, `sanitize_content_json()`
- `session_export.py` - Export: JSON, MD, HTML, XLSX, TXT
- `account_discovery.py` - Erkennt AI-Assistenten-Accounts (Claude, Codex, Gemini)
- `cost_service.py` - Token-Kosten-Berechnung pro Modell
- `plans_import.py` - Scannt ~/.claude/plans/, erkennt Projekte aus Inhalt, importiert in DB
- `ai_scope_service.py` - Sprint 9: AI-Flag-Extraktion (Tool-Erkennung, Write-Detection)
- `file_touch_service.py` - Sprint 10: Per-File Touch-Extraktion, Heatmap-Aggregation, Risk-Radar
- `model_recommendation.py` - Sprint 11: Quality-Score, Stack-Analyse, Empfehlungs-Engine

**Datenspeicher (JSON-Dateien, in .gitignore):**
- `groups.json`, `relations.json`, `ideas.json`, `scheduled_tasks.json` - Benutzerdaten (JSON)
- `project_plans` - DB-Tabelle fuer Plans (importiert aus ~/.claude/plans/)
- `notifications.json`, `.notification_state.json` - Benachrichtigungen
- `favorites.json` - Projekt-Favoriten
- `.env` - Secrets (Gitea-Token, DB-Passwort)

**Konfiguration:** `config.py` laedt alle Werte via `os.environ` mit Defaults. Secrets in `.env`-Datei, geladen via systemd `EnvironmentFile`.

## Verbote

- **Kein `python3 -c` und kein eigenes `psycopg2.connect()`** fuer DB-Zugriffe oder Tests. Ausschliesslich die vorhandenen DB-Funktionen und Service-Schicht im Projekt nutzen. DB-Struktur durch Code-Lesen verstehen, nicht durch Abfragen ans Running-System.

## Wichtige Patterns

- **Blueprint-Architektur:** Jedes Route-Modul ist ein Flask Blueprint, registriert in `routes/__init__.py`.
- **Pfad-Aufloesung:** Immer `services/path_resolver.py:resolve_project_path()` nutzen, nie manuell.
- **Projekt-Metadaten:** `project.json` mit Schema-Version, auto-generiert beim ersten Scan.
- **Sub-Projekte:** Monorepo-Support in `apps/`, `packages/`, `services/`, `modules/` etc.
- **Keine externen HTTP-Libraries:** Gitea-API nutzt `urllib.request` direkt.
- **Notification-System:** Background-Thread prueft alle 60s auf Aenderungen, JSON-Store ist thread-safe via Lock.
- **Volltextsuche:** Nutzt ripgrep (rg) mit Typ-Filtern, Fallback auf grep.
- **Dashboard-Widgets:** Chart.js via CDN, Lazy-Loading beim Tab-Wechsel.
- **Plans-Import:** Scannt `~/.claude/plans/*.md`, erkennt Projekt aus `/mnt/projects/XXX`-Pfaden im Inhalt, verknuepft mit Sessions via Zeitstempel-Korrelation.
- **Session-Sync:** Hash-basierter Cache (`.sync_hashes.json`), kein Timer. Auto-Sync beim Oeffnen der Sessions-Seite, max 1x/Stunde. Bei unveraenderten Dateien null DB-Zugriffe (<1s).
- **Session-Marker-Binding (Sprint SB):** Sessions tragen ihre Marker-Zugehoerigkeit explizit in `sessions.marker_id` (+ `marker_handoff_path`). Setz-Wege: (a) Backfill `scripts/backfill_session_marker_id.py` aus `marker.last_session`, (b) Post-Sync-Hook `_stamp_marker_context_after_sync()` in `session_import.py` stempelt nach jedem `sync_all()` alle Sessions, die seit mtime der projektlokalen `marker-context.md` importiert wurden. Read-Path in `session_routes.py:_resolve_session_marker` bevorzugt `sessions.marker_id` und faellt auf `get_marker_by_last_session` zurueck. Verlauf aller Sessions zu einem Marker: `GET /api/markers/<marker_id>/sessions?project=...`. Schema-Migration idempotent in `db_service.py:ensure_session_marker_schema`.
- **Shared Helpers:** `session_import_utils.py` enthaelt `parse_ts()`, `sanitize_content_json()`, `create_session_meta()`, `update_time_range()` - werden von `session_import.py` und den Modulen unter `services/importers/` gemeinsam genutzt (vermeidet Circular Import). Neue Session-Meta-Felder oder Timestamp-Logik IMMER hier aendern, nicht in den Import-Modulen.
- **Tag-Erkennung:** `project_detector.py:detect_tags()` ist die zentrale Funktion fuer Technologie-Tags (nodejs, python, rust, go, docker, php + Frameworks). NICHT in project_scanner.py oder anderswo duplizieren.
- **Fetch-Wrapper `api.js`:** Zentraler HTTP-Client, eingebunden in base.html vor base.js. Alle API-Aufrufe ueber `api.get(url)`, `api.post(url, body)`, `api.put()`, `api.del()`, `api.request(url, opts)`. Automatisches JSON-Parsing, Content-Type, Status-Check. Fuer Downloads: `api.request(url, {raw: true})`. Wirft `api.ApiError` bei Fehlern. KEIN rohes `fetch()` in Seiten-JS verwenden.
- **Globale JS-Utilities:** `base.js` enthaelt `formatTokens()`, `formatDate()`, `formatDateTime()`, `escapeHtml()`, `formatTimeAgo()` - auf allen Seiten verfuegbar, nicht in einzelnen JS-Dateien duplizieren. Neue Utility-Funktionen die in >1 Seite gebraucht werden gehoeren hierher.
- **Generisches Modal-System:** `base.js` enthaelt `openModal(id)`, `closeModal(id)`, Modal-Stack (`_modalStack`), globalen Escape-Handler und delegierten Overlay-Click. Alle `modal-overlay`-Elemente werden automatisch per Overlay-Click geschlossen. Fuer Modals mit Cleanup-Logik: benannte Wrapper-Funktionen (z.B. `closeEditModal()`) die intern `closeModal(id)` aufrufen. KEINE eigenen Escape-Handler oder `classList.add/remove('show')` in Seiten-JS.
- **Search-Parser:** `_parse_search_output()` in `search_routes.py` - gemeinsame Ergebnis-Verarbeitung fuer rg und grep.
- **Timesheet-Filter:** `_build_timesheet_filter()` in `timesheet_routes.py` - baut WHERE-Klausel aus Request-Parametern.
- **API Error-Handling:** `@api_route` Decorator aus `routes/api_utils.py` statt try/except in jedem Endpoint. Fuer Endpoints mit speziellen Fehler-Responses (z.B. Fallback-Daten) weiterhin manuelles try/except.
- **Plan-Handoff:** `build_plan_handoff_markdown(plan_id)` erzeugt YAML-Frontmatter + 7 Sektionen inkl. Sections/Specs aus `plan_sections`. `write_plan_handoff(plan_id)` schreibt `handoff-<plan_id>.md` ins Projektverzeichnis. Handoff ist IMMER abgeleitet aus DB (plan_sections.status, position) — nie manuell in der .md-Datei pflegen. Wird automatisch beim Project-Memory-Abruf und beim API-Call generiert/aktualisiert.
- **Plan-Sections:** `plan_sections` Tabelle fuer Level-2-Cards (Abschnitte/Specs innerhalb eines Plans). CRUD via `plan_section_service.py`. Board-Spalten nutzen `status` (backlog/ready/in_progress/review/done/blocked), NICHT `workflow_stage`. `/copilot?plan_id=X` zeigt das Section-Board, `/plans` bleibt Level 1.
- **LLM Commands mit Handoff-Kontext:** Platzhalter `{{handoff_data}}`, `{{sections_data}}`, `{{plan_id}}` in `prompts/*.md` verfuegbar. Context Resolver in `llm_command_service.py` laedt diese aus der DB.
- **Workflow-State-System (Sprint Workflow-v2):** Persistente Marker-Workflow-States in `marker_workflow_states` Tabelle. Service-Schicht in `services/workflow_state_service.py` mit expliziten Transition-Regeln (`ALLOWED_TRANSITIONS`), Audit-Trail in `workflow_transitions` Tabelle. Schema lazy via `ensure_workflow_state_schema()`. REST-API in `routes/workflow_routes.py`. Sync aus handoff.md erfolgt automatisch beim Workflow-Loop-Abruf (`_sync_markers_to_workflow` in `workflow_loop_service.py`). Statuses: `planned`, `ready`, `active`, `write_back`, `rating`, `done`, `blocked`.

- **Dead-Code-Erkennung (Quality Scanner):** 3 neue Checks in `auto_coder/checks/`: `dead_frontend.py` (verwaiste JS/CSS + CSS-Klassen), `dead_dependencies.py` (ungenutzte Python/npm Deps), `dead_code.py` (ungenutzte Imports + verwaiste .py-Dateien, AST-basiert). Shared Helpers in `_dead_code_utils.py`. Issues haben `confidence` (high/medium/low) und `evidence` Felder. Projekt-Ignore via `.dead-code-ignore`. V1 erkennt bewusst keine ungenutzten Funktionen/Klassen (Flask-False-Positives), das ist V2.

## Scheduled Tasks (Claude Code)

Dashboard-Seite unter `/scheduled-tasks` zur Verwaltung geplanter Aufgaben. Tasks werden in `scheduled_tasks.json` gespeichert und koennen optional als Claude Code RemoteTrigger angelegt werden.

### Aktive RemoteTrigger

| Name | ID | Cron | Zweck |
|---|---|---|---|
| TUI Bug Check #39294 | trig_01AppVBkp2M9xSd3EySnkpfJ | 0 9 * * * | GitHub-Issue Monitoring |
| Dashboard Health Check | trig_01EyXhKZkHTYQLkMcj3k9Zju | 23 8 * * * | Service + DB + Disk |
| Backup Verification | trig_01NQ7gimC19cSqAvawor3rs6 | 17 2 * * * | Backup-Integritaet |

### CLI-Verwaltung

```bash
# Alle Trigger auflisten
RemoteTrigger list

# Trigger manuell ausfuehren
RemoteTrigger run --trigger_id trig_...

# Trigger deaktivieren
RemoteTrigger update --trigger_id trig_... --body '{"enabled": false}'
```

### Zwei Mechanismen

- **RemoteTrigger**: Persistent, ueberlebt Sessions, laeuft auf claude.ai-Infrastruktur
- **CronCreate**: Session-lokal, max 7 Tage, gut fuer temporaere Checks

## Workflow: Issues bei Aenderungen

Bei **jeder Code-Aenderung** (neue Features, Bugfixes, Refactoring) wird ein Gitea-Issue erstellt:

1. **Vor der Arbeit:** Issue auf Gitea anlegen mit Titel und kurzer Beschreibung
   ```bash
   # Issue erstellen (Gitea API)
   curl -s -X POST "https://git.webideas24.com/api/v1/repos/webideas24/project_dashboard/issues" \
     -H "Authorization: token $GITEA_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "feat: Kurzbeschreibung", "body": "Details..."}'
   ```
2. **Im Commit:** Issue-Nummer referenzieren (`fixes #N` oder `refs #N`)
3. **Nach Abschluss:** Issue schliessen (automatisch via `fixes #N` im Commit oder manuell)

**Ausnahmen** (kein Issue noetig):
- Reine Dokumentations-Updates (next-session.md, Archiv)
- Typo-Fixes unter 5 Zeilen
- Automatisch generierte Dateien (project.json, Cache)

**GitHub-Mirror:** Wird via `git push github main` synchronisiert. Issues nur auf Gitea, nicht doppelt auf GitHub.

## Backup

Automatisches Backup via Cronjob (`scripts/backup.sh`):
- Taeglich 12:30: JSON-Daten, project.json, Claude Sessions (7 Tage Rotation)
- Woechentlich So 13:30: Wochen-Backup (4 Wochen Rotation)
- Speicherort: `/mnt/projects/backups/project-dashboard/`
- **Wichtig:** Cron laeuft mittags, weil die Workstation nachts ausgeschaltet ist. Bei Aenderung der Zeit beide Cron-Eintraege im User-Crontab anpassen.
