/**
 * Plan Index - Import, Filter, Detail-Ansicht, Drag & Drop Board
 */
let allPlans = [];
let filters = { status: '', project: '', category: '' };
let currentView = 'grid';

// Workflow-Stage Spalten-Definition (Mapping: Label → workflow_stage)
const BOARD_COLUMNS = [
    { label: 'Idea',    stage: 'idea' },
    { label: 'Spec',    stage: 'spec_ready' },
    { label: 'Prompt',  stage: 'prompt_ready' },
    { label: 'Execute', stage: 'executing' },
    { label: 'Review',  stage: 'review_pending' },
    { label: 'Fixed',   stage: 'fixed' },
    { label: 'Done',    stage: 'done' },
    { label: 'Blocked', stage: 'blocked' },
];

document.addEventListener('DOMContentLoaded', () => {
    // URL-Parameter auswerten (z.B. /plans?project=contypio&view=board&plan=123)
    const params = new URLSearchParams(window.location.search);
    const legacyPlanId = params.get('plan');
    if (legacyPlanId) {
        window.location.replace('/plans/' + encodeURIComponent(legacyPlanId));
        return;
    }
    if (params.get('project')) {
        filters.project = params.get('project');
    } else if (typeof getActiveProjectContext === 'function') {
        filters.project = getActiveProjectContext() || '';
    }
    if (params.get('status')) {
        filters.status = params.get('status');
    }
    loadStats();
    loadPlans();
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
            if (filters.project) sel.value = filters.project;
        })
        .catch(() => {});
}

// === Rendering ===
function renderPlans() {
    var loading = document.getElementById('loading');
    var grid = document.getElementById('plansGrid');
    var board = document.getElementById('plansBoard');
    var empty = document.getElementById('emptyState');

    if (loading) loading.style.display = 'none';

    if (allPlans.length === 0) {
        if (grid) grid.style.display = 'none';
        if (board) board.style.display = 'none';
        if (empty) empty.style.display = 'block';
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
    }

    if (empty) empty.style.display = 'none';

    if (currentView === 'board') {
        if (grid) grid.style.display = 'none';
        renderBoard();
    } else {
        if (board) board.style.display = 'none';
        renderGrid();
    }
}

function _buildCardHtml(plan, draggable) {
    const statusClass = plan.status || 'draft';
    const wfStage = plan.workflow_stage || 'idea';
    const catIcon = getCategoryIcon(plan.category);
    const dragAttr = draggable ? `draggable="true" data-plan-id="${plan.id}" data-stage="${wfStage}"` : '';

    const summary = plan.context_summary || plan.description || '';

    const projectBadge = plan.project_name
        ? `<span class="card-project"><i data-lucide="folder" class="icon icon-xs"></i> ${escapeHtml(plan.project_name)}</span>`
        : '';
    const cockpitUrl = buildCopilotUrl(plan.id, plan.title, plan.project_name || filters.project || '');
    const detailUrl = buildPlanDetailUrl(plan);
    const projectWorkspaceUrl = plan.project_name
        ? `/project/${encodeURIComponent(plan.project_name)}`
        : '';
    const projectWorkspaceAction = projectWorkspaceUrl
        ? `<a href="${projectWorkspaceUrl}" class="card-inline-btn" onclick="event.stopPropagation()"><i data-lucide="folder-open" class="icon icon-xs"></i> Project</a>`
        : '';

    return `
    <div class="plan-card status-${statusClass}" ${dragAttr} onclick="location.href='${detailUrl}'">
        <div class="card-head">
            <span class="card-cat-badge cat-${plan.category || 'plan'}"><i data-lucide="${catIcon}" class="icon icon-xs"></i> ${plan.category || 'plan'}</span>
            <span class="card-wf-badge wf-${wfStage}">${wfStage.replace(/_/g, ' ')}</span>
        </div>
        <div class="card-body">
            <p class="card-title">${escapeHtml(plan.title)}</p>
            ${summary ? `<p class="card-summary">${escapeHtml(summary)}</p>` : ''}
        </div>
        <div class="card-foot">
            <div class="card-foot-meta">${projectBadge}</div>
            <div class="card-foot-actions">
                ${projectWorkspaceAction}
                <a href="${cockpitUrl}" class="card-inline-btn" onclick="event.stopPropagation()"><i data-lucide="message-square" class="icon icon-xs"></i> Cockpit</a>
            </div>
        </div>
    </div>`;
}

