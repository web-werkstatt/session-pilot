"""
Relations/Abhängigkeiten Routes
"""
import os
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template

relation_bp = Blueprint('relations', __name__)

RELATIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'relations.json')

DEFAULT_RELATION_TYPES = [
    {"id": "depends_on", "name": "hängt ab von", "icon": "link", "color": "#3498db"},
    {"id": "replaces", "name": "ersetzt", "icon": "refresh-cw", "color": "#e74c3c"},
    {"id": "extends", "name": "erweitert", "icon": "plus", "color": "#2ecc71"},
    {"id": "uses", "name": "nutzt", "icon": "settings", "color": "#9b59b6"},
    {"id": "related", "name": "verwandt mit", "icon": "git-merge", "color": "#f39c12"},
    {"id": "fork_of", "name": "Fork von", "icon": "git-fork", "color": "#1abc9c"},
]


def load_relations():
    """Lädt die Projekt-Beziehungen"""
    if os.path.exists(RELATIONS_FILE):
        try:
            with open(RELATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"relations": [], "relation_types": list(DEFAULT_RELATION_TYPES)}


def save_relations(data):
    """Speichert die Projekt-Beziehungen"""
    with open(RELATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@relation_bp.route('/dependencies')
def dependencies_page():
    return render_template('dependencies.html', active_page='dependencies')


@relation_bp.route('/api/relations')
def get_relations():
    return jsonify(load_relations())


@relation_bp.route('/api/relations', methods=['POST'])
def add_relation():
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    source = req.get("source")
    target = req.get("target")
    relation_type = req.get("type")
    note = req.get("note", "")

    if not source or not target or not relation_type:
        return jsonify({"error": "source, target und type sind erforderlich"}), 400
    if source == target:
        return jsonify({"error": "Projekt kann nicht mit sich selbst verknüpft werden"}), 400

    data = load_relations()

    for rel in data["relations"]:
        if rel["source"] == source and rel["target"] == target and rel["type"] == relation_type:
            return jsonify({"error": "Diese Beziehung existiert bereits"}), 400

    new_relation = {
        "id": f"{source}_{target}_{relation_type}_{datetime.now().timestamp()}",
        "source": source, "target": target, "type": relation_type,
        "note": note, "created": datetime.now().isoformat()
    }
    data["relations"].append(new_relation)
    save_relations(data)
    return jsonify({"success": True, "relation": new_relation})


@relation_bp.route('/api/relations/<relation_id>', methods=['DELETE'])
def delete_relation(relation_id):
    data = load_relations()
    original_count = len(data["relations"])
    data["relations"] = [r for r in data["relations"] if r.get("id") != relation_id]

    if len(data["relations"]) == original_count:
        return jsonify({"error": "Beziehung nicht gefunden"}), 404

    save_relations(data)
    return jsonify({"success": True})


@relation_bp.route('/api/relations/types')
def get_relation_types():
    data = load_relations()
    return jsonify(data.get("relation_types", []))


@relation_bp.route('/api/relations/types', methods=['POST'])
def add_relation_type():
    req = request.get_json()
    if not req:
        return jsonify({"error": "Keine Daten"}), 400

    type_id = req.get("id", "").lower().replace(" ", "_")
    name = req.get("name")
    icon = req.get("icon", "link")
    color = req.get("color", "#666666")

    if not type_id or not name:
        return jsonify({"error": "id und name sind erforderlich"}), 400

    data = load_relations()
    if any(t["id"] == type_id for t in data["relation_types"]):
        return jsonify({"error": "Dieser Beziehungstyp existiert bereits"}), 400

    new_type = {"id": type_id, "name": name, "icon": icon, "color": color}
    data["relation_types"].append(new_type)
    save_relations(data)
    return jsonify({"success": True, "type": new_type})


@relation_bp.route('/api/project/<path:project_name>/relations')
def get_project_relations(project_name):
    data = load_relations()
    return jsonify({
        "outgoing": [r for r in data["relations"] if r["source"] == project_name],
        "incoming": [r for r in data["relations"] if r["target"] == project_name],
    })
