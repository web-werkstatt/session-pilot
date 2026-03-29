/**
 * Plans - Import, Filter, Detail-Ansicht
 */
let allPlans = [];
let filters = { status: '', project: '', category: '' };

document.addEventListener('DOMContentLoaded', () => {
    // URL-Parameter auswerten (z.B. /plans?project=contypio)
    const params = new URLSearchParams(window.location.search);
    if (params.get('project')) {
        filters.project = params.get('project');
    }
    if (params.get('status')) {
        filters.status = params.get('status');
    }
    loadStats();
    loadPlans().then(() => {
        const planId = params.get('plan');
        if (planId) showPlan(parseInt(planId));
    });
    loadProjects();
});

// === Data ===
function loadPlans() {
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.project) params.set('project', filters.project);
    if (filters.category) params.set('category', filters.category);

    return api.get('/api/plans?' + params.toString())
        .then(data => {
            allPlans = data.plans || [];
            renderPlans();
        })
        .catch(err => {
            console.error('Error:', err);
            document.getElementById('loading').innerHTML = '<div class="error">Error loading</div>';
        });
}

function loadStats() {
    api.get('/api/plans/stats')
        .then(s => {
            // Umsetzung
            document.getElementById('completionRate').textContent = s.completion_rate;
            document.getElementById('completionBar').style.width = s.completion_rate + '%';
            const total = s.completed + s.active + s.draft;
            document.getElementById('completionDetail').textContent =
                `${s.completed} completed / ${total} total`;

            // Pipeline
            document.getElementById('draftCount').textContent = s.draft;
            document.getElementById('activeCount').textContent = s.active;
            document.getElementById('completedCount').textContent = s.completed;

            // Aktivitaet
            document.getElementById('last30d').textContent = s.last_30d;
            const sub = s.last_7d > 0
                ? `of which ${s.last_7d} this week`
                : 'none this week';
            document.getElementById('last7dInfo').textContent = sub;

            // Abdeckung
            document.getElementById('projectCount').textContent = s.projects;
            document.getElementById('unassignedCount').textContent = s.unassigned;
            const topEl = document.getElementById('topProject');
            if (s.top_project) {
                topEl.innerHTML = `Aktivstes: <strong>${escapeHtml(s.top_project.name)}</strong> (${s.top_project.count})`;
            } else {
                topEl.textContent = '';
            }

            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(() => {});
}

function loadProjects() {
    api.get('/api/plans/projects')
        .then(data => {
            const sel = document.getElementById('projectFilter');
            (data.projects || []).forEach(p => {
                if (!p.name) return;
                const opt = document.createElement('option');
                opt.value = p.name;
                opt.textContent = `${p.name} (${p.count})`;
                sel.appendChild(opt);
            });
        })
        .catch(() => {});
}

// === Rendering ===
function renderPlans() {
    document.getElementById('loading').style.display = 'none';

    if (allPlans.length === 0) {
        document.getElementById('plansGrid').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
    }

    document.getElementById('emptyState').style.display = 'none';
    const grid = document.getElementById('plansGrid');
    grid.style.display = 'grid';

    let html = '';
    allPlans.forEach(plan => {
        const statusClass = plan.status || 'draft';
        const catIcon = getCategoryIcon(plan.category);
        const date = formatDate(plan.created_at);
        const projectName = plan.project_name
            ? escapeHtml(plan.project_name)
            : '<span class="text-muted">No project</span>';
        const sessionLink = plan.session_slug
            ? `<a href="/sessions/${plan.session_slug}" class="session-link" onclick="event.stopPropagation()"><i data-lucide="bot" class="icon icon-xs"></i> Session</a>`
            : '';

        html += `
        <div class="plan-card status-${statusClass}" onclick="showPlan(${plan.id})">
            <div class="plan-card-top">
                <span class="plan-project"><i data-lucide="folder" class="icon icon-xs"></i> ${projectName}</span>
                <span class="plan-date">${date}</span>
            </div>
            <h3 class="plan-card-title">${escapeHtml(plan.title)}</h3>
            ${plan.context_summary ? `<p class="plan-card-context">${escapeHtml(plan.context_summary.substring(0, 120))}${plan.context_summary.length > 120 ? '...' : ''}</p>` : ''}
            <div class="plan-card-footer">
                <span class="badge badge-cat"><i data-lucide="${catIcon}" class="icon icon-xs"></i> ${plan.category || 'plan'}</span>
                <span class="badge badge-status badge-${statusClass}">${statusLabel(plan.status)}</span>
                ${sessionLink}
            </div>
        </div>`;
    });

    grid.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function getCategoryIcon(cat) {
    const icons = {
        'feature': 'sparkles',
        'bugfix': 'bug',
        'refactor': 'refresh-cw',
        'infra': 'server',
        'plan': 'file-text',
    };
    return icons[cat] || 'file-text';
}

function statusLabel(status) {
    const labels = {
        'draft': 'Draft',
        'active': 'Active',
        'completed': 'Done',
        'archived': 'Archive',
    };
    return labels[status] || status || 'Draft';
}

// === Filter ===
function setFilter(key, value) {
    filters[key] = value;

    if (key === 'status') {
        document.querySelectorAll('.filter-btn[data-filter="status"]').forEach(btn => {
            const btnVal = btn.onclick.toString().match(/'([^']*)'\)/);
            btn.classList.toggle('active', btnVal && btnVal[1] === value);
        });
    }

    loadPlans();
    loadStats();
}

// === Detail ===
function showPlan(id) {
    api.get(`/api/plans/${id}`)
        .then(plan => {
            document.getElementById('modalTitle').textContent = plan.title;

            const meta = [];
            if (plan.project_name) meta.push(`<span class="meta-item"><i data-lucide="folder" class="icon icon-xs"></i> ${escapeHtml(plan.project_name)}</span>`);
            meta.push(`<span class="meta-item"><i data-lucide="calendar" class="icon icon-xs"></i> ${formatDate(plan.created_at)}</span>`);
            if (plan.session_slug) {
                meta.push(`<a href="/sessions/${plan.session_slug}" class="meta-item session-link"><i data-lucide="bot" class="icon icon-xs"></i> View session</a>`);
            }
            document.getElementById('modalMeta').innerHTML = meta.join('');

            // Toolbar: Status (auto-erkannt), Kategorie, Dateiname
            document.getElementById('modalToolbar').innerHTML = `
                <span class="badge badge-status badge-${plan.status}">${statusLabel(plan.status)}</span>
                <span class="badge badge-cat"><i data-lucide="${getCategoryIcon(plan.category)}" class="icon icon-xs"></i> ${plan.category}</span>
                <code class="filename">${escapeHtml(plan.filename)}</code>
            `;

            document.getElementById('modalContent').innerHTML = plan.content_html || '<em>No content</em>';
            openModal('planModal');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(err => alert('Error: ' + err.message));
}

function closePlanModal() {
    closeModal('planModal');
}

// === Sync ===
function syncPlans() {
    const btn = document.querySelector('[onclick="syncPlans()"]');
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="icon icon-sm spin"></i> Importing...';

    api.post('/api/plans/sync')
        .then(result => {
            if (result.success) {
                const s = result.stats;
                showToast(`Import: ${s.imported} new, ${s.updated} updated, ${s.unchanged} unchanged (${s.total} files)`);
                loadPlans();
                loadStats();
                loadProjects();
            }
        })
        .catch(err => showToast('Error: ' + err.message, true))
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="download" class="icon icon-sm"></i> Import';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        });
}

function showToast(msg, isError) {
    const toast = document.getElementById('syncToast');
    toast.textContent = msg;
    toast.className = 'toast show' + (isError ? ' toast-error' : '');
    setTimeout(() => toast.className = 'toast', 4000);
}
// formatDate: in base.js (global)