function buildPlanDetailUrl(plan) {
    var url = '/plans/' + encodeURIComponent(plan.id);
    if (!filters.project && !plan.project_name) return url;

    var params = new URLSearchParams();
    if (filters.project) {
        params.set('project', filters.project);
        params.set('from', 'index');
    } else if (plan.project_name) {
        params.set('project', plan.project_name);
    }
    return url + '?' + params.toString();
}

function renderGrid() {
    const grid = document.getElementById('plansGrid');
    grid.style.display = 'grid';
    let html = '';
    allPlans.forEach(plan => { html += _buildCardHtml(plan, false); });
    grid.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderBoard() {
    const board = document.getElementById('plansBoard');
    board.style.display = 'flex';

    // Gruppiere Plans nach workflow_stage
    const grouped = {};
    BOARD_COLUMNS.forEach(col => { grouped[col.stage] = []; });
    allPlans.forEach(plan => {
        const stage = plan.workflow_stage || 'idea';
        if (grouped[stage]) {
            grouped[stage].push(plan);
        } else {
            grouped['idea'].push(plan);
        }
    });

    let html = '';
    BOARD_COLUMNS.forEach(col => {
        const plans = grouped[col.stage];
        const count = plans.length;
        html += `
        <div class="board-column" data-stage="${col.stage}">
            <div class="board-column-header">
                <span class="badge badge-wf badge-wf-${col.stage}">${col.label}</span>
                <span class="board-count">${count}</span>
            </div>
            <div class="board-column-body" data-stage="${col.stage}">`;
        plans.forEach(plan => { html += _buildCardHtml(plan, true); });
        html += `
            </div>
        </div>`;
    });

    board.innerHTML = html;
    _initBoardDragDrop();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

// === View Toggle ===
function setView(view) {
    currentView = view;
    document.getElementById('viewGrid').classList.toggle('active', view === 'grid');
    document.getElementById('viewBoard').classList.toggle('active', view === 'board');
    renderPlans();
}

// === Drag & Drop ===
let _dragPlanId = null;
let _dragSourceStage = null;

function _initBoardDragDrop() {
    // Drag-Start auf Cards
    document.querySelectorAll('.plans-board .plan-card[draggable]').forEach(card => {
        card.addEventListener('dragstart', function(e) {
            _dragPlanId = parseInt(this.dataset.planId);
            _dragSourceStage = this.dataset.stage;
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', _dragPlanId);
        });
        card.addEventListener('dragend', function() {
            this.classList.remove('dragging');
            document.querySelectorAll('.board-column-body.drag-over').forEach(el => el.classList.remove('drag-over'));
            _dragPlanId = null;
            _dragSourceStage = null;
        });
    });

    // Drop-Zonen auf Column-Bodies
    document.querySelectorAll('.board-column-body').forEach(colBody => {
        colBody.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.classList.add('drag-over');
        });
        colBody.addEventListener('dragleave', function(e) {
            // Nur entfernen wenn wirklich verlassen (nicht bei Kind-Elementen)
            if (!this.contains(e.relatedTarget)) {
                this.classList.remove('drag-over');
            }
        });
        colBody.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            const targetStage = this.dataset.stage;
            const planId = parseInt(e.dataTransfer.getData('text/plain'));
            if (!planId || targetStage === _dragSourceStage) return;
            _moveCardToStage(planId, _dragSourceStage, targetStage);
        });
    });
}

function _moveCardToStage(planId, oldStage, newStage) {
    // Optimistisch: Card sofort verschieben
    const card = document.querySelector(`.plan-card[data-plan-id="${planId}"]`);
    const targetCol = document.querySelector(`.board-column-body[data-stage="${newStage}"]`);
    if (card && targetCol) {
        targetCol.appendChild(card);
        card.dataset.stage = newStage;
        // Badge auf Card aktualisieren
        const wfBadge = card.querySelector('.badge-wf');
        if (wfBadge) {
            wfBadge.className = `badge badge-wf badge-wf-${newStage}`;
            wfBadge.textContent = newStage.replace('_', ' ');
        }
        // Column-Counts aktualisieren
        _updateColumnCounts();
    }

    // API-Call
    api.put(`/api/plans/${planId}/workflow`, { workflow_stage: newStage })
        .then(function(result) {
            // Lokale Daten aktualisieren
            const plan = allPlans.find(p => p.id === planId);
            if (plan) {
                plan.workflow_stage = newStage;
                if (result.current_state !== undefined) plan.current_state = result.current_state;
                if (result.target_state !== undefined) plan.target_state = result.target_state;
                if (result.next_action !== undefined) plan.next_action = result.next_action;
            }
            showToast(`Plan in "${_stageLabel(newStage)}" verschoben`);
        })
        .catch(function(err) {
            // Rollback: Card zurueck in alte Spalte
            const sourceCol = document.querySelector(`.board-column-body[data-stage="${oldStage}"]`);
            if (card && sourceCol) {
                sourceCol.appendChild(card);
                card.dataset.stage = oldStage;
                const wfBadge = card.querySelector('.badge-wf');
                if (wfBadge) {
                    wfBadge.className = `badge badge-wf badge-wf-${oldStage}`;
                    wfBadge.textContent = oldStage.replace('_', ' ');
                }
                _updateColumnCounts();
            }
            showToast('Fehler: ' + (err.message || 'Workflow-Update fehlgeschlagen'), true);
        });
}

