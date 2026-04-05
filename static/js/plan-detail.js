var PLAN_DETAIL_ID = null;
var PLAN_DETAIL_DATA = null;
var PLAN_WORKFLOW_DATA = null;
var PLAN_HANDOFF_LOADED = false;
var PLAN_DETAIL_QUERY = null;

document.addEventListener('DOMContentLoaded', function() {
    var root = document.querySelector('.plan-detail-page');
    if (!root) return;
    PLAN_DETAIL_ID = parseInt(root.dataset.planId, 10);
    PLAN_DETAIL_QUERY = new URLSearchParams(window.location.search);
    if (!PLAN_DETAIL_ID) return;
    loadPlanDetailPage();
});

function loadPlanDetailPage() {
    Promise.all([
        api.get('/api/plans/' + PLAN_DETAIL_ID),
        api.get('/api/plans/' + PLAN_DETAIL_ID + '/workflow').catch(function() { return null; })
    ])
        .then(function(results) {
            PLAN_DETAIL_DATA = results[0];
            PLAN_WORKFLOW_DATA = results[1];
            renderPlanDetailPage();
            loadPlanHandoff();
        })
        .catch(function(err) {
            var loading = document.getElementById('planDetailLoading');
            var error = document.getElementById('planDetailError');
            if (loading) loading.style.display = 'none';
            if (error) error.style.display = 'block';
            document.getElementById('planDetailErrorText').textContent = err && err.message ? err.message : 'Unknown error';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        });
}

