# Projekt-Dashboard

Web-Dashboard zur Verwaltung und Übersicht aller Projekte, Docker-Container und Claude Code Sessions.

## Features

- **Projekt-Übersicht**: Automatische Erkennung aller Projekte mit Typ, Tech-Stack, Git-Status
- **Container-Status**: Docker-Container mit Health-Check
- **Gitea-Integration**: Sync-Status mit Remote-Repository
- **Claude Sessions**: Import, Anzeige und Export von Claude Code Sessions (PostgreSQL)
- **Projekt-Management**: Priorität, Deadline, Fortschritt, Meilensteine
- **Dokumenten-System**: Lazy-Loading Browser, Viewer, Editor, Export
- **Gruppierung**: Benutzerdefinierte Gruppen (Privat, Geschäftlich, Kunde etc.)
- **Ideen/Notizen**: Kategorisierte Ideen mit Projekt-Zuordnung
- **Beziehungen**: Projekt-Abhängigkeiten visualisieren
- **News**: Automatische Aktivitäts-Übersicht aller Projekte
- **Backup**: Tägliches + wöchentliches automatisches Backup

## Schnellstart

### Option A: Docker (empfohlen)

```bash
git clone https://git.webideas24.com/webideas24/project_dashboard.git
cd project_dashboard
cp .env.example .env
# .env anpassen (Gitea-Token, Projekt-Pfad)
docker compose up -d
```

Dashboard öffnen: http://localhost:5055

### Option B: Bare-Metal (Linux)

```bash
git clone https://git.webideas24.com/webideas24/project_dashboard.git
cd project_dashboard
./setup.sh
```

### Option C: Manuell

```bash
git clone https://git.webideas24.com/webideas24/project_dashboard.git
cd project_dashboard
pip3 install -r requirements.txt
cp .env.example .env
# .env anpassen
python3 app.py
```

## Konfiguration

Alle Einstellungen via Umgebungsvariablen (`.env`-Datei):

| Variable | Beschreibung | Standard |
|---|---|---|
| `DASHBOARD_PROJECTS_DIR` | Pfad zu deinen Projekten | `/mnt/projects` |
| `DASHBOARD_PORT` | Web-Server Port | `5055` |
| `GITEA_URL` | Gitea Server URL | `https://git.webideas24.com` |
| `GITEA_TOKEN` | Gitea API-Token | (leer) |
| `GITEA_USER` | Gitea Benutzername | `webideas24` |
| `DB_HOST` | PostgreSQL Host | `localhost` |
| `DB_PORT` | PostgreSQL Port | `5432` |
| `DB_NAME` | Datenbankname | `project_dashboard` |
| `DB_USER` | DB-Benutzer | `autodns` |
| `DB_PASSWORD` | DB-Passwort | (leer) |

## Projektstruktur

```
project_dashboard/
├── app.py                          # Flask-Einstiegspunkt (schlank)
├── config.py                       # Konfiguration via Umgebungsvariablen
├── routes/
│   ├── project_routes.py           # Projekt-Info, Data, Save, Export, Assets
│   ├── relation_routes.py          # Abhängigkeiten
│   ├── group_routes.py             # Gruppen-Verwaltung
│   ├── idea_routes.py              # Ideen/Notizen
│   ├── news_routes.py              # News + Vorlagen
│   ├── session_routes.py           # Claude Sessions
│   └── document_routes.py          # Dokumenten-Browser
├── services/
│   ├── project_scanner.py          # Projekt-Erkennung + Analyse
│   ├── gitea_service.py            # Gitea API (urllib)
│   ├── git_service.py              # Lokale Git-Infos
│   ├── docker_service.py           # Docker Container-Status
│   ├── cache_service.py            # JSON-Cache
│   ├── db_service.py               # PostgreSQL Connection-Pool
│   ├── session_import.py           # JSONL-Parser für Claude Sessions
│   ├── session_export.py           # Export: JSON, MD, HTML, XLSX, TXT
│   └── path_resolver.py            # Zentralisierte Pfad-Auflösung
├── templates/                      # Jinja2-Templates
├── static/                         # CSS, JS, Favicon
├── scripts/
│   └── backup.sh                   # Automatisches Backup-Skript
├── Dockerfile                      # Container-Image
├── docker-compose.yml              # Docker Compose mit PostgreSQL
├── setup.sh                        # Bare-Metal Installationsskript
├── requirements.txt                # Python-Abhängigkeiten
├── .env.example                    # Konfigurations-Vorlage
├── groups.json                     # Benutzerdefinierte Gruppen
├── relations.json                  # Projekt-Beziehungen
└── ideas.json                      # Ideen/Notizen
```

## Voraussetzungen

| Komponente | Erforderlich | Wofür |
|---|---|---|
| Python 3.9+ | Ja | Anwendung |
| PostgreSQL 14+ | Optional | Claude Sessions (Import/Export) |
| Docker | Optional | Container-Status-Anzeige |
| Git | Optional | Git-Status, Commits |
| Gitea | Optional | Remote-Sync-Status |

Ohne PostgreSQL funktioniert alles außer dem Sessions-Feature.
Ohne Docker wird die Container-Seite leer angezeigt.

## Projekt-Metadaten

Jedes Projekt kann eine `project.json` im Projektordner haben:

```json
{
  "name": "Projektname",
  "description": "Kurze Beschreibung",
  "group": "private",
  "priority": "high",
  "deadline": "2026-01-31",
  "progress": 75,
  "milestones": [
    {"name": "MVP", "done": true},
    {"name": "Testing", "done": false}
  ]
}
```

Metadaten können direkt im Dashboard bearbeitet werden.

## API-Endpunkte

| Endpunkt | Methode | Beschreibung |
|---|---|---|
| `/api/data` | GET | Alle Projektdaten + Stats |
| `/api/containers` | GET | Docker Container-Liste |
| `/api/info?name=X` | GET | Umfassende Projekt-Info |
| `/api/project/<name>` | GET | project.json laden |
| `/api/project/save` | POST | project.json speichern |
| `/api/project/<name>/documents` | GET | Dokumenten-Browser |
| `/api/project/<name>/readme` | GET/PUT | README lesen/schreiben |
| `/api/project/<name>/export` | GET | Export (json/md/html) |
| `/api/groups` | GET/POST | Gruppen verwalten |
| `/api/relations` | GET/POST | Beziehungen verwalten |
| `/api/ideas` | GET/POST | Ideen verwalten |
| `/api/sessions` | GET | Claude Sessions |
| `/api/sessions/sync` | POST | Sessions importieren |
| `/api/news` | GET | Aktivitäts-News |

## Backup

Automatisches Backup via Cronjob:

```bash
# Tägliches Backup (01:00 Uhr, 7 Tage Rotation)
scripts/backup.sh daily

# Wöchentliches Backup (Sonntag 02:00, 4 Wochen Rotation)
scripts/backup.sh weekly
```

Gesichert werden: JSON-Datenspeicher, alle project.json, Claude Sessions/Memory.

## Entwicklung

```bash
# Manuell starten
python3 app.py

# systemd-Service
sudo systemctl restart project-dashboard
sudo systemctl status project-dashboard

# Logs
tail -f dashboard.log
```
