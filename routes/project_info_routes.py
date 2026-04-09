"""
Projekt-Info Route: /api/info - Umfassende Projekt-Detailansicht
"""
import os
import json
import html as html_mod
import subprocess
from flask import Blueprint, jsonify, request

from services.path_resolver import resolve_project_path
from services import get_docker_containers
from services.metadata_extractor import (
    extract_version, detect_license, get_repo_size,
    count_lines_of_code, parse_changelog,
)
from services.git_service import get_branches, get_contributors
from services.description_extractor import parse_env_example
from routes.project_info_sections_s3 import add_github_section, add_health_section, add_security_section

project_info_bp = Blueprint('project_info', __name__)


def _escape(text):
    """HTML-Escape fuer sichere Ausgabe"""
    return html_mod.escape(str(text)) if text else ""


def _normalize_description_text(text):
    value = str(text or "").strip()
    if not value:
        return ""
    # Tolerate broken trailing HTML remnants from older project metadata.
    value = value.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    if value.endswith("<br"):
        value = value[:-3].rstrip()
    return value


def _is_meaningful_description(name, text):
    value = _normalize_description_text(text)
    if not value:
        return False

    normalized_name = str(name or "").strip().lower().replace("-", " ").replace("_", " ")
    normalized_value = value.lower().replace("-", " ").replace("_", " ")
    return normalized_value != normalized_name


def _project_action_link(label, tab=None):
    safe_label = _escape(label)
    if not tab:
        return safe_label
    return (
        f"<a href='#' onclick=\"switchProjectTabByName('{_escape(tab)}');return false;\">"
        f"{safe_label}</a>"
    )


def _find_files(project_path, matcher, max_depth=3, limit=8):
    matches = []
    root_depth = project_path.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(project_path):
        current_depth = root.count(os.sep) - root_depth
        if current_depth >= max_depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".venv", "venv"}]
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, project_path)
            if matcher(filename, rel_path):
                matches.append(rel_path)
                if len(matches) >= limit:
                    return matches
    return matches


def _read_quality_summary(project_path):
    report_path = os.path.join(project_path, ".quality", "report.json")
    if not os.path.exists(report_path):
        return None
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    summary = report.get("summary") or {}
    return {
        "score": report.get("score"),
        "score_numeric": report.get("score_numeric"),
        "errors": summary.get("errors", 0),
        "warnings": summary.get("warnings", 0),
        "info": summary.get("info", 0),
    }


def _build_project_signals(name, pj, project_path):
    readme_path = None
    readme_length = 0
    for readme in ["README.md", "readme.md", "Readme.md"]:
        candidate = os.path.join(project_path, readme)
        if os.path.exists(candidate):
            readme_path = readme
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    readme_length = len(f.read().strip())
            except OSError:
                readme_length = 0
            break

    tests = _find_files(
        project_path,
        lambda filename, rel_path: (
            "test" in filename.lower()
            or "spec" in filename.lower()
            or "/tests/" in rel_path.lower().replace("\\", "/")
            or rel_path.lower().startswith("tests/")
        ),
        max_depth=4,
        limit=10,
    )
    ci_files = _find_files(
        project_path,
        lambda filename, rel_path: (
            rel_path.startswith(".github/workflows/")
            or rel_path == ".gitlab-ci.yml"
            or rel_path == ".circleci/config.yml"
            or filename.startswith("Jenkinsfile")
        ),
        max_depth=4,
        limit=6,
    )
    env_examples = _find_files(
        project_path,
        lambda filename, rel_path: filename in {".env.example", ".env.sample", ".env.template"},
        max_depth=4,
        limit=6,
    )
    docs_exists = os.path.isdir(os.path.join(project_path, "docs"))
    subprojects = pj.get("subprojects") if isinstance(pj.get("subprojects"), list) else []
    quality = _read_quality_summary(project_path)
    description_text = _normalize_description_text(pj.get("description"))

    meaningful_sub_descriptions = 0
    for sub in subprojects:
        if _is_meaningful_description(sub.get("name", ""), sub.get("description", "")):
            meaningful_sub_descriptions += 1

    return {
        "project_name": name,
        "is_monorepo": pj.get("project_type") == "monorepo",
        "description_ok": _is_meaningful_description(name, description_text),
        "readme_path": readme_path,
        "readme_length": readme_length,
        "docs_exists": docs_exists,
        "subprojects": subprojects,
        "meaningful_sub_descriptions": meaningful_sub_descriptions,
        "tests": tests,
        "ci_files": ci_files,
        "env_examples": env_examples,
        "quality": quality,
    }


