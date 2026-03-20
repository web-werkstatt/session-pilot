# AI Observability Roadmap

Erweiterung des Project Dashboards um AI-Coding-Analyse-Features.
Aufgeteilt in 4 Sprints, jeweils ca. 1 Session.

## Sprint-Uebersicht

| Sprint | Feature | Abhaengigkeiten | Status |
|--------|---------|-----------------|--------|
| Sprint 1 | AI Timesheets & Nutzungsanalyse | Vorhandene Session-Daten | DONE |
| Sprint 2 | Rework-Tracking fuer AI-Code | Sprint 1 (Timesheet-Daten) | DONE |
| Sprint 3 | Context Effectiveness (CLAUDE.md) | Sprint 1+2 (Metriken) | DONE |
| Sprint 4 | Self-Service Scaffolding | Unabhaengig | DONE |

## Datenbasis

Bereits vorhanden:
- 277+ Sessions aus 5 AI-Tools (Claude, Codex, Gemini, Copilot, Amazon Q)
- Token-Tracking (Input/Output) pro Session
- Duration pro Session
- Projekt-Zuordnung
- Account/Tool-Zuordnung
- Message-History mit Timestamps

## Architektur-Prinzipien

- Neue Features als eigene Flask Blueprints
- SQL-Aggregation in der DB, nicht in Python
- Chart.js fuer Visualisierung (bereits im Projekt)
- Bestehende UI-Patterns wiederverwenden (Dark Mode, Sidebar, Widgets)
- Keine neuen Dependencies wenn vermeidbar
