# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-02
> **Status:** Release v1.2.0, Test-Suite komplett (Stufe 1-3)
> **Naechste Aufgabe:** Refactoring + offene Feature-Arbeit

---

## Was in dieser Session fertig wurde (2026-04-02 Abend)

### Release v1.2.0
- CHANGELOG.md erstellt (27 Features, 22 Fixes, 19 Docs seit v1.1.0)
- Git-Tag v1.2.0 gesetzt, Docker-Image getaggt (sessionpilot:v1.2.0)
- Release-Skill `sessionpilot-release` als wiederverwendbarer 7-Schritt-Prozess gespeichert

### Test-Infrastruktur (Stufe 1-3)
**Vorher:** 258 Tests, 37 failed, 54 errors
**Nachher:** 451 Tests, 0 failed, 0 errors (65s)

**Stufe 1 — Shared Fixtures:**
- `tests/conftest.py` — client, mock_perplexity, mock_docker, mock_gitea, mock_scanner

**Stufe 2 — Smoke-Tests (110 Tests):**
- `tests/test_routes_smoke.py` — 20 HTML-Seiten, 66 API-Endpoints, 6 Param-Required, 6 Param-Missing, 7 Edge-Cases, 13 Struktur-Checks

**Stufe 3 — Unit-Tests (82 Tests):**
- `tests/test_cost_service.py` — 14 Tests (Pricing, Berechnung, Formatierung)
- `tests/test_notification_service.py` — 13 Tests (CRUD, Dedup, Thread-Safety)
- `tests/test_session_import.py` — 23 Tests (Projektname, Content-Parsing, JSONL, Hash-Dedup)
- `tests/test_session_import_utils.py` — 14 Tests (parse_ts, sanitize, time_range)
- `tests/test_project_detector.py` — 14 Tests (Tags, Typen, Validierung, Schema)

### Bugs gefixt
1. **config.py** — `load_dotenv()` fehlte: Tests konnten DB-Credentials nicht laden (91 Failures weg)
2. **timesheets/projects** — SQL-Bug: `'<%>'` wurde von psycopg2 als Format-Spezifikator interpretiert → Produktion kaputt, Fix: `'<%%>'`
3. **ai_file_touches Schema** — CREATE INDEX vor ALTER TABLE ADD COLUMN + Duplikate vor UNIQUE Constraint → Widget ai-hotspots kaputt
4. **copilot_board Test** — Template-IDs aus Sprint N Redesign nicht nachgezogen (sectionModal→addSectionModal, sectionChatInput→panel-chat-input)

### Commits
- `e42ed29` docs: CHANGELOG fuer v1.2.0
- `ab65270` fix: load_dotenv in config.py
- `5c752de` test: conftest.py + 39 Smoke-Tests
- `3142cc2` fix: Copilot-Board Test Template-IDs
- `83e5774` test: Stufe 2 komplett — 110 Smoke-Tests + fix timesheets SQL
- `94d2e18` fix: ai_file_touches Schema-Migration
- `d430d51` test: Stufe 3 — Unit-Tests fuer 5 Services

---

## Naechste Session

### Offene Aufgaben

- [ ] Copilot-Workflow: Perplexity als Copilot einsetzen
- [ ] LLM-agnostischer Connector (llm_connector.py)
- [ ] Pre-Commit Zeilenlimits fixen (db_service.py 526 Zeilen, governance_service.py 519 Zeilen)
- [ ] 6x bare except: fixen (cache_service, docker_service, git_service, gitea_service)
- [ ] 5x f-strings ohne Platzhalter (F541) pruefen
- [ ] 7x unused global Declarations (F824) bereinigen

### Moegliche naechste Schritte
- Error Class Tagging (Fehler-Kategorisierung pro Session)
- Git Diff per Session (welche Dateien hat Claude geaendert)
- CLAUDE.md Effectiveness Tracking
- Refactoring der 104 Funktionen mit >50 Zeilen (Top: build_plan_handoff_markdown 199 Zeilen)

### Nicht vergessen
- **Release-Skill:** `sessionpilot-release` — einfach "Mach ein Release" sagen
- **Rollenmodell:** Perplexity = Copilot (plant/reviewt), Claude Code = Executor (.md), Joseph = Abnahme
- **Level-Architektur:** /plans = Plan-Board (Level 1), /copilot?plan_id=X = Section-Board + Chat (Level 2)
- **Handoff-Service:** project_handoff_service.py — 3 Funktionen, eine handoff.md pro Projekt
