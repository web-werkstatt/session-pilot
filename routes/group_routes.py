"""
Gruppen-Verwaltung Routes
"""
import os
import re
import json
from flask import Blueprint, jsonify, request

group_bp = Blueprint('groups', __name__)

GROUPS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'groups.json')

DEFAULT_GROUPS = [
    {"id": "private", "name": "Private", "icon": "home", "color": "#6b5b95", "description": "Private projects"},
    {"id": "business", "name": "Business", "icon": "building-2", "color": "#0077b6", "description": "Business projects"},
    {"id": "customer", "name": "Customer", "icon": "user", "color": "#2d6a4f", "description": "Customer projects"},
]


def load_groups():
    """Lädt die benutzerdefinierten Gruppen"""
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"groups": list(DEFAULT_GROUPS)}


def save_groups(data):
    """Speichert die benutzerdefinierten Gruppen"""
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_valid_group_ids():
    """Gibt Liste aller gültigen Gruppen-IDs zurück"""
    groups_data = load_groups()
    return [g['id'] for g in groups_data.get('groups', [])]


@group_bp.route('/api/groups')
def api_get_groups():
    return jsonify(load_groups())


@group_bp.route('/api/groups', methods=['POST'])
def api_create_group():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    group_id = data.get('id', '').strip().lower()
    group_name = data.get('name', '').strip()
    group_icon = data.get('icon', 'folder')
    group_color = data.get('color', '#666666')
    group_desc = data.get('description', '')

    if not group_id or not group_name:
        return jsonify({"error": "ID and name are required"}), 400

    if not re.match(r'^[a-z0-9_]+$', group_id):
        return jsonify({"error": "ID may only contain lowercase letters, numbers and underscores"}), 400

    groups_data = load_groups()
    existing_ids = [g['id'] for g in groups_data['groups']]
    if group_id in existing_ids:
        return jsonify({"error": f"Group with ID '{group_id}' already exists"}), 400

    groups_data['groups'].append({
        "id": group_id, "name": group_name, "icon": group_icon,
        "color": group_color, "description": group_desc
    })
    save_groups(groups_data)
    return jsonify({"success": True, "message": f"Group '{group_name}' created"})


@group_bp.route('/api/groups/<group_id>', methods=['PUT'])
def api_update_group(group_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    groups_data = load_groups()
    group = next((g for g in groups_data['groups'] if g['id'] == group_id), None)
    if not group:
        return jsonify({"error": f"Group '{group_id}' not found"}), 404

    for field in ('name', 'icon', 'color', 'description'):
        if field in data:
            group[field] = data[field]

    save_groups(groups_data)
    return jsonify({"success": True, "message": f"Group '{group_id}' updated"})


@group_bp.route('/api/groups/<group_id>', methods=['DELETE'])
def api_delete_group(group_id):
    groups_data = load_groups()
    group = next((g for g in groups_data['groups'] if g['id'] == group_id), None)
    if not group:
        return jsonify({"error": f"Group '{group_id}' not found"}), 404

    groups_data['groups'].remove(group)
    save_groups(groups_data)
    return jsonify({"success": True, "message": f"Group '{group['name']}' deleted"})
