# Workflow-Status nach ADR-002 Stufe 1a + 1b

Stand: 2026-04-11 (Spaet-Abend)
Typ: Status-Dokument (keine bindende Architekturentscheidung, kein Sprint-Plan mit Tickets)
Grundlage: `sprints/adr-002-ai-control-plane-multi-llm-reviewer.md`,
           `sprints/sprint-adr002-stufe1-control-plane.md`

## Context

Nach einer langen Session wurde ADR-002 Stufe 1a und 1b in 12 Commits
durchgezogen (746/746 Tests gruen, alles auf Gitea gepusht). Joseph
fragt nach einer knappen Uebersicht, **was der AI-Control-Plane-Workflow
jetzt operativ leisten kann** und **was noch fehlt, bis der Workflow
als End-to-End rund ist**. Kein neuer Build-Plan — nur Bestandsaufnahme
als Entscheidungsgrundlage fuer die naechste Session.

---

## Was wir jetzt haben — Observe / Review / Steer live

### Observe (Kontext einsammeln)

- **Setup-Collector** (`services/tool_setup_review/context_collector.py`)
  liest pro Projekt: `project.json`, Tool-Files (CLAUDE.md/AGENTS.md/
  GEMINI.md) ueber `block_marker_parser`, Workflow-Snapshot ueber
  `workflow_core_service`, marker-context.md, optional Quality-Report.
- **Context-Drift-Check** (`services/tool_setup_review/drift_check.py`)
  erkennt, wenn die drei Tool-Files unterschiedliche generated Bloecke
  haben. Das ist der laute „mehrere Tools sehen verschiedene Wahrheiten"-
  Waechter.
- **Policy-Collector** (`services/policy_review_service.py`) liest
  aktuelle Rollen, Tool-Profile, aktive Policies als Snapshot fuer den
  Policy-Reviewer.
- **Session-Stats-Helper** (`services/policy_stats.py`) aggregiert
  Sessions pro `account` fuer ein Zeitfenster. Noch nicht aktiv im
  Policy-Reviewer-Input, aber bereit.

### Review (Perplexity als unabhaengiger Reviewer)

- **Setup-Reviewer** (`services/tool_setup_review/orchestrator.py`)
  schickt den Projekt-Snapshot an Perplexity, bekommt strukturierte
  Findings (area, severity, title, problem, recommendation) und
  suggested_blocks. Ergebnis persistiert in `project_reviews`-Tabelle
  mit `context_hash`-Dedup.
- **Policy-Reviewer** (`services/policy_review_service.py`) schickt
  die Policy-Schicht an Perplexity, bekommt Suggestions (new_policy,
  update_policy, deprecate_tool, new_role, update_tool_profile).
  Persistiert in `policy_review_suggestions`-Tabelle, approval-pflichtig.
- **Prompts** (`prompts/setup_reviewer.md`, `prompts/policy_reviewer.md`)
  sind editierbar ohne Code-Deploy. Setup-Reviewer-Prompt wurde in
  dieser Session zweimal geschaerft (keine geratenen Befehle,
  Severity-Kalibrierung, keine Citations).

### Steer (vorgeschlagene Aenderungen anwenden)

- **Tool-Profile-Adapter** (`services/tool_profile_adapter_service.py`,
  ADR-001 Prio 6) schreibt `DASHBOARD-GENERATED`-Bloecke in die drei
  Tool-Files ueber `write_guard` + `block_marker_parser`. Joseph
  triggert das manuell ueber „Regenerate schreiben" im Modal.
- **Policy-Apply-Pfad** (`policy_service.apply_suggestion`) nimmt eine
  Pending-Suggestion an, erzeugt eine neue `role_tool_policies`-Zeile
  mit Versionierung (alte bekommt `valid_until`). Joseph triggert das
  ueber Approve-Button auf `/policies`.
- **Kein Auto-Write.** Keine Suggestion wird ohne manuelle Freigabe
  wirksam, auch nicht bei Confidence 99/100.

### UI live

- **Tool-Files-Modal in jedem Projekt**: Topbar-Button „Tool Files"
  hat einen Status-Badge (grau/gruen/gelb/rot) aus dem letzten
  Setup-Review. Modal zeigt Review-Banner oben (Drift-Warnung,
  Findings in `<details>`, Refresh-Link dauerhaft sichtbar) plus
  Tool-File-Diff-Preview + einzigen Primaer-Button „Regenerate schreiben".
- **`/policies`-Seite**: vier Sektionen (Pending Suggestions, Aktive
  Policies, Rollen, Tool-Profile), Inline Approve/Reject, zwei
  Admin-Aktionen („Seed-Defaults anlegen", „Review anfordern").
  Navigation-Eintrag unter „Steuern".

