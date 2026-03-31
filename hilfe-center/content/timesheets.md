---
title: "AI Timesheets"
icon: "clock"
description: "Sessions gruppiert nach Projekt und Datum - Dauer, Tokens, Kosten und Rework-Tracking."
section: "Sessions & Analyse"
tags: [timesheets, zeit, projekt, kosten, rework, abrechnung]
order: 5
tips:
  - "Die Rework-Spalte zeigt Sessions mit Outcome 'needs_fix' oder 'reverted' - ein hoher Wert deutet auf Verbesserungspotenzial hin."
  - "Nutze den Projekt-Filter, um Timesheets für einen bestimmten Kunden oder ein bestimmtes Projekt zu erstellen."
  - "Die Modell-Aufschlüsselung pro Projekt hilft, die Modellwahl für künftige Projekte zu optimieren."
---

![AI Timesheets](/static/img/timesheets.png)

## Überblick

Die Timesheets-Seite (`/timesheets`) gruppiert alle AI-Coding-Sessions nach Projekt und Datum. Sie bietet eine abrechnungstaugliche Übersicht über Dauer, Token-Verbrauch und Kosten pro Projekt.

## Gruppierung

Sessions werden nach zwei Dimensionen aggregiert:

- **Nach Projekt** - Alle Sessions eines Projekts zusammengefasst
- **Nach Datum** - Innerhalb eines Projekts nach Tagen aufgeschlüsselt

So entsteht eine hierarchische Ansicht: Projekt > Datum > einzelne Sessions.

## Metriken pro Projekt

Für jedes Projekt werden folgende Kennzahlen berechnet:

| Metrik | Beschreibung |
|--------|-------------|
| **Dauer** | Gesamtdauer aller Sessions des Projekts |
| **Tokens** | Aufsummierte Token-Anzahl (Input + Output) |
| **Kosten** | Gesamtkosten aller Sessions |
| **Sessions** | Anzahl der Sessions |

## Modell-Aufschlüsselung

Innerhalb jedes Projekts wird der Verbrauch nach Modell aufgeschlüsselt. So siehst du, welches Modell für welches Projekt verwendet wurde und wie sich die Kosten auf die verschiedenen Modelle verteilen.

## Rework-Tracking

Ein besonderes Feature der Timesheets ist das Rework-Tracking. Sessions, die nachgearbeitet werden mussten (Outcome: `needs_fix`) oder deren Änderungen zurückgesetzt wurden (Outcome: `reverted`), werden separat ausgewiesen.

Das Rework-Tracking zeigt:

- **Anzahl Rework-Sessions** pro Projekt
- **Rework-Anteil** als Prozentsatz aller Sessions
- **Rework-Kosten** für Sessions, die nicht zum gewünschten Ergebnis führten

Ein hoher Rework-Anteil kann auf verschiedene Ursachen hindeuten: unklare Anforderungen, ungeeignetes Modell oder zu komplexe Aufgaben für eine einzelne Session.

## Filter

Die Timesheets lassen sich filtern nach:

- **Zeitraum** - Bestimmten Datumsbereich auswählen
- **Projekt** - Einzelnes Projekt oder alle Projekte
- **Modell** - Nach verwendetem AI-Modell filtern

## Anwendungsfälle

- **Projekt-Abrechnung** - Kosten und Aufwand pro Projekt dokumentieren
- **Sprint-Review** - AI-Nutzung im Sprint zusammenfassen
- **Effizienz-Analyse** - Rework-Quote pro Projekt vergleichen
- **Budget-Kontrolle** - Projekt-Kosten im Zeitverlauf überwachen
- **Modell-Optimierung** - Erkennen, welches Modell pro Projekttyp am effizientesten ist
