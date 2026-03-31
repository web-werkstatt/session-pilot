---
title: "Datenbank"
icon: "database"
description: "PostgreSQL-Tabellen und JSON-Dateien - das Datenmodell von SessionPilot."
section: "Architektur"
tags: [datenbank, postgresql, json, tabellen, schema]
order: 3
tips:
  - "Der Connection-Pool wird über db_service.py verwaltet - nie direkt psycopg2 verwenden."
  - "JSON-Dateien sind für lokale, schnell änderbare Daten - PostgreSQL für strukturierte, abfragbare Daten."
  - "Die Materialized View mv_model_quality muss nach Datenimport refreshed werden."
---

## Überblick

SessionPilot verwendet zwei Datenspeicher: **PostgreSQL** für strukturierte Daten (Sessions, Messages, Plans) und **JSON-Dateien** für lokale Konfigurationsdaten (Gruppen, Relationen, Favoriten).

## PostgreSQL-Tabellen

### sessions

Zentrale Tabelle für alle importierten AI-Coding-Sessions.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | SERIAL | Primärschlüssel |
| session_uuid | TEXT | Eindeutige Session-ID |
| account | TEXT | AI-Account (Claude, Codex, Gemini) |
| project_name | TEXT | Zugeordnetes Projekt |
| model | TEXT | Verwendetes AI-Modell |
| started_at | TIMESTAMP | Startzeit |
| ended_at | TIMESTAMP | Endzeit |
| duration_ms | INTEGER | Dauer in Millisekunden |
| total_input_tokens | INTEGER | Verbrauchte Input-Tokens |
| total_output_tokens | INTEGER | Generierte Output-Tokens |
| cost_estimate | DECIMAL | Geschätzte Kosten |
| outcome | TEXT | Ergebnis (ok, needs_fix, reverted) |
| outcome_reason | TEXT | Grund für das Ergebnis |
| outcome_severity | TEXT | Schweregrad |
| ai_has_writes | BOOLEAN | Hat die AI Dateien geschrieben? |
| ai_has_tool_calls | BOOLEAN | Hat die AI Tools verwendet? |
| ai_tools_used | TEXT[] | Liste verwendeter Tools |

### messages

Einzelne Nachrichten innerhalb einer Session.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | SERIAL | Primärschlüssel |
| session_id | INTEGER | FK auf sessions |
| type | TEXT | Nachrichtentyp (human, assistant, tool) |
| content | TEXT | Textinhalt |
| content_json | JSONB | Strukturierter Inhalt |
| model | TEXT | Verwendetes Modell |
| input_tokens | INTEGER | Input-Tokens dieser Nachricht |
| output_tokens | INTEGER | Output-Tokens dieser Nachricht |
| timestamp | TIMESTAMP | Zeitstempel |

### ai_file_touches

Aufzeichnung aller Datei-Zugriffe durch die AI pro Session.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | SERIAL | Primärschlüssel |
| session_id | INTEGER | FK auf sessions |
| file_path | TEXT | Betroffene Datei |
| touch_type | TEXT | Art des Zugriffs (read, write, create, delete) |
| tool_name | TEXT | Verwendetes Tool |
| timestamp | TIMESTAMP | Zeitstempel |

### project_plans

Importierte Claude Plans.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | SERIAL | Primärschlüssel |
| filename | TEXT | Dateiname der Plan-Datei |
| title | TEXT | Titel des Plans |
| project_name | TEXT | Zugeordnetes Projekt |
| content | TEXT | Volltext des Plans |
| status | TEXT | Status (draft, active, completed) |
| session_uuid | TEXT | Verknüpfte Session |

### review_threads und session_reviews

Tabellen für das Review-System zur Bewertung von Sessions.

### mv_model_quality (Materialized View)

Aggregierte Modell-Metriken aus Sprint 11. Berechnet Quality Scores, Erfolgsraten und Performance-Daten pro Modell. Muss nach Datenimport mit `REFRESH MATERIALIZED VIEW mv_model_quality` aktualisiert werden.

## JSON-Dateien

Für lokale, schnell änderbare Daten werden JSON-Dateien verwendet:

| Datei | Beschreibung |
|-------|--------------|
| `groups.json` | Projekt-Gruppen und Zuordnungen |
| `relations.json` | Beziehungen zwischen Projekten |
| `ideas.json` | Ideen und Notizen |
| `scheduled_tasks.json` | Geplante Aufgaben |
| `favorites.json` | Projekt-Favoriten |
| `notifications.json` | Aktive Benachrichtigungen |
| `.notification_state.json` | Zustand des Notification-Checkers |
| `.sync_hashes.json` | Hash-Cache für Session-Import |

## Technische Details

- **Connection-Pool** über `services/db_service.py` (psycopg2)
- **Thread-Safety** - JSON-Stores nutzen Locks für konkurrierende Zugriffe
- **Kein ORM** - Direkte SQL-Queries für maximale Kontrolle
- **Secrets** in `.env`-Datei (DB-Passwort, Gitea-Token), geladen via systemd EnvironmentFile