### Policy-Schicht als DB-Governance

- Vier Tabellen: `roles`, `tool_profiles`, `role_tool_policies`
  (versioniert ueber `valid_from`/`valid_until`),
  `policy_review_suggestions` (approval-pflichtig).
- Seed-Defaults fuer 6 Rollen (programming, saas_webdesign, ux_ui,
  code_fix, quality_review, research_review) und 5 Tool-Profile
  (claude-code-opus-4-6, codex, gemini-cli, hermes, perplexity).
- Seed ist idempotent und preserviert Joseph-Edits beim Re-Run.

---

## Was der Workflow jetzt praktisch beantworten kann

Joseph oeffnet ein Projekt und fragt:

- *„Ist mein Setup fuer die AI-Tools ueberhaupt sinnvoll?"* — **ja, beantwortet**
  (Setup-Reviewer + Badge + Banner)
- *„Arbeiten meine Tools mit dem gleichen Kontext?"* — **ja, beantwortet**
  (Context-Drift-Check)
- *„Welche Rollen und Tool-Profile habe ich im System?"* — **ja, beantwortet**
  (`/policies`)
- *„Welches Tool ist aktuell fuer welche Rolle zustaendig?"* — **ja, beantwortet**
  (aktive Policies auf `/policies`)
- *„Was wuerde ein unabhaengiger Dritter an meiner Tool-Zuweisung aendern?"* —
  **ja, beantwortet** (Policy-Reviewer via Perplexity + Suggestions)

---

## Was noch fehlt — sortiert nach Stufe

### Stufe 2 (naechste logische Etappe)

| Feature | Wofuer | Aufwand-Gefuehl |
|---|---|---|
| Cross-Project-Review-Widget | Eine Uebersichts-Zeile pro Projekt mit Setup-Review-Status (Badge + Summary) auf der Hauptseite. Joseph sieht sofort, wo es brennt. | klein |
| Batch-Review-Endpoint | `POST /api/reviews/batch` reviewt alle aktiven Projekte in einem Rutsch, mit Dedup. Grundlage fuer scheduled reviews. | mittel |
| Scheduled Reviews | `RemoteTrigger` (taeglich) ruft den Batch-Endpoint. Joseph muss nicht mehr manuell triggern. | klein, nach Batch |
| Artefakt-Reviewer | Prueft, ob `handoff.md`-Mirror und Tool-Bloecke konsistent mit dem DB-Core sind (ADR-001 Prio 8 Originalscope). Eigener Prompt, eigene Tabelle. | mittel |
| Konflikt-Melder | Warnt, wenn zwei Tools parallel am gleichen Marker oder an den gleichen Dateien arbeiten. Braucht Session-Touch-Tracking. | mittel |

### Stufe 3 (das, was Multi-LLM-Kooperation wirklich rund macht)

| Feature | Wofuer | Aufwand-Gefuehl |
|---|---|---|
| Arbeits-Reviewer fuer Sessions | Perplexity bewertet Session-Outputs: Hat das Tool sein Ziel erreicht? Welche Drift? Eigener Reviewer, eigener Prompt, Rating als Evidence fuer Stufe 4. | gross |
| Marker-Schema: `role_id`, `assigned_tool` | Marker kann explizit an eine Rolle und ein Tool gebunden werden. Voraussetzung fuer Tool-Routing und Handoffs. | mittel |
| Tool-Routing-Berater | Perplexity empfiehlt beim Marker-Dispatch ein Tool basierend auf Rolle + Rating-Historie. Vorschlag, nicht Zwang. | mittel, nach Arbeits-Reviewer |
| Uebergabe-Pruefer | Wenn Tool A auf `write_back` setzt, prueft Perplexity vor Tool-B-Uebernahme, ob Uebergabe vollstaendig ist. | mittel |
| Handoff-Blocks pro Tool | Der `DASHBOARD-GENERATED`-Block enthaelt dann wirklich rollenspezifischen Uebergabestand. Macht die drei Tool-Files **inhaltlich** verschieden, aber konsistent zum DB-Core. | gross |
| `account → tool_id`-Mapping | Aktuell nutzt `policy_stats` nur `sessions.account`. Fuer ehrliche Tool-Qualitaet braucht es das Mapping auf `tool_profiles.tool_id` (mehrere Profile pro Account moeglich). | klein, aber datenabhaengig |

### Stufe 4 (selbstverbessernde Control-Plane)

| Feature | Wofuer |
|---|---|
| Tool-Vertrauens-Trend ueber Zeit | Zeigt, ob Claude oder Codex ueber Wochen schlechter werden. Graph, Alarm bei Absinken. |
| Auto-Routing-Vorschlaege | Perplexity nutzt Rating-Historie, um Policies automatisch nachzuschaerfen (Vorschlag, nicht Auto-Apply). |
| Capability-/Skill-Modell | ADR-001 Prio 7 bleibt zurueckgestellt. Wird erst relevant, wenn Policies nicht mehr ausreichen. |

