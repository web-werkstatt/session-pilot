# Sprint ADR-002 Stufe 1 — AI-Control-Plane (1a + 1b)

Stand: 2026-04-11
Status: **FREIGEGEBEN** (Review Joseph)
Grundlage: `sprints/adr-002-ai-control-plane-multi-llm-reviewer.md`

## Ziel

Stufe 1 aus ADR-002 umsetzen: kleinste funktionierende Control-Plane fuer kooperierende Multi-LLM-Systeme. Zuerst Stufe 1a (Setup-Reviewer als Proof-of-Concept), dann Stufe 1b (Policy-Schicht als DB-Governance).

**Stufe 1a = kleinste funktionierende Control-Plane.** Sie beweist, dass der Observe-Review-Steer-Fluss technisch traegt, und liefert sofort sichtbaren Wert.

**Stufe 1b = DB-Governance der Tool-Zuweisung.** Sie ersetzt hart kodierte Best-Practices durch versionierte, Perplexity-gestuetzte Policy-Daten.

Damit wird das Fundament gelegt, auf dem Stufen 2-4 (Cross-Project-Reviews, Arbeits-Reviewer, Tool-Trendwaechter) spaeter aufbauen.

## Relation zu bestehenden Plaenen

### ADR-001 Welle 1 (DB-First Marker Core)

**Beziehung: Dieser Sprint setzt ADR-001 fort.**

- ADR-001 Prio 1-6 sind DONE und bleiben als Fundament.
- ADR-001 Prio 7 (Capability-/Skill-Modell) bleibt zurueckgestellt. Die Policy-Schicht aus Stufe 1b liefert stattdessen Rollen + Tool-Profile + Zuweisungen als DB-Daten.
- ADR-001 Prio 8 (Perplexity als Review-Layer) wird durch ADR-002 erweitert und vorgezogen. Der Setup-Reviewer aus Stufe 1a ist die erste operative Umsetzung dieses Prinzips.
- `workflow_core_service` (ADR-001 Prio 4) bleibt zentrale Domaenenschicht. In Stufe 1b wird `get_handoff_view()` um aktive Policies erweitert.
- Write-Guard + Block-Marker-Parser (ADR-001 Prio 2) schuetzen weiterhin alle Markdown-Schreibvorgaenge.

### Sprint Workflow-v2 (GUI/UX)

**Beziehung: Orthogonal.**

Der Workflow-Tab bleibt unveraendert. Die neue `/policies`-Seite aus Stufe 1b ist eine eigene Route und beruehrt Workflow-v2 nicht. Der Setup-Reviewer aus Stufe 1a nutzt ausschliesslich das bestehende Tool-Files-Modal auf der Projekt-Detailseite.

### Sprint QS (DB-First State Consolidation)

**Beziehung: Phase 1 wird respektiert.**

Die Policy-Schicht aus Stufe 1b legt 4 neue DB-Tabellen an, **keine neuen JSON-Stores**. Sprint QS Phase 1 (JSON-Stores migrieren) bleibt unberuehrt, aber wir erweitern die Legacy-Oberflaeche nicht um weitere JSON-Dateien.

## Scope-Schnitt Stufe 1a vs. Stufe 1b

Nach Commit 3 ist Stufe 1a vollstaendig lauffaehig. Joseph kann an diesem Punkt innehalten, das Ergebnis testen und entscheiden, ob Stufe 1b direkt anschliesst oder auf einen spaeteren Zeitpunkt verschoben wird. Der Sprint ist bewusst so geschnitten, dass 1a eigenstaendigen Wert liefert.

---

## Commits 1-10 (sequentielle Umsetzung)

### Commit 1 — Doku-Rahmen

**Ziel:** Architektur-Rahmen und Sprint-Plan festschreiben, append-only Nachtraege an bestehende Dokumente anhaengen.

**Scope:**
- `sprints/adr-002-ai-control-plane-multi-llm-reviewer.md` (neu, bindende Produkt-Architektur)
- `sprints/sprint-adr002-stufe1-control-plane.md` (neu, dieses Dokument)
- Nachtraege (append-only):
  - `sprints/adr-001-db-first-marker-core-tool-adapter.md`
  - `sprints/master-plan-2026-04-01.md`
  - `next-session.md`

**Akzeptanzkriterien:**
- [ ] ADR-002 liegt mit Status ACCEPTED vor
- [ ] Sprint-Plan Stufe 1 liegt mit 10 Commit-Tickets vor
- [ ] Alle 3 append-only Nachtraege sind am Ende der jeweiligen Datei, kein bestehender Text angefasst
- [ ] Gitea-Issue referenziert ADR-002 + Sprint-Plan

