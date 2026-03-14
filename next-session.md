# Projekt-Dashboard - Session-Zusammenfassung

## Letztes Update: 2026-03-14

## Implementierte Features (Session 2026-03-14 Nachmittag)

### 6. Dokumenten-System (NEU)
- **Lazy-Loading Datei-Browser**: Baumstruktur mit on-demand Ordner-Expansion
  - Nur Root-Verzeichnis wird initial geladen, Unterordner erst bei Klick
  - Verhindert Browser-Freeze bei grossen Projekten (z.B. WordPress mit 314k Dateien)
  - Suche innerhalb geladener Dateien
- **Dokument-Viewer**: Markdown gerendert, Raw-Text, Bilder-Vorschau
  - EasyMDE-Editor pro Datei (Bearbeiten/Speichern direkt im Browser)
- **Bilder-Galerie**: Grid mit Thumbnails, Lade-Spinner pro Bild, "X Bilder geladen" Counter
- **Export-Konfigurator**: Datei-Auswahl mit Checkboxen, 4 Formate:
  - ZIP (Archiv), HTML Bundle (Base64-Bilder eingebettet), Markdown (zusammengefuegt), JSON
- **Status-Bar**: Lade-Feedback auf allen Ebenen (Spinner, Erfolg, Fehler)
- **API-Endpunkte**:
  - `GET /api/project/<name>/documents?dir=.` - Lazy-Loading pro Verzeichnis
  - `GET /api/project/<name>/document/<path>` - Einzeldokument (MD gerendert, Bilder als Base64)
  - `PUT /api/project/<name>/document/<path>` - Dokument speichern
  - `GET /api/project/<name>/document-image/<path>` - Bild direkt servieren
  - `POST /api/project/<name>/export-bundle` - Export mit Auswahl

### 7. Lightbox-Navigation (NEU)
- **Vor/Zurueck-Pfeile** links/rechts (halbtransparent, Glasmorphismus)
- **Tastatur**: Pfeiltasten links/rechts navigieren, Escape schliesst
- **Counter**: "2 / 6" Anzeige unten mittig
- **Dateiname** unter dem Bild
- **Schliessen-Button** oben rechts (X)
- Global auf allen Seiten (base.html)

## Fruehere Features (Session 2026-03-14 Vormittag)

### 1. Claude Code Sessions
- PostgreSQL-Import aller JSONL-Sessions (3 Accounts: claude, claude1, minimax)
- 214+ Sessions importiert, automatischer Sync via systemd-Timer (alle 15min)
- Uebersicht, Detail, Export (JSON/MD/HTML/XLSX/TXT)

### 2. UX-Redesign
- Sidebar-Navigation, Command Palette Ctrl+K, Base-Template, Sticky Headers

### 3. Globale Architektur
- CSS/JS extrahiert, alle Templates nutzen base.html

### 4. UX-Features
- Lightbox, Favoriten, Row-Context-Menu, Alternating Rows

### 5. Projekt-Detailseite
- Route `/project/<name>`, README-Editor, Export (HTML/MD/JSON)

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
│   ├── session_routes.py           # Session-API + Seiten
│   └── document_routes.py          # Dokumenten-System API (NEU)
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
│   ├── base.html                   # Globales Base-Template + Lightbox-Navigation
│   ├── index.html                  # Dashboard (Projekt-Tabelle)
│   ├── project_detail.html         # Projekt-Detail + Dokumenten-Browser
│   ├── sessions.html               # Claude Sessions Uebersicht
│   ├── session_detail.html         # Session-Konversation
│   ├── containers.html             # Container-Uebersicht
│   ├── dependencies.html           # Abhaengigkeiten-Graph
│   ├── news.html                   # News-Seite
│   └── vorlagen.html               # Vorlagen-Sammlung
├── static/
│   ├── css/dashboard.css           # Globale CSS + Lightbox-Navigation
│   ├── css/documents.css           # Dokumenten-Browser CSS (NEU)
│   ├── js/dashboard.js             # Dashboard JS (Gruppen, Filter, Rendering)
│   ├── js/documents.js             # Dokumenten-Browser JS (NEU)
│   └── favicon.svg
└── systemd/
    ├── claude-session-sync.service  # Sync-Service
    └── claude-session-sync.timer    # Timer (alle 15min)
```

## Naechste Session: Ideen

- **Dokumenten-System erweitern**: Datei-Upload, Drag&Drop Bilder
- **Volltextsuche**: Ueber alle Dokumente aller Projekte suchen
- **Dashboard-Widgets**: Projekt-Aktivitaet als Heatmap/Chart
- **Benachrichtigungen**: Neue Commits, Container-Status-Aenderungen

## Git Status

- Branch: `main`
- Remote: `origin` (git.webideas24.com)
- Letzter Commit: `6512ee2` - Dokumenten-System + Lightbox-Navigation
