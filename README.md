<p align="center">
  <img src="static/favicon.svg" width="80" alt="SessionPilot">
</p>

<h1 align="center">SessionPilot</h1>

<p align="center">
  <strong>Your AI coding sessions deserve a cockpit.</strong><br>
  <em>Deine AI-Coding-Sessions verdienen ein Cockpit.</em>
</p>

<p align="center">
  Self-hosted dashboard to monitor, analyze, and review Claude Code sessions in real-time.<br>
  Track costs, manage projects, and keep your dev infrastructure in check — all in one place.
</p>

<p align="center">
  <a href="https://session-pilot.com">session-pilot.com</a> (coming soon)
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#api">API</a> •
  <a href="#deutsch">Deutsch</a>
</p>

---

## Why SessionPilot?

If you use **Claude Code** daily across multiple projects, you know the pain: sessions scattered across accounts, no cost visibility, no way to review what happened yesterday. SessionPilot solves this by importing your Claude Code JSONL session files into a searchable, browsable, and analyzable web interface.

But it doesn't stop there — it also monitors your Docker containers, scans your project directories, integrates with Gitea, and gives you a unified command center for your entire dev environment.

## Features

### Claude Code Session Management
- **Live Session Viewer** — Browse sessions with full Markdown rendering, syntax-highlighted code blocks, and timestamps per message
- **Smart Message Types** — Distinguishes between User input, Assistant responses, and Tool Results (Bash, Grep, Read, etc.)
- **Table of Contents** — Right sidebar with navigable TOC, numbered user questions as "chapters", scroll tracking
- **Multi-Account Support** — Monitor multiple Claude Code accounts simultaneously
- **Session Reviews** — Rate sessions (OK / Needs Fix / Reverted / Partial), add notes, link review threads across sessions
- **Export** — JSON, Markdown, HTML, XLSX, TXT

### Cost Analysis & Analytics
- **Cost Dashboard** — Estimated API costs by model (Opus, Sonnet, Haiku), project, and time period
- **Token Tracking** — Input/output tokens per session, model, and project
- **Activity Charts** — Daily activity, hourly distribution, weekday heatmap
- **Tool Usage Ranking** — Most-used tools with visual bars and gradient highlights
- **Project Cost Ranking** — Top projects by cost with color-coded tiers
- **AI Timesheets** — Automatic time tracking based on session data

### Project Management
- **Auto-Discovery** — Scans your project directory and detects project types (monorepo, fork, tool, library, etc.)
- **Project Detail** — README rendering, dependencies, Git status, Docker containers per project
- **Sub-Project Detection** — Monorepo support for `apps/`, `packages/`, `services/` directories
- **Project Scaffolding** — Create new projects from templates
- **Relations & Groups** — Manage project dependencies, custom groups, favorites
- **Ideas & Notes** — Capture project-related ideas with categories

### DevOps & Infrastructure
- **Docker Container Dashboard** — Live status with health checks, ports, uptime
- **Dependency Tracker** — Dependencies across all projects (npm, pip, composer, etc.)
- **Gitea Integration** — Repository info, branches, commits via Gitea API
- **Notifications** — Background thread checks every 60s for container issues, sync status, new projects

### Search & Navigation
- **Full-Text Search** — Ripgrep-powered search across all projects with type filters
- **Command Palette** — Ctrl+K quick search across projects, sessions, and documents
- **Document Browser** — Browse, view, edit, and upload files

### Technical
- Flask with modular Blueprint architecture (19 route modules, 18 services)
- PostgreSQL for session data with connection pooling
- JSON file cache with TTL for fast project scans
- Dark theme with design token system
- Responsive layout with collapsible sidebar
- No build step — runs directly, no compilation needed
- Docker & systemd deployment options
- ~8,000 lines of Python

## Screenshots

> Coming soon — or run it yourself and see!

## Quick Start

### Option A: Docker (recommended)

```bash
git clone https://github.com/web-werkstatt/session-pilot.git
cd session-pilot
cp .env.example .env
# Edit .env (set your project path, DB credentials, optional Gitea token)
docker compose up -d
```

Open http://localhost:5055

### Option B: Bare Metal (Linux)

```bash
git clone https://github.com/web-werkstatt/session-pilot.git
cd session-pilot
./setup.sh
```

### Option C: Manual

```bash
git clone https://github.com/web-werkstatt/session-pilot.git
cd session-pilot
pip3 install -r requirements.txt
cp .env.example .env
# Edit .env
python3 app.py
```

## Configuration

All settings via environment variables (`.env` file):

