# claude-task — CLI-Helper fuer den Agent-Orchestrator

Kurzanleitung zum Executor-Handoff (Modell B: Dashboard als Empfaenger).

## Setup

```bash
# Token einmalig anlegen
echo "mein-geheimer-token" > ~/.agent-task-token
chmod 600 ~/.agent-task-token

# Optional: Dashboard-URL konfigurieren (Default: http://localhost:5055)
cat > ~/.agent-task.toml <<'EOF'
[agent_task]
url = "http://localhost:5055"
token = "mein-geheimer-token"
EOF
```

Alternativ via Umgebungsvariablen: `AGENT_TASK_URL`, `AGENT_TASK_TOKEN`.

## Typischer Ablauf

```bash
# 1. Task anlegen (direkt ueber CLI, ohne Marker/UI)
python3 scripts/claude_task.py create \
  --title "README Quickstart" \
  --goal "Fuege einen Quickstart-Abschnitt in README.md hinzu" \
  --allowed README.md
# Antwort enthaelt task_id, z.B. 42

# 2. Prompt herunterladen
python3 scripts/claude_task.py pull 42
# Schreibt .agent-task-42.md ins aktuelle Verzeichnis

# 3. Claude starten, Inhalt von .agent-task-42.md pasten und arbeiten

# 4. Nach dem Run: Execution-Result uebertragen
python3 scripts/claude_task.py finish 42
# Liest automatisch git status + git diff --stat HEAD
# Optionale Notizen: --notes meine-notizen.txt
# Anderer Repo-Pfad: --repo /pfad/zum/repo

# 5. Verify-Gate ausfuehren
python3 scripts/claude_task.py verify 42

# 6. Task schliessen
python3 scripts/claude_task.py close 42
```

### Task an bestehenden Marker haengen (optional)

```bash
python3 scripts/claude_task.py create \
  --title "Fix fuer Marker XY" \
  --marker marker-abc-123 \
  --project 7 \
  --allowed services/x.py --allowed tests/test_x.py
```

## Optionen

| Option | Beschreibung |
|--------|-------------|
| `--url URL` | Dashboard-URL (ueberschreibt Config) |
| `--token TOKEN` | Auth-Token (ueberschreibt Config) |
| `create --title TEXT` | Task-Titel (Pflicht) |
| `create --goal TEXT` | Ziel-Beschreibung (optional) |
| `create --allowed FILE` | Erlaubte Datei (mehrfach verwendbar) |
| `create --mode MODE` | Task-Modus (Default: executor) |
| `create --project ID` | Optional: project_id |
| `create --marker MARKER_ID` | Optional: marker_id zur Verknuepfung |
| `finish --notes FILE` | Notiz-Datei, deren Inhalt als summary gespeichert wird |
| `finish --repo PATH` | Repo-Pfad fuer git-Befehle (Default: CWD) |
| `finish --started ISO8601` | Optional: started_at-Timestamp |
| `finish --finished ISO8601` | Optional: finished_at-Timestamp |
| `close --session ID` | Optionale Session-ID |

## Ohne CLI-Helper

Task-Detail-Seite im Dashboard oeffnen:
- "Prompt kopieren" — kopiert den Prompt in die Zwischenablage
- "Execution-Result pasten" — manuelle Eingabe des JSON-Payloads
