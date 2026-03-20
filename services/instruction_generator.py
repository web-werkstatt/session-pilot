"""
Generator fuer AI-Instruktionsdateien (CLAUDE.md, AGENTS.md, GEMINI.md).
Erstellt typ-spezifische Basis-Konfigurationen fuer neue Projekte.
"""


def generate_claude_md(name, description, project_type, **kwargs):
    """Generiert CLAUDE.md fuer ein neues Projekt"""
    commands = _commands_for_type(project_type)
    return f"""# CLAUDE.md

## Projekt

{description or f'{name} - {project_type}'}

## Befehle

```bash
{commands}
```

## Architektur

{_architecture_hint(project_type)}

## Wichtige Patterns

- Keine externen Dependencies ohne Absprache
- Tests vor Merge
- Commits auf Deutsch
"""


def generate_agents_md(name, description, project_type, **kwargs):
    """Generiert AGENTS.md fuer OpenAI Codex"""
    commands = _commands_for_type(project_type)
    return f"""# AGENTS.md

## Repository: {name}

{description or f'{name} - {project_type}'}

## Directory Layout

Siehe Verzeichnisstruktur im Root.

## Build & Test

```bash
{commands}
```

## Conventions

- Sprache: Deutsch fuer Kommentare und Commits
- Code-Stil: Bestehende Patterns beibehalten
"""


def generate_gemini_md(name, description, project_type, **kwargs):
    """Generiert GEMINI.md fuer Google Gemini CLI"""
    return f"""# GEMINI.md

## Projekt: {name}

{description or f'{name} - {project_type}'}

## Konventionen

- Sprache: Deutsch
- Commits: Aussagekraeftige Messages auf Deutsch
- Keine Breaking Changes ohne Absprache
"""


def _commands_for_type(project_type):
    """Gibt typische Befehle fuer einen Projekttyp zurueck"""
    commands = {
        "app": "# Entwicklung\nnpm run dev\n\n# Build\nnpm run build\n\n# Tests\nnpm test",
        "service": "# Entwicklung\npython3 -m uvicorn app:app --reload\n\n# Tests\npytest",
        "tool": "# Ausfuehren\npython3 main.py\n\n# Tests\npytest",
        "library": "# Tests\npytest\n\n# Build\npython3 -m build",
    }
    return commands.get(project_type, "# TODO: Befehle ergaenzen")


def _architecture_hint(project_type):
    """Gibt Architektur-Hinweis fuer einen Projekttyp zurueck"""
    hints = {
        "app": "Frontend-Anwendung. Einstiegspunkt: `src/` oder `app/`.",
        "service": "Backend-Service/API. Einstiegspunkt: `app.py` oder `main.py`.",
        "tool": "CLI-Tool oder Script. Einstiegspunkt: `main.py`.",
        "library": "Wiederverwendbare Library. Public API in `src/`.",
    }
    return hints.get(project_type, "Projektstruktur noch zu definieren.")
