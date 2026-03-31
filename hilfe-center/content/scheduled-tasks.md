---
title: "Scheduled Tasks"
icon: "clock-history"
description: "Geplante Aufgaben verwalten - RemoteTrigger und CronCreate für automatisierte Workflows."
section: "DevOps"
tags: [tasks, cron, automation, remotetrigger, scheduling]
order: 3
tips:
  - "RemoteTrigger sind persistent und überleben Sessions - ideal für regelmäßige Checks wie Health Monitoring."
  - "CronCreate eignet sich für temporäre Aufgaben, die maximal 7 Tage laufen sollen."
  - "Tasks werden in scheduled_tasks.json gespeichert und können jederzeit bearbeitet oder gelöscht werden."
---

![Scheduled Tasks](/static/img/scheduled-tasks.png)

## Überblick

Die Scheduled-Tasks-Seite (`/scheduled-tasks`) ermöglicht die Verwaltung geplanter Aufgaben. Du kannst Tasks erstellen, bearbeiten, aktivieren und deaktivieren. Die Ausführung erfolgt über zwei unterschiedliche Mechanismen.

## Zwei Mechanismen

### RemoteTrigger (persistent)

- **Dauerhaft** - Überlebt Sessions und läuft auf der claude.ai-Infrastruktur
- **Cron-basiert** - Ausführung nach Cron-Schedule (z.B. `0 9 * * *` für täglich 9 Uhr)
- **Ideal für** - Regelmäßige Checks, Monitoring, Backups

### CronCreate (session-lokal)

- **Temporär** - Maximal 7 Tage Laufzeit
- **Session-gebunden** - Wird mit der Session beendet
- **Ideal für** - Einmalige oder kurzfristige Prüfungen

## Aktive RemoteTrigger

| Name | Cron | Zweck |
|------|------|-------|
| TUI Bug Check | `0 9 * * *` | GitHub-Issue Monitoring |
| Dashboard Health Check | `23 8 * * *` | Service + DB + Disk |
| Backup Verification | `17 2 * * *` | Backup-Integrität prüfen |

## Verwaltung

Über die Web-Oberfläche kannst du:

- **Neuen Task erstellen** - Name, Beschreibung, Cron-Schedule, Mechanismus wählen
- **Tasks bearbeiten** - Schedule oder Beschreibung ändern
- **Tasks aktivieren/deaktivieren** - Temporär pausieren ohne zu löschen
- **Tasks löschen** - Endgültig entfernen

## CLI-Verwaltung

RemoteTrigger können auch über die Kommandozeile verwaltet werden:

```bash
# Alle Trigger auflisten
RemoteTrigger list

# Trigger manuell ausführen
RemoteTrigger run --trigger_id trig_...

# Trigger deaktivieren
RemoteTrigger update --trigger_id trig_... --body '{"enabled": false}'
```

## Technische Details

- Tasks werden in `scheduled_tasks.json` gespeichert (JSON-Store)
- CRUD-Operationen über `scheduled_tasks_routes.py`
- RemoteTrigger nutzen die Claude-API-Infrastruktur