---

### Commit 2 (Stufe 1a) — Setup-Reviewer Core + project_reviews-Schema

**Ziel:** Context-Collector, Reviewer-Service und Storage als Python-Fundament. Kein REST, keine UI, aber voll getestet.

**Scope:**
- `services/db_tool_setup_review_schema.py` (neu):
  - `ensure_tool_setup_review_schema()` lazy idempotent
  - Tabelle `project_reviews` mit `review_type`, `reviewer_tool`, `reviewed_tools`, `setup_ok`, `priority`, `summary`, `findings`, `suggested_blocks`, `project_json_patch`, `implementation_scope`, `notes`, `context_hash`, `raw_response`, `created_at`, `updated_at`
- `services/tool_setup_review_service.py` (neu):
  - `build_tool_setup_context(project_name)` — Collector aus `project.json`, Tool-Files via `block_marker_parser`, `workflow_core_service.get_markers()`, Quality-Snapshot, marker-context.md
  - `detect_context_drift(tool_files)` — Check, ob DASHBOARD-GENERATED-Bloecke in CLAUDE.md/AGENTS.md/GEMINI.md identisch sind
  - `review_tool_setup(project_name, query_fn=query_perplexity)` — orchestriert Collector + Perplexity-Call + Parsing + DB-Upsert
  - `save_review(project_name, result)` / `load_review(project_name)` via DB
- `prompts/setup_reviewer.md` (neu, tool-agnostischer System-Prompt mit exaktem JSON-Schema)
- `tests/test_tool_setup_review.py` (~15 Faelle): Schema-Idempotenz, Collector-Faelle (leer/voll/ohne Tool-Files/mit Drift), Drift-Check, Reviewer-Flow mit injected query_fn, Parse-Fehler-Handling, Dedup per context_hash

**Akzeptanzkriterien:**
- [ ] `ensure_tool_setup_review_schema()` ist idempotent
- [ ] Collector liefert bei unterschiedlichen Projektzustaenden den erwarteten Snapshot
- [ ] Drift-Check erkennt Divergenz in den DASHBOARD-GENERATED-Bloecken
- [ ] `review_tool_setup` mit injected Fake-Query-Function ergibt korrekte Datenbankeintragungen
- [ ] Parse-Fehler werden mit `error: "parse_failed"` + `raw_response` persistiert, setup_ok wird NULL
- [ ] Alle neuen Tests gruen, keine Regression in bestehenden Tests

**Dateien:**
- neu: `services/db_tool_setup_review_schema.py`
- neu: `services/tool_setup_review_service.py`
- neu: `prompts/setup_reviewer.md`
- neu: `tests/test_tool_setup_review.py`

---

### Commit 3 (Stufe 1a) — Setup-Reviewer REST + minimale UI-Anzeige

**Ziel:** Stufe 1a wird lauffaehig. Joseph kann per Button im Dashboard den Review ausloesen und das Ergebnis sehen.

**Scope:**
- `routes/tool_setup_review_routes.py` (neu):
  - `POST /api/project/<name>/tool-setup/review` — triggert Review-Lauf, persistiert, liefert Ergebnis
  - `GET /api/project/<name>/tool-setup/review` — liefert letztes gespeichertes Ergebnis ohne Call
  - Registration in `routes/__init__.py`
- UI-Erweiterung im **bestehenden** Tool-Files-Modal (`templates/project_detail.html` + `static/js/tool-profile-adapter.js`):
  - Button „Setup reviewen" unterhalb der bestehenden Diff-Anzeige
  - Findings-Liste mit Severity-Farben (info/warn/error)
  - Diff-Preview fuer `suggested_blocks` (read-only, kein Write)
  - Hinweis-Banner falls `context_drift` erkannt wurde
- Live-Check via Chrome-DevTools MCP: Button reagiert, Findings werden gerendert, Drift-Warnung erscheint wenn vorhanden
- Tests: 3 Endpoint-Tests (POST mit Fake-Query, GET vor/nach Review, 404)

**Akzeptanzkriterien:**
- [ ] POST-Endpoint triggert den Reviewer-Service und speichert das Ergebnis
- [ ] GET-Endpoint liefert letztes Ergebnis ohne neuen Call
- [ ] 404 bei unbekanntem Projekt
- [ ] UI zeigt Findings mit Severity-Farben
- [ ] UI zeigt Drift-Warnung wenn `context_drift.has_drift === true`
- [ ] Live-Verifikation am Dashboard erfolgreich
- [ ] **Stufe 1a vollstaendig, Joseph kann hier pausieren und testen**

