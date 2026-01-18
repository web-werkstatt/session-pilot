# Projekt-Dashboard

Web-GUI zur Übersicht aller Projekte und Docker-Container auf dem Entwicklungsserver.

## Features

- **Projekt-Übersicht**: Alle Projekte in `/mnt/projects/` mit Metadaten
- **Container-Status**: Docker-Container mit Health-Check
- **Gitea-Integration**: Sync-Status mit Remote-Repository
- **Projekt-Management**: Priorität, Deadline, Fortschritt, Meilensteine
- **Gruppierung**: Privat, Geschäftlich, Kunde
- **Filter & Sortierung**: Nach Gruppe, Priorität, Aktivität
- **Live-Updates**: Automatische Aktualisierung alle 15 Sekunden

## Struktur

```
project_dashboard/
├── app.py                    # Flask-Hauptanwendung
├── config.py                 # Konfiguration
├── services/
│   ├── __init__.py
│   ├── gitea_service.py      # Gitea API
│   ├── git_service.py        # Lokale Git-Infos
│   ├── docker_service.py     # Docker-Container
│   ├── project_scanner.py    # Projekt-Erkennung
│   └── cache_service.py      # Cache-Verwaltung
├── templates/
│   ├── index.html            # Dashboard
│   └── containers.html       # Container-Übersicht
├── static/
│   └── favicon.svg
└── dashboard.log             # Log-Datei
```

## Installation

Das Dashboard läuft als systemd-Service:

```bash
# Service-Status prüfen
sudo systemctl status project-dashboard

# Service neu starten
sudo systemctl restart project-dashboard

# Logs anzeigen
tail -f /mnt/projects/project_dashboard/dashboard.log
```

## Konfiguration

Einstellungen in `config.py`:

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `PROJECTS_DIR` | Projektverzeichnis | `/mnt/projects` |
| `PORT` | Web-Server Port | `5055` |
| `GITEA_URL` | Gitea Server URL | `https://git.webideas24.com` |
| `GITEA_TOKEN` | API-Token | (konfiguriert) |

## Projekt-Metadaten

Jedes Projekt kann eine `project.json` im Projektordner haben:

```json
{
  "name": "Projektname",
  "description": "Kurze Beschreibung",
  "group": "private|business|customer",
  "priority": "high|medium|low",
  "deadline": "2026-01-31",
  "progress": 75,
  "milestones": [
    {"name": "MVP", "done": true},
    {"name": "Testing", "done": false}
  ]
}
```

Metadaten können direkt im Dashboard über den ✏️ Button bearbeitet werden.

## URLs

| Seite | URL |
|-------|-----|
| Dashboard | http://192.168.100.93:5055/ |
| Container | http://192.168.100.93:5055/containers |

## API-Endpunkte

| Endpunkt | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/data` | GET | Alle Projektdaten |
| `/api/containers` | GET | Container-Liste |
| `/api/project/<name>` | GET | Projekt-Metadaten laden |
| `/api/project/save` | POST | Projekt-Metadaten speichern |

## Entwicklung

```bash
# Manuell starten (für Entwicklung)
cd /mnt/projects/project_dashboard
python3 app.py

# Service stoppen
sudo systemctl stop project-dashboard
```

## Systemd-Service

Der Service ist konfiguriert unter `/etc/systemd/system/project-dashboard.service`:

- Startet automatisch nach `network.target` und `docker.service`
- Neustart bei Fehler nach 10 Sekunden
- Läuft als User `joshko`
