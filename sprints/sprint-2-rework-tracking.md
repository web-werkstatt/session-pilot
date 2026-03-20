# Sprint 2: Rework-Tracking fuer AI-Code

**Ziel:** Sessions/Commits bewerten und Rework-Rate als Qualitaetsindikator tracken.
**Abhaengigkeit:** Sprint 1 (Timesheet-Infrastruktur, Cost-Service)
**Geschaetzter Umfang:** 1 Session

---

## Aufgaben

### 2.1 DB-Schema: Outcome-Tracking

Neue Spalten in `sessions`-Tabelle:

```sql
ALTER TABLE sessions ADD COLUMN outcome VARCHAR(20) DEFAULT NULL;
-- Werte: 'ok', 'needs_fix', 'reverted', 'partial', NULL (unbewertet)

ALTER TABLE sessions ADD COLUMN outcome_note TEXT DEFAULT NULL;
-- Freitext fuer Kontext

ALTER TABLE sessions ADD COLUMN outcome_at TIMESTAMPTZ DEFAULT NULL;
-- Wann bewertet
```

### 2.2 Backend: Outcome-API

**POST `/api/sessions/<uuid>/outcome`**
- Body: `{outcome: "ok|needs_fix|reverted|partial", note: "..."}`
- Setzt outcome, outcome_note, outcome_at
- Validierung der erlaubten Werte

**GET `/api/timesheets/rework`**
- Parameter: `period`, `project`, `account`
- Aggregation:
  - Bewertete vs. unbewertete Sessions
  - Rework-Rate: `(needs_fix + reverted) / bewertete_sessions * 100`
  - Verteilung nach Outcome-Typ
  - Rework-Rate pro Projekt
  - Rework-Rate pro Tool/Modell
  - Trend ueber Zeit (wochenweise)

**GET `/api/timesheets/rework/costs`**
- "Verschwendete" Kosten: Tokens von reverted Sessions
- Nachbesserungskosten: Tokens von needs_fix Sessions
- Effektive Kosten: Nur ok + partial Sessions

### 2.3 Frontend: Outcome-Bewertung

**Session-Detail (`templates/session_detail.html`):**
- Outcome-Buttons am oberen Rand: OK / Needs Fix / Reverted / Partial
- Aktiver Status visuell hervorgehoben
- Optionales Notiz-Feld (aufklappbar)
- Outcome wird per AJAX gesetzt, kein Page-Reload

**Sessions-Liste (`templates/sessions.html`):**
- Neue Spalte "Outcome" mit farbigem Badge
  - ok: gruen
  - needs_fix: orange
  - reverted: rot
  - partial: gelb
  - NULL: grau (unbewerted)
- Filter nach Outcome

### 2.4 Frontend: Rework-Dashboard

**Neuer Tab auf Timesheets-Seite oder eigene Seite:**

**KPI-Karten:**
- Rework-Rate (%)
- Bewertete Sessions / Gesamt
- Verschwendete Kosten ($)
- Effektive Kosten ($)

**Charts:**
- Donut: Outcome-Verteilung (ok/needs_fix/reverted/partial)
- Linien-Chart: Rework-Rate ueber Zeit (Wochen-Trend)
- Balken: Rework-Rate pro Projekt (Top 10)
- Balken: Rework-Rate pro Tool/Modell

**Tabelle:**
- Sessions mit needs_fix/reverted, sortiert nach Kosten
- Spalten: Projekt, Modell, Tokens, Kosten, Outcome, Note

### 2.5 Bulk-Bewertung

**Sessions-Liste:**
- Checkbox-Selektion fuer Mehrfach-Bewertung
- Dropdown "Ausgewaehlte bewerten als: OK / Needs Fix / ..."
- API: POST `/api/sessions/bulk-outcome` mit `{uuids: [...], outcome: "ok"}`

---

## Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `services/db_service.py` | EDIT | Schema-Migration (outcome-Spalten) |
| `routes/session_routes.py` | EDIT | Outcome-API Endpoint |
| `routes/timesheet_routes.py` | EDIT | Rework-Aggregation Endpoints |
| `templates/session_detail.html` | EDIT | Outcome-Buttons |
| `templates/sessions.html` | EDIT | Outcome-Spalte + Filter |
| `templates/timesheets.html` | EDIT | Rework-Tab/Bereich |
| `static/js/timesheets.js` | EDIT | Rework-Charts |

---

## Akzeptanzkriterien

- [x] Sessions koennen mit Outcome bewertet werden (UI + API)
- [x] Rework-Rate wird korrekt berechnet und angezeigt
- [x] Trend-Chart zeigt Entwicklung ueber Wochen
- [x] Verschwendete Kosten werden quantifiziert
- [x] Bulk-Bewertung funktioniert (API)
- [x] Outcome-Spalte in Sessions-Liste mit Badges
- [ ] Outcome-Filter in Sessions-Liste (UI-Dropdown)
- [ ] Bulk-Bewertung UI (Checkboxen + Dropdown)