**Dateien:**
- neu: `routes/tool_setup_review_routes.py`
- erweitert: `routes/__init__.py`
- erweitert: `templates/project_detail.html`
- erweitert: `static/js/tool-profile-adapter.js`
- erweitert: `static/css/tool-profile-adapter.css` (falls noetig)

---

### Commit 4 (Stufe 1b) — Policy-Schema + Service + Tests

**Ziel:** 4 Policy-Tabellen, Policy-Service mit CRUD, Versionierung, Suggestion-Flow. Kein Perplexity-Call, keine REST, keine UI.

**Scope:**
- `services/db_policy_schema.py` (neu):
  - `ensure_policy_schema()` lazy idempotent
  - Tabellen: `roles`, `tool_profiles`, `role_tool_policies`, `policy_review_suggestions`
  - Partial-Index auf `role_tool_policies (role_id, tool_id) WHERE valid_until IS NULL`
  - Partial-Index auf `policy_review_suggestions (status, created_at) WHERE status = 'pending'`
- `services/policy_service.py` (neu):
  - `list_roles(include_inactive=False)`, `get_role(role_id)`, `upsert_role(...)`
  - `list_tool_profiles(include_inactive=False)`, `get_tool_profile(tool_id)`, `upsert_tool_profile(...)`
  - `get_active_policies(role_id=None)` — liest `WHERE valid_until IS NULL AND approved_by IS NOT NULL`
  - `insert_policy(role_id, tool_id, rank, confidence, rationale, source, approved_by)` — legt Zeile an, setzt alte aktive Zeile auf `valid_until = NOW()`
  - `list_pending_suggestions()`, `record_suggestion(...)` mit Dedup via `context_hash`
  - `apply_suggestion(suggestion_id, decided_by)` — setzt `applied`, legt neue Policy-Zeile an, verknuepft via `applied_policy_id`
  - `reject_suggestion(suggestion_id, decided_by, reason=None)`
- `tests/test_policy_service.py` (~15 Faelle): Schema-Idempotenz, Rollen/Tool-Profile Roundtrip, Policy-Versionierung, Dedup, Approval-Flow, Reject-Flow, Pending-Filter

**Akzeptanzkriterien:**
- [ ] Schema idempotent, zwei Aufrufe werfen nicht
- [ ] Roles + Tool-Profiles CRUD funktioniert
- [ ] Policy-Versionierung: zweiter Insert fuer (role, tool) setzt ersten auf `valid_until`
- [ ] `get_active_policies` filtert korrekt
- [ ] Dedup per `context_hash` verhindert Duplikate
- [ ] Approval-Flow erzeugt neue Policy-Zeile und verknuepft die Suggestion

**Dateien:**
- neu: `services/db_policy_schema.py`
- neu: `services/policy_service.py`
- neu: `tests/test_policy_service.py`

---

### Commit 5 (Stufe 1b) — Seed-Defaults (6 Rollen + Tool-Profile)

**Ziel:** Bootstrap-Daten fuer die Policy-Schicht. Explizit, nicht auto-boot.

**Scope:**
- `seed_defaults()` in `services/policy_service.py` erweitern:
  - 6 Rollen: `programming`, `saas_webdesign`, `ux_ui`, `code_fix`, `quality_review`, `research_review`
  - Initiale Tool-Profile: `claude-code-opus-4-6`, `codex`, `gemini-cli`, `hermes`, `perplexity`
  - Keine initialen `role_tool_policies` — Joseph setzt sie manuell oder laesst Perplexity Vorschlaege machen
  - Idempotent: Re-Run legt nichts doppelt an, aber updated auch nichts bestehendes
- Admin-Trigger via REST (kommt in Commit 7)
- Tests: Seed-Idempotenz, Rollen vorhanden, Tool-Profile vorhanden, keine Policies gesetzt

**Akzeptanzkriterien:**
- [ ] `seed_defaults()` idempotent
- [ ] Alle 6 Rollen existieren
- [ ] Alle 5 Tool-Profile existieren
- [ ] `role_tool_policies` bleibt leer
- [ ] Seed-Daten sind als Python-Konstante im Service definiert, aber nur fuer den initialen Bootstrap-Zweck, nicht als Runtime-Quelle

