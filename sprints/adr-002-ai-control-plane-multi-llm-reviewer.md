# ADR-002: AI-Control-Plane fuer kooperierende Multi-LLM-Systeme

Stand: 2026-04-11
Status: **ACCEPTED**
Entscheider: Joseph
Grundlage: ADR-001 (DB-First Marker Core + Tool-Adapter, Compatible Migration)

## Kontext

Das Projekt wurde bisher als Flask-Web-Dashboard fuer die Verwaltung von Projekten, Docker-Containern und Claude-Code-Sessions positioniert. Die reale Nutzung hat sich anders entwickelt:

- Joseph arbeitet taeglich mit **mehreren AI-Coding-Tools parallel**: Claude Code, Codex, Gemini CLI, Hermes, potentiell weitere. Jedes Tool hat eigene Staerken, eigene Ausfaelle, eigene Tagesform.
- **Einzelne LLMs werden mit der Zeit unzuverlaessiger**, inkonsistenter oder qualitativ schwaecher. Modell-Updates aendern Verhalten. Joseph kann sich nicht mehr darauf verlassen, dass ein Tool dauerhaft gut fuer eine bestimmte Aufgabe bleibt.
- Der heutige Arbeitsfluss besteht zu grossen Teilen aus **manuellem Copy-&-Paste** zwischen Tools, aus manueller Kontextpflege in mehreren Tool-Dateien (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`), aus manueller Qualitaetskontrolle und manueller Tool-Auswahl pro Task.
- ADR-001 hat das Fundament gelegt: DB-first Marker-Core, Write-Guard, Block-Marker-Schutz, Tool-Profile-Adapter, kompatible Migration. Aber es fehlt eine **Steuerungsebene drueber**, die mehrere Tools als Einheit betrachtet.
- Generische Software-Engineering-Aussagen ueber „welches Tool fuer welche Aufgabe" veralten schnell oder sind schlicht falsch. Sie gehoeren nicht hart in den Code.

Zwei Sprint-Plaene widersprechen sich nicht mehr, sondern erweitern sich:

- **ADR-001** bleibt gueltig als DB-first-Fundament fuer Marker und Tool-Files.
- **ADR-002** (dieses Dokument) erweitert die Architektur um eine **modellagnostische Steuerungsschicht** fuer kooperierende LLMs, bei der Perplexity als Aufsichtsinstanz und Policy-Reviewer auftritt.

## Entscheidung

### 1. Produktdefinition

Das Projekt ist ab sofort offiziell definiert als **modellagnostische AI-Control-Plane fuer Software-Projekte**, die:

- die Arbeit mehrerer kooperierender AI-Coding-Tools (Claude, Codex, Gemini, Hermes und weitere) **beobachtet, synchronisiert, bewertet und steuert**
- den Projektkontext (Plaene, Marker, Workflows, Qualitaetssignale, Sessions, Tool-Setups) **zentral und konsistent** haelt, damit beliebige AI-Coding-Tools darauf aufsetzen koennen
- einen **unabhaengigen Reviewer** (heute Perplexity, austauschbar) als **Aufsichtsinstanz** nutzt, die Tool-Setups, Arbeitsartefakte und AI-Outputs modellagnostisch bewertet und Verbesserungen vorschlaegt
- **Joseph als finale Autoritaet** behaelt: Der Reviewer schlaegt vor, das Dashboard rendert, der Mensch entscheidet

Das System ersetzt den manuellen Copy-&-Paste-Review-Workflow zwischen mehreren LLMs und dem Projektkontext.

**Leitbild:** „Nicht noch ein AI-Tool. Eine Aufsichtsschicht ueber allen."

Was das System **nicht** ist:

- Kein Claude-Code-Dashboard (auch wenn es heute so aussieht)
- Kein Single-Vendor-Frontend
- Kein autonomes Remediation-System
- Kein Ersatz fuer menschliche Priorisierung

### 2. Fuenf-Ebenen-Architektur

Die Control-Plane wird konzeptionell in fuenf Ebenen geschnitten. Die Ebenen sind **Rollen**, nicht zwingend getrennte Services:

| Ebene | Rolle | Wer heute |
|---|---|---|
| Steuerung | Orchestrator / Supervisor | Joseph + Perplexity |
| Planung | Planner / Scope-Cutter | Joseph, unterstuetzt durch Perplexity |
| Umsetzung | Specialist Executor | jeweils gewaehltes Coding-Tool (Claude, Codex, Gemini, ...) |
| Pruefung | Reviewer / Quality Gate | Perplexity, optional zweites Tool als Peer-Reviewer |
| Freigabe | Final Authority | Joseph |

Diese Schichten werden nicht als Code-Module abgebildet. Sie sind die **sprachliche Struktur**, in der Entscheidungen und Artefakte eingeordnet werden.

### 3. Observe / Review / Steer als Control-Plane-Schichten

Technisch teilt sich die Control-Plane in drei strikt getrennte Funktionsgruppen:

```
        +-------------------------+
        |  Observe                |   Snapshot aus bestehenden Services
        |  (Context-Collector)    |   nur lesend
        +-----------+-------------+
                    | Context-Snapshot
                    v
        +-------------------------+
        |  Review                 |   Perplexity als erste Backend-Implementierung
        |  (Reviewer-Service)     |   read-only Supervisor
        +-----------+-------------+   schreibt NUR in Suggestion-Tabellen
                    | Findings / Suggestions
                    v
        +-------------------------+
        |  Steer                  |   ueber bestehende Schreibpfade:
        |  (Approval + Apply)     |   write_guard, tool_profile_adapter,
        +-----------+-------------+   Approval-Endpoints
                    | nur nach Joseph-Freigabe
                    v
            Projekt-Artefakte
```

**Harte Trennlinien:**

- **Observe** ist rein lesend. Kein Schreibzugriff, keine Seiteneffekte.
- **Review** schreibt ausschliesslich in **Suggestion-Tabellen** (`project_reviews`, `policy_review_suggestions`). Niemals direkt in Runtime-Artefakte.
- **Steer** ist der einzige Schreibweg in Runtime-Artefakte. Er nutzt ausschliesslich bestehende Schreibpfade (`write_guard`, `tool_profile_adapter_service`) und braucht immer explizite Freigabe durch Joseph.

### 4. Reviewer-Rolle als Provider-agnostische Abstraktion

Der Reviewer ist eine **Rolle**, kein konkreter Provider. Perplexity ist die erste Backend-Implementierung und kann durch andere Modelle ersetzt werden, sobald Perplexity selbst unzuverlaessig wird. Die Architektur-Regel lautet: **das System spricht intern nur mit einer generischen Reviewer-API; der konkrete Provider ist eine austauschbare Backend-Implementierung.**

Der Reviewer hat im Vollausbau acht Funktionen, davon sind in Stufe 1 drei implementiert:

| # | Funktion | Stufe | Status |
|---|---|---|---|
| 1 | Setup-Reviewer (bewertet Projekt-Einrichtung fuer AI-Tools) | Stufe 1 | jetzt |
| 2 | Artefakt-Reviewer (prueft generierte Tool-Bloecke gegen DB-Core) | Stufe 2 | spaeter |
| 3 | Arbeits-Reviewer (bewertet Ergebnisse einer Session) | Stufe 3 | spaeter |
| 4 | Trendwaechter (erkennt Qualitaetsverfall pro Tool ueber Zeit) | Stufe 4 | spaeter |
| 5 | **Context-Drift-Waechter** (prueft Konsistenz zwischen CLAUDE.md/AGENTS.md/GEMINI.md) | Stufe 1 | jetzt |
| 6 | Tool-Routing-Berater (empfiehlt Tool pro Task-Typ) | Stufe 3 | spaeter |
| 7 | Uebergabe-Pruefer (prueft Tool-zu-Tool-Handoffs) | Stufe 3 | spaeter |
| 8 | **Policy-Reviewer** (schlaegt Aenderungen an Rollen/Tool-Profile/Policies vor) | Stufe 1 | jetzt |

**Kernregeln der Reviewer-Rolle:**

- Der Reviewer antwortet ausschliesslich in **strukturierten JSON-Schemas**. Freitext-Antworten werden verworfen.
- Der Reviewer ist **nie derselbe Provider** wie der Executor, dessen Arbeit er beurteilt. Kein Selbst-Review.
- Der Reviewer kann **nie** den Menschen ueberstimmen. Sein einziger Durchgriff ist eine Finding- oder Suggestion-Liste.
- Reviewer-Prompts sind **tool-agnostisch** formuliert: Sie sprechen von „dem schreibenden Tool", nicht von „Claude".

### 5. Policy-Schicht als DB-Governance

**Die Arbeitsteilung zwischen Tools wird nicht durch harte Architektur-Annahmen im Code definiert, sondern ueber eine DB-Policy-Schicht.** Das ist die zentrale Korrektur gegenueber einer fruehen Version dieses ADR.

Begruendung: Aussagen darueber, welches Tool fuer welche Aufgabe am besten ist, veralten schnell. Sie haengen von Modell-Releases, Developer-Erfahrungen und Tool-Aenderungen ab. Diese Information gehoert **nicht** in Konstanten oder Dispatch-Tabellen im Python-Code, sondern in die DB, wo sie sichtbar, versionierbar, manuell ueberschreibbar und durch Perplexity-Reviews aktualisierbar ist.

**Vier DB-Tabellen bilden die Policy-Schicht:**

| Tabelle | Rolle | Besonderheit |
|---|---|---|
| `roles` | Arbeits-Rollen als Datensatz | Slug-PK, aenderbar, deaktivierbar |
| `tool_profiles` | CLI/Modell/Provider-Kombinationen | Freie Staerken/Schwaechen als JSONB |
| `role_tool_policies` | Zuweisungen, versioniert | `valid_from`/`valid_until` fuer Historie, `approved_by` fuer Freigabe |
| `policy_review_suggestions` | Perplexity-Vorschlaege | Approval-pflichtig, `context_hash` fuer Dedup |

**Drei harte Flussregeln:**

1. **Perplexity schreibt nie direkt in `role_tool_policies`.** Der einzige Schreibpfad in die aktive Policy-Tabelle ist der Approval-Pfad, der explizit `decided_by` setzt.
2. **`context_hash` ist Dedup-Pflicht.** Identische Inputs erzeugen keinen neuen Vorschlag, sondern aktualisieren die bestehende `pending`-Zeile.
3. **Kein Auto-Apply selbst bei hohem Confidence.** Auch 99/100 bleibt `pending`, bis Joseph entscheidet.

**Seed-Rollen als Vorschlag, nicht als Wahrheit:** Beim ersten Bootstrap werden sechs initiale Rollen (`programming`, `saas_webdesign`, `ux_ui`, `code_fix`, `quality_review`, `research_review`) als Startpunkt angelegt. Sie sind **vollstaendig aenderbar, erweiterbar, deaktivierbar**. Sie stehen nicht als Konstanten im Code, sondern als Datensaetze in der DB.

### 6. Kernregeln der Control-Plane (bindend)

Diese Regeln gelten fuer jeden Code, jede UI und jeden neuen Reviewer, der unter ADR-002 gebaut wird:

1. **Ein Writer pro Marker**, mehrere Reviewer moeglich. Keine parallelen Schreibvorgaenge durch mehrere Tools auf denselben Marker.
2. **Reviewer immer anderer Provider** als Executor. Kein Selbst-Review.
3. **Kein Auto-Write ohne Joseph-Freigabe**, auch bei hohem Confidence.
4. **Keine tool-spezifische Logik im Core-Code.** Tool-Namen und Provider-Namen sind Daten in `tool_profiles`, nicht Konstanten in Python.
5. **Keine hart kodierten „Best Practices".** Policies sind Daten. Regeln, die altern koennen, gehoeren in die DB.
6. **Write-Guard + Block-Marker-Parser** (aus ADR-001) schuetzen manuellen Text in allen generierten Dateien.
7. **DB-first** (aus ADR-001) gilt weiter: Policies, Reviews und Suggestions leben in der DB, sind sichtbar, versionierbar und manuell ueberschreibbar.
8. **Reviewer-Prompts sind tool-agnostisch** formuliert. Neue Tools kommen ohne Prompt-Aenderung dazu.
9. **Provider-Trennung:** Der Reviewer ist eine Rolle, nicht Perplexity. Perplexity ist **eine** Backend-Implementierung.
10. **Jede Policy-Aenderung hat einen Audit-Trail** ueber `valid_from`/`valid_until` + `approved_by` + `applied_policy_id`.

### 7. Stufenplan

Die Control-Plane wird in vier Stufen gebaut. Jede Stufe ist eigenstaendig lauffaehig und committable.

**Stufe 1a (JETZT, kleinste funktionierende Control-Plane):**
- Setup-Reviewer mit `context_drift`-Check zwischen CLAUDE.md/AGENTS.md/GEMINI.md
- `project_reviews`-Tabelle (mit `review_type`, `reviewer_tool`, `reviewed_tools`)
- Context-Collector als Read-Only-Schicht auf bestehende Services (`workflow_core_service`, Quality-Scanner, `block_marker_parser`, `project.json`)
- Perplexity-Call als erste Backend-Implementierung der Reviewer-Rolle
- Minimaler Review-Trigger (REST-POST-Endpoint)
- Minimale Anzeige der Findings im bestehenden Tool-Files-Modal

Begruendung fuer den Schnitt: Stufe 1a ist die kleinste funktionierende Control-Plane. Sie beweist, dass der Observe-Review-Steer-Fluss technisch traegt und liefert sofort sichtbaren Wert, bevor die Policy-Schicht (1b) darauf aufbaut. Scope-Schutz vor Ueberdimensionierung.

**Stufe 1b (direkt nach 1a, sobald 1a lauffaehig):**
- Policy-Datenmodell (4 Tabellen: `roles`, `tool_profiles`, `role_tool_policies`, `policy_review_suggestions`) + Policy-Service mit CRUD + Versionierung
- Seed-Defaults (6 Rollen + initiale Tool-Profile) als expliziter Bootstrap-Aufruf, nicht als Auto-Boot
- Perplexity-Policy-Reviewer mit Suggestion-Flow + Dedup per `context_hash` + Approval-Pfad
- REST-Endpoints fuer Policies, Tool-Profile, Suggestions, Review-Trigger, Seed-Trigger
- UI-Seite `/policies` mit Rollen, Tool-Profilen, aktiven Policies, Pending Suggestions inkl. Approve/Reject
- Integration in `workflow_core_service.get_handoff_view()` um aktive Policies
- Session-Stats-Helper als Input fuer Policy-Reviews

**Stufe 2:**
- Cross-Project-Review-Widget im Hauptdashboard
- Batch-Review-Endpoint fuer alle aktiven Projekte
- Scheduled Reviews (RemoteTrigger, taeglich)
- Artefakt-Reviewer (prueft generierte Tool-Bloecke gegen DB-Core)
- Konflikt-Melder bei parallelen Tool-Zugriffen

**Stufe 3:**
- Arbeits-Reviewer fuer Sessions
- Tool-Routing-Berater
- Uebergabe-Pruefer fuer Tool-zu-Tool-Handoffs
- Marker-Schema-Erweiterung: `role_id`, `assigned_tool` optional
- Handoff-Blocks zwischen Tools

**Stufe 4:**
- Tool-Vertrauens-Trend pro Tool ueber Zeit
- Auto-Routing-Vorschlaege basierend auf Rating-Historie
- Capability-/Skill-Modell (falls dann noch sinnvoll — ADR-001 Prio 7 bleibt bis dahin zurueckgestellt)

### 8. Beziehung zu ADR-001

ADR-001 bleibt **vollstaendig gueltig**. ADR-002 setzt darauf auf:

| ADR-001-Element | Status | Rolle in ADR-002 |
|---|---|---|
| Prio 1 (Marker-DB-Tabelle) | DONE | Datenbasis fuer Policy-Reviewer |
| Prio 2 (Block-Marker + Write-Guard) | DONE | Schutzschicht fuer alle Steer-Schreibvorgaenge |
| Prio 3 (Marker-Importer) | DONE | unveraendert |
| Prio 4 (DB-first Umbau) | DONE | `workflow_core_service` als Observe-Datenquelle |
| Prio 5 (Write-Back Core -> handoff.md) | DONE | unveraendert |
| Prio 6 (`tool_profile_adapter_service`) | DONE | Renderer fuer Steer-Schicht |
| **Prio 7 (Capability-/Skill-Modell)** | **zurueckgestellt** | Nutzen nicht nachgewiesen, minimal-invasive Alternative via Policy-Schicht |
| **Prio 8 (Perplexity-Copilot als Review-Layer)** | **erweitert durch ADR-002** | Perplexity-Rolle wird auf Multi-LLM-Control-Plane ausgeweitet |

Prio 8 aus ADR-001 wird durch ADR-002 vollstaendig abgeloest und erweitert. Der urspruengliche Scope von ADR-001 Prio 8 (Perplexity prueft generierte `handoff.md` und Tool-Bloecke) bleibt enthalten — er wird unter ADR-002 als Artefakt-Reviewer (Stufe 2) geplant.

### 9. Was ADR-002 NICHT ist

- **Kein Code.** Konkrete Implementierung steht im Sprint-Plan `sprint-adr002-stufe1-control-plane.md`.
- **Keine vollstaendigen DB-Schemas.** Die stehen im Sprint-Plan.
- **Keine UI-Details** wie Screen-Layouts, CSS-Klassen, JS-Funktionen.
- **Keine hart kodierten Tool-Routing-Heuristiken.** „Claude ist gut fuer X, Codex fuer Y" ist Policy-Daten, nicht ADR.
- **Keine bindenden Listen** wie „beste Tools 2026". Policies sind DB-Daten.
- **Keine Tool-Namen als Architektur-Konstanten.** Claude, Codex, Gemini werden nur genannt, wo sie den aktuellen Kontext beschreiben — nicht als fest verdrahtete Identifikatoren.

## Alternativen (verworfen)

### A: Claude Code als Single-Tool-Basis

**Verworfen:** Das Problem (einzelne LLMs werden unzuverlaessig) besteht genau deshalb, weil Joseph **nicht** auf ein einzelnes Tool setzen kann. Eine Architektur, die Claude Code bevorzugt, zementiert das Risiko statt es zu adressieren.

### B: Routing-Heuristik im Code

**Verworfen:** Konstanten wie `PREFERRED_TOOL_PER_ROLE = {...}` in Python altern schnell, haben keinen Audit-Trail, keine Versionierung, keine Freigabe-Historie. Jede Aenderung braeuchte einen Code-Deploy. Das widerspricht dem Prinzip, dass Policies lebende Daten sind.

### C: Auto-Apply bei hohem Confidence

**Verworfen:** Auch 99/100 ist keine Gewissheit. Der Wert der Control-Plane liegt gerade darin, dass Joseph die finale Autoritaet behaelt. Auto-Apply macht das System zu einem weiteren autonomen LLM — das Gegenteil der Zielsetzung.

### D: Separate DB pro Tool

**Verworfen:** Zerlegt den Projektkontext in Silos, widerspricht ADR-001 DB-first, erzwingt kuenstlich getrennte Wahrheit pro Tool. Eine Control-Plane braucht **eine** gemeinsame Wahrheit, nicht mehrere parallele.

### E: Reviewer als MCP-Server oder Side-Process

**Verworfen fuer Stufe 1:** Zusaetzliche Infrastruktur-Komplexitaet ohne kurzfristigen Gewinn. Der Reviewer ist heute ein synchroner Perplexity-Call im bestehenden Python-Prozess. Bei spaeterem Skalierungsbedarf kann er ausgelagert werden, ohne die Datenvertraege zu brechen.

## Konsequenzen

### Positiv

- **Modellagnostisch:** Neue Tools (auch chinesische LLMs via Wrapper) fuegen sich als neue `tool_profiles`-Zeilen ein, ohne Code-Aenderung.
- **Audit-Trail fuer alle Policy-Entscheidungen** durch Versionierung und `approved_by`.
- **Perplexity-Vorschlaege sind versionierbar und reversibel.** Keine stillen Aenderungen.
- **Kein Vendor-Lock-In** auf ein einzelnes LLM oder einen einzelnen Reviewer-Provider.
- **Mentale Klarheit:** Control-Plane ist keine neue Architektur, sondern eine Leserichtung auf dem bestehenden Bau.
- **Joseph bleibt in Kontrolle.** Alle wichtigen Entscheidungen gehen durch seine Haende.
- **Kontextkonsistenz:** `context_drift`-Check verhindert, dass mehrere Tools mit verschiedenen Wahrheiten arbeiten.

### Negativ / Risiken

- **Policy-Pflege ist eine neue Arbeitsdomaene** fuer Joseph. Initial-Freigabe der Seed-Rollen + Tool-Profile + initiale Policies kostet Zeit.
- **Perplexity-Reviews kosten Tokens.** Dedup ueber `context_hash` und Cooldown sind Pflicht.
- **Rollenkatalog entwickelt sich.** Versionierung ist nicht optional.
- **Mehr Tabellen in der DB.** Wartungsaufwand steigt leicht. Wird durch lazy Schema-Migrationen und sauberes Pattern aufgefangen.
- **Perplexity selbst kann schlechter werden.** Die Architektur adressiert das durch Provider-Trennung: der Reviewer ist eine Rolle, nicht Perplexity. Aber der Wechsel waere Arbeit.
- **Zwei Review-Tabellen** (`project_reviews` fuer Setup-Reviews, `policy_review_suggestions` fuer Policy-Vorschlaege) muessen sauber getrennt gehalten werden, sonst verschmieren die Zustaendigkeiten.

### Leitregeln fuer die Umsetzung

- **Kein Big-Bang:** Schrittweise Umsetzung wie in ADR-001, jeder Schritt einzeln testbar und committbar.
- **Seed-Daten sind Vorschlaege, nicht Wahrheit.** Joseph kann sie jederzeit aendern.
- **Policies sind Daten, keine Konstanten.** Niemals als Python-Konstante definieren. Wenn eine Regel sich aendern koennte, gehoert sie in die DB.
- **UI zeigt immer Policy-Source und Approval-Historie.** Transparenz statt Magie.
- **Reviewer-Prompt tool-agnostisch formulieren.** Kein Tool-Name im Prompt als Bedingung.
- **Neue Reviewer-Funktionen brauchen eigenen Prompt und eigene Tabelle.** Keine gemeinsame Review-Tabelle fuer alle Funktionen.
- **Jeder Perplexity-Call ist strukturiert.** Freitext-Antworten werden verworfen.
- **Der Tool-Profile-Adapter bleibt Renderer**, nicht Bewerter. Seine Rolle aus ADR-001 bleibt unveraendert.

## Herkunft

Dieses ADR entstand aus einer Serie von Klaerungen zwischen Joseph und Claude Code waehrend der Planung von ADR-001 Prio 7 (Capability-Modell). Im Laufe der Diskussion wurde klar:

1. Das Capability-Modell in der urspruenglich geplanten Form loest nicht das eigentliche Problem — die Multi-LLM-Kooperation.
2. Der `tool_profile_adapter_service` aus ADR-001 Prio 6 ist technisch korrekt, aber inhaltlich zu schwach, weil er Metadaten statt Substanz rendert.
3. Der tatsaechliche Bedarf ist eine Steuerungsebene ueber mehreren LLMs, die Kontext, Qualitaet und Tool-Auswahl zentral haelt — nicht ein weiteres Feature innerhalb eines einzelnen Tools.
4. Harte Annahmen ueber „welches Tool fuer welche Aufgabe" gehoeren nicht in Code, sondern in versionierte Daten, die durch einen unabhaengigen Reviewer (Perplexity) laufend aktualisiert werden koennen.

Das Ergebnis ist dieses ADR. Prio 7 aus ADR-001 wird bis auf Weiteres zurueckgestellt, Prio 8 wird durch ADR-002 erweitert und vorgezogen.

## Nachtrag 2026-04-11: Dispatch/Execute als explizite Schicht + Autonomie-Regel

### 1. Anlass und Befund

Beim Lesen von Abschnitt 3 („Observe / Review / Steer") wurde klar, dass ADR-002 zwar den Schreibvorgang in Runtime-Artefakte beschreibt (Write-Guard, Tool-Profile-Adapter, Policy-Apply), aber nicht den Schritt, der aus einer freigegebenen Entscheidung einen konkreten Arbeitsauftrag an ein CLI ableitet.

Konkret:
Steer definiert, was sich wie aendern darf, nutzt bestehende Schreibpfade und verlangt explizite Freigabe. Es sagt aber nicht, welches Tool diesen Auftrag ausfuehrt, wann es beginnt und mit welchem Scope es arbeitet. Die heutige Luecke: Der Uebergang von „Marker X ist fuer Rolle programming freigegeben" zu „Tool Y oeffnet einen Prompt mit Marker-X-Kontext und beginnt zu arbeiten" ist nirgends formal modelliert.

Ohne diese Schicht kann die Control-Plane beobachten, bewerten und freigeben, aber sie kann keine Arbeitszuweisung an CLIs aussprechen. Sie bleibt Review-Ebene, keine Arbeitssteuerung.

### 2. Erweiterte Domaenenfolge: Observe → Review → Steer → Dispatch → Execute

Die bisherige Dreiteilung

Observe → Review → Steer

wird um eine explizite vierte Domaene erweitert:

Observe → Review → Steer → Dispatch → Execute

Observe sammelt Kontext (Sessions, Marker, Artefakte).

Review bewertet Vorschlaege/Aenderungen, ggf. multi-LLM.

Steer definiert, welche Aenderungen an welchen Artefakten prinzipiell erlaubt sind (Write-Guard, Policy-Apply).

Dispatch erzeugt einen Arbeitsauftrag fuer ein konkretes Tool mit klar definiertem Scope und Risiko-Label.

Execute ist die tatsaechliche Ausfuehrung im Tool/CLI und die Rueckschreibung in Artefakte ueber bestehende Schreibpfade.

Damit gilt als Grundregel:

Ein Tool arbeitet nicht, weil ein Review existiert, sondern weil ein freigegebenes Assignment mit klarer Zustaendigkeit und Scope erzeugt wurde.

### 3. work_assignments als neue Datenentitaet

Zur Abbildung von Dispatch wird eine neue, eigenstaendige Datenentitaet `work_assignments` eingefuehrt. Sie ist konzeptionell Teil des Datenlayers der Control-Plane (neben `project_reviews`, `policies`, Marker-Workflow-Zustaenden usw.).

Zweck:
`work_assignments` halten fest, welches Tool fuer welchen Marker / Scope mit welchem Risiko-Label und welchem Autonomie-Level arbeiten darf, und in welchem Zustandsverlauf sich dieser Auftrag befindet.

Minimaler Feldumfang (konzeptionell, kein Schema):

- `assignment_id` — eindeutige ID.
- `marker_id` — Bezug auf den Marker / Task / Sprint-Abschnitt.
- `role` — Rolle, fuer die der Auftrag formuliert wurde (z.B. programming, analysis).
- `executor_tool` — das konkret adressierte Tool/CLI (z.B. codex, kilo_code).
- `scope_ref` — Referenz auf den Arbeitsumfang (Dateiliste, Code-Region, Dokument-Segment, Marker-Scope).
- `input_payload_ref` — Referenz auf das Input-Paket fuer das Tool (Prompts, Kontext, Parameter), nicht der Inhalt selbst.
- `risk_level` — qualitative Einstufung (low, medium, high) nach Policy-Regelwerk.
- `automation_level` — Autonomie-Stufe (siehe Abschnitt 5).
- `approval_required` — boolesches Flag, ob vor Dispatch eine explizite Freigabe noetig ist.
- `approval_state` — proposed, approved, rejected, revoked.
- `dispatch_mode` — manual, pull, push (siehe Abschnitt 4).
- `allowed_write_scope` — Begrenzung, wo das Tool schreiben darf (z.B. nur bestimmte Dateien oder Marker-Boundaries).
- `timeout_at` — Zeitpunkt, ab dem der Auftrag als veraltet gilt.
- `claimed_at` / `claimed_by` — wann/wodurch der Auftrag von einem Tool aufgenommen wurde.
- `completed_at` — Abschlusszeitpunkt.
- `result_ref` — Referenz auf Ergebnis-Artefakte / Logs / Reviews.

Die konkrete Ausformung (SQL-Tabellen, Indizes, Event-Sourcing vs. klassische Tabelle) ist nicht Teil dieses Nachtrags und bleibt nachgelagerten Implementierungs-ADRs vorbehalten. Wichtig ist hier die Existenz der Entitaet und ihr Lebenszyklus.

Lebenszyklus (konzeptionell):

- `proposed` — aus einem Review/Steer heraus vorgeschlagener Auftrag, noch nicht freigegeben.
- `approved` — Auftrag ist durch Joseph oder eine autorisierte Rolle freigegeben (oder Policy-basiert automatisch genehmigt, wenn erlaubt).
- `dispatched` — Auftrag wurde aktiv einem Tool zugestellt oder zur Abholung bereitgestellt.
- `claimed` / `running` — ein Tool hat den Auftrag uebernommen und arbeitet.
- `completed` — Arbeit ist abgeschlossen; Ergebnis ist in Artefakten/Reviews referenziert.
- `failed` / `expired` / `escalated` — Auftrag gescheitert, abgelaufen oder zur manuellen Klaerung eskaliert.

### 4. Dispatch-Varianten: manuell, Pull, Push

Dispatch wird als eigene Operation gefuehrt, die sich in drei Varianten manifestieren kann. Alle drei erzeugen denselben Typ von `work_assignment`, unterscheiden sich aber darin, wie der Auftrag beim Tool ankommt.

**A. Manuell (Assignment durch Joseph)**

Joseph waehlt in UI/CLI einen Marker oder Scope, laesst sich Review/Steer-Output anzeigen und erstellt daraus explizit ein `work_assignment` fuer ein bestimmtes Tool.

Das Tool erhaelt keinen automatischen Start; Joseph startet das CLI selbst und uebergibt Kontext (Stufe 1b/2).

Dies ist der heutige Status quo (Copy-Paste, manuelles Oeffnen) — nun aber modelliert.

**B. Pull (Tool holt sich Aufgaben)**

Tools/CLIs fragen aktiv nach „offenen, zu mir passenden work_assignments" (z.B. nach Rolle, Tool-Profil, Status approved).

Das Control-Plane-Backend beantwortet diese Pull-Anfrage und liefert ein Assignment mit Input-Payload-Ref.

Das Tool entscheidet, wann es den Auftrag annimmt (claimed) und beginnt (running).

**C. Push (System stoesst Tool-Run an)**

Die Control-Plane triggert aktiv einen Tool-Run, sobald ein `work_assignment` die Kriterien fuer automatischen Dispatch erfuellt (z.B. low risk, automation_level erlaubt Push).

Das CLI wird extern gestartet oder ueber eine laufende Session angesprochen.

Fuer dein System gilt:

Kurzfristig ist A bindend, B ist Zielbild fuer hoehere Autonomie-Stufen, C bleibt explizit nachgelagerte Option und erfordert separate Freigabe/ADRs.

### 5. Autonomie-Regel: Risikobasierte Automatisierung

Die Autonomie-Regel wird direkt an Dispatch gekoppelt. Fuer jede Operation wird festgelegt, ob und unter welchen Bedingungen sie automatisch gestartet werden darf.

Leitfrage:

„Ist diese Operation niedrig riskant, reversibel, klar eingegrenzt und gut messbar?"

Wenn ja, kann eine automatische Behandlung sinnvoll sein; wenn nein, ist mindestens eine Approval-, Escalation- oder Timeout-Regel notwendig.

#### 5.1 Autonomie-Stufen

Das System kennt vier Autonomie-Stufen, die pro `work_assignment` (Feld `automation_level`) gesetzt werden:

**Level 0 — Observe Only**

Nur Lesen: Observe, Sync, Analyse, Status-Abfragen.

Keine Schreibrechte, kein Dispatch-Start.

Beispiele: Log-Aggregation, Metrik-Berechnung, Code-Scanning ohne Write-Back.

**Level 1 — Draft / Prepare (kein automatischer Dispatch)**

Tools duerfen Entwuerfe erzeugen (z.B. Code-Diffs, PR-Vorlagen, Doc-Entwuerfe), aber keine eigenstaendigen Schreiboperationen ausfuehren.

`work_assignments` koennen erstellt werden, aber `approval_required = true` und `dispatch_mode = manual`.

Beispiele: Draft-Refactorings, Vorschlaege fuer Testfaelle, Architektur-Notizen.

**Level 2 — Low-Risk Dispatch (teilweise automatisch)**

Automatisierung ist erlaubt fuer niedrig riskante, reversible, klar eingegrenzte und messbare Operationen.

`work_assignments` mit `risk_level = low` und `automation_level = 2` duerfen per Pull oder (konfiguriert) per Push automatisch angenommen werden, sofern `allowed_write_scope` eng definiert ist.

Beispiele: Lint-Runs, Formatter, kleine Konsistenz-Fixes in bekannten Dateien, mechanische Aenderungen mit klaren Rollback-Moeglichkeiten.

**Level 3 — High-Impact / Policy-aktivierend (immer approval-pflichtig)**

Alle Operationen mit grossem Schreibumfang, Architekturwirkung oder Produktwirkung.

`approval_required = true`, `dispatch_mode = manual`. Keine automatische Ausfuehrung.

Beispiele: Architekturwechsel, Migrations, aktivierende Policy-Aenderungen, Cross-Tool-Neurouting.

#### 5.2 Bindende Grundregel

Fuer ADR-002 gilt damit:

Automatisierung ist erlaubt fuer Observe-, Sync-, Draft- und Low-Risk-Dispatch-Vorgaenge (Level 0–2); alle policy-aktivierenden oder weitreichend schreibenden Vorgaenge (Level 3) bleiben approval-pflichtig.

Jeder `work_assignment` muss ein `risk_level` und ein `automation_level` tragen. Das Zusammenspiel aus beidem entscheidet, ob:

- der Auftrag automatisch in den Zustand `approved` wechseln darf,
- der Auftrag automatisch im Pull/Push-Modus `dispatched` werden darf oder
- eine explizite Freigabe durch Joseph erforderlich ist.

### 6. Auswirkungen auf bestehende Artefakte

**HTML-Grafik (Systemuebersicht)**

- Zwischen Control-Plane und AI-Tools wird ein zusaetzlicher Block DISPATCH eingefuegt.
- Neben `policies` wird die Datenbox `work_assignments` ergaenzt.
- Der Rueckkanal von den AI-Tools zu Observe wird als echter Zyklus (Tools → Artefakte → Observe) visualisiert, nicht nur angedeutet.

**Stufen-/Timeline-Tabelle**

Die Implementierung von Dispatch (`work_assignments`, manuelle Assignment-Erzeugung, erste Pull-Variante) wird als eigene Ausbaustufe gefuehrt (z.B. Stufe 2a), basierend auf der bestehenden Stufe 1a/1b (Reviews, Policies, Approval-Pfad).

**Bestehende Stufen bleiben gueltig**

- Stufe 1b (Control-Plane fuer Reviews + Policies + Approval) bleibt unveraendert gueltig und ist Voraussetzung fuer Dispatch.
- Der Nachtrag erweitert die Produktvision, widerspricht ihr aber nicht.

**Keine sofortigen Schema-Aenderungen**

- Dieser Nachtrag definiert Konzept und Regeln, nicht das finale Datenmodell.
- Konkrete Tabellen, Felder und eventuelle Anpassungen an `marker_workflow_states` (z.B. `assigned_tool`) werden in nachgelagerten ADRs beschrieben.
