"""
Projekt-Scaffolding: Erstellt neue Projekte mit Templates,
AI-Instruktionsdateien, Docker-Setup und Git-Integration.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from config import PROJECTS_DIR
from services.instruction_generator import (
    generate_claude_md, generate_agents_md, generate_gemini_md
)

VORLAGEN_DIR = os.path.join(PROJECTS_DIR, "vorlagen")

# Eingebaute Minimal-Templates
BUILTIN_TEMPLATES = {
    "blank": {
        "name": "Blank",
        "description": "Leeres Projekt mit README und project.json",
        "type": None,
        "files": {},
    },
    "python-app": {
        "name": "Python App",
        "description": "Python-Anwendung mit pyproject.toml",
        "type": "app",
        "files": {
            "pyproject.toml": '[project]\nname = "{{name}}"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n\n[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.backends._legacy:_Backend"\n',
            "src/__init__.py": "",
            "tests/__init__.py": "",
            "tests/test_main.py": "def test_placeholder():\n    assert True\n",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\ndist/\n*.egg-info/\n.env\n",
        },
    },
    "python-api": {
        "name": "Python API (FastAPI)",
        "description": "FastAPI Backend mit requirements.txt",
        "type": "service",
        "files": {
            "requirements.txt": "fastapi>=0.115\nuvicorn[standard]\npydantic\n",
            "app.py": 'from fastapi import FastAPI\n\napp = FastAPI(title="{{name}}")\n\n\n@app.get("/health")\ndef health():\n    return {"status": "ok"}\n',
            "tests/__init__.py": "",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\n.env\n",
        },
    },
    "node-app": {
        "name": "Node.js App",
        "description": "Node.js Projekt mit package.json",
        "type": "app",
        "files": {
            "package.json": '{\n  "name": "{{name}}",\n  "version": "0.1.0",\n  "private": true,\n  "scripts": {\n    "dev": "node src/index.js",\n    "test": "echo \\"No tests\\" && exit 0"\n  }\n}\n',
            "src/index.js": 'console.log("{{name}} gestartet");\n',
            ".gitignore": "node_modules/\ndist/\n.env\n",
        },
    },
    "static-site": {
        "name": "Statische Website",
        "description": "HTML/CSS/JS Grundgeruest",
        "type": "app",
        "files": {
            "index.html": '<!DOCTYPE html>\n<html lang="de">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{{name}}</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <h1>{{name}}</h1>\n    <script src="main.js"></script>\n</body>\n</html>\n',
            "style.css": "* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: system-ui, sans-serif; }\n",
            "main.js": '// {{name}}\nconsole.log("Bereit");\n',
            ".gitignore": ".env\nnode_modules/\n",
        },
    },
}


def get_templates():
    """Gibt alle verfuegbaren Templates zurueck (builtin + vorlagen/)"""
    templates = []

    # Eingebaute
    for tid, t in BUILTIN_TEMPLATES.items():
        templates.append({
            "id": tid,
            "name": t["name"],
            "description": t["description"],
            "type": t["type"],
            "source": "builtin",
            "files": list(t["files"].keys()),
        })

    # Vorlagen-Verzeichnis
    if os.path.isdir(VORLAGEN_DIR):
        for entry in sorted(os.listdir(VORLAGEN_DIR)):
            path = os.path.join(VORLAGEN_DIR, entry)
            if not os.path.isdir(path) or entry.startswith("."):
                continue
            files = []
            for root, dirs, fnames in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in fnames:
                    rel = os.path.relpath(os.path.join(root, f), path)
                    files.append(rel)
            templates.append({
                "id": f"vorlagen/{entry}",
                "name": entry,
                "description": f"Vorlage: {entry}",
                "type": None,
                "source": "vorlagen",
                "files": files[:20],
            })

    return templates


def preview_project(config):
    """Vorschau: Welche Dateien wuerden erstellt?"""
    files = ["README.md", "project.json"]

    template_id = config.get("template", "blank")
    if template_id in BUILTIN_TEMPLATES:
        files.extend(BUILTIN_TEMPLATES[template_id]["files"].keys())

    ai_tools = config.get("ai_tools", [])
    if "claude" in ai_tools:
        files.append("CLAUDE.md")
    if "codex" in ai_tools:
        files.append("AGENTS.md")
    if "gemini" in ai_tools:
        files.append("GEMINI.md")

    if config.get("docker"):
        files.extend(["Dockerfile", "docker-compose.yml", ".dockerignore"])

    if config.get("git_init"):
        files.append(".git/")

    return sorted(set(files))


def validate_name(name):
    """Validiert Projektnamen"""
    if not name:
        return "Name ist erforderlich"
    if not re.match(r'^[a-z][a-z0-9_-]*$', name):
        return "Name darf nur Kleinbuchstaben, Zahlen, - und _ enthalten"
    if len(name) > 50:
        return "Name darf maximal 50 Zeichen lang sein"
    project_path = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(project_path):
        return f"Projekt '{name}' existiert bereits"
    return None


def create_project(config):
    """Erstellt ein neues Projekt. Gibt (path, log) zurueck."""
    name = config["name"]
    error = validate_name(name)
    if error:
        raise ValueError(error)

    project_path = os.path.join(PROJECTS_DIR, name)
    description = config.get("description", "")
    project_type = config.get("type", "app")
    template_id = config.get("template", "blank")
    ai_tools = config.get("ai_tools", [])
    log = []

    # 1. Verzeichnis erstellen
    os.makedirs(project_path, exist_ok=True)
    log.append(f"Verzeichnis erstellt: {project_path}")

    # 2. Template-Dateien
    if template_id in BUILTIN_TEMPLATES:
        tmpl = BUILTIN_TEMPLATES[template_id]
        for filepath, content in tmpl["files"].items():
            content = content.replace("{{name}}", name)
            full_path = os.path.join(project_path, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        log.append(f"Template '{template_id}': {len(tmpl['files'])} Dateien")
    elif template_id.startswith("vorlagen/"):
        src = os.path.join(VORLAGEN_DIR, template_id.replace("vorlagen/", ""))
        if os.path.isdir(src):
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(project_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            log.append(f"Vorlage kopiert: {template_id}")

    # 3. README.md
    readme_path = os.path.join(project_path, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w") as f:
            f.write(f"# {name}\n\n{description}\n")
        log.append("README.md erstellt")

    # 4. project.json
    pjson = {
        "schema_version": 2,
        "name": name,
        "description": description,
        "type": project_type,
        "group": config.get("group", ""),
        "priority": "medium",
        "progress": 0,
        "archived": False,
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(project_path, "project.json"), "w") as f:
        json.dump(pjson, f, indent=2, ensure_ascii=False)
    log.append("project.json erstellt")

    # 5. AI-Instruktionsdateien
    generators = {
        "claude": ("CLAUDE.md", generate_claude_md),
        "codex": ("AGENTS.md", generate_agents_md),
        "gemini": ("GEMINI.md", generate_gemini_md),
    }
    for tool in ai_tools:
        if tool in generators:
            filename, gen_fn = generators[tool]
            content = gen_fn(name, description, project_type)
            with open(os.path.join(project_path, filename), "w") as f:
                f.write(content)
            log.append(f"{filename} generiert")

    # 6. Docker-Setup
    if config.get("docker"):
        _generate_docker(project_path, name, project_type)
        log.append("Docker-Setup erstellt")

    # 7. Git initialisieren
    if config.get("git_init"):
        _init_git(project_path)
        log.append("Git initialisiert + Initial Commit")

    # 8. Gitea Repo erstellen
    if config.get("gitea_create"):
        try:
            _create_gitea_repo(name, description, project_path)
            log.append("Gitea Repository erstellt + gepusht")
        except Exception as e:
            log.append(f"Gitea-Fehler: {e}")

    # Cache invalidieren
    from config import CACHE_FILE
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)

    return project_path, log


def _generate_docker(project_path, name, project_type):
    """Generiert Docker-Dateien"""
    dockerfiles = {
        "service": "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD [\"uvicorn\", \"app:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n",
        "app": "FROM node:22-alpine\nWORKDIR /app\nCOPY package*.json .\nRUN npm ci\nCOPY . .\nEXPOSE 3000\nCMD [\"npm\", \"run\", \"dev\"]\n",
    }
    dockerfile = dockerfiles.get(project_type, f"FROM alpine:latest\nWORKDIR /app\nCOPY . .\n")

    with open(os.path.join(project_path, "Dockerfile"), "w") as f:
        f.write(dockerfile)

    compose = f"""services:
  {name}:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    restart: unless-stopped