def _render_action_items(items, empty_text):
    if not items:
        return f"<div style='font-size:13px;color:#888;line-height:1.55'>{_escape(empty_text)}</div>"
    rows = "".join(
        f"<div style='display:flex;gap:10px;align-items:flex-start;padding:6px 0;font-size:13px;line-height:1.5'>"
        f"<span style='color:#4fc3f7'>•</span><span>{item}</span></div>"
        for item in items
    )
    return rows


def _add_action_summary_section(sections, name, pj, project_path):
    signals = _build_project_signals(name, pj, project_path)
    quality = signals["quality"] or {}
    good = []
    missing = []
    next_steps = []

    if signals["is_monorepo"] and signals["subprojects"]:
        good.append(
            f"Das Projekt ist als Monorepo erkennbar und hat {len(signals['subprojects'])} sichtbare Teilbereiche."
        )
    if signals["readme_path"] and signals["readme_length"] >= 200:
        good.append(
            f"Es gibt eine brauchbare Einstiegsdoku in <code>{_escape(signals['readme_path'])}</code>."
        )
    if signals["docs_exists"]:
        good.append("Ein eigener <code>docs/</code>-Bereich ist vorhanden.")
    if signals["env_examples"]:
        good.append(
            f"Mindestens ein Konfigurationsbeispiel liegt vor, z. B. <code>{_escape(signals['env_examples'][0])}</code>."
        )
    if quality.get("score_numeric") is not None and quality.get("score_numeric", 0) >= 60:
        good.append(
            f"Es liegt bereits ein Quality-Scan mit {quality.get('score_numeric')}/100 vor."
        )

    if not signals["description_ok"]:
        missing.append("Die Projektbeschreibung ist zu duenn und erklaert den Zweck kaum.")
        next_steps.append(
            f"Die Kurzbeschreibung in <code>project.json</code> schaerfen, damit oben sofort klar ist, was dieses Projekt leistet."
        )
    if signals["is_monorepo"] and signals["subprojects"] and signals["meaningful_sub_descriptions"] == 0:
        missing.append("Die Teilprojekte haben kaum brauchbare Beschreibungen.")
        next_steps.append(
            "Die Eintraege unter <code>project.json.subprojects</code> mit echten Beschreibungen ergaenzen."
        )
    if not signals["readme_path"]:
        missing.append("Es fehlt ein README als schneller Einstieg.")
        next_steps.append(
            f"Im {_project_action_link('Documents-Tab', 'documents')} ein <code>README.md</code> anlegen und Setup, Zweck und Startschritte dokumentieren."
        )
    elif signals["readme_length"] < 200:
        missing.append("Das README ist vorhanden, aber noch zu knapp fuer einen brauchbaren Einstieg.")
        next_steps.append(
            "Das <code>README.md</code> um Zweck, Setup, Start, Architektur und wichtige Befehle erweitern."
        )
    if not signals["tests"]:
        missing.append("Es sind keine erkennbaren Tests oder Spec-Dateien sichtbar.")
        next_steps.append(
            "Mindestens einen ersten Smoke-Test oder API-/UI-Test anlegen, damit Aenderungen pruefbar werden."
        )
    if not signals["ci_files"]:
        missing.append("Es ist keine sichtbare CI-Pipeline konfiguriert.")
        next_steps.append(
            "Eine einfache Pipeline fuer Lint, Tests oder Build unter <code>.github/workflows/</code> oder aequivalent anlegen."
        )
    if quality.get("score_numeric") is None:
        missing.append("Es gibt noch keinen Quality-Scan fuer konkrete technische Baustellen.")
        next_steps.append(
            f"Im {_project_action_link('Quality-Tab', 'quality')} einen Scan starten, um blocker und warnings mit Dateibezug zu sehen."
        )
    elif quality.get("errors", 0) > 0 or quality.get("warnings", 0) > 0:
        missing.append(
            f"Der letzte Quality-Scan meldet {quality.get('errors', 0)} blocker und {quality.get('warnings', 0)} warnings."
        )
        next_steps.append(
            f"Im {_project_action_link('Quality-Tab', 'quality')} die offenen Funde nach Kategorie durchgehen und die betroffenen Dateien priorisieren."
        )

    if not next_steps:
        next_steps.append("Als Naechstes den Quality-Tab und die Struktur pruefen, um konkrete Code- oder Doku-Verbesserungen abzuleiten.")

    cards = [
        (
            "Was Ist Gut",
            "#43a047",
            _render_action_items(good, "Aktuell gibt es noch keine starken positiven Signale ausser der sichtbaren Struktur."),
        ),
        (
            "Was Fehlt",
            "#ffb300",
            _render_action_items(missing, "Aktuell sind keine offensichtlichen Luecken erkannt."),
        ),
        (
            "Was Als Naechstes",
            "#4fc3f7",
            _render_action_items(next_steps, "Noch keine direkten Folgeaktionen erkannt."),
        ),
    ]

    card_html = "".join(
        f"<div style='padding:14px 16px;border:1px solid #2a2a2a;border-radius:10px;background:#141414'>"
        f"<div style='font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:{color};margin-bottom:10px'>{title}</div>"
        f"{body}</div>"
        for title, color, body in cards
    )
    sections.append(
        f"<h3>Was Kann Ich Verbessern?</h3>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px'>{card_html}</div>"
    )


