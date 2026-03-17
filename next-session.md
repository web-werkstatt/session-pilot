# Projekt-Dashboard - Naechste Session

## Letzte Aktualisierung: 2026-03-17
## Status: Alle tech. Schulden + 4 Features abgearbeitet, Codebase vollstaendig modularisiert

## Session 2026-03-17 (Abend) - Zusammenfassung

### Technische Schulden (alle erledigt)
- **dashboard.css** (1012 Zeilen) in 5 thematische Dateien aufgeteilt: base.css, layout.css, table.css, modals.css, features.css
- **project_routes.py** (534 Zeilen) aufgeteilt: /api/info -> project_info_routes.py (281 Zeilen)
- **base.html** (391 Zeilen) -> 132 Zeilen (JS nach static/js/base.js extrahiert)
- **project_detail.html** (384 Zeilen) -> 286 Zeilen (CSS nach project-detail.css)
- **dashboard.js** (1627 Zeilen) in 10 Module aufgeteilt (max 316 Zeilen pro Datei)
- **index.html** (575 Zeilen) -> 256 Zeilen (Modals in partials/, JS in index-ui.js)
- **Pre-Commit Hook** installiert: Dateigroessen-Limits + Secrets-Erkennung
- **Docker-Compose** end-to-end getestet (PostgreSQL + Dashboard)

### Neue Features
1. **Container-Aktionen** - Start/Stop/Restart + Logs-Modal direkt aus /containers
2. **Session-Analyse** (/sessions/analysis) - Token-Kosten nach Modell/Projekt, Stunden/Wochentag-Verteilung, haeufigste Tools, Aktivitaets-Charts
3. **Git-Aktionen** - Commit/Push/Pull Panel in Projekt-Detailseite mit Status, geaenderten Dateien, Ahead/Behind-Anzeige
4. **Projekt-Archivierung** - Archivieren/Wiederherstellen via Kontextmenue, Toggle-Filter in Filter-Leiste

## Git Commits (Session 2026-03-17 Abend)

```
112455c Refactoring: dashboard.js + index.html aufgeteilt (Pre-Commit clean)
ab5170f Feature: Projekt-Archivierung mit Filter-Toggle
feb078f Feature: Git-Aktionen (Commit/Push/Pull) aus Projekt-Detail
13760c1 Features: Container-Aktionen + Session-Analyse + base.js Extraktion
59510ff Technische Schulden: CSS + Routes aufgeteilt, Pre-Commit Hook
```

## Naechste Session: Offene Punkte

### Moegliche Features
- **Projekt-Tags/Labels** - Flexiblere Kategorisierung als nur Gruppen
- **Session-Import automatisieren** - Cronjob statt manueller Sync
- **Container-Compose-Aktionen** - Ganzen Stack starten/stoppen (nicht nur einzelne Container)
- **Dashboard auf base.html migrieren** - index.html nutzt noch eigenes Layout statt base.html

### Code-Qualitaet
- Alle Dateien unter den Groessen-Limits, Pre-Commit Hook greift sauber
- Keine bekannten technischen Schulden

## Dateistruktur (aktuell)

