# Agent-Orchestrator Hardening — Technical Spec

Stand: 2026-04-17
Bezug:
- `sprints/sprint-agent-orchestrator-hardening.md`
- `docs/managed-agents-gap-analysis.md`

## Ziel

Diese Datei konkretisiert den Sprint
`sprints/sprint-agent-orchestrator-hardening.md` auf technischer Ebene.

Sie definiert:

- Kernobjekte
- Zustandsmodell
- API-Shape
- Validierungsregeln
- minimale Persistenzobjekte
- Integrationspunkte im bestehenden Programm

Die Datei ist bewusst auf den aktuellen Stack zugeschnitten und setzt auf den
bereits vorhandenen Control-Plane-Bausteinen auf, statt ein neues System
parallel zu entwerfen.

## 1. Kernidee

Heute steuert das Programm Arbeit fachlich schon gut, vertraut aber operativ
noch zu stark auf:

- Prompt-Disziplin
- manuelle Reviews
- freie Textbehauptungen wie „verifiziert“ oder „fertig“

Kuenftig soll jeder Agentenlauf technisch durch diese Schichten gehen:

1. `task_contract`
2. `preflight_result`
3. `session_state`
4. `execution_result`
5. `verify_gate_result`
6. `close_decision`

## 2. Kernobjekte

### 2.1 `agent_task_contract`

Beschreibt den konkreten Arbeitsauftrag fuer einen Executor.

```json
{
  "task_id": "tsk_20260417_001",
  "session_id": "ses_123",
  "title": "Fix recursive scanner smoke test",
  "goal": "Add exactly one real test for project_recursive discovery",
  "allowed_files": [
    "tests/test_plan_discovery.py"
  ],
  "forbidden_actions": [
    "git",
    "delete_file",
    "rename_file"
  ],
  "required_verification": [
    {
      "type": "command_exit_zero",
      "command": "pytest tests/test_plan_discovery.py -k recursive -q"
    }
  ],
  "required_outputs": [
    {
      "type": "diff_contains",
      "path": "tests/test_plan_discovery.py"
    }
  ],
  "stop_conditions": [
    "scope_violation",
    "dirty_worktree_conflict",
    "missing_dependency"
  ],
  "mode": "executor"
}
```

#### Felder

| Feld | Typ | Zweck |
|---|---|---|
| `task_id` | string | stabile Task-ID |
| `session_id` | string | Zuordnung zur Session |
| `title` | string | Kurzlabel fuer UI |
| `goal` | string | fachliches Ziel |
| `allowed_files` | string[] | einzige erlaubte Write-Scope-Dateien |
| `forbidden_actions` | string[] | verbotene Aktionskategorien |
| `required_verification` | object[] | verpflichtende Nachweise |
| `required_outputs` | object[] | erwartete Artefakte / Diffs |
| `stop_conditions` | string[] | harte Abbruchgruende |
| `mode` | enum | `executor`, `reviewer`, `recovery` |

### 2.2 `agent_session_state`

Beschreibt, in welcher Arbeitsphase sich die Session gerade befindet.

```json
{
  "session_id": "ses_123",
  "state": "verify",
  "previous_state": "implement",
  "reason": "executor_changes_complete",
  "updated_at": "2026-04-17T18:30:00Z",
  "locked": false,
  "blocking_issues": []
}
```

#### Erlaubte `state`-Werte

- `inspect`
- `implement`
- `verify`
- `document`
- `done`
- `recovery`

#### Erlaubte Uebergaenge

| Von | Nach |
|---|---|
| `inspect` | `implement`, `recovery` |
| `implement` | `verify`, `recovery` |
| `verify` | `document`, `implement`, `recovery` |
| `document` | `done`, `implement`, `recovery` |
| `done` | - |
| `recovery` | `inspect`, `verify` |

Nicht erlaubt:

- `implement -> done`
- `inspect -> done`
- `recovery -> done`

### 2.3 `preflight_result`

Maschinenlesbarer Sicherheitscheck vor jeder Executor-Ausfuehrung.

