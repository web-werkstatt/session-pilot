---
title: "Projekte"
icon: "folder"
description: "Projekt-Verwaltung, automatische Erkennung und Organisation"
section: "Projekt-Verwaltung"
tags: [projekte, verwaltung, erkennung, tags, gruppen, favoriten]
order: 1
tips:
  - "Projekte werden automatisch aus /mnt/projects/ erkannt - kein manuelles Anlegen nötig."
  - "Nutze Gruppen und Favoriten um bei vielen Projekten den Überblick zu behalten."
---

## Projekte

SessionPilot erkennt und verwaltet alle Projekte automatisch. Das Dashboard scannt das Verzeichnis `/mnt/projects/` und erstellt für jedes Projekt ein Profil mit Typ, Technologien und Aktivitätsdaten.

## Automatische Erkennung

### Projekt-Typen

Beim ersten Scan wird der Projekt-Typ automatisch erkannt:

| Typ | Erkennung |
|---|---|
| **Monorepo** | Enthält apps/, packages/ oder workspaces |
| **Fork** | Git-Remote zeigt auf fremdes Repository |
| **Tool** | CLI-Tool oder Utility-Projekt |
| **Webapp** | Web-Anwendung mit Frontend |
| **Library** | Wiederverwendbare Bibliothek |

### Technologie-Tags

Folgende Technologien werden automatisch erkannt und als Tags angezeigt:

- **Sprachen:** Node.js, Python, Rust, Go, PHP
- **Frameworks:** React, Vue, Angular, Flask, Django, Express und weitere
- **Tools:** Docker, TypeScript, Tailwind CSS

Die Tag-Erkennung erfolgt zentral und berücksichtigt Konfigurationsdateien, Package-Manager und Verzeichnisstruktur.

### project.json

Für jedes Projekt wird beim ersten Scan eine `project.json` erstellt. Diese Datei speichert Metadaten wie Typ, Beschreibung und benutzerdefinierte Einstellungen. Die Datei wird automatisch aktualisiert, kann aber auch manuell bearbeitet werden.

## Sub-Projekte

Monorepos werden mit ihren Sub-Projekten unterstützt. SessionPilot erkennt Unterverzeichnisse in:

- `apps/`
- `packages/`
- `services/`
- `modules/`

Sub-Projekte erscheinen als eigenständige Einträge mit Verweis auf das übergeordnete Projekt.

## Organisation

### Favoriten

Häufig genutzte Projekte können als Favorit markiert werden. Favoriten erscheinen im Dashboard oben und sind schneller erreichbar.

### Gruppen

Projekte lassen sich in frei definierbare Gruppen einteilen, z.B. nach Kunde, Technologie oder Status. Gruppen werden in `groups.json` gespeichert.

### Relationen

Zwischen Projekten können Beziehungen definiert werden (z.B. "hängt ab von", "Fork von", "ergänzt"). Diese Relationen werden in `relations.json` gespeichert und auf der Projekt-Detail-Seite visualisiert.

## Aktivitäts-Heatmap

Das Dashboard zeigt eine Aktivitäts-Heatmap der letzten 30 Tage. Sie visualisiert, an welchen Tagen in welchen Projekten AI-Sessions stattgefunden haben. Dunklere Felder bedeuten mehr Aktivität.