**Dateien:**
- erweitert: `services/policy_service.py`
- erweitert: `tests/test_policy_service.py`

---

### Commit 6 (Stufe 1b) — Perplexity-Policy-Reviewer

**Ziel:** Perplexity analysiert den aktuellen Policy-Stand (aktive Policies + Tool-Profile + Session-Stats) und gibt strukturierte Vorschlaege.

**Scope:**
- `prompts/policy_reviewer.md` (neu, tool-agnostischer System-Prompt):
  - Beschreibt den Multi-LLM-Kontext
  - Definiert JSON-Schema der Antwort (suggestion_type, payload, rationale, evidence)
  - Betont: keine Empfehlungen aus Tool-Namen-Aesthetik, nur aus beobachtbaren Daten
- `services/policy_review_service.py` (neu):
  - `build_policy_review_context()` — sammelt Rollen, Tool-Profile, aktive Policies, Session-Stats pro Tool (Read-Only-Query auf bestehenden `sessions`-Table)
  - `review_policies(query_fn=query_perplexity)` — orchestriert Call, Parsing, Dedup, Insert in `policy_review_suggestions`
  - Dedup per `context_hash` (SHA256 ueber Collector-Output)
- Tests: 8 Faelle mit injected Fake-Query-Function, Parse-Fehler, Dedup, leere Daten, volle Daten

**Akzeptanzkriterien:**
- [ ] Collector liefert strukturierten Input
- [ ] `review_policies` mit Fake-Query erzeugt Eintraege in `policy_review_suggestions` mit `status=pending`
- [ ] Dedup: gleicher `context_hash` → kein neuer Eintrag, `updated_at` wird gesetzt
- [ ] Parse-Fehler werden gespeichert, kein Crash

**Dateien:**
- neu: `prompts/policy_reviewer.md`
- neu: `services/policy_review_service.py`
- neu: `tests/test_policy_review_service.py`

---

### Commit 7 (Stufe 1b) — Policy-REST-Endpoints

**Ziel:** Alle Policy-Funktionen ueber HTTP erreichbar.

**Scope:**
- `routes/policy_routes.py` (neu, eigenes Blueprint):
  - `GET /api/policies/roles`
  - `GET /api/policies/tool-profiles`
  - `GET /api/policies/assignments` (aktive Policies, optional `?role_id=`)
  - `GET /api/policies/suggestions?status=pending`
  - `POST /api/policies/review` — triggert Perplexity-Review
  - `POST /api/policies/suggestions/<id>/approve`
  - `POST /api/policies/suggestions/<id>/reject`
  - `POST /api/policies/seed-defaults`
- Registration in `routes/__init__.py`
- Alle Endpoints via `@api_route` Decorator
- Tests: ~8 Faelle (Happy-Path + 404 + Reject-Path)

**Akzeptanzkriterien:**
- [ ] Alle 8 Endpoints liefern erwartete Responses
- [ ] Approval-Endpoint legt neue Policy-Zeile an
- [ ] Reject-Endpoint aendert nur Suggestion-Status
- [ ] Seed-Endpoint ist idempotent

**Dateien:**
- neu: `routes/policy_routes.py`
- erweitert: `routes/__init__.py`
- neu: `tests/test_policy_routes.py`

---

### Commit 8 (Stufe 1b) — Policy-UI Seite /policies

**Ziel:** Joseph kann Rollen, Tool-Profile, aktive Policies und Pending Suggestions sehen und Suggestions freigeben/ablehnen.

**Scope:**
- `templates/policies.html` (neu):
  - 4 Sektionen: Rollen, Tool-Profile, Aktive Policies, Pending Suggestions
  - Rollen und Tool-Profile read-only
  - Aktive Policies als Tabelle mit Rolle, Tool, Rank, Confidence, Source, Rationale, Approved-By
  - Pending Suggestions als Cards mit Approve/Reject-Buttons
  - „Review anfordern"-Button fuer POST /api/policies/review
  - „Seed anlegen"-Button fuer POST /api/policies/seed-defaults (nur sichtbar wenn Rollen-Liste leer)
- `static/js/policies.js` (neu): Datenabruf via `api.get/post`, DOM-Rendering, Modal-Bestaetigung fuer Approve/Reject
- `static/css/policies.css` (neu): passend zum bestehenden Dashboard-Look (dunkles Theme)
- Navigation-Eintrag in `templates/base.html` oder `templates/_sidebar.html` (sofern es einen gibt)
- Live-Check via Chrome-DevTools MCP: Seite laedt, Daten werden angezeigt, Approve/Reject funktionieren

