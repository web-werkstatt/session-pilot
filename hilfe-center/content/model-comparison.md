---
title: "Modell-Vergleich"
icon: "arrow-left-right"
badge: "PRO"
description: "Vergleiche AI-Modelle nach Qualität, Kosten und Effizienz"
section: "Modell-Vergleich"
tags: [modelle, vergleich, qualität, kosten, analyse]
order: 1
tips:
  - "Bewerte Sessions regelmäßig mit ok/needs_fix/reverted - je mehr Bewertungen, desto aussagekräftiger der Vergleich."
  - "Nutze den Stack-Filter um Backend- und Frontend-Qualität getrennt zu analysieren."
---

![Modell-Vergleich](/static/img/model-comparison.png)

## Modell-Vergleich

Die Seite **Modell-Vergleich** (`/model-comparison`) bietet eine datengetriebene Gegenüberstellung aller eingesetzten AI-Modelle. Hier lassen sich Claude Opus, Sonnet, Codex, Gemini und weitere Modelle anhand konkreter Metriken vergleichen.

## Filter

Über die Filter-Leiste lässt sich der Vergleich eingrenzen:

| Filter | Optionen | Beschreibung |
|---|---|---|
| Zeitraum | 30d / 90d / 365d / Alle | Betrachtungszeitraum für die Metriken |
| Projekt | Alle / einzelnes Projekt | Vergleich auf ein Projekt einschränken |
| Stack | Alle / Backend / Frontend | Nach Technologie-Bereich filtern |

## KPI-Karten

Am oberen Seitenrand zeigen vier Kennzahlen die wichtigsten Werte auf einen Blick:

- **Modelle** - Anzahl der aktiven Modelle im gewählten Zeitraum
- **Durchschn. Qualität** - Gemittelte Quality-Score über alle Modelle
- **Bester $/Success** - Modell mit den niedrigsten Kosten pro erfolgreichem Ergebnis
- **Empfehlung** - Das aktuell am besten bewertete Modell

## Vergleichs-Tabelle

Die zentrale Tabelle listet alle Modelle mit folgenden Spalten:

| Spalte | Inhalt |
|---|---|
| Modell | Name des AI-Modells |
| Sessions | Gesamtzahl der Sessions im Zeitraum |
| Rework % | Anteil der Sessions mit Nacharbeit (needs_fix) |
| $/Success | Durchschnittskosten pro erfolgreicher Session |
| Qualität | Qualitäts-Note von A bis F |
| Trend | Sparkline der letzten Wochen |

### Drill-Down

Die Tabelle ist interaktiv:

- **Klick auf Modellname** öffnet die gefilterte Session-Liste für dieses Modell
- **Klick auf Rework %** zeigt nur Sessions mit Status `needs_fix`

## Diagramme

![Modell-Vergleich Charts](/static/img/model-comparison-charts.png)

### Radar-Chart

Vergleicht die Modelle in drei Dimensionen:

- **Qualität** - Quality Score (0-100)
- **Kosten-Effizienz** - Umgekehrtes Verhältnis der Kosten pro Erfolg
- **Geschwindigkeit** - Durchschnittliche Bearbeitungszeit

### Rework-Rate nach Stack

Balkendiagramm das die Nacharbeits-Rate pro Technologie-Stack aufschlüsselt:

- CSS
- JavaScript
- Markup
- Python
- TypeScript

So wird sichtbar, in welchem Bereich ein Modell Stärken oder Schwächen hat.

## Automatische Insights

Unterhalb der Diagramme generiert SessionPilot automatisch Text-Hinweise. Diese fassen auffällige Muster zusammen, z.B.:

- Welches Modell die beste Rework-Rate hat
- Ob ein Modell bei bestimmten Stacks besonders gut oder schlecht abschneidet
- Kosten-Trends im gewählten Zeitraum
