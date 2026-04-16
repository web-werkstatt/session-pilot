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
    initPlansContextBar();
    loadStats();
    loadPlans();
    loadProjects();
});

function initPlansContextBar() {
    var contextBar = document.getElementById('plansContextBar');
    var backLink = document.getElementById('plansBackLink');
    if (!contextBar || !backLink || !filters.project) return;
    backLink.href = '/project/' + encodeURIComponent(filters.project) + '?tab=plans';
    contextBar.style.display = 'block';
}

// === Data ===
function loadPlans() {
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.project) params.set('project', filters.project);
    if (filters.category) params.set('category', filters.category);

    return api.get('/api/plans?' + params.toString())
        .then(data => {
            // Diese Seite zeigt ausschliesslich lokale Plaene:
            //   - project_sprints  (<project>/sprints/)
            //   - project_plans    (<project>/plans/)
            // Claude-Plans, Docs-Plans und Projekt-Root bleiben ausgeblendet.
            allPlans = (data.plans || []).filter(_isLocalPlanOrSprint);
            renderPlans();
        })
        .catch(err => {
            console.error('Error:', err);
            document.getElementById('loading').innerHTML = '<div class="error">Error loading</div>';
        });
}

var _PLANS_VISIBLE_SOURCE_KINDS = new Set(['project_sprints', 'project_plans']);

function _isLocalPlanOrSprint(plan) {
    return _PLANS_VISIBLE_SOURCE_KINDS.has(plan && plan.source_kind || '');
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
    const dragAttr = draggable ? `draggable="true" data-plan-id="${plan.id}" data-stage="${wfStage}"` : '';
    // Kategorie liefert Label + Klasse + Icon konsistent — Sprint-Plaene sehen
    // unabhaengig von detect_category() als "Sprintplan" aus.
    const catMeta = _buildPlanCategoryMeta(plan);
    // Zweiter (inhaltlicher) Category-Badge — nur bei Sprint-Plaenen, damit die
    // detect_category()-Info (feature/bugfix/refactor/infra/plan) nicht verloren geht.
    const contentCatBadge = _buildPlanContentCategoryBadge(plan);
    // Default-Workflow-Stage 'idea' wird nicht als Badge gerendert (zu unspezifisch).
    const wfBadge = wfStage && wfStage !== 'idea'
        ? `<span class="card-wf-badge wf-${wfStage}">${wfStage.replace(/_/g, ' ')}</span>`
        : '';

    const summary = plan.context_summary || plan.description || '';

    const projectBadge = plan.project_name
        ? `<span class="card-project"><i data-lucide="folder" class="icon icon-xs"></i> ${escapeHtml(plan.project_name)}</span>`
        : '';
    const sourceBadge = _buildPlanSourceBadge(plan);
    // Card-Date zeigt die echte Datei-Aenderungszeit (file_mtime_iso),
    // nicht DB-updated_at — Letzteres kann durch System-Syncs gebumpt werden
    // (z.B. Auto-Tagging-Lauf) und ist dann irrefuehrend.
    const planDate = plan.file_mtime_iso || plan.updated_at || plan.created_at || '';
    const dateBadge = planDate
        ? `<span class="card-date" title="Datei zuletzt geaendert">${formatDate(planDate)}</span>`
        : '';
    const cockpitUrl = buildCopilotUrl(plan.id, plan.title, plan.project_name || filters.project || '');
    const detailUrl = buildPlanDetailUrl(plan);
    // Phase 7 (2026-04-14): Project-Button entfernt — Card-Klick fuehrt zum Plan-Detail,
    // Projekt-Badge im Footer bleibt. Project-Workspace erreichbar ueber Breadcrumb oder Sidebar.

    return `
    <div class="plan-card status-${statusClass}" ${dragAttr} onclick="location.href='${detailUrl}'">
        <div class="card-head">
            <span class="card-cat-badge cat-${catMeta.cssKey}"><i data-lucide="${catMeta.icon}" class="icon icon-xs"></i> ${escapeHtml(catMeta.label)}</span>
            ${contentCatBadge}
            ${wfBadge}
            ${sourceBadge}
        </div>
        <div class="card-body">
            <p class="card-title">${escapeHtml(plan.title)}</p>
            ${summary ? `<p class="card-summary">${escapeHtml(summary)}</p>` : ''}
        </div>
        <div class="card-foot">
            <div class="card-foot-meta">${projectBadge}${dateBadge}</div>
            <div class="card-foot-actions">
                <a href="${cockpitUrl}" class="card-inline-btn" onclick="event.stopPropagation()"><i data-lucide="message-square" class="icon icon-xs"></i> Cockpit</a>
            </div>
        </div>
    </div>`;
}

