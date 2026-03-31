---
title: "Was ist SessionPilot?"
icon: "info-circle"
description: "Überblick über SessionPilot - das Self-Hosted Dashboard für AI-Coding-Sessions"
section: "Einstieg"
tags: [einführung, überblick, features]
order: 1
tips:
  - "SessionPilot läuft lokal auf deinem Server - keine Cloud, keine externen Abhängigkeiten."
  - "Alle Daten bleiben unter deiner Kontrolle in /mnt/projects/ und PostgreSQL."
---

![SessionPilot Dashboard](/static/img/dashboard.png)

## Was ist SessionPilot?

SessionPilot ist ein Self-Hosted Web-Dashboard zur Überwachung und Analyse von AI-Coding-Sessions. Es wurde speziell für Entwickler gebaut, die mit KI-Assistenten wie **Claude Code**, **Codex CLI** oder **Gemini CLI** arbeiten und den Überblick über ihre Projekte, Kosten und Produktivität behalten wollen.

Das Dashboard läuft als Flask-Anwendung auf Port 5055 und scannt automatisch alle Projekte unter `/mnt/projects/`. Session-Daten werden aus JSONL-Dateien importiert und in PostgreSQL gespeichert.

## Kernfunktionen

### Session-Tracking
Automatischer Import und Analyse aller AI-Coding-Sessions. SessionPilot erkennt Claude Code, Codex CLI und Gemini CLI Sessions, extrahiert Konversationen, Tool-Nutzung und Ergebnisse.

### Kosten-Analyse
Detaillierte Aufschlüsselung der Token-Kosten pro Modell, Projekt und Zeitraum. Tages-, Wochen- und Monatsreports zeigen, wo das Budget hinfliegt.

### Modell-Vergleich
Vergleiche die Qualität und Effizienz verschiedener AI-Modelle anhand von Metriken wie Erfolgsrate, Token-Verbrauch und Bearbeitungszeit.

### Projekt-Verwaltung
Zentrale Übersicht aller Projekte mit automatischer Typ-Erkennung (Monorepo, Tool, Fork etc.), Technologie-Tags und Aktivitäts-Heatmaps.

### Container-Monitoring
Live-Status aller Docker-Container mit Health-Checks und Benachrichtigungen bei Änderungen.

### Code-Qualität
Integration mit Semgrep für statische Code-Analyse. Pro-Datei AI-Heatmaps zeigen, welche Dateien am häufigsten von KI bearbeitet werden.

## Für wen ist SessionPilot?

SessionPilot richtet sich an **Entwickler und Teams**, die:

- Regelmäßig mit AI-Coding-Assistenten arbeiten
- Ihre AI-Kosten im Blick behalten wollen
- Mehrere Projekte parallel verwalten
- Nachvollziehen möchten, welche Änderungen durch KI entstanden sind
- Self-Hosting bevorzugen und volle Kontrolle über ihre Daten behalten wollen

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Backend | Python / Flask |
| Datenbank | PostgreSQL |
| Frontend | Vanilla JS, Chart.js, Tailwind CSS |
| Session-Import | JSONL-Parser mit Hash-basiertem Cache |
| Suche | ripgrep (rg) für Volltextsuche |
| Deployment | systemd-Service oder Docker |
| Benachrichtigungen | Background-Thread (60s Intervall) |