```json
{
  "task_id": "tsk_20260417_001",
  "ok": false,
  "branch": "main",
  "dirty_worktree": true,
  "untracked_files": [
    "tests/test_plan_discovery.py"
  ],
  "modified_files": [
    "next-session.md",
    "tests/test_plan_discovery.py"
  ],
  "out_of_scope_files": [
    "next-session.md"
  ],
  "risk_flags": [
    "dirty_worktree",
    "scope_violation"
  ],
  "blocking_reason": "out_of_scope_files_present"
}
```

#### Mindestpruefungen

- Branch ermitteln
- `git status --short`
- untracked Dateien
- modifizierte Dateien
- modifizierte Dateien ausserhalb `allowed_files`
- sensitive Dateien beruehrt?
  - `next-session.md`
  - `handoff.md`
  - `sprints/master-plan-2026-04-01.md`

### 2.4 `execution_result`

Erfasst das rohe Ergebnis der Agentenarbeit.

```json
{
  "task_id": "tsk_20260417_001",
  "agent": "claude_code",
  "started_at": "2026-04-17T18:35:00Z",
  "finished_at": "2026-04-17T18:42:00Z",
  "changed_files": [
    "tests/test_plan_discovery.py"
  ],
  "created_files": [],
  "deleted_files": [],
  "claims": [
    {
      "type": "test_added",
      "value": true
    },
    {
      "type": "smoke_test_done",
      "value": false
    }
  ],
  "summary": "Added one executable recursive scanner test"
}
```

### 2.5 `verify_gate_result`

Prueft, ob die Claims und Pflichtnachweise wirklich belegt sind.

```json
{
  "task_id": "tsk_20260417_001",
  "status": "blocked",
  "checks": [
    {
      "type": "scope_enforcement",
      "status": "pass",
      "details": "all changed files within allowed_files"
    },
    {
      "type": "required_verification",
      "status": "fail",
      "details": "pytest command not executed"
    }
  ],
  "unverified_claims": [
    "test_added"
  ],
  "next_state": "implement"
}
```

#### `status`-Werte

- `pass`
- `blocked`
- `fail`

#### Regel

`done` ist nur erlaubt, wenn `verify_gate_result.status == "pass"`.

### 2.6 `close_decision`

Letzte Entscheidung, ob ein Task wirklich abgeschlossen werden darf.

```json
{
  "task_id": "tsk_20260417_001",
  "can_close": false,
  "reason": "verification_missing",
  "required_actions": [
    "run pytest command",
    "attach output"
  ]
}
```

## 3. Claim-Modell

Damit das Programm Agenten-Behauptungen nicht blind glaubt, werden Claims in
eine kleine feste Typologie ueberfuehrt.

### Claim-Typen v1

- `test_added`
- `tests_passed`
- `syntax_check_passed`
- `smoke_test_done`
- `append_only_respected`
- `docs_updated`
- `feature_complete`

### Zuordnung zu Belegen

| Claim | Erforderlicher Nachweis |
|---|---|
| `test_added` | Diff + ausführbarer Testpfad |
| `tests_passed` | Test-Command + Exit-Code 0 + Output |
| `syntax_check_passed` | Command + Exit-Code 0 |
| `smoke_test_done` | API-/UI-/DB-Nachweis mit konkretem Ergebnis |
| `append_only_respected` | Diff-Regelpruefung |
| `docs_updated` | Diff auf erlaubter Datei/Sektion |
| `feature_complete` | alle Pflicht-Checks `pass` |

## 4. Doku-Gates

### 4.1 `next-session.md`

Regel v1:

- nur definierte Update-Bloecke anhaengen
- keine stillen Umschreibungen historischer Session-Abschnitte

Technische Pruefung v1:

- Datei darf waehrend Doku-Task geaendert werden
- Diff darf nur Additionen am Ende oder in definierten Update-Abschnitten
  enthalten

### 4.2 `sprints/master-plan-2026-04-01.md`

Regel v1:

- append-only fuer neue Sprint-Eintraege / Korrektur-Hinweise
- keine breitflaechige Umschreibung historischer Ueberschriften

Technische Pruefung v1:

- wenn >N bestehende Zeilen veraendert statt nur neu angehaengt werden,
  Gate = `blocked`

### 4.3 `handoff.md`

Regel v1:

- nur in expliziten Handoff-/Mirror-Kontexten aenderbar
- bei allgemeinem Code-Task standardmaessig nicht im Scope

## 5. Recovery-Mode

### Trigger fuer `recovery`

