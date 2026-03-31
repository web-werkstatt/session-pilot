---
title: "Quality Score"
icon: "star"
badge: "PRO"
description: "Wie der Qualitäts-Score berechnet wird und was die Noten bedeuten"
section: "Modell-Vergleich"
tags: [qualität, score, bewertung, modelle, formel]
order: 2
tips:
  - "Ein Modell braucht mindestens einige bewertete Sessions, damit der Score aussagekräftig ist."
  - "Revertierte Sessions wiegen dreimal schwerer als Nacharbeit - vermeide Reverts wo möglich."
---

## Quality Score

Der Quality Score ist die zentrale Kennzahl für die Bewertung von AI-Modellen in SessionPilot. Er fasst Erfolgsrate, Nacharbeit und Schweregrad in einer einzigen Zahl zusammen.

## Berechnung

Die Formel lautet:

```
Score = 100 - (rework_rate * 0.5) - (reverted_rate * 1.5) - (incomplete_rate * 0.3)
```

| Faktor | Gewicht | Beschreibung |
|---|---|---|
| `rework_rate` | 0.5 | Anteil Sessions mit Outcome `needs_fix` |
| `reverted_rate` | 1.5 | Anteil Sessions die zurückgesetzt wurden |
| `incomplete_rate` | 0.3 | Anteil unvollständiger Sessions |

### Bonus

Modelle mit mehr als 20 bewerteten Sessions erhalten einen Bonus von **+5 Punkten**. Damit werden Modelle belohnt, für die eine breite Datenbasis vorliegt.

### Severity-Abzug

Pro durchschnittlichem Schweregrad-Punkt werden **-2 Punkte** abgezogen. Ein Modell, das regelmäßig schwerwiegende Fehler produziert, wird dadurch deutlich abgestraft.

## Noten-System

Der numerische Score wird in Buchstaben-Noten übersetzt:

| Note | Score-Bereich | Bedeutung |
|---|---|---|
| **A** | 90 und höher | Hervorragend - minimale Nacharbeit |
| **B** | 75 bis 89 | Gut - gelegentliche Korrekturen |
| **C** | 60 bis 74 | Befriedigend - regelmäßige Nacharbeit nötig |
| **D** | 40 bis 59 | Mangelhaft - häufige Probleme |
| **F** | unter 40 | Ungenügend - mehr Fehler als Nutzen |

## Voraussetzungen

Damit der Quality Score berechnet werden kann, müssen Sessions bewertet sein. Relevante Outcomes sind:

- **ok** - Session war erfolgreich
- **needs_fix** - Nacharbeit erforderlich
- **reverted** - Änderungen wurden zurückgesetzt

Unbewertete Sessions fließen nicht in den Score ein.

## Filterung

Der Score kann eingegrenzt werden nach:

- **Projekt** - Score für ein bestimmtes Projekt
- **Stack** - Score getrennt nach Backend/Frontend
- **Zeitraum** - Score für die letzten 30, 90 oder 365 Tage
