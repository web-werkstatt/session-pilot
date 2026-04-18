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
# 1. Task im Dashboard anlegen (UI oder API), dann ID merken, z.B. 42

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

## Optionen

| Option | Beschreibung |
|--------|-------------|
| `--url URL` | Dashboard-URL (ueberschreibt Config) |
| `--token TOKEN` | Auth-Token (ueberschreibt Config) |
| `finish --notes FILE` | Notiz-Datei, deren Inhalt als notes_text gespeichert wird |
| `finish --repo PATH` | Repo-Pfad fuer git-Befehle (Default: CWD) |
| `close --session ID` | Optionale Session-ID |

## Ohne CLI-Helper

Task-Detail-Seite im Dashboard oeffnen:
- "Prompt kopieren" — kopiert den Prompt in die Zwischenablage
- "Execution-Result pasten" — manuelle Eingabe des JSON-Payloads
