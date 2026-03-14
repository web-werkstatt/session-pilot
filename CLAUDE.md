# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

Flask-basiertes Web-Dashboard zur Verwaltung und Uebersicht aller Projekte unter `/mnt/projects/` sowie Docker-Container auf dem Entwicklungsserver. Laeuft als systemd-Service (`project-dashboard`) auf Port 5055.

## Befehle

```bash
# Entwicklung: App manuell starten
python3 app.py

# Produktion: systemd-Service
sudo systemctl restart project-dashboard
sudo systemctl status project-dashboard

# Logs
tail -f /mnt/projects/project_dashboard/dashboard.log
```

Kein Build-Schritt, keine Tests, kein Linting konfiguriert. Reine Python-Anwendung ohne virtuelle Umgebung - Abhaengigkeiten (Flask) sind systemweit installiert.

## Architektur

**Einstiegspunkt:** `app.py` - Flask-App mit allen Routes und JSON-Datei-basierten Datenspeichern (kein Datenbankserver).

**Service-Schicht (`services/`):**
- `project_scanner.py` - Kernlogik: Scannt `/mnt/projects/`, erkennt Projekttypen (Flask, Node, Docker etc.), liest/generiert `project.json` pro Projekt, erkennt Sub-Projekte in Monorepos
- `gitea_service.py` - Gitea-API-Integration (REST via urllib, kein requests-Package), In-Memory-Cache (60s TTL)
- `docker_service.py` - Docker-Container-Status via `docker ps` Subprocess-Aufruf
- `git_service.py` - Lokale Git-Infos via `git log`/`git status` Subprocess-Aufrufe
- `cache_service.py` - JSON-Datei-basierter Cache (`/mnt/projects/.project_dashboard_cache.json`, 120s TTL)

**Datenspeicher (JSON-Dateien im Projektroot):**
- `groups.json` - Benutzerdefinierte Projekt-Gruppen (Privat, Geschaeftlich, Kunde etc.)
- `relations.json` - Projekt-Beziehungen/Abhaengigkeiten (depends_on, replaces, extends etc.)
- `ideas.json` - Ideen/Notizen-System mit Kategorien und Status

**Templates:** Jinja2-Templates in `templates/` - enthalten eingebettetes JavaScript/CSS (kein separates Frontend-Build).

## Wichtige Patterns

- **Projekt-Metadaten:** Jedes Projekt unter `/mnt/projects/` kann eine `project.json` mit Schema-Version, Beschreibung, Gruppe, Prioritaet, Fortschritt und Meilensteinen haben. Schema-Version wird in `project_scanner.py` via `SCHEMA_VERSION` verwaltet.
- **Sub-Projekte:** Monorepo-Support - Sub-Projekte werden in `apps/`, `packages/`, `services/`, `modules/` etc. gesucht. API-Pfade nutzen `<path:name>` fuer `parent/subproject` Notation.
- **Keine externen HTTP-Libraries:** Gitea-API nutzt `urllib.request` direkt (kein requests/httpx).
- **Sync-Status:** Vergleicht lokalen Git-SHA mit Gitea-Remote-SHA um Sync-Konflikte zu erkennen.
- **Konfiguration:** Alle Einstellungen in `config.py` - enthaelt Gitea-Token (sensibel, nicht committen wenn geaendert).
