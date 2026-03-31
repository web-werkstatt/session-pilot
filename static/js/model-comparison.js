/**
 * Sprint 11: Model Quality Comparison
 * Compares AI model performance across sessions with drill-down capabilities.
 */

const MODEL_COLORS = [
    '#4fc3f7', '#81c784', '#ffb74d', '#e57373', '#ba68c8',
    '#4dd0e1', '#aed581', '#ff8a65', '#f06292', '#7986cb'
];

const BACKEND_STACKS = ['python'];
const FRONTEND_STACKS = ['typescript', 'javascript', 'css', 'markup'];

let _period = '90d';
let _project = '';
let _stackFilter = 'all';
let _radarChart = null;
let _stackChart = null;
let _trendCache = {};


async function loadModelComparison() {
    var tableBody = document.getElementById('mcTableBody');
    if (tableBody) tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';

    _trendCache = {};

    var params = new URLSearchParams();
    params.set('period', _period);
    if (_project) params.set('project', _project);
    if (_stackFilter !== 'all') params.set('stack', _stackFilter);
    var qs = params.toString();

    try {
        var results = await Promise.all([
            api.get('/api/analytics/model-comparison?' + qs),
            api.get('/api/analytics/model-by-stack?' + qs),
            loadAllTrends(qs)
        ]);

        var compData = results[0];
        var stackData = results[1];

        var models = compData.models || [];
        renderComparisonTable(models);
        renderKPIs(models, compData.recommendation);
        renderRadarChart(models);
        renderStackChart(stackData.matrix || []);
        renderInsights(stackData.insights || []);
    } catch (err) {
        console.error('Model comparison load failed:', err);
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load data</td></tr>';
        }
    }
}


async function loadAllTrends(qs) {
    // Pre-load trend data for sparklines. We fetch the comparison first implicitly
    // via the parallel call, but trends need model names. We do a best-effort
    // approach: fetch comparison, then trends. Since loadAllTrends runs in
    // parallel with comparison, we fetch comparison again (cheap, cached on server).
    try {
        var compData = await api.get('/api/analytics/model-comparison?' + qs);
        var models = compData.models || [];
        var trendPromises = models.map(function(m) {
            var trendParams = new URLSearchParams();
            trendParams.set('model', m.model);
            trendParams.set('period', _period);
            trendParams.set('granularity', 'weekly');
            if (_project) trendParams.set('project', _project);
            return api.get('/api/analytics/model-trend?' + trendParams.toString())
                .then(function(data) { _trendCache[m.model] = data.trends || []; })
                .catch(function() { _trendCache[m.model] = []; });
        });
        await Promise.all(trendPromises);
    } catch (e) {
        // Trends are optional, table still renders without sparklines
    }
}


function renderComparisonTable(models) {
    var tbody = document.getElementById('mcTableBody');
    if (!tbody) return;

    if (!models.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No model data available for this period</td></tr>';
        return;
    }

    var rows = models.map(function(m) {
        var hasRatings = m.rated_sessions > 0;
        var modelLink = '<a href="/sessions?model=' + encodeURIComponent(m.model) + '">'
            + escapeHtml(m.model) + '</a>';

        var sessionsText = m.total_sessions + ' (' + m.rated_sessions + ' rated)';

        var reworkHtml = hasRatings
            ? '<a href="/sessions?model=' + encodeURIComponent(m.model)
              + '&outcome=needs_fix,reverted" title="Show sessions needing fixes">'
              + m.rework_rate.toFixed(1) + '%</a>'
            : '<span style="color:var(--text-muted)">-</span>';

        var costText = m.cost_per_success != null ? '$' + m.cost_per_success.toFixed(2) : '-';

        var qualityHtml = hasRatings
            ? renderGradeBadge(m.grade) + ' ' + renderScoreBar(m.quality_score, m.grade)
              + ' <span class="score-value">' + m.quality_score.toFixed(1) + '</span>'
            : '<span style="color:var(--text-muted)">No ratings</span>';

        var trendEntry = (_trendCache[m.model] || [])[0];
        var periods = trendEntry ? trendEntry.periods || [] : [];
        var sparkHtml = periods.length > 1 ? renderSparkline(periods) : '<span style="color:var(--text-muted)">-</span>';

        return '<tr>'
            + '<td>' + modelLink + '</td>'
            + '<td>' + sessionsText + '</td>'
            + '<td>' + reworkHtml + '</td>'
            + '<td>' + costText + '</td>'
            + '<td>' + qualityHtml + '</td>'
            + '<td>' + sparkHtml + '</td>'
            + '</tr>';
    });

    tbody.innerHTML = rows.join('');
}


