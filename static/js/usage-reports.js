/* Usage Reports - Chart.js Rendering + Controls */
/* globals: api, formatTokens, formatDate, escapeHtml (from base.js) */

var _urPeriod = 'daily';
var _urPreset = '7days';
var _urCharts = {};

document.addEventListener('DOMContentLoaded', urInit);

function urInit() {
    urLoad();
}

function urLoad() {
    var params = 'period=' + _urPeriod + '&preset=' + _urPreset;
    if (_urPreset === 'custom') {
        var s = document.getElementById('urStartDate').value;
        var e = document.getElementById('urEndDate').value;
        if (s) params += '&start=' + s;
        if (e) params += '&end=' + e;
    }
    api.get('/api/usage-reports/data?' + params)
        .then(function(data) { urRender(data); })
        .catch(function(err) { console.error('Usage reports error:', err); });
}

function urRender(data) {
    var empty = !data.rows || data.rows.length === 0;
    document.getElementById('urEmpty').style.display = empty ? 'block' : 'none';
    document.querySelector('.ur-charts').style.display = empty ? 'none' : 'grid';
    document.querySelector('.ur-table-wrap').style.display = empty ? 'none' : 'block';
    document.getElementById('urHourlyCard').style.display = (_urPeriod === 'daily' && !empty) ? 'block' : 'none';

    urRenderSummary(data.summary);
    if (!empty) {
        urRenderCostChart(data.rows);
        urRenderTokenChart(data.rows);
        urRenderModelChart(data.model_distribution);
        if (_urPeriod === 'daily' && data.hourly) urRenderHourlyChart(data.hourly);
        urRenderTable(data.rows);
    }
}

function urRenderSummary(s) {
    document.getElementById('urKpiCost').textContent = '$' + fmtCost(s.total_cost);
    document.getElementById('urKpiTokens').textContent = fmtNum(s.total_tokens);
    document.getElementById('urKpiMessages').textContent = fmtNum(s.total_messages);
    document.getElementById('urKpiSessions').textContent = fmtNum(s.total_sessions);
    document.getElementById('urKpiAvgCost').textContent = '$' + fmtCost(s.avg_daily_cost);
    document.getElementById('urKpiApiCalls').textContent = fmtNum(s.total_api_calls);
}

function urRenderCostChart(rows) {
    var ctx = document.getElementById('urCostChart');
    if (_urCharts.cost) _urCharts.cost.destroy();

    _urCharts.cost = new Chart(ctx, {
        type: 'line',
        data: {
            labels: rows.map(function(r) { return fmtLabel(r.date); }),
            datasets: [{
                label: 'Kosten ($)',
                data: rows.map(function(r) { return r.cost; }),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointHoverRadius: 5,
            }]
        },
        options: urChartOpts('$')
    });
}

function urRenderTokenChart(rows) {
    var ctx = document.getElementById('urTokenChart');
    if (_urCharts.tokens) _urCharts.tokens.destroy();

    _urCharts.tokens = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: rows.map(function(r) { return fmtLabel(r.date); }),
            datasets: [
                { label: 'Input', data: rows.map(function(r) { return r.input_tokens; }), backgroundColor: '#3b82f6' },
                { label: 'Output', data: rows.map(function(r) { return r.output_tokens; }), backgroundColor: '#10b981' },
                { label: 'Cache Read', data: rows.map(function(r) { return r.cache_read; }), backgroundColor: '#6366f1', hidden: true },
                { label: 'Cache Create', data: rows.map(function(r) { return r.cache_create; }), backgroundColor: '#f59e0b', hidden: true },
            ]
        },
        options: Object.assign({}, urChartOpts(), { plugins: { legend: { display: true, labels: { color: '#8888aa', font: { size: 11 } } } } })
    });
}

function urRenderModelChart(models) {
    var ctx = document.getElementById('urModelChart');
    if (_urCharts.model) _urCharts.model.destroy();

    var colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
    _urCharts.model = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: models.map(function(m) { return m.model; }),
            datasets: [{
                data: models.map(function(m) { return m.cost; }),
                backgroundColor: colors.slice(0, models.length),
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'right', labels: { color: '#8888aa', font: { size: 11 }, padding: 12 } },
                tooltip: {
                    callbacks: {
                        label: function(ctx) { return ctx.label + ': $' + fmtCost(ctx.raw) + ' (' + models[ctx.dataIndex].pct + '%)'; }
                    }
                }
            }
        }
    });
}

function urRenderHourlyChart(hourly) {
    var ctx = document.getElementById('urHourlyChart');
    if (_urCharts.hourly) _urCharts.hourly.destroy();

    _urCharts.hourly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hourly.map(function(h) { return h.hour + ':00'; }),
            datasets: [{
                label: 'Kosten ($)',
                data: hourly.map(function(h) { return h.cost; }),
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderRadius: 3,
            }]
        },
        options: urChartOpts('$')
    });
}

function urRenderTable(rows) {
    var tbody = document.getElementById('urTableBody');
    var html = '';
    for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        html += '<tr>' +
            '<td>' + escapeHtml(fmtLabel(r.date)) + '</td>' +
            '<td class="cost-cell">$' + fmtCost(r.cost) + '</td>' +
            '<td>' + fmtNum(r.input_tokens) + '</td>' +
            '<td>' + fmtNum(r.output_tokens) + '</td>' +
            '<td>' + fmtNum(r.cache_read) + '</td>' +
            '<td>' + fmtNum(r.cache_create) + '</td>' +
            '<td>' + r.messages + '</td>' +
            '<td>' + r.sessions + '</td>' +
            '<td>' + r.api_calls + '</td>' +
            '</tr>';
    }
    tbody.innerHTML = html;
}

/* Controls */
function urChangePeriod(p) {
    _urPeriod = p;
    var tabs = document.querySelectorAll('.ur-tab');
    tabs.forEach(function(t) { t.classList.toggle('active', t.dataset.period === p); });
    urLoad();
}

function urChangePreset(val) {
    _urPreset = val;
    document.getElementById('urCustomRange').style.display = val === 'custom' ? 'flex' : 'none';
    if (val !== 'custom') urLoad();
}

function urApplyCustom() {
    _urPreset = 'custom';
    urLoad();
}

/* Chart defaults */
function urChartOpts(prefix) {
    return {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { intersect: false, mode: 'index' },
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#8888aa', font: { size: 10 } } },
            y: {
                grid: { color: 'rgba(255,255,255,0.05)' },
                ticks: {
                    color: '#8888aa', font: { size: 10 },
                    callback: function(v) { return prefix ? prefix + fmtCost(v) : fmtNum(v); }
                }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#1a1a2e', borderColor: '#2a2a3e', borderWidth: 1,
                titleColor: '#e0e0e0', bodyColor: '#e0e0e0',
                callbacks: {
                    label: function(ctx) {
                        var val = prefix ? prefix + fmtCost(ctx.raw) : fmtNum(ctx.raw);
                        return ctx.dataset.label + ': ' + val;
                    }
                }
            }
        }
    };
}

/* Formatting helpers */
function fmtCost(v) {
    if (v == null) return '0';
    if (v >= 1000) return v.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    if (v >= 100) return v.toFixed(0);
    if (v >= 1) return v.toFixed(2);
    return v.toFixed(4);
}

function fmtNum(v) {
    if (v == null) return '0';
    if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
    if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
    if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
    return String(v);
}

function fmtLabel(d) {
    if (!d) return '';
    if (d.length === 7) return d; // YYYY-MM
    if (d.length === 10) {
        var parts = d.split('-');
        return parts[2] + '.' + parts[1] + '.';
    }
    return d;
}
