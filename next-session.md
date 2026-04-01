# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-01
> **Status:** SPEC-basierte Architektur: Repo-Assessment, Project Memory, Perplexity Connector, Audit LLM Analyzer + Gating + Persistence
> **Naechste Aufgabe:** PERPLEXITY_API_KEY in .env setzen + Live-Test, dann Sprint 13 planen

---

## Session 2026-04-01 - Control-Plane & RAG Foundation (6 SPECs)

### Was wurde erledigt

**SPEC-REPO-ASSESS-001: Repository Assessment**
- Vollstaendiger Befund des Repos in docs/repo-assessment-control-plane-rag.md
- 10 DB-Tabellen dokumentiert, alle Services/Routes/Patterns katalogisiert
- Top-3 Integrationspunkte und 3 Folgesprints vorgeschlagen

**SPEC-PROJECT-MEMORY-001: Project Identity + Memory Foundation**
- Neue `projects`-Tabelle via `ensure_project_identity_schema()` (additiv)
- `services/project_memory_service.py`: aggregiert Sessions, Plans, Governance, File-Touches
- `GET /api/projects/<name>/memory` Endpoint (200 + 404)
- 9 Tests

**SPEC-PERPLEXITY-CONNECTOR-001: Isolierter Perplexity Connector**
- `services/perplexity_service.py`: `query_perplexity()` via urllib (analog gitea_service.py)
- 3 eigene Exceptions: PerplexityConfigError, PerplexityRequestError, PerplexityAPIError
- Config: PERPLEXITY_API_KEY, _BASE_URL, _MODEL, _TIMEOUT in config.py
- 19 Tests

**SPEC-AUDIT-ANALYZER-LLM-001: LLM-basierter Audit-Analyzer**
- `audit/analyzers/__init__.py`: `run_analyzers()` als Hook in audit/service.py
- Opt-in via AUDIT_LLM_ANALYZER_ENABLED Feature-Flag
- Ergaenzt nur evidence["llm_review"], aendert niemals status/overall_status
- 16 Tests

**SPEC-AUDIT-ANALYZER-GATING-001: Gating Rules**
- AUDIT_LLM_DEFAULT_MODE (auto/off/on), AUDIT_LLM_ALLOWED_PRIORITIES, _RISK_LEVELS
- Per-Requirement `llm_mode` Override (inherit/off/on) im Pydantic-Model
- `_should_run_llm()` Evaluation-Order wie in Spec definiert
- 24 Tests

**SPEC-AUDIT-PERSISTENCE-LLM-001: Evidence Persistence**
- Evidence-Shape angereichert: llm_review +model/created_at/analyzer_version
- llm_review_error als strukturiertes Objekt {code, message, status_code}
- `save_audit_response()` + `load_audit_results()` in audit/repository.py
- 13 Tests

### Git Commits
```
340a03e feat: SPEC-AUDIT-PERSISTENCE-LLM-001
684e2eb feat: SPEC-AUDIT-ANALYZER-GATING-001
52476b0 feat: SPEC-AUDIT-ANALYZER-LLM-001
7416c14 feat: SPEC-PERPLEXITY-CONNECTOR-001
bc66152 feat: SPEC-AUDIT-001 - Audit-Core
1f38ea7 feat: Sprint 12 - Governance JS-Refactoring
1ea60ce feat: SPEC-PROJECT-MEMORY-001
```

### Test-Status
- **113 Tests gruen** (9 Project Memory + 19 Perplexity + 32 Audit Core + 16 LLM Analyzer + 24 Gating + 13 Persistence)

---

## Naechste Session

### Prioritaet 1: Live-Test Perplexity
- [ ] PERPLEXITY_API_KEY in .env setzen
- [ ] Manueller Test: `query_perplexity([{"role":"user","content":"test"}])`
- [ ] AUDIT_LLM_ANALYZER_ENABLED=1 setzen und Audit mit LLM-Evidence testen

### Prioritaet 2: Sprint 13 planen
- [ ] Audit-API-Route (POST /api/audit/run, GET /api/audit/results/<run_id>)
- [ ] Audit-UI Seite mit Ergebnis-Darstellung
- [ ] Project Memory in Projekt-Detail-Seite einbinden

### Offene Bugs / Datenluecken
- [ ] joshko (6 Sessions), llm-test (1 Session) - Projektnamen ohne Verzeichnis
- [ ] 80 Sessions ohne Modell (26x claude, 25x codex, 8x gemini)
- [ ] 0/357 Sessions haben cost_estimate - Backfill-Script
- [ ] TOC top: 188px ist hardcoded - sollte dynamisch berechnet werden

### Docker Image Workflow
- [ ] GitHub Actions Pipeline fuer automatischen Build bei Release/Tag

### Nicht vergessen
- `projects`-Tabelle existiert jetzt in DB (lazy bootstrap via Project Memory API)
- Perplexity Connector: nur urllib, kein requests/httpx
- Audit LLM Analyzer: Feature-Flag AUDIT_LLM_ANALYZER_ENABLED=1 zum Aktivieren
- Gating: AUDIT_LLM_ALLOWED_PRIORITIES="must,should" zum Filtern
- **Git Push Safety:** Nur auf Gitea pushen, GitHub nur nach Rueckfrage
- **MODULAR BAUEN:** Eigene Dateien pro Concern
