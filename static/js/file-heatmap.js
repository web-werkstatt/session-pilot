/**
 * File Heatmap + Risk Radar (Sprint 10)
 * Erwartet globale Variable: PROJECT_NAME (gesetzt im Template)
 * Nutzt api.js fuer HTTP-Calls, base.js fuer formatTimeAgo()
 */
let heatmapLoaded = false;
let heatmapData = [];
let heatmapSort = { col: 'total', dir: 'desc' };

async function loadFileHeatmap() {
    if (heatmapLoaded) return;
    heatmapLoaded = true;

    const container = document.getElementById('heatmapBody');
    if (!container) return;

    try {
        const [heatmap, radar] = await Promise.all([
            api.get('/api/analytics/file-heatmap/' + encodeURIComponent(PROJECT_NAME)),
            api.get('/api/analytics/risk-radar/' + encodeURIComponent(PROJECT_NAME)),
        ]);

        heatmapData = heatmap.files || [];

        if (!heatmapData.length && !radar.hotspots?.length) {
            container.innerHTML = '<div class="heatmap-empty"><p>No file touch data available yet.</p><p style="font-size:12px;color:var(--text-faint)">Run the backfill script or wait for new sessions to be imported.</p></div>';
            return;
        }

        let html = '';

        // Risk Radar
        html += renderRiskRadar(radar);

        // Trend Chart
        if (radar.weekly_trend?.length > 1) {
            html += '<div class="trend-chart-wrap"><h4>Weekly Activity Trend</h4><canvas id="trendChart" height="200"></canvas></div>';
        }

        // Heatmap Table
        html += renderHeatmapTable(heatmapData);

        container.innerHTML = html;

        // Trend Chart rendern (Chart.js ist via CDN in base.html)
        if (radar.weekly_trend?.length > 1 && typeof Chart !== 'undefined') {
            renderTrendChart(radar.weekly_trend);
        }

        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (e) {
        container.innerHTML = '<div class="heatmap-empty"><p>Error loading heatmap data.</p></div>';
        console.error('Heatmap load error:', e);
    }
}

function renderRiskRadar(radar) {
    let html = '<div class="risk-radar">';

    // Hotspots Card
    html += '<div class="radar-card"><h4><i data-lucide="flame" class="icon icon-sm"></i> Top Hotspots</h4>';
    if (radar.hotspots?.length) {
        html += '<ul class="radar-list">';
        radar.hotspots.forEach(h => {
            const badge = h.changes > 20 ? 'hot' : h.changes > 10 ? 'warm' : 'cool';
            html += `<li><span class="radar-file" title="${escapeHtml(h.file_path)}">${escapeHtml(shortPath(h.file_path))}</span>`;
            html += `<span class="radar-badge ${badge}">${h.changes} changes</span></li>`;
        });
        html += '</ul>';
    } else {
        html += '<p style="color:var(--text-muted);font-size:12px">No hotspots detected</p>';
    }
    html += '</div>';

    // Error Files Card
    html += '<div class="radar-card"><h4><i data-lucide="alert-triangle" class="icon icon-sm"></i> Rework Files</h4>';
    if (radar.error_files?.length) {
        html += '<ul class="radar-list">';
        radar.error_files.forEach(f => {
            html += `<li><span class="radar-file" title="${escapeHtml(f.file_path)}">${escapeHtml(shortPath(f.file_path))}</span>`;
            html += `<span class="radar-badge hot">${f.error_sessions} issues</span></li>`;
        });
        html += '</ul>';
    } else {
        html += '<p style="color:var(--text-muted);font-size:12px">No rework patterns detected</p>';
    }
    html += '</div>';

    // Summary Card
    if (heatmapData.length) {
        const totalFiles = heatmapData.length;
        const totalTouches = heatmapData.reduce((s, f) => s + f.total, 0);
        const totalWrites = heatmapData.reduce((s, f) => s + f.writes, 0);
        const totalEdits = heatmapData.reduce((s, f) => s + f.edits, 0);
        html += '<div class="radar-card"><h4><i data-lucide="bar-chart-3" class="icon icon-sm"></i> Summary</h4>';
        html += '<ul class="radar-list">';
        html += `<li><span>Files touched</span><span style="color:var(--text-primary)">${totalFiles}</span></li>`;
        html += `<li><span>Total touches</span><span style="color:var(--text-primary)">${totalTouches}</span></li>`;
        html += `<li><span>Writes</span><span style="color:var(--status-error-text)">${totalWrites}</span></li>`;
        html += `<li><span>Edits</span><span style="color:var(--status-warning-text)">${totalEdits}</span></li>`;
        html += '</ul></div>';
    }

    html += '</div>';
    return html;
}

function renderHeatmapTable(files) {
    let html = '<div class="heatmap-table-wrap">';
    html += '<div class="heatmap-toolbar">';
    html += '<input type="text" id="heatmapSearch" placeholder="Filter files..." oninput="filterHeatmap()">';
    html += '<select id="heatmapTypeFilter" onchange="filterHeatmap()">';
    html += '<option value="">All types</option>';
    html += '<option value="write">Writes only</option>';
    html += '<option value="edit">Edits only</option>';
    html += '<option value="read">Reads only</option>';
    html += '</select>';
    html += '</div>';

    html += '<table class="heatmap-table"><thead><tr>';
    html += '<th onclick="sortHeatmap(\'file_path\')" data-col="file_path">File</th>';
    html += '<th onclick="sortHeatmap(\'total\')" data-col="total" class="sorted-desc">Total</th>';
    html += '<th onclick="sortHeatmap(\'writes\')" data-col="writes">Writes</th>';
    html += '<th onclick="sortHeatmap(\'edits\')" data-col="edits">Edits</th>';
    html += '<th onclick="sortHeatmap(\'reads\')" data-col="reads">Reads</th>';
    html += '<th onclick="sortHeatmap(\'sessions\')" data-col="sessions">Sessions</th>';
    html += '<th onclick="sortHeatmap(\'last_touched\')" data-col="last_touched">Last Touch</th>';
    html += '</tr></thead>';
    html += '<tbody id="heatmapTableBody">';
    html += renderHeatmapRows(files);
    html += '</tbody></table></div>';
    return html;
}

function renderHeatmapRows(files) {
    if (!files.length) return '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:16px">No files match filter</td></tr>';

    const maxTotal = Math.max(...files.map(f => f.total), 1);
    let html = '';
    files.forEach(f => {
        const barW = Math.max(4, (f.writes / maxTotal) * 120);
        const barE = Math.max(4, (f.edits / maxTotal) * 120);
        const barR = Math.max(4, (f.reads / maxTotal) * 120);
        html += '<tr>';
        html += `<td class="file-path" title="${escapeHtml(f.file_path)}">${escapeHtml(shortPath(f.file_path))}</td>`;
        html += `<td>${f.total}</td>`;
        html += `<td><div class="heat-cell"><span class="count">${f.writes}</span><span class="heat-bar write" style="width:${barW}px"></span></div></td>`;
        html += `<td><div class="heat-cell"><span class="count">${f.edits}</span><span class="heat-bar edit" style="width:${barE}px"></span></div></td>`;
        html += `<td><div class="heat-cell"><span class="count">${f.reads}</span><span class="heat-bar read" style="width:${barR}px"></span></div></td>`;
        html += `<td>${f.sessions}</td>`;
        html += `<td>${f.last_touched ? formatTimeAgo(f.last_touched) : '-'}</td>`;
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
    const typeFilter = document.getElementById('heatmapTypeFilter')?.value || '';

    let filtered = heatmapData;
    if (search) {
        filtered = filtered.filter(f => f.file_path.toLowerCase().includes(search));
    }
    if (typeFilter) {
        const key = typeFilter + 's';
        filtered = filtered.filter(f => f[key] > 0);
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

    // Update header classes
    document.querySelectorAll('.heatmap-table th').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.col === col) {
            th.classList.add('sorted-' + heatmapSort.dir);
        }
    });

    filterHeatmap();
}

function sortFiles(files) {
    const { col, dir } = heatmapSort;
    return [...files].sort((a, b) => {
        let va = a[col], vb = b[col];
        if (typeof va === 'string') {
            return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
        }
        return dir === 'asc' ? (va || 0) - (vb || 0) : (vb || 0) - (va || 0);
    });
}

function renderTrendChart(trend) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    const labels = trend.map(t => {
        const d = new Date(t.week);
        return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
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
