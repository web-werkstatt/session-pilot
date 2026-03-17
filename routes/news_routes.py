"""
News und Vorlagen Routes
"""
import os
import json
import subprocess
from datetime import datetime
from flask import Blueprint, jsonify, render_template

from config import PROJECTS_DIR
from services import scan_projects

news_bp = Blueprint('news', __name__)


@news_bp.route('/news')
def news_page():
    return render_template('news.html', active_page='news')


@news_bp.route('/vorlagen')
def vorlagen_page():
    return render_template('vorlagen.html', active_page='vorlagen')


@news_bp.route('/api/vorlagen')
def get_vorlagen():
    """Listet alle verfügbaren Vorlagen"""
    vorlagen_dir = os.path.join(PROJECTS_DIR, 'vorlagen')
    vorlagen = []

    if os.path.isdir(vorlagen_dir):
        for item in os.listdir(vorlagen_dir):
            item_path = os.path.join(vorlagen_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                vorlage = {
                    "name": item,
                    "path": f"/mnt/projects/vorlagen/{item}",
                    "files": [], "readme": None, "preview": None
                }
                try:
                    for f in os.listdir(item_path):
                        if not f.startswith('.'):
                            vorlage["files"].append(f)
                            if f.lower() == 'readme.md':
                                try:
                                    with open(os.path.join(item_path, f), 'r') as rf:
                                        vorlage["readme"] = rf.read()
                                except OSError:
                                    pass
                            if f.endswith('.html'):
                                vorlage["preview"] = f
                except OSError:
                    pass
                vorlagen.append(vorlage)

    return jsonify({"vorlagen": vorlagen, "total": len(vorlagen), "path": vorlagen_dir})


@news_bp.route('/api/news')
def get_news():
    """Sammelt aktuelle Neuigkeiten aus allen Projekten"""
    projects = scan_projects(auto_generate=False)

    news_items = []
    now = datetime.now()

    for proj_name, proj_info in projects.items():
        # Letzte Commits als News
        if proj_info.get("last_commit"):
            try:
                commit_date = datetime.strptime(proj_info["last_commit"][:16], "%Y-%m-%d %H:%M")
                days_ago = (now - commit_date).days
                if days_ago <= 7:
                    news_items.append({
                        "type": "commit", "project": proj_name,
                        "title": f"Commit in {proj_name}",
                        "message": proj_info.get("last_commit_msg", ""),
                        "date": proj_info["last_commit"],
                        "days_ago": days_ago, "icon": "git-commit"
                    })
            except (ValueError, TypeError):
                pass

        # Letzte Dateiänderungen
        if proj_info.get("last_file_change"):
            try:
                change_date = datetime.strptime(proj_info["last_file_change"], "%Y-%m-%d %H:%M")
                days_ago = (now - change_date).days
                if days_ago <= 3:
                    news_items.append({
                        "type": "file_change", "project": proj_name,
                        "title": f"Dateien geändert in {proj_name}",
                        "message": f"Letzte Änderung: {proj_info['last_file_change']}",
                        "date": proj_info["last_file_change"],
                        "days_ago": days_ago, "icon": "file-edit"
                    })
            except (ValueError, TypeError):
                pass

        # Neue Projekte
        project_json_path = os.path.join(PROJECTS_DIR, proj_name, "project.json")
        if proj_info.get("project_type") == "project" and os.path.exists(project_json_path):
            try:
                mtime = os.path.getmtime(project_json_path)
                create_date = datetime.fromtimestamp(mtime)
                days_ago = (now - create_date).days
                if days_ago <= 1:
                    news_items.append({
                        "type": "new_project", "project": proj_name,
                        "title": f"Neues Projekt: {proj_name}",
                        "message": proj_info.get("function", "Keine Beschreibung"),
                        "date": create_date.strftime("%Y-%m-%d %H:%M"),
                        "days_ago": days_ago, "icon": "folder-plus"
                    })
            except OSError:
                pass

        # Sync-Status Probleme
        if proj_info.get("sync_status") == "differs":
            news_items.append({
                "type": "sync_warning", "project": proj_name,
                "title": f"Sync-Konflikt: {proj_name}",
                "message": "Lokale und Remote-Version unterscheiden sich",
                "date": now.strftime("%Y-%m-%d %H:%M"),
                "days_ago": 0, "icon": "alert-triangle"
            })

    news_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return jsonify({
        "news": news_items[:50],
        "headlines": news_items[:5],
        "total": len(news_items),
        "timestamp": now.strftime("%d.%m.%Y %H:%M:%S")
    })


@news_bp.route('/api/news/detail/<project>')
def get_news_detail(project):
    """Holt detaillierte News-Informationen für ein Projekt"""
    project_path = os.path.join(PROJECTS_DIR, project)
    if not os.path.isdir(project_path):
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    details = {
        "project": project, "path": project_path,
        "commits": [], "recent_files": [],
        "project_info": {}, "git_status": None
    }

    json_path = os.path.join(project_path, "project.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                details["project_info"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Letzte 5 Commits
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%H|%s|%an|%ar", "-n", "5"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line and '|' in line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        details["commits"].append({
                            "sha": parts[0][:8], "message": parts[1],
                            "author": parts[2], "when": parts[3]
                        })
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Git Status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            details["git_status"] = {
                "clean": len(changes) == 0,
                "changes": len(changes),
                "modified": len([c for c in changes if c.startswith(' M') or c.startswith('M ')]),
                "untracked": len([c for c in changes if c.startswith('??')]),
                "staged": len([c for c in changes if c.startswith('A ') or c.startswith('M ')])
            }
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Kürzlich geänderte Dateien
    try:
        result = subprocess.run(
            ["find", ".", "-type", "f", "-mtime", "-3", "-not", "-path", "./.git/*",
             "-not", "-name", "*.pyc", "-not", "-path", "./node_modules/*",
             "-not", "-path", "./__pycache__/*"],
            cwd=project_path, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            files = [f.lstrip('./') for f in result.stdout.strip().split('\n') if f and f != '.']
            file_times = []
            for f in files[:20]:
                try:
                    full_path = os.path.join(project_path, f)
                    mtime = os.path.getmtime(full_path)
                    file_times.append((f, mtime))
                except OSError:
                    pass
            file_times.sort(key=lambda x: x[1], reverse=True)
            details["recent_files"] = [
                {"name": f[0], "modified": datetime.fromtimestamp(f[1]).strftime("%d.%m.%Y %H:%M")}
                for f in file_times[:10]
            ]
    except (OSError, subprocess.TimeoutExpired):
        pass

    return jsonify(details)
