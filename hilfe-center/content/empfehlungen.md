---
title: "Modell-Empfehlungen"
icon: "lightbulb"
badge: "PRO"
description: "Wie SessionPilot das beste Modell für dein Projekt empfiehlt"
section: "Modell-Vergleich"
tags: [empfehlung, modelle, qualität, kosten, api]
order: 3
tips:
  - "Mindestens 5 bewertete Sessions pro Modell sind nötig, damit eine Empfehlung ausgesprochen wird."
  - "Die Empfehlung berücksichtigt sowohl Qualität als auch Kosten - das teuerste Modell ist nicht automatisch das beste."
---

## Modell-Empfehlungen

SessionPilot analysiert die gesammelten Bewertungsdaten und spricht automatisch Empfehlungen aus, welches AI-Modell für ein bestimmtes Projekt oder einen Stack am besten geeignet ist.

## Wie die Empfehlung entsteht

### Mindestanforderung

Ein Modell wird erst in die Empfehlung einbezogen, wenn es mindestens **5 bewertete Sessions** im gewählten Kontext hat. Damit wird verhindert, dass ein Modell mit nur wenigen zufällig guten Ergebnissen empfohlen wird.

### Sortierung

Die Modelle werden in folgender Reihenfolge sortiert:

1. **Quality Score absteigend** - Das Modell mit dem höchsten Score kommt zuerst
2. **Kosten pro Erfolg aufsteigend** - Bei gleichem Score gewinnt das günstigere Modell

Das Modell an Position 1 wird als Empfehlung angezeigt.

## Wo die Empfehlung erscheint

### Projekt-Detail-Seite

Im Header der Projekt-Detail-Seite (`/project/<name>`) wird ein **Empfehlungs-Badge** angezeigt. Dieser zeigt das empfohlene Modell für dieses spezifische Projekt an.

### Modell-Vergleich

Auf der Modell-Vergleich-Seite wird das empfohlene Modell in der KPI-Karte hervorgehoben.

## API

Die Empfehlung ist auch programmatisch abrufbar:

```
GET /api/analytics/model-recommendation?project=X&stack=Y
```

| Parameter | Pflicht | Beschreibung |
|---|---|---|
| `project` | Nein | Empfehlung für ein bestimmtes Projekt |
| `stack` | Nein | Filterung nach Stack (backend/frontend) |

Die Antwort enthält das empfohlene Modell mit Score, Kosten und Begründung.

## Einschränkungen

- Ohne bewertete Sessions gibt es keine Empfehlung
- Neue Modelle brauchen Zeit, um genug Daten zu sammeln
- Die Empfehlung basiert auf historischen Daten und kann sich ändern, wenn neue Bewertungen hinzukommen
