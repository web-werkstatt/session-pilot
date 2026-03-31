---
title: "API-Referenz"
icon: "braces"
description: "Alle API-Endpoints von SessionPilot - Daten, Sessions, Analytics, Projekte und mehr."
section: "Architektur"
tags: [api, endpoints, rest, json, referenz]
order: 2
tips:
  - "Alle API-Aufrufe geben JSON zurück. Im Frontend immer api.js verwenden statt rohes fetch()."
  - "Der @api_route Decorator übernimmt das Error-Handling - bei Fehlern kommt automatisch ein JSON-Error-Objekt."
  - "Für Downloads api.request(url, {raw: true}) verwenden, um die Raw-Response zu erhalten."
---

## Überblick

SessionPilot bietet eine REST-API für alle Funktionen. Alle Endpoints geben JSON zurück und nutzen den `@api_route` Decorator für einheitliches Error-Handling.

## Daten

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/data` | Haupt-Daten-Aggregation (alle Projekte) |
| GET | `/api/containers` | Docker-Container-Status |

## Sessions

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/sessions` | Alle Sessions mit Filtern |
| POST | `/api/sessions/sync` | Session-Sync auslösen |

## Analytics

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/analytics/file-heatmap/<project>` | Per-File AI-Touch-Heatmap |
| GET | `/api/analytics/risk-radar/<project>` | Risk-Radar für Dateien |
| GET | `/api/analytics/model-comparison` | Modell-Vergleich (Quality Score) |
| GET | `/api/analytics/model-by-stack` | Modell-Performance nach Tech-Stack |
| GET | `/api/analytics/model-trend` | Modell-Trend über Zeit |
| GET | `/api/analytics/model-recommendation` | AI-Modell-Empfehlung |

## Projekte

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/info?name=X` | Projekt-Informationen |
| GET | `/api/project/<name>/export` | Projekt-Export |

## Suche

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/search?q=X` | Volltextsuche über alle Projekte (via ripgrep) |

## Widgets

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/widgets/activity` | Aktivitäts-Widget (Heatmap, Charts) |
| GET | `/api/widgets/overview` | Dashboard-Übersicht-Widget |

## Einstellungen

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/settings` | Aktuelle Einstellungen abrufen |
| POST | `/api/settings` | Einstellungen speichern |

## Usage Reports

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/usage-reports/data?period=daily&preset=30days` | Nutzungsdaten mit Zeitraum-Filter |

## Error-Handling

Alle API-Endpoints nutzen den `@api_route` Decorator aus `routes/api_utils.py`. Bei Fehlern wird automatisch ein JSON-Objekt zurückgegeben:

```json
{
  "error": "Fehlerbeschreibung",
  "status": 500
}
```

Für Endpoints mit speziellen Fehler-Responses (z.B. Fallback-Daten) wird weiterhin manuelles try/except verwendet.

## Frontend-Integration

Im Frontend werden API-Aufrufe über den zentralen Fetch-Wrapper `api.js` gemacht:

```javascript
// GET-Request
const data = await api.get('/api/sessions');

// POST-Request
const result = await api.post('/api/sessions/sync', { force: true });

// Download (Raw-Response)
const response = await api.request('/api/project/X/export', { raw: true });
```