@project_info_bp.route('/api/info')
def get_info():
    """Schnelle Basis-Info: Metadaten, Tech-Stack, Env, Changelog, README, Screenshots, Milestones, Relations"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Name missing"}), 400

    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"description": f"Project '{_escape(name)}' not found.", "source": "", "name": name})

    sections = []

    # project.json Metadaten + schnelle on-demand Berechnung
    pj = _load_project_json(project_path)

    if not pj.get("version"):
        pj["version"] = extract_version(project_path)
    if not pj.get("license"):
        pj["license"] = detect_license(project_path)
    if not pj.get("changelog_latest"):
        pj["changelog_latest"] = parse_changelog(project_path)

    is_monorepo = pj.get("project_type") == "monorepo"

    description_text = _normalize_description_text(pj.get("description"))
    if _is_meaningful_description(name, description_text):
        sections.append(f"<h3>Description</h3><p>{_escape(description_text)}</p>")

    # Schnelle Sections (File I/O only, kein Subprocess/Netzwerk)
    _add_action_summary_section(sections, name, pj, project_path)
    if is_monorepo:
        _add_structure_section(sections, pj, project_path)
        _add_root_assets_section(sections, project_path, compact=True)
        _add_tech_stack_section(sections, project_path, minimum_items=2)
    else:
        _add_metadata_section(sections, pj, project_path)
        _add_structure_section(sections, pj, project_path)
        _add_tech_stack_section(sections, project_path)
        _add_root_assets_section(sections, project_path)
    _add_env_section(sections, project_path)
    _add_changelog_section(sections, pj)
    _add_readme_section(sections, project_path, compact=is_monorepo)
    _add_screenshots_section(sections, name, project_path)
    _add_milestones_section(sections, pj)
    _add_relations_section(sections, name)

    description = "".join(sections) if sections else f"No information found for '{_escape(name)}'."
    return jsonify({"description": description, "source": "project", "name": name})


@project_info_bp.route('/api/info/slow')
def get_info_slow():
    """Teure Sections: Git, LoC, Contributors, Branches, Sessions, Containers, GitHub, Health, Security"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Name missing"}), 400

    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"html": "", "name": name})

    pj = _load_project_json(project_path)

    # Teure on-demand Berechnungen
    if not pj.get("loc_stats"):
        pj["loc_stats"] = count_lines_of_code(project_path)
    if not pj.get("repo_size"):
        pj["repo_size"] = get_repo_size(project_path)

    sections = []

    is_monorepo = pj.get("project_type") == "monorepo"

    # Repo-Groesse als eigene Zeile
    if pj.get("repo_size") and not is_monorepo:
        sections.append(
            f"<h3>Size</h3><p style='font-size:13px'>{_escape(pj['repo_size'])}</p>"
        )
    _add_loc_section(sections, pj, compact=is_monorepo)
    _add_git_section(sections, project_path)
    _add_branches_section(sections, project_path)
    _add_contributors_section(sections, project_path)
    add_github_section(sections, project_path)
    add_health_section(sections, name, pj, project_path)
    add_security_section(sections, name, project_path)
    _add_sessions_section(sections, name)
    _add_containers_section(sections, name)

    return jsonify({"html": "".join(sections), "name": name})