/**
 * Category-Meta (Label + CSS-Klasse + Icon) fuer Plan-Cards.
 * Sprint-Plaene (plan_type === 'sprint' ODER source_kind === 'project_sprints')
 * bekommen eine einheitliche Optik (cssKey=sprint, icon=rocket, label=Sprintplan).
 * Sonstige Plaene behalten detect_category()-Wert als Label, Klasse, Icon.
 */
function _buildPlanCategoryMeta(plan) {
    var type = plan.plan_type || '';
    var kind = plan.source_kind || '';
    if (type === 'sprint' || kind === 'project_sprints') {
        return { label: 'Sprintplan', cssKey: 'sprint', icon: 'rocket' };
    }
    var cat = plan.category || 'plan';
    return { label: cat, cssKey: cat, icon: getCategoryIcon(cat) };
}

/**
 * Zweiter Category-Badge fuer Sprint-Plaene — zeigt die inhaltliche
 * Kategorie aus detect_category() (feature/bugfix/refactor/infra/plan)
 * rechts neben dem "Sprintplan"-Badge. Bei Nicht-Sprint-Plaenen leer.
 */
function _buildPlanContentCategoryBadge(plan) {
    var type = plan.plan_type || '';
    var kind = plan.source_kind || '';
    var isSprint = (type === 'sprint' || kind === 'project_sprints');
    if (!isSprint) return '';
    var cat = plan.category || 'plan';
    var icon = getCategoryIcon(cat);
    return '<span class="card-cat-badge cat-' + escapeHtml(cat) + '">'
        + '<i data-lucide="' + escapeHtml(icon) + '" class="icon icon-xs"></i> '
        + escapeHtml(cat) + '</span>';
}

/**
 * Source-Badge fuer Plan-Cards (rekonstruiert aus sprint-plan-discovery-followup.md).
 * plan_type wird vom API-Endpoint /api/plans geliefert (claude/sprint/plan/docs/root).
 * 'sprint' und 'plan' werden NICHT als Badge gerendert — diese Info liegt bereits
 * im Category-Label ('Sprintplan' bzw. 'plan'), der Source-Badge waere redundant.
 */
function _buildPlanSourceBadge(plan) {
    var type = plan.plan_type || '';
    if (!type || type === 'sprint' || type === 'plan') return '';
    var label;
    switch (type) {
        case 'claude': label = 'Claude Plan'; break;
        case 'docs':   label = 'Docs'; break;
        case 'root':   label = 'Projekt-Root'; break;
        default:       return '';
    }
    var tip = plan.source_path ? ' title="' + escapeHtml(plan.source_path) + '"' : '';
    return '<span class="card-source-badge src-' + escapeHtml(type) + '"' + tip + '>' + escapeHtml(label) + '</span>';
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
// Drag & Drop Logik ausgelagert in plans-board.js (Phase 7, 2026-04-14).

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

    // Phase 7 (2026-04-14): Project-Filter aktualisiert URL + Breadcrumb.
    if (key === 'project' && window.history && window.history.replaceState) {
        const url = new URL(window.location.href);
        if (value) url.searchParams.set('project', value);
        else url.searchParams.delete('project');
        window.history.replaceState(null, '', url.toString());
        _updateBreadcrumbProject(value);
    }

    loadPlans();
    loadStats();
}

function _updateBreadcrumbProject(project) {
    const bc = document.querySelector('.breadcrumb');
    if (!bc) return;
    // Bestehenden Projekt-Link entfernen (plus Separator davor/dahinter).
    const existing = bc.querySelector('.bc-project-injected');
    if (existing) {
        const sep = existing.nextSibling;
        if (sep && sep.classList && sep.classList.contains('bc-sep')) sep.remove();
        existing.remove();
    }
    if (!project) return;
    const bcActive = bc.querySelector('.bc-active');
    if (!bcActive) return;
    const link = document.createElement('a');
    link.href = '/project/' + encodeURIComponent(project);
    link.textContent = project;
    link.className = 'bc-link bc-project-injected';
    const sep = document.createElement('span');
    sep.className = 'bc-sep';
    sep.textContent = '/';
    bc.insertBefore(link, bcActive);
    bc.insertBefore(document.createTextNode(' '), bcActive);
    bc.insertBefore(sep, bcActive);
    bc.insertBefore(document.createTextNode(' '), bcActive);
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