**Akzeptanzkriterien:**
- [ ] Seite `/policies` ruft REST-API korrekt auf
- [ ] Alle 4 Sektionen rendern
- [ ] Approve/Reject-Buttons funktionieren mit Bestaetigungs-Modal
- [ ] Review-Trigger-Button funktioniert
- [ ] Navigation-Eintrag ist sichtbar
- [ ] Null Console-Errors bei Live-Check

**Dateien:**
- neu: `templates/policies.html`
- neu: `static/js/policies.js`
- neu: `static/css/policies.css`
- erweitert: `templates/base.html` (Nav-Eintrag)
- evtl. neu: `routes/policy_routes.py` bekommt zusaetzlichen `GET /policies` Template-Render-Endpoint

---

### Commit 9 (Stufe 1b) — workflow_core_service Integration

**Ziel:** Aktive Policies sind aus dem Core-Service lesbar, damit spaeter der Tool-Adapter oder Handoff-Mirror sie rendern kann.

**Scope:**
- `services/workflow_core_service.get_handoff_view(project_name)` erweitern:
  - Zusatzfeld `active_policies`: Map `role_id → primary tool_id + rank`
  - Read-Only, keine DB-Writes
- `services/policy_service.get_session_stats_per_tool(days=30)` als neuer Helper:
  - Join `sessions` + `tool_profiles` ueber `tool_type` / `tool_id`
  - Liefert Dict `{tool_id: {session_count, total_tokens, distinct_projects}}`
  - Wird vom Policy-Reviewer als Evidence-Quelle genutzt
- Tests: `get_handoff_view` liefert `active_policies`, `get_session_stats_per_tool` gegen Mock-Sessions
- **Stufe 1b ist nach diesem Commit vollstaendig**

**Akzeptanzkriterien:**
- [ ] `get_handoff_view` hat `active_policies` im Output
- [ ] `get_session_stats_per_tool` liefert korrekte Aggregate
- [ ] Bestehende `get_handoff_view`-Tests bleiben gruen

**Dateien:**
- erweitert: `services/workflow_core_service.py`
- erweitert: `services/policy_service.py`
- erweitert: `tests/test_workflow_core.py` oder neues Testfile

---

### Commit 10 — Session-Close + Push

**Ziel:** Dokumentation aktualisieren, final Testsuite, Push.

**Scope:**
- `next-session.md` append-only mit Session-Zusammenfassung
- `pytest` vollstaendig laufen, alle Tests gruen
- Push auf Gitea
- Verifikation via `git log --oneline -12`

**Akzeptanzkriterien:**
- [ ] Alle Tests gruen (Stand: 659 + ~60 neue = ~720)
- [ ] 10 Commits auf Gitea sichtbar
- [ ] `next-session.md` hat Session-Block mit allen Commits

**Dateien:**
- erweitert: `next-session.md`

---

## Was dieser Sprint NICHT anfasst

- Cross-Project-Review-Widget (Stufe 2)
- Batch-Review / Scheduled Reviews (Stufe 2)
- Artefakt-Reviewer fuer generierte Tool-Bloecke (Stufe 2)
- Arbeits-Reviewer fuer Sessions (Stufe 3)
- Tool-Routing-Berater / Uebergabe-Pruefer (Stufe 3)
- Marker-Schema-Erweiterung um `role_id` / `assigned_tool` (Stufe 3)
- Tool-Vertrauens-Trend (Stufe 4)
- Capability-/Skill-Modell (ADR-001 Prio 7, bleibt zurueckgestellt)
- Umbenennung `tool_profile_adapter_service` → `tool_instruction_adapter_service` (spaeter)
- Migration Legacy-JSON-Stores (Sprint QS Phase 1, unabhaengig)

## Verifikation

1. ADR-002 liegt mit Status ACCEPTED vor
2. Nach Commit 3: Setup-Reviewer funktioniert live am Dashboard, Drift-Warnung erscheint bei divergenten Tool-Files
3. Nach Commit 9: /policies-Seite zeigt Rollen, Tool-Profile, Aktive Policies, Pending Suggestions; Approve/Reject funktionieren; `get_handoff_view` liefert `active_policies`
4. Nach Commit 10: alle Tests gruen, Gitea-Push durch, next-session.md aktualisiert

## Status-Nachtraege

_Platzhalter fuer Commit-Nachtraege (append-only waehrend der Umsetzung):_

