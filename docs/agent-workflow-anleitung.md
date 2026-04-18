# Agent-Orchestrator: Anwender-Anleitung

> Stand: 2026-04-18 — Sprint Workflow-Finalization Session 3.
> Zielgruppe: Personen, die einen Agent-Run (z.B. Claude Code, Codex)
> kontrolliert ueber das Dashboard fahren wollen.

Der Agent-Orchestrator deckt fuenf Workflow-Schritte ab:

```
create  ->  pull  ->  finish  ->  verify  ->  close
```

Du kannst den Workflow komplett per CLI (`claude-task`) oder gemischt mit
der UI fahren. Beide Wege sind aequivalent; der CLI-Pfad ist
reproduzierbar (Smoke-Script), der UI-Pfad zeigt Status und Ergebnis
visuell im Cockpit.

---

## Setup (einmalig)

### 1. Token anlegen

Der Agent-Orchestrator nutzt einen Shared-Secret-Header
`X-Agent-Task-Token`. Token als erste Zeile in `~/.agent-task-token`:

```bash
openssl rand -hex 16 > ~/.agent-task-token
chmod 600 ~/.agent-task-token
```

Optional: Konfiguration in `~/.agent-task.toml` ablegen, damit URL und
Token zentral gepflegt sind:

```toml
[agent_task]
url   = "http://localhost:5055"
token = "DEIN_TOKEN"
```

Prioritaet beim Lesen: Env-Variable (`AGENT_TASK_URL`,
`AGENT_TASK_TOKEN`) > `~/.agent-task.toml` > `~/.agent-task-token` >
Default `http://localhost:5055`.

### 2. CLI verfuegbar machen

```bash
# Direkt aufrufen:
python3 /mnt/projects/project_dashboard/scripts/claude_task.py --help

# Optional: alias in ~/.bashrc
alias claude-task="python3 /mnt/projects/project_dashboard/scripts/claude_task.py"
```

### 3. Dashboard erreichbar?

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5055/agent-tasks
# erwartet: HTTP 200
```

---

## Schritt 1 — Task anlegen (`create`)

Du beschreibst Ziel, erlaubte Dateien und optional Marker/Project. Der
Server vergibt eine `task_id`.

### CLI

```bash
claude-task create \
  --title "Fix CSS in plan_detail.html" \
  --goal  "Padding der Subtasks anpassen, keine Logik aendern" \
  --allowed templates/plan_detail.html \
  --allowed static/css/plans.css
```

Antwort:

```
Task 17 angelegt: Fix CSS in plan_detail.html
Erlaubte Dateien:
  - templates/plan_detail.html
  - static/css/plans.css

