# Week Final Execution Plan — Dashboard 1.4-final

Stand: 2026-04-07
Ziel-Datum: **bis Sonntag 2026-04-12** (6 Tage Di-So)
Status: **DEFERRED — nicht aktiv**

> **Hinweis 2026-04-07 (Closeout):** Dieser Plan wurde am Vormittag des 2026-04-07
> erstellt mit der Annahme, alle 10 offenen Sprints in einer Woche umsetzen zu koennen.
> Ein anschliessender Audit hat ergeben:
>
> - Sprint 12 (Governance) ist bereits zu ~80% DONE (Sprint C Light + Erweiterungen)
> - Die restlichen 9 Sprints umfassen ~275-355h tatsaechlichen Restaufwand
>   (Audit-Details siehe Conversation-Log Closeout 2026-04-07)
> - In einer Woche nicht realistisch ohne Code-Qualitaet zu opfern
>
> **Entscheidung:** Statt aggressiver Week-Final wurde der `sprint-final-closeout.md`
> Plan reaktiviert. Dashboard wurde mit Tag `v1.3-final` auf Feature-Freeze gesetzt.
> Die deferred Sprints sind im Master-Plan unter "Deferred Sprints (post-closeout v1.3-final)"
> dokumentiert.
>
> **Dieser Plan bleibt als Referenz erhalten** — die Backend/GUI-Aufteilung Claude/Codex,
> die Tagesplanung und die API-Kontrakt-Vorlagen sind valide und koennen bei Reaktivierung
> einzelner Sprints wiederverwendet werden.

---

## Auftrag

Alle 10 offenen Sprints aus dem Master-Plan **inklusive GUI** abschliessen, dann
Feature-Freeze. Ab Montag 2026-04-13 keine Dashboard-Entwicklung mehr.

Parallel-Strategie: **Zwei Rollen** — **Claude = Backend/Coding**, **Codex = GUI**.
Keine Datei-Ueberschneidung: Claude fasst nie `templates/`, `static/js/`, `static/css/`
an; Codex fasst nie `services/`, `routes/` (ausser HTML-Render-Endpoint), `db_service.py`,
`auto_coder/`, `scripts/` an.

Koordination laeuft ueber `next-session.md` (lesen beide). Pro Sprint legt Claude
den **API-Kontrakt** dort ab, sobald Backend steht; Codex baut die GUI dagegen.

## Scope (10 Sprints)

| # | Sprint | Backend (Claude) | GUI (Codex) | Tag |
|---|--------|------------------|-------------|-----|
| 1 | QS DB-First Phase 1 | 5 JSON-Stores → DB, alte JSON als Fallback | — (keine GUI) | Di |
| 2 | QS Phase 2+3 | Marker-State DB-first + Service-Layer | — (keine GUI) | Mi |
| 3 | Sprint 12 Governance Voll | Policy-Service + Gate-API + Overview-API | `/governance` Page + Project-Detail Block + Sidebar | Di-Mi |
| 4 | Sprint 13 Bidirektional LLM | Recommendations-Tabelle + Decide-API + 3 Generatoren + tool_control.py | `/recommendations` Tabelle + Decide-Modal + Project-Detail Badge | Mi-Do |
| 5 | Sprint 14 Sprint-Flow | `sprints` + `sprint_sessions` Tabelle + Backfill + KPI-Service | `/sprints` Liste mit Soll/Ist-Spalten | Do-Fr |
| 6 | Sprint 15 Turn-Level | Segment-Heuristik + `segments` Tabelle + Outcome-API | Segment-Marker + Per-Segment-Outcome im Session-Detail | Fr-Sa |
| 7 | Sprint 16 Workflow-Profile | `workflow_profiles` Tabelle + Service + Default-Seed | `/workflow` Settings-Page mit Toggles | Sa |
| 8 | Sprint 6 DeRep Fixer | `auto_coder/derep.py` MVP + CLI | — (keine GUI) | Sa |
| 9 | Sprint 8 Automation | Quality-Scheduler + neue Notif-Typen + RemoteTrigger | — (Notifs erscheinen in bestehender Liste) | So |
| 10 | Audit-Weiterentwicklung | `input_facts` in Audit-Run + Gate-Integration | Audit-Detail Header zeigt Facts | So |
| — | Sprint 20 Product Launch Bundle | Release-Notes-Daten + Tag-Skript | `release-notes.html` + Footer-Link | So |

