---
title: "Containers"
icon: "box"
description: "Docker-Container-Übersicht - Status, Ports, Images und Uptime aller laufenden Container."
section: "DevOps"
tags: [docker, containers, devops, status, monitoring]
order: 1
tips:
  - "Der Notification-Checker prüft alle 60 Sekunden den Container-Status und meldet Änderungen automatisch."
  - "Gestoppte oder fehlerhafte Container werden rot markiert, damit du Probleme sofort erkennst."
---

![Containers](/static/img/containers.png)

## Überblick

Die Container-Seite (`/containers`) zeigt alle Docker-Container deines Systems in einer übersichtlichen Tabelle. SessionPilot ruft die Daten direkt über `docker ps` ab und stellt sie strukturiert dar.

## Angezeigte Informationen

Für jeden Container werden folgende Details angezeigt:

- **Name** - Der Container-Name
- **Image** - Das verwendete Docker-Image mit Tag
- **Status** - Aktueller Zustand (running, stopped, restarting, exited)
- **Ports** - Gemappte Ports (Host:Container)
- **Uptime** - Laufzeit seit dem letzten Start

## Auto-Refresh

Der Container-Status wird automatisch aktualisiert. Der Notification-Checker läuft als Background-Thread und prüft alle 60 Sekunden den Zustand aller Container. Bei Änderungen (z.B. Container gestoppt oder neu gestartet) wird eine Benachrichtigung ausgelöst.

## API-Zugriff

Die Container-Daten sind auch per API abrufbar:

- `GET /api/containers` - Gibt eine JSON-Liste aller Container mit Status, Ports und Image zurück

## Technische Details

- Die Daten werden über den `docker_service.py` abgerufen, der `docker ps --format` als Subprocess ausführt
- Kein Docker-SDK nötig - reine CLI-Integration
- Der Service ist in die Notification-Pipeline integriert und meldet Container-Ausfälle automatisch
