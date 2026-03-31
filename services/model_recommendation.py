"""
Sprint 11: Model Quality Comparison & Recommendation Engine.
Berechnet Qualitaets-Scores pro Modell, Stack-spezifische Metriken,
Trend-Analysen und Empfehlungen.
"""
from datetime import datetime, timedelta, timezone

from services.db_service import execute, ensure_model_quality_view, refresh_model_quality_view


# --- Helpers ---

STACK_MAP = {
    '.py': 'python',
    '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript',
    '.css': 'css', '.scss': 'css',
    '.html': 'markup', '.astro': 'markup',
}


def _parse_period(period):
    """Parse period string to cutoff datetime. Returns None for 'all'."""
    if period == 'all':
        return None
    days = int(period.rstrip('d')) if period.endswith('d') else 90
    return datetime.now(timezone.utc) - timedelta(days=days)


# --- Quality Score ---

def calculate_quality_score(ok_count, needs_fix, reverted, rated, avg_severity=None):
    """Quality score 0-100.
    Formula: 100 - (rework_rate * 0.5) - (reverted_rate * 1.5) - (incomplete_rate * 0.3)
    Bonus: +5 if rated > 20 sessions.
    """
    if rated == 0:
        return 0.0
    rework_rate = (needs_fix + reverted) / rated * 100
    reverted_rate = reverted / rated * 100
    # Sessions rated but not ok/needs_fix/reverted (e.g. partial, abandoned)
    incomplete_rate = max(0, rated - ok_count - needs_fix - reverted) / rated * 100

    score = 100.0 - (rework_rate * 0.5) - (reverted_rate * 1.5) - (incomplete_rate * 0.3)

    if avg_severity and avg_severity > 0:
        score -= avg_severity * 2

    if rated > 20:
        score += 5.0

    return max(0.0, min(100.0, round(score, 1)))


def score_to_grade(score):
    """Convert score to letter grade."""
    if score >= 90:
        return 'A'
    if score >= 75:
        return 'B'
    if score >= 60:
        return 'C'
    if score >= 40:
        return 'D'
    return 'F'


# --- Model Comparison ---