**Sprint 20 ist das Closeout-Bundle**, kein eigener Feature-Sprint.

---

## Pipeline & Rollen

```
Sprint X:  Claude Backend  ──API-Kontrakt──→  next-session.md  ──→  Codex GUI
              (Tag N)                                                  (Tag N oder N+1)
```

Claude arbeitet **eine halbe bis ganze Sprint-Laenge voraus**. Sobald Backend
einer Stufe steht, dokumentiert Claude den API-Kontrakt in `next-session.md`
(Endpoints, JSON-Shape, Sidebar-Eintrag-Vorschlag). Codex liest, baut GUI dagegen,
markiert in `next-session.md` als "GUI DONE" wenn fertig.

Reine Backend-Sprints (QS, 6, 8) laufen komplett bei Claude — Codex hat in der
Zeit Puffer fuer GUI-Sprints, die Backend-seitig schon fertig sind.

## Datei-Eigentum (No-Conflict-Zone)

| Rolle | Dateien (exklusiv) |
|-------|--------------------|
| **Claude (Backend)** | `services/**`, `routes/**`, `db_service.py`, `auto_coder/**`, `scripts/**`, `migrations/**` (falls neu), alle `*.py` Dateien |
| **Codex (GUI)** | `templates/**`, `static/js/**`, `static/css/**`, alle Frontend-Dateien |
| **Geteilt (Append-Only, am Tagesende mergen)** | `routes/__init__.py` (Blueprint-Registrierung — Claude), `templates/base.html` (Sidebar — Codex), `CLAUDE.md`, `sprints/master-plan-2026-04-01.md`, `next-session.md` |

**Regeln:**

- Codex fasst **keine** `.py` Datei an. Wenn Codex einen Backend-Bug sieht: in
  `next-session.md` als "BLOCKER fuer Codex" eintragen, Claude fixt im naechsten
  Backend-Block.
- Claude fasst **keine** `templates/`, `static/` Datei an. Wenn Claude die GUI
  fuer einen Smoke-Test braucht: nur `curl` gegen die API testen, nicht im Browser.
- `routes/__init__.py` und `templates/base.html`: nur je eine Rolle pro Tag, klare
  Reihenfolge im Tagesplan unten festgelegt.

---

## Tagesplan

### Tag 1 — Dienstag 2026-04-07 (heute)

**Claude (Backend):**
- **Sprint 12 Backend** komplett:
  - `services/governance_service.py`: `get_policy(name)`, `set_policy(name, level)`, `compute_gate(name)` (gruen/gelb/rot aus Quality+Audit+Outcome)
  - `routes/governance_routes.py`: `GET /api/governance/overview`, `GET/PUT /api/projects/<name>/policy`, `GET /api/governance/gate/<name>`
  - Schema fuer Workflow-Toggles in `project.json` (V2-Migration in `project_scanner.py`)
  - `routes/__init__.py`: Blueprint registrieren
  - **API-Kontrakt + Sidebar-Vorschlag** in `next-session.md` ablegen
- **Sprint QS Phase 1** Backend (parallel laufen lassen wenn Sprint 12 hakt):
  - `services/state_migrations/migrate_notifications.py` etc.
  - `ensure_state_schema()` in `db_service.py` (ein Block)
  - JSON-Stores als Fallback, Daten in DB
  - Smoke-Test pro Endpoint

**Codex (GUI):**
- Wartet morgens auf Sprint-12-Kontrakt in `next-session.md`
- Sobald Kontrakt da: `templates/governance.html` + `static/js/governance.js` + `static/css/governance.css` + Sidebar-Eintrag in `base.html`
- Quelle nur die in `next-session.md` dokumentierten Endpoints, kein direkter Backend-Code-Lookup
- `next-session.md`: "Sprint 12 GUI DONE" wenn fertig

**Tagesziel Di:** Sprint 12 Backend + GUI DONE. QS Phase 1 DONE. Tag-Commit beider Rollen.

