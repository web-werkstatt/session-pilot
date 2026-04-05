#!/usr/bin/env python3
"""
Projekt-Dashboard: Web-GUI für Projekt- und Container-Übersicht
Modulare Version mit Blueprint-Routing
"""
import sys
import os
import json
import time

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# .env-Datei laden (falls vorhanden und python-dotenv nicht installiert)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())

from flask import Flask, render_template, jsonify, request
from config import HOST, PORT

app = Flask(__name__)
app.jinja_env.globals['cache_bust'] = int(time.time())

# Alle Blueprints registrieren
from routes import register_blueprints
register_blueprints(app)

# Notification Checker starten (Background-Thread)
from services.notification_checker import start_checker
start_checker()

# Projekt-Scan im Hintergrund starten (Daten sind bereit wenn User Dashboard oeffnet)
from routes.data_routes import init_background_scan
init_background_scan()

# Favoriten
FAVORITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'favorites.json')


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_favorites(favs):
    with open(FAVORITES_FILE, 'w') as f:
        json.dump(favs, f)


@app.route('/api/favorites')
def get_favorites():
    return jsonify(load_favorites())


@app.route('/api/favorites', methods=['POST'])
def toggle_favorite():
    data = request.get_json()
    name = data.get('name', '')
    if not name:
        return jsonify({"error": "Name fehlt"}), 400
    favs = load_favorites()
    if name in favs:
        favs.remove(name)
        action = "removed"
    else:
        favs.append(name)
        action = "added"
    save_favorites(favs)
    return jsonify({"success": True, "action": action, "favorites": favs})


@app.route('/')
def index():
    dashboard_tab = request.args.get('tab', 'projects').strip().lower()
    if dashboard_tab not in ('projects', 'widgets', 'gitea'):
        dashboard_tab = 'projects'
    return render_template('index.html', active_page='dashboard', dashboard_tab=dashboard_tab)


@app.route('/containers')
def containers():
    return render_template('containers.html', active_page='containers')


if __name__ == '__main__':
    print(f"Projekt-Dashboard startet auf http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
