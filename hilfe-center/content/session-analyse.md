---
title: "Session-Analyse"
icon: "graph-up"
description: "Visuelle Auswertung aller Sessions - KPIs, Kosten-Trends, Outcome-Verteilung und Modell-Vergleich."
section: "Sessions & Analyse"
tags: [analyse, charts, kpi, kosten, outcome, modell, statistik]
order: 2
tips:
  - "Die Erfolgsquote berücksichtigt nur Sessions mit gesetztem Outcome - bewerte regelmäßig deine Sessions für aussagekräftige Statistiken."
  - "Der Kosten-pro-Modell-Chart hilft dir, das kosteneffizienteste Modell für deine Projekte zu identifizieren."
  - "Vergleiche die Erfolgsquote pro Projekt, um zu erkennen, welche Projekte gut mit AI-Unterstützung funktionieren."
---

![Session Analyse](/static/img/session-analyse.png)

## Überblick

Die Analyse-Seite (`/sessions/analysis`) bietet eine visuelle Auswertung aller importierten Sessions. Interaktive Charts und KPI-Karten helfen dir, Trends zu erkennen, Kosten zu überwachen und die Effektivität verschiedener Modelle zu vergleichen.

## KPI-Karten

Am oberen Rand der Seite werden vier zentrale Kennzahlen angezeigt:

| KPI | Beschreibung |
|-----|-------------|
| **Gesamte Sessions** | Anzahl aller importierten Sessions |
| **Gesamtkosten** | Aufsummierte Kosten aller Sessions |
| **Erfolgsquote** | Anteil der Sessions mit Outcome "ok" |
| **Durchschnittliche Kosten/Session** | Mittlere Kosten pro Session |

## Charts

### Sessions pro Monat

Balkendiagramm mit der Anzahl der Sessions pro Monat. Zeigt die Entwicklung der AI-Nutzung über die Zeit und hilft, Nutzungsspitzen zu erkennen.

### Kosten pro Monat

Linien- oder Balkendiagramm der monatlichen Gesamtkosten. Nützlich für die Budgetplanung und um Kostentrends früh zu erkennen.

### Outcome-Verteilung

Kreisdiagramm mit der Verteilung der Session-Outcomes (ok, needs_fix, reverted). Zeigt auf einen Blick, wie hoch der Anteil erfolgreicher Sessions ist.

### Modell-Verteilung

Kreisdiagramm, das zeigt, welche AI-Modelle wie häufig genutzt werden. Hilfreich, um die Nutzungsgewohnheiten zu verstehen.

### Kosten pro Modell

Balkendiagramm mit den aufsummierten Kosten je Modell. Ermöglicht den direkten Kostenvergleich zwischen verschiedenen Modellen.

### Erfolgsquote pro Projekt

Balkendiagramm mit der Erfolgsquote (Anteil "ok"-Outcomes) pro Projekt. Zeigt, bei welchen Projekten AI-Coding besonders gut oder weniger gut funktioniert.

## Interpretation

Die Analyse-Daten sind besonders aussagekräftig, wenn Sessions regelmäßig mit Outcomes bewertet werden. Ohne Outcomes können nur quantitative Metriken (Anzahl, Kosten, Tokens) ausgewertet werden, aber keine Erfolgsquoten.
