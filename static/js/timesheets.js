let currentDays = 30;
let dailyChart, projectDonut, toolChart, modelChart;
let dailyMetric = 'cost';
let projectsData = [];
let projectSort = 'cost';

const CHART_COLORS = ['#0078d4','#4fc3f7','#cf6ff7','#6ff7b0','#f7a96f','#f76f6f','#f7f06f','#6f9ef7','#b06ff7','#6ff7e0'];

function getDays() { return parseInt(document.getElementById('periodSelect').value); }
function getAccount() { return document.getElementById('filterAccount').value; }
function getProject() { return document.getElementById('filterProject').value; }

document.addEventListener('DOMContentLoaded', function() {
    const sel = document.getElementById('filterProject');
    if (!sel) return;
    if (!sel.value && typeof getActiveProjectContext === 'function') {
        const activeProject = getActiveProjectContext();
        if (activeProject) sel.value = activeProject;
    }
    sel.addEventListener('change', function() {
        if (sel.value && typeof setActiveProjectContext === 'function') {
            setActiveProjectContext(sel.value);
        }
    });
});

function changePeriod() {
    currentDays = getDays();
    const labels = {7:'7 days',14:'14 days',30:'30 days',90:'Quarter',180:'Half year',365:'Year'};
    document.getElementById('periodLabel').textContent = 'Last ' + (labels[currentDays] || currentDays + ' days');
    reloadAll();
}