function _stageLabel(stage) {
    const col = BOARD_COLUMNS.find(c => c.stage === stage);
    return col ? col.label : stage;
}

function _updateColumnCounts() {
    document.querySelectorAll('.board-column').forEach(col => {
        const count = col.querySelectorAll('.plan-card').length;
        const countEl = col.querySelector('.board-count');
        if (countEl) countEl.textContent = count;
    });
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
    if (key === 'project' && value && typeof setActiveProjectContext === 'function') {
        setActiveProjectContext(value);
    }

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
var currentPlanId = null;

function slugifyPlanTitle(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'plan';
}

function buildCopilotUrl(planId, planTitle, projectName) {
    var url = `/copilot?plan_id=${encodeURIComponent(planId)}&plan=${encodeURIComponent(slugifyPlanTitle(planTitle))}`;
    if (projectName) {
        url += `&project=${encodeURIComponent(projectName)}`;
    }
    return url;
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

// === Workflow Panel für Sidebar ===
function _loadPlanWorkflow(planId) {
    api.get('/api/plans/' + planId + '/workflow')
        .then(function(wf) {
            if (wf.next_action) {
                const nextSection = document.createElement('div');
                nextSection.className = 'plan-sidebar-section';
                nextSection.innerHTML = `<span class="plan-sidebar-label">Next</span><div class="plan-next">${escapeHtml(wf.next_action)}</div>`;
                document.querySelector('.plan-modal-sidebar').appendChild(nextSection);
            }

            // Signale
            const signals = [];
            if (wf.latest_quality_score != null) signals.push(`<span class="signal-pill">Quality ${wf.latest_quality_score}</span>`);
            if (wf.governance_status) signals.push(`<span class="signal-pill gov-${wf.governance_status}">Gov ${wf.governance_status}</span>`);
            if (wf.latest_executor_status) signals.push(`<span class="signal-pill exec-${wf.latest_executor_status}">exec ${wf.latest_executor_status}</span>`);

            if (signals.length) {
                const sigSection = document.createElement('div');
                sigSection.className = 'plan-sidebar-section';
                sigSection.innerHTML = `<span class="plan-sidebar-label">Signale</span><div class="plan-signals">${signals.join('')}</div>`;
                document.querySelector('.plan-modal-sidebar').appendChild(sigSection);
            }
        })
        .catch(function() {});
}

function showHandoff(planId) {
    api.request('/api/plans/' + planId + '/handoff', { raw: true })
        .then(function(resp) { return resp.text(); })
        .then(function(md) {
            // Handoff-Markdown im Modal-Content anzeigen
            var content = document.getElementById('modalContent');
            content.innerHTML = '<div class="handoff-view">'
                + '<div class="handoff-actions">'
                + '<button class="btn btn-sm btn-primary" onclick="copyHandoff()"><i data-lucide="copy" class="icon icon-xs"></i> Kopieren</button> '
                + '<a href="/api/plans/' + planId + '/handoff" download="plan-handoff-' + planId + '.md" class="btn btn-sm btn-secondary"><i data-lucide="download" class="icon icon-xs"></i> Download</a>'
                + '</div>'
                + '<pre class="handoff-content">' + escapeHtml(md) + '</pre>'
                + '</div>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function(err) {
            showToast('Handoff-Fehler: ' + (err.message || 'Unbekannt'), true);
        });
}

function copyHandoff() {
    var pre = document.querySelector('.handoff-content');
    if (!pre) return;
    navigator.clipboard.writeText(pre.textContent)
        .then(function() { showToast('Handoff in Zwischenablage kopiert'); })
        .catch(function() { showToast('Kopieren fehlgeschlagen', true); });
}

function showToast(msg, isError) {
    const toast = document.getElementById('syncToast');
    toast.textContent = msg;
    toast.className = 'toast show' + (isError ? ' toast-error' : '');
    setTimeout(() => toast.className = 'toast', 4000);
}

// formatDate: in base.js (global)
