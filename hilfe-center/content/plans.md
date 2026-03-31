---
title: "Plans"
icon: "clipboard-check"
description: "Claude Plans importieren, verwalten und mit Sessions verknüpfen."
section: "DevOps"
tags: [plans, claude, import, sessions, project-linking]
order: 4
tips:
  - "Plans werden automatisch dem richtigen Projekt zugeordnet, wenn sie /mnt/projects/XXX-Pfade im Inhalt enthalten."
  - "Die Verknüpfung mit Sessions erfolgt über Zeitstempel-Korrelation - Plans und Sessions im gleichen Zeitraum werden verbunden."
  - "Nutze den Status (draft/active/completed), um den Fortschritt deiner Plans zu verfolgen."
---

![Plans](/static/img/plans.png)

## Überblick

Die Plans-Seite (`/plans`) importiert und verwaltet Claude Plans aus dem Verzeichnis `~/.claude/plans/`. Du siehst alle Plans mit Projekt-Zuordnung, Status und Verknüpfung zu den zugehörigen Sessions.

## Auto-Import

SessionPilot scannt automatisch `~/.claude/plans/*.md` und importiert neue oder geänderte Plans. Der Import-Prozess:

1. **Scan** - Alle Markdown-Dateien im Plans-Verzeichnis werden gelesen
2. **Projekt-Erkennung** - Pfade wie `/mnt/projects/XXX` im Inhalt werden erkannt und dem Projekt zugeordnet
3. **Session-Verknüpfung** - Über Zeitstempel-Korrelation werden Plans mit passenden Sessions verknüpft
4. **Speicherung** - Import in die PostgreSQL-Datenbank (Tabelle `project_plans`)

## Status-Verwaltung

Jeder Plan hat einen Status, der manuell gesetzt werden kann:

- **Draft** - Plan ist in Arbeit
- **Active** - Plan wird gerade umgesetzt
- **Completed** - Plan ist abgeschlossen

## Angezeigte Informationen

- **Titel** - Aus dem Markdown-Dateinamen oder der ersten Überschrift
- **Projekt** - Automatisch erkanntes Projekt
- **Session-Links** - Verknüpfte Sessions mit Zeitraum
- **Status** - Aktueller Bearbeitungsstand
- **Inhalt** - Volltext des Plans mit Markdown-Rendering

## Technische Details

- Import-Logik in `services/plans_import.py`
- PostgreSQL-Tabelle `project_plans` mit Feldern: id, filename, title, project_name, content, status, session_uuid
- Routen in `routes/plans_routes.py`
- Projekt-Erkennung basiert auf Regex-Matching von `/mnt/projects/`-Pfaden