function renderScoreBar(score, grade) {
    var pct = Math.max(0, Math.min(100, score));
    return '<div class="score-bar">'
        + '<div class="score-bar__fill score-bar__fill--' + escapeHtml(grade) + '" style="width:' + pct + '%"></div>'
        + '</div>';
}


function renderGradeBadge(grade) {
    return '<span class="grade-badge grade-badge--' + escapeHtml(grade) + '">' + escapeHtml(grade) + '</span>';
}


function renderSparkline(trendData) {
    if (!trendData || trendData.length < 2) return '';

    var width = 80;
    var height = 24;
    var padding = 2;

    var values = trendData.map(function(d) { return d.rework_rate; });
    var minVal = Math.min.apply(null, values);
    var maxVal = Math.max.apply(null, values);
    var range = maxVal - minVal || 1;

    var points = values.map(function(v, i) {
        var x = padding + (i / (values.length - 1)) * (width - 2 * padding);
        var y = height - padding - ((v - minVal) / range) * (height - 2 * padding);
        return x.toFixed(1) + ',' + y.toFixed(1);
    });

    var first = values[0];
    var last = values[values.length - 1];
    var trend;
    if (last < first - 1) trend = 'improving';
    else if (last > first + 1) trend = 'degrading';
    else trend = 'stable';

    return '<svg class="sparkline sparkline--' + trend + '" width="' + width + '" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '">'
        + '<polyline fill="none" stroke="currentColor" stroke-width="1.5" points="' + points.join(' ') + '"/>'
        + '</svg>';
}


function renderRadarChart(models) {
    var canvas = document.getElementById('radarChart');
    if (!canvas) return;

    if (_radarChart) {
        _radarChart.destroy();
        _radarChart = null;
    }

    var subset = models.slice(0, 5);
    if (!subset.length) return;

    var datasets = subset.map(function(m, i) {
        var quality = m.quality_score || 0;
        var costEff = Math.max(0, Math.min(100, 100 - (m.cost_per_success || 0) * 10));
        var speed = Math.max(0, Math.min(100, 100 - (m.avg_duration_min || 0) * 2));

        return {
            label: m.model,
            data: [quality, costEff, speed],
            borderColor: MODEL_COLORS[i % MODEL_COLORS.length],
            backgroundColor: MODEL_COLORS[i % MODEL_COLORS.length] + '33',
            pointBackgroundColor: MODEL_COLORS[i % MODEL_COLORS.length],
            borderWidth: 2,
            pointRadius: 3
        };
    });

    _radarChart = new Chart(canvas, {
        type: 'radar',
        data: {
            labels: ['Quality', 'Cost Efficiency', 'Speed'],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 20, display: false },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#ccc', font: { size: 12 } }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#ccc', boxWidth: 12, padding: 15 }
                }
            }
        }
    });
}


