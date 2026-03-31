---
title: "Dependencies"
icon: "diagram-2"
description: "Abhängigkeiten aller Projekte im Überblick - package.json, requirements.txt, Cargo.toml und mehr."
section: "DevOps"
tags: [dependencies, packages, npm, pip, cargo, devops]
order: 2
tips:
  - "Die Dependency-Erkennung nutzt den description_extractor.py, der automatisch alle gängigen Paketmanager-Formate parst."
  - "Achte auf veraltete Pakete - sie können Sicherheitslücken enthalten."
---

## Überblick

Die Dependencies-Seite (`/dependencies`) zeigt die Abhängigkeiten aller Projekte unter `/mnt/projects/`. Du siehst auf einen Blick, welche Pakete in welchen Versionen verwendet werden und wo möglicherweise Updates nötig sind.

## Unterstützte Paketmanager

SessionPilot erkennt Abhängigkeiten aus folgenden Quellen:

- **Node.js** - `package.json` (dependencies, devDependencies)
- **Python** - `requirements.txt`, `pyproject.toml`, `Pipfile`
- **Rust** - `Cargo.toml`
- **PHP** - `composer.json`
- **Go** - `go.mod`

## Funktionen

- **Projekt-übergreifende Ansicht** - Alle Abhängigkeiten aller Projekte in einer Tabelle
- **Versions-Erkennung** - Installierte Version und ggf. verfügbare Updates
- **Veraltete Pakete** - Markierung von Paketen, die nicht mehr aktuell sind
- **Duplikat-Erkennung** - Zeigt, wenn dasselbe Paket in verschiedenen Projekten in unterschiedlichen Versionen verwendet wird

## Technische Details

- Der `description_extractor.py` parst die Paketmanager-Dateien beim Projekt-Scan
- Die Ergebnisse werden im Projekt-Cache zwischengespeichert
- Topic-Erkennung ordnet Pakete automatisch Kategorien zu (z.B. Testing, UI, Database)
