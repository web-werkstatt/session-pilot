---
title: "Projekt-Detail"
icon: "file-earmark-text"
description: "Die Projekt-Detail-Seite mit allen Tabs und Funktionen"
section: "Projekt-Verwaltung"
tags: [projekt, detail, tabs, sessions, plans, dokumente, qualität, heatmap]
order: 2
tips:
  - "Über den Export-Button kannst du Projekt-Informationen als HTML, Markdown oder JSON herunterladen."
  - "Der Modell-Empfehlungs-Badge im Header zeigt dir sofort das beste Modell für dieses Projekt."
---

![Projekt Detail](/static/img/projekt-detail.png)

## Projekt-Detail

Die Projekt-Detail-Seite (`/project/<name>`) bietet eine umfassende Ansicht aller Informationen und Analysen zu einem einzelnen Projekt. Die Seite ist in sechs Tabs organisiert.

## Header

Im Seitenkopf werden angezeigt:

- Projektname und Typ-Badge
- Technologie-Tags
- Modell-Empfehlungs-Badge (zeigt das beste AI-Modell für dieses Projekt)
- Export-Button (HTML, Markdown, JSON)

## Tabs

### Übersicht

Der Übersicht-Tab zeigt die wichtigsten Projekt-Informationen:

- Beschreibung (automatisch aus README oder package.json extrahiert)
- Technologie-Tags und erkannter Projekttyp
- Git-Informationen (Branch, letzter Commit, Remote-URL)
- README-Vorschau (gerendertes Markdown)

### Sessions

Alle AI-Coding-Sessions für dieses Projekt. Die Liste ist filterbar und zeigt:

- Datum, Dauer und eingesetztes Modell
- Token-Verbrauch und Kosten
- Outcome-Status (ok, needs_fix, reverted)

### Plans

Aus `~/.claude/plans/` importierte Claude-Plans, die mit diesem Projekt verknüpft sind. Die Verknüpfung erfolgt automatisch anhand von Pfad-Referenzen im Plan-Inhalt und Zeitstempel-Korrelation mit Sessions.

### Dokumente

Integrierter Dokumenten-Browser für die Projektdateien:

- Verzeichnisbaum-Navigation
- Markdown-Dateien direkt im Browser anzeigen und bearbeiten
- Datei-Upload
- Export einzelner Dokumente

### Qualität

Ergebnisse der statischen Code-Analyse mit Semgrep:

- Gefundene Probleme nach Schweregrad
- Betroffene Dateien und Zeilennummern
- Empfehlungen zur Behebung

### AI Heatmap

Per-Datei-Analyse der AI-Aktivität (Sprint 10):

- Welche Dateien wurden am häufigsten von AI bearbeitet
- Aufschlüsselung nach Writes, Edits und Reads
- Risk Radar mit Hotspots
- Wochen-Trend der letzten 8 Wochen

Mehr Details unter [AI Heatmap](heatmap).
