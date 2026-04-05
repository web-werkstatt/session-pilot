"""
Settings: Zentrale Einstellungsseite (SaaS-Pattern)
Sektionen: Modell-Preise, AI Accounts, External Links, Allgemein
"""
import json
import os
from flask import Blueprint, jsonify, request, render_template
from services.db_service import execute
from services.account_discovery import discover_all_accounts
from services.dashboard_settings_service import load_dashboard_settings, save_dashboard_settings
from config import PROJECTS_DIR, GITEA_URL, GITEA_USER, HOST, PORT, DB_CONFIG
from routes.api_utils import api_route

EXTERNAL_LINKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'external_links.json')

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
def settings_page():
    return render_template('settings.html', active_page='settings')


# === General Settings ===

@settings_bp.route('/api/settings/general')
@api_route
def api_general_settings():
    return jsonify(load_dashboard_settings())


@settings_bp.route('/api/settings/general', methods=['POST'])
@api_route
def api_general_settings_save():
    data = request.get_json() or {}
    settings = save_dashboard_settings(data)
    return jsonify({"success": True, "settings": settings})


# === Modell-Preise ===

@settings_bp.route('/api/settings/pricing')
@api_route
def api_pricing_list():
    rows = execute("""
        SELECT id, model_pattern, display_name, provider,
               input_price, output_price,
               cache_read_factor, cache_create_factor, updated_at
        FROM model_pricing ORDER BY provider, model_pattern
    """, fetch=True)
    return jsonify([{
        "id": r["id"],
        "model_pattern": r["model_pattern"],
        "display_name": r["display_name"],
        "provider": r["provider"],
        "input_price": float(r["input_price"]),
        "output_price": float(r["output_price"]),
        "cache_read_factor": float(r["cache_read_factor"] or 0.1),
        "cache_create_factor": float(r["cache_create_factor"] or 1.25),
        "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
    } for r in (rows or [])])


@settings_bp.route('/api/settings/pricing', methods=['POST'])
@api_route
def api_pricing_save():
    data = request.get_json()
    if not data or not data.get("model_pattern"):
        return jsonify({"error": "model_pattern required"}), 400

    row_id = data.get("id")
    if row_id:
        execute("""
            UPDATE model_pricing SET
                model_pattern = %s, display_name = %s, provider = %s,
                input_price = %s, output_price = %s,
                cache_read_factor = %s, cache_create_factor = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            data["model_pattern"], data.get("display_name", ""),
            data.get("provider", ""), data["input_price"], data["output_price"],
            data.get("cache_read_factor", 0.1), data.get("cache_create_factor", 1.25),
            row_id
        ))
    else:
        execute("""
            INSERT INTO model_pricing
                (model_pattern, display_name, provider, input_price, output_price,
                 cache_read_factor, cache_create_factor)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["model_pattern"], data.get("display_name", ""),
            data.get("provider", ""), data["input_price"], data["output_price"],
            data.get("cache_read_factor", 0.1), data.get("cache_create_factor", 1.25),
        ))

    import services.cost_service as cs
    cs._pricing_cache = None
    return jsonify({"success": True})


@settings_bp.route('/api/settings/pricing/<int:pricing_id>', methods=['DELETE'])
@api_route
def api_pricing_delete(pricing_id):
    execute("DELETE FROM model_pricing WHERE id = %s", (pricing_id,))
    import services.cost_service as cs
    cs._pricing_cache = None
    return jsonify({"success": True})


# === AI Accounts ===

@settings_bp.route('/api/settings/accounts')
@api_route
def api_accounts_list():
    """Automatisch erkannte AI-Accounts"""
    accounts = discover_all_accounts()
    # Session-Counts pro Account
    counts = execute("""
        SELECT account, COUNT(*) as sessions,
               MAX(started_at) as last_session
        FROM sessions GROUP BY account
    """, fetch=True)
    count_map = {r["account"]: r for r in (counts or [])}

    result = []
    for acc in accounts:
        stats = count_map.get(acc["name"], {})
        result.append({
            "name": acc["name"],
            "tool": acc["tool"],
            "config_dir": acc["config_dir"],
            "sessions": stats.get("sessions", 0),
            "last_session": stats["last_session"].isoformat() if stats.get("last_session") else None,
        })
    return jsonify(result)


# === System Info ===

@settings_bp.route('/api/settings/system')
@api_route
def api_system_info():
    """System-Konfiguration (read-only)"""
    db_stats = execute("""
        SELECT
            (SELECT COUNT(*) FROM sessions) as total_sessions,
            (SELECT COUNT(*) FROM messages) as total_messages,
            (SELECT COUNT(*) FROM model_pricing) as pricing_models,
            (SELECT pg_size_pretty(pg_database_size(current_database()))) as db_size
    """, fetchone=True)

    return jsonify({
        "projects_dir": PROJECTS_DIR,
        "gitea_url": GITEA_URL,
        "gitea_user": GITEA_USER,
        "host": HOST,
        "port": PORT,
        "db_host": DB_CONFIG["host"],
        "db_port": DB_CONFIG["port"],
        "db_name": DB_CONFIG["dbname"],
        "db_size": db_stats["db_size"] if db_stats else "?",
        "total_sessions": db_stats["total_sessions"] if db_stats else 0,
        "total_messages": db_stats["total_messages"] if db_stats else 0,
        "pricing_models": db_stats["pricing_models"] if db_stats else 0,
    })


# === External Links ===

def _load_external_links():
    if os.path.exists(EXTERNAL_LINKS_FILE):
        with open(EXTERNAL_LINKS_FILE, 'r') as f:
            return json.load(f)
    return []


def _save_external_links(links):
    with open(EXTERNAL_LINKS_FILE, 'w') as f:
        json.dump(links, f, indent=2)


@settings_bp.route('/api/settings/external-links')
@api_route
def api_external_links_list():
    return jsonify(_load_external_links())


@settings_bp.route('/api/settings/external-links', methods=['POST'])
@api_route
def api_external_links_save():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('url'):
        return jsonify({"error": "Name and URL required"}), 400

    links = _load_external_links()
    link_id = data.get('id')

    if link_id:
        for link in links:
            if link['id'] == link_id:
                link['name'] = data['name']
                link['url'] = data['url']
                link['icon'] = data.get('icon', 'external-link')
                break
    else:
        new_id = max((l['id'] for l in links), default=0) + 1
        links.append({
            'id': new_id,
            'name': data['name'],
            'url': data['url'],
            'icon': data.get('icon', 'external-link'),
        })

    _save_external_links(links)
    return jsonify({"success": True})


@settings_bp.route('/api/settings/external-links/<int:link_id>', methods=['DELETE'])
@api_route
def api_external_links_delete(link_id):
    links = _load_external_links()
    links = [l for l in links if l['id'] != link_id]
    _save_external_links(links)
    return jsonify({"success": True})
