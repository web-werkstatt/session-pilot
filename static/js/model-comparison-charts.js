/**
 * Sprint 11: Model Comparison Charts
 * Radar, Scatter (Bubble), Stack-Bar Charts + helpers.
 * Depends on: MODEL_COLORS, _radarChart, _scatterChart, _stackChart,
 *             _stackFilter, BACKEND_STACKS, FRONTEND_STACKS from model-comparison.js
 */

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


function renderScatterChart(models) {
    var canvas = document.getElementById('scatterChart');
    if (!canvas) return;

    if (_scatterChart) {
        _scatterChart.destroy();
        _scatterChart = null;
    }

    var filtered = models.filter(function(m) {
        return m.cost_per_success != null && m.rated_sessions > 0;
    });
    if (!filtered.length) return;

    var maxSessions = Math.max.apply(null, filtered.map(function(m) { return m.rated_sessions; }));

    var datasets = filtered.map(function(m, i) {
        var radius = Math.max(6, (m.rated_sessions / (maxSessions || 1)) * 30);
        return {
            label: m.model,
            data: [{x: m.cost_per_success, y: m.rework_rate, r: radius}],
            backgroundColor: MODEL_COLORS[i % MODEL_COLORS.length] + 'aa',
            borderColor: MODEL_COLORS[i % MODEL_COLORS.length],
            borderWidth: 1
        };
    });

    _scatterChart = new Chart(canvas, {
        type: 'bubble',
        data: {datasets: datasets},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    title: {display: true, text: '$/Success', color: '#ccc'},
                    ticks: {color: '#ccc', callback: function(v) { return '$' + v; }},
                    grid: {color: 'rgba(255,255,255,0.05)'}
                },
                y: {
                    beginAtZero: true,
                    title: {display: true, text: 'Rework Rate %', color: '#ccc'},
                    ticks: {color: '#ccc', callback: function(v) { return v + '%'; }},
                    grid: {color: 'rgba(255,255,255,0.05)'}
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {color: '#ccc', boxWidth: 12, padding: 15}
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            var d = ctx.raw;
                            return ctx.dataset.label + ': $' + d.x.toFixed(2) + '/success, '
                                + d.y.toFixed(1) + '% rework';
                        }
                    }
                }
            }
        }
    });
}


function flattenMatrix(matrix) {
    var flat = [];
    (matrix || []).forEach(function(entry) {
        var stack = entry.stack;
        Object.keys(entry.models || {}).forEach(function(model) {
            var m = entry.models[model];
            flat.push({model: model, stack: stack, rework_rate: m.rework_rate, sessions: m.sessions,
                rated: m.rated, cost_per_success: m.cost_per_success, quality_score: m.quality_score, grade: m.grade});
        });
    });
    return flat;
}


function renderStackChart(matrix) {
    var canvas = document.getElementById('stackChart');
    if (!canvas) return;

    if (_stackChart) {
        _stackChart.destroy();
        _stackChart = null;
    }

    var flat = flattenMatrix(matrix);
    if (!flat.length) return;

    var filtered = filterMatrixByStack(flat);
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
            onClick: function(evt, elements) {
                if (!elements.length) return;
                var el = elements[0];
                var model = models[el.datasetIndex];
                var stack = stacks[el.index];
                window.location.href = '/sessions?model=' + encodeURIComponent(model)
                    + '&outcome=needs_fix,reverted&stack=' + encodeURIComponent(stack);
            },
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
    canvas.style.cursor = 'pointer';
}


function filterMatrixByStack(matrix) {
    if (_stackFilter === 'all') return matrix;

    var allowed = _stackFilter === 'backend' ? BACKEND_STACKS : FRONTEND_STACKS;
    return matrix.filter(function(entry) {
        return allowed.indexOf(entry.stack) !== -1;
    });
}