| Variable | Description | Default |
|---|---|---|
| `DASHBOARD_PROJECTS_DIR` | Path to your projects | `/mnt/projects` |
| `DASHBOARD_PORT` | Web server port | `5055` |
| `GITEA_URL` | Gitea server URL | — |
| `GITEA_TOKEN` | Gitea API token | — |
| `GITEA_USER` | Gitea username | — |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `project_dashboard` |
| `DB_USER` | DB user | `autodns` |
| `DB_PASSWORD` | DB password | — |

## Prerequisites

| Component | Required | Used for |
|---|---|---|
| Python 3.9+ | Yes | Application |
| PostgreSQL 14+ | Optional | Claude Code sessions |
| Docker | Optional | Container status monitoring |
| Git | Optional | Git status, commits |
| Gitea | Optional | Remote sync status |
| ripgrep (rg) | Optional | Full-text search |

Without PostgreSQL, everything works except the Sessions feature.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/data` | GET | All project data + stats |
| `/api/containers` | GET | Docker container list |
| `/api/sessions` | GET | Claude Code sessions |
| `/api/sessions/sync` | POST | Import/sync sessions |
| `/api/sessions/analysis` | GET | Cost & usage analytics |
| `/api/sessions/<uuid>` | GET | Session detail with messages |
| `/api/sessions/<uuid>/export` | GET | Export (json/md/html/xlsx/txt) |
| `/api/sessions/<uuid>/outcome` | POST | Set session review status |
| `/api/sessions/<uuid>/reviews` | POST | Add review note |
| `/api/timesheets` | GET | AI timesheet data |
| `/api/info?name=X` | GET | Comprehensive project info |
| `/api/project/<name>` | GET | Load project.json |
| `/api/project/save` | POST | Save project.json |
| `/api/search` | GET | Full-text search |
| `/api/groups` | GET/POST | Manage groups |
| `/api/relations` | GET/POST | Manage relations |
| `/api/ideas` | GET/POST | Manage ideas |
| `/api/notifications` | GET | Notification list |

## Backup

Automatic backup via cron:

```bash
# Daily backup (01:00, 7-day rotation)
scripts/backup.sh daily

