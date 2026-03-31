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

_provider_cache = None
_provider_cache_ts = 0


def _load_provider_map():
    """Load provider mapping from model_pricing DB table. Cached 60s."""
    import time
    global _provider_cache, _provider_cache_ts
    now = time.time()
    if _provider_cache is not None and (now - _provider_cache_ts) < 60:
        return _provider_cache
    try:
        rows = execute(
            "SELECT model_pattern, provider FROM model_pricing WHERE provider IS NOT NULL",
            fetch=True
        )
        mapping = [(r['model_pattern'].lower(), r['provider']) for r in (rows or [])]
        _provider_cache = mapping
        _provider_cache_ts = now
        return mapping
    except Exception:
        return _provider_cache or []


def _detect_provider(model_name):
    """Detect provider from model_pricing DB table (fuzzy-match like cost_service)."""
    if not model_name:
        return None
    lower = model_name.lower()
    display_names = {'openai': 'OpenAI', 'deepseek': 'DeepSeek'}
    for pattern, provider in _load_provider_map():
        if pattern in lower or lower.startswith(pattern):
            if not provider:
                return None
            return display_names.get(provider.lower(), provider.capitalize())
    return None


def _parse_period(period):
    """Parse period string to cutoff datetime. Returns None for 'all'."""
    if period == 'all':
        return None
    days = int(period.rstrip('d')) if period.endswith('d') else 90
    return datetime.now(timezone.utc) - timedelta(days=days)


# --- Quality Score ---