def _load_project_json(project_path):
    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _add_metadata_section(sections, pj, project_path, hide_path=False):
    meta = []
    if pj.get("project_type"):
        meta.append(("Type", _escape(pj["project_type"])))
    if pj.get("group"):
        meta.append(("Group", _escape(pj["group"])))
    if pj.get("priority"):
        icons = {"high": "High", "medium": "Medium", "low": "Low"}
        meta.append(("Priority", _escape(icons.get(pj["priority"], pj["priority"]))))
    if pj.get("deadline"):
        meta.append(("Deadline", _escape(pj["deadline"])))
    if pj.get("progress") is not None:
        meta.append(("Progress", f"{_escape(pj['progress'])}%"))
    if pj.get("version"):
        meta.append(("Version", f"<code style='color:#4fc3f7'>{_escape(pj['version'])}</code>"))
    if pj.get("license"):
        meta.append(("License", _escape(pj["license"])))
    if pj.get("repo_size"):
        meta.append(("Size", _escape(pj["repo_size"])))
    if not hide_path:
        meta.append(("Path", _escape(project_path)))

    if meta:
        rows = "".join(
            f"<tr><td style='color:#888;padding:4px 12px 4px 0'>{k}</td><td style='padding:4px 0'>{v}</td></tr>"
            for k, v in meta
        )
        sections.append(f"<h3>Details</h3><table style='font-size:13px'>{rows}</table>")


def _add_structure_section(sections, pj, project_path):
    subprojects = pj.get("subprojects")
    if not isinstance(subprojects, list) or not subprojects:
        return

    items = []
    for sub in subprojects[:8]:
        name = _escape(sub.get("name", "Subproject"))
        subtype = _escape(sub.get("type", "component"))
        desc = _normalize_description_text(sub.get("description"))
        desc_html = f"<div style='color:#888;font-size:12px;line-height:1.45'>{_escape(desc)}</div>" if desc else ""
        rel_path = _escape(sub.get("path", ""))
        link_target = sub.get("name") or sub.get("path") or ""
        link_html = (
            f"<a href='/project/{html_mod.escape(link_target)}' "
            f"style='color:#4fc3f7;text-decoration:none;font-weight:600'>{name}</a>"
        )
        items.append(
            f"<div style='padding:10px 12px;border:1px solid #2a2a2a;border-radius:8px;background:#151515'>"
            f"<div style='display:flex;justify-content:space-between;gap:10px;align-items:flex-start'>"
            f"<div>{link_html}{desc_html}</div>"
            f"<span style='font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:0.06em'>{subtype}</span></div>"
            f"<div style='margin-top:8px;font-size:11px;color:#666'>{rel_path}</div>"
            f"</div>"
        )

    sections.append(
        f"<h3>Structure</h3>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px'>{''.join(items)}</div>"
    )


