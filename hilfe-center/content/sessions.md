---
title: "Claude Sessions"
icon: "robot"
description: "Alle importierten AI-Coding-Sessions auf einen Blick - Import, Filter, Export und Detail-Ansicht."
section: "Sessions & Analyse"
tags: [sessions, import, claude, codex, gemini, filter, export]
order: 1
tips:
  - "Der Auto-Sync lauft maximal einmal pro Stunde - beim Öffnen der Sessions-Seite wird automatisch geprüft, ob neue Daten vorliegen."
  - "Unveränderte JSONL-Dateien werden dank Hash-Cache übersprungen und verursachen keine Datenbank-Zugriffe."
  - "Mit dem Export kannst du Sessions als XLSX für Abrechnungen oder als Markdown für Dokumentation speichern."
---

![Claude Sessions](/static/img/sessions.png)

## Überblick

Die Sessions-Seite (`/sessions`) zeigt alle importierten AI-Coding-Sessions in einer übersichtlichen Tabelle. Hier siehst du auf einen Blick, wann welche Session mit welchem Modell stattfand, wie viele Tokens verbraucht wurden und was sie gekostet hat.

## Auto-Import

SessionPilot importiert Sessions automatisch aus mehreren Quellen:

- **Claude Code** - JSONL-Dateien aus `~/.claude/projects/`
- **Codex CLI** - Sessions aus `~/.codex/sessions/`
- **Gemini CLI** - JSON-Dateien aus dem Gemini-Verzeichnis

Der Import nutzt einen **Hash-basierten Cache** (`.sync_hashes.json`): Nur tatsächlich veränderte Dateien werden verarbeitet. Bei unveränderten Dateien entstehen null Datenbank-Zugriffe und der Sync dauert unter einer Sekunde. Der automatische Sync wird beim Öffnen der Sessions-Seite ausgelöst, maximal einmal pro Stunde.

## Filter

Die Sessions-Tabelle bietet umfangreiche Filtermöglichkeiten:

| Filter | Beschreibung |
|--------|-------------|
| **Projekt** | Sessions eines bestimmten Projekts anzeigen |
| **Account** | Nach AI-Assistenten-Account filtern |
| **Modell** | Bestimmtes AI-Modell auswählen (z.B. Opus, Sonnet) |
| **Zeitraum** | Sessions eines bestimmten Zeitraums anzeigen |
| **Outcome** | Nach Ergebnis filtern (ok, needs_fix, reverted) |

## Tabellen-Spalten

Jede Session wird mit folgenden Informationen dargestellt:

- **Datum** - Zeitpunkt der Session
- **Projekt** - Zugeordnetes Projekt
- **Modell** - Verwendetes AI-Modell
- **Tokens** - Verbrauchte Tokens (Input + Output)
- **Kosten** - Berechnete Kosten basierend auf dem Modell
- **Outcome** - Ergebnis-Bewertung der Session

## Session-Detail

Ein Klick auf eine Tabellenzeile öffnet die Detail-Ansicht der Session. Dort werden alle Nachrichten (User-Prompts und AI-Antworten) chronologisch dargestellt. So kannst du den gesamten Verlauf einer Coding-Session nachvollziehen.

## Outcomes

Sessions können manuell mit einem Outcome bewertet werden:

- **ok** - Session war erfolgreich, Code funktioniert
- **needs_fix** - Ergebnis erfordert Nacharbeit
- **reverted** - Änderungen wurden zurückgesetzt

Diese Bewertungen fließen in die Analyse-Seite ein und helfen, die Erfolgsquote pro Projekt und Modell zu ermitteln.

## Export

Sessions lassen sich in verschiedenen Formaten exportieren:

- **JSON** - Strukturierte Daten für Weiterverarbeitung
- **Markdown** - Lesbare Dokumentation
- **HTML** - Formatierte Ansicht für den Browser
- **XLSX** - Excel-Tabelle für Abrechnungen und Reports
- **TXT** - Einfacher Text für schnelle Referenz