function renderPlanDetailPage() {
    var plan = PLAN_DETAIL_DATA || {};
    var wf = PLAN_WORKFLOW_DATA || {};
    document.getElementById('planDetailLoading').style.display = 'none';
    document.getElementById('planDetailShell').style.display = 'block';

    document.getElementById('detailCategory').innerHTML = '<i data-lucide="' + getCategoryIcon(plan.category) + '" class="icon icon-xs"></i> ' + escapeHtml(plan.category || 'plan');
    document.getElementById('detailTitle').textContent = plan.title || ('Plan ' + PLAN_DETAIL_ID);
    document.getElementById('detailStatus').textContent = statusLabel(plan.status);
    document.getElementById('detailStatus').className = 'status-pill status-' + (plan.status || 'draft');

    var wfStage = plan.workflow_stage || (wf && wf.workflow_stage) || 'idea';
    document.getElementById('detailWorkflow').textContent = wfStage.replace(/_/g, ' ');
    document.getElementById('detailWorkflow').className = 'wf-pill wf-' + wfStage;
    document.getElementById('detailWorkflowStage').innerHTML = '<span class="wf-pill wf-' + wfStage + '">' + escapeHtml(wfStage.replace(/_/g, ' ')) + '</span>';

    var meta = [];
    if (plan.project_name) meta.push('<span><i data-lucide="folder" class="icon icon-xs"></i> ' + escapeHtml(plan.project_name) + '</span>');
    if (plan.created_at) meta.push('<span><i data-lucide="calendar" class="icon icon-xs"></i> ' + formatDate(plan.created_at) + '</span>');
    if (plan.updated_at) meta.push('<span><i data-lucide="refresh-cw" class="icon icon-xs"></i> Updated ' + formatDate(plan.updated_at) + '</span>');
    document.getElementById('detailMeta').innerHTML = meta.join('');

    document.getElementById('detailIst').textContent = plan.current_state || wf.current_state || '—';
    document.getElementById('detailSoll').textContent = plan.target_state || wf.target_state || '—';
    document.getElementById('detailSummary').textContent = plan.context_summary || 'No summary available.';
    document.getElementById('detailContent').innerHTML = plan.content_html || '<em>No content</em>';

    var sidebarMeta = [];
    if (plan.filename) sidebarMeta.push('<div class="meta-row"><span>File</span><code>' + escapeHtml(plan.filename.split('/').pop()) + '</code></div>');
    if (plan.session_slug) sidebarMeta.push('<div class="meta-row"><span>Session</span><a href="/sessions/' + plan.session_slug + '"><i data-lucide="bot" class="icon icon-xs"></i> Open</a></div>');
    if (plan.project_name) sidebarMeta.push('<div class="meta-row"><span>Project</span><a href="/project/' + encodeURIComponent(plan.project_name) + '">' + escapeHtml(plan.project_name) + '</a></div>');
    document.getElementById('detailMetaSidebar').innerHTML = sidebarMeta.join('') || '<span class="text-muted">—</span>';

    var nextAction = wf.next_action || plan.next_action || '';
    document.getElementById('detailNextAction').innerHTML = nextAction
        ? '<span class="plan-sidebar-label">Next</span><div class="plan-next">' + escapeHtml(nextAction) + '</div>'
        : '<span class="text-muted">No next action defined.</span>';

    var signals = [];
    if (wf.latest_quality_score != null) signals.push('<span class="signal-pill">Quality ' + escapeHtml(String(wf.latest_quality_score)) + '</span>');
    if (wf.governance_status) signals.push('<span class="signal-pill gov-' + escapeHtml(wf.governance_status) + '">Gov ' + escapeHtml(wf.governance_status) + '</span>');
    if (wf.latest_executor_status) signals.push('<span class="signal-pill exec-' + escapeHtml(wf.latest_executor_status) + '">exec ' + escapeHtml(wf.latest_executor_status) + '</span>');
    document.getElementById('detailSignals').innerHTML = signals.length ? signals.join('') : '<span class="text-muted">No signals available.</span>';

    var cockpitUrl = buildPlanDetailCopilotUrl(plan.id, plan.title);
    document.getElementById('planDetailCopilotBtn').href = cockpitUrl;
    document.getElementById('planDetailCopilotTop').href = cockpitUrl;
    document.getElementById('planDetailHandoffDownload').href = '/api/plans/' + plan.id + '/handoff';
    document.getElementById('planDetailHandoffDownload').setAttribute('download', 'plan-handoff-' + plan.id + '.md');

    updateContextNavigation(plan);

    renderTaggedStructure(plan.tagged_sections || []);

    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderTaggedStructure(sections) {
    var panel = document.getElementById('detailStructurePanel');
    var container = document.getElementById('detailStructure');
    if (!sections || !sections.length) {
        panel.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    panel.style.display = 'block';
    container.innerHTML = sections.map(function(section) {
        var specs = Array.isArray(section.specs) ? section.specs : [];
        var directMarkers = Array.isArray(section.direct_markers) ? section.direct_markers : (Array.isArray(section.markers) ? section.markers : []);
        var specHtml = specs.map(function(spec) {
            var markers = Array.isArray(spec.markers) ? spec.markers : [];
            return '<div class="plan-structure-spec">'
                + '<div class="plan-structure-spec-title">' + escapeHtml(spec.title || 'Spec') + '</div>'
                + '<div class="plan-structure-spec-meta">' + markers.length + ' markers</div>'
                + '</div>';
        }).join('');

        return '<div class="plan-structure-sprint">'
            + '<div class="plan-structure-head">'
            + '<strong>' + escapeHtml(section.title || 'Sprint') + '</strong>'
            + '<span>' + directMarkers.length + ' direct markers</span>'
            + '</div>'
            + '<div class="plan-structure-body">' + specHtml + '</div>'
            + '</div>';
    }).join('');
}

function switchPlanDetailTab(tab, btn) {
    document.querySelectorAll('.plan-detail-tab').forEach(function(item) {
        item.classList.toggle('active', item.dataset.tab === tab);
    });
    document.querySelectorAll('.plan-detail-tab-body').forEach(function(body) {
        body.classList.toggle('active', body.id === 'tab-' + tab);
    });
    if (btn) btn.classList.add('active');
    if (tab === 'handoff' && !PLAN_HANDOFF_LOADED) loadPlanHandoff();
}

function loadPlanHandoff() {
    if (PLAN_HANDOFF_LOADED) return;
    api.request('/api/plans/' + PLAN_DETAIL_ID + '/handoff', { raw: true })
        .then(function(resp) { return resp.text(); })
        .then(function(md) {
            PLAN_HANDOFF_LOADED = true;
            document.getElementById('detailHandoffContent').textContent = md || '';
        })
        .catch(function(err) {
            document.getElementById('detailHandoffContent').textContent = 'Handoff could not be loaded: ' + (err.message || 'Unknown error');
        });
}

function copyPlanHandoff() {
    var pre = document.getElementById('detailHandoffContent');
    if (!pre) return;
    navigator.clipboard.writeText(pre.textContent || '')
        .then(function() { if (typeof showToast === 'function') showToast('Handoff copied'); })
        .catch(function() {});
}

function downloadPlanHandoff() {
    window.location.href = '/api/plans/' + PLAN_DETAIL_ID + '/handoff';
}

function buildPlanDetailCopilotUrl(planId, planTitle) {
    return '/copilot?plan_id=' + encodeURIComponent(planId) + '&plan=' + encodeURIComponent(slugifyPlanDetailTitle(planTitle));
}

function updateContextNavigation(plan) {
    var projectName = (PLAN_DETAIL_QUERY && PLAN_DETAIL_QUERY.get('project')) || plan.project_name || '';
    var origin = PLAN_DETAIL_QUERY && PLAN_DETAIL_QUERY.get('from');
    var backLink = document.getElementById('planDetailBackLink');
    var projectLink = document.getElementById('planDetailProjectLink');
    var contextHint = document.getElementById('planDetailContextHint');
    var indexUrl = '/plans';

    if (projectName && origin === 'index') {
        indexUrl += '?project=' + encodeURIComponent(projectName);
    }

    if (backLink) {
        backLink.href = indexUrl;
    }

    if (projectLink && projectName) {
        projectLink.href = '/project/' + encodeURIComponent(projectName);
        projectLink.style.display = 'inline-flex';
    }

    if (contextHint && projectName) {
        contextHint.style.display = 'block';
        contextHint.innerHTML = 'This plan belongs to <strong>' + escapeHtml(projectName) + '</strong>. Use <a href="/project/' + encodeURIComponent(projectName) + '" style="color:#4fc3f7">Planning</a> for the primary workspace and this detail page for direct deep links.';
    }
}

function slugifyPlanDetailTitle(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'plan';
}

function getCategoryIcon(cat) {
    var icons = {
        'plan': 'file-text',
        'feature': 'sparkles',
        'bugfix': 'bug',
        'refactor': 'wrench',
        'ops': 'server',
        'research': 'search',
        'spec': 'clipboard-list',
    };
    return icons[cat] || 'file-text';
}

function statusLabel(status) {
    var labels = {
        'draft': 'Draft',
        'active': 'Active',
        'completed': 'Done',
        'archived': 'Archive',
    };
    return labels[status] || status || 'Draft';
}