def _add_root_assets_section(sections, project_path, compact=False):
    try:
        entries = sorted(os.listdir(project_path))
    except OSError:
        return

    doc_files = []
    key_dirs = []
    priority_files = {"INTEGRATION.md", "CLAUDE.md", "README.md", "README.txt", ".mcp.json"}
    priority_dirs = {"docs", "scripts", "docker", "app", "apps", "packages", "services"}

    for entry in entries:
        full_path = os.path.join(project_path, entry)
        if os.path.isfile(full_path) and entry in priority_files:
            doc_files.append(entry)
        elif os.path.isdir(full_path) and entry in priority_dirs:
            key_dirs.append(entry)

    if not doc_files and not key_dirs:
        return

    blocks = []
    if doc_files:
        docs_html = "".join(
            f"<span style='display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;"
            f"background:#1a1a1a;border:1px solid #2a2a2a;font-size:12px;color:#ddd'>{_escape(name)}</span>"
            for name in doc_files
        )
        blocks.append(f"<div><div style='font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px'>Root Docs</div><div style='display:flex;flex-wrap:wrap;gap:8px'>{docs_html}</div></div>")

    if key_dirs:
        dirs_html = "".join(
            f"<span style='display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;"
            f"background:#141d2b;border:1px solid #22344f;font-size:12px;color:#9ac7ff'>{_escape(name)}/</span>"
            for name in key_dirs
        )
        blocks.append(f"<div><div style='font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px'>Important Paths</div><div style='display:flex;flex-wrap:wrap;gap:8px'>{dirs_html}</div></div>")

    if compact:
        compact_items = []
        compact_items.extend(
            f"<span style='display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;"
            f"background:#1a1a1a;border:1px solid #2a2a2a;font-size:12px;color:#ddd'>{_escape(name)}</span>"
            for name in doc_files
        )
        compact_items.extend(
            f"<span style='display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;"
            f"background:#141d2b;border:1px solid #22344f;font-size:12px;color:#9ac7ff'>{_escape(name)}/</span>"
            for name in key_dirs
        )
        sections.append(
            f"<h3>Quick Entry Points</h3>"
            f"<div style='display:flex;flex-wrap:wrap;gap:8px'>{''.join(compact_items)}</div>"
        )
        return

    sections.append(
        f"<h3>Root Orientation</h3>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px'>{''.join(blocks)}</div>"
    )


def _add_loc_section(sections, pj, compact=False):
    loc = pj.get("loc_stats")
    if not loc or not loc.get("total"):
        return
    if compact and loc.get("total", 0) < 2000:
        return
    total = loc["total"]
    total_display = f"{total:,}".replace(",", ".")
    lang_colors = {
        'Python': '#3572A5', 'JavaScript': '#f1e05a', 'TypeScript': '#3178c6',
        'React JSX': '#61dafb', 'React TSX': '#3178c6', 'Vue': '#41b883',
        'HTML': '#e34c26', 'CSS': '#563d7c', 'SCSS': '#c6538c',
        'PHP': '#4F5D95', 'Go': '#00ADD8', 'Rust': '#dea584',
        'Java': '#b07219', 'Shell': '#89e051', 'SQL': '#e38c00',
    }
    bars_html = ""
    for lang, count in loc.items():
        if lang == 'total':
            continue
        pct = round(count / total * 100, 1)
        color = lang_colors.get(lang, '#888')
        count_display = f"{count:,}".replace(",", ".")
        bars_html += (
            f"<div style='display:flex;align-items:center;gap:8px;padding:2px 0;font-size:12px'>"
            f"<span style='width:90px;color:#ccc'>{_escape(lang)}</span>"
            f"<div style='flex:1;background:#222;border-radius:3px;height:14px;overflow:hidden'>"
            f"<div style='width:{pct}%;background:{color};height:100%;border-radius:3px;min-width:2px'></div></div>"
            f"<span style='width:60px;text-align:right;color:#888'>{count_display}</span>"
            f"<span style='width:40px;text-align:right;color:#666'>{pct}%</span></div>"
        )
    sections.append(
        f"<h3>Code Statistics <span style='font-weight:normal;color:#888;font-size:12px'>"
        f"({total_display} lines)</span></h3>{bars_html}"
    )


