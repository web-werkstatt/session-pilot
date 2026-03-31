---
title: "Seitenübersicht"
icon: "map"
description: "Alle Seiten und Funktionen von SessionPilot auf einen Blick"
section: "Einstieg"
tags: [navigation, seiten, übersicht, referenz]
order: 3
tips:
  - "Die meisten Seiten sind auch über die Volltextsuche (Ctrl+K) erreichbar."
  - "Projekt-Detail-Seiten haben mehrere Tabs - über URL-Parameter direkt ansteuerbar."
---

## Alle Seiten im Überblick

### Workspace

| Seite | URL | Beschreibung |
|---|---|---|
| Dashboard | `/` | Zentrale Projekt-Übersicht mit Favoriten, Aktivitäts-Heatmap und Schnellzugriff auf alle Projekte. Zeigt Projekt-Typen, Technologie-Tags und letzten Commit. |
| Sessions | `/sessions` | Liste aller AI-Coding-Sessions (Claude Code, Codex, Gemini). Filtern nach Projekt, Modell, Zeitraum und Outcome. Export als JSON, Markdown, HTML oder XLSX. |
| Session-Analyse | `/sessions/analysis` | Visuelle Auswertung: Kosten pro Modell, Outcome-Verteilung (Erfolg/Abbruch/Fehler), Token-Verbrauch im Zeitverlauf, aktivste Projekte. |
| Usage Monitor | `/usage-monitor` | Live-Ansicht des aktuellen Token-Verbrauchs. Zeigt laufende und kürzlich abgeschlossene Sessions mit Kosten in Echtzeit. |
| Usage Reports | `/usage-reports` | Aggregierte Berichte auf Tages-, Wochen- und Monatsbasis. Kosten-Trends, Modell-Verteilung und Projekt-Aufschlüsselung. |
| Timesheets | `/timesheets` | AI-Arbeitszeiterfassung: Wie viel Zeit hat welches AI-Modell an welchem Projekt gearbeitet? Filterbar nach Zeitraum und Projekt. |
| Modell-Vergleich | `/model-comparison` | Qualitätsvergleich verschiedener AI-Modelle anhand von Erfolgsrate, durchschnittlichem Token-Verbrauch, Kosten-Effizienz und Bearbeitungszeit. |

### Projekt-Detail

| Seite | URL | Beschreibung |
|---|---|---|
| Projekt-Detail | `/project/<name>` | Detailansicht eines einzelnen Projekts mit mehreren Tabs: |
| - Tab: Overview | | Projekt-Typ, Beschreibung, Technologie-Tags, Git-Infos, letzte Commits |
| - Tab: Sessions | | Alle AI-Sessions für dieses Projekt, chronologisch sortiert |
| - Tab: Plans | | Importierte Claude Plans mit Status-Verwaltung |
| - Tab: Documents | | Dokumenten-Browser mit Viewer, Editor und Upload |
| - Tab: Quality | | Semgrep-Ergebnisse und Code-Qualitäts-Metriken |
| - Tab: AI Heatmap | | Per-Datei Visualisierung: Welche Dateien wurden wie oft von KI bearbeitet? Risk-Radar für häufig geänderte Dateien. |

### DevOps

| Seite | URL | Beschreibung |
|---|---|---|
| Container | `/containers` | Live-Status aller Docker-Container. Zeigt Name, Image, Status, Ports und Health-Checks. Benachrichtigung bei Status-Änderungen. |
| Dependencies | `/dependencies` | Übersicht der Abhängigkeiten aller Projekte (npm, pip, composer). Erkennt veraltete Pakete und Sicherheitsprobleme. |
| Scheduled Tasks | `/scheduled-tasks` | Verwaltung geplanter Aufgaben. Unterstützt Claude Code RemoteTrigger mit Cron-Ausdrücken für automatisierte Checks. |
| Plans | `/plans` | Import und Verwaltung von Claude Plans aus `~/.claude/plans/`. Zeigt Plan-Inhalt, verknüpfte Projekte und Status. |
| Quality | `/quality` | Projektübergreifende Code-Qualitäts-Analyse via Semgrep. Zeigt Findings nach Schweregrad, Kategorie und Projekt. |

### Content & Einstellungen

| Seite | URL | Beschreibung |
|---|---|---|
| Scaffold | `/scaffold` | Neues Projekt erstellen mit vorkonfigurierten Templates. Legt Verzeichnisstruktur, Git-Repository und Basis-Dateien an. |
| Vorlagen | `/vorlagen` | Sammlung von Projekt-Templates für verschiedene Tech-Stacks (Flask, Node.js, etc.). |
| News | `/news` | Neuigkeiten und Updates rund um SessionPilot und die verwalteten Projekte. |
| Einstellungen | `/settings` | Globale Konfiguration: Gitea-Integration, Benachrichtigungen, Darstellung und Cache-Verwaltung. |

### Weitere Funktionen

| Funktion | Zugriff | Beschreibung |
|---|---|---|
| Volltextsuche | `Ctrl+K` oder Suchfeld | Durchsucht alle Projekte via ripgrep. Filtert nach Dateityp und zeigt Ergebnisse mit Kontext. |
| Projekt-Export | Projekt-Detail | Export von Projekt-Metadaten und Session-Daten in verschiedenen Formaten. |
| Benachrichtigungen | Glocken-Icon | Automatische Benachrichtigungen bei Container-Änderungen, neuen Projekten und Sync-Events. |
| Projekt-Beziehungen | Projekt-Detail | Verknüpfungen zwischen Projekten (Fork, Abhängigkeit, Referenz) visualisieren. |
| Gruppen | Dashboard | Projekte in Gruppen organisieren für bessere Übersicht. |
| Ideen | Dashboard | Schnellnotizen und Ideen zu Projekten erfassen. |