def get_model_comparison(period='90d', project=None, stack=None):
    """Returns model comparison data. Uses mv_model_quality view when no filters,
    falls back to direct query with filters."""
    cutoff = _parse_period(period)
    has_filters = project or stack or cutoff is not None

    if not has_filters:
        # Fast path: materialized view
        ensure_model_quality_view()
        try:
            refresh_model_quality_view()
        except Exception:
            pass
        rows = execute(
            "SELECT * FROM mv_model_quality ORDER BY rated_sessions DESC",
            fetch=True
        )
    else:
        # Direct query with filters
        params = []
        where_parts = ["s.model IS NOT NULL", "s.model != ''"]

        if cutoff:
            where_parts.append("s.started_at > %s")
            params.append(cutoff)
        if project:
            where_parts.append("s.project_name = %s")
            params.append(project)

        # Stack filter: join with ai_file_touches
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
                COUNT(DISTINCT s.id) AS total_sessions,
                COUNT(DISTINCT s.id) FILTER (WHERE s.outcome IS NOT NULL) AS rated_sessions,
                COUNT(DISTINCT s.id) FILTER (WHERE s.outcome = 'ok') AS ok_count,
                COUNT(DISTINCT s.id) FILTER (WHERE s.outcome = 'needs_fix') AS needs_fix_count,
                COUNT(DISTINCT s.id) FILTER (WHERE s.outcome = 'reverted') AS reverted_count,
                SUM(COALESCE(s.total_input_tokens, 0) + COALESCE(s.total_output_tokens, 0)) AS total_tokens,
                SUM(COALESCE(s.cost_estimate, 0)) AS total_cost,
                AVG(s.duration_ms / 60000.0) FILTER (WHERE s.duration_ms > 0) AS avg_duration_min,
                AVG(s.outcome_severity::int) FILTER (WHERE s.outcome_severity IS NOT NULL) AS avg_severity
            FROM sessions s
            {join_clause}
            WHERE {where_sql}
            GROUP BY s.model
            ORDER BY COUNT(DISTINCT s.id) FILTER (WHERE s.outcome IS NOT NULL) DESC
        """, params, fetch=True)

    models = []
    for r in (rows or []):
        rated = int(r.get('rated_sessions') or 0)
        ok = int(r.get('ok_count') or 0)
        nf = int(r.get('needs_fix_count') or 0)
        rev = int(r.get('reverted_count') or 0)
        avg_sev = float(r['avg_severity']) if r.get('avg_severity') else None
        total_cost = float(r.get('total_cost') or 0)

        score = calculate_quality_score(ok, nf, rev, rated, avg_sev)
        rework_rate = round((nf + rev) / rated * 100, 1) if rated > 0 else 0.0
        cost_per_session = round(total_cost / rated, 4) if rated > 0 and total_cost > 0 else None
        cost_per_success = round(total_cost / ok, 4) if ok > 0 and total_cost > 0 else None

        models.append({
            'model': r['model'],
            'total_sessions': int(r.get('total_sessions') or 0),
            'rated_sessions': rated,
            'ok': ok,
            'needs_fix': nf,
            'reverted': rev,
            'rework_rate': rework_rate,
            'quality_score': score,
            'grade': score_to_grade(score),
            'total_tokens': int(r.get('total_tokens') or 0),
            'total_cost': round(total_cost, 2),
            'cost_per_session': cost_per_session,
            'cost_per_success': cost_per_success,
            'avg_duration_min': round(float(r['avg_duration_min']), 1) if r.get('avg_duration_min') else None,
        })

    # Sort by quality score descending
    models.sort(key=lambda m: m['quality_score'], reverse=True)

    rec = recommend_model(project=project, stack=stack)

    return {
        'period': period,
        'models': models,
        'recommendation': rec.get('recommended', '') if rec else '',
    }


# --- Stack-specific Metrics ---

def get_model_by_stack(period='90d', project=None):
    """Returns stack-specific metrics matrix."""
    cutoff = _parse_period(period)
    params = []
    where_parts = ["s.model IS NOT NULL", "s.model != ''", "ft.file_path IS NOT NULL"]

    if cutoff:
        where_parts.append("s.started_at > %s")
        params.append(cutoff)
    if project:
        where_parts.append("s.project_name = %s")
        params.append(project)

    where_sql = " AND ".join(where_parts)

    rows = execute(f"""
        SELECT
            s.model,
            ft.file_path,
            s.outcome
        FROM sessions s
        JOIN ai_file_touches ft ON ft.session_id = s.id
        WHERE {where_sql}
    """, params, fetch=True)

    # Aggregate by model + stack
    matrix_data = {}  # (model, stack) -> {ok, needs_fix, reverted, total}
    for r in (rows or []):
        ext = _ext_from_path(r['file_path'])
        stack = STACK_MAP.get(ext)
        if not stack:
            continue
        key = (r['model'], stack)
        if key not in matrix_data:
            matrix_data[key] = {'ok': 0, 'needs_fix': 0, 'reverted': 0, 'total': 0}
        matrix_data[key]['total'] += 1
        outcome = r.get('outcome')
        if outcome in ('ok', 'needs_fix', 'reverted'):
            matrix_data[key][outcome] += 1

    # Build matrix list
    matrix = []
    for (model, stack), counts in sorted(matrix_data.items()):
        rated = counts['ok'] + counts['needs_fix'] + counts['reverted']
        rework = counts['needs_fix'] + counts['reverted']
        rework_rate = round(rework / rated * 100, 1) if rated > 0 else 0.0
        score = calculate_quality_score(counts['ok'], counts['needs_fix'], counts['reverted'], rated)
        matrix.append({
            'model': model,
            'stack': stack,
            'sessions': counts['total'],
            'rated': rated,
            'rework_rate': rework_rate,
            'quality_score': score,
            'grade': score_to_grade(score),
        })

    # Generate insights
    insights = _generate_stack_insights(matrix)

    return {
        'matrix': matrix,
        'insights': insights,
    }


def _ext_from_path(file_path):
    """Extract file extension from path."""
    if not file_path:
        return ''
    dot = file_path.rfind('.')
    return file_path[dot:].lower() if dot >= 0 else ''


def _generate_stack_insights(matrix):
    """Generate 1-2 simple string insights from the stack matrix."""
    if not matrix:
        return []

    insights = []

    # Find best model per stack
    stacks = {}
    for entry in matrix:
        if entry['rated'] < 3:
            continue
        s = entry['stack']
        if s not in stacks or entry['quality_score'] > stacks[s]['quality_score']:
            stacks[s] = entry

    if stacks:
        best_stack = max(stacks.values(), key=lambda e: e['quality_score'])
        insights.append(
            f"{best_stack['model']} performs best on {best_stack['stack']} "
            f"with a {best_stack['grade']} grade ({best_stack['rework_rate']}% rework rate)."
        )

    # Find worst rework rate across stacks
    worst = [e for e in matrix if e['rated'] >= 3]
    if worst:
        worst_entry = max(worst, key=lambda e: e['rework_rate'])
        if worst_entry['rework_rate'] > 20:
            insights.append(
                f"High rework rate for {worst_entry['model']} on {worst_entry['stack']}: "
                f"{worst_entry['rework_rate']}% - consider alternatives."
            )

    return insights


# --- Trend Analysis ---

def get_model_trend(model=None, project=None, granularity='weekly'):
    """Returns weekly/daily rework rate trends per model."""
    params = []
    where_parts = ["s.model IS NOT NULL", "s.model != ''", "s.outcome IS NOT NULL"]

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
        model_periods[m].append({
            'period': r['period'].isoformat() if r['period'] else None,
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
    where_parts = ["s.model IS NOT NULL", "s.model != ''", "s.outcome IS NOT NULL"]

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
            AVG(s.outcome_severity::int) FILTER (WHERE s.outcome_severity IS NOT NULL) AS avg_severity
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
    reason = (
        f"Highest quality score ({best['quality_score']}) with "
        f"{best['rework_rate']}% rework rate{stack_hint} "
        f"across {best['rated']} sessions."
    )

    return {
        'recommended': best['model'],
        'reason': reason,
        'alternative': alt['model'] if alt else None,
    }