async function reloadAll() {
    if (getProject() && typeof setActiveProjectContext === 'function') {
        setActiveProjectContext(getProject());
    }
    const loader = document.getElementById('tsLoading');
    if (loader) loader.style.display = '';
    try {
        await Promise.all([loadSummary(), loadDaily(), loadProjects(), loadTools(), loadModels(), loadRework(), loadContext()]);
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

function trendHtml(val, invert) {
    if (val === null || val === undefined) return '';
    const isUp = val > 0;
    const cls = val === 0 ? 'neutral' : (invert ? (isUp ? 'down' : 'up') : (isUp ? 'up' : 'down'));
    const arrow = val > 0 ? '&#9650;' : val < 0 ? '&#9660;' : '&#8211;';
    return `<span class="ts-kpi-trend ${cls}">${arrow} ${Math.abs(val)}% vs. prev. period</span>`;
}

async function loadSummary() {
    const params = new URLSearchParams({days: getDays()});
    if (getAccount()) params.set('account', getAccount());
    if (getProject()) params.set('project', getProject());

    try {
        const d = await api.get('/api/timesheets/summary?' + params);

        document.getElementById('kpiSessions').textContent = d.sessions.toLocaleString('en-US');
        document.getElementById('kpiDuration').textContent = d.duration_formatted;
        document.getElementById('kpiTokens').textContent = formatTokens(d.total_tokens);
        document.getElementById('kpiCost').textContent = d.total_cost_formatted;
        document.getElementById('kpiAvgCost').textContent = '$' + d.avg_cost.toFixed(2);
        document.getElementById('kpiAvgDuration').textContent = d.avg_duration_formatted + ' / Session';

        document.getElementById('kpiSessionsTrend').innerHTML = trendHtml(d.trends.sessions, true);
        document.getElementById('kpiDurationTrend').innerHTML = trendHtml(d.trends.duration, false);
        document.getElementById('kpiTokensTrend').innerHTML = trendHtml(d.trends.tokens, false);
        document.getElementById('kpiCostTrend').innerHTML = trendHtml(d.trends.cost, false);
    } catch(e) { console.error('Summary error:', e); }
}

async function loadDaily() {
    const params = new URLSearchParams({days: getDays()});
    if (getAccount()) params.set('account', getAccount());
    if (getProject()) params.set('project', getProject());

    try {
        const data = await api.get('/api/timesheets/daily?' + params);

        const labels = data.map(d => {
            const dt = new Date(d.date);
            return dt.toLocaleDateString('en-US', {day:'2-digit', month:'2-digit'});
        });

        const metricMap = {
            cost: {data: data.map(d => d.cost), label: 'Cost ($)', color: '#4fc3f7'},
            duration: {data: data.map(d => d.duration_h), label: 'Hours', color: '#6ff7b0'},
            tokens: {data: data.map(d => (d.tokens_in + d.tokens_out) / 1e6), label: 'Tokens (M)', color: '#cf6ff7'},
            sessions: {data: data.map(d => d.sessions), label: 'Sessions', color: '#f7a96f'},
        };
        const m = metricMap[dailyMetric];

        if (dailyChart) dailyChart.destroy();
        dailyChart = new Chart(document.getElementById('dailyChart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: m.label,
                    data: m.data,
                    backgroundColor: m.color + '88',
                    borderColor: m.color,
                    borderWidth: 1,
                    borderRadius: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {legend: {display: false}},
                scales: {
                    y: {beginAtZero: true, grid: {color: '#2a2a2a'}, ticks: {color: '#888', font: {size: 11}}},
                    x: {grid: {display: false}, ticks: {color: '#888', font: {size: 10}, maxRotation: 45}}
                }
            }
        });
    } catch(e) { console.error('Daily error:', e); }
}

function setDailyMetric(metric) {
    dailyMetric = metric;
    document.querySelectorAll('.ts-toggle').forEach(b => b.classList.toggle('active', b.dataset.metric === metric));
    loadDaily();
}

async function loadProjects() {
    const params = new URLSearchParams({days: getDays()});
    if (getAccount()) params.set('account', getAccount());

    try {
        projectsData = await api.get('/api/timesheets/projects?' + params);

        const top = projectsData.slice(0, 8);
        const rest = projectsData.slice(8);
        const donutLabels = top.map(p => p.project || 'unknown');
        const donutData = top.map(p => p.cost);
        if (rest.length) {
            donutLabels.push('Other (' + rest.length + ')');
            donutData.push(rest.reduce((s,p) => s + p.cost, 0));
        }

        if (projectDonut) projectDonut.destroy();
        projectDonut = new Chart(document.getElementById('projectDonut'), {
            type: 'doughnut',
            data: {
                labels: donutLabels,
                datasets: [{
                    data: donutData,
                    backgroundColor: CHART_COLORS,
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {color: '#ccc', font: {size: 11}, padding: 8, boxWidth: 12}
                    }
                }
            }
        });

        const sel = document.getElementById('filterProject');
        if (sel.options.length <= 1) {
            projectsData.forEach(p => {
                if (p.project) {
                    const opt = document.createElement('option');
                    opt.value = p.project;
                    opt.textContent = p.project;
                    sel.appendChild(opt);
                }
            });
            if (!sel.value && typeof getActiveProjectContext === 'function') {
                const activeProject = getActiveProjectContext();
                if (activeProject) sel.value = activeProject;
            }
        }

        renderProjectTable();
    } catch(e) { console.error('Projects error:', e); }
}

function renderProjectTable() {
    const tbody = document.getElementById('projectTableBody');
    if (!projectsData.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No data</td></tr>';
        return;
    }

    const maxTokens = Math.max(1, ...projectsData.map(p => p.tokens_in + p.tokens_out));

    tbody.innerHTML = projectsData.map(p => {
        const totalTokens = p.tokens_in + p.tokens_out;
        const pctIn = totalTokens ? Math.round(p.tokens_in / totalTokens * 100) : 0;
        const pctOut = 100 - pctIn;
        const barWidth = Math.round(totalTokens / maxTokens * 100);
        const accounts = (p.accounts || []).map(a => `<span class="ts-account-tag">${a}</span>`).join('');

        return `<tr>
            <td><a class="ts-project-link" href="/project/${encodeURIComponent(p.project || '')}">${p.project || 'unknown'}</a></td>
            <td>${p.sessions}</td>
            <td>${p.duration_formatted}</td>
            <td>
                ${formatTokens(totalTokens)}
                <div class="ts-token-bar" style="width:${barWidth}%">
                    <div class="ts-token-in" style="width:${pctIn}%"></div>
                    <div class="ts-token-out" style="width:${pctOut}%"></div>
                </div>
            </td>
            <td>${p.cost_formatted}</td>
            <td>${accounts}</td>
        </tr>`;
    }).join('');
}

function sortProjects(key) {
    const sortKeys = {
        project: p => (p.project || '').toLowerCase(),
        sessions: p => p.sessions,
        duration: p => p.duration_ms,
        tokens: p => p.tokens_in + p.tokens_out,
        cost: p => p.cost,
    };
    const fn = sortKeys[key];
    if (!fn) return;

    // Toggle direction
    if (projectSort === key) {
        projectsData.reverse();
    } else {
        projectSort = key;
        projectsData.sort((a, b) => {
            const va = fn(a), vb = fn(b);
            if (typeof va === 'string') return va.localeCompare(vb);
            return vb - va;
        });
    }

    document.querySelectorAll('.ts-table th').forEach(th => th.classList.remove('active-sort'));
    event.target.classList.add('active-sort');
    renderProjectTable();
}

async function loadTools() {
    try {
        const data = await api.get('/api/timesheets/tools?days=' + getDays());

        const sel = document.getElementById('filterAccount');
        if (sel.options.length <= 1) {
            data.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.account;
                opt.textContent = t.account + ' (' + t.sessions + ')';
                sel.appendChild(opt);
            });
        }

        if (toolChart) toolChart.destroy();
        toolChart = new Chart(document.getElementById('toolChart'), {
            type: 'bar',
            data: {
                labels: data.map(t => t.account),
                datasets: [
                    {
                        label: 'Cost ($)',
                        data: data.map(t => t.cost),
                        backgroundColor: '#4fc3f788',
                        borderColor: '#4fc3f7',
                        borderWidth: 1,
                        borderRadius: 3,
                    },
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {legend: {display: false}},
                scales: {
                    x: {beginAtZero: true, grid: {color: '#2a2a2a'}, ticks: {color: '#888'}},
                    y: {grid: {display: false}, ticks: {color: '#ccc', font: {size: 12}}}
                }
            }
        });
    } catch(e) { console.error('Tools error:', e); }
}

