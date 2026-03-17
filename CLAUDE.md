# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

**Einstiegspunkt:** `app.py` (85 Zeilen) - Flask-App, registriert Blueprints, startet Notification-Checker, laedt .env.

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
- `session_import.py` - JSONL-Parser fuer Claude Sessions
- `session_export.py` - Export: JSON, MD, HTML, XLSX, TXT

**Datenspeicher (JSON-Dateien, in .gitignore):**
- `groups.json`, `relations.json`, `ideas.json` - Benutzerdaten
- `notifications.json`, `.notification_state.json` - Benachrichtigungen
- `favorites.json` - Projekt-Favoriten
- `.env` - Secrets (Gitea-Token, DB-Passwort)

**Konfiguration:** `config.py` laedt alle Werte via `os.environ` mit Defaults. Secrets in `.env`-Datei, geladen via systemd `EnvironmentFile`.

## Wichtige Patterns

- **Blueprint-Architektur:** Jedes Route-Modul ist ein Flask Blueprint, registriert in `routes/__init__.py`.
- **Pfad-Aufloesung:** Immer `services/path_resolver.py:resolve_project_path()` nutzen, nie manuell.
- **Projekt-Metadaten:** `project.json` mit Schema-Version, auto-generiert beim ersten Scan.
- **Sub-Projekte:** Monorepo-Support in `apps/`, `packages/`, `services/`, `modules/` etc.
- **Keine externen HTTP-Libraries:** Gitea-API nutzt `urllib.request` direkt.
- **Notification-System:** Background-Thread prueft alle 60s auf Aenderungen, JSON-Store ist thread-safe via Lock.
- **Volltextsuche:** Nutzt ripgrep (rg) mit Typ-Filtern, Fallback auf grep.
- **Dashboard-Widgets:** Chart.js via CDN, Lazy-Loading beim Tab-Wechsel.

## Backup

Automatisches Backup via Cronjob (`scripts/backup.sh`):
- Taeglich 01:00: JSON-Daten, project.json, Claude Sessions (7 Tage Rotation)
- Woechentlich So 02:00: Wochen-Backup (4 Wochen Rotation)
- Speicherort: `/mnt/projects/backups/project-dashboard/`
