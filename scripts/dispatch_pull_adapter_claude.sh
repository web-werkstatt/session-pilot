#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# ADR-002 Stufe 2a, Commit 7: Claude Code Pull-Adapter
#
# Wrapper um dispatch_pull_adapter.py fuer Claude Code.
# Holt ein Assignment, fuehrt es mit `claude --print` aus und
# meldet das Ergebnis zurueck.
#
# Voraussetzungen:
#   - Claude Code CLI installiert und im PATH
#   - DISPATCH_API_KEY gesetzt
#   - Python 3 verfuegbar
#
# Usage:
#   export DISPATCH_API_KEY=<dein-key>
#   ./dispatch_pull_adapter_claude.sh                # One-Shot (fuer Cron)
#   ./dispatch_pull_adapter_claude.sh --daemon       # Daemon-Modus
#   ./dispatch_pull_adapter_claude.sh --poll 120     # Custom Poll-Intervall
#
# Cron-Beispiel (alle 5 Minuten):
#   */5 * * * * DISPATCH_API_KEY=... /pfad/dispatch_pull_adapter_claude.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER="$SCRIPT_DIR/dispatch_pull_adapter.py"

# Defaults (ueberschreibbar via Env)
export DISPATCH_API_URL="${DISPATCH_API_URL:-http://localhost:5055}"
export DISPATCH_TOOL_ID="${DISPATCH_TOOL_ID:-claude_code}"
export DISPATCH_EXECUTE="${DISPATCH_EXECUTE:-1}"
export DISPATCH_CLI_CMD="${DISPATCH_CLI_CMD:-claude --print}"

# Argument-Parsing
DAEMON=0
POLL_SEC="${DISPATCH_POLL_SEC:-60}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --daemon)
            DAEMON=1
            shift
            ;;
        --poll)
            POLL_SEC="$2"
            shift 2
            ;;
        --tool)
            export DISPATCH_TOOL_ID="$2"
            shift 2
            ;;
        --url)
            export DISPATCH_API_URL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--daemon] [--poll SECONDS] [--tool TOOL_ID] [--url API_URL]"
            echo ""
            echo "Options:"
            echo "  --daemon       Laeuft als Daemon mit Poll-Intervall"
            echo "  --poll SEC     Poll-Intervall in Sekunden (Default: 60)"
            echo "  --tool ID      Tool-ID (Default: claude_code)"
            echo "  --url URL      Dashboard-URL (Default: http://localhost:5055)"
            echo ""
            echo "Environment:"
            echo "  DISPATCH_API_KEY     Bearer-Token (Pflicht)"
            echo "  DISPATCH_API_URL     Dashboard-URL"
            echo "  DISPATCH_TOOL_ID     Tool-ID"
            echo "  DISPATCH_CLI_CMD     CLI-Kommando (Default: claude --print)"
            echo "  DISPATCH_POLL_SEC    Poll-Intervall"
            exit 0
            ;;
        *)
            echo "Unbekanntes Argument: $1" >&2
            exit 1
            ;;
    esac
done

# Pre-Flight Checks
if [[ -z "${DISPATCH_API_KEY:-}" ]]; then
    echo "FEHLER: DISPATCH_API_KEY nicht gesetzt." >&2
    exit 1
fi

if ! command -v claude &>/dev/null; then
    echo "WARNUNG: 'claude' CLI nicht im PATH. Dry-Run Modus moeglich." >&2
fi

if [[ ! -f "$ADAPTER" ]]; then
    echo "FEHLER: Adapter-Script nicht gefunden: $ADAPTER" >&2
    exit 1
fi

# Export Poll-Konfiguration
export DISPATCH_POLL_SEC="$POLL_SEC"

if [[ "$DAEMON" -eq 1 ]]; then
    echo "Claude Dispatch-Adapter gestartet (Daemon, Poll: ${POLL_SEC}s)"
    export DISPATCH_ONE_SHOT=0
    exec python3 "$ADAPTER"
else
    # One-Shot Modus (fuer Cron)
    export DISPATCH_ONE_SHOT=1
    python3 "$ADAPTER"
fi
