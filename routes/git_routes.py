"""
Git-Aktionen Routes: Status, Commit, Push, Pull
"""
from flask import Blueprint, jsonify, request
from services.path_resolver import resolve_project_path
from services.git_service import (
    get_git_status_detail, git_add_all, git_commit, git_push, git_pull
)

git_bp = Blueprint('git', __name__)


@git_bp.route('/api/git/<path:name>/status')
def api_git_status(name):
    """Detaillierter Git-Status"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    do_fetch = request.args.get('fetch', '0') == '1'
    status = get_git_status_detail(project_path, do_fetch=do_fetch)
    return jsonify(status)


@git_bp.route('/api/git/<path:name>/commit', methods=['POST'])
def api_git_commit(name):
    """Staged alles und committed"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"success": False, "error": "Commit-Message fehlt"}), 400

    # Stage all
    ok, err = git_add_all(project_path)
    if not ok:
        return jsonify({"success": False, "error": f"git add fehlgeschlagen: {err}"}), 400

    # Commit
    ok, output = git_commit(project_path, message)
    return jsonify({"success": ok, "output": output}), (200 if ok else 400)


@git_bp.route('/api/git/<path:name>/push', methods=['POST'])
def api_git_push(name):
    """Pusht zum Remote"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    ok, output = git_push(project_path)
    return jsonify({"success": ok, "output": output}), (200 if ok else 400)


@git_bp.route('/api/git/<path:name>/pull', methods=['POST'])
def api_git_pull(name):
    """Pullt vom Remote (fast-forward only)"""
    project_path = resolve_project_path(name)
    if not project_path:
        return jsonify({"error": "Projekt nicht gefunden"}), 404

    ok, output = git_pull(project_path)
    return jsonify({"success": ok, "output": output}), (200 if ok else 400)
