---
title: "Architektur"
icon: "diagram-3"
description: "Technische Architektur von SessionPilot - Blueprints, Services, Templates und Datenspeicher."
section: "Architektur"
tags: [architektur, flask, blueprints, services, templates, api]
order: 1
tips:
  - "Neue Routen immer als Flask Blueprint anlegen und in routes/__init__.py registrieren."
  - "Pfad-Auflösung immer über services/path_resolver.py - nie manuell Pfade zusammenbauen."
  - "API-Aufrufe im Frontend immer über static/js/api.js statt rohes fetch()."
---

## Überblick

SessionPilot ist eine Flask-basierte Web-Anwendung mit einer klaren Schichtentrennung: Routes (API/Views), Services (Business-Logik) und Datenspeicher (PostgreSQL + JSON).

## Einstiegspunkt

`app.py` ist der zentrale Einstiegspunkt (ca. 85 Zeilen). Er:

- Erstellt die Flask-App
- Registriert alle Blueprints
- Startet den Notification-Checker (Background-Thread)
- Lädt Umgebungsvariablen aus `.env`

## Projektstruktur

| Bereich | Anzahl | Beschreibung |
|---------|--------|--------------|
| Route-Module | 31 | Flask Blueprints in `routes/` |
| Service-Module | 32 | Business-Logik in `services/` |
| Templates | 19 | Jinja2-Templates, erweitern `base.html` |
| JS-Module | 39 | Frontend-Logik in `static/js/` |
| CSS-Dateien | 35 | Styles in `static/css/` |

## Blueprint-Architektur

Jedes Route-Modul ist ein eigenständiger Flask Blueprint. Die Registrierung erfolgt zentral in `routes/__init__.py`. Wichtige Blueprints:

- **data_routes** - Haupt-Daten-Aggregation (`/api/data`, `/api/containers`)
- **session_routes** - Claude Sessions (PostgreSQL)
- **project_routes** - Projekt-Info, Detail, Export
- **search_routes** - Volltextsuche via ripgrep
- **widget_routes** - Dashboard-Widgets (Charts, Statistiken)
- **analytics_routes** - File-Heatmap, Risk-Radar, Modell-Vergleich
- **plans_routes** - Plans Import und Verwaltung

## Service-Schicht

Die Services kapseln die gesamte Business-Logik:

- **project_scanner.py** - Scannt Projekte, verwaltet project.json, Cache
- **project_detector.py** - Typ-Erkennung (monorepo, fork, tool etc.)
- **path_resolver.py** - Zentralisierte Projektpfad-Auflösung
- **notification_service.py** - Thread-safe JSON-Store für Benachrichtigungen
- **notification_checker.py** - Background-Thread, prüft alle 60s auf Änderungen
- **gitea_service.py** - Gitea-API (In-Memory-Cache, 60s TTL)
- **docker_service.py** - Container-Status via `docker ps`
- **db_service.py** - PostgreSQL Connection-Pool
- **session_import.py** - JSONL-Parser mit Hash-basiertem Cache
- **cost_service.py** - Token-Kosten-Berechnung pro Modell
- **file_touch_service.py** - Per-File Touch-Extraktion, Heatmap, Risk-Radar

## Frontend-Architektur

- **api.js** - Zentraler Fetch-Wrapper (`api.get()`, `api.post()`, `api.put()`, `api.del()`)
- **base.js** - Globale Utilities: `formatTokens()`, `formatDate()`, `escapeHtml()`, `formatTimeAgo()`
- **Modal-System** - `openModal(id)`, `closeModal(id)` mit Modal-Stack und Escape-Handler
- **Design Tokens** - Zentrale CSS-Variablen in `static/css/design-tokens.css`
- **Chart.js** - Dashboard-Charts via CDN, Lazy-Loading beim Tab-Wechsel

## Datenspeicher

### PostgreSQL

- **sessions** - Importierte AI-Sessions mit Token-Statistiken
- **messages** - Einzelne Nachrichten pro Session
- **ai_file_touches** - Datei-Zugriffe pro Session
- **project_plans** - Importierte Claude Plans

### JSON-Dateien

- `groups.json` - Projekt-Gruppen
- `relations.json` - Projekt-Beziehungen
- `ideas.json` - Ideen und Notizen
- `scheduled_tasks.json` - Geplante Aufgaben
- `favorites.json` - Projekt-Favoriten
- `notifications.json` - Benachrichtigungen

## Wichtige Patterns

- **@api_route Decorator** - Einheitliches Error-Handling für API-Endpoints
- **Shared Helpers** - `session_import_utils.py` für gemeinsame Funktionen (vermeidet Circular Imports)
- **Tag-Erkennung** - Zentral in `project_detector.py:detect_tags()`, nicht duplizieren
- **Session-Sync** - Hash-basierter Cache, max 1x/Stunde, null DB-Zugriffe bei unveränderten Dateien
