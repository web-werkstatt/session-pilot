---
title: "Usage Monitor"
icon: "activity"
description: "Echtzeit-Überwachung des Token-Verbrauchs und der Kosten aus aktiven AI-Sessions."
section: "Sessions & Analyse"
tags: [usage, monitor, echtzeit, tokens, kosten, live]
order: 3
tips:
  - "Der Vergleich mit dem Vortag hilft dir, ungewöhnlich hohen Verbrauch früh zu erkennen."
  - "Behalte die Kosten-Schätzung im Blick, um dein Budget nicht zu überschreiten."
  - "Die Pro-Modell-Aufschlüsselung zeigt dir, welches Modell gerade am meisten Tokens verbraucht."
---

![Usage Monitor](/static/img/usage-monitor.png)

## Überblick

Der Usage Monitor (`/usage-monitor`) zeigt den aktuellen Token-Verbrauch in Echtzeit. Die Daten werden direkt aus aktiven JSONL-Dateien gelesen und bieten einen Live-Blick auf die laufende AI-Nutzung.

## Funktionen

### Echtzeit-Token-Verbrauch

Der Monitor liest aktive JSONL-Dateien und zeigt den aktuellen Verbrauch an. So siehst du jederzeit, wie viele Tokens in laufenden Sessions verbraucht werden.

### Tagesvergleich

Der heutige Verbrauch wird mit dem gestrigen verglichen. Ein Pfeil oder eine prozentuale Änderung zeigt an, ob der aktuelle Tag über oder unter dem Vortag liegt. Das hilft, ungewöhnliche Nutzungsmuster schnell zu erkennen.

### Pro-Modell-Aufschlüsselung

Der Verbrauch wird nach verwendetem AI-Modell aufgeschlüsselt. So siehst du auf einen Blick, welches Modell wie viele Tokens verbraucht:

- **Input-Tokens** - Tokens in User-Prompts und Kontext
- **Output-Tokens** - Tokens in AI-Antworten
- **Gesamtverbrauch** - Summe pro Modell

### Kosten-Schätzung

Basierend auf den aktuellen Token-Zählen und den hinterlegten Modellpreisen wird eine Echtzeit-Kosten-Schätzung angezeigt. Die Berechnung erfolgt über den Cost Service, der die aktuellen Preise pro Modell kennt.

## Anwendungsfälle

- **Budget-Überwachung** - Tageskosten im Blick behalten
- **Anomalie-Erkennung** - Ungewöhnlich hohen Verbrauch früh erkennen
- **Modell-Auswahl** - Sehen, welches Modell aktuell genutzt wird
- **Team-Transparenz** - Aktuelle Nutzung für alle sichtbar machen
