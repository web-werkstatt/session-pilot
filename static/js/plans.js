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

        // Workflow-Badges
        const wfStage = plan.workflow_stage || 'idea';
        const wfBadge = `<span class="badge badge-wf badge-wf-${wfStage}">${wfStage.replace('_', ' ')}</span>`;
        const execBadge = plan.latest_executor_status
            ? `<span class="badge badge-exec badge-exec-${plan.latest_executor_status}">exec: ${plan.latest_executor_status}</span>` : '';
        const reviewBadge = plan.latest_review_status
            ? `<span class="badge badge-review badge-review-${plan.latest_review_status}">review: ${plan.latest_review_status}</span>` : '';

        // Ist/Soll/Next Micro-Info
        let microInfo = '';
        if (plan.current_state || plan.target_state || plan.next_action) {
            microInfo = '<div class="plan-card-micro">';
            if (plan.current_state) microInfo += `<div class="micro-row"><span class="micro-label">Ist:</span> ${escapeHtml(plan.current_state.substring(0, 80))}</div>`;
            if (plan.target_state) microInfo += `<div class="micro-row"><span class="micro-label">Soll:</span> ${escapeHtml(plan.target_state.substring(0, 80))}</div>`;
            if (plan.next_action) microInfo += `<div class="micro-row micro-next"><span class="micro-label">Next:</span> ${escapeHtml(plan.next_action.substring(0, 80))}</div>`;
            microInfo += '</div>';
        }

        html += `
        <div class="plan-card status-${statusClass}" onclick="showPlan(${plan.id})">
            <div class="plan-card-top">
                <span class="plan-project"><i data-lucide="folder" class="icon icon-xs"></i> ${projectName}</span>
                <span class="plan-date">${date}</span>
            </div>
            <h3 class="plan-card-title">${escapeHtml(plan.title)}</h3>
            ${plan.context_summary ? `<p class="plan-card-context">${escapeHtml(plan.context_summary.substring(0, 120))}${plan.context_summary.length > 120 ? '...' : ''}</p>` : ''}
            ${microInfo}
            <div class="plan-card-footer">
                ${wfBadge}
                <span class="badge badge-cat"><i data-lucide="${catIcon}" class="icon icon-xs"></i> ${plan.category || 'plan'}</span>
                <span class="badge badge-status badge-${statusClass}">${statusLabel(plan.status)}</span>
                ${execBadge}${reviewBadge}
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

            // Workflow-Daten laden (Sprint E)
            _loadPlanWorkflow(id, plan.project_name);

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

// === Sprint E: Workflow Panel ===
function _loadPlanWorkflow(planId, projectName) {
    var panel = document.getElementById('workflowPanel');
    if (!panel) return;
    panel.innerHTML = '<span class="text-muted">Workflow laden...</span>';

    api.get('/api/plans/' + planId + '/workflow')
        .then(function(wf) {
            var html = '<div class="wf-grid">';

            // Ist / Soll / Next (M6)
            html += '<div class="wf-section">';
            html += '<div class="wf-field"><span class="wf-label">Ist:</span> ' + escapeHtml(wf.current_state || '—') + '</div>';
            html += '<div class="wf-field"><span class="wf-label">Soll:</span> ' + escapeHtml(wf.target_state || '—') + '</div>';
            html += '<div class="wf-field wf-next"><span class="wf-label">Next:</span> ' + escapeHtml(wf.next_action || '—') + '</div>';
            html += '</div>';

            // Status-Badges
            html += '<div class="wf-section">';
            html += '<span class="badge badge-wf badge-wf-' + (wf.workflow_stage || 'idea') + '">' + (wf.workflow_stage || 'idea').replace('_', ' ') + '</span> ';
            if (wf.latest_executor_status) html += '<span class="badge badge-exec badge-exec-' + wf.latest_executor_status + '">exec: ' + wf.latest_executor_status + '</span> ';
            if (wf.latest_review_status) html += '<span class="badge badge-review badge-review-' + wf.latest_review_status + '">review: ' + wf.latest_review_status + '</span> ';
            html += '</div>';

            // Signale (M7)
            html += '<div class="wf-section wf-signals">';
            if (wf.latest_quality_score != null) html += '<span class="wf-signal">Quality: ' + wf.latest_quality_score + '</span> ';
            if (wf.governance_status) html += '<span class="wf-signal wf-gov-' + wf.governance_status + '">Gov: ' + wf.governance_status + '</span> ';
            if (wf.latest_audit_status) html += '<span class="wf-signal">Audit: ' + wf.latest_audit_status + '</span> ';
            if (wf.spec_ref) html += '<span class="wf-signal">Spec: ' + escapeHtml(wf.spec_ref) + '</span> ';
            html += '</div>';

            // Copilot-Link (M5)
            if (projectName) {
                html += '<div class="wf-section"><a href="/copilot?project=' + encodeURIComponent(projectName) + '&plan_id=' + planId + '" class="btn btn-sm btn-secondary">Copilot fuer diesen Plan</a></div>';
            }

            html += '</div>';
            panel.innerHTML = html;
        })
        .catch(function() {
            panel.innerHTML = '<span class="text-muted">Workflow nicht verfuegbar</span>';
        });
}

function showToast(msg, isError) {
    const toast = document.getElementById('syncToast');
    toast.textContent = msg;
    toast.className = 'toast show' + (isError ? ' toast-error' : '');
    setTimeout(() => toast.className = 'toast', 4000);
}
// formatDate: in base.js (global)
