function openSessionStats() {
    var grid = document.getElementById('sessionStatsGrid');
    grid.innerHTML = [
        {label:'Sessions', id:'statSessions', color:'#4fc3f7'},
        {label:'Projekte', id:'statProjects', color:'#fff'},
        {label:'Gesamt-Dauer', id:'statDuration', color:'#66bb6a'},
        {label:'Input-Tokens', id:'statTokensIn', color:'#ff9800'},
        {label:'Output-Tokens', id:'statTokensOut', color:'#cf6ff7'},
    ].map(function(s) {
        var val = document.getElementById(s.id).textContent;
        return '<div class="stat"><span class="stat-label">' + s.label + '</span><span class="stat-value" style="color:' + s.color + '">' + val + '</span></div>';
    }).join('');
    document.getElementById('sessionStatsModal').classList.add('show');
}

let currentOffset = 0;
const pageSize = 50;
let totalCount = 0;
let searchTimer = null;
let currentSort = 'started_at';
let currentOrder = 'desc';
let maxDuration = 1;
let sessionsData = [];

function sortBy(col) {
    if (currentSort === col) {
        currentOrder = currentOrder === 'desc' ? 'asc' : 'desc';
    } else {
        currentSort = col;
        currentOrder = col === 'project_name' || col === 'account' ? 'asc' : 'desc';
    }
    currentOffset = 0;
    updateSortIcons();
    loadSessions();
}

function updateSortIcons() {
    document.querySelectorAll('.sort-icon').forEach(el => {
        el.textContent = el.dataset.col === currentSort ? (currentOrder === 'desc' ? '▼' : '▲') : '';
    });
}

function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { currentOffset = 0; loadSessions(); }, 250);
}

function resetAndLoad() { currentOffset = 0; loadSessions(); }

function setQuickFilter(range, btn) {
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const from = document.getElementById('filterDateFrom');
    const to = document.getElementById('filterDateTo');
    const now = new Date();
    to.value = '';
    if (range === 'all') { from.value = ''; }
    else if (range === 'today') { from.value = now.toISOString().slice(0,10); }
    else if (range === 'week') { now.setDate(now.getDate()-7); from.value = now.toISOString().slice(0,10); }
    else if (range === 'month') { now.setDate(now.getDate()-30); from.value = now.toISOString().slice(0,10); }
    resetAndLoad();
}

async function loadStats() {
    try {
        const r = await fetch('/api/sessions/stats');
        if (!r.ok) throw new Error('Stats failed');
        const d = await r.json();
        document.getElementById('statSessions').textContent = d.total_sessions || 0;
        document.getElementById('statProjects').textContent = d.projects || 0;
        document.getElementById('statDuration').textContent = d.total_duration_formatted || '0s';
        document.getElementById('statTokensIn').textContent = d.total_input_formatted || '0';
        document.getElementById('statTokensOut').textContent = d.total_output_formatted || '0';

        if (d.accounts) {
            document.getElementById('statAccountsSub').textContent = d.accounts.map(a => `${a.account}: ${a.cnt}`).join(' · ');
        }
        if (d.total_user_messages) {
            document.getElementById('statMsgSub').textContent = `${(d.total_user_messages||0).toLocaleString('de-DE')} Nachrichten`;
        }

        const sel = document.getElementById('filterProject');
        if (d.top_projects && sel.options.length <= 1) {
            d.top_projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.name;
                opt.textContent = `${p.name} (${p.count})`;
                sel.appendChild(opt);
            });
        }
    } catch(e) {
        console.error('Stats Error:', e);
        if (!loadStats._retries) loadStats._retries = 0;
        if (++loadStats._retries < 3) setTimeout(loadStats, 2000);
    }
}

async function loadSessions() {
    const params = new URLSearchParams({ sort: currentSort, order: currentOrder, limit: pageSize, offset: currentOffset });
    const account = document.getElementById('filterAccount').value;
    const project = document.getElementById('filterProject').value;
    const search = document.getElementById('filterSearch').value;
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    if (account) params.set('account', account);
    if (project) params.set('project', project);
    if (search) params.set('search', search);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);

    try {
        const r = await fetch('/api/sessions?' + params);
        if (!r.ok) {
            console.error('Sessions laden fehlgeschlagen:', r.status);
            document.getElementById('loading').innerHTML = '<p style="color:var(--danger)">Fehler beim Laden der Sessions (DB nicht erreichbar?)</p>';
            return;
        }
        const d = await r.json();
        totalCount = d.total;
        sessionsData = d.sessions || [];
        maxDuration = Math.max(1, ...sessionsData.map(s => s.duration_ms || 0));
        renderSessions(sessionsData);
        renderPagination();
    } catch(e) {
        console.error('Sessions Error:', e);
        document.getElementById('loading').innerHTML = '<p style="color:var(--danger)">Fehler beim Laden der Sessions</p>';
    }
}

function outcomeBadge(outcome) {
    if (!outcome) return '<span class="outcome-unrated">-</span>';
    const labels = {ok:'OK', needs_fix:'Needs Fix', reverted:'Reverted', partial:'Partial'};
    return `<span class="outcome-badge outcome-${outcome}">${labels[outcome] || outcome}</span>`;
}

