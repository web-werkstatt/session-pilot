"""
Sprint 11: Model Trend Analysis & Recommendation Engine.
Woechentliche/taegliche Rework-Rate-Trends und Modell-Empfehlungen.
"""
from datetime import datetime, timedelta, timezone

from services.db_service import execute
from services.model_recommendation import STACK_MAP, _parse_period, calculate_quality_score


# --- Trend Analysis ---

def get_model_trend(model=None, project=None, granularity='weekly'):
    """Returns weekly/daily rework rate trends per model."""
    params = []
    where_parts = ["s.model IS NOT NULL", "s.model != ''", "s.model NOT LIKE '<%%>'", "s.outcome IS NOT NULL"]

    if model:
        where_parts.append("s.model = %s")
        params.append(model)
    if project:
        where_parts.append("s.project_name = %s")
        params.append(project)

    # Only look at last 6 months max
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    where_parts.append("s.started_at > %s")
    params.append(cutoff)

    trunc = 'week' if granularity == 'weekly' else 'day'
    where_sql = " AND ".join(where_parts)

    rows = execute(f"""
        SELECT
            s.model,
            date_trunc('{trunc}', s.started_at) AS period,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE s.outcome = 'ok') AS ok,
            COUNT(*) FILTER (WHERE s.outcome = 'needs_fix') AS needs_fix,
            COUNT(*) FILTER (WHERE s.outcome = 'reverted') AS reverted
        FROM sessions s
        WHERE {where_sql}
        GROUP BY s.model, date_trunc('{trunc}', s.started_at)
        ORDER BY s.model, period
    """, params, fetch=True)

    # Group by model
    model_periods = {}
    for r in (rows or []):
        m = r['model']
        if m not in model_periods:
            model_periods[m] = []
        total = int(r['total'])
        nf = int(r['needs_fix'])
        rev = int(r['reverted'])
        rated = int(r['ok']) + nf + rev
        rework_rate = round((nf + rev) / rated * 100, 1) if rated > 0 else 0.0
        p = r['period']
        if p and granularity == 'weekly':
            period_label = f"{p.isocalendar()[0]}-W{p.isocalendar()[1]:02d}"
        elif p:
            period_label = p.strftime('%Y-%m-%d')
        else:
            period_label = None
        model_periods[m].append({
            'period': period_label,
            'total': total,
            'rated': rated,
            'rework_rate': rework_rate,
        })

    trends = []
    for m, periods in model_periods.items():
        # Calculate direction and 4-week delta
        direction = 'stable'
        delta_4w = 0.0
        if len(periods) >= 2:
            recent = periods[-1]['rework_rate']
            older = periods[-min(4, len(periods))]['rework_rate']
            delta_4w = round(recent - older, 1)
            if delta_4w > 5:
                direction = 'worsening'
            elif delta_4w < -5:
                direction = 'improving'

        trends.append({
            'model': m,
            'periods': periods,
            'direction': direction,
            'delta_4w': delta_4w,
        })

    return {'trends': trends}


# --- Recommendation ---

def recommend_model(project=None, stack=None):
    """Simple recommendation: filter models with >5 sessions for stack,
    sort by quality_score DESC then cost_per_success ASC."""
    cutoff = _parse_period('90d')
    params = []
    where_parts = ["s.model IS NOT NULL", "s.model != ''", "s.model NOT LIKE '<%%>'", "s.outcome IS NOT NULL"]

    where_parts.append("s.started_at > %s")
    params.append(cutoff)

    if project:
        where_parts.append("s.project_name = %s")
        params.append(project)

    join_clause = ""
    if stack:
        join_clause = " JOIN ai_file_touches ft ON ft.session_id = s.id"
        exts = [ext for ext, s_name in STACK_MAP.items() if s_name == stack]
        if exts:
            where_parts.append(f"({' OR '.join('ft.file_path LIKE %s' for _ in exts)})")
            params.extend(f'%{ext}' for ext in exts)

    where_sql = " AND ".join(where_parts)

    rows = execute(f"""
        SELECT
            s.model,
            COUNT(DISTINCT s.id) AS rated,
            COUNT(DISTINCT s.id) FILTER (WHERE s.outcome = 'ok') AS ok,
            COUNT(DISTINCT s.id) FILTER (WHERE s.outcome = 'needs_fix') AS needs_fix,
            COUNT(DISTINCT s.id) FILTER (WHERE s.outcome = 'reverted') AS reverted,
            SUM(COALESCE(s.cost_estimate, 0)) AS total_cost,
            AVG(CASE s.outcome_severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 END) FILTER (WHERE s.outcome_severity IS NOT NULL) AS avg_severity
        FROM sessions s
        {join_clause}
        WHERE {where_sql}
        GROUP BY s.model
        HAVING COUNT(DISTINCT s.id) > 5
        ORDER BY COUNT(DISTINCT s.id) DESC
    """, params, fetch=True)

    if not rows:
        return {'recommended': None, 'reason': 'Not enough data', 'alternative': None}

    candidates = []
    for r in rows:
        rated = int(r['rated'])
        ok = int(r['ok'])
        nf = int(r['needs_fix'])
        rev = int(r['reverted'])
        avg_sev = float(r['avg_severity']) if r.get('avg_severity') else None
        total_cost = float(r.get('total_cost') or 0)
        score = calculate_quality_score(ok, nf, rev, rated, avg_sev)
        cost_per_success = round(total_cost / ok, 4) if ok > 0 and total_cost > 0 else 999.0

        candidates.append({
            'model': r['model'],
            'quality_score': score,
            'cost_per_success': cost_per_success,
            'rated': rated,
            'rework_rate': round((nf + rev) / rated * 100, 1) if rated > 0 else 0.0,
        })

    # Sort: quality_score DESC, then cost_per_success ASC
    candidates.sort(key=lambda c: (-c['quality_score'], c['cost_per_success']))

    best = candidates[0]
    alt = candidates[1] if len(candidates) > 1 else None

    stack_hint = f" for {stack}" if stack else ""
    cost_str = f"${best['cost_per_success']:.2f}/success" if best['cost_per_success'] < 999 else "n/a"
    reason = (
        f"Best value{stack_hint}: {best['quality_score']} quality, "
        f"{best['rework_rate']}% rework, {cost_str} "
        f"across {best['rated']} sessions."
    )

    alt_info = None
    if alt:
        cost_ratio = ''
        if best['cost_per_success'] > 0 and best['cost_per_success'] < 999 and alt['cost_per_success'] < 999:
            ratio = alt['cost_per_success'] / best['cost_per_success']
            if ratio > 1.5:
                cost_ratio = f", {ratio:.0f}x more expensive"
        alt_info = (
            f"{alt['model']} for critical tasks "
            f"({alt['quality_score']} quality, {alt['rework_rate']}% rework{cost_ratio})"
        )

    return {
        'recommended': best['model'],
        'reason': reason,
        'alternative': alt_info,
    }
