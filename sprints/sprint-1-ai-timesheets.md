# Sprint 1: AI Timesheets & Nutzungsanalyse

**Ziel:** Auswertung von Zeit, Tokens und Kosten pro Projekt, Tool und Zeitraum.
**Abhaengigkeit:** Vorhandene Session-Daten in PostgreSQL (277+ Sessions)
**Geschaetzter Umfang:** 1 Session

---

## Aufgaben

### 1.1 Backend: Timesheet-API (`routes/timesheet_routes.py`)

Neuer Blueprint `timesheets_bp` mit folgenden Endpoints:

**GET `/api/timesheets/summary`**
- Parameter: `period` (week/month/quarter/year/custom), `from`, `to`, `group_by` (project/tool/account)
- Aggregiert aus `sessions`-Tabelle:
  - Gesamtzeit (SUM duration_ms)
  - Gesamt-Tokens (SUM input + output)
  - Gesamt-Kosten (berechnet aus Modell-Preisen)
  - Session-Count
  - Message-Count
- Gruppiert nach: Projekt, Account (=Tool), Modell
- SQL-Aggregation, kein Python-Loop

**GET `/api/timesheets/daily`**
- Parameter: `from`, `to`, `project`, `account`
- Tagesweise Aggregation fuer Chart-Daten
- Return: `[{date, duration_ms, tokens_in, tokens_out, cost, sessions}]`

**GET `/api/timesheets/projects`**
- Parameter: `period`
- Top-Projekte nach Zeit/Tokens/Kosten sortiert
- Inklusive Trend (Vergleich zum Vorzeitraum)

**GET `/api/timesheets/tools`**
- Vergleich Claude vs Codex vs Gemini etc.
- Pro Tool: Sessions, Zeit, Tokens, Kosten

### 1.2 Service: Kosten-Berechnung (`services/cost_service.py`)

Modell-Preise (USD pro 1M Tokens):

| Modell | Input | Output |
|--------|-------|--------|
| claude-opus-4-6 | 15.00 | 75.00 |
| claude-sonnet-4-6 | 3.00 | 15.00 |
| claude-haiku-4-5 | 0.80 | 4.00 |
| gpt-4o | 2.50 | 10.00 |
| gpt-4.1 | 2.00 | 8.00 |
| gpt-4.1-mini | 0.40 | 1.60 |
| o3 | 10.00 | 40.00 |
| o4-mini | 1.10 | 4.40 |
| gemini-2.5-pro | 1.25 | 10.00 |
| gemini-2.5-flash | 0.15 | 0.60 |

Funktion: `calculate_cost(model, input_tokens, output_tokens) -> float`
Funktion: `get_model_price(model_name) -> {input, output}` (Fuzzy-Match)

### 1.3 Frontend: Timesheets-Seite (`templates/timesheets.html`)

Neue Seite unter `/timesheets`, Navigation in Sidebar.

**Header-Bereich:**
- Zeitraum-Selector (Diese Woche / Monat / Quartal / Jahr / Custom)
- Filter: Projekt, Tool/Account

**KPI-Karten (oben):**
- Gesamtzeit (formatiert: "12h 34m")
- Gesamt-Tokens (formatiert: "2.4M")
- Gesamt-Kosten ("$14.20")
- Sessions-Anzahl
- Durchschnitt pro Session

**Charts (Mitte):**
- Tagesbalken-Chart: Zeit pro Tag (letzte 30 Tage)
- Donut-Chart: Verteilung nach Projekt
- Balken-Chart: Vergleich nach Tool (Claude vs Codex vs Gemini)

**Tabelle (unten):**
- Pro Projekt: Name, Sessions, Zeit, Tokens (In/Out), Kosten, Trend-Pfeil
- Sortierbar nach jeder Spalte
- Zeile klickbar -> Filter auf Projekt

### 1.4 Navigation & Integration

- Neuer Menuepunkt "AI Timesheets" in Sidebar (`templates/base.html`)
- Widget auf Haupt-Dashboard: Kompakte Wochen-Zusammenfassung
- Link von Session-Detail zur Timesheet-Ansicht

---

## Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `services/cost_service.py` | NEU | Kostenberechnung |
| `routes/timesheet_routes.py` | NEU | API-Endpoints |
| `templates/timesheets.html` | NEU | Frontend-Seite |
| `static/js/timesheets.js` | NEU | Charts & Interaktion |
| `static/css/timesheets.css` | NEU | Styling |
| `routes/__init__.py` | EDIT | Blueprint registrieren |
| `templates/base.html` | EDIT | Sidebar-Link |

---

## Akzeptanzkriterien

- [x] `/timesheets` zeigt Wochen-Report mit KPI-Karten
- [x] Zeitraum wechselbar, Charts aktualisieren sich
- [x] Kosten werden pro Modell korrekt berechnet
- [x] Tool-Vergleich zeigt alle erkannten AI-Assistenten
- [x] Projekt-Tabelle ist sortierbar und filterbar
- [x] Responsive, Dark-Mode-kompatibel
- [x] Keine neuen Dependencies

## Bekannte Einschraenkungen

- Kosten sind ueberschaetzt weil `cache_read_input_tokens` zum vollen Preis berechnet werden
  (Claude cached Tokens kosten nur 10% des regulaeren Preises)
- Fix erfordert separates DB-Feld fuer Cache-Tokens -> Sprint 1.1
