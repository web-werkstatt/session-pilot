"""
Ideen/Notizen Routes
"""
import os
import json
from datetime import datetime
from flask import Blueprint, jsonify, request

idea_bp = Blueprint('ideas', __name__)

IDEAS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ideas.json')

DEFAULT_CATEGORIES = [
    {"id": "feature", "name": "Feature-Idee", "icon": "💡", "color": "#f1c40f"},
    {"id": "improvement", "name": "Verbesserung", "icon": "🔧", "color": "#3498db"},
    {"id": "bug", "name": "Bug/Problem", "icon": "🐛", "color": "#e74c3c"},
    {"id": "note", "name": "Notiz", "icon": "📝", "color": "#9b59b6"},
    {"id": "research", "name": "Recherche", "icon": "🔍", "color": "#1abc9c"},
    {"id": "question", "name": "Frage", "icon": "❓", "color": "#e67e22"},
]


def load_ideas():
    if os.path.exists(IDEAS_FILE):
        try:
            with open(IDEAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"ideas": [], "categories": list(DEFAULT_CATEGORIES)}


def save_ideas(data):
    with open(IDEAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@idea_bp.route('/api/ideas')
def get_ideas():
    data = load_ideas()
    data["ideas"] = sorted(data["ideas"], key=lambda x: x.get("created", ""), reverse=True)
    return jsonify(data)


@idea_bp.route('/api/ideas', methods=['POST'])
def add_idea():
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    title = req.get("title", "").strip()
    if not title:
        return jsonify({"error": "Titel ist erforderlich"}), 400

    data = load_ideas()
    new_idea = {
        "id": f"idea_{datetime.now().timestamp()}",
        "title": title,
        "content": req.get("content", "").strip(),
        "category": req.get("category", "note"),
        "project": req.get("project"),
        "priority": req.get("priority", "normal"),
        "status": "open",
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }
    data["ideas"].append(new_idea)
    save_ideas(data)
    return jsonify({"success": True, "idea": new_idea})


@idea_bp.route('/api/ideas/<idea_id>', methods=['PUT'])
def update_idea(idea_id):
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    data = load_ideas()
    for idea in data["ideas"]:
        if idea["id"] == idea_id:
            for field in ('title', 'content', 'category', 'project', 'priority', 'status'):
                if field in req:
                    idea[field] = req[field]
            idea["updated"] = datetime.now().isoformat()
            save_ideas(data)
            return jsonify({"success": True, "idea": idea})

    return jsonify({"error": "Idee nicht gefunden"}), 404


@idea_bp.route('/api/ideas/<idea_id>', methods=['DELETE'])
def delete_idea(idea_id):
    data = load_ideas()
    original_count = len(data["ideas"])
    data["ideas"] = [i for i in data["ideas"] if i.get("id") != idea_id]

    if len(data["ideas"]) == original_count:
        return jsonify({"error": "Idee nicht gefunden"}), 404

    save_ideas(data)
    return jsonify({"success": True})


@idea_bp.route('/api/ideas/categories')
def get_idea_categories():
    data = load_ideas()
    return jsonify(data.get("categories", []))
