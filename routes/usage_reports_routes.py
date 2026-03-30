"""
Usage Reports: Tages-, Wochen-, Monatsberichte aus JSONL-Daten.
"""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request, render_template
from services.usage_reports_service import get_usage_report
from routes.api_utils import api_route

usage_reports_bp = Blueprint('usage_reports', __name__)


@usage_reports_bp.route('/usage-reports')
def usage_reports_page():
    return render_template('usage_reports.html', active_page='usage_reports')


@usage_reports_bp.route('/api/usage-reports/data')
@api_route
def api_usage_reports_data():
    """Aggregierte Usage-Daten fuer einen Zeitraum."""
    period = request.args.get('period', 'daily')
    if period not in ('daily', 'weekly', 'monthly'):
        period = 'daily'

    preset = request.args.get('preset', '7days')
    now = datetime.now(timezone.utc)

    if preset == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif preset == '7days':
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif preset == '30days':
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif preset == 'this_month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif preset == 'this_week':
        monday = now - timedelta(days=now.weekday())
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif preset == 'custom':
        try:
            start = datetime.fromisoformat(request.args.get('start', '')).replace(tzinfo=timezone.utc)
            end = datetime.fromisoformat(request.args.get('end', '')).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
    else:
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now

    data = get_usage_report(period, start, end)
    return jsonify(data)