Naechster Schritt: claude-task pull 17
```

### UI

1. `/agent-tasks` -> Schaltflaeche **„Refresh"** (Liste aktualisieren)
2. Aus dem Cockpit (`/copilot`) -> Workflow-Ring-Card oeffnet das
   Handoff-Modal -> Reiter „Neuer Task" (sofern Marker hinterlegt)

### Failure-Faelle

| Symptom | Ursache | Fix |
|---|---|---|
| `HTTP 401` | Token fehlt / falsch | `~/.agent-task-token` kontrollieren, `AGENT_TASK_TOKEN` setzen |
| `HTTP 400 title darf nicht leer sein` | Pflichtfeld fehlt | `--title` setzen |
| `Verbindung abgelehnt` | Dashboard down | `sudo systemctl status project-dashboard` |

---

## Schritt 2 — Prompt fuer den Agenten holen (`pull`)

Der Server rendert einen Prompt mit acht Abschnitten (Titel, Ziel,
erlaubte Dateien, verbotene Aktionen, Nachweise, Stop-Bedingungen,
Handoff-Kontext, Abschluss-Protokoll).

### CLI

```bash
claude-task pull 17
# Schreibt .agent-task-17.md ins aktuelle Verzeichnis
```

Den Inhalt von `.agent-task-17.md` paste in deine Claude-Code-Session
oder uebergib ihn dem Agenten deiner Wahl.

### UI

`/agent-tasks` -> Zeile des Tasks anklicken -> **„Prompt kopieren"** im
Modal. Der Browser legt den Markdown-Prompt in die Zwischenablage; ein
Toast bestaetigt den Kopiervorgang.

### Failure-Faelle

| Symptom | Ursache | Fix |
|---|---|---|
| `Task <id> nicht gefunden (HTTP 404)` | Task-ID falsch | mit `claude-task` Liste pruefen oder UI nutzen |
| Clipboard wird nicht beschrieben | Browser ohne `navigator.clipboard` | Markdown-Block in der Modal-Vorschau manuell markieren + Strg+C |

---

## Schritt 3 — Execution-Result eintragen (`finish`)

Nach dem Agent-Run sammelst du Aenderungsstatus + Diff und meldest sie
zurueck. Pro Task ist genau **ein** Execution-Result erlaubt.

### CLI

```bash
cd /mnt/projects/project_dashboard
claude-task finish 17 --notes /tmp/run-17.md
# Sammelt git status --porcelain + git diff --stat HEAD
# Berechnet out_of_scope_files anhand der allowed_files
```

Zusaetzliche Flags:

* `--repo PATH` — Repo-Pfad, falls nicht im aktuellen Verzeichnis
* `--started ISO8601` / `--finished ISO8601` — Timestamps protokollieren

### UI

Im Handoff-Modal (Cockpit oder `/agent-tasks`):

1. Reiter „Schritt 2: Execution melden" oeffnen
2. Felder ausfuellen (`changed_files`, `summary`, optional
   `diff_stat_text`) und „Senden" klicken
3. Toast „Execution gespeichert" bestaetigt den 201er

### Failure-Faelle

| Symptom | Ursache | Fix |
|---|---|---|
| `409 execution_already_recorded` (mit `existing_execution_id`) | Zweites `finish` auf denselben Task | Kein erneutes `finish` noetig, weiter mit `verify` |
| Out-of-Scope-Warnung | Du hast Dateien geaendert, die nicht in `allowed_files` stehen | Aenderungen rueckgaengig machen oder Task mit angepasstem Scope neu anlegen |
| `socket.timeout` | Dashboard ueberlastet/abgestuerzt | systemd-Status pruefen, Logs (`tail -f dashboard.log`) |

---

## Schritt 4 — Verify-Gate (`verify`)

Der Server prueft `scope_enforcement` plus alle `required_verification`
des Task-Contracts (z.B. `command_exit_zero`, `smoke_test_evidence`,
`append_only_diff`, `docs_updated`).

### CLI

```bash
claude-task verify 17
# Verify-Gate: PASS (Task 17)
```

Bei FAIL listet die CLI die `failed_claims`.

### UI

Im Handoff-Modal erscheint nach `finish` der Block „Schritt 3: Verify &
Close". Klick auf **„Verify jetzt"** triggert den Gate-Run; PASS / FAIL
und die Claims werden im selben Modal angezeigt.

### Failure-Faelle

| Symptom | Ursache | Fix |
|---|---|---|
| `Task <id> nicht gefunden (kein Execution-Result?)` | `finish` wurde uebersprungen | Erst `finish` aufrufen |
| `status=blocked` mit `tests_passed` blocked | `command_runner` nicht uebergeben (Server-Default) | Test-Run lokal nachweisen, Result via API mit `claims=[…]` ergaenzen |
| `status=fail` mit `out_of_scope_files` | `changed_files` ausserhalb `allowed_files` | Aenderungen wegnehmen oder Scope erweitern und neu starten |

---

## Schritt 5 — Task schliessen (`close`)

Close ist nur erlaubt, wenn der Verify-Gate `pass` liefert.

### CLI

```bash
claude-task close 17
# Task 17 erfolgreich geschlossen.
```

Optional `--session SESSION_ID` setzt zusaetzlich den Session-State auf
`done`.

### UI

Der Close-Button im Handoff-Modal ist deaktiviert, solange der
Verify-Status nicht `pass` ist. Nach Klick wird der `decision.reason`
inline angezeigt — etwa `verify_pass` (gruener Toast) oder bei 409
`verify_not_pass` / `verification_missing`.

### Failure-Faelle

| Symptom | Ursache | Fix |
|---|---|---|
| `Task X kann nicht geschlossen werden (409): verification_missing` | Verify wurde nicht aufgerufen | `verify` ausfuehren |
| `Task X kann nicht geschlossen werden (409): verify_not_pass` | Verify endete mit fail/blocked | Ursachen beheben, `finish` ist NICHT wiederholbar — neuen Task mit korrektem Scope anlegen |

---

## Reproduzierbarer Smoke-Run

`scripts/e2e_smoke.py` fuehrt alle fuenf Schritte automatisiert gegen
ein laufendes Dashboard durch und prueft zusaetzlich die HTML-Listen-
und JSON-API-Sicht. Exit 0 bedeutet PASS aller 17 Pruefpunkte.

```bash
python3 scripts/e2e_smoke.py
# AGENT_TASK_URL und AGENT_TASK_TOKEN per env oder ~/.agent-task-token
```

Nutzung im CI-Setup (sobald CI eingerichtet wird): Smoke nach jedem
Restart des Dashboards laufen lassen, um Regressionen sofort zu
erkennen.

---

## Limitierungen (Stand 2026-04-18)

* **Nicht fuer autonome Runs gedacht.** Der Workflow erwartet, dass ein
  Mensch oder ein anderes Skript `finish` mit dem realen Diff aufruft.
  Es gibt keinen Auto-Pull oder Auto-Verify-Loop.
* **Ein Execution-Result pro Task.** Wer iterieren will, legt einen
  neuen Task an. Das ist bewusst, um Audit-Spuren klar zu halten.
* **Token-Rotation manuell.** Es gibt keine Subscription-Verwaltung
  oder Session-basierte Token. Token-Tausch erfordert
  `~/.agent-task-token` neu schreiben + Service-Restart, falls auch der
  Server-Cache-Eintrag betroffen ist.
* **Marker-Bindung optional.** `--marker` und `--project` sind
  Komfort-Felder, nicht Pflicht.

---

## Verwandte Dokumente

* Sprint mit Akzeptanzkriterien:
  `sprints/sprint-agent-orchestrator-workflow-finalization.md`
* CLI-Kurzreferenz: `scripts/README-claude-task.md`
* Technische Spezifikation:
  `docs/agent-orchestrator-hardening-technical-spec.md`
