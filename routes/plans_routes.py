"""
Plans Routes - Uebersicht und Verwaltung von Claude Code Plans
"""
import markdown
from flask import Blueprint, Response, jsonify, request, render_template
from services.db_service import execute, ensure_plans_schema, ensure_plan_workflow_schema
from services.plans_import import sync_plans
from services.plan_workflow_service import (
    get_plan_workflow,
    update_plan_workflow,
    get_project_plan_workflows,
)
from services.project_handoff_service import write_handoff

plans_bp = Blueprint('plans', __name__)


@plans_bp.route('/plans')
def plans_page():
    return render_template('plans.html', active_page='plans')


@plans_bp.route('/api/plans')
def get_plans():
    """Alle Plans aus der DB laden."""
    ensure_plan_workflow_schema()
    project = request.args.get('project')
    status = request.args.get('status')
    category = request.args.get('category')

    query = """
        SELECT p.id, p.filename, p.title, p.project_name, p.context_summary,
               p.category, p.status, p.session_uuid, p.created_at, p.updated_at,
               p.workflow_stage, p.current_state, p.target_state, p.next_action,
               p.latest_executor_status, p.latest_review_status, p.open_items_count,
               s.slug as session_slug
        FROM project_plans p
        LEFT JOIN sessions s ON s.session_uuid = p.session_uuid
    """
    conditions = []
    params = []

    if project:
        conditions.append("p.project_name = %s")
        params.append(project)
    if status:
        conditions.append("p.status = %s")
        params.append(status)
    if category:
        conditions.append("p.category = %s")
        params.append(category)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY p.created_at DESC"

    rows = execute(query, params if params else None, fetch=True)
    plans = []
    for row in (rows or []):
        plans.append({
            'id': row['id'],
            'filename': row['filename'],
            'title': row['title'],
            'project_name': row['project_name'],
            'context_summary': row['context_summary'],
            'category': row['category'],
            'status': row['status'],
            'session_uuid': row['session_uuid'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            'session_slug': row['session_slug'],
            'workflow_stage': row.get('workflow_stage') or 'idea',
            'current_state': row.get('current_state'),
            'target_state': row.get('target_state'),
            'next_action': row.get('next_action'),
            'latest_executor_status': row.get('latest_executor_status'),
            'latest_review_status': row.get('latest_review_status'),
            'open_items_count': row.get('open_items_count') or 0,
        })

    return jsonify({'plans': plans})


@plans_bp.route('/api/plans/<int:plan_id>')
def get_plan_detail(plan_id):
    """Einzelnen Plan mit vollstaendigem Inhalt laden."""
    ensure_plans_schema()
    rows = execute(
        """SELECT p.id, p.filename, p.title, p.project_name, p.content,
                  p.context_summary, p.category, p.status, p.session_uuid,
                  p.created_at, p.updated_at,
                  s.slug as session_slug, s.started_at as session_started
           FROM project_plans p
           LEFT JOIN sessions s ON s.session_uuid = p.session_uuid
           WHERE p.id = %s""",
        (plan_id,), fetch=True
    )
    if not rows:
        return jsonify({'error': 'Plan not found'}), 404

    row = rows[0]
    content_md = row['content'] or ''
    content_html = markdown.markdown(
        content_md,
        extensions=['fenced_code', 'tables', 'nl2br']
    )

    return jsonify({
        'id': row['id'],
        'filename': row['filename'],
        'title': row['title'],
        'project_name': row['project_name'],
        'content': content_md,
        'content_html': content_html,
        'context_summary': row['context_summary'],
        'category': row['category'],
        'status': row['status'],
        'session_uuid': row['session_uuid'],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
        'session_slug': row['session_slug'],
        'session_started': row['session_started'].isoformat() if row['session_started'] else None,
    })


@plans_bp.route('/api/plans/<int:plan_id>', methods=['PUT'])
def update_plan(plan_id):
    """Plan-Metadaten aktualisieren (Projekt, Kategorie). Status wird automatisch erkannt."""
    ensure_plans_schema()
    req = request.get_json()
    if not req:
        return jsonify({'error': 'No data'}), 400

    allowed = ('project_name', 'category', 'title')
    updates = []
    params = []
    for field in allowed:
        if field in req:
            updates.append(f"{field} = %s")
            params.append(req[field])

    if not updates:
        return jsonify({'error': 'No editable fields'}), 400

    updates.append("updated_at = NOW()")
    params.append(plan_id)

    execute(
        f"UPDATE project_plans SET {', '.join(updates)} WHERE id = %s",
        params
    )
    return jsonify({'success': True})


@plans_bp.route('/api/plans/sync', methods=['POST'])
def trigger_sync():
    """Plans aus Dateisystem synchronisieren."""
    stats = sync_plans()
    return jsonify({'success': True, 'stats': stats})


@plans_bp.route('/api/plans/stats')
def get_plan_stats():
    """Erweiterte Statistiken mit handlungsrelevanten KPIs."""
    ensure_plans_schema()
    row = execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'draft') as draft,
            COUNT(*) FILTER (WHERE status = 'active') as active,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'archived') as archived,
            COUNT(DISTINCT project_name) FILTER (WHERE project_name IS NOT NULL) as projects,
            COUNT(*) FILTER (WHERE project_name IS NULL) as unassigned,
            COUNT(*) FILTER (WHERE session_uuid IS NOT NULL) as linked_sessions,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as last_30d,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as last_7d,
            MIN(created_at) as oldest,
            MAX(created_at) as newest
        FROM project_plans
    """, fetchone=True)

    if not row:
        return jsonify({
            'total': 0, 'draft': 0, 'active': 0, 'completed': 0,
            'archived': 0, 'projects': 0, 'unassigned': 0,
            'linked_sessions': 0, 'last_30d': 0, 'last_7d': 0,
            'completion_rate': 0, 'top_project': None,
            'categories': {},
        })

    # Umsetzungsrate berechnen (completed / (completed + archived + active + draft))
    actionable = row['completed'] + row['active'] + row['draft']
    completion_rate = round(row['completed'] / actionable * 100) if actionable > 0 else 0

    # Top-Projekt ermitteln
    top = execute("""
        SELECT project_name, COUNT(*) as cnt
        FROM project_plans
        WHERE project_name IS NOT NULL
        GROUP BY project_name ORDER BY cnt DESC LIMIT 1
    """, fetchone=True)

    # Kategorie-Verteilung
    cats = execute("""
        SELECT category, COUNT(*) as cnt
        FROM project_plans GROUP BY category ORDER BY cnt DESC
    """, fetch=True)

    return jsonify({
        'total': row['total'],
        'draft': row['draft'],
        'active': row['active'],
        'completed': row['completed'],
        'archived': row['archived'],
        'projects': row['projects'],
        'unassigned': row['unassigned'],
        'linked_sessions': row['linked_sessions'],
        'last_30d': row['last_30d'],
        'last_7d': row['last_7d'],
        'oldest': row['oldest'].isoformat() if row['oldest'] else None,
        'newest': row['newest'].isoformat() if row['newest'] else None,
        'completion_rate': completion_rate,
        'top_project': {'name': top['project_name'], 'count': top['cnt']} if top else None,
        'categories': {r['category']: r['cnt'] for r in (cats or [])},
    })


@plans_bp.route('/api/plans/projects')
def get_plan_projects():
    """Alle Projekte mit Plan-Anzahl."""
    ensure_plans_schema()
    rows = execute("""
        SELECT project_name, COUNT(*) as cnt, MAX(created_at) as latest
        FROM project_plans
        WHERE project_name IS NOT NULL
        GROUP BY project_name
        ORDER BY COUNT(*) DESC
    """, fetch=True)

    projects = [
        {'name': r['project_name'], 'count': r['cnt'],
         'latest': r['latest'].isoformat() if r['latest'] else None}
        for r in (rows or [])
    ]
    # Nicht-zugeordnete zaehlen
    unassigned = execute(
        "SELECT COUNT(*) as cnt FROM project_plans WHERE project_name IS NULL",
        fetchone=True
    )
    if unassigned and unassigned['cnt'] > 0:
        projects.append({'name': None, 'count': unassigned['cnt'], 'latest': None})

    return jsonify({'projects': projects})


# --- Sprint E: Plan-Workflow Micro-Ebene ---

@plans_bp.route('/api/plans/<int:plan_id>/workflow')
def api_get_plan_workflow(plan_id):
    """Workflow-/Micro-Daten fuer eine Plan-Card (M2)."""
    data = get_plan_workflow(plan_id)
    if not data:
        return jsonify({'error': 'Plan not found'}), 404
    return jsonify(data)


@plans_bp.route('/api/plans/<int:plan_id>/workflow', methods=['PUT'])
def api_update_plan_workflow(plan_id):
    """Workflow-Felder aktualisieren (M2)."""
    body = request.get_json(silent=True)
    if not body:
        return jsonify({'error': 'Request-Body muss JSON sein'}), 400
    try:
        result = update_plan_workflow(plan_id, body)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    if not result:
        return jsonify({'error': 'Plan not found'}), 404
    return jsonify(result)


@plans_bp.route('/api/plans/<int:plan_id>/handoff')
def api_get_plan_handoff(plan_id):
    """Projekt-Handoff als Markdown fuer LLM-Executors. Ermittelt project_name aus plan_id."""
    row = execute(
        "SELECT project_name FROM project_plans WHERE id = %s",
        (plan_id,), fetchone=True,
    )
    if not row or not row.get("project_name"):
        return jsonify({'error': 'Plan not found or no project assigned'}), 404
    project_name = row["project_name"]
    _, md = write_handoff(project_name)
    if md is None:
        return jsonify({'error': 'Could not generate handoff'}), 404
    return Response(md, mimetype='text/markdown',
                    headers={'Content-Disposition': f'inline; filename="handoff.md"'})


@plans_bp.route('/api/plans/workflow')
def api_get_project_workflows():
    """Aggregierte Workflow-Daten fuer ein Projekt (M2 optional)."""
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': 'project_id ist erforderlich'}), 400
    workflows = get_project_plan_workflows(project_id)
    return jsonify({'workflows': workflows})
