"""
Dashboard-Widget API: Aggregierte Statistiken und Aktivitaetsdaten
"""
from datetime import datetime, timedelta
from collections import Counter
from flask import Blueprint, jsonify

from services import scan_projects, get_docker_containers
from services.db_service import execute

widget_bp = Blueprint('widgets', __name__)


@widget_bp.route('/api/widgets/activity')
def widget_activity():
    """Projekt-Aktivitaet der letzten 30 Tage als Heatmap-Daten"""
    projects = scan_projects(auto_generate=False)
    now = datetime.now()

    # Commits pro Tag (letzte 30 Tage)
    day_counts = Counter()
    for proj in projects.values():
        commit_date = proj.get('last_commit')
        if commit_date:
            try:
                dt = datetime.strptime(commit_date[:10], '%Y-%m-%d')
                days_ago = (now - dt).days
                if days_ago <= 30:
                    day_counts[commit_date[:10]] += 1
            except (ValueError, TypeError):
                pass

        file_date = proj.get('last_file_change')
        if file_date:
            try:
                dt = datetime.strptime(file_date[:10], '%Y-%m-%d')
                days_ago = (now - dt).days
                if days_ago <= 30:
                    day_counts[file_date[:10]] += 1
            except (ValueError, TypeError):
                pass

    # Letzten 30 Tage auffuellen
    heatmap = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        weekday = (now - timedelta(days=i)).strftime('%a')
        heatmap.append({
            'date': day,
            'weekday': weekday,
            'count': day_counts.get(day, 0),
        })

    return jsonify({"heatmap": heatmap})


@widget_bp.route('/api/widgets/overview')
def widget_overview():
    """Aggregierte Projekt-Statistiken fuer Dashboard-Widgets"""
    projects = scan_projects(auto_generate=False)
    containers = get_docker_containers()

    # Projekttyp-Verteilung
    type_counts = Counter()
    group_counts = Counter()
    tech_counts = Counter()
    status_counts = {'active': 0, 'stale': 0, 'inactive': 0}

    now = datetime.now()

    for proj in projects.values():
        ptype = proj.get('project_type', 'project')
        type_counts[ptype] += 1

        group = proj.get('group') or 'Ungrouped'
        group_counts[group] += 1

        for tag in proj.get('tags', []):
            tech_counts[tag] += 1

        # Aktivitaets-Status
        last_change = proj.get('last_file_change') or proj.get('last_commit')
        if last_change:
            try:
                dt = datetime.strptime(last_change[:10], '%Y-%m-%d')
                days_ago = (now - dt).days
                if days_ago <= 7:
                    status_counts['active'] += 1
                elif days_ago <= 30:
                    status_counts['stale'] += 1
                else:
                    status_counts['inactive'] += 1
            except (ValueError, TypeError):
                status_counts['inactive'] += 1
        else:
            status_counts['inactive'] += 1

    # Container-Stats
    running = sum(1 for c in containers if 'Running' in c.get('status', '') or 'Healthy' in c.get('status', ''))
    stopped = sum(1 for c in containers if 'Stopped' in c.get('status', ''))

    # Session-Stats (letzte 7 Tage)
    session_stats = {}
    try:
        recent = execute("""
            SELECT DATE(started_at) as day, COUNT(*) as cnt,
                   SUM(duration_ms) as dur, SUM(total_input_tokens) as tokens
            FROM sessions
            WHERE started_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(started_at)
            ORDER BY day
        """, fetch=True)
        session_stats = {
            'days': [{'date': str(r['day']), 'sessions': r['cnt'],
                      'duration_min': (r['dur'] or 0) // 60000,
                      'tokens_k': (r['tokens'] or 0) // 1000}
                     for r in (recent or [])],
        }
    except Exception:
        pass

    # Top aktive Projekte (letzte 7 Tage)
    top_active = []
    for name, proj in projects.items():
        last = proj.get('last_file_change') or proj.get('last_commit')
        if last:
            try:
                dt = datetime.strptime(last[:10], '%Y-%m-%d')
                if (now - dt).days <= 7:
                    top_active.append({
                        'name': name,
                        'last_activity': last,
                        'type': proj.get('project_type', 'project'),
                        'git_status': proj.get('git_status', ''),
                    })
            except (ValueError, TypeError):
                pass
    top_active.sort(key=lambda x: x['last_activity'], reverse=True)

    return jsonify({
        'project_types': dict(type_counts.most_common(10)),
        'groups': dict(group_counts.most_common(10)),
        'technologies': dict(tech_counts.most_common(15)),
        'activity_status': status_counts,
        'containers': {'running': running, 'stopped': stopped, 'total': len(containers)},
        'sessions': session_stats,
        'top_active': top_active[:10],
        'totals': {
            'projects': len(projects),
            'containers': len(containers),
            'with_docker': sum(1 for p in projects.values() if p.get('has_docker')),
            'with_gitea': sum(1 for p in projects.values() if p.get('has_gitea')),
        },
    })