---

### Tag 2 — Mittwoch 2026-04-08

**Claude (Backend):**
- **Sprint QS Phase 2+3** komplett:
  - `marker_state` Tabelle, `scripts/backfill_marker_state.py`
  - `copilot_marker_service.py` liest aus DB, faellt auf `handoff.md` zurueck
- **Sprint 13 Backend** starten:
  - `recommendations` Tabelle, `services/recommendation_service.py`
  - `services/tool_control.py` mit `TOOL_INTERFACES` und Dry-Run-Default
  - `services/recommendation_generators.py`: 3 MVP-Generatoren
  - `routes/recommendations_routes.py`
  - **API-Kontrakt fuer Sprint 13** in `next-session.md`

**Codex (GUI):**
- Falls Sprint 12 noch offen: fertigmachen
- Ab Mittag: Sprint 13 GUI gegen Kontrakt — `templates/recommendations.html` + `static/js/recommendations.js` + Project-Detail Badge

**Tagesziel Mi:** QS DONE (alle 3 Phasen). Sprint 13 Backend + GUI DONE.

---

### Tag 3 — Donnerstag 2026-04-09

**Claude (Backend):**
- **Sprint 14 Backend** komplett:
  - `sprints` + `sprint_sessions` Tabelle (in `ensure_state_schema` anhaengen)
  - `services/sprint_flow_service.py`: `create_sprint()`, `list_sprints(project)`, `attach_session()`, `compute_kpis(sprint_id)`
  - Backfill bestehender `sprints/sprint-*.md` (Mtime als start_date wenn kein Frontmatter)
  - `routes/sprint_flow_routes.py`
  - **API-Kontrakt fuer Sprint 14** in `next-session.md`

**Codex (GUI):**
- Sprint 14 GUI: `templates/sprints.html` + `static/js/sprints.js` + `static/css/sprints.css` + Sidebar-Eintrag

**Tagesziel Do:** Sprint 14 Backend + GUI DONE.

---

### Tag 4 — Freitag 2026-04-10

**Claude (Backend):**
- **Sprint 15 Backend** komplett:
  - `services/segment_service.py`: `detect_segments(messages)` Heuristik
  - `segments` Tabelle
  - `routes/segments_routes.py`
  - **API-Kontrakt fuer Sprint 15** in `next-session.md`
- **Sprint 16 Backend** starten:
  - `workflow_profiles` Tabelle
  - `services/workflow_profile_service.py`
  - 1 Default-Profil seeden
  - `routes/workflow_routes.py`
  - **API-Kontrakt fuer Sprint 16** in `next-session.md`

**Codex (GUI):**
- Sprint 15 GUI: Segment-Marker + Per-Segment-Outcome im bestehenden `templates/session_detail.html`
- Falls Zeit: Sprint 16 GUI starten

**Tagesziel Fr:** Sprint 15 DONE. Sprint 16 Backend DONE, GUI ggf. Sa.

---

### Tag 5 — Samstag 2026-04-11

**Claude (Backend):**
- **Sprint 6 DeRep** komplett (rein Backend):
  - `auto_coder/derep.py`: `DeRep` Klasse mit `clean(code, language)` (3 Level)
  - CLI-Wrapper: `python -m auto_coder.derep <file>`
- **Sprint 8 Automation** komplett (rein Backend):
  - `services/quality_scheduler.py`
  - Neue Notification-Typen in `notification_service.py`
  - RemoteTrigger "Quality Scan" eintragen
- **Audit-Weiterentwicklung** komplett:
  - `services/audit_service.py`: `input_facts` Block laedt Quality-Score, Governance-Gate, Recommendations-Count
  - Governance-Gate nutzt Audit-Last-Result als Input
  - **API-Kontrakt fuer Audit-Header** in `next-session.md`

**Codex (GUI):**
- Falls offen: Sprint 16 GUI fertigmachen
- Audit-Detail Header: Quality-Facts anzeigen (kleine Aenderung im bestehenden Audit-Template)
- Notif-Typen visuell pruefen (in bestehender Notif-Liste)

