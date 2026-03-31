---
title: "AI Heatmap"
icon: "fire"
badge: "PRO"
description: "Per-Datei AI-Aktivitätsanalyse mit Risk Radar und Trend-Charts"
section: "Projekt-Verwaltung"
tags: [heatmap, dateien, risiko, trend, analyse, hotspots]
order: 3
tips:
  - "Dateien mit vielen Writes und wenig Reads deuten auf häufige Änderungen ohne Review hin - ein potenzielles Risiko."
  - "Der Risk Radar zeigt die kritischsten Dateien zuerst - beginne dort mit Code-Reviews."
---

## AI Heatmap

Die AI Heatmap (Sprint 10) analysiert auf Datei-Ebene, wie intensiv AI-Assistenten mit einzelnen Dateien eines Projekts interagiert haben. Sie ist über den Tab **AI Heatmap** auf der Projekt-Detail-Seite erreichbar.

## Datenquelle

Die Heatmap-Daten stammen aus der Tabelle `ai_file_touches`. Bei jedem Session-Import werden die Tool-Nutzungen (`tool_use`) analysiert und pro Datei die Zugriffe extrahiert:

| Zugriffs-Typ | Beschreibung |
|---|---|
| **Write** | Datei wurde neu erstellt oder komplett überschrieben |
| **Edit** | Bestehende Datei wurde teilweise geändert |
| **Read** | Datei wurde gelesen (z.B. zur Analyse) |

## Heatmap-Tabelle

Die zentrale Tabelle zeigt alle berührten Dateien mit folgenden Spalten:

- **Datei** - Relativer Pfad innerhalb des Projekts
- **Gesamt** - Gesamtzahl aller Zugriffe
- **Writes** - Anzahl der Schreibzugriffe
- **Edits** - Anzahl der Bearbeitungen
- **Reads** - Anzahl der Lesezugriffe
- **Sessions** - In wie vielen Sessions die Datei berührt wurde

Die Tabelle ist nach jeder Spalte sortierbar. Standardmäßig wird nach Gesamtzahl absteigend sortiert.

### Filter

Über den Typ-Filter lassen sich gezielt bestimmte Zugriffs-Arten anzeigen, z.B. nur Writes oder nur Edits.

## Risk Radar

Der Risk Radar hebt die kritischsten Dateien hervor:

### Top 5 Hotspots

Dateien mit den meisten Writes und Edits. Diese Dateien werden am häufigsten von AI verändert und sollten priorisiert reviewed werden.

### Top 5 Fehler-Dateien

Dateien, die in Sessions mit dem Outcome `needs_fix` oder `reverted` am häufigsten berührt wurden. Diese Dateien sind potenzielle Problemquellen.

## Wochen-Trend

Ein Liniendiagramm zeigt die AI-Aktivität der letzten **8 Wochen**. Der Trend macht sichtbar:

- Ob die AI-Nutzung zu- oder abnimmt
- In welchen Wochen besonders viele Änderungen stattfanden
- Ob es Spitzen gibt, die auf größere Refactorings hindeuten

## Typische Anwendungsfälle

- **Code-Review-Priorisierung** - Beginne Reviews bei Dateien mit den meisten Writes
- **Risiko-Erkennung** - Dateien mit hoher Änderungsfrequenz und Fehlern identifizieren
- **Architektur-Analyse** - Erkennen, welche Bereiche des Codes am meisten AI-Unterstützung benötigen
- **Team-Kommunikation** - Hotspots als Diskussionsgrundlage für Code-Ownership nutzen
