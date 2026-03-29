"""
Auto-Discovery fuer AI Coding Assistant Accounts.
Erkennt automatisch installierte Assistenten und deren Session-Verzeichnisse.

Unterstuetzte Assistenten:
- Claude Code (~/.claude, ~/.claude-*)
- OpenAI Codex CLI (~/.codex)
- Google Gemini CLI (~/.gemini)
- GitHub Copilot CLI (~/.copilot)
- Amazon Q Developer CLI (~/.aws/amazonq)

Cross-platform: uses os.path.expanduser("~") which resolves to:
- Linux/macOS: /home/user or /Users/user
- Windows: C:\\Users\\user
"""
import os
import sys
import glob

# Bekannte Verzeichnisse die KEINE Accounts sind
CLAUDE_IGNORE = {
    ".claude-local", ".claude-code-router", ".claude-monitor", ".claude-squad"
}


def discover_claude_accounts(home_dir):
    """Findet alle Claude Code Account-Verzeichnisse mit Session-Daten"""
    accounts = []
    pattern = os.path.join(home_dir, ".claude*")

    for path in sorted(glob.glob(pattern)):
        if not os.path.isdir(path):
            continue
        basename = os.path.basename(path)
        if basename in CLAUDE_IGNORE:
            continue
        projects_dir = os.path.join(path, "projects")
        if not os.path.isdir(projects_dir):
            continue
        # Hat JSONL-Dateien?
        has_sessions = any(
            f.endswith(".jsonl")
            for p in os.listdir(projects_dir)
            if os.path.isdir(os.path.join(projects_dir, p))
            for f in os.listdir(os.path.join(projects_dir, p))
        )
        if not has_sessions:
            continue

        # Account-Name ableiten
        if basename == ".claude":
            name = "claude"
        else:
            name = basename.replace(".claude-", "").replace(".claude", "claude")

        accounts.append({
            "name": name,
            "tool": "claude",
            "config_dir": path,
            "session_format": "jsonl",
        })

    return accounts


def discover_codex_accounts(home_dir):
    """Findet OpenAI Codex CLI Sessions"""
    codex_dir = os.path.join(home_dir, ".codex")
    if not os.path.isdir(codex_dir):
        return []

    # Codex speichert Sessions in sessions/YYYY/MM/DD/*.jsonl
    sessions_dir = os.path.join(codex_dir, "sessions")
    if not os.path.isdir(sessions_dir):
        return []

    return [{
        "name": "codex",
        "tool": "codex",
        "config_dir": codex_dir,
        "session_format": "codex_jsonl",
    }]


def discover_gemini_accounts(home_dir):
    """Findet Google Gemini CLI Sessions"""
    gemini_dir = os.path.join(home_dir, ".gemini")
    if not os.path.isdir(gemini_dir):
        return []

    tmp_dir = os.path.join(gemini_dir, "tmp")
    if not os.path.isdir(tmp_dir):
        return []

    # Pruefen ob es Projekt-Hashes mit logs.json gibt
    has_logs = any(
        os.path.isfile(os.path.join(tmp_dir, d, "logs.json"))
        for d in os.listdir(tmp_dir)
        if os.path.isdir(os.path.join(tmp_dir, d))
    )
    if not has_logs:
        return []

    return [{
        "name": "gemini",
        "tool": "gemini",
        "config_dir": gemini_dir,
        "session_format": "gemini_json",
    }]


def discover_copilot_accounts(home_dir):
    """Findet GitHub Copilot CLI Sessions"""
    copilot_dir = os.path.join(home_dir, ".copilot")
    if not os.path.isdir(copilot_dir):
        return []

    # Copilot speichert Sessions in session-state/ oder history-session-state/
    has_sessions = (
        os.path.isdir(os.path.join(copilot_dir, "session-state")) or
        os.path.isdir(os.path.join(copilot_dir, "history-session-state"))
    )
    if not has_sessions:
        return []

    return [{
        "name": "copilot",
        "tool": "copilot",
        "config_dir": copilot_dir,
        "session_format": "copilot_json",
    }]


def discover_amazonq_accounts(home_dir):
    """Findet Amazon Q Developer CLI Sessions"""
    q_dir = os.path.join(home_dir, ".aws", "amazonq")
    if not os.path.isdir(q_dir):
        return []

    history_dir = os.path.join(q_dir, "history")
    if not os.path.isdir(history_dir):
        return []

    return [{
        "name": "amazonq",
        "tool": "amazonq",
        "config_dir": q_dir,
        "session_format": "amazonq_json",
    }]


def _get_home_dirs():
    """Returns list of home directories to search for AI accounts.
    On Windows, also checks APPDATA and LOCALAPPDATA."""
    dirs = [os.path.expanduser("~")]
    if sys.platform == "win32":
        for var in ("APPDATA", "LOCALAPPDATA"):
            p = os.environ.get(var)
            if p and p not in dirs:
                dirs.append(p)
    return dirs


def discover_all_accounts():
    """Entdeckt alle AI Coding Assistenten auf dem System.
    Returns: Liste von Account-Dicts mit name, tool, config_dir, session_format
    """
    accounts = []
    seen_dirs = set()

    for home_dir in _get_home_dirs():
        for discover_fn in (discover_claude_accounts, discover_codex_accounts,
                            discover_gemini_accounts, discover_copilot_accounts,
                            discover_amazonq_accounts):
            for acc in discover_fn(home_dir):
                if acc["config_dir"] not in seen_dirs:
                    seen_dirs.add(acc["config_dir"])
                    accounts.append(acc)

    return accounts


if __name__ == "__main__":
    print("AI Coding Assistant Auto-Discovery")
    print("=" * 50)
    for acc in discover_all_accounts():
        print(f"  {acc['name']:20s} [{acc['tool']}] -> {acc['config_dir']}")
