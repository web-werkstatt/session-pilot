# Managed Agents Gap Analysis fuer den aktuellen Stack

Stand: 2026-04-09

## Kurzfazit

Der aktuelle Stack deckt bereits einen grossen Teil der Control Plane fuer agentische Arbeit ab:
Session-Ingestion, Workflow-Steuerung, Marker/Handoffs, Governance, Audit, Usage-Monitoring,
Notifications und Copilot-Interaktion sind vorhanden.

Die groesste verbleibende Luecke gegenueber einer echten Managed-Agent-Plattform liegt nicht
in der Oberflaeche oder in Reports, sondern in einer standardisierten Execution Plane:
isolierte Agent-Runtime, langlebige Job-Ausfuehrung, Tool-Permissions, Retry/Resume,
Credential-Scoping und tiefes Run-Tracing.

## Einordnung

- Schon stark vorhanden: Control Plane, Observability, Governance, Workflow- und Review-Schicht
- Teilweise vorhanden: Copilot-Ausfuehrung, Command-Hub, Marker-basierte Arbeitssteuerung
- Noch schwach / nicht systematisch vorhanden: echte Agent-Runtime und Worker-Infrastruktur

## Matrix

| Bereich | Was der aktuelle Stack schon abdeckt | Was Managed Agents typischerweise zusaetzlich liefern | Reale Luecke bei uns | Bewertung |
|---|---|---|---|---|
| Agent-Control-Plane | Projekt-Dashboard als zentrale UI fuer Sessions, Copilot, Plans, Governance, Audit, Usage und Notifications | Oft nur teilweise oder generisch vorhanden | Keine kritische Luecke | Stark |
| Multi-Tool-Transparenz | Import von Claude, Codex, Gemini, OpenCode und Kilo in ein gemeinsames Modell | Meist Fokus auf eigene Runtime statt auf historisierte Fremdtools | Keine akute Luecke | Stark |
| Kontext- und Handoff-Modell | Marker, `handoff.md`, `marker-context.md`, Plan-Bindung, Aktivierung/Close/Rating | Teilweise als Session-/Task-Context abstrahiert | Keine grosse Luecke | Stark |
| Workflow-Steuerung | Plan-Workflow, Marker-Status, Gate-Logik, Abschluss-Flow, Workflow-Loop | Haengt vom Anbieter ab | Keine grosse Luecke | Stark |
| Governance | Projekt-Policies, Gate, Regelvorschlaege, Workflow-Vorgaben, Snippets | Scoped Permissions und standardisierte Runtime-Policies | Fehlt eher auf Runtime-Ebene, nicht auf Policy-Ebene | Mittel |
| Audit | Audit-Runs, persistierte Ergebnisse, Spec-Bezug, Review-Historie | Audit-Trails pro Runtime-Run und Tool-Call | Tieferes Laufzeit-Audit fehlt | Mittel |
| Observability | Usage Monitor, OTel, Limits, Burn-Rate, Analytics, Hotspots, Notifications | Vollstaendige Run-Traces und Tool-Event-Timeline | Runtime-Tracing fehlt | Mittel |
| LLM-Operations | LLM Command Hub, Copilot-Chat, Run-Listen, Plan-Bezug | Einheitliche Agent-Runtime fuer alle Modelle/Tools | Gemeinsamer Ausfuehrungs-Layer fehlt | Mittel |
| Langlaufende Agent-Jobs | Teilweise ueber manuelle Workflows und externe Tools abbildbar | First-class Jobs mit Queue, Retry, Resume, Timeout, Cancellation | Deutliche Luecke | Schwach |
| Sandbox / Isolation | Operativ durch Umgebung und Tooling, aber nicht als systematischer Run-Container im Produkt | Pro Run isolierte Sandbox, reproduzierbare Umgebung | Deutliche Luecke | Schwach |
| Tool-Permissions | Logische Governance vorhanden | Feingranulare, technisch erzwungene Tool-/Secret-Permissions pro Run | Deutliche Luecke | Schwach |
| Credentials / Secret Brokerage | Nicht als zentrale Agent-Schicht sichtbar | Scoped Secrets je Agent/Run | Deutliche Luecke | Schwach |
| Multi-Agent-Koordination | Konzeptionell ueber Marker/Workflow denkbar | Supervisor/Worker/Delegation als Runtime-Funktion | Deutliche Luecke | Schwach |
| Recovery / Resume | Teilweise ueber Persistenz, Marker, Sessions und Handoffs | Robuste Wiederaufnahme abgebrochener Langlaeufer | Noch nicht systematisch | Mittel bis schwach |

## Was unser Programm heute bereits klar ersetzt

- Ein zentrales Operator-Dashboard fuer agentische Arbeit
- Workflow- und Zustandsmodell fuer Plan -> Marker -> Execution -> Rating
- Governance- und Review-Schicht
- Audit- und Qualitaetssicht
- Multi-Tool-Session-Archivierung
- Nutzungstransparenz und Limitsicht
- Projektbezogene Kontext- und Handoff-Steuerung