# Weekly backup (Sunday 02:00, 4-week rotation)
scripts/backup.sh weekly
```

## Project Structure

```
project_dashboard/
├── app.py                    # Flask entry point
├── config.py                 # Configuration via env vars
├── routes/                   # 19 Blueprint modules
│   ├── session_routes.py     # Session CRUD, detail, export
│   ├── session_analysis_routes.py  # Cost & analytics API
│   ├── data_routes.py        # Main data aggregation
│   ├── project_routes.py     # Project info, save, assets
│   ├── document_routes.py    # Document browser & editor
│   ├── search_routes.py      # Full-text search via ripgrep
│   ├── timesheet_routes.py   # AI timesheets
│   └── ...                   # Groups, ideas, news, etc.
├── services/                 # 18 service classes
│   ├── session_import.py     # JSONL parser for Claude sessions
│   ├── session_export.py     # Multi-format export
│   ├── project_scanner.py    # Auto-discovery & caching
│   ├── project_detector.py   # Type detection (monorepo, fork, etc.)
│   ├── docker_service.py     # Docker container status
│   ├── gitea_service.py      # Gitea API integration
│   └── ...                   # Git, cache, notifications, etc.
├── templates/                # Jinja2 templates
├── static/                   # CSS (design tokens), JS, assets
├── scripts/backup.sh         # Automated backup
├── docker-compose.yml        # Docker deployment
├── setup.sh                  # Bare-metal installer
└── requirements.txt          # Flask, psycopg2, markdown, openpyxl
```

## Roadmap

SessionPilot is actively developed. Here's what's coming next:

| Priority | Feature | Description |
|---|---|---|
| **Next** | **Error Class Tagging** | Categorize *why* sessions need fixes — hallucination, wrong context, missing domain knowledge, edge case, infra problem. Turn reviews into learning curves. |
| **Next** | **Git Diff per Session** | Show which files Claude Code actually changed. Diff view per session — what was generated vs. what survived review. Hard proof of real rework ratio. |
| **Planned** | **CLAUDE.md Effectiveness Tracking** | Version-track prompt files per project. Compare metrics (tokens/session, rework rate) before/after CLAUDE.md updates. |
| **Planned** | **Session Comparison** | Side-by-side comparison of two sessions — same task, different model (Opus vs. Sonnet), different prompt strategy. What worked better? |
| **Planned** | **LLM Model Benchmarking** | "Opus vs. Sonnet: rework rate over time" across all projects. Unique research-grade insights. |
| **Planned** | **Prompt Library** | Extract and rate reusable initial prompts per task type. Build a personal prompt playbook from real session data. |
| **Future** | **Multi-LLM Support** | Extend beyond Claude Code — Codex CLI, Gemini CLI, aider, and other AI coding tools. |
| **Future** | **Team Mode** | Shared dashboard for small teams with role-based views. |

Have an idea? [Open an issue](https://github.com/web-werkstatt/session-pilot/issues) or contribute directly.

## Contributing

Contributions welcome! This project is actively developed and used daily as the author's primary development tool.

## License

MIT

---

<a name="deutsch"></a>

## Deutsch

### Warum SessionPilot?

Wenn Du **Claude Code** taeglich mit mehreren Projekten nutzt, kennst Du das Problem: Sessions ueber verschiedene Accounts verstreut, keine Kostenuebersicht, kein Weg um nachzuvollziehen was gestern passiert ist. SessionPilot loest das, indem es deine Claude Code JSONL-Session-Dateien in eine durchsuchbare, browsbare und analysierbare Weboberflaeche importiert.

Aber das ist nicht alles — es ueberwacht auch Docker-Container, scannt Projektverzeichnisse, integriert sich mit Gitea und gibt dir ein einheitliches Kontrollzentrum fuer deine gesamte Entwicklungsumgebung.

### Features

**Claude Code Session-Verwaltung**
- Live Session Viewer mit Markdown-Rendering, Syntax-Highlighting und Zeitstempel pro Nachricht
- Intelligente Message-Typen: User-Eingaben, Assistant-Antworten und Tool-Results (Bash, Grep, Read etc.)
- Inhaltsverzeichnis-Sidebar mit Scroll-Tracking und nummerierten User-Fragen
- Multi-Account-Support fuer mehrere Claude Code Accounts
- Session-Bewertungen mit Status, Notizen und uebergreifenden Review-Threads
- Export als JSON, Markdown, HTML, XLSX, TXT

**Kosten-Analyse & Statistiken**
- Geschaetzte API-Kosten nach Modell, Projekt und Zeitraum
- Token-Tracking (Input/Output) pro Session und Projekt
- Aktivitaets-Charts, Stunden-Verteilung, Wochentag-Heatmap
- Tool-Nutzungs-Ranking und Projekt-Kostenranking
- AI Timesheets mit automatischer Zeiterfassung

**Projekt-Verwaltung**
- Auto-Discovery: Erkennt Projekttyp, Tech-Stack, Sub-Projekte
- Projekt-Details mit README, Dependencies, Git-Status, Container
- Scaffolding, Gruppen, Favoriten, Beziehungen, Ideen/Notizen

**DevOps & Infrastruktur**
- Docker Container Dashboard mit Health-Checks
- Dependency-Tracker ueber alle Projekte
- Gitea-Integration und Echtzeit-Benachrichtigungen

**Suche & Navigation**
- Volltextsuche via ripgrep ueber alle Projekte
- Ctrl+K Command Palette
- Dokumenten-Browser mit Editor

### Schnellstart

```bash
git clone https://github.com/web-werkstatt/session-pilot.git
cd session-pilot
cp .env.example .env
# .env anpassen (Projektpfad, DB-Zugangsdaten, optional Gitea-Token)
docker compose up -d
```

Dashboard oeffnen: http://localhost:5055

### Konfiguration

Alle Einstellungen via Umgebungsvariablen (`.env`-Datei):

| Variable | Beschreibung | Standard |
|---|---|---|
| `DASHBOARD_PROJECTS_DIR` | Pfad zu deinen Projekten | `/mnt/projects` |
| `DASHBOARD_PORT` | Web-Server Port | `5055` |
| `GITEA_URL` | Gitea Server URL | — |
| `GITEA_TOKEN` | Gitea API-Token | — |
| `DB_HOST` | PostgreSQL Host | `localhost` |
| `DB_NAME` | Datenbankname | `project_dashboard` |
| `DB_USER` | DB-Benutzer | `autodns` |
| `DB_PASSWORD` | DB-Passwort | — |

### Voraussetzungen

| Komponente | Erforderlich | Wofuer |
|---|---|---|
| Python 3.9+ | Ja | Anwendung |
| PostgreSQL 14+ | Optional | Claude Sessions |
| Docker | Optional | Container-Status |
| Git | Optional | Git-Status |
| ripgrep (rg) | Optional | Volltextsuche |

Ohne PostgreSQL funktioniert alles ausser dem Sessions-Feature.