---

## Parkzettel aus Stufe 1b (kleine offene Ecken)

- **`context_hash` enthaelt die Prompt-Version nicht.** Wenn Joseph den
  Reviewer-Prompt schaerft, greift der Dedup-Check weiterhin auf den
  alten Review. Workaround: `force=True`. Fix: Prompt-Hash mit in den
  context_hash, kleine Aenderung.
- **`policy_stats` aggregiert `account`, nicht `tool_id`.** Nur
  sinnvoll, wenn ein Account 1:1 auf ein Tool-Profil mappt. Fuer
  Multi-Profile-Accounts zu ungenau.
- **Tool-Profile-`strengths`/`weaknesses` leer.** Absichtlich, damit sie
  aus Review-Historie entstehen, nicht spekulativ gesetzt werden.
  Bleibt leer bis Stufe 3.
- **Policy-Reviewer ohne Session-Evidence.** Der Prompt erwaehnt
  `session_stats_per_tool`, aber der Collector schickt es noch nicht
  mit. Trivialer Einbau, aber nur sinnvoll mit Stufe 3 (echte Ratings).
- **Live-Test des Policy-Reviewers fehlt.** Setup-Reviewer wurde echt
  gegen Perplexity getestet und Prompt geschaerft. Policy-Reviewer ist
  nur mit injected query_fn geprueft, nie echt gegen Perplexity laufen
  lassen. Erste Aufgabe der naechsten Session.

---

## Kritische Files (Pfade fuer die naechste Session)

- **Setup-Reviewer:** `services/tool_setup_review/*.py`,
  `prompts/setup_reviewer.md`,
  `routes/tool_setup_review_routes.py`,
  `static/js/setup-reviewer.js`
- **Policy-Schicht:** `services/db_policy_schema.py`,
  `services/policy_service.py`,
  `services/policy_seed.py`,
  `services/policy_review_service.py`,
  `services/policy_stats.py`,
  `routes/policy_routes.py`,
  `templates/policies.html`,
  `static/js/policies.js`,
  `prompts/policy_reviewer.md`
- **Workflow-Integration:** `services/workflow_core_service.py`
  (get_handoff_view liefert markers + active_policies)
- **Architektur-Dokumente:** `sprints/adr-002-ai-control-plane-multi-llm-reviewer.md`,
  `sprints/sprint-adr002-stufe1-control-plane.md`
- **Naechste Session Start:** `next-session.md` (letzter Session-Block
  hat alle Commits + Parkzettel + Hausaufgaben)

---

## Empfohlene Reihenfolge fuer die naechste Session

Nichts davon implementieren ohne Joseph-Go — das hier ist nur die
Status-Uebersicht.

1. **Echter Policy-Reviewer-Testlauf** (no-write, wie beim Setup-Reviewer)
   → Prompt-Qualitaet bewerten, ggf. nachschaerfen
2. **Stufe 2 Kick-off:** Cross-Project-Review-Widget + Batch-Endpoint.
   Das sind die zwei kleinsten Schritte, die sofort sichtbaren Mehrwert
   bringen (Dashboard-Landingpage zeigt Setup-Health aller Projekte
   auf einen Blick).
3. **Scheduled Review** danach, sobald Batch-Endpoint steht
4. **Parkzettel `context_hash`** aufraeumen, wenn Gelegenheit — kleiner
   Fix, hoher Nutzen beim Prompt-Tuning

---

## Verifikation — wie Joseph den aktuellen Stand selbst pruefen kann

- **Dashboard:** `http://localhost:5055/` → „Steuern" → „Policies"
  → vier Sektionen sind sichtbar, „Seed-Defaults anlegen" klicken →
  Rollen/Tool-Profile erscheinen, „Review anfordern" triggert echten
  Perplexity-Call (kostet ein paar Cent)
- **Pro Projekt:** `/project/<name>` → Topbar-Button „Tool Files" →
  Status-Badge sichtbar, im Modal Banner oben + Diff-Preview unten,
  Inline-Link „Erneut reviewen" immer sichtbar
- **API:**
  - `GET /api/policies/roles` → aktuelle Rollen
  - `GET /api/policies/assignments` → aktive Policies
  - `GET /api/policies/suggestions?status=pending` → offene Vorschlaege
  - `GET /api/project/<name>/tool-setup/review` → letztes Setup-Review
- **Tests:** `pytest` → 746/746 gruen
- **Git-Log:** `git log --oneline e5c5b31..HEAD` → 12 Commits der Session
