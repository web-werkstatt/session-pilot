---
title: "AI Governance"
icon: "shield"
description: "Projekt-Policies verwalten, Regel-Vorschläge generieren und Feedback-Loops analysieren."
section: "Projekt-Verwaltung"
tags: [governance, policy, sandbox, controlled, critical, rules, compliance, feedback]
order: 5
badge: "NEW"
tips:
  - "Alle Projekte starten als 'Sandbox' - bestehende Workflows bleiben unverändert."
  - "Policies sind informativ, nicht blockierend. Ziel ist Awareness, nicht Enforcement."
  - "Regel-Vorschläge basieren auf den häufigsten Fehlergrund-Kategorien der letzten 90 Tage."
  - "Exportierte Snippets können direkt in CLAUDE.md oder AGENTS.md eingefügt werden."
related: [code-quality, sessions, projekt-detail, quality-score]
---

## Überblick

Die AI-Governance-Seite (`/governance`) ermöglicht es, **Projekt-Policies** für den Umgang mit AI-Assistenten festzulegen. Jedes Projekt kann eine von drei Stufen erhalten, die bestimmen, wie frei AI-Tools arbeiten dürfen.

## Policy-Stufen

SessionPilot verwendet ein dreistufiges Policy-System:

| Level | Name | AI darf schreiben | Review erforderlich | AI darf deployen |
|-------|------|-------------------|---------------------|------------------|
| 1 | **Sandbox** | Ja | Nein | Ja |
| 2 | **Controlled** | Ja | Ja | Nein |
| 3 | **Critical** | Nein | Ja | Nein |

### Sandbox (Level 1)

Für Experimente, Prototypen und persönliche Projekte. AI-Assistenten können frei schreiben, refactoren und deployen. Dies ist der **Default für alle Projekte**.

### Controlled (Level 2)

Für produktive Projekte. AI darf Code schreiben, aber ein Review vor dem Merge wird empfohlen. Keine Deployments durch AI.

### Critical (Level 3)

Für produktionskritische und Compliance-relevante Projekte. AI sollte nur reviewen und planen, nicht eigenständig schreiben. Kein Schreiben und kein Deployment ohne Freigabe.

## Governance-Übersicht

Die Hauptseite zeigt alle Projekte in einer Tabelle mit:

- **Policy-Badge** - Farbcodiert: Grün (Sandbox), Orange (Controlled), Rot (Critical)
- **Rework-Rate** - Prozentsatz der Sessions mit `needs_fix` oder `reverted` Outcome
- **Angewandte Regeln** - Anzahl automatisch übernommener Regeln
- **Letzte Aktualisierung** - Wann die Policy zuletzt geändert wurde

Über den **Edit**-Button kann die Policy direkt geändert werden.

## Policy ändern

1. In der Governance-Übersicht auf **Edit** klicken
2. Im Modal die gewünschte Stufe wählen (Sandbox / Controlled / Critical)
3. Optional Notizen hinzufügen (z.B. Grund für die Einstufung)
4. **Save** klicken

Die Restrictions (Write, Review, Deploy) werden automatisch aus dem Level abgeleitet.

## Regel-Vorschläge

Der Tab **Rule Suggestions** generiert automatisch Regeln aus den häufigsten Fehlerursachen:

1. **Projekt auswählen** und Zeitraum festlegen (30/90/180 Tage)
2. SessionPilot analysiert die `outcome_reason`-Daten der Sessions
3. Die Top-Fehlerursachen werden mit passenden Regel-Templates verknüpft
4. Jeder Vorschlag zeigt:
   - **Fehlergrund** und Häufigkeit
   - **Konfidenz** (high/medium/low basierend auf Anzahl)
   - **CLAUDE.md-Snippet** das direkt übernommen werden kann

### Verfügbare Regel-Kategorien

| Kategorie | Beispiel-Regel |
|-----------|---------------|
| missing_tests | "IMMER Tests schreiben für neue Funktionen und Bugfixes." |
| logic_error | "Edge Cases (null, empty, boundary) explizit prüfen." |
| incomplete | "Keine TODO/FIXME hinterlassen. Aufgabe vollständig erledigen." |
| wrong_approach | "VOR Implementierung: bestehende Patterns und Architektur studieren." |
| broke_existing | "VOR Änderung: bestehende Funktionalität verifizieren. Keine Regressionen." |
| wrong_scope | "NUR die angeforderten Änderungen umsetzen. Kein Scope Creep." |