**Tagesziel Sa:** Sprint 6, 8, 16, Audit-Erw. DONE.

---

### Tag 6 — Sonntag 2026-04-12 (Closeout-Tag)

**Claude (Backend):**
- Restbacklog (alles was Sa rausgefallen ist) zuerst
- Release-Notes-Generator: `scripts/generate_release_notes.py` aus Master-Plan-DONE-Bloecken
- Tag-Skript vorbereiten

**Codex (GUI):**
- `templates/release_notes.html` + Footer-Link
- Final-QA: alle neuen Pages im Browser durchklicken

**Beide Rollen zusammen — Sprint 20 Launch Bundle**
- Smoke-Test aller neuen Pages: `/governance`, `/recommendations`, `/sprints`, `/segments` (Detail), `/workflow`
- Smoke-Test aller alten Pages: Dashboard, Project-Detail, Copilot-Board, Sessions, Plans
- Backup-Lauf manuell: `bash scripts/backup.sh`
- README aktualisieren: neue Features-Liste, neue Routes
- CLAUDE.md aktualisieren: neue Service-Module, neue Patterns
- next-session.md neu schreiben: "Dashboard feature-frozen 2026-04-12, ab jetzt Wartungsmodus"
- master-plan: alle 10 Sprints in DONE-Block
- Tag: `git tag -a v1.4-final -m "Dashboard feature-freeze 2026-04-12"`
- Push zu Gitea (GitHub-Mirror nur nach Rueckfrage)

**Tagesziel So:** Audit-Erweiterung, Sprint 8 DONE. Tag `v1.4-final` auf Gitea. Dashboard im Wartungsmodus.

---

## GUI-Liefermatrix (was am Ende sichtbar ist)

| Sprint | Neue Page / UI-Element | Pfad |
|--------|------------------------|------|
| 12 | `/governance` Uebersicht + Project-Detail Governance-Block | Sidebar "Governance" |
| 13 | `/recommendations` Tabelle + Project-Detail Badge | Sidebar "Empfehlungen" |
| 14 | `/sprints` Liste mit Soll/Ist | Sidebar "Sprint-Flow" |
| 15 | Segment-Marker in `/session/<uuid>` | im bestehenden Session-Detail |
| 16 | `/workflow` Settings | Sidebar "Workflow" (unter Settings) |
| 6 | (keine UI, nur CLI) | — |
| 8 | Notifications-Typen erscheinen in bestehender Notif-Liste | bestehend |
| QS | Keine sichtbare UI, aber 5 alte JSON-Stores weg | Sidebar unveraendert |
| Audit-Erweiterung | Audit-Detail zeigt Quality-Score-Header | bestehend |
| 20 | Release-Notes Page `/release-notes` (statisch) | Footer-Link |

---

## Acceptance Criteria (Gesamt)

1. Alle 10 Sprints stehen mit DONE-Block im Master-Plan inkl. geaenderter Dateien
2. Service `project-dashboard` laeuft gruen, alle Smoke-Tests 200 OK
3. Alle neuen Sidebar-Eintraege fuehren zu funktionierenden Pages (kein 404, kein 500)
4. DB-Schema-Migrationen sind idempotent (zweiter Lauf = 0 Aenderungen)
5. Backup-Lauf gruen, eine Stichprobe entpackt und gelesen
6. Tag `v1.4-final` auf Gitea sichtbar
7. README + CLAUDE.md + next-session.md spiegeln den Endzustand
8. Kein offener Gitea-Issue mehr fuer einen der 10 Sprints

## Risiken & Gegenmassnahmen

| Risiko | Wahrscheinlichkeit | Gegenmassnahme |
|--------|--------------------|----------------|
| `db_service.py` Merge-Konflikt | hoch | Append-Only-Regel + `git pull --rebase` vor jedem Append; bei Konflikt manuell mergen, nicht autoresolve |
| Sprint 13 Tool-Control schreibt versehentlich live in CLAUDE.md | mittel | Dry-Run als Default, Apply nur ueber explizite User-Decide-Action |
| Sprint 14 Sprint-Backfill missdeutet alte Markdown-Dateien | mittel | Backfill schreibt Sprints mit `auto_imported=true`, User kann manuell korrigieren |
| Track-Synchronisation laeuft auseinander | mittel | Tagesende-Checkpoint: gemeinsamer Commit, Smoke-Test, kurze Statusnachricht in next-session.md |
| Eines der MVP-Features bricht alte Funktion | hoch | Smoke-Test alter Pages am Ende jedes Tages, nicht nur am Sonntag |
| Zeit reicht nicht | hoch | Sprint 20 (Launch Bundle) ist Pflicht, alles andere ist priorisiert nach Tabelle oben — bei Engpass rutscht Sprint 6 oder 8 raus, beides hat keinen UI-Impact |