def _add_changelog_section(sections, pj):
    cl = pj.get("changelog_latest")
    if not cl:
        return
    version = _escape(cl.get("version", ""))
    date = _escape(cl.get("date", ""))
    summary = _escape(cl.get("summary", ""))
    date_html = f" <span style='color:#666'>({date})</span>" if date else ""
    sections.append(
        f"<h3>Changelog</h3><div style='font-size:13px'>"
        f"<strong>v{version}</strong>{date_html}<br>"
        f"<span style='color:#aaa'>{summary}</span></div>"
    )


def _add_tech_stack_section(sections, project_path, minimum_items=1):
    tech = []
    markers = {
        "package.json": "Node.js", "tsconfig.json": "TypeScript", "next.config": "Next.js",
        "astro.config": "Astro", "nuxt.config": "Nuxt", "vite.config": "Vite",
        "requirements.txt": "Python", "pyproject.toml": "Python", "Pipfile": "Python",
        "app.py": "Flask", "manage.py": "Django", "Cargo.toml": "Rust",
        "go.mod": "Go", "composer.json": "PHP", "Gemfile": "Ruby",
        "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
        "docker-compose.yaml": "Docker Compose", ".env": "Env Config",
        "tailwind.config": "Tailwind CSS", "CLAUDE.md": "Claude Code",
    }
    try:
        for f in os.listdir(project_path):
            for marker, label in markers.items():
                if f.startswith(marker) and label not in tech:
                    tech.append(label)
    except OSError:
        pass
    if len(tech) >= minimum_items:
        badges = " ".join(
            f"<code style='background:#1a3a5c;color:#4fc3f7;padding:2px 8px;border-radius:4px;font-size:12px'>"
            f"{_escape(t)}</code>"
            for t in tech
        )
        sections.append(f"<h3>Tech Stack</h3><p>{badges}</p>")


def _add_git_section(sections, project_path):
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%h|%s|%ar", "-n", "5"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            commits_html = ""
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|', 2)
                    if len(parts) >= 3:
                        commits_html += (
                            f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>"
                            f"<code style='color:#888'>{_escape(parts[0])}</code>"
                            f"<span style='flex:1'>{_escape(parts[1])}</span>"
                            f"<span style='color:#666;font-size:11px'>{_escape(parts[2])}</span></div>"
                        )
            if commits_html:
                sections.append(f"<h3>Recent Commits</h3>{commits_html}")

        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path, capture_output=True, text=True, timeout=3
        )
        if branch.returncode == 0 and branch.stdout.strip():
            sections.append(
                f"<p style='font-size:12px;color:#888'>Branch: <code>{_escape(branch.stdout.strip())}</code></p>"
            )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _add_readme_section(sections, project_path, compact=False):
    for readme in ["README.md", "readme.md", "Readme.md"]:
        rpath = os.path.join(project_path, readme)
        if os.path.exists(rpath):
            try:
                with open(rpath, 'r', encoding='utf-8') as f:
                    content = f.read()[:3000]
                if compact and len(content.strip()) < 120:
                    return
                safe = html_mod.escape(content)
                safe = safe.replace('\n\n', '</p><p>').replace('\n', '<br>')
                sections.append(
                    f"<h3>README</h3><div style='font-size:13px;color:#aaa;max-height:300px;"
                    f"overflow-y:auto;background:#141414;padding:12px;border-radius:6px'><p>{safe}</p></div>"
                )
            except OSError:
                pass
            break