### Regel übernehmen

Klicke auf **Apply to project.json**, um eine Regel in die `ai_policy.rules_applied` des Projekts zu speichern. Die Regel wird mit Zeitstempel gespeichert, sodass ihre Wirkung später gemessen werden kann.

## Feedback-Loop

Der Tab **Feedback Loop** zeigt die häufigsten Fehlerursachen **gruppiert nach Policy-Level**:

- **Critical-Projekte** - Welche Fehler treten in kritischen Projekten auf?
- **Controlled-Projekte** - Gibt es systematische Muster?
- **Sandbox-Projekte** - Wo sind die größten Baustellen?

Diese Ansicht macht den Zusammenhang zwischen Policy-Level und Fehlerarten sichtbar und hilft bei der Entscheidung, ob Policies angepasst werden sollten.

## Export-Snippets

Der Tab **Export Snippets** generiert fertige Textblöcke zum Kopieren:

### CLAUDE.md Snippet

Enthält Policy-Zusammenfassung und angewandte Regeln. Kann direkt in die `CLAUDE.md` eines Projekts eingefügt werden.

### AGENTS.md Snippet

Enthält Restrictions im Format für AI-Agenten. Nützlich für Multi-Agent-Setups.

### Pre-Commit Hook

Ein optionales Shell-Script für Warnungen bei Commits in restricted Projekten.

Alle Snippets können per **Copy**-Button in die Zwischenablage kopiert werden.

## Wirkungs-Tracking

Über das Chart-Icon in der Governance-Tabelle kann für jedes Projekt die **Wirksamkeit angewandter Regeln** geprüft werden:

- **Vorher** - Fehlerrate 30 Tage vor Regel-Einführung
- **Nachher** - Fehlerrate seit Regel-Einführung
- **Bewertung:**
  - ✅ **wirksam** - Fehlerrate sank um ≥ 10 Prozentpunkte
  - ⚠️ **unklar** - Fehlerrate sank um < 10pp oder zu wenig Daten
  - ❌ **unwirksam** - Fehlerrate stieg oder blieb gleich

## Governance im Projekt-Detail

Jedes Projekt hat einen eigenen **Governance-Tab** in der Projekt-Detailansicht (`/project/<name>`). Dort werden angezeigt:

- Aktuelles Policy-Level mit Restrictions
- Workflow-Einstellungen (Sprints, Session-Review, Governance-Mode)
- Liste angewandter Regeln mit Zeitstempel

## Dashboard-Widget

Auf dem Haupt-Dashboard (Widgets-Tab) zeigt ein kompaktes Governance-Widget:

- Gesamtzahl der Projekte mit Policy
- Aufteilung nach Sandbox / Controlled / Critical
- Warnung bei unreviewed Sessions in Critical-Projekten

## API-Referenz

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/governance/overview` | GET | Alle Projekte mit Policy und Rework-Rate |
| `/api/projects/<name>/policy` | GET | Policy eines Projekts |
| `/api/projects/<name>/policy` | PUT | Policy aktualisieren |
| `/api/governance/rules/<project>` | GET | Regel-Vorschläge |
| `/api/governance/rules/<project>/apply` | POST | Regel übernehmen |
| `/api/governance/effectiveness/<project>` | GET | Wirkungs-Tracking |
| `/api/governance/feedback-loop` | GET | Feedback-Loop-Analyse |
| `/api/governance/snippets/<project>` | GET | Export-Snippets |

## Technische Details

- Policies werden in `project.json` unter `ai_policy` gespeichert (kein eigenes DB-Schema)
- Default-Policy ist Sandbox (Level 1) - kein Breaking Change für bestehende Projekte
- Regel-Templates sind in `services/rule_generator.py` definiert (17 Kategorien)
- Policies sind **informativ, nicht blockierend** - keine harten Blocker via Tooling
- Rework-Rate wird aus Sessions der letzten 90 Tage berechnet
