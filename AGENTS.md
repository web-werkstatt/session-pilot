# Repository Guidelines

## Project Structure & Module Organization
`app.py` is the Flask entrypoint, loads `.env`, registers blueprints, and starts the notification checker. Keep HTTP handlers in `routes/*_routes.py` and reusable logic in `services/*.py`. Rendered pages live in `templates/`; browser assets are split across `static/js/` and `static/css/`. Root JSON files such as `groups.json`, `relations.json`, `ideas.json`, `favorites.json`, and `notifications.json` are lightweight data stores. Operational files live in `scripts/`, `systemd/`, and the Docker files at repo root.

## Architecture & Repo Workflow
Follow the existing Blueprint architecture: add endpoints in the appropriate route module and register them through `routes/__init__.py`. Do not build project paths manually; use `services/path_resolver.py` helpers so monorepos and sub-projects resolve correctly. Keep Git, Docker, Gitea, search, and session logic in `services/` rather than route files. Preserve the repo handoff process by updating `next-session.md` after meaningful changes.

## Build, Test, and Development Commands
Install dependencies with `pip3 install -r requirements.txt`. Run locally with `python3 app.py`; the app serves on `DASHBOARD_PORT` from `.env` and defaults to `5055`. Use `./setup.sh` for bare-metal setup, or `docker compose up -d` to start the app and PostgreSQL together. Production runs as the `project-dashboard` systemd service; inspect runtime issues with `tail -f /mnt/projects/project_dashboard/dashboard.log`.

## Coding Style & Naming Conventions
Use 4-space indentation in Python, snake_case for modules, functions, and variables, and keep route files focused by feature. Match the current frontend style in `static/js/`: plain functions, `var`, and small feature-specific files rather than framework abstractions. Name new route modules `*_routes.py`, keep template and asset names aligned by page or feature, and prefer small service functions over duplicated route logic.

## Testing Guidelines
There is no committed automated test, lint, or build pipeline yet. Before opening a PR, run the affected flow locally, hit the changed endpoint, and review `dashboard.log` for regressions. If you add tests, prefer `pytest`, place them in `tests/test_<feature>.py`, and keep fixtures file-based and minimal.

## Commit, PR, and Data Safety Guidelines
Recent history uses short imperative subjects such as `Feature: ...`, `Refactoring: ...`, and `Dokumentation: ...`. PRs should include a summary, impacted routes/services, linked issue if available, and screenshots for template or CSS changes. Never commit `.env` secrets, and treat JSON store files as user data: preserve keys, make format changes explicit, and document new storage expectations in `README.md`.

## Sprint Documentation
After completing a Sprint or meaningful feature work, always document in BOTH files:
1. **sprints/master-plan-2026-04-01.md** — Add/update Sprint entry under "Completed Sprints" with: Sprint name, goal, changes, files modified, and commit hash
2. **next-session.md** — Update "Was in dieser Session fertig wurde" section with the work summary, and add open items to "Naechste Session" if any
