# Projekt-Dashboard - Session-Zusammenfassung

## Letztes Update: 2026-03-14

## Implementierte Features (Session 2026-03-14)

### 1. Claude Code Sessions
- PostgreSQL-Import aller JSONL-Sessions (3 Accounts: claude, claude1, minimax)
- 214+ Sessions importiert, automatischer Sync via systemd-Timer (alle 15min)
- **Übersicht** `/sessions` - Filter (Account, Projekt, Datum), Sortierung, Pagination
- **Detail** `/sessions/<uuid>` - Konversationsansicht, Copy-Buttons, Code-Block-Kopieren
- **Export**: JSON, Markdown, HTML, XLSX, TXT
- Breite-Slider für Konversationsansicht (persistent in localStorage)

### 2. UX-Redesign
- **Sidebar-Navigation** (Workspace/DevOps/Content/Extern) statt Icon-Header
- **Command Palette** Ctrl+K mit Projekt-Suche und Schnellzugriff
- **Base-Template** `base.html` - alle Seiten erben Sidebar, Topbar, Lightbox, Command Palette
- **Stats als Modal** statt permanenter Anzeige
- **Sticky Headers** (Topbar + Filter + Tabellen-Header) auf allen Seiten
- **Topbar**: Breadcrumb, Suche, ⋯-Mehr-Menü (Scan/Docker/Gruppen)

### 3. Globale Architektur
- CSS extrahiert: `static/css/dashboard.css` (globale Styles)
- JS extrahiert: `static/js/dashboard.js` (Dashboard-Logik)
- Alle Templates nutzen `base.html` (sessions, containers, news, vorlagen, dependencies)
- Einheitliche Tabellen-Styles auf allen Seiten
- Sticky thead per dynamischem JS (berechnet Höhen automatisch)

### 4. UX-Features
- **Lightbox** für Bilder (Thumbnails in Tabelle, Klick zum Vergrössern)
- **Projekt-Favoriten** (⭐) mit eigener Sektion oben in der Tabelle
- **Row-Context-Menu** (⋯) mit Details/Bearbeiten/Favorit
- **Alternating Row Colors**, Hover-Highlight
- **Datumsformate** vereinheitlicht (DD.MM.YY)
- **Deadline** ohne Umbruch, mit Leerzeichen nach Icon

### 5. Projekt-Detailseite
- **Route** `/project/<name>` - eigene Seite pro Projekt
- **Sektionen**: Beschreibung, Details, Tech-Stack, Commits, README, Screenshots, Meilensteine, Beziehungen, Claude Sessions, Container
- **README als Markdown** gerendert (Tabellen, Code-Blöcke, Blockquotes)
- **WYSIWYG Editor** (EasyMDE) zum Bearbeiten der README.md direkt im Browser
- **Export**: HTML (standalone, druckbar), Markdown, JSON
- **Info-API** `/api/info` mit Bindestrich/Underscore Fallback

## Dateistruktur

```
/mnt/projects/project_dashboard/
├── app.py                          # Flask-Backend (alle Routes + API)
├── config.py                       # Config (DB, Accounts, Gitea)
├── sync_sessions.py                # Standalone Session-Sync-Skript
├── favorites.json                  # Projekt-Favoriten
├── relations.json                  # Beziehungen
├── ideas.json                      # Ideen/Notizen
├── groups.json                     # Benutzerdefinierte Gruppen
├── routes/
│   ├── __init__.py                 # Blueprint-Registrierung
│   └── session_routes.py           # Session-API + Seiten
├── services/
│   ├── db_service.py               # PostgreSQL-Pool + Schema
│   ├── session_import.py           # JSONL-Parser + Sync
│   ├── session_export.py           # Export (JSON/MD/HTML/XLSX/TXT)
│   ├── project_scanner.py          # Projekt-Erkennung
│   ├── docker_service.py           # Docker-Container-Status
│   ├── gitea_service.py            # Gitea-API
│   ├── git_service.py              # Git-Info
│   └── cache_service.py            # JSON-Cache
├── templates/
│   ├── base.html                   # Globales Base-Template (Sidebar, Topbar, Cmd Palette)
│   ├── index.html                  # Dashboard (Projekt-Tabelle)
│   ├── project_detail.html         # Projekt-Detailseite + README-Editor
│   ├── sessions.html               # Claude Sessions Übersicht
│   ├── session_detail.html         # Session-Konversation
│   ├── containers.html             # Container-Übersicht
│   ├── dependencies.html           # Abhängigkeiten-Graph
│   ├── news.html                   # News-Seite
│   └── vorlagen.html               # Vorlagen-Sammlung
├── static/
│   ├── css/dashboard.css           # Globale CSS (Sidebar, Tabellen, Modals, etc.)
│   ├── js/dashboard.js             # Dashboard JS (Gruppen, Filter, Rendering)
│   └── favicon.svg
└── systemd/
    ├── claude-session-sync.service  # Sync-Service
    └── claude-session-sync.timer    # Timer (alle 15min)
```

## Nächste Session: Dokumenten-System

### Feature: Projekt-Dokumenten-System

Die Projekt-Detailseite soll erweitert werden um ein vollständiges Dokumenten-System:

#### 1. Dokument-Sammlung API
- `GET /api/project/<name>/documents` - Sammelt rekursiv:
  - Alle `.md` Dateien (README, CHANGELOG, docs/, etc.)
  - Alle Bilder (.png, .jpg, .svg, .webp, etc.)
  - Gruppiert nach Verzeichnis
  - Mit Dateigrösse, Änderungsdatum, Typ

#### 2. Dokumenten-Browser (UI)
- **Baumstruktur** aller Dateien im linken Panel
- **Viewer** rechts: MD-Dateien gerendert, Bilder als Preview
- **Suche** innerhalb der Dokumente
- Jede MD-Datei mit EasyMDE bearbeitbar (wie README)

#### 3. Bilder-Gallery
- Alle Bilder des Projekts als Grid-Gallery
- Thumbnails mit Lightbox
- Bilder-Upload Möglichkeit?

#### 4. Export-Konfigurator
- **Checkboxen** pro Dokument (auswählen was exportiert wird)
- **Alle/Keine** Schnellauswahl
- **Export-Formate**:
  - HTML Bundle (alle ausgewählten Dateien in einem HTML, Bilder eingebettet als Base64)
  - ZIP (Dateien + Bilder als Archiv)
  - Markdown (alle MD-Dateien zusammengefügt)
  - JSON (Struktur + Inhalte)
- **Ziel**: Direkt auf Vermarktungsseiten einbettbar (mit Bildern!)

#### 5. Implementierungsplan
1. API: `/api/project/<name>/documents` - Datei-Sammlung
2. API: `/api/project/<name>/document/<path>` - Einzelnes Dokument lesen/schreiben
3. API: `/api/project/<name>/export-bundle` - Export mit Auswahl
4. UI: Dokumenten-Browser in `project_detail.html` als neue Sektion
5. UI: Export-Modal mit Checkboxen + Format-Auswahl

## Git Status

- Branch: `main`
- Remote: `origin` (git.webideas24.com)
- Letzter Commit: `a6239e5` - README Editor + README API