def _add_screenshots_section(sections, name, project_path):
    try:
        screenshots = [
            f"/{name}/{f}" for f in os.listdir(project_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
        ]
        if screenshots:
            imgs = "".join(
                f'<img src="{_escape(s)}" alt="{_escape(os.path.basename(s))}" '
                f'style="max-width:200px;max-height:150px;border-radius:6px;cursor:pointer;margin:4px">'
                for s in screenshots[:6]
            )
            sections.append(f"<h3>Screenshots</h3><div style='display:flex;flex-wrap:wrap;gap:8px'>{imgs}</div>")
    except OSError:
        pass


def _add_milestones_section(sections, pj):
    if pj.get("milestones"):
        ms_html = "".join(
            f"<div style='padding:4px 0;font-size:13px'>"
            f"{'done' if m.get('done') else 'pending'} {_escape(m.get('name', ''))}</div>"
            for m in pj["milestones"]
        )
        sections.append(f"<h3>Milestones</h3>{ms_html}")


def _add_relations_section(sections, name):
    try:
        from routes.relation_routes import load_relations
        rel_data = load_relations()
        outgoing = [r for r in rel_data.get("relations", []) if r.get("source") == name]
        incoming = [r for r in rel_data.get("relations", []) if r.get("target") == name]
        rel_types = {t["id"]: t for t in rel_data.get("relation_types", [])}
        if outgoing or incoming:
            rel_html = ""
            for r in outgoing:
                t = rel_types.get(r.get("type"), {})
                note = f" - {_escape(r.get('note'))}" if r.get('note') else ""
                rel_html += (
                    f"<div style='padding:4px 0;font-size:13px'>"
                    f"{_escape(t.get('icon', 'link'))} {_escape(t.get('name', r.get('type', '')))} -> "
                    f"<strong>{_escape(r.get('target', ''))}</strong>{note}</div>"
                )
            for r in incoming:
                t = rel_types.get(r.get("type"), {})
                note = f" - {_escape(r.get('note'))}" if r.get('note') else ""
                rel_html += (
                    f"<div style='padding:4px 0;font-size:13px'>"
                    f"{_escape(t.get('icon', 'link'))} {_escape(t.get('name', r.get('type', '')))} <- "
                    f"<strong>{_escape(r.get('source', ''))}</strong>{note}</div>"
                )
            sections.append(f"<h3>Relations</h3>{rel_html}")
    except Exception:
        pass


def _add_sessions_section(sections, name):
    try:
        from services.db_service import execute
        sessions = execute(
            """SELECT session_uuid, slug, started_at, duration_ms, model,
                      user_message_count, assistant_message_count, total_input_tokens, total_output_tokens
               FROM sessions WHERE project_name ILIKE %s
               ORDER BY started_at DESC LIMIT 5""",
            (f"%{name.replace('_', '-').replace('proj-', 'proj_')}%",), fetch=True
        )
        if sessions:
            sess_html = ""
            for s in sessions:
                dt = s["started_at"].strftime("%d.%m.%y %H:%M") if s.get("started_at") else "-"
                dur_s = (s.get("duration_ms") or 0) // 1000
                dur = (
                    f"{dur_s // 3600}h {(dur_s % 3600) // 60}m" if dur_s >= 3600
                    else f"{dur_s // 60}m {dur_s % 60}s" if dur_s >= 60
                    else f"{dur_s}s"
                )
                msgs = (s.get("user_message_count") or 0) + (s.get("assistant_message_count") or 0)
                model_short = _escape((s.get('model') or '').replace('claude-', ''))
                sess_html += (
                    f"<a href='/sessions/{s['session_uuid']}' "
                    f"style='display:flex;gap:12px;padding:6px 0;font-size:13px;color:#ccc;text-decoration:none'>"
                    f"<span style='color:#888'>{dt}</span><span>{dur}</span>"
                    f"<span style='color:#888'>{msgs} msgs</span>"
                    f"<span style='color:#666;margin-left:auto'>{model_short}</span></a>"
                )
            sections.append(f"<h3>Claude Sessions</h3>{sess_html}")
    except Exception:
        pass


def _add_containers_section(sections, name):
    try:
        containers = get_docker_containers()
        proj_containers = [
            c for c in containers
            if name.lower().replace('_', '-') in c.get("name", "").lower()
            or name.lower().replace('-', '_') in c.get("name", "").lower()
        ]
        if proj_containers:
            cont_html = ""
            for c in proj_containers:
                status_icon = (
                    "running" if "Running" in c.get("status", "") or "Healthy" in c.get("status", "") else "stopped"
                )
                port = f":{c['port']}" if c.get("port") else ""
                cont_html += (
                    f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>"
                    f"{status_icon} <strong>{_escape(c.get('name', ''))}</strong>"
                    f"<span style='color:#888'>{_escape(c.get('image', ''))}</span>"
                    f"<span style='color:#666'>{_escape(port)}</span></div>"
                )
            sections.append(f"<h3>Container</h3>{cont_html}")
    except Exception:
        pass


def _add_branches_section(sections, project_path):
    """Branch-Uebersicht (Sprint 2)"""
    try:
        branch_data = get_branches(project_path)
        if branch_data["count"] <= 1:
            return
        rows = ""
        for b in branch_data["branches"]:
            current = " <strong>(current)</strong>" if b["is_current"] else ""
            rows += (
                f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>"
                f"<code style='color:#64b5f6'>{_escape(b['name'])}</code>{current}"
                f"<span style='color:#666;margin-left:auto'>{_escape(b.get('last_commit', ''))}</span></div>"
            )
        sections.append(
            f"<h3>Branches <span style='font-weight:normal;color:#888;font-size:12px'>"
            f"({branch_data['count']})</span></h3>{rows}"
        )
    except Exception:
        pass


def _add_contributors_section(sections, project_path):
    """Top Contributors (Sprint 2)"""
    try:
        contributors = get_contributors(project_path)
        if not contributors:
            return
        rows = ""
        for c in contributors:
            rows += (
                f"<div style='display:flex;gap:10px;padding:4px 0;font-size:13px'>"
                f"<strong>{_escape(c['name'])}</strong>"
                f"<span style='color:#888'>{_escape(c['email'])}</span>"
                f"<span style='color:#4caf50;margin-left:auto'>{c['commits']} commits</span></div>"
            )
        sections.append(f"<h3>Contributors</h3>{rows}")
    except Exception:
        pass


def _add_env_section(sections, project_path):
    """Environment-Variablen aus .env.example (Sprint 2)"""
    try:
        env_vars = parse_env_example(project_path)
        if not env_vars:
            return
        badges = ""
        for v in env_vars:
            color = "#1a3a2a" if v["has_default"] else "#3a1a1a"
            text_color = "#4caf50" if v["has_default"] else "#ff8a80"
            title = _escape(v["comment"]) if v["comment"] else ("Has default" if v["has_default"] else "Must be set")
            badges += (
                f"<code style='background:{color};color:{text_color};padding:2px 8px;"
                f"border-radius:4px;font-size:11px;margin:2px' title='{title}'>"
                f"{_escape(v['key'])}</code> "
            )
        sections.append(f"<h3>Environment Variables</h3><p>{badges}</p>")
    except Exception:
        pass
