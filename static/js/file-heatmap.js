/**
 * File Heatmap + Risk Radar (Sprint 10)
 * Erwartet globale Variable: PROJECT_NAME (gesetzt im Template)
 * Nutzt api.js fuer HTTP-Calls, base.js fuer formatTimeAgo(), escapeHtml()
 */
let heatmapLoaded = false;
let heatmapTree = [];
let heatmapFlat = [];
let heatmapSort = { col: 'touches', dir: 'desc' };
let heatmapPeriod = '30d';
let heatmapModel = '';
let heatmapCategory = '';

async function loadRiskRadarPanel() {
    const panel = document.getElementById('riskRadarPanel');
    if (!panel) return;
    try {
        const radar = await api.get(`/api/analytics/risk-radar/${encodeURIComponent(PROJECT_NAME)}`);
        if (!radar.hotspot_files?.length && !radar.top_categories?.length) return;
        window._radarCategories = radar.top_categories || [];
        panel.innerHTML = renderRiskRadar(radar);
        panel.style.display = '';
        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (e) {
        console.warn('Risk radar not available:', e);
    }
}

async function loadFileHeatmap() {
    if (heatmapLoaded) return;
    heatmapLoaded = true;

    const container = document.getElementById('heatmapBody');
    if (!container) return;

    try {
        let heatUrl = `/api/analytics/file-heatmap/${encodeURIComponent(PROJECT_NAME)}?period=${heatmapPeriod}`;
        if (heatmapModel) heatUrl += `&model=${encodeURIComponent(heatmapModel)}`;
        if (heatmapCategory) heatUrl += `&category=${encodeURIComponent(heatmapCategory)}`;
        const [heatmap, radar] = await Promise.all([
            api.get(heatUrl),
            api.get(`/api/analytics/risk-radar/${encodeURIComponent(PROJECT_NAME)}`),
        ]);

        window._radarCategories = radar.top_categories || [];
        heatmapTree = heatmap.tree || [];
        // Flatten: Dirs + Children fuer Tabelle
        heatmapFlat = [];
        heatmapTree.forEach(dir => {
            heatmapFlat.push({ ...dir, _isDir: true });
            (dir.children || []).forEach(f => heatmapFlat.push({ ...f, _isDir: false }));
        });

        if (!heatmapFlat.length && !radar.hotspot_files?.length) {
            container.innerHTML = '<div class="heatmap-empty"><p>No file touch data available yet.</p><p style="font-size:12px;color:var(--text-faint)">Run the backfill script or wait for new sessions to be imported.</p></div>';
            return;
        }

        let html = '';
        html += renderRiskRadar(radar);
        if (radar.weekly_trend?.length > 1) {
            html += '<div class="trend-chart-wrap"><h4>Weekly Activity Trend</h4><canvas id="trendChart" height="200"></canvas></div>';
        }
        html += renderHeatmapToolbar();
        html += renderHeatmapTable(heatmapFlat);
        container.innerHTML = html;

        if (radar.weekly_trend?.length > 1 && typeof Chart !== 'undefined') {
            renderTrendChart(radar.weekly_trend);
        }
        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (e) {
        container.innerHTML = '<div class="heatmap-empty"><p>Error loading heatmap data.</p></div>';
        console.error('Heatmap load error:', e);
    }
}

async function reloadHeatmap() {
    heatmapLoaded = false;
    const container = document.getElementById('heatmapBody');
    if (container) container.innerHTML = '<p style="padding:16px;color:var(--text-muted)">Loading...</p>';
    await loadFileHeatmap();
}

function renderRiskRadar(radar) {
    let html = '<div class="risk-radar">';

    // Top Hotspots
    html += '<div class="radar-card"><h4><i data-lucide="flame" class="icon icon-sm"></i> Top Hotspots</h4>';
    if (radar.hotspot_files?.length) {
        html += '<ul class="radar-list">';
        radar.hotspot_files.forEach(h => {
            const badge = h.touches_30d > 20 ? 'hot' : h.touches_30d > 10 ? 'warm' : 'cool';
            const drillDown = h.drill_down ? ` onclick="window.location='${escapeHtml(h.drill_down)}'"` : '';
            html += `<li${drillDown} style="cursor:pointer" title="This file was modified ${h.touches_30d} times by AI in the last 30 days">`;
            html += `<span class="radar-file">${escapeHtml(shortPath(h.path))}</span>`;
            html += `<span class="ai-hotspot-badge">AI Hotspot</span>`;
            html += `<span class="radar-badge ${badge}">${h.touches_30d} Touches${h.avg_severity != null ? ', Sev ' + h.avg_severity : ''}</span>`;
            if (h.top_reason) html += `<span class="radar-reason">${escapeHtml(h.top_reason)}</span>`;
            html += '<span class="drill-arrow">→</span>';
            html += '</li>';
        });
        html += '</ul>';
    } else {
        html += '<p style="color:var(--text-muted);font-size:12px">No hotspots detected</p>';
    }
    html += '</div>';

    // Top Error Categories
    html += '<div class="radar-card"><h4><i data-lucide="alert-triangle" class="icon icon-sm"></i> Top Error Categories</h4>';
    if (radar.top_categories?.length) {
        html += '<ul class="radar-list">';
        radar.top_categories.forEach(c => {
            html += `<li><span>${escapeHtml(c.reason)}</span><span class="radar-badge warm">${c.pct}% (${c.count}x)</span></li>`;
        });
        html += '</ul>';
    } else {
        html += '<p style="color:var(--text-muted);font-size:12px">No error categories</p>';
    }
    html += '</div>';

    // Trend-Card
    if (radar.trend) {
        const t = radar.trend;
        const arrow = t.direction === 'improving' ? 'trend-arrow--down' : t.direction === 'worsening' ? 'trend-arrow--up' : '';
        const arrowIcon = t.direction === 'improving' ? '↓' : t.direction === 'worsening' ? '↑' : '→';
        html += '<div class="radar-card"><h4><i data-lucide="trending-up" class="icon icon-sm"></i> Rework-Trend</h4>';
        html += '<ul class="radar-list">';
        html += `<li><span>Rework-Rate 7d</span><span>${t.rework_rate_7d}%</span></li>`;
        html += `<li><span>Rework-Rate 30d</span><span>${t.rework_rate_30d}%</span></li>`;
        html += `<li><span>Delta</span><span class="${arrow}">${arrowIcon} ${t.delta_pp > 0 ? '+' : ''}${t.delta_pp}pp</span></li>`;
        html += '</ul></div>';
    }

    html += '</div>';
    return html;
}

function renderHeatmapToolbar() {
    let html = '<div class="heatmap-table-wrap">';
    html += '<div class="heatmap-toolbar">';
    html += '<input type="text" id="heatmapSearch" placeholder="Filter files..." oninput="filterHeatmap()">';

    // Period Filter
    html += '<select id="heatmapPeriod" onchange="changePeriod(this.value)">';
    ['30d', '90d', '365d', 'all'].forEach(p => {
        const label = p === 'all' ? 'All' : p;
        html += `<option value="${p}" ${p === heatmapPeriod ? 'selected' : ''}>${label}</option>`;
    });
    html += '</select>';

    // Model Filter
    html += '<select id="heatmapModel" onchange="changeModelFilter(this.value)">';
    html += '<option value="">All models</option>';
    // Modelle aus den Daten extrahieren
    const models = new Set();
    heatmapFlat.forEach(f => {
        if (f.models) Object.keys(f.models).forEach(m => models.add(m));
    });
    models.forEach(m => {
        html += `<option value="${escapeHtml(m)}" ${m === heatmapModel ? 'selected' : ''}>${escapeHtml(m)}</option>`;
    });
    html += '</select>';

    // Category Filter (befuellt aus top_categories des Risk-Radars)
    html += '<select id="heatmapCategory" onchange="changeCategoryFilter(this.value)">';
    html += '<option value="">All categories</option>';
    if (window._radarCategories) {
        window._radarCategories.forEach(c => {
            html += `<option value="${escapeHtml(c.reason)}" ${c.reason === heatmapCategory ? 'selected' : ''}>${escapeHtml(c.reason)} (${c.count})</option>`;
        });
    }
    html += '</select>';

    html += '</div>';
    return html;
}

function renderHeatmapTable(files) {
    let html = '<table class="heatmap-table"><thead><tr>';
    html += '<th onclick="sortHeatmap(\'path\')" data-col="path">Path</th>';
    html += '<th onclick="sortHeatmap(\'touches\')" data-col="touches" class="sorted-desc">Touches</th>';
    html += '<th onclick="sortHeatmap(\'rework_rate\')" data-col="rework_rate">Rework</th>';
    html += '<th>Distribution</th>';
    html += '<th onclick="sortHeatmap(\'sessions\')" data-col="sessions">Sessions</th>';
    html += '<th>Category</th>';
    html += '<th></th>';
    html += '</tr></thead>';
    html += '<tbody id="heatmapTableBody">';
    html += renderHeatmapRows(files);
    html += '</tbody></table></div>';
    return html;
}

function renderHeatmapRows(files) {
    if (!files.length) return '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:16px">No files match filter</td></tr>';

    const maxTouches = Math.max(...files.map(f => f.touches), 1);
    let html = '';
    files.forEach(f => {
        const isDir = f._isDir;
        const barWidth = Math.max(4, (f.touches / maxTouches) * 140);
        const rework = f.rework_rate || 0;
        const reworkClass = rework >= 15 ? 'heatmap-bar--red' : rework >= 5 ? 'heatmap-bar--yellow' : 'heatmap-bar--green';
        const pathDisplay = isDir ? `<strong>${escapeHtml(f.path)}</strong>` :
            `<span class="heatmap-indent"></span>${escapeHtml(shortPath(f.path))}`;

        // Haeufigste Kategorie aus outcome_stats oder top_reason
        const topCategory = f.top_reason || '';
        const stats = f.outcome_stats || {};
        const nf = stats.needs_fix || 0;
        const rv = stats.reverted || 0;

        // Drill-down URLs
        const fileParam = isDir ? `file_prefix=${encodeURIComponent(f.path)}` : `file=${encodeURIComponent(f.path)}`;
        const drillBase = `/sessions?project=${encodeURIComponent(PROJECT_NAME)}&${fileParam}`;
        const drillRework = `${drillBase}&outcome=needs_fix,reverted`;

        html += `<tr class="${isDir ? 'heatmap-dir-row' : ''}">`;
        html += `<td class="file-path" title="${escapeHtml(f.path)}"><a href="${drillBase}" class="drill-link">${pathDisplay}</a></td>`;
        html += `<td>${f.touches} <span class="heatmap-pct">(${f.pct || 0}%)</span></td>`;
        html += `<td><a href="${drillRework}" class="drill-link"><span class="rework-badge ${reworkClass}">${rework}%</span></a></td>`;
        html += `<td><div class="heat-cell"><span class="heat-bar ${reworkClass}" style="width:${barWidth}px"></span></div></td>`;
        html += `<td>${f.sessions || '-'}</td>`;
        html += `<td>${topCategory ? `<span class="category-tag">${escapeHtml(topCategory)}</span>` : nf + rv > 0 ? `<span class="category-tag muted">${nf} fix, ${rv} rev</span>` : '-'}</td>`;
        html += `<td><a href="${drillBase}" class="drill-arrow" title="Show sessions">→</a></td>`;
        html += '</tr>';
    });
    return html;
}

function shortPath(p) {
    if (!p || p.length < 50) return p;
    const parts = p.split('/');
    if (parts.length <= 3) return p;
    return parts[0] + '/.../' + parts.slice(-2).join('/');
}

function filterHeatmap() {
    const search = (document.getElementById('heatmapSearch')?.value || '').toLowerCase();
    let filtered = heatmapFlat;
    if (search) {
        filtered = filtered.filter(f => f.path.toLowerCase().includes(search));
    }
    const sorted = sortFiles(filtered);
    const tbody = document.getElementById('heatmapTableBody');
    if (tbody) tbody.innerHTML = renderHeatmapRows(sorted);
}

function sortHeatmap(col) {
    if (heatmapSort.col === col) {
        heatmapSort.dir = heatmapSort.dir === 'desc' ? 'asc' : 'desc';
    } else {
        heatmapSort = { col, dir: 'desc' };
    }
    document.querySelectorAll('.heatmap-table th').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.col === col) th.classList.add('sorted-' + heatmapSort.dir);
    });
    filterHeatmap();
}

function sortFiles(files) {
    const { col, dir } = heatmapSort;
    return [...files].sort((a, b) => {
        let va = a[col], vb = b[col];
        if (typeof va === 'string') return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
        return dir === 'asc' ? (va || 0) - (vb || 0) : (vb || 0) - (va || 0);
    });
}

function changePeriod(val) {
    heatmapPeriod = val;
    reloadHeatmap();
}

function changeModelFilter(val) {
    heatmapModel = val;
    reloadHeatmap();
}

function changeCategoryFilter(val) {
    heatmapCategory = val;
    reloadHeatmap();
}

function renderTrendChart(trend) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    const labels = trend.map(t => {
        const d = new Date(t.week);
        return d.toLocaleDateString('de', { month: 'short', day: 'numeric' });
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Changes',
                    data: trend.map(t => t.changes),
                    backgroundColor: 'rgba(255, 152, 0, 0.6)',
                    borderRadius: 4,
                },
                {
                    label: 'Reads',
                    data: trend.map(t => t.total_touches - t.changes),
                    backgroundColor: 'rgba(91, 155, 213, 0.4)',
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#888' } } },
            scales: {
                x: {
                    stacked: true,
                    ticks: { color: '#666' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: { color: '#666' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                },
            },
        },
    });
}