"""
    with open(os.path.join(project_path, "docker-compose.yml"), "w") as f:
        f.write(compose)

    with open(os.path.join(project_path, ".dockerignore"), "w") as f:
        f.write(".git\nnode_modules\n__pycache__\n.venv\n.env\n")


def _init_git(project_path):
    """Initialisiert Git und erstellt Initial Commit"""
    subprocess.run(["git", "init"], cwd=project_path, capture_output=True, timeout=10)
    subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True, timeout=10)
    subprocess.run(
        ["git", "commit", "-m", "Initial Commit"],
        cwd=project_path, capture_output=True, timeout=10
    )


def _create_gitea_repo(name, description, project_path):
    """Erstellt ein Gitea-Repository und pusht den Code"""
    import ssl
    import urllib.request
    from config import GITEA_URL, GITEA_TOKEN, GITEA_USER

    if not GITEA_TOKEN:
        raise ValueError("GITEA_TOKEN nicht konfiguriert")

    ctx = ssl.create_default_context()
    data = json.dumps({
        "name": name,
        "description": description or "",
        "private": True,
        "auto_init": False,
    }).encode()

    req = urllib.request.Request(
        f"{GITEA_URL}/api/v1/user/repos",
        data=data,
        headers={
            "Authorization": f"token {GITEA_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    urllib.request.urlopen(req, timeout=15, context=ctx)

    # Remote hinzufuegen und pushen
    remote_url = f"{GITEA_URL}/{GITEA_USER}/{name}.git"
    subprocess.run(["git", "remote", "add", "origin", remote_url],
                   cwd=project_path, capture_output=True, timeout=10)
    subprocess.run(["git", "push", "-u", "origin", "main"],
                   cwd=project_path, capture_output=True, timeout=30)
