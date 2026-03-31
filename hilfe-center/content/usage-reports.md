---
title: "Usage Reports"
icon: "bar-chart-line"
description: "Detaillierte Verbrauchsberichte nach Zeitraum - Token-Charts, Kosten-Aufschlüsselung und Modell-Vergleich."
section: "Sessions & Analyse"
tags: [usage, reports, berichte, tokens, kosten, zeitraum, vergleich]
order: 4
tips:
  - "Cache-Read- und Cache-Create-Tokens sind standardmäßig ausgeblendet - klicke auf die Legende im Chart, um sie einzublenden."
  - "Nutze die Wochenansicht für Sprint-Reviews und die Monatsansicht für Abrechnungen."
  - "Benutzerdefinierte Zeiträume eignen sich gut, um den Verbrauch eines bestimmten Sprints oder Features zu analysieren."
---

![Usage Reports](/static/img/usage-reports.png)

## Überblick

Die Usage Reports (`/usage-reports`) bieten detaillierte Verbrauchsberichte für frei wählbare Zeiträume. Hier analysierst du Token-Verbrauch, Kosten und Modell-Nutzung mit flexiblen Zeitraum-Filtern.

## Zeitraum-Ansichten

Die Berichte können in drei Granularitäten dargestellt werden:

| Ansicht | Beschreibung |
|---------|-------------|
| **Täglich** | Verbrauch pro Tag, ideal für kurzfristige Analyse |
| **Wöchentlich** | Aggregiert pro Woche, gut für Sprint-Reviews |
| **Monatlich** | Monatsüberblick, geeignet für Abrechnungen |

## Zeitraum-Presets

Für schnellen Zugriff stehen vordefinierte Zeiträume bereit:

- **Heute** - Nur der aktuelle Tag
- **Letzte 7 Tage** - Die vergangene Woche
- **Letzte 30 Tage** - Der vergangene Monat
- **Diese Woche** - Aktuelle Kalenderwoche
- **Dieser Monat** - Aktueller Kalendermonat
- **Benutzerdefiniert** - Frei wählbarer Zeitraum mit Start- und Enddatum

## Token-Chart

Das Haupt-Chart zeigt den Token-Verbrauch über den gewählten Zeitraum, aufgeteilt in vier Kategorien:

- **Input-Tokens** - Tokens in User-Prompts, Kontext und Tool-Ergebnissen
- **Output-Tokens** - Tokens in AI-Antworten und Tool-Aufrufen
- **Cache Read** - Aus dem Cache gelesene Tokens (standardmäßig ausgeblendet)
- **Cache Create** - In den Cache geschriebene Tokens (standardmäßig ausgeblendet)

Die Cache-Kategorien sind standardmäßig ausgeblendet, können aber über die Chart-Legende eingeblendet werden. Sie sind relevant, um die tatsächliche Token-Effizienz zu beurteilen.

## Kosten-Aufschlüsselung

Eine Tabelle zeigt die Kosten detailliert aufgeschlüsselt:

- Kosten pro Zeiteinheit (Tag/Woche/Monat)
- Kosten pro Token-Kategorie
- Gesamtkosten für den gewählten Zeitraum

## Modell-Vergleich

Innerhalb des gewählten Zeitraums werden die verwendeten Modelle verglichen:

- Token-Verbrauch pro Modell
- Kosten pro Modell
- Anteil am Gesamtverbrauch
- Durchschnittliche Kosten pro Session je Modell

So erkennst du, welches Modell im betrachteten Zeitraum am meisten genutzt wurde und welches das beste Kosten-Nutzen-Verhältnis bietet.