async function loadModels() {
    try {
        const data = await api.get('/api/timesheets/models?days=' + getDays());

        const top = data.slice(0, 6);

        if (modelChart) modelChart.destroy();
        modelChart = new Chart(document.getElementById('modelChart'), {
            type: 'bar',
            data: {
                labels: top.map(m => {
                    let name = m.model;
                    if (name.length > 20) name = name.substring(0, 20) + '...';
                    return name;
                }),
                datasets: [{
                    label: 'Cost ($)',
                    data: top.map(m => m.cost),
                    backgroundColor: CHART_COLORS.slice(0, top.length).map(c => c + '88'),
                    borderColor: CHART_COLORS.slice(0, top.length),
                    borderWidth: 1,
                    borderRadius: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {legend: {display: false}},
                scales: {
                    x: {beginAtZero: true, grid: {color: '#2a2a2a'}, ticks: {color: '#888'}},
                    y: {grid: {display: false}, ticks: {color: '#ccc', font: {size: 11}}}
                }
            }
        });
    } catch(e) { console.error('Models error:', e); }
}

let outcomeDonut, reworkTrend;
const OUTCOME_COLORS = {ok:'#66bb6a', needs_fix:'#ff9800', reverted:'#ef5350', partial:'#f9a825', unrated:'#444'};
const OUTCOME_LABELS = {ok:'OK', needs_fix:'Needs Fix', reverted:'Reverted', partial:'Partial', unrated:'Unrated'};

async function loadRework() {
    const params = new URLSearchParams({days: getDays()});
    if (getAccount()) params.set('account', getAccount());
    if (getProject()) params.set('project', getProject());

    try {
        const d = await api.get('/api/timesheets/rework?' + params);

        document.getElementById('reworkRate').textContent = d.rework_rate + '%';
        document.getElementById('reworkRated').textContent = d.rated_sessions + '/' + d.total_sessions;
        document.getElementById('reworkWasted').textContent = d.costs.wasted_formatted;

        const dist = d.distribution;
        const donutLabels = [];
        const donutData = [];
        const donutColors = [];
        for (const [key, val] of Object.entries(dist)) {
            if (val > 0) {
                donutLabels.push(OUTCOME_LABELS[key] || key);
                donutData.push(val);
                donutColors.push(OUTCOME_COLORS[key] || '#666');
            }
        }

        if (outcomeDonut) outcomeDonut.destroy();
        outcomeDonut = new Chart(document.getElementById('outcomeDonut'), {
            type: 'doughnut',
            data: { labels: donutLabels, datasets: [{data: donutData, backgroundColor: donutColors, borderWidth: 0}] },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: {color:'#ccc', font:{size:10}, padding:6, boxWidth:10} } }
            }
        });

        const weeks = d.trend;
        if (reworkTrend) reworkTrend.destroy();
        reworkTrend = new Chart(document.getElementById('reworkTrend'), {
            type: 'line',
            data: {
                labels: weeks.map(w => {
                    const dt = new Date(w.week);
                    return dt.toLocaleDateString('en-US', {day:'2-digit', month:'2-digit'});
                }),
                datasets: [{
                    label: 'Rework-Rate %',
                    data: weeks.map(w => w.rate),
                    borderColor: '#ef5350',
                    backgroundColor: 'rgba(239,83,80,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: {color:'#2a2a2a'}, ticks: {color:'#888', callback: v => v+'%'} },
                    x: { grid: {display:false}, ticks: {color:'#888', font:{size:10}} }
                }
            }
        });
        const projBody = document.getElementById('reworkProjectBody');
        if (projBody && d.by_project && d.by_project.length) {
            projBody.innerHTML = d.by_project.filter(p => p.rework > 0).map(p =>
                `<tr>
                    <td><a href="/project/${encodeURIComponent(p.project)}" style="color:var(--accent-link)">${escapeHtml(p.project)}</a></td>
                    <td>${p.rated}</td>
                    <td>${p.rework}</td>
                    <td style="color:${p.rate >= 20 ? 'var(--status-error)' : p.rate >= 10 ? 'var(--status-warning)' : 'var(--status-success)'}">${p.rate}%</td>
                    <td><a href="/sessions?project=${encodeURIComponent(p.project)}&outcome=needs_fix,reverted" style="color:var(--accent-link);font-size:11px" title="Show rework sessions">→</a></td>
                </tr>`
            ).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No rework</td></tr>';
        }

        const reasonsBody = document.getElementById('reworkReasonsBody');
        if (reasonsBody && d.reason_distribution) {
            if (!d.reason_distribution.length) {
                reasonsBody.innerHTML = '<span style="color:var(--text-muted)">No outcome reasons set yet.</span>';
            } else {
                reasonsBody.innerHTML = d.reason_distribution.map(r => {
                    const label = escapeHtml(r.reason.replace(/_/g, ' '));
                    const link = `/sessions?outcome_reason=${encodeURIComponent(r.reason)}&outcome=needs_fix,reverted`;
                    return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="min-width:130px">${label}</span><div style="flex:1;height:6px;background:var(--bg-elevated);border-radius:3px;overflow:hidden"><div style="height:100%;width:${r.pct}%;background:var(--accent);border-radius:3px"></div></div><span style="min-width:50px;text-align:right;font-size:11px;color:var(--text-muted)">${r.count}x (${r.pct}%)</span><a href="${link}" style="color:var(--accent-link);font-size:11px" title="Show sessions">→</a></div>`;
                }).join('');
            }
        }

    } catch(e) { console.error('Rework error:', e); }
}

async function loadContext() {
    const params = new URLSearchParams();
    if (getProject()) params.set('project', getProject());

    try {
        const d = await api.get('/api/timesheets/context-effectiveness?' + params);

        const container = document.getElementById('contextCards');
        const changes = d.changes || [];

        if (!changes.length) {
            container.innerHTML = '<div class="ts-ctx-empty">No instruction changes with session data found.</div>';
            document.getElementById('contextDesc').textContent =
                `${d.summary?.length || 0} projects with CLAUDE.md/AGENTS.md changes analyzed.`;
            return;
        }

        document.getElementById('contextDesc').textContent =
            `${changes.length} changes in ${d.summary?.length || 0} projects analyzed.`;

        container.innerHTML = changes.slice(0, 10).map(ch => {
            const date = new Date(ch.date).toLocaleDateString('en-US', {day:'2-digit',month:'2-digit',year:'numeric'});
            const b = ch.before;
            const a = ch.after;
            const delta = ch.deltas;

            return `<div class="ts-ctx-card">
                <div class="ts-ctx-header">
                    <div>
                        <span class="ts-ctx-project">${ch.project}</span>
                        <span class="ts-ctx-file">${ch.file}</span>
                        <span class="ts-ctx-commit">${ch.commit || ''}</span>
                    </div>
                    <div>
                        <span class="ts-ctx-date">${date}</span>
                        <span style="color:#666;font-size:11px;margin-left:8px">+${ch.added}/-${ch.removed} lines</span>
                    </div>
                </div>
                ${ch.message ? `<div class="ts-ctx-msg">${escapeHtml(ch.message)}</div>` : ''}
                <div class="ts-ctx-metrics">
                    ${ctxMetric('Messages/Session', b.avg_messages, a.avg_messages, delta.avg_messages, true)}
                    ${ctxMetric('Tokens/Session', fmtK(b.avg_tokens), fmtK(a.avg_tokens), delta.avg_tokens, true)}
                    ${ctxMetric('Cost/Session', '$'+b.avg_cost.toFixed(2), '$'+a.avg_cost.toFixed(2), delta.avg_cost, true)}
                    ${ctxMetric('Sessions', b.sessions, a.sessions, null, false)}
                </div>
            </div>`;
        }).join('');
    } catch(e) { console.error('Context error:', e); }
}

function fmtK(n) { return n >= 1e6 ? (n/1e6).toFixed(1)+'M' : n >= 1e3 ? (n/1e3).toFixed(0)+'K' : n; }

function ctxMetric(label, before, after, delta, lowerIsBetter) {
    let deltaHtml = '';
    if (delta !== null && delta !== undefined) {
        const cls = delta === 0 ? 'ts-ctx-neutral'
            : (lowerIsBetter ? (delta < 0 ? 'ts-ctx-better' : 'ts-ctx-worse') : (delta > 0 ? 'ts-ctx-better' : 'ts-ctx-worse'));
        const arrow = delta < 0 ? '&#9660;' : delta > 0 ? '&#9650;' : '&#8211;';
        deltaHtml = `<div class="ts-ctx-delta ${cls}">${arrow} ${Math.abs(delta)}%</div>`;
    }
    return `<div class="ts-ctx-metric">
        <div class="ts-ctx-metric-label">${label}</div>
        <div class="ts-ctx-before-after">
            <span class="ts-ctx-val">${before}</span>
            <span class="ts-ctx-arrow">&#8594;</span>
            <span class="ts-ctx-val">${after}</span>
        </div>
        ${deltaHtml}
    </div>`;
}

reloadAll();
