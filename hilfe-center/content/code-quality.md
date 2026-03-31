---
title: "Code Quality"
icon: "shield-check"
description: "Code-Qualität messen und verbessern - Semgrep-basierte Analyse mit Quality Score."
section: "Projekt-Verwaltung"
tags: [quality, semgrep, scanning, warnings, security]
order: 4
tips:
  - "Die Quality-Pipeline kann als auto_coder-Task wiederverwendbar ausgeführt werden."
  - "Die Baseline liegt bei 189 Warnings - neue Änderungen sollten diesen Wert nicht erhöhen."
  - "Semgrep erkennt Sicherheitsprobleme, Code-Smells und Framework-spezifische Anti-Patterns."
---

![Code Quality](/static/img/code-quality.png)

## Überblick

Die Code-Quality-Seite (`/quality`) bietet eine Semgrep-basierte Code-Analyse für alle Projekte. Du siehst Warnings pro Projekt, einen Quality Score und kannst gezielte Scans ausführen.

## Semgrep-Analyse

SessionPilot nutzt Semgrep für die statische Code-Analyse. Erkannt werden:

- **Sicherheitsprobleme** - SQL-Injection, XSS, unsichere Konfigurationen
- **Code-Smells** - Ungenutzte Variablen, duplizierter Code, komplexe Funktionen
- **Framework-Patterns** - React, Vue.js, Angular-spezifische Anti-Patterns
- **Best Practices** - Fehlende Error-Handler, unsichere Defaults

## Quality Score

Der Quality Score wird pro Projekt berechnet und berücksichtigt:

- Anzahl der Warnings nach Schweregrad (ERROR, WARNING, INFO)
- Verhältnis von Warnings zur Codegröße
- Trend gegenüber dem vorherigen Scan

## auto_coder Pipeline

Die Quality-Analyse kann als wiederverwendbare Pipeline über auto_coder ausgeführt werden. Das ermöglicht:

- **Automatisierte Scans** - Bei jedem Push oder nach Zeitplan
- **Baseline-Tracking** - Aktuelle Baseline bei 189 Warnings
- **Regressions-Erkennung** - Warnung wenn neue Warnings eingeführt werden

## Workflow

1. **Scan starten** - Über die Web-Oberfläche oder CLI
2. **Ergebnisse prüfen** - Warnings nach Schweregrad sortiert
3. **Fixes anwenden** - Direkt im Code oder über Semgrep-Autofix
4. **Erneut scannen** - Verifizieren dass Warnings behoben sind

## Technische Details

- Semgrep-Ergebnisse werden als `ergebnisse.json` gespeichert
- Validierter Workflow: Erst Scanner-Rauschen filtern, dann echte Duplikate beheben
- Integration in die auto_coder Quality-Engine für automatisierte Durchläufe