function renderStackChart(matrix) {
    var canvas = document.getElementById('stackChart');
    if (!canvas) return;

    if (_stackChart) {
        _stackChart.destroy();
        _stackChart = null;
    }

    if (!matrix || !matrix.length) return;

    var filtered = filterMatrixByStack(matrix);
    if (!filtered.length) return;

    // Collect unique stacks and models
    var stackSet = {};
    var modelSet = {};
    filtered.forEach(function(entry) {
        stackSet[entry.stack] = true;
        modelSet[entry.model] = true;
    });
    var stacks = Object.keys(stackSet).sort();
    var models = Object.keys(modelSet).sort();

    // Build lookup: model+stack -> rework_rate
    var lookup = {};
    filtered.forEach(function(entry) {
        lookup[entry.model + '|' + entry.stack] = entry.rework_rate;
    });

    var datasets = models.map(function(model, i) {
        return {
            label: model,
            data: stacks.map(function(stack) { return lookup[model + '|' + stack] || 0; }),
            backgroundColor: MODEL_COLORS[i % MODEL_COLORS.length],
            borderColor: MODEL_COLORS[i % MODEL_COLORS.length],
            borderWidth: 1
        };
    });

    _stackChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: stacks,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: { color: '#ccc' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: '#ccc', callback: function(v) { return v + '%'; } },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    title: { display: true, text: 'Rework Rate %', color: '#ccc' }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#ccc', boxWidth: 12, padding: 15 }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%';
                        }
                    }
                }
            }
        }
    });
}


function filterMatrixByStack(matrix) {
    if (_stackFilter === 'all') return matrix;

    var allowed = _stackFilter === 'backend' ? BACKEND_STACKS : FRONTEND_STACKS;
    return matrix.filter(function(entry) {
        return allowed.indexOf(entry.stack) !== -1;
    });
}


function renderKPIs(models, recommendation) {
    var countEl = document.getElementById('mcModelCount');
    var scoreEl = document.getElementById('mcAvgScore');
    var costEl = document.getElementById('mcBestCost');
    var recEl = document.getElementById('mcRecommendation');

    if (countEl) countEl.textContent = models.length;

    if (scoreEl && models.length) {
        var avgScore = models.reduce(function(s, m) { return s + m.quality_score; }, 0) / models.length;
        scoreEl.textContent = avgScore.toFixed(1);
    }

    if (costEl && models.length) {
        var costs = models.filter(function(m) { return m.cost_per_success != null; })
            .map(function(m) { return m.cost_per_success; });
        costEl.textContent = costs.length ? '$' + Math.min.apply(null, costs).toFixed(2) : '-';
    }

    if (recEl) recEl.textContent = recommendation || '-';
}


function renderInsights(insights) {
    var el = document.getElementById('mcInsights');
    if (!el) return;
    if (!insights.length) {
        el.innerHTML = '<li style="color:var(--text-muted)">No insights available yet</li>';
        return;
    }
    el.innerHTML = insights.map(function(i) { return '<li>' + escapeHtml(i) + '</li>'; }).join('');
}


function setStackFilter(type) {
    _stackFilter = type;

    // Update toggle button active states
    var buttons = document.querySelectorAll('[data-stack-filter]');
    buttons.forEach(function(btn) {
        if (btn.getAttribute('data-stack-filter') === type) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Re-fetch includes stack filter for comparison endpoint too
    loadModelComparison();
}


function setPeriod(period) {
    _period = period;

    var buttons = document.querySelectorAll('[data-period]');
    buttons.forEach(function(btn) {
        if (btn.getAttribute('data-period') === period) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    loadModelComparison();
}


function setProject(project) {
    _project = project;
    loadModelComparison();
}


async function populateProjectFilter() {
    var sel = document.getElementById('filterProject');
    if (!sel || sel.options.length > 1) return;
    try {
        var results = await Promise.all([
            api.get('/api/sessions/filters'),
            api.get('/api/data')
        ]);
        var sessionProjects = new Set(results[0].projects || []);
        var realProjects = (results[1].projects || []).map(function(p) { return p.name; });
        var filtered = realProjects.filter(function(n) { return sessionProjects.has(n); }).sort();
        filtered.forEach(function(name) {
            var opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            sel.appendChild(opt);
        });
    } catch (e) { /* ignore */ }
}

document.addEventListener('DOMContentLoaded', function() {
    populateProjectFilter();
    loadModelComparison();
});
