# Sprint 3: Context Effectiveness (CLAUDE.md Tracking)

**Ziel:** Messen, ob Aenderungen an Projekt-Instruktionen (CLAUDE.md, AGENTS.md, GEMINI.md)
die AI-Effizienz verbessern. Vorher/Nachher-Vergleiche automatisch erstellen.
**Abhaengigkeit:** Sprint 1 (Metriken), Sprint 2 (Outcome-Daten)
**Geschaetzter Umfang:** 1 Session

---

## Aufgaben

### 3.1 Service: Context-Change-Detection (`services/context_tracker.py`)

**Erkennung von Instruktions-Dateien:**
- `CLAUDE.md` (Claude Code)
- `AGENTS.md` (OpenAI Codex)
- `GEMINI.md` (Google Gemini CLI)
- `.cursorrules` (Cursor)
- `.github/copilot-instructions.md` (Copilot)

**Change-Tracking:**
- Bei jedem Sync: Pruefen ob Instruktions-Dateien sich geaendert haben
- Git-basiert: `git log --follow -p -- CLAUDE.md` fuer Aenderungshistorie
- Speichern: Zeitpunkt, Datei, Projekt, Diff-Groesse (Zeilen +/-)

**DB-Schema:**
```sql
CREATE TABLE IF NOT EXISTS context_changes (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    commit_hash VARCHAR(40),
    commit_message TEXT,
    content_snapshot TEXT
);
CREATE INDEX IF NOT EXISTS idx_context_project ON context_changes(project_name);
CREATE INDEX IF NOT EXISTS idx_context_changed ON context_changes(changed_at);
```

### 3.2 Backend: Effectiveness-API (`routes/timesheet_routes.py`)

**GET `/api/timesheets/context-effectiveness`**
- Parameter: `project`
- Fuer jede CLAUDE.md-Aenderung im Projekt:
  - Metriken VORHER (14 Tage vor Aenderung):
    - Durchschnitt Messages pro Session
    - Durchschnitt Tokens pro Session
    - Durchschnitt Kosten pro Session
    - Rework-Rate (wenn bewertet)
  - Metriken NACHHER (14 Tage nach Aenderung):
    - Gleiche Metriken
  - Delta: Verbesserung/Verschlechterung in %
- Mindestens 3 Sessions vor UND nach fuer validen Vergleich

**GET `/api/timesheets/context-changes`**
- Parameter: `project`, `from`, `to`
- Liste aller Instruktions-Aenderungen mit Zeitstempel
- Optionaler Diff/Snapshot

### 3.3 Scan-Integration

**In `services/project_scanner.py` oder separater Cronjob:**
- Beim Projekt-Scan: CLAUDE.md Aenderungen erkennen
- Via `git log` den letzten Aenderungszeitpunkt lesen
- Neue Aenderungen in `context_changes` Tabelle einfuegen
- Idempotent: Gleicher Commit wird nicht doppelt eingefuegt

### 3.4 Frontend: Context-Effectiveness Report

**Auf Timesheets-Seite als eigener Tab "Context":**

**Pro Projekt (mit CLAUDE.md-Aenderungen):**
- Timeline-Ansicht: Vertikale Linie mit Aenderungs-Markern
- Vorher/Nachher-Karten nebeneinander:
  - Messages/Session: 12 -> 8 (-33%)
  - Tokens/Session: 450K -> 280K (-38%)
  - Kosten/Session: $2.10 -> $1.30 (-38%)
  - Rework-Rate: 25% -> 10% (-60%)
- Farb-Kodierung: Gruen = besser, Rot = schlechter

**Zusammenfassung ueber alle Projekte:**
- Welche Projekte haben sich nach CLAUDE.md-Updates verbessert?
- Ranking: Groesste Verbesserung -> groesste Verschlechterung

### 3.5 Projekt-Detail Integration

**Auf Projekt-Detail-Seite:**
- Neuer Bereich "AI Context Effectiveness"
- Zeigt letzte CLAUDE.md-Aenderung und deren Auswirkung
- Link zum vollstaendigen Report

---

## Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `services/context_tracker.py` | NEU | Change-Detection, Git-Analyse |
| `services/db_service.py` | EDIT | context_changes Tabelle |
| `routes/timesheet_routes.py` | EDIT | Effectiveness-Endpoints |
| `templates/timesheets.html` | EDIT | Context-Tab |
| `static/js/timesheets.js` | EDIT | Vorher/Nachher-Charts |
| `templates/project_detail.html` | EDIT | Effectiveness-Widget |

---

## Akzeptanzkriterien

- [x] CLAUDE.md/AGENTS.md/GEMINI.md Aenderungen werden automatisch erkannt (170 in 25 Projekten)
- [x] Vorher/Nachher-Metriken werden korrekt berechnet (14-Tage-Fenster)
- [x] Verbesserung/Verschlechterung wird prozentual angezeigt (Farb-kodiert)
- [x] Mindestens 2 Sessions pro Zeitraum fuer validen Vergleich
- [x] Report auf Timesheets-Seite (Context Effectiveness Bereich)
- [ ] Projekt-Detail Integration (Widget)