def calculate_quality_score(ok_count, needs_fix, reverted, rated,
                            avg_severity=None, security_issues=0):
    """Quality score 0-100.
    Formula: 100 - (rework_rate * 0.5) - (reverted_rate * 1.5) - (incomplete_rate * 0.3)
    Bonus: +5 if rated > 20 sessions.
    Malus: -10 if > 3 security issues.
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

    if security_issues > 3:
        score -= 10.0

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


# --- Top Reasons ---

def _fetch_top_reasons(cutoff=None, project=None, stack=None, limit=3):
    """Fetch top outcome_reasons per model (max `limit` per model)."""
    params = []
    where_parts = [
        "s.model IS NOT NULL", "s.model != ''", "s.model NOT LIKE '<%%>'",
        "s.outcome_reason IS NOT NULL", "s.outcome_reason != ''",
    ]
    if cutoff:
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
        SELECT model, outcome_reason, COUNT(*) AS cnt
        FROM sessions s {join_clause}
        WHERE {where_sql}
        GROUP BY model, outcome_reason
        ORDER BY model, cnt DESC
    """, params, fetch=True)

    top = {}        # model -> [{reason, count}, ...] (max limit)
    sec_counts = {} # model -> total security-related issue count
    for r in (rows or []):
        m = r['model']
        cnt = int(r['cnt'])
        reason = r['outcome_reason']
        if m not in top:
            top[m] = []
        if len(top[m]) < limit:
            top[m].append({'reason': reason, 'count': cnt})
        if 'security' in reason.lower():
            sec_counts[m] = sec_counts.get(m, 0) + cnt
    return top, sec_counts


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
        where_parts = ["s.model IS NOT NULL", "s.model != ''", "s.model NOT LIKE '<%%>'"]

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
                AVG(CASE s.outcome_severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 END) FILTER (WHERE s.outcome_severity IS NOT NULL) AS avg_severity
            FROM sessions s
            {join_clause}
            WHERE {where_sql}
            GROUP BY s.model
            ORDER BY COUNT(DISTINCT s.id) FILTER (WHERE s.outcome IS NOT NULL) DESC
        """, params, fetch=True)

    # Fetch top outcome_reasons + security counts per model
    top_reasons_map, security_counts = _fetch_top_reasons(cutoff, project, stack)

    models = []
    for r in (rows or []):
        rated = int(r.get('rated_sessions') or 0)
        ok = int(r.get('ok_count') or 0)
        nf = int(r.get('needs_fix_count') or 0)
        rev = int(r.get('reverted_count') or 0)
        avg_sev = float(r['avg_severity']) if r.get('avg_severity') else None
        total_cost = float(r.get('total_cost') or 0)

        sec_count = security_counts.get(r['model'], 0)
        score = calculate_quality_score(ok, nf, rev, rated, avg_sev, sec_count)
        rework_rate = round((nf + rev) / rated * 100, 1) if rated > 0 else 0.0
        cost_per_session = round(total_cost / rated, 4) if rated > 0 and total_cost > 0 else None
        cost_per_success = round(total_cost / ok, 4) if ok > 0 and total_cost > 0 else None

        models.append({
            'model': r['model'],
            'provider': _detect_provider(r['model']),
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
            'top_reasons': top_reasons_map.get(r['model'], []),
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
    where_parts = ["s.model IS NOT NULL", "s.model != ''", "s.model NOT LIKE '<%%>'", "ft.file_path IS NOT NULL"]

    if cutoff:
        where_parts.append("s.started_at > %s")
        params.append(cutoff)
    if project:
        where_parts.append("s.project_name = %s")
        params.append(project)

    where_sql = " AND ".join(where_parts)

    rows = execute(f"""
        SELECT
            s.id AS session_id,
            s.model,
            s.outcome,
            COALESCE(s.cost_estimate, 0) AS cost_estimate,
            ft.file_path
        FROM sessions s
        JOIN ai_file_touches ft ON ft.session_id = s.id
        WHERE {where_sql}
    """, params, fetch=True)

    # Step 1: Determine dominant stack per session (>50% of touches)
    session_stacks = {}  # session_id -> {stack: count}
    session_meta = {}    # session_id -> {model, outcome, cost}
    for r in (rows or []):
        sid = r['session_id']
        ext = _ext_from_path(r['file_path'])
        s = STACK_MAP.get(ext)
        if not s:
            continue
        if sid not in session_stacks:
            session_stacks[sid] = {}
            session_meta[sid] = {
                'model': r['model'],
                'outcome': r.get('outcome'),
                'cost': float(r['cost_estimate']),
            }
        session_stacks[sid][s] = session_stacks[sid].get(s, 0) + 1

    # Step 2: Aggregate by model + dominant stack
    matrix_data = {}  # (model, stack) -> {ok, needs_fix, reverted, total, cost}
    for sid, stack_counts in session_stacks.items():
        total_touches = sum(stack_counts.values())
        dominant = max(stack_counts, key=stack_counts.get)
        if stack_counts[dominant] / total_touches < 0.5:
            continue  # no clear dominant stack
        meta = session_meta[sid]
        key = (meta['model'], dominant)
        if key not in matrix_data:
            matrix_data[key] = {'ok': 0, 'needs_fix': 0, 'reverted': 0, 'total': 0, 'cost': 0.0}
        matrix_data[key]['total'] += 1
        matrix_data[key]['cost'] += meta['cost']
        outcome = meta['outcome']
        if outcome in ('ok', 'needs_fix', 'reverted'):
            matrix_data[key][outcome] += 1

    # Build nested matrix: grouped by stack, models nested inside
    stack_groups = {}  # stack -> {model -> metrics}
    for (model, stack), counts in sorted(matrix_data.items()):
        rated = counts['ok'] + counts['needs_fix'] + counts['reverted']
        rework = counts['needs_fix'] + counts['reverted']
        rework_rate = round(rework / rated * 100, 1) if rated > 0 else 0.0
        ok = counts['ok']
        cost = counts['cost']
        score = calculate_quality_score(ok, counts['needs_fix'], counts['reverted'], rated)

        if stack not in stack_groups:
            stack_groups[stack] = {}
        stack_groups[stack][model] = {
            'sessions': counts['total'],
            'rated': rated,
            'rework_rate': rework_rate,
            'cost_per_success': round(cost / ok, 4) if ok > 0 and cost > 0 else None,
            'quality_score': score,
            'grade': score_to_grade(score),
        }

    matrix = [
        {'stack': stack, 'models': models}
        for stack, models in sorted(stack_groups.items())
    ]

    # Generate insights (needs flat list internally)
    flat = []
    for entry in matrix:
        for model, metrics in entry['models'].items():
            flat.append({'model': model, 'stack': entry['stack'], **metrics})
    insights = _generate_stack_insights(flat)

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

    # Cross-stack comparison: find models with large rework-rate differences across stacks
    model_entries = {}
    for entry in matrix:
        if entry['rated'] < 3:
            continue
        m = entry['model']
        if m not in model_entries:
            model_entries[m] = []
        model_entries[m].append(entry)

    for m, entries in model_entries.items():
        if len(entries) < 2:
            continue
        best = min(entries, key=lambda e: e['rework_rate'])
        worst = max(entries, key=lambda e: e['rework_rate'])
        if best['rework_rate'] > 0 and worst['rework_rate'] / best['rework_rate'] >= 2:
            insights.append(
                f"{m} has {worst['rework_rate'] / best['rework_rate']:.1f}x higher rework rate "
                f"on {worst['stack']} ({worst['rework_rate']}%) vs {best['stack']} ({best['rework_rate']}%)."
            )
            break  # max one cross-stack insight

    # Find worst rework rate across stacks
    worst_all = [e for e in matrix if e['rated'] >= 3]
    if worst_all:
        worst_entry = max(worst_all, key=lambda e: e['rework_rate'])
        if worst_entry['rework_rate'] > 20:
            insights.append(
                f"High rework rate for {worst_entry['model']} on {worst_entry['stack']}: "
                f"{worst_entry['rework_rate']}% - consider alternatives."
            )

    return insights


# Trend + Recommendation live in model_trend_service.py (Split wg. Zeilenlimit)
from services.model_trend_service import get_model_trend, recommend_model  # noqa: F401, E402