```
project_dashboard/
├── app.py                          # Flask-Einstiegspunkt (85 Zeilen)
├── config.py                       # Konfiguration via Umgebungsvariablen
├── routes/
│   ├── __init__.py                 # Blueprint-Registrierung (14 Blueprints)
│   ├── project_routes.py           # Projekt Detail, Save, Export, Archiv
│   ├── project_info_routes.py      # /api/info (Projekt-Detailansicht)
│   ├── data_routes.py              # /api/data, /api/containers, Container-Aktionen
│   ├── document_routes.py          # Dokumenten-Browser + Upload
│   ├── session_routes.py           # Claude Sessions
│   ├── session_analysis_routes.py  # Session-Analyse (Kosten, Tools, Zeiten)
│   ├── git_routes.py               # Git-Aktionen (Status, Commit, Push, Pull)
│   ├── search_routes.py            # Volltextsuche (ripgrep)
│   ├── widget_routes.py            # Dashboard-Widgets
│   ├── notification_routes.py      # Benachrichtigungs-API
│   ├── relation_routes.py          # Abhaengigkeiten
│   ├── group_routes.py             # Gruppen
│   ├── idea_routes.py              # Ideen/Notizen
│   └── news_routes.py              # News + Vorlagen
├── services/
│   ├── project_scanner.py          # Scan + project.json (361 Zeilen)
│   ├── project_detector.py         # Typ-Erkennung (352 Zeilen)
│   ├── description_extractor.py    # Beschreibung + Deps (395 Zeilen)
│   ├── path_resolver.py            # Pfad-Aufloesung
│   ├── notification_service.py     # JSON-Store (thread-safe)
│   ├── notification_checker.py     # Background-Thread (60s)
│   ├── gitea_service.py            # Gitea API
│   ├── docker_service.py           # Docker Status + Aktionen + Logs
│   ├── git_service.py              # Git Info + Commit/Push/Pull
│   ├── cache_service.py            # JSON-Cache
│   ├── db_service.py               # PostgreSQL Pool
│   ├── session_import.py           # JSONL-Parser
│   └── session_export.py           # Export-Formate
├── templates/
│   ├── base.html                   # Basis-Layout (132 Zeilen)
│   ├── index.html                  # Dashboard-Startseite (256 Zeilen)
│   ├── partials/index_modals.html  # Modals fuer Index-Seite
│   ├── containers.html             # Container-Verwaltung + Aktionen
│   ├── session_analysis.html       # Session-Analyse mit Charts
│   ├── project_detail.html         # Projekt-Detail + Git-Panel
│   └── ...                         # sessions, news, vorlagen, dependencies
├── static/
│   ├── css/
│   │   ├── dashboard.css           # Import-Hub (6 Zeilen)
│   │   ├── base.css                # Reset, Badges, Status
│   │   ├── layout.css              # Sidebar, Topbar, Tabs
│   │   ├── table.css               # Tabelle, Lightbox
│   │   ├── modals.css              # Modals, Forms, Groups
│   │   ├── features.css            # Command Palette, News, Stats, Ideas
│   │   ├── project-detail.css      # Projekt-Detail + Git-Panel + EasyMDE
│   │   ├── documents.css           # Dokumenten-Browser
│   │   ├── widgets.css             # Dashboard-Widgets
│   │   └── notifications.css       # Benachrichtigungen
│   └── js/
│       ├── dashboard-state.js      # Globale Variablen (21)
│       ├── dashboard-core.js       # loadData, renderData, Init (108)
│       ├── dashboard-table.js      # Tabellen-Rendering (309)
│       ├── dashboard-modals.js     # Edit-Modal, Relations (316)
│       ├── dashboard-groups.js     # Gruppen CRUD (257)
│       ├── dashboard-actions.js    # Favoriten, Archiv, Refresh (194)
│       ├── dashboard-ideas.js      # Ideen/Notizen (160)
│       ├── dashboard-filters.js    # Filter, Suche, Sortierung (137)
│       ├── dashboard-misc.js       # Quotes, Konfetti (88)
│       ├── dashboard-news.js       # News Ticker (57)
│       ├── index-ui.js             # Lightbox, Stats, Sidebar, Cmd Palette (130)
│       ├── base.js                 # Lightbox, Cmd Palette fuer base.html (253)
│       ├── git-actions.js          # Git-Panel fuer Projekt-Detail (161)
│       ├── documents.js            # Dokumenten-Browser
│       ├── widgets.js              # Dashboard-Widgets
│       └── notifications.js        # Benachrichtigungen
├── scripts/
│   ├── backup.sh                   # Backup-Skript (taeglich + woechentlich)
│   └── pre-commit                  # Git Hook: Dateigroessen + Secrets
├── Dockerfile + docker-compose.yml # Docker-Deployment
├── setup.sh                        # Bare-Metal Installation
└── requirements.txt                # Python-Abhaengigkeiten
```
