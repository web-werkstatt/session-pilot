---
title: "Erste Schritte"
icon: "rocket-takeoff"
description: "Schnellstart-Anleitung für SessionPilot"
section: "Einstieg"
tags: [quickstart, installation, navigation, setup]
order: 2
tips:
  - "Sessions werden automatisch synchronisiert - beim ersten Öffnen der Sessions-Seite und dann maximal einmal pro Stunde."
  - "Projekte als Favorit markieren für schnellen Zugriff auf dem Dashboard."
  - "Der systemd-Service startet automatisch nach einem Server-Neustart."
---

![Dashboard Übersicht](/static/img/dashboard.png)

## Zugriff auf SessionPilot

SessionPilot ist nach der Installation direkt im Browser erreichbar:

```
http://localhost:5055
```

Oder über die IP-Adresse bzw. den Hostnamen deines Servers im lokalen Netzwerk.

## Was passiert beim ersten Start?

Beim ersten Aufruf führt SessionPilot automatisch folgende Schritte aus:

1. **Projekt-Scan** - Alle Verzeichnisse unter `/mnt/projects/` werden gescannt und als Projekte erkannt
2. **Typ-Erkennung** - Jedes Projekt bekommt automatisch einen Typ (z.B. Node.js, Python, Monorepo) und Technologie-Tags
3. **Metadaten-Erstellung** - Für jedes Projekt wird eine `project.json` mit Schema-Version angelegt
4. **Container-Status** - Laufende Docker-Container werden erkannt und den Projekten zugeordnet

## Session-Synchronisation

Claude Code Sessions werden automatisch aus den JSONL-Dateien importiert:

- **Speicherort**: `~/.claude/projects/` (Claude Code), weitere Pfade für Codex und Gemini
- **Auto-Sync**: Beim Öffnen der Sessions-Seite, maximal einmal pro Stunde
- **Hash-Cache**: Nur geänderte Dateien werden neu importiert - unveränderte Dateien verursachen null Datenbankzugriffe

## Navigation

Die Sidebar ist in drei Hauptbereiche gegliedert:

### Workspace
- **Dashboard** - Projekt-Übersicht mit Favoriten und Aktivitäts-Heatmap
- **Sessions** - Alle AI-Coding-Sessions mit Filter und Export
- **Session-Analyse** - Charts und Statistiken zu Kosten, Modellen und Outcomes
- **Usage Monitor** - Live Token-Verbrauch
- **Usage Reports** - Tages-, Wochen- und Monatsberichte
- **Timesheets** - AI-Arbeitszeiterfassung pro Projekt
- **Modell-Vergleich** - Qualitätsvergleich verschiedener AI-Modelle

### DevOps
- **Container** - Docker-Container-Status und Health-Checks
- **Dependencies** - Projekt-Abhängigkeiten
- **Scheduled Tasks** - Geplante Aufgaben und RemoteTrigger
- **Plans** - Importierte Claude Plans
- **Quality** - Code-Qualität via Semgrep

### Content
- **News** - Neuigkeiten und Updates
- **Scaffold** - Neues Projekt erstellen
- **Vorlagen** - Projekt-Templates
- **Einstellungen** - Konfiguration

## Service-Verwaltung

SessionPilot läuft als systemd-Service. Die wichtigsten Befehle:

```bash
# Status prüfen
sudo systemctl status project-dashboard

# Service neu starten
sudo systemctl restart project-dashboard

# Service stoppen
sudo systemctl stop project-dashboard

# Logs anzeigen (live)
tail -f /mnt/projects/project_dashboard/dashboard.log
```

### Docker-Alternative

Falls Docker bevorzugt wird:

```bash
# Starten
docker compose up -d

# Stoppen
docker compose down

# Logs
docker compose logs -f
```

## Nächste Schritte

- Öffne die **Sessions-Seite**, um den ersten Import deiner AI-Sessions auszulösen
- Markiere häufig genutzte Projekte als **Favoriten** auf dem Dashboard
- Prüfe unter **Container**, ob alle Docker-Services laufen
- Schaue dir die **Session-Analyse** an für erste Einblicke in Kosten und Modell-Nutzung