## Reihenfolge bei Zeitknappheit (Drop-Liste)

Falls Sa-Abend klar ist dass nicht alles passt, in dieser Reihenfolge fallen lassen:

1. Sprint 8 Automation (komplett oder nur RemoteTrigger ohne Notif-Typen)
2. Sprint 6 DeRep (in deferred-Liste)
3. Audit-Weiterentwicklung (auf Sprint 21 verschieben)
4. Sprint 15 Turn-Level (auf MVP ohne UI reduzieren — nur Backend + Heuristik, UI deferred)

**Pflicht-Sprints (nie droppen):** QS, 12, 13, 14, 16, 20.

## Tagesende-Ritual (jeden Abend, beide Rollen)

1. Beide: lokaler Smoke-Test (Claude per `curl`, Codex im Browser)
2. Claude: `git pull --rebase`, eigene Commits, push
3. Codex: `git pull --rebase`, eigene Commits, push
4. Master-Plan: heutige DONE-Eintraege als Block (Claude pflegt)
5. `next-session.md`: Status anhaengen — was DONE, was offen, welcher Kontrakt fuer morgen liegt schon bereit
6. Service-Restart auf Live, ein `/api/data` Smoke-Test
7. Falls etwas rot: morgen frueh fixen, bevor neuer Sprint startet

## Koordination ueber `next-session.md`

`next-session.md` ist die einzige Live-Koordinationsdatei. Format pro Sprint-Block:

```
## Sprint XX — <Name> — <STATUS>

### Backend-Status
- DONE / IN PROGRESS / BLOCKED
- Neue Endpoints: GET /api/..., POST /api/...
- Response-Shapes (kompaktes JSON-Beispiel)
- Sidebar-Vorschlag: "<Label>" → /<route>

### GUI-Status
- DONE / IN PROGRESS / WAITING / BLOCKED
- Geplante Templates/JS/CSS-Dateien
- Offene Fragen an Backend (falls vorhanden)

### Smoke-Test
- curl-Beispiel
- Browser-Pfad
```

**Regeln:**

- Claude darf nur den Backend-Block schreiben, Codex nur den GUI-Block.
- Beide duerfen "BLOCKER fuer X" Zeilen unten anhaengen.
- Bei Konflikt im Tagesende-Merge: jeder pulled rebase, eigenen Block neu einfuegen.

---

## Definition of "DONE" pro Sprint

Ein Sprint ist DONE wenn **alle** Punkte erfuellt sind:

- [ ] Backend-Code committed
- [ ] DB-Schema (falls noetig) idempotent in `db_service.py`
- [ ] API-Smoke-Test 200 OK
- [ ] GUI-Element sichtbar und navigierbar (sofern vorgesehen)
- [ ] Sprint-Plan-Datei in `sprints/` hat Status-Header "DONE 2026-04-XX"
- [ ] Master-Plan hat DONE-Block mit Datei-Liste
- [ ] Gitea-Issue (sofern angelegt) geschlossen oder mit `fixes #N` im Commit
- [ ] Kein 500-Error im Service-Log seit Sprint-Start

## Definition of "WEEK FINAL DONE"

- [ ] Alle 10 Sprints DONE (oder dokumentiert gedroppt mit Begruendung)
- [ ] Tag `v1.4-final` auf Gitea
- [ ] README, CLAUDE.md, next-session.md final
- [ ] Backup gruen
- [ ] Service stabil, kein Restart-Loop, keine 500er
- [ ] User-Bestaetigung: "passt, ab Montag echte Projekte"