## Was Managed Agents uns technisch abnehmen wuerden

- Hosting der Agent-Runtime
- Lifecycle von Langlaeufern
- Queueing, Retry, Cancellation, Resume
- technische Tool- und Secret-Isolation
- tieferes Tracing auf Run-Ebene
- Standardisierung der Ausfuehrungsumgebung

## Was uns konkret noch fehlt, wenn wir das selbst bauen wollten

### 1. Einheitliche Execution Plane

Heute gibt es mehrere Ausfuehrungspfade:

- Copilot-Chat
- LLM Commands
- externe Tool-Sessions, die importiert werden
- Marker-gesteuerte manuelle Execution

Was fehlt, ist ein gemeinsames internes Objekt wie:

- `agent_run`
- `agent_step`
- `tool_call`
- `run_state`
- `run_checkpoint`

Damit koennte jede Ausfuehrung gleich behandelt, wiederaufgenommen und observiert werden.

### 2. Job-/Worker-Schicht

Fuer Managed-Agents-Paritaet wuerde eine robuste Hintergrund-Ausfuehrung fehlen:

- Queue
- Worker
- Heartbeats
- Retry-Policy
- Timeouts
- Cancellation
- Dead-letter / Fehlerklassen

Aktuell ist der Stack eher auf Steuerung und Sichtbarkeit optimiert als auf autonome,
langlaufende, betriebssichere Agent-Ausfuehrung.

### 3. Technisch erzwungene Permissions

Die vorhandene Governance ist fachlich stark, aber nicht dieselbe Kategorie wie:

- dieser Agent darf nur Git lesen
- jener Agent darf nur in ein bestimmtes Repo schreiben
- ein anderer darf kein Netzwerk nutzen
- ein weiterer darf nur mit bestimmten Secrets laufen

Hier fehlt eine technische Enforcement-Schicht.

### 4. Standardisierte Sandbox

Ein Managed-Agent-System kapselt oft jeden Lauf in eine reproduzierbare Umgebung.
Im aktuellen Stack ist der Fokus staerker auf:

- Session-Historie
- Kontextsteuerung
- Workflow
- Analyse

Nicht auf systematisch isolierter Ausfuehrung pro Run.

### 5. Tieferes Runtime-Tracing

Vorhanden sind:

- Session-Daten
- Usage/OTel
- Audit-Ergebnisse
- Notifications
- Hotspots und Analytics

Nicht gleichwertig vorhanden ist eine komplette Timeline pro Agent-Run:

- Prompt
- Modellaufruf
- Tool-Call
- Tool-Result
- Zwischenschritt
- Retry
- Failure Cause
- Resume Point

## Wichtigste Schlussfolgerung

Der aktuelle Stack ist bereits viel naeher an einer eigenen Agent-Plattform als an einem
normalen Projekt-Dashboard. Er ist aber heute vor allem eine gute Control Plane,
nicht vollstaendig eine standardisierte Execution Plane.

Das bedeutet:

- Wenn das Ziel bessere Steuerung, Sichtbarkeit, Governance und Handoffs ist, seid ihr schon weit.
- Wenn das Ziel eine komplett gehostete autonome Agent-Laufzeit ist, fehlt noch substanzielle Infra.

## Build-vs-Buy fuer unseren Fall

### Managed Agents lohnen sich eher, wenn

- wir bewusst Runtime-Betrieb abgeben wollen
- wir schnell zu langlebigen Agent-Jobs mit weniger eigener Infra kommen wollen
- wir technische Permissions, Sandboxing und Run-Tracing nicht selbst bauen wollen
- Time-to-Market wichtiger ist als Kontrolle

### Selbst weiterbauen lohnt sich eher, wenn

- wir Kontrolle ueber Runtime, Kosten und Tooling behalten wollen
- unsere heutige Orchestrierung fachlich bereits gut genug ist
- wir die fehlende Execution Plane gezielt selbst ausbauen koennen
- wir Vendor-Lock-in vermeiden wollen

## Konkrete Empfehlung

Fuer den aktuellen Stand ist die sinnvollste Sicht:

1. Nicht vorschnell Managed Agents einkaufen, nur weil das Label attraktiv klingt.
2. Erst sauber pruefen, ob uns wirklich die Execution Plane fehlt oder nur einzelne operative Komfortfunktionen.
3. Falls wir weiter selbst bauen, dann als naechste Architekturbausteine priorisieren:

- internes `agent_run`-Modell
- Worker-/Queue-Schicht
- Checkpoints / Resume
- technische Tool-/Secret-Permissions
- standardisierte Run-Traces

## Referenz auf den aktuellen Stack

Die Einschaetzung basiert vor allem auf folgenden Repo-Bereichen:

- `app.py`
- `routes/__init__.py`
- `routes/copilot_routes.py`
- `routes/governance_routes.py`
- `routes/audit_routes.py`
- `routes/usage_monitor_routes.py`
- `routes/llm_command_routes.py`
- `services/copilot_marker_service.py`
- `services/session_import.py`
- `services/notification_checker.py`
