# Sprint 4: Self-Service Scaffolding

**Ziel:** Neue Projekte direkt aus dem Dashboard anlegen mit Template, CLAUDE.md,
Docker-Setup und project.json. Internal Developer Portal Pattern.
**Abhaengigkeit:** Keine (unabhaengig von Sprint 1-3)
**Geschaetzter Umfang:** 1 Session

---

## Aufgaben

### 4.1 Service: Projekt-Scaffolding (`services/scaffolding_service.py`)

**Template-Registry:**
- Vorlagen aus `/mnt/projects/vorlagen/` lesen (bereits vorhanden)
- Zusaetzlich: Eingebaute Minimal-Templates fuer gaengige Typen
- Template-Metadaten: Name, Beschreibung, Typ, enthaltene Dateien

**Scaffold-Funktion: `create_project(config) -> path`**
- Parameter:
  - `name`: Projektname (wird zu Verzeichnisname)
  - `template`: Template-ID oder "blank"
  - `type`: app/service/tool/library
  - `group`: Gruppen-Zuordnung
  - `description`: Kurzbeschreibung
  - `ai_tools`: Liste von AI-Tools (claude/codex/gemini)
  - `docker`: Boolean - Docker-Setup generieren
  - `git_init`: Boolean - Git initialisieren
  - `gitea_create`: Boolean - Gitea Repo erstellen

**Ablauf:**
1. Verzeichnis unter `/mnt/projects/{name}` erstellen
2. Template-Dateien kopieren (wenn gewaehlt)
3. `project.json` generieren mit Metadaten
4. AI-Instruktionsdateien generieren:
   - `CLAUDE.md` (wenn claude in ai_tools)
   - `AGENTS.md` (wenn codex in ai_tools)
   - `GEMINI.md` (wenn gemini in ai_tools)
5. Docker-Dateien generieren (wenn docker=true):
   - `Dockerfile` (passend zum Typ)
   - `docker-compose.yml`
   - `.dockerignore`
6. Git initialisieren + Initial Commit (wenn git_init=true)
7. Gitea Repo erstellen + Push (wenn gitea_create=true)

### 4.2 Service: AI-Instruktions-Generator (`services/instruction_generator.py`)

**CLAUDE.md Generator:**
- Projekt-Typ-spezifische Basis-Struktur
- Sections: Projekt, Befehle, Architektur, Patterns
- Automatisch befuellt aus Template-Infos und Typ

**AGENTS.md Generator (Codex):**
- Codex-spezifisches Format
- Verzeichnis-Layout, Build-Commands, Test-Commands

**GEMINI.md Generator:**
- Gemini CLI Format
- Projekt-Kontext und Konventionen

### 4.3 Backend: Scaffold-API (`routes/scaffold_routes.py`)

**GET `/api/scaffold/templates`**
- Liste verfuegbarer Templates mit Metadaten
- Eingebaute + Vorlagen-Verzeichnis

**POST `/api/scaffold/create`**
- Body: Scaffold-Konfiguration (siehe 4.1)
- Erstellt Projekt, gibt Pfad und Status zurueck
- Validierung: Name-Konflikte, erlaubte Zeichen

**POST `/api/scaffold/preview`**
- Gleiche Config wie create, aber nur Vorschau
- Zeigt welche Dateien erstellt wuerden
- Kein Dateisystem-Zugriff

### 4.4 Frontend: "Neues Projekt" Dialog

**Button im Dashboard:**
- "+ Neues Projekt" Button in der Topbar oder Sidebar

**Modal/Seite mit Wizard-Schritten:**

**Schritt 1: Grundlagen**
- Projektname (Input, Validierung: lowercase, keine Leerzeichen)
- Beschreibung (Textarea)
- Typ (Dropdown: app/service/tool/library)
- Gruppe (Dropdown aus bestehenden Gruppen)

**Schritt 2: Template**
- Template-Karten mit Vorschau
- "Blank" Option fuer leeres Projekt
- Template-Details aufklappbar (Dateiliste)

**Schritt 3: AI & DevOps**
- Checkboxen: Claude Code / Codex / Gemini CLI
- Toggle: Docker-Setup generieren
- Toggle: Git initialisieren
- Toggle: Gitea Repository erstellen

**Schritt 4: Vorschau & Erstellen**
- Datei-Baum der zu erstellenden Dateien
- CLAUDE.md Vorschau
- "Projekt erstellen" Button
- Fortschrittsanzeige waehrend Erstellung

**Ergebnis:**
- Erfolgsmeldung mit Link zum neuen Projekt
- Automatischer Redirect zur Projekt-Detail-Seite

### 4.5 Integration

- Neues Projekt erscheint sofort im Dashboard (Cache invalidieren)
- project.json wird beim Erstellen geschrieben
- Gitea-Repo wird via bestehender `gitea_service.py` erstellt

---

## Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `services/scaffolding_service.py` | NEU | Projekt-Erstellung |
| `services/instruction_generator.py` | NEU | AI-Instruktionsdateien |
| `routes/scaffold_routes.py` | NEU | Scaffold-API |
| `templates/scaffold.html` | NEU | Wizard-UI (oder Modal) |
| `static/js/scaffold.js` | NEU | Wizard-Logik |
| `routes/__init__.py` | EDIT | Blueprint registrieren |
| `templates/base.html` | EDIT | Button in Navigation |

---

## Eingebaute Minimal-Templates

| Template-ID | Typ | Inhalt |
|-------------|-----|--------|
| `blank` | - | Nur project.json + README.md |
| `python-app` | app | pyproject.toml, src/, tests/, .gitignore |
| `python-api` | service | FastAPI Skeleton, requirements.txt |
| `node-app` | app | package.json, src/, .gitignore |
| `astro-site` | app | Astro Skeleton mit Tailwind |
| `static-site` | app | HTML/CSS/JS Grundgeruest |

---

## Akzeptanzkriterien

- [x] "Neues Projekt" Link in Sidebar sichtbar
- [x] 4-Schritt Wizard (Grundlagen, Template, AI/DevOps, Vorschau)
- [x] Projekt wird korrekt angelegt mit allen gewaehlten Dateien
- [x] CLAUDE.md/AGENTS.md/GEMINI.md typ-spezifisch generiert
- [x] Docker-Setup wird optional erstellt (Dockerfile, docker-compose, .dockerignore)
- [x] Git wird initialisiert mit Initial Commit
- [x] Gitea-Repo wird optional erstellt + gepusht
- [x] Neues Projekt erscheint sofort im Dashboard (Cache invalidiert)
- [x] Vorschau zeigt Dateibaum vor Erstellung
- [x] 8 Templates (5 builtin + 3 Vorlagen)
