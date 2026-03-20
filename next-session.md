# Projekt-Dashboard - Naechste Session

## Letzte Aktualisierung: 2026-03-20
## Status: AI Observability Suite komplett (4 Sprints), alle Preise aktuell
## Naechste Aufgabe: Sprint 2/3 UI-Feinschliff, Outcome-Filter, Bulk-Bewertung

## Session 2026-03-20 - AI Observability Suite

### Was wurde erledigt

**Bugfixes & Infrastruktur:**
- Sessions JSON.parse SyntaxError gefixt (HTML statt JSON bei DB-Fehler)
- DB Connection-Pool stabilisiert (thread-safe, 3 init / 10 max)
- claude-session-sync.service gefixt (EnvironmentFile + docker.service Dependency)
- Loading-Spinner auf allen Seiten ergaenzt (sessions, containers, analyse, vorlagen)
- Inline-JS aus 3 Templates extrahiert (session_detail, sessions, vorlagen)

**Auto-Discovery (5 AI-Tools):**
- Claude Code, OpenAI Codex CLI, Google Gemini CLI, GitHub Copilot CLI, Amazon Q
- Automatische Erkennung aller ~/.claude* Verzeichnisse
- Codex JSONL-Parser + Gemini JSON-Parser implementiert
- 277 Sessions importiert (claude, claude1, minimax, account1, codex, gemini)
- Projektnamen bereinigt (~ Home, ~ Gemini Session)

**Sprint 1: AI Timesheets** (/timesheets)
- 5 KPI-Karten (Sessions, AI-Zeit, Tokens, Kosten, Durchschnitt)
- 4 Charts (Tagesbalken, Projekt-Donut, Tool-Vergleich, Modell-Kosten)
- Projekt-Tabelle sortierbar mit Token-Balken
- Zeitraum-Selector (7d bis 1 Jahr) + Account/Projekt-Filter
- Trend-Vergleich zur Vorperiode

**Sprint 2: Rework-Tracking**
- Outcome-Bewertung pro Session (OK / Needs Fix / Reverted / Partial)
- Outcome-Buttons in Session-Detail + Notiz-Feld
- Outcome-Badges in Sessions-Liste (farbig, sortierbar)
- Rework-KPIs (Rate, bewertete Sessions, verschwendete Kosten)
- Outcome-Donut + Wochen-Trend-Chart auf Timesheets
- Bulk-Bewertung API (POST /api/sessions/bulk-outcome)

**Sprint 3: Context Effectiveness**
- context_tracker.py: Scannt 5 Instruktionsdateitypen (CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules, copilot-instructions.md)
- 170 Aenderungen in 25 Projekten erkannt
- Vorher/Nachher-Vergleich (14-Tage-Fenster): Messages, Tokens, Kosten
- Delta-Anzeige mit Farb-Kodierung (gruen=besser, rot=schlechter)
- Summary-Ranking ueber alle Projekte

**Sprint 4: Self-Service Scaffolding** (/scaffold)
- 4-Schritt Wizard (Grundlagen, Template, AI/DevOps, Vorschau)
- 8 Templates (5 builtin: blank, python-app, python-api, node-app, static-site + 3 Vorlagen)
- AI-Instruktionsdateien Generator (CLAUDE.md, AGENTS.md, GEMINI.md)
- Docker-Setup Generator (Dockerfile, docker-compose, .dockerignore)
- Git Init + Initial Commit + optionaler Gitea-Push
- Name-Validierung + Dateibaum-Vorschau

**Kosten-System:**
- Cache-Tokens (read/create) separat getrackt - echte Kosten 87% guenstiger
- Modell-Preise in DB statt hardcoded (model_pricing Tabelle)
- 31 aktuelle Modelle (Claude, OpenAI GPT-5.x, Gemini 3.x, Amazon Nova)
- Admin-UI zum Bearbeiten auf Settings-Seite

**Settings-Seite** (/settings)
- SaaS-Pattern: Sidebar mit 3 Tabs
- Modell-Preise: Inline-Editing, Provider-Filter, Hinzufuegen/Loeschen
- AI Accounts: Auto-Discovery Karten mit Session-Stats
- System: Server-Config, DB-Statistiken

### Git Commits
```
8d88c5a Feature: AI Observability Suite (4 Sprints)
```

---

## Naechste Session

### Offene Punkte Sprint 2
- [ ] Outcome-Filter Dropdown in Sessions-Liste
- [ ] Bulk-Bewertung UI (Checkboxen + Dropdown in Sessions-Liste)

### Offene Punkte Sprint 3
- [ ] Projekt-Detail Integration (Context Effectiveness Widget)

### Moegliche Features
- Projekt-Tags/Labels (flexiblere Kategorisierung)
- Container-Compose-Aktionen (ganzen Stack starten/stoppen)
- Dashboard auf base.html migrieren (index.html nutzt noch eigenes Layout)

### Code-Qualitaet
- Alle Dateien unter den Groessen-Limits
- Pre-Commit Hook greift sauber
- Keine bekannten technischen Schulden
