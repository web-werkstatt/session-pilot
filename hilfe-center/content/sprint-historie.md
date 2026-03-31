---
title: "Sprint-Historie"
icon: "journal-text"
description: "Alle Sprints im Überblick - von AI Timesheets bis Modell-Vergleich."
section: "Architektur"
tags: [sprints, historie, changelog, entwicklung, features]
order: 4
tips:
  - "Jeder Sprint hat ein eigenes Gitea-Issue mit detaillierter Beschreibung und Commit-Referenzen."
  - "Die Sprint-Nummern entsprechen den Issue-Nummern auf Gitea."
  - "Neue Features werden immer in einem Sprint-Kontext entwickelt und dokumentiert."
---

## Überblick

SessionPilot wird in Sprints entwickelt. Jeder Sprint fokussiert sich auf ein Thema und wird als Gitea-Issue getrackt. Hier ist die vollständige Historie aller bisherigen Sprints.

## Sprint-Tabelle

| Sprint | Thema | Highlights |
|--------|-------|------------|
| 1 | AI Timesheets | Zeiterfassung pro Projekt - automatische Berechnung von Arbeitszeit und Kosten aus Session-Daten |
| 2 | Rework Tracking | Outcome-Bewertung (ok, needs_fix, reverted) - erkennt ob AI-Arbeit nachgebessert werden musste |
| 3 | Context Effectiveness | Session-Analyse Charts - Visualisierung von Token-Verbrauch und Effizienz |
| 4 | Scaffolding | Neues Projekt erstellen - Projekt-Templates und Initialisierung direkt aus dem Dashboard |
| 5 | Scanner | Verbesserte Projekt-Erkennung - Monorepo-Support, Sub-Projekte, bessere Typ-Erkennung |
| 6 | System Cleanup | Duplikate entfernen, Refactoring - Code-Qualität und technische Schulden abbauen |
| 7 | UI Integration | Frontend-Verbesserungen - Design Tokens, Modal-System, einheitliche UX |
| 8 | Automation | auto_coder Pipeline, Quality Checks - automatisierte Code-Analyse und Semgrep-Integration |
| 9 | Fehler-Kategorien | outcome_reason, AI-Scope-Filter, Tool-Erkennung - detaillierte Klassifizierung von Session-Ergebnissen |
| 10 | File Heatmap | Per-File AI-Touches, Risk Radar - zeigt welche Dateien am häufigsten von der AI bearbeitet werden |
| 11 | Modell-Vergleich | Quality Score, Stack-Analyse, Empfehlungs-Engine - welches AI-Modell für welchen Einsatzzweck am besten geeignet ist |

## Sprint-Details

### Sprint 1-3: Grundlagen

Die ersten drei Sprints legten das Fundament: Session-Import, Kosten-Tracking und erste Analysen. Hier entstanden die Kern-Tabellen `sessions` und `messages` sowie der Hash-basierte Import-Cache.

### Sprint 4-6: Infrastruktur

Projekt-Scaffolding, verbesserter Scanner und ein grosses Cleanup-Sprint. Der `project_detector.py` wurde zur zentralen Instanz für Typ-Erkennung und Tags.

### Sprint 7-8: Qualität

Frontend-Vereinheitlichung mit Design Tokens und dem Modal-System. Die auto_coder Pipeline ermöglicht automatisierte Quality-Checks mit Semgrep.

### Sprint 9-11: Intelligence

Die jüngsten Sprints bringen tiefere Analyse-Fähigkeiten: Fehler-Kategorien mit outcome_reason, File-Heatmaps die zeigen wo die AI am meisten arbeitet, und der Modell-Vergleich mit Empfehlungs-Engine.