- dirty worktree + riskanter Task
- Scope-Verletzung an sensitiver Datei
- Git-/Cleanup-Aktion in verbotener Phase
- unbeabsichtigte Massen-Aenderungen

### Verhalten in `recovery`

- keine normalen Executor-Writes
- keine destruktiven Git-Aktionen
- Snapshot:
  - `git status --short`
  - relevante Diffs
  - untracked files
- naechster Schritt nur:
  - sichern
  - vergleichen
  - wiederherstellen

## 6. API-Shape v1

Diese Endpunkte muessen nicht sofort so existieren, bilden aber das
Zielmodell fuer das Programm.

### `POST /api/agent-tasks`

Erzeugt einen strukturierten Task-Contract.

```json
{
  "title": "Fix smoke test",
  "goal": "Add one executable recursive scanner test",
  "allowed_files": ["tests/test_plan_discovery.py"],
  "forbidden_actions": ["git", "delete_file", "rename_file"],
  "required_verification": [
    {"type": "command_exit_zero", "command": "pytest ..."}
  ]
}
```

### `POST /api/agent-tasks/<id>/preflight`

Fuehrt den Preflight aus und liefert `preflight_result`.

### `POST /api/agent-tasks/<id>/verify`

Fuehrt die Verify-Gates gegen aktuelle Diffs / Outputs aus.

### `POST /api/agent-tasks/<id>/close`

Schliesst nur, wenn `verify_gate_result.status == pass`.

### `POST /api/agent-sessions/<id>/recover`

Versetzt eine Session explizit in `recovery`.

## 7. Persistenz v1

Falls der Stack das in DB statt nur im Arbeitsspeicher halten soll, reichen
zunaechst schlanke Tabellen.

### Tabelle `agent_task_contracts`

| Feld | Typ |
|---|---|
| id | UUID / SERIAL |
| session_id | VARCHAR |
| title | TEXT |
| goal | TEXT |
| mode | VARCHAR(20) |
| allowed_files_json | JSONB |
| forbidden_actions_json | JSONB |
| required_verification_json | JSONB |
| required_outputs_json | JSONB |
| stop_conditions_json | JSONB |
| created_at | TIMESTAMP |

### Tabelle `agent_session_states`

| Feld | Typ |
|---|---|
| session_id | VARCHAR PRIMARY KEY |
| state | VARCHAR(20) |
| previous_state | VARCHAR(20) |
| reason | TEXT |
| locked | BOOLEAN |
| blocking_issues_json | JSONB |
| updated_at | TIMESTAMP |

### Tabelle `agent_verify_results`

| Feld | Typ |
|---|---|
| id | UUID / SERIAL |
| task_id | FK |
| status | VARCHAR(20) |
| checks_json | JSONB |
| unverified_claims_json | JSONB |
| created_at | TIMESTAMP |

## 8. Integrationspunkte im bestehenden Programm

### Bestehende Bereiche, die wiederverwendet werden sollen

- Workflow-/Control-Plane-Denken aus:
  - `sprints/workflow-control-plane-loop.md`
  - `sprints/sprint-cp-control-plane-loop-closure.md`
- Contract-Denken aus:
  - `sprints/sprint-cp-workflow-loop-contracts.md`
- Handoff-Disziplin aus:
  - `next-session.md`
  - `AGENTS.md`
- Observability-/Governance-Bausteine aus:
  - `docs/managed-agents-gap-analysis.md`

### Erwartete Produktintegration

1. Task anlegen
2. Preflight ausfuehren
3. State `inspect -> implement`
4. Executor arbeitet
5. Verify-Gate
6. optional `document`
7. Close oder `recovery`

## 9. MVP-Reihenfolge

### Phase 1

- `task_contract`
- `preflight_result`
- `agent_session_state`

### Phase 2

- `verify_gate_result`
- Claim-Nachweislogik
- Close-Gate

### Phase 3

- Doku-Gates
- Recovery-Mode

## 10. Akzeptanz fuer diese Technical Spec

Diese Spec ist ausreichend, wenn ein Implementierer daraus ohne neue
Produktentscheidungen mindestens Folgendes bauen kann:

- Session-State-Maschine
- Task-Contract-Objekt
- Preflight-Gate
- Verify-Gate
- Doku-Gates fuer Schluesseldateien
- Recovery-Flow
