/**
 * Dashboard-Widgets: Charts, Heatmap, Statistiken
 * Nutzt Chart.js (via CDN in index.html)
 */

const CHART_COLORS = [
    '#4fc3f7', '#66bb6a', '#ffa726', '#ef5350', '#ab47bc',
    '#26c6da', '#9ccc65', '#ffca28', '#ec407a', '#7e57c2',
    '#42a5f5', '#8bc34a', '#ff7043', '#78909c', '#5c6bc0',
];

let chartInstances = {};

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

async function loadWidgets() {
    window._widgetsLoaded = true;

    try {
        const [overview, activity] = await Promise.all([
            api.get('/api/widgets/overview'),
            api.get('/api/widgets/activity'),
        ]);

        renderNumberCards(overview);
        renderHeatmap(activity.heatmap);
        renderTypeChart(overview.project_types);
        renderTechChart(overview.technologies);
        renderSessionChart(overview.sessions);
        renderTopActive(overview.top_active);
    } catch (e) {
        console.error('Widget error:', e);
    }
}

function renderNumberCards(data) {
    var t = data.totals || {};
    var a = data.activity_status || {};
    setText('wTotalProjects', t.projects);
    setText('wActiveProjects', a.active);
    setText('wContainers', (data.containers || {}).running + ' / ' + (data.containers || {}).total);
    setText('wGitea', t.with_gitea);
}

function setText(id, value) {
    var el = document.querySelector('#' + id + ' .widget-card-value');
    if (el) el.textContent = value || '0';
}

function renderHeatmap(days) {
    var el = document.getElementById('wHeatmap');
    if (!el || !days) return;

    var maxCount = Math.max(1, ...days.map(d => d.count));
    var html = '<div class="heatmap-row">';

    days.forEach(function(d) {
        var intensity = d.count / maxCount;
        var bg = intensity === 0 ? '#1a1a1a' :
                 intensity < 0.25 ? '#0e3a1e' :
                 intensity < 0.5 ? '#1a6b2f' :
                 intensity < 0.75 ? '#2ea043' : '#3fb950';
        var label = d.date.slice(5) + ': ' + d.count + ' activities';
        html += '<div class="heatmap-cell" title="' + label + '" style="background:' + bg + '">';
        html += '<span class="heatmap-day">' + d.weekday.slice(0, 2) + '</span>';
        html += '</div>';
    });
    html += '</div>';

    // Legende
    html += '<div class="heatmap-legend">';
    html += '<span style="color:#555;font-size:10px">Less</span>';
    ['#1a1a1a', '#0e3a1e', '#1a6b2f', '#2ea043', '#3fb950'].forEach(function(c) {
        html += '<div style="width:12px;height:12px;border-radius:2px;background:' + c + '"></div>';
    });
    html += '<span style="color:#555;font-size:10px">More</span>';
    html += '</div>';

    el.innerHTML = html;
}

function renderTypeChart(types) {
    if (!types || !window.Chart) return;
    var ctx = document.getElementById('chartTypes');
    if (!ctx) return;

    var labels = Object.keys(types);
    var values = Object.values(types);

    destroyChart('types');
    chartInstances['types'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: CHART_COLORS.slice(0, labels.length),
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right', labels: { color: '#aaa', font: { size: 11 } } }
            }
        }
    });
}

function renderTechChart(techs) {
    if (!techs || !window.Chart) return;
    var ctx = document.getElementById('chartTech');
    if (!ctx) return;

    var sorted = Object.entries(techs).sort((a, b) => b[1] - a[1]).slice(0, 10);
    var labels = sorted.map(e => e[0]);
    var values = sorted.map(e => e[1]);

    destroyChart('tech');
    chartInstances['tech'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: '#4fc3f7',
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: '#222' }, ticks: { color: '#888' } },
                y: { grid: { display: false }, ticks: { color: '#ccc', font: { size: 11 } } },
            }
        }
    });
}

function renderSessionChart(sessions) {
    if (!sessions || !sessions.days || !window.Chart) return;
    var ctx = document.getElementById('chartSessions');
    if (!ctx) return;

    var labels = sessions.days.map(d => d.date.slice(5));
    var sessionCounts = sessions.days.map(d => d.sessions);
    var durations = sessions.days.map(d => d.duration_min);

    destroyChart('sessions');
    chartInstances['sessions'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sessions',
                    data: sessionCounts,
                    backgroundColor: '#4fc3f7',
                    borderRadius: 4,
                    yAxisID: 'y',
                },
                {
                    label: 'Minutes',
                    data: durations,
                    type: 'line',
                    borderColor: '#66bb6a',
                    backgroundColor: 'rgba(102,187,106,0.1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#aaa', font: { size: 11 } } } },
            scales: {
                x: { grid: { color: '#222' }, ticks: { color: '#888' } },
                y: { position: 'left', grid: { color: '#222' }, ticks: { color: '#4fc3f7' },
                     title: { display: true, text: 'Sessions', color: '#4fc3f7' } },
                y1: { position: 'right', grid: { display: false }, ticks: { color: '#66bb6a' },
                      title: { display: true, text: 'Minutes', color: '#66bb6a' } },
            }
        }
    });
}

function renderTopActive(projects) {
    var el = document.getElementById('wTopActive');
    if (!el) return;

    if (!projects || !projects.length) {
        el.innerHTML = '<div style="padding:16px;color:#555;text-align:center">No active projects in the last 7 days</div>';
        return;
    }

    var html = '';
    projects.forEach(function(p) {
        var statusDot = p.git_status === 'geaendert' || p.git_status === 'geändert' || p.git_status === 'modified'
            ? '<span style="color:#ffa726" title="Unsaved changes">&#9679;</span>'
            : '<span style="color:#66bb6a" title="Clean">&#9679;</span>';
        var typeLabel = p.type === 'monorepo' ? '<span style="color:#ab47bc;font-size:10px;margin-left:4px">MONO</span>' : '';

        html += '<div class="widget-list-item" onclick="location.href=\'/project/' + encodeURIComponent(p.name) + '\'">';
        html += statusDot + ' ';
        html += '<span class="widget-list-name">' + p.name + '</span>';
        html += typeLabel;
        html += '<span class="widget-list-time">' + (p.last_activity || '').slice(0, 16) + '</span>';
        html += '</div>';
    });
    el.innerHTML = html;
}
