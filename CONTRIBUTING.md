# Contributing to SessionPilot

Thanks for your interest in contributing! SessionPilot is a self-hosted dashboard for AI coding sessions, and we welcome contributions of all kinds.

## Ways to Contribute

- **Bug reports** — [Open an issue](https://github.com/web-werkstatt/session-pilot/issues/new) with steps to reproduce
- **Feature ideas** — Post in [Discussions > Ideas](https://github.com/web-werkstatt/session-pilot/discussions/categories/ideas)
- **Code contributions** — Fix bugs, add features, improve docs
- **Share your setup** — Post in [Discussions > Show and tell](https://github.com/web-werkstatt/session-pilot/discussions/categories/show-and-tell)

## Development Setup

```bash
git clone https://github.com/web-werkstatt/session-pilot.git
cd session-pilot
pip3 install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python3 app.py
```

Open http://localhost:5055 — the app reloads automatically on code changes during development.

### Prerequisites

- Python 3.9+
- PostgreSQL 14+ (optional, for Sessions features)
- Git, Docker, ripgrep (all optional)

## Project Structure

```
app.py                  # Entry point, registers blueprints
config.py               # Environment-based configuration
routes/                 # Flask blueprints (one per feature)
services/               # Business logic, data access
templates/              # Jinja2 HTML templates
static/css/             # Stylesheets (design tokens + per-page)
static/js/              # Vanilla JS (no framework, no build step)
```

Key patterns:
- **Blueprints** — Each feature is a Flask Blueprint in `routes/`
- **No build step** — Vanilla JS and CSS, loaded directly
- **JSON stores** — Simple features use JSON files (groups, ideas, relations)
- **PostgreSQL** — Sessions, messages, timesheets, plans use the database
- **`api.js`** — Centralized fetch wrapper, use `api.get()` / `api.post()` instead of raw `fetch()`
- **`base.js`** — Shared utilities (`formatDate`, `escapeHtml`, `openModal`, etc.)

## Pull Request Guidelines

### Before you start

1. Check [existing issues](https://github.com/web-werkstatt/session-pilot/issues) and [discussions](https://github.com/web-werkstatt/session-pilot/discussions) to avoid duplicate work
2. For larger changes, open an issue or discussion first to align on the approach

### Code style

- **Python** — Standard Python conventions, no linter enforced. Keep functions short.
- **JavaScript** — Vanilla JS, no frameworks. Use `api.js` for HTTP calls, `base.js` utilities for formatting.
- **CSS** — Use design tokens from `static/css/design-tokens.css`. No hardcoded colors.
- **HTML** — Jinja2 templates extending `base.html`. English UI text.

### What makes a good PR

- **Small and focused** — One feature or fix per PR
- **Tested** — Verify the app starts and your feature works (`python3 app.py`)
- **No unrelated changes** — Don't reformat files you didn't change
- **English** — UI text, commit messages, and PR descriptions in English

### Commit messages

Follow the pattern used in this repo:

```
feat: add usage monitor page with burn rates and predictions
fix: session filter now matches hyphen/underscore variants
docs: update README with cross-platform setup instructions
```

Prefix: `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `chore:`

## Adding a New Page

1. Create `routes/your_feature_routes.py` with a Flask Blueprint
2. Register it in `routes/__init__.py`
3. Create `templates/your_feature.html` extending `base.html`
4. Create `static/css/your-feature.css` and `static/js/your-feature.js`
5. Add a nav link in `templates/base.html`

## Adding Support for a New AI Tool

1. Add a discovery function in `services/account_discovery.py`
2. Add a session parser in `services/session_import_multi.py`
3. The rest (session browser, timesheets, analysis) works automatically

## Questions?

- [Q&A Discussions](https://github.com/web-werkstatt/session-pilot/discussions/categories/q-a)
- [Open an issue](https://github.com/web-werkstatt/session-pilot/issues/new)

Thanks for helping make SessionPilot better!