function renderSessions(sessions) {
    document.getElementById('loading').style.display = 'none';
    const table = document.getElementById('sessionsTable');
    const empty = document.getElementById('emptyState');

    if (!sessions.length) {
        table.style.display = 'none';
        empty.style.display = 'block';
        return;
    }
    table.style.display = 'table';
    empty.style.display = 'none';

    const tbody = document.getElementById('sessionsBody');
    tbody.innerHTML = sessions.map((s, i) => {
        const date = s.started_at ? new Date(s.started_at) : null;
        const dateStr = date ? date.toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit',year:'2-digit'}) : '-';
        const timeStr = date ? date.toLocaleTimeString('de-DE', {hour:'2-digit',minute:'2-digit'}) : '';
        const acctClass = 'account-' + (s.account || '').replace(/[^a-z0-9]/g, '');
        const durPct = Math.min(100, ((s.duration_ms || 0) / maxDuration) * 100);
        const model = (s.model || '-').replace('claude-', '').replace('opus-4-6', 'Opus').replace('sonnet-4-6', 'Sonnet');
        const msgCount = (s.user_message_count||0) + (s.assistant_message_count||0);
        const branch = s.git_branch || '';

        return `<tr class="row" onclick="location.href='/sessions/${s.session_uuid}'" onmouseenter="showPreview(event,${i})" onmouseleave="hidePreview()">
            <td><a href="/sessions/${s.session_uuid}" class="project-name">${s.project_name || s.project_hash || '-'}</a></td>
            <td><span class="account-badge ${acctClass}">${s.account}</span></td>
            <td><span style="color:#ccc">${dateStr}</span> <span style="color:#666;font-size:11px">${timeStr}</span></td>
            <td><div class="dur-wrap"><div class="dur-bar" style="width:${durPct}%"></div><span class="dur-text">${s.duration_formatted}</span></div></td>
            <td>${msgCount}</td>
            <td style="color:#888;font-size:12px">${model}</td>
            <td class="token-cell">${s.tokens_formatted}</td>
            <td>${branch ? `<span class="branch" title="${branch}">${branch}</span>` : ''}</td>
            <td>${outcomeBadge(s.outcome)}</td>
            <td><div class="row-actions"><button class="row-action" onclick="event.stopPropagation();exportSession('${s.session_uuid}','json')">JSON</button><button class="row-action" onclick="event.stopPropagation();exportSession('${s.session_uuid}','md')">MD</button></div></td>
        </tr>`;
    }).join('');
}

function exportSession(uuid, fmt) {
    window.open(`/api/sessions/${uuid}/export?format=${fmt}`, '_blank');
}

function showPreview(e, idx) {
    const s = sessionsData[idx];
    if (!s) return;
    const tip = document.getElementById('previewTip');
    const date = s.started_at ? new Date(s.started_at).toLocaleString('de-DE') : '-';
    tip.innerHTML = `
        <div class="pt-title">${s.project_name || '-'}</div>
        <div class="pt-row"><span class="pt-label">Account</span><span class="pt-value">${s.account}</span></div>
        <div class="pt-row"><span class="pt-label">Datum</span><span class="pt-value">${date}</span></div>
        <div class="pt-row"><span class="pt-label">Dauer</span><span class="pt-value">${s.duration_formatted}</span></div>
        <div class="pt-row"><span class="pt-label">Nachrichten</span><span class="pt-value">${(s.user_message_count||0)} User / ${(s.assistant_message_count||0)} Assistant</span></div>
        <div class="pt-row"><span class="pt-label">Tokens</span><span class="pt-value">${s.tokens_formatted}</span></div>
        <div class="pt-row"><span class="pt-label">Model</span><span class="pt-value">${s.model || '-'}</span></div>
        <div class="pt-row"><span class="pt-label">Branch</span><span class="pt-value">${s.git_branch || '-'}</span></div>
        <div class="pt-row"><span class="pt-label">Slug</span><span class="pt-value" style="font-style:italic">${s.slug || '-'}</span></div>
    `;
    tip.style.top = Math.min(e.clientY + 12, window.innerHeight - 260) + 'px';
    tip.style.left = Math.min(e.clientX + 16, window.innerWidth - 300) + 'px';
    tip.classList.add('show');
}

function hidePreview() { document.getElementById('previewTip').classList.remove('show'); }

function renderPagination() {
    const pag = document.getElementById('pagination');
    if (totalCount <= pageSize) { pag.style.display = 'none'; return; }
    pag.style.display = 'flex';
    const page = Math.floor(currentOffset / pageSize) + 1;
    const totalPages = Math.ceil(totalCount / pageSize);
    document.getElementById('pageInfo').textContent = `${page} / ${totalPages}  (${totalCount})`;
    document.getElementById('prevBtn').disabled = currentOffset === 0;
    document.getElementById('nextBtn').disabled = currentOffset + pageSize >= totalCount;
}

function changePage(dir) {
    currentOffset = Math.max(0, currentOffset + dir * pageSize);
    loadSessions();
    window.scrollTo({top: 0, behavior: 'smooth'});
}

async function syncSessions() {
    const btn = document.getElementById('syncBtn');
    btn.classList.add('syncing');
    btn.textContent = '⏳ Sync...';
    try {
        const r = await fetch('/api/sessions/sync', {method: 'POST'});
        if (!r.ok) throw new Error(`Sync failed: ${r.status}`);
        const d = await r.json();
        if (d.success) {
            btn.textContent = `+${d.stats.imported} neu`;
            loadStats();
            loadSessions();
        } else { btn.textContent = 'Fehler'; }
    } catch(e) { btn.textContent = 'Fehler'; }
    btn.classList.remove('syncing');
    setTimeout(() => { btn.textContent = '🔄 Sync'; }, 3000);
}

loadStats();
updateSortIcons();
loadSessions();
